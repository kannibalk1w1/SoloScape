# Journeys sprint: orphan-session recovery and controller name entry — design review

This was a static design audit only. I made no source edits, builds or commits, ran no game,
used no network, and read no saves, cache or credentials. I read:
- `scripts/profile_session.py`, `launcher_backend.py`, `profiles.py`, `local_dev.stop`
- `scripts/test_launcher_backend.py`, the killed-launcher test in particular
- `SoloScapeLauncher.java` (`newCharacter`, `startController`)
- `EntryControls.java` and `EntryState.java`

The recommendations below are designs, not verified behaviour.

## 1. Current behaviour and the actual orphan cases
- The JVMs are started with `start_new_session=True` and `pass_fds=(profile.lock, build.lock)`
  (`profile_session.py:72, 93`). Each JVM holds the same open file descriptions, so both
  `flock`s stay held until the last owned JVM exits.
- Nothing records the children's PIDs. `stop()` uses `os.killpg(process.pid, SIGTERM)` and then
  waits forever (`local_dev.py:113-127`), and only the in-process `Popen` object knows the PID.
- **Loss of the launcher GUI is already safe.** The backend sees EOF on stdin, `serve` exits,
  `close()` sets `cancelled` and joins the worker, and the worker stops the client and server
  gracefully and takes the post-stop backup.
- **Loss of the backend is the orphan case.** That covers SIGKILL, OOM, a crash outside the
  worker, and also **plain SIGTERM**: Python's default SIGTERM action ends the process without
  running `finally`, `serve`'s `backend.close()` or the worker's cleanup. Then:
  - the server, and the client if it was started, keep running and keep both locks;
  - the after-clean-shutdown backup never happens;
  - a new launcher only sees "This character/world is running or another save operation is
    active" (`profiles.py:149-151`) and has no way to Save & Quit;
  - after the user closes the orphaned client window, the **server keeps running forever**,
    because no parent is left to stop it, and the world stays locked.
- **Smallest immediate fix, independent of recovery:** install a SIGTERM/SIGHUP handler in
  `launcher_backend.py` that sets `cancelled` and lets `serve` and `close()` finish. That turns
  the most common "launcher killed" case into a normal graceful stop. Keep SIGKILL and OOM for
  the recovery design below.

## 2. Recommended recovery design

### 2.1 Persisted session record (written under the profile lock)
`profiles/<id>/session.json` (0600, written with `atomic_json`). Write it **before** the first
`Popen`, with `state: "starting"`, then update it right after each `Popen`:

```json
{"format":1,"session":"<uuid4>","profile":"<id>","generation":"<generation>",
 "boot_id":"<contents of /proc/sys/kernel/random/boot_id>","backend_pid":1234,
 "port":43594,"started_at":"…","state":"starting|playing|stopping",
 "server":{"pid":5678,"starttime":123456789,"jar":"/abs/void-server-x.jar"},
 "client":{"pid":5690,"starttime":123456800,"jar":"/abs/void-client-x.jar"}}
```

- `starttime` is field 22 of `/proc/<pid>/stat`, the start time in clock ticks since boot.
  Parse it *after* the last `)` of the comm field, because comm can contain spaces or `)`.
- `boot_id` together with `starttime` identifies a process across PID reuse. A record with a
  different `boot_id` is from an earlier boot, so its processes can't exist any more.
- Pass `SOLOSCAPE_SESSION_ID=<uuid>` in the owned environment. It has no dot, so
  `owned_environment` keeps it, and it lets identity be checked from `/proc/<pid>/environ`.
- Remove the record only **after** the after-clean-shutdown backup succeeds, or after a startup
  that was cancelled before any JVM started. A record that is still there therefore always
  means a session ended without verified closure.
- Gap to close: if the backend dies between `Popen` and the PID update, the record still says
  `starting` with no PID. Recovery then has to fall back to a discovery scan (2.3).

### 2.2 Identity check before signalling anything
A candidate PID is accepted only if **all** of these hold. Read everything from `/proc`, and
never print `environ` or `cmdline` contents.
1. The current `boot_id` equals the recorded one, and `/proc/<pid>/stat` `starttime` equals the
   recorded value. This rejects PID reuse.
2. The process has the same owner uid as the launcher (`os.stat('/proc/<pid>').st_uid`).
3. `/proc/<pid>/environ` contains exactly `SOLOSCAPE_SESSION_ID=<uuid>` **and**
   `storage.players.path=<this profile's absolute saves path>`. This rejects unrelated Java
   processes, and SoloScape worlds belonging to other profiles.
4. **Inherited lock identity:** one of `/proc/<pid>/fd/*` resolves to a file whose `(st_dev,
   st_ino)` equals `os.stat(profile.lock)`. Optionally, `/proc/<pid>/fdinfo/<n>` shows a
   `lock:` FLOCK line. This proves the process is what keeps the profile locked. Don't rely on
   `/proc/locks` PIDs, because they can name the dead backend that originally took the lock.
5. The process isn't a zombie (`stat` state `Z`). If it is stopped (state `T`, for example
   after SIGSTOP or a frozen terminal job), warn that SIGTERM won't take effect until it
   continues. Never send SIGCONT or SIGKILL automatically.

For the race between checking and signalling, open `os.pidfd_open(pid)` (Python 3.9+, Linux
5.3+) **first**, then run checks 1–5, then use `signal.pidfd_send_signal(fd, SIGTERM)`, and wait
for the pidfd to become readable to detect exit. A pidfd can't be redirected to a reused PID. If
`pidfd_open` isn't available, refuse automatic stop and show manual instructions instead of
falling back to `os.kill`.

### 2.3 Discovery when the record is missing or incomplete
If the profile lock is busy and there's no usable record, scan only the current uid's
`/proc/[0-9]*` for processes that pass checks 2–4 (environ `storage.players.path` plus a
profile.lock fd). Show what you find, but **never auto-stop** something found this way. Require
the user to confirm, because the record's session id and start time aren't available.

### 2.4 Recovery flow in the launcher
- Add a separate `profiles/<id>/recovery.lock` (exclusive, non-blocking) so two launchers can't
  both act on one orphan.
- `list` / `status` should report `orphaned: {server_pid, client_alive, started_at}` when the
  profile lock is busy and a record passes 2.2. The GUI then shows "World still running from
  an earlier launcher session".
- **Don't stop it automatically.** The user may still be playing in the orphaned client. Offer
  two choices:
  - **Reattach.** Watch the pidfds and show "playing". Save & Quit then signals SIGTERM to the
    client first, then the server, waiting each time.
  - **Save & Quit now.**
- Stop order: signal the client, wait, then signal the **server's process group**. Check that
  `os.getpgid(pid) == pid` first (it is the leader because of `start_new_session`), then
  `os.killpg`, or signal the leader through its pidfd. Never SIGKILL, and keep the existing
  "Still saving…" status after 60 s.
- Once both processes have exited, the inherited descriptions close and the locks are
  released. Take the profile lock normally, then run the backup step below while holding it.

### 2.5 Backup truth after launcher loss
A recovering launcher **can't** see the server's exit status, because the server isn't its
child. So the existing rule ("returncode in (0, 143, −15) and ready") can't be applied. Options,
from most to least reliable:
1. **Preferred (small server patch): a clean-shutdown marker.** At the end of the shutdown hook,
   after `World.shutdown()` → `worldDespawn` (`saveQueue.direct().join()` plus `exchange.save()`)
   and `AuditLog.save()`, atomically write
   `<storage.players.path>/../session-clean-<SOLOSCAPE_SESSION_ID>`. Recovery then takes an
   `after-clean-shutdown` backup only if that marker exists for the recorded session, and
   deletes the marker afterwards.
2. **Without the marker:** take a backup with a **new** reason, for example
   `after-recovered-shutdown`, and only if:
   - every top-level account TOML passes `validate_save`,
   - there is no `.save-*.tmp`,
   - the errors directory is empty.

   `retention_plan` currently prunes only `before-launch` and `after-clean-shutdown`, so the new
   reason is kept by default. That's the conservative choice.
3. **Otherwise:** take no backup. Tell the user that the newest verified backup is the
   before-launch one from the recorded `started_at`, and that the on-disk save may be newer and
   unverified.

In every case, leave `session.json` in place until one of these outcomes is recorded. Also add a
`recovered_from_session` field to the backup manifest so this history can be traced.

### 2.6 Failure cases the tests should cover
- The backend is SIGKILLed while playing; a new launcher detects, reattaches and stops it, gets
  the marker, takes the backup and removes the record.
- The recorded PID has exited and the PID was reused by an unrelated process with a different
  `starttime`. Expect "not running", no signal sent, and the backup-truth path applied.
- A process with the same PID and `starttime` but a different `boot_id` (simulate this by
  editing the record) is rejected.
- A Java process for **another** profile, with a different `storage.players.path`, is rejected
  even if the record PID matches.
- A record that says `starting` with no PID gets discovery-only behaviour and no automatic
  stop.
- Two launchers race on recovery: one wins `recovery.lock`, and the other reports busy.
- A stopped (`T`) orphan produces a warning and no signal escalation.
- A missing marker leads to `after-recovered-shutdown` or no backup, never
  `after-clean-shutdown`.
- The backend receives SIGTERM, and the handler gives a normal graceful stop with no record
  left behind.

**Test seam:** the current tests use a Python `FAKE_JAVA`, so `/proc/<pid>/exe` is Python, not
Java. Identity therefore has to be based on environ, starttime and the lock fd (as above), not
on the executable name. Otherwise the tests will need a matcher they can inject.

## 3. Controller name entry in the launcher (reusing `EntryControls`)
Current gap: `newCharacter()` uses `JTextField`s in a `JOptionPane`. `startController()` can
only move Swing focus with the D-pad or stick, press buttons with A, and close dialogs with B.
It can't type, so creating a character is impossible with a controller alone.

`EntryControls` can be reused as it is. It depends only on `EntryState` and the three
`UiControls.Gateway` entry methods. Recommended adapter:
- **Adapter gateway.** `editEntry` writes into the focused `JTextField` on the EDT and returns
  true. `submitEntry` moves to the next field, or presses OK on the last one. `cancelEntry`
  leaves the keyboard but keeps the dialog open. Every other `Gateway` method is a no-op.
  Create a new `EntryState(type, revision++, label, field.getText())` each time a field gains
  focus, so `sameSession` resets the cursor when moving between fields.
- **Validation per field must match the backend.**
  - The account name must match `ACCOUNT = [A-Za-z0-9 _]{1,12}` (`profiles.py`).
  - The label must be 1–48 characters after `strip()`.
  - `EntryControls.keys()` offers `-` and `'`, and `EntryState.valid` for type 8 accepts any
    printable ASCII up to 12 characters. For the account field the keyboard could therefore
    produce input the backend rejects.

  Fix: add an account-name `EntryState` type, or a validator or key-set parameter, that leaves
  out `-` and `'`. Also show the backend's error inline instead of closing the dialog.
- **There is no uppercase.** The keys are lowercase only. Account files are lowercased anyway,
  but labels and the displayed account name will always be lowercase. Optionally add a Shift
  key, which needs a key-set change in `EntryControls`.
- **Input must have one owner.** While the keyboard is active, `startController()`'s timer must
  stop its own D-pad, stick, A, B, LB and RB handling. Otherwise one D-pad press both moves the
  key cursor and moves Swing focus, and B both cancels the entry and `dispose()`s the dialog. B
  should go in two steps: cancel the entry, then close the dialog.
- **Re-arm.** `EntryControls` requires A, B, X, Y and the D-pad to be released before it acts,
  and the launcher has its own `armed`. When the keyboard opens because of an A press, make
  sure that A isn't treated as a key press. The `armed=false` reset on open already does this,
  provided the adapter calls `reset()` when it activates.
- **Something visible on screen.** `EntryControls` has no renderer; the in-game overlay draws
  it. The launcher needs a small Swing panel: a 6-column key grid with the current `index`
  highlighted, plus its prompt line.
- **Remapped buttons.** `EntryControls.prompt()` hard-codes A, X, Y and B. The launcher reads
  raw SDL buttons and ignores plugin remaps, so that's consistent. Just don't pass these
  strings through the in-game `hint()` mapper.
- **Tutorial checkbox.** A presses `AbstractButton`s, so the `JCheckBox` already toggles. No
  change is needed.

## 4. Limits
- I didn't run anything or check `/proc` details on this machine. These details should be
  confirmed in tests on Linux:
  - the format of `fdinfo` `lock:` lines, which varies by kernel,
  - `pidfd` availability,
  - whether `environ` can be read for the same uid under hardened `ptrace_scope`. Reading
    `/proc/<pid>/environ` needs `PTRACE_MODE_READ`, which a same-uid process has unless
    Yama `ptrace_scope` is 2 or higher. If it can't be read, refuse to auto-stop.
- The clean-shutdown marker needs a small server patch. Where it belongs relative to the
  pinned shutdown hook (`Main.kt`) should be checked against the startup-ordering change in
  `CLAUDE_SESSION_FOLLOWUP.md`. In particular, a cancel *before* the hook is registered must
  never leave a marker behind.
- I didn't review any launcher GUI layout code beyond the two methods named.
