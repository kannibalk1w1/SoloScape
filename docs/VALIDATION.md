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

## Movement tile overlay (2026-10-08)

- Patch 0003 adds enabled-by-default ground markers for the actual controller
  destination and current player tile, using existing perspective/overlay APIs.
- Client Shadow jar rebuilt; all 20 existing client tests pass without skips.
- Existing-build upgrade and fresh patch-stack reproduction match all 23 patched
  files; sequential reverse application succeeds and application is idempotent.
- In-game visual verification remains pending.

## Inventory and dialogue controls (2026-10-08)

- Patch 0004 adds Y inventory focus, D-pad grid navigation, A default actions,
  X action lists, B back, and automatic dialogue focus with A/D-pad/B controls.
- Captured bounds come from actually rendered native widgets. Native permission
  flags/action IDs match the existing 634 menu pipeline. Cached widgets are
  rejected if their ancestors hide, their interface closes, or item data changes.
- Native tab IDs and dialogue groups match the pinned server interface definitions.
  Dialogue B uses the existing same-tile Walk action; the Movement handler's
  interface/suspension cancellation was checked in source.
- All 31 client tests pass with zero skips/errors; Shadow jar rebuilt successfully.
  Eleven new tests cover UI modes, edges/repeat, context changes, delayed redraw,
  actual native permission bits, bounds, ancestors and stale-widget rejection.
- Existing-build upgrade and fresh patch-stack reproduction match all 30 patched
  files; reverse application and repeated application succeed.
- User confirmed movement markers work. Inventory/dialogue gameplay, tab opening,
  fixed/resized slot placement and Steam Deck acceptance remain pending.

## Walking, aiming and interaction usability (2026-10-08)

- Patch 0005 adds one-to-three-tile walks from the physical player tile, LT aim-only,
  LB/RB target cycling, stable focus during camera panning and gold scene labels.
- A preserves entity identity across NPC movement and revalidates before dispatch.
  The held walking direction pauses after interaction; a new direction or neutral
  resumes movement after A is released.
- All 38 client tests pass with zero failures/errors/skips; Shadow jar rebuilt.
  Three patch-stack tests and four launcher tests also pass.
- Upgrade, sequential reverse and fresh patch-stack reproduction match all 31
  patched files exactly. Repeated application succeeds.
- User reported controller gameplay works but walking/aiming/interaction is hard.
  This usability pass still needs their in-game feel and visual placement check.

## Optional direct movement (2026-10-08)

- Client patch 0006 adds **Direct movement**, default off; changing it stops the
  previous mode and requires neutral before resuming. Legacy walking is preserved.
- Server patch 0001 decodes directional opcode 85 and takes local, collision-checked
  steps on existing 600ms ticks. Stop clears only direct movement. Freshness timeout
  is 750ms, checked each tick. No absolute positions are accepted from the client.
- Gentle tilt walks; full tilt requests running with normal energy/equipment limits
  while preserving the run-toggle preference. Native menu actions stop direct input
  and require neutral before the stick takes over again.
- 47 client, 246 network and 56 selected engine tests pass with zero failures,
  errors or skips. Both Shadow jars rebuilt and new class entries verified.
- Client/server patch reproduction matches 36/9 files exactly. Fresh, upgrade,
  reverse and idempotent application pass; three patch-helper and four launcher
  tests, Python compilation and server patch-script ShellCheck pass.
- First server test run downloaded missing upstream JUnit dependencies. No cache,
  player saves or currently running game processes were changed.
- In-game direct movement, stop latency, interaction ownership, region edges and
  Steam Deck acceptance require a full client/server restart and physical testing.

## World menus, loot and cancellation (2026-10-08)

- Client patch 0007 adds X native action lists, D-pad/A/B list input, all visible
  loot-pile entries and A Take targeting. Entity/option/quantity freshness is checked.
- Equal-score target cycling now uses deterministic tie-breakers; a native five-item
  pile test exposed and verifies the fix for alternating between only two entries.
- Server patch 0002 adds position-free cancel opcode 86 for normal approaches and
  interactions, respecting busy/forced modes. Direct stop is sent before cancel.
- 58 client, 247 network and 59 selected engine tests pass with zero failures,
  errors or skips. Both Shadow jars rebuild; cancel classes are present in the server jar.
- Fresh, upgrade, reverse and idempotent source reproduction matches 37 client
  and 14 server files. Three patch-helper and four launcher tests also pass.
- Server UI close is mocked in cancellation unit tests; actual in-game cancellation,
  menu layout, loot pickup and inventory/dialogue coexistence remain for acceptance.
- User confirmed optional direct movement feels good. No current game processes,
  player saves or game cache were changed during this build.
- `ROADMAP.md` and `PROJECT_HANDOFF.md` capture the proposed next work and current
  status for review/discussion. They do not mark unplayed features as accepted.


## Claude review fixes (2026-10-08)

- Preserved Claude's independent pre-fix findings in `CLAUDE_REVIEW.md`.
- Client patch 0008 fixes M2/M3 with per-scan geometry reachability caching, keeping
  the eight-geometry budget while allowing every item on an evaluated pile.
- Server patch 0003 fixes H1: B runs walk cleanup once after cancelling the old
  mode, preserving an exit route installed by that cleanup. Forced busy actions
  retain their callback.
- Regression tests pass for 12-item cycling both ways and wrap, a dense blocked
  pile beside reachable loot, cache expiry, morph-style cleanup, single execution,
  cleanup-created exit routes and forced-action preservation.
- Full client run: 61 cases (58 distinct methods), zero failures/errors; one SDL
  virtual-device case deliberately skipped. This batch did not rerun native SDL.
- Network: 247 cases; selected engine movement/decoder/cancel: 61 cases. Both
  have zero failures/errors/skips. Both Shadow jars rebuild and classes verified.
- Fresh/upgrade/reverse/idempotent patch reproduction matches all 37/14 affected
  files; real checkout patch helpers are idempotent. Seven root tooling tests pass.
- Current game processes, player saves and cache were not changed. Both processes
  need restarting for gameplay acceptance. The roadmap now includes extra review
  checks; capability negotiation, error recovery and idle UI cost remain proposals.
