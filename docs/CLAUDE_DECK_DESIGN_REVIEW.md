# Steam Deck test deployment tooling: static review

This was a bounded **static** review. I made no source edits and ran no builds, tests, game,
probes or processes. I didn't use SSH, the network or Git commands, and I opened no saves, cache
or credentials. I only listed the names under `upstream/*/.git/refs` and the object sizes, without
reading their contents.

I read:
- `docs/DECK_SPRINT_TASKS.md`
- `scripts/deck-launch.sh`, `deck_export.py`, `deck_runtime.py`, `native_metrics.py`
- `scripts/smoke_profile.py` and `smoke-launcher.py` (including the working-tree diff)
- `scripts/harness/NativeControllerProbe.java`, `NativeLauncherProbe.java`, `NativeSessionSmoke.java`
- the `NativeAdventureProbe.java` diff
- for context only: `launcher.sh`, `local_dev.py` (pins and build stamp), `session_recovery.identity`
  and the `SdlGamepad` initialization

## Verdict
**No blockers.** There are two **medium** findings:
1. The snapshot's copied `.git` metadata gets around the tracked-file privacy filter, and it also
   makes later verification fragile.
2. In `--desktop` mode, the evidence screenshots and synthetic input share the real Deck screen,
   pointer and controller.

Everything else is low. The held-A fix in the launcher probe is sound for the race you
described.

## Verified (no issue)
- **What gets exported.**
  - Both the root and upstream file lists come from `git ls-files` (plus the files the patches
    add, plus a fixed, named list of this sprint's new tooling). Untracked or ignored files
    therefore can't leak in.
  - These are excluded: `upstream/` and `.runtime/` (from the root list), `config/local.env`, and
    from upstream the `data/{saves,errors,.temp,cache,exchange}` paths.
  - Any path that is absolute or contains `..` is rejected.
  - A source file that is a symlink is refused.
  - Every pin is checked against `local_dev.PINNED` before copying.
  - The jars are copied under the shared build lock, after `verify_build_stamp`.
  - A symlink in either JDK that points outside the JDK is refused.
  - Profiles, session logs and the launcher's settings all live under `.runtime/`, so they are
    never exported.
- **`deck_runtime.verify`.**
  - Each path listed in the manifest is checked: it must be relative with no `..`, and after
    `resolve()` it must stay inside the snapshot root, which also catches a directory that is a
    symlink.
  - A file must not be a symlink, and its size and SHA-256 must match the manifest.
  - A link must have exactly the recorded target.
  - The manifest pins must equal `local_dev.PINNED`.
- **`configure`.**
  - It refuses if a config file or symlink already exists, and writes with `open('x')`.
  - Paths are quoted with `shlex.quote`.
  - It writes only the two Java paths, then sets mode `0600`.
- **Process ownership.**
  - **`--desktop`:** both smoke scripts require an explicit `DISPLAY`, never start a second
    display, and never stop the user's one.
  - **Default mode:** they use the owned `Xvfb -displayfd ... -nolisten tcp` (now also in
    `smoke_profile`). Cleanup sends terminate, then kill only that owned `Popen`.
  - `NativeMetrics` reads only `/proc` for the children it was given. It rechecks pid and start
    time before and after each read, so a reused pid can't be attributed to the game.
    `identity()` can't fail for a child that was just started and not yet reaped (a zombie still
    has its `/proc` entry), so the `Popen` wrapper can't lose a child's handle.
- **Measurement fields.**
  - `cpu_ticks` uses fields 14 and 15 of `stat` (utime and stime; indexes 11 and 12 after the
    `)` split), which is correct.
  - A missing sensor is left out rather than reported as zero.
  - The method text says that charging power isn't evidence of battery life.
  - The labels for the environment and the display match the mode. Neither claims anything about
    the GPU, Gaming Mode or the physical controller.
- **Launcher held-A fix** (`NativeLauncherProbe.java:34`). One EDT callback does all of this:
  1. asserts the label is empty;
  2. calls `activate(label)`, which re-arms the keyboard;
  3. sends a held-A update;
  4. asserts nothing was typed;
  5. calls `press()`.

  The live launcher timer also runs on the EDT, so it can't run in between those steps. Between
  later callbacks the timer can only feed the real neutral state. `press()` always starts with
  its own neutral update, so a neutral poll in between can't remove the A edge or create one.
- **`NativeControllerProbe`** only polls. It sends no input, rumble or writes, and it states that
  physical mapping, gameplay and Gaming Mode aren't covered.
- **Screenshot capture is now limited to the canvas or dialog** (`NativeSessionSmoke:35-36`,
  `NativeAdventureProbe` `capture`, `NativeLauncherProbe:38`). This is better for privacy than the
  earlier full-screen capture.

## Findings

### 1. Medium: the copied `.git` gets around the export filter and makes verification fragile
`deck_export.py:62-70` copies `HEAD`, `shallow`, `packed-refs`, `index`, **all of `objects/`**
and **all of `refs/`** for each upstream repository.

**Privacy.**
- `objects/` holds every object in the store, including unreachable blobs left over from any
  local `git add` or `git stash`. A save, an exchange file or a token that was ever staged in
  `upstream/game-server` (for example `data/saves/*.toml` while debugging) ends up in the
  snapshot, even though the `MUTABLE` filter excludes it from the working tree.
- `refs/` would carry a future `refs/stash`.
- Today the refs are clean (`heads/main`, `remotes/origin/HEAD`) and the stores are small (1.7,
  5.9 and 3.1 MB). So this is a latent hole, not a current leak. I didn't check whether
  unreachable objects exist.

**Fragile verification.**
- `index` (and the whole `.git` tree) is part of the hashed manifest. Any `git status` or `diff`
  on the Deck refreshes the stat data in `.git/index`. The next `deck_runtime.py` then fails with
  "Snapshot file mismatch", even though nothing that matters changed.
- An `objects/info/alternates` file, if one exists, would point to an absolute path on the host.

**Testable trigger:** stage, then unstage, a dummy file under `upstream/game-server/data/saves/`.
Export, then search the snapshot's `objects` with
`git cat-file --batch-all-objects --batch-check`, and the blob is there. Separately, run
`git -C <snapshot>/upstream/game-server status`, then `deck_runtime.py`, and it fails.

**Smallest fix:**
- Don't copy `index` or `refs/`.
- Write the pinned commit into `HEAD` (or `refs/heads/main`) yourself.
- Replace the raw copy of `objects/` with objects that are reachable from the pin only. For
  example, `git -C repo pack-objects --revs` with `<pin>` as input, written into the snapshot's
  `objects/pack`. Or skip the `.git` metadata entirely and record the pin in the manifest, which
  already holds `pins`.
- Either way, keep `.git/` out of the hashed manifest entries, or hash only the pack.

### 2. Medium (`--desktop` on the Deck): evidence and input share the real screen, pointer and controller
In `--desktop` mode, `smoke_profile.py` and `smoke-launcher.py` run against the user's live
desktop.

**Privacy of the evidence.**
- `Robot.createScreenCapture(canvas or dialog bounds)` captures whatever is drawn **on top of**
  that rectangle: notifications, the Steam overlay, a keyboard popup, other windows.
- Those PNGs (`marker.png`, the adventure captures, `launcher-name-entry.png`) are written as
  "private evidence" and may later be copied into the combined reports.

**Input interaction.**
- In Steam's desktop mode the controller is still in lizard mode: the trackpads and sticks drive
  the real pointer and keys.
- The native mouse logout in `NativeAdventureProbe` uses the real pointer, and the client's
  real SDL loop is live.
- Anyone touching the Deck, or just resting a thumb on a trackpad, can move the pointer or focus
  during a probe step.
- For the launcher probe, a real **held** button while the probe runs is fed to the keyboard by
  the live timer between callbacks.

As far as I can see, these mostly cause **false failures** (exact-text asserts like
`equals("a")`, panel or step checks), not false passes. That keeps the evidence honest, but
still not proof that physical input works.

**Fix:**
- In `--desktop` mode, write a "hands off the Deck" precondition into the summary.
- Record whether any non-neutral controller state was seen during the run. The launcher probe
  could sample the live `GamepadState` per callback; the session smoke could use the client's
  last polled state. If one was seen, mark the result invalid.
- Mark `--desktop` screenshots as "may include desktop overlays; review before publishing", or
  keep them out of the combined report unless a person has checked them.

### 3. Low: `verify` accepts extra files and the manifest isn't authenticated
`deck_runtime.verify` checks only the paths the manifest lists.
- An extra file, for example a `config/local.env` pointing somewhere else, saves copied in by
  hand, or a stray JDK, still gives "Verified private snapshot files: N".
- The SHA-256 values check against corruption, not against tampering: the manifest travels with
  the files and isn't signed.

**Fix:**
- Make the wording say "listed files match".
- Optionally report unlisted files outside `.runtime/{profiles,…}`, `config/local.env` and
  `.git`.
- Record the manifest's own hash on the host so the owner can compare it by eye.

### 4. Low: `deck-launch.sh` loses to an existing `config/local.env`
`deck-launch.sh` exports the snapshot JDK paths, but `launcher.sh` then `source`s
`config/local.env`, and the plain assignments there override what was exported. `configure`
refuses to replace an existing file, so an older `local.env` silently decides which JVM runs.
`doctor` still checks the Java versions, so the effect is only on which JVM gets measured.
**Fix:** apply the exports in `deck-launch.sh` *after* sourcing `local.env`, or have
`deck-launch` run `verify` and refuse when `local.env` names other paths.

### 5. Low: export robustness
- **Partial snapshot left behind.** The destination is created before the lock and the pin
  checks (`deck_export.py:37-38`). A failure leaves a snapshot with no manifest. `verify` fails
  closed on it, but nothing removes it or marks it incomplete. **Fix:** write into a
  `*.partial` directory and rename it at the end.
- **The cache copy follows links.** `shutil.copytree(.../data/cache)` (`:73`) uses the default
  `symlinks=False`, so a symlink inside the cache is **followed**, and outside content is copied
  silently. **Fix:** reuse the JDK check (no symlink resolving outside the tree), or pass
  `symlinks=True` and let the manifest record the link.
- **Parent-directory symlinks.** `copy_file` checks only the final path component for a symlink.
  A tracked directory that is a symlink isn't caught. **Fix:** check
  `source.resolve().is_relative_to(repo)`.

### 6. Low: what the measurements can and can't support
- **Silent truncation.** `NativeMetrics.collect` stops after 1200 samples (10 minutes) without
  saying so. **Fix:** add `"truncated": true` and the sample count to `finish()`.
- **Race on timeout.** If `join(3)` times out (a sysfs read hangs), `finish()` returns the list
  while the worker can still append to it. **Fix:** return a copy taken under the lock, and record
  `worker_alive`.
- **Host-wide readings.** `battery`, `temperatures` and `gpu_busy_percent` are host-wide, not
  per-process. Under Xvfb the GPU is idle by design. The method text should say "host-wide" and
  "software-rendered under Xvfb", so a quiet GPU isn't read as efficiency.
- **No phase markers.** Samples cover startup, loading, login, play and save together, so an
  average mixes JVM and cache loading with steady-state play. **Fix:** record the
  ready/in-game/stopping times (the stage callback already gets them), so later analysis can
  separate the phases.

### 7. Low: `NativeControllerProbe` coverage and wording
- **Wording.** "without changing Steam controller configuration" is true for files. But SDL2's
  HIDAPI Steam Deck driver, when it is the one claiming the device, can disable lizard mode
  temporarily while it has the device open. I didn't verify which driver claims it here, because
  that depends on the SDL build and whether Steam's virtual pad is present. Say "no configuration
  files written" rather than imply there is no effect on the device.
- **Duplicate count.** `joysticks` may count Steam's virtual pad and the hidraw Deck device
  separately. **Fix:** report each controller's name, GUID and whether it is a game controller,
  so "Steam Deck Controller detected" is attributable.

## Limits
- Static only. I didn't run the export, `verify`, the doctor, the probes or `test_deck_runtime.py`.
  The Deck doctor pass and the SDL detection result are as you reported them.
- I didn't inspect the contents of the Git object stores (no Git use). Finding 1 is about what
  the code would copy, not a leak I observed.
- The lizard-mode and Steam Input behaviour in findings 2 and 7 come from general knowledge of
  SteamOS and SDL. I didn't check them on this device.
- No physical controller, ergonomics, Gaming Mode, GPU, suspend/resume or gameplay acceptance is
  claimed or implied.

## Codex response to static review

The exporter now packs only pin-reachable Git objects with a detached pinned HEAD and a new index; it copies no stash refs, remote config, alternates, hooks, reflogs or dangling objects. A temporary-repository regression stages/unstages a dummy private save and proves its blob is absent in the snapshot. Mutable index stat data is excluded from manifest hashing. Source-parent escapes and cache symlinks are refused; incomplete exports are marked `.partial` until their manifest is complete. Deck launch directly invokes the snapshot Java path, avoiding a second config override. Metrics now record lifecycle phases, bounded sample count/truncation, worker liveness and host-wide sensor scope. Desktop summaries record hands-off/awake and private screenshot caveats. Device input is tested separately; no physical mapping acceptance is inferred. Real native core New/Continue/save/cancel passes; the broader mouse-logout probe is still being diagnosed.
