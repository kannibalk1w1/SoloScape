# Bootstrap validation — 2026-10-08

Passed:

- Installed official Temurin **21.0.12.1+1** and **8u504-b01** into ignored
  `.runtime/jdks/`, with downloaded archives checked against official API SHA-256
  metadata. Configured `config/local.env`; no system Java changes.
- `setup-java.sh` passes ShellCheck and an idempotent repeat preserves the existing
  configuration and successfully invokes both installed runtimes.
- Both pinned Gradle distributions download and run. The unmodified selected
  client completes `:client:shadowJar`; its jar is
  `upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar`.
- The unmodified server completes `:game:shadowJar`; its jar is
  `upstream/game-server/game/build/libs/void-server-dev.jar`.
  Starting that jar from the correct server cwd loads properties then fails at
  the expected missing `data/cache/main_file_cache.dat2`. No game world starts.
  Upstream emits compiler/deprecation warnings; no build errors. Compiling test
  sources as a build dependency is not evidence that upstream tests were run.
- ShellCheck for `scripts/doctor.sh` and `scripts/dev-run.sh`.
- Python compilation for launcher and test harness.
- Four simulated-process lifecycle tests: wait for world readiness and explicitly
  use localhost; stop server after client exit; never launch client after server
  startup failure; gracefully stop server after readiness timeout; interrupt
  cleanup stops both children. The first test covers readiness and client exit.
- All three upstream working trees remain clean at the documented commit pins.
- Host doctor port probe: port 43594 available. The restricted execution sandbox
  itself denies local socket access; doctor reports that as an environment error.
- `dev-run.sh --no-build` fails before creating game processes when prerequisites
  are missing.

Blocked/unverified:

- No compatible cache was found in this workspace, Downloads or other checked
  Orca project directories. Doctor passes both Java checks and the host port
  check, and reports two missing cache files.
- Real rendering, login and persistence restart have not run. Simulator shutdown
  markers are not proof of real saves.
- `/proc/bus/input/devices` shows keyboard, mouse/touchpad and virtual input
  devices; no Steam Deck or identifiable physical gamepad. A virtual fake mouse
  exposes `js0`, demonstrating that a joystick node alone does not prove a pad.
- No controller provider or controller feature is implemented or validated.
- No exhaustive dependency/bundled-native licence audit or distributable package.

Reproduce the implemented checks:

```bash
shellcheck scripts/doctor.sh scripts/dev-run.sh
python3 -m py_compile scripts/local_dev.py scripts/test_local_dev.py
python3 scripts/test_local_dev.py
./scripts/doctor.sh
```

Next actual acceptance test requires user-supplied compatible cache.
Follow `STEAM_DECK_TEST_CHECKLIST.md` for the real game roundtrip.
