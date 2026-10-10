# Journeys sprint: implementation review (session recovery and launcher name entry)

This was a bounded static review. I made no source edits, builds, tests or commits, ran no
game, used no network, and read no saves, cache or credentials. I read:
- `scripts/session_recovery.py` and `test_session_recovery.py` (test names and structure only)
- the `profile_session.py` and `launcher_backend.py` integration
- `EntryState.java`, `EntryControls.java`, `LauncherKeyboard.java`
- `SoloScapeLauncher.java` (`newCharacter`, `recoverSession`, `startController`)

Implementation remains Codex's responsibility.

## Verdict
**No safety blockers.** Nothing can signal an unrelated process. The checks are boot id,
process start time, uid, session id plus role plus saves path in the environment, the jar in
argv, both inherited `FLOCK` descriptions, a pidfd opened before verification, and a stopped
process refusing all signals. A recovered backup is never labelled clean.

There are three **medium** findings where the profile can get stuck behind a session record
with no way out from the launcher (findings 1–3). The rest is low.

## Verified
- **PID reuse, boot and start.**
  - `same_process` compares `/proc/<pid>/stat` start time (parsed after the last `)`) and
    rejects `Z`/`X`.
  - `candidates` and `verified` require the recorded `boot` to equal the current one.
  - `recover` opens every pidfd, then verifies, then checks for suspension (`T`/`t`), and
    signals nothing until **all** roles pass (`session_recovery.py:174-182`). Signals go only
    through `pidfd_send_signal`.
  - Without pidfd support, nothing is signalled.
- **Session, role, environment, argv and locks.**
  - Required in the environment: `SOLOSCAPE_SESSION_ID`, `SOLOSCAPE_SESSION_ROLE` and this
    profile's `storage.players.path`.
  - Required in argv: the recorded jar path.
  - The current `(st_dev, st_ino)` of profile.lock and build.lock must match the recorded
    values, and both must appear in `fdinfo` with `FLOCK` (`:83-111`).
  - The environment and argv are compared, never logged.
- **Death between `Popen` and the record.**
  - `begin()` writes the record (`phase: starting`) before any `Popen`, under the profile lock,
    and refuses if a record already exists.
  - A child that never got registered is found by the exact session-id-plus-role-plus-guards
    scan (`candidates`), which the test covers.
  - Death between `begin` and `Popen` leaves a record with no children. Recovery then only
    takes the lock and the checked backup.
- **Normal cleanup survives record I/O failure.**
  - The `phase: stopping` write in `finally` is wrapped (`profile_session.py` `finally`).
  - `local_dev.stop` for the client and server always runs **before** any later record
    write or unlink that could raise.
  - A failed `registered()` write also falls into `finally` and stops the server normally.
- **Owner vs orphan.**
  - `owner = identity(backend pid)` with its start time. `inspect`/`recover` refuse while the
    owner is alive, unless the phase is `unverified`.
  - `test_live_original_launcher_is_not_adopted` covers this.
- **No clean claim.**
  - `recover` waits for each pidfd without SIGKILL. It then takes the profile lock (which
    proves the inherited guards were released), checks that the record is still the same,
    and refuses if `errors/` has any entries or any `.save-*.tmp` exists.
  - It backs up only as `after-recovered-shutdown`, which retention keeps.
  - The UI and notify text both say "Clean shutdown is unconfirmed".
- **Backend SIGTERM/SIGHUP.** `graceful_exit` raises `SystemExit` in the main thread.
  `serve`'s `finally` → `close()` → cancel and join, so the normal graceful stop runs. A second
  signal during the join still can't orphan anything, because the interpreter joins the
  non-daemon worker on exit.
- **Controller name entry.**
  - Account input uses `[A-Za-z0-9 _]`, at most 12 characters (`EntryState.LAUNCHER_ACCOUNT`),
    with an account-only key set without `-`/`'`. Labels allow up to 48 characters, and Shift
    applies to launcher types only. Native in-game key sets and types are unchanged, so in-game
    entry doesn't regress.
  - `activate()` feeds a held A, so the keyboard needs a neutral release first.
  - While the keyboard is active the launcher timer returns early, so the Swing focus and
    dialog-B handling don't run. B leaves the keyboard first, and only a later B closes the
    dialog.
  - `armed` re-arms on window change.
  - A failed `create` keeps the dialog open, shows the backend message and re-enables
    Create.
  - The `DocumentFilter` applies the same validation to desktop typing.

## Findings
### 1. Medium: a stale record owned by the *current* launcher blocks both Start and Recover
In the clean branch of `profile_session` `finally`, `_backup('after-clean-shutdown')` can raise
(an invalid account file, a full disk, a validation failure). So can the record
`unlink`/`fsync`. Either way the record stays at `phase: stopping`, and `owner` is this same,
still-running backend. Then:
- `begin()` refuses ("use Recover Session");
- `inspect` reports `owner_alive` → "owned by another active launcher" with
  `recoverable: False`;
- `recover` refuses ("original launcher is still active").

Play and Recover stay disabled until the launcher is restarted, and the message is wrong.

**Fix:** treat the owner as alive only while it actually has an **active session worker**. For
example, the backend passes `owner_active=lambda: self.worker and self.worker.is_alive()` when
the owner pid equals `os.getpid()`. Or, in an outer `try` around the post-stop branch, set
`phase = 'unverified'` (best effort) whenever anything after `stop()` fails.

### 2. Medium: restoring a backup while a record exists strands the profile
`restore` and `restore_profile` (`profiles.py`) don't check for `session.json`. After a crash,
the user can pick **Restore Backup**, which is enabled whenever `!running`, instead of
**Recover**. The restore switches `generation`. After that, `read()` raises "Session record does
not match this world" (`session_recovery.py:52-56`):
- `inspect` → `recoverable: False` and "Session recovery unavailable";
- `begin()` raises on every Start.

The profile can't be used from the launcher any more.

**Fix:** make `restore`, and recovery-restore of a damaged manifest, refuse while a session
record exists ("Recover the earlier session first"). Also add an explicit, logged **"Archive
stale session record"** path, which runs under the profile lock and only when `candidates()`
finds no live verified process. It renames the record to `session.<id>.stale.json` instead of
deleting it.

### 3. Medium (fragile): the argv jar check compares a resolved path with an unresolved one
`begin()` records `str(server_jar.resolve())`, but `Popen` passes `str(server_jar)` unchanged.
The two are equal only while no directory on the jar path is a symlink. `ROOT` is resolved,
but `upstream/game-server`, `build/` or `libs/` could be a symlink in another checkout layout.
In that case `verified()` is always false: `inspect` says "identity could not be verified", and
recovery is permanently unavailable for live orphans (fail-closed, but the user is stuck).

The same risk applies, more weakly, to `storage.players.path`. The environment uses
`profile.state.resolve()`, while `verified()` builds `profile.state/'saves'` without resolving.

**Fix:** store the exact argv string handed to `Popen` (and the exact environment value), or
resolve both sides before comparing.

### 4. Low: failed startups force the Recover flow
Any non-clean end with `server is not None` sets `phase = 'unverified'`. That includes the
server exiting during startup (port conflict, load error), when `ready` is false. The next Start
is then refused until Recover runs. That's safe, but it's friction for errors where no player
could have logged in.

**Optional:** when `not ready` and the server's exit was observed by this backend (`server.poll()
is not None`), remove the record instead. The before-launch backup already exists, and logins
attach only after readiness.

### 5. Low: the launcher's own running world is labelled "Earlier session"
While this launcher is playing a profile, `list` → `inspect` finds the record with the owner
alive, so the row shows "• Earlier session" and "World is owned by another active launcher."
**Fix:** suppress `recovery` for the profile of this backend's own active worker, or word the
owner-is-self case as "running in this launcher".

### 6. Low: `list` does a lot of /proc work when there's an orphan
For each profile with an orphaned record, every `list` call scans all of `/proc`, reading
environ, cmdline and fd for every same-uid process (`candidates`). The launcher polls
regularly, so with several stale records this costs real I/O. **Fix:** cache `inspect` results
for a few seconds, or scan only on demand (Recover) and show "earlier session needs recovery"
from the record alone.

### 7. Low: the profile lock after recovery doesn't wait
`recover` takes `profile.lock()` (non-blocking) right after the pidfds report exit. Kernel file
release runs before the pidfd becomes readable, so this normally works. But any other holder of
an inherited description, such as a child the JVM spawned, makes it fail immediately with the
generic "running" error, after the world was already stopped. **Fix:** retry with a short bounded
wait and a specific message ("owned processes closed; waiting for remaining lock holders").

### 8. Low: the keyboard opens automatically on focus
`focusGained` → `activate()` means navigating with the D-pad onto a text field immediately takes
over the D-pad. Mouse and keyboard users also see the grid. This works (B leaves, LB/RB moves
between fields), but it's surprising. **Optional:** activate only with A (that branch already
exists), and keep `focusGained` only for the first field when the dialog opens.

### 9. Low: labels accept control characters typed on a desktop keyboard
`LAUNCHER_LABEL` skips character checks, and the backend only strips the label and checks its
length. Pasting a tab or newline can store a multi-line label. **Fix:** reject `Character.isISOControl`
in `valid` for labels.

## Limits
- I didn't run the tests. The orphan, wrong-environment, live-owner, suspended, missing-PID,
  cancel and parallel-lock cases are listed in `test_session_recovery.py` but weren't checked
  here.
- The `fdinfo` `FLOCK` format, pidfd support and `/proc/<pid>/environ` access under hardened
  ptrace settings depend on the kernel. Recovery fails closed when they're missing.
- I didn't look at Settings/menu/selection priority beyond the `EntryControls` change, which
  leaves native key sets and types unchanged. No gameplay, controller hardware or Steam Deck
  acceptance is claimed.
