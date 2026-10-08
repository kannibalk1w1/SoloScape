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
  With the authorized upstream cache installed, starting that jar from the
  correct server cwd reaches `Void loaded in 3561ms`. SIGTERM exits with code
  143 after save hooks log successful writes of zero accounts and empty exchange
  state. No real character was created, so persistence is still unverified.
  Upstream emits compiler/deprecation warnings; no build errors. Compiling test
  sources as a build dependency is not evidence that upstream tests were run.
- ShellCheck for `scripts/doctor.sh` and `scripts/dev-run.sh`.
- Python compilation for launcher and test harness.
- Four simulated-process lifecycle tests: wait for world readiness and explicitly
  use localhost; stop server after client exit; never launch client after server
  startup failure; gracefully stop server after readiness timeout; interrupt
  cleanup stops both children. The first test covers readiness and client exit.
- Initial baseline inspection/build used clean upstream working trees at the
  documented pins. The client now intentionally has the tracked controller patch;
  the server and plain 634-client remain unchanged.
- Host doctor port probe: port 43594 available. The restricted execution sandbox
  itself denies local socket access; doctor reports that as an environment error.
- `dev-run.sh --no-build` fails before creating game processes when prerequisites
  are missing.
- Downloaded and extracted the latest full cache from the upstream-linked MEGA
  folder with user authorization; MEGA integrity check and 7-Zip extraction pass.
  Host doctor now reports **zero errors**. Cache/archive are ignored by Git.
  Log: `.runtime/cache-smoke.log`. One first-tick timing warning occurred during
  startup; sustained tick performance has not been measured.

Blocked/unverified:

- Real rendering, login and persistence restart have not run. Simulator shutdown
  markers are not proof of real saves.
- `/proc/bus/input/devices` shows keyboard, mouse/touchpad and virtual input
  devices; no Steam Deck or identifiable physical gamepad. A virtual fake mouse
  exposes `js0`, demonstrating that a joystick node alone does not prove a pad.
- Controller detection/right-stick camera implementation builds and passes nine
  tests, including real native SDL virtual-controller polling/hotplug. Physical
  controller and Deck acceptance remain pending; see `CONTROLLER_TESTING.md`.
- No exhaustive dependency/bundled-native licence audit or distributable package.

Reproduce the implemented checks:

```bash
shellcheck scripts/doctor.sh scripts/dev-run.sh
python3 -m py_compile scripts/local_dev.py scripts/test_local_dev.py
python3 scripts/test_local_dev.py
./scripts/doctor.sh
```

Next acceptance test is client rendering, local login and persisted character
restart. Follow `STEAM_DECK_TEST_CHECKLIST.md` for the real game roundtrip.

## Movement and A interaction build (2026-10-08)

- User confirmed physical controller camera panning works.
- Left-stick walking and nearby NPC/object A actions built as patch 0002.
- Twenty client tests pass with zero skips/errors, including native SDL axes/A
  and the actual revision-634 pathfinder. Shadow jar rebuilt successfully.
- Three patch-stack tests pass; fresh source reproduction and camera-build upgrade
  checked independently. Local conflicts are detected before changing source.
- Physical movement/interaction, focus recovery and Steam Deck acceptance remain
  pending. See `CONTROLLER_TESTING.md` for the gameplay checklist.
