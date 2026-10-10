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


## Home-tab radial and public repository preparation (2026-10-08)

- Client patch 0009 adds View/Select, a 16-slot tab wheel, analog/D-pad/bumper
  selection, A/B input, native availability checks and a config toggle.
- Seven state tests cover all sectors, confirmation once, held input, unavailable
  tabs, cancel/toggle, reset/dialogue blocking, wrap and angular hysteresis.
- Three native UI tests cover all fixed/resized IDs, hidden/replaced buttons,
  dialogue blocking and actual ordinary tab operation packet dispatch.
- Full client tests: 71 cases (68 distinct methods), zero failures/errors, one SDL
  virtual-device case deliberately skipped. Shadow jar builds successfully.
- Upgrade/fresh/reverse/idempotent reproduction matches all 41 client files.
  Seven root tooling tests pass. Server source/jar is unchanged by this prototype;
  latest server evidence remains 247 network plus 61 selected engine cases.
- Actual renderer previews inspected at 765×503 and 1280×800, using a plain
  background; no gameplay acceptance claimed. Current game and saves untouched.
- Public setup docs now explain the maintainer-linked cache source, verified
  archive, extraction path and client/server download distinction. Upstream README
  link was checked through GitHub's API. Public contribution policy preserves
  maintainer control; no original-material licence grant was inferred.


## Overnight reliability checkpoint (2026-10-08)

Client patch 0010 implements the reliability changes described in `MORNING_REPORT.md` and `PROTOCOL_EXTENSIONS.md`. Client test/build: 76 cases, zero failures/errors, one SDL skip. Root tooling: 11 cases pass. Fresh, upgrade, reverse and repeated patch application reproduce all 41 affected client files. Claude found no blockers; minor follow-ups were applied. Direct movement now requires both Direct movement and SoloScape server features settings. Automatic remote capability negotiation and physical gameplay acceptance remain pending.


## Completed overnight controller sprint (2026-10-08)

Implementation commits: `daf577c`, `40cc0a0`, `237e5be`, `bb1aca0`. Final client test/Shadow build passes: **100 cases, zero failures/errors, one SDL virtual-device skip**. Root tooling: **14 cases**, ShellCheck and Python compilation pass. Server source/jar was unchanged by this client sprint; existing server evidence remains **247 network + 61 selected engine** passing cases.

The complete modified trees match reproduced patches: **53 client / 14 server files**. Fresh application, upgrades, reverse application and repeated application pass; real patch helpers are idempotent. Whole-tree export verification additionally detects omitted tracked/new files and changed contents. Patch 0013 includes the entry observer, render-frame and selection hooks, completing the exported native paths.

Native widget/pane tests cover bank/shop grids, permissions, quantities, scroll bounds, item replacement, close retry and radial handoff. Entry checks cover native edit/Enter/Escape argument shapes, explicit one-shot bank search, hidden/replaced prompts and overflow. Selection tests cover source identity/permissions/quantity, re-selection tokens, inventory tab preservation, ineligible item targets and an actual native spell-on-NPC packet (opcode 61, source group/component, child/item and NPC fields matched to the pinned decoder).

Three bounded Claude reviews are retained; identified medium bank close/recovery and minor redraw/search/test improvements were fixed. Bank and keyboard overlays were inspected at 765×503 and 1280×800 on plain backgrounds. No real session was launched/stopped, no cache/saves changed and no physical acceptance or fresh native SDL run is claimed. See `MORNING_REPORT.md` for remaining checks.

## Second autonomous controller sprint — 2026-10-08

Patch `0014-quick-actions-production-and-controller-usability.patch` adds the separate eight-slot wheel, explicit native quick-action assignments, production amount presets and common modal screens, additional home-tab focus, server-authoritative attack/spell approach selection, auxiliary button settings, glyph labels, scaled overlays and the optional in-client guide.

Final client test/Shadow build: **121 cases, zero failures/errors, one SDL virtual-device skip**. The 21 additional cases exercise quick-slot assignment/serialization/type checks, potion family and dose selection, unavailable/cancel/timeout behavior, held-input guards, native smithing sibling packet dispatch, permission/hidden/replaced widgets, paired jewellery names, production recipe/amount separation, additional tabs and obstacle targets. Root tooling: **14 cases pass**. Complete patch reproduction matches **59 client / 14 server files**, including upgrades, fresh application, reversal and repeat application. Server code and its previously verified jar remain unchanged (247 network + 61 selected engine cases are existing evidence).

Actual Claude performed a bounded planning audit, implementation review and fix follow-up. Its medium finding about unspecified food/potion consumption is fixed: every quick slot starts empty. Bindings retain native type/operation; assigned potion families prefer their lowest dose. Partial-food ID changes deliberately fail closed. The follow-up reports no remaining blockers. Read the three `CLAUDE_SECOND_SPRINT_*.md` records for the review scope and remaining physical checks.

Quick-wheel and keyboard renderer previews were inspected at 765×503 and 1280×800, including 100% and 150% scaling. Published images are plain-background renderer artifacts, not game screenshots. No game process was started/stopped and no cache/player/save files were modified. Physical controller, production cache/CS2 op availability, native modal closing, real save persistence, Deck performance and suspend behavior remain unaccepted.

Second-sprint implementation `c8a7031` is pushed; [GitHub Tooling checks](https://github.com/kannibalk1w1/SoloScape/actions/runs/37832832337) pass. Public main was verified unchanged at `07e789b`. The local build stamp was updated only after final test/build and exact export verification; no processes were launched.

## Console alpha completion checkpoint

Client 139 cases (one optional SDL skip), root tooling 37, config 74, networking 249, selected engine 49 and one full isolated native progression route pass. Client/server shadow jars and complete patch stacks match across 78/28 source files. Private New→Continue verifies native rendered login, current-session capabilities, normal shutdown/save, field preservation and four verified backups while original mutable path fingerprints remain unchanged. Python compile, shellcheck and git whitespace checks pass. See MORNING_REPORT.md and ALPHA_SAVE_VALIDATION.md for scope and physical acceptance limits.


## Cohesive session checkpoint — 9 October 2026

Client: 151 cases, no failures/errors, one existing optional SDL skip. Root: 44 cases pass. Selected game: 11 pass (seven existing shops, prior alpha progression, combined quest/commerce/gather/production/bank/combat/save, transient shared stock and actual Lumbridge walking). Client/server shadow builds and full 87/31-file patch reproduction pass. Prior alpha config/network/engine results above are historical, not newly rerun.

Native isolated graphical New/Continue reaches rendered world and verified capabilities, preserves save/load fields and produces four completed-session backups. An observed cancellation before world readiness preserves every saved-world file. Original mutable paths' size/mtime fingerprints remain unchanged. Prepare refuses while that private session is live and succeeds afterward. New/Continue total-session times: 27.407/25.532 seconds (Xvfb/software, includes waits/shutdown; no FPS/latency claim). Python compilation, ShellCheck and whitespace checks pass.

Actual Claude static reviews and follow-up find no remaining blockers after child-parent ownership, native-label, build-lock and startup fixes. Physical controller/Deck, complete real-map quest travel and exhaustive startup cancellation remain unclaimed. See MORNING_REPORT.md, CONSOLE_SESSION_ACCEPTANCE.md and CLAUDE_SESSION_FOLLOWUP.md.


## 9 October controller-first adventure checkpoint

Latest: 172 client cases (zero failures/errors, one existing optional SDL skip), 47 root tooling/profile/lifecycle/socket cases and 18 selected game cases pass. Two strengthened actual-map save cases reran within the same selected slice. Matched shadow jars and stamp verify; complete exported stacks reproduce 98 client and 32 server files. See [native adventure validation](ADVENTURE_NATIVE_VALIDATION.md), [route audit](ADVENTURE_ROUTE_AUDIT.md), [task status](ADVENTURE_SPRINT_TASKS.md) and [combined report](MORNING_REPORT.md). Historical counts above remain evidence for their original checkpoints, not newly rerun claims. Hardware acceptance is separate.

## 10 October controller journeys/recovery checkpoint

176 client cases (zero errors/failures, one optional SDL skip), 62 root cases and 20 selected game cases pass. Full actual-map Cook/Rune routes include native rewards and save/load; no production collision/content rule changes. Exact exported stacks match 99 client/33 server files; shadow builds and matched stamp verify. Actual Swing character-entry/backend, real owned-server pidfd recovery and repeated graphical New/Continue pass. Four completed-session backups, native save/reload, fresh relog capabilities and pre-ready cancellation preserving the entire saved world are verified; original mutable-path size/mtime fingerprints remain unchanged. Actual Claude completed four bounded static reviews and findings were repaired. See [journeys validation](CONTROLLER_JOURNEYS_VALIDATION.md) and [combined report](MORNING_REPORT.md). Hardware, native orphan-client and exhaustive content/crash coverage remain separate.

## Real Steam Deck and launcher keyboard checkpoint (2026-10-10)

Actual SteamOS Desktop private deployment, SDL detection, native New/Continue/adventure/settings/save/cancel and native two-JVM ownership recovery pass. 78 root cases pass on host and Deck. Windowed software-renderer intervals/resources are observations, with host-wide sensors and no battery-life claim. After physical owner feedback, launcher patch 0029 adds exclusive Steam/local keyboard modes, neutral rearm and desktop/controller navigation choice; 179 fresh client cases pass (one optional SDL skip) and 100 client/33 server files reproduce. Native Swing local/system-mode probes pass. See [Deck evidence](DECK_VALIDATION.md), [setup](DECK_SETUP.md), [Claude keyboard review](CLAUDE_DECK_KEYBOARD_REVIEW.md) and [combined report](MORNING_REPORT.md). Physical keyboard behavior, Gaming Mode and the requested in-game ownership extension remain open.


## In-game text ownership and classic UI — 10 October 2026

Client test/shadow build: 192 cases, zero failures/errors, one existing optional SDL skip. Root tooling: 78 passing. Exact client/server source reproduction: 106/33 files through client 0030/server 0011, with matched jar/stamp. ShellCheck and Python compilation pass for the extended native smoke wrapper/parser.

Twenty synthetic previews compile/render in both palettes at 765×503 and 1280×800; representative classic inventory/journal/Home/text layouts were inspected. The Swing local/system entry/backend probe passes after sharing the Steam request transport.

Focused host New/Continue and full adventure/settings native probes pass real CS2 amount/name/string edit/cancel, native received public chat on Enter, Escape without submission and retained-text cleanup. Native movement remains unchanged; logout/relogin/capability refresh, configuration reversal, exact saves/four backups and early cancellation pass. Private evidence: `.runtime/alpha-tests/session-1791639855995810149` (focused) and `.runtime/alpha-tests/session-1791639994070449193` (full). These use an owned Xvfb and injected Steam visibility; physical simultaneous keys/buttons and Steam visibility remain acceptance work. [Scope](IN_GAME_TEXT_INPUT.md), [Claude static review](CLAUDE_INGAME_KEYBOARD_REVIEW.md) and the combined report distinguish remaining server-suspension/type-11/full-widget coverage.

The same full probe passes on the actual Deck Desktop in verified r8, with zero non-probe mouse clicks and exact save/backup/cancellation checks. Deployment and capture limits are in [Deck validation](DECK_VALIDATION.md#in-game-text-and-classic-ui-deployment--r8).
