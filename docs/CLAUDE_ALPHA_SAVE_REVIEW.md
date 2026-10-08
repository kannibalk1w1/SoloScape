# Alpha save and isolation foundation: correctness review

Scope: `scripts/profiles.py`, `scripts/profile_session.py`, `scripts/launcher_backend.py`, and
`patches/server/0004-profile-save-durability-and-loopback.patch`. I also read
`local_dev.stop` and the pinned `PlayerSave` field types where the review depended on them.
This was static only: no runs, no real saves, cache or `login.json`, and no edits.

## Verdict

**No blocking findings for save integrity.**
- Account TOMLs are now written atomically.
- The profile lock covers the whole session, including the backups before launch and after a
  clean shutdown.
- Stops use SIGTERM only, never SIGKILL.
- A restore switches one atomic manifest pointer and keeps the old generation.
- Isolation keys cover every mutable `storage.*` path I found in the earlier audit.

The two medium findings are Grand Exchange state that is still written non-atomically, and a
stdio protocol desync after an oversized request.

## What I checked and found correct

**Server patch**
- `Config.atomicFileWriter` writes to a temp file in the same directory (`.save-*.tmp`, so
  `names()` ignores it), then fsyncs, does an `ATOMIC_MOVE`, and fsyncs the directory. It
  deletes the temp file in `finally`.
- Only `PlayerSave.save` uses it.
- `Settings.load` now re-applies `System.getenv()` on every load, which closes the
  reload-override trap.
- The saves directory is created with `mkdirs()`, checked.
- The game server binds to `network.bind`, default `127.0.0.1`.
- `GameServer.stop` is idempotent and releases the selector and dispatcher after a failed bind.

**Profile environment**
- `profile_session.owned_environment` removes every inherited environment variable with a dot
  in its name (`profile_session.py:18`).
- `Profile.environment` sets absolute paths for saves, logs, errors, `data.modified`,
  `wildcards` and `caching.path`. Grand Exchange data and reports follow the saves directory.
- It also sets `development.admin.name=''`, which no account name can match
  (`Rights.kt:22` compares for equality), and turns bots and the web server off.

**Lock and lifecycle**
- `lock()` uses `flock(LOCK_EX | LOCK_NB)` on its own file descriptor each time, so a second
  thread or process gets "running" (`profiles.py:144-153`).
- `run()` holds the lock from the pre-launch backup until the post-stop backup
  (`profile_session.py:31-101`).
- `local_dev.stop` waits forever after SIGTERM and never sends SIGKILL.
- A post-stop backup is taken only when the server reached ready, exited 0, 143 or −15, and
  nothing failed (`profile_session.py:96`).

**Backup and restore**
- Backups are written to a temp file, validated by re-reading, fsynced and renamed, then the
  directory is fsynced.
- A restore writes a new `states/<uuid>` with `open('xb')` and fsyncs, then switches
  `profile.json` atomically. It only removes the new directory if the manifest switch never
  happened (`profiles.py:315-320`).
- Path traversal, symlinks, duplicate entries, size, checksums, profile and account are all
  checked.
- `validate_save` expects integer arrays, which matches `PlayerSave` (`experience`, `levels`,
  `looks` and `colours` are `IntArray`, and items write `amount` only when it is > 1).

## Findings (ranked)

### 1. Medium: Grand Exchange, claims, price history and reports are still written non-atomically
The patch switches only `PlayerSave.save`. `FileStorage.saveOffers`, `saveClaims`,
`savePriceHistory` and `saveReport` still use `Config.fileWriter`, which truncates the file
first. These run from autosave and from `worldDespawn` → `exchange.save()`.

A crash, a full disk or a power loss during those writes can truncate files under
`saves/grand_exchange/`. At the next start, `GrandExchange` is a `createdAtStart` singleton
that loads them, so the world may refuse to start until the player restores a backup. The
pre-launch and post-stop backups make this recoverable, but it is the remaining gap in the
"atomic save" goal.

**Fix:** switch those `Config.fileWriter(file)` calls in `FileStorage.kt` (lines 99, 123, 131,
215 and 298 in the pinned source) to `Config.atomicFileWriter`. Add a test that a failing
writer keeps the previous `claimable_offers.toml`.

### 2. Medium: stdio protocol desync after an oversized request
`serve()` reads `readline(MAX_REQUEST + 1)` (`launcher_backend.py:208`). For a line longer than
16 KB, the first chunk is rejected, but **the rest of that same line is read as further
"requests"**. Each produces another `{"id": null, "ok": false}` response. A GUI that pairs one
response with each request it sends falls out of step.

**Fix:** after rejecting an oversized chunk, keep reading and discarding with `readline()`
until a chunk ends in `\n` or input ends. Then send exactly one error response.

### 3. Low/medium: the backend loop stops on unexpected exception types
`serve()` catches only `ValueError`, `RuntimeError`, `OSError`, `KeyError` and `TypeError`
(`:220`). Any other exception from `dispatch` escapes the loop, for example
`AttributeError` from a request field of an unexpected JSON type, `RecursionError` from deeply
nested JSON, or `zipfile.LargeZipFile`. That runs `backend.close()` and ends the protocol.
A running world still gets a graceful save, because `close()` cancels and joins the worker.
The GUI loses its backend, though.

**Fix:** catch `Exception` for the response path, keeping `BaseException` for interrupts, and
log the traceback to stderr.

### 4. Low/medium (future functionality): imported characters can't log in yet
`import_character` creates the profile with `password=''` (`profiles.py:368`) and copies a save
whose `passwordHash` is unknown. Nothing in this batch reconciles `login.json` with an
imported hash. That needs future work: `SOLOSCAPE_AUTH_FILE` is passed through, but no
consumer exists in these files.

Also, if the copy or backup fails after `create()`, an orphaned profile stays listed.

**Fix:** keep import disabled in the GUI until the authentication bridge exists. Wrap
`import_character` in a try that removes the new profile directory on failure.

### 5. Low: no backup or generation retention
Every launch creates two zips (before launch and after a clean shutdown), each up to 512 MB.
`previous_generations` keeps growing, and old `states/<uuid>` directories are never pruned.
Over time this fills the disk, and a full disk is exactly the failure mode that makes saves
fragile. **Fix:** keep the newest N automatic backups plus all manual ones, and prune
generations older than the newest restorable backup that references them. This is future
functionality, but it should land before the alpha ships.

### 6. Low: one corrupt account file blocks every backup
`_backup` runs `validate_save` on every top-level `saves/*.toml` (`profiles.py:221-222`). If any
save is invalid, the backup fails, and so the *launch* fails (`profile_session.py:36`), at the
moment the user most needs a recovery snapshot. **Fix:** allow a clearly marked "raw/unverified"
backup that `restore` refuses unless the user confirms it, or skip the strict check for
accounts other than the profile's own.

### 7. Low: server temp files get into backups
After a crash, `.save-*.tmp` left by `atomicFileWriter` sits in `saves/`. `_files()` copies
it into the backup and `restore` writes it back. It's harmless, because `names()` ignores it,
but it's clutter and could be large. **Fix:** skip names starting with `.save-` and ending in
`.tmp` in `_files()`.

### 8. Low: a hung server blocks the GUI from closing
`local_dev.stop` waits forever after SIGTERM, which is correct, and `Backend.close()` then
joins the worker forever. If the JVM's shutdown hook hangs, the launcher can't exit, and the
status stays at "saving". **Fix (UX only):** after about 60 s, update the status with
"still saving; PID n; logs at …" so the GUI can tell the user. Keep never killing the server.

### 9. Note: cancelling during startup sends SIGTERM to a half-loaded world
If the user cancels before "Void loaded", the server gets SIGTERM while it is still loading,
and its shutdown hook may run `worldDespawn` → `exchange.save()`. I did not trace whether a
partly initialised `GrandExchange` could write empty state. No post-stop backup runs
(`ready` is false), and the pre-launch backup exists. **Suggestion:** test a cancel during
startup against a profile that has Grand Exchange offers before trusting it.

## Limits
- I didn't run anything or test against real saves. The client-side authentication consumer
  (`SOLOSCAPE_AUTH_FILE`) and the GUI integration are still in progress and not reviewed.
- I did not trace `Despawn.world()` in full.
- Directory fsync and `ATOMIC_MOVE` are fine on Linux filesystems. They would fail on Windows,
  where opening a directory fails, but that platform isn't targeted.
