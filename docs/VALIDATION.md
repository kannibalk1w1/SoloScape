# Bootstrap validation — 2026-10-08

Passed:

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

- JDK 21 and JDK 8 are absent. No cache was found in this workspace or Downloads;
  no Java was found in the checked standard JDK locations.
- Real Gradle resolution, game compilation, rendering, login and persistence
  restart have not run. Simulator shutdown markers are not proof of real saves.
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

Next actual acceptance test requires user-supplied compatible cache plus JDKs.
Follow `STEAM_DECK_TEST_CHECKLIST.md` for the real game roundtrip.
