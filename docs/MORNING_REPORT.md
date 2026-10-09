# SoloScape — combined morning / completion report

9 October 2026. This combines the two original controller sprints, the larger console alpha, and the approved cohesive session milestone. The implementation is committed to [overnight/controller-sprint](https://github.com/kannibalk1w1/SoloScape/tree/overnight/controller-sprint); public main remains at its preceding baseline. The existing game was left running. Original saves/cache were not migrated or removed. Private native checks used a disposable profile, separate port and virtual display.

Historical reports remain available: [two controller sprints](MORNING_REPORT_CONTROLLER_SPRINTS.md), [console alpha](MORNING_REPORT_CONSOLE_ALPHA.md), and [first sprint](MORNING_REPORT_SPRINT_1.md). This report supersedes their current-state instructions.

## Current state for ChatGPT discussion

SoloScape is a playable local, single-player-first revision-634 RuneScape project, delivered as reproducible patches over pinned 2011Scape/Void server and RuneLite-style client sources. The intended experience is pre-EoC RuneScape with console controls and eventual Steam Deck support. Tile simulation, collision, combat and inventory transactions remain native and server-authoritative. Assets, saves, credentials, runtimes and built jars stay outside the public source repository. Contributions are welcome within agreed maintainer-directed scope.

The owner has confirmed launch, camera, movement feedback, improved aiming/interaction and that optional direct movement feels good. The newest menu hierarchy, artwork and recovery changes have automated evidence and still need physical acceptance. There is no packaged release, measured Deck performance budget, complete content audit, AI population, solo-economy redesign, exposed world pause or wholesale original graphics replacement.

Read [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) and the full proposed [ROADMAP.md](ROADMAP.md) alongside this report for discussion. The roadmap is a proposed backlog, not approval to implement every future feature.

## Combined delivery

| Area | Earlier controller sprints | Console alpha | New session milestone |
| --- | --- | --- | --- |
| Movement/world | Camera, destination/direct movement toggle, movement markers, LT aim, cycling, X native menus, loot, B cancellation | Eight mappings, presets, conflict checks, run threshold, capability nonce, interruption guards | Camera/scroll ownership and neutral handoff across menus |
| Native interfaces | Inventory/dialogue, bank/shop quantities/search, controller entry, equipment/prayer/spells, production | Optional custom inventory/equipment/bank/shop surfaces with fresh native validation and destructive confirmation | Shared Home/tab/modal ancestry, restored focus, active-pane right-stick scrolling, stale-parent cleanup |
| Readability | Scalable overlays, Xbox/PS labels and guide | Native item names, quantities, bonuses, actions, mouse/trackpad, game feedback | Cached native item artwork, physical mapped hints, selected-action sidebar viewport |
| Sessions/saves | Owned startup/readiness/shutdown and matched build stamp | Graphical New/Continue, independent worlds/generations, verified backups/restore, damaged metadata recovery, stopped-copy CLI import | Startup failure/save-hook ordering, native cancellation preservation, explicit previewed backup retention, restore-source protection |
| Content | Ordinary native handlers retained | Level-one fishing/cooking/equipment/chicken/food/save route | Existing Cook's Assistant quest plus shop/milling/bank/fishing/cooking/combat/save route; actual Lumbridge travel; general-store validation repair |
| Delivery | Public development branch, pinned patches, cache instructions, Claude reviews | Full patch reproduction and isolated graphical New/Continue | Build-only Prepare/update workflow, archive locks, acceptance/performance checklist, bounded Claude review and follow-up |

## What changed in this milestone

**Menu back:** Settings opened from Home returns through its observed native child close to Settings, then Home, then world controls. An action list closes before its panel. Direct inventory retains its direct world return. Focus is remembered by native identity and refreshed before actions; server-closed modals discard their parent entry. Generic reopening of one server-owned modal from another remains limited to supported parent-tab restoration.

**Right stick:** vertically scrolls/moves rows in the active pane, repeats slowly at gentle tilt and faster at strong tilt, and uses validated native scrolling at viewport edges. It never performs an item transaction. A held stick must return to neutral when opening/closing a menu. Camera is suppressed while menus own input. Horizontal-dominant tilt is ignored for these vertical panes. Confirm/actions/pane button presses take precedence over a simultaneous scroll step.

**Art and hints:** original native sprite pixels are copied into a bounded 128-entry memory cache keyed by exact item/quantity. Names remain the fallback. Native sprite-cache hits after relog and offscreen items can still lack artwork, and outline variants may differ; no extra asset/model renderer runs on the overlay thread. Hints follow the eight physical mappings in one pass; native labels such as Withdraw-X and Make X remain unchanged. Long action lists preserve native indices and only drawn rows have hit targets.

**Commerce/content:** Lumbridge general-store purchases previously failed the native validator because global stock was not registered in the player's validation context. A transient shared inventory reference now exists only while the shop is open, and is excluded from character saves. Tests still reject wrong item identity. The existing quest route earns ingredients/progress/rewards through native handlers. Only starting net/coins are seeded; valid deterministic rolls remove chance. A separate real-map test walks courtyard→village→north bridge and back. Full ingredient travel, gates and mill floor changes still need physical route acceptance.

**Recovery/delivery:** failed preload/world startup returns after stopping owned services. The shared-world save hook is registered only after successful world loading. Native early cancellation preserves the entire saved world. Manage Backups previews filenames/bytes, keeps the chosen 2–100 recent automatic backups, and retains manual/import/damaged/restore-source archives and all generations. Cleanup locks the profile and refuses a changed preview. Prepare builds without launching a world, and exclusive archive locks refuse rebuilding while an owned session uses the jars.

## Validation evidence

| Check | Result |
| --- | --- |
| Client suite | 151 cases, zero failures/errors; one pre-existing optional SDL skip |
| Root tooling/profile/lifecycle suite | 44 cases, all passing; disposable fixtures only |
| Selected native game suite | 11 cases: seven existing shop cases, prior progression route, and three new session/shared-stock/actual-travel checks; all passing |
| Prior alpha server module evidence | 74 config, 249 networking, 49 selected engine cases passed at the alpha checkpoint; not rerun or claimed as newly measured here |
| Graphical native integration | New/Continue reach rendered world, ordinary native Continue and verified capabilities; XP/items/location preserve across save/load; four verified completed-session backups |
| Real native cancellation | Observed early content-load cancellation before ready; every saved-world file preserved, no client started |
| Original world preservation | Original saves/errors/derived path size/mtime fingerprints unchanged after private sessions |
| Build/export | Matched shadow jars and stamp; full 87-file client and 31-file server stacks reproduce exactly; fresh/upgrade/reverse/idempotence verified |
| Prepare | Succeeds with cached pinned setup without launching; correctly refuses during the native profile session |
| Hygiene | Python compilation, ShellCheck and whitespace checks pass |

Private Xvfb/software New and Continue complete-session totals were **27.407 s** and **25.532 s**. These include readiness dwell, client loading and shutdown; they are not frame-rate or input-latency benchmarks. The harness writes a local summary under `.runtime/alpha-tests/session-*/native-smoke-summary.json`; it is not committed. Neither fixture tests nor the graphical smoke claim physical controller/Deck acceptance or exhaustive cancellation at every loading phase.

## Claude review

Actual Claude reviewed navigation and the subsequent implementation in the existing Orca terminal, with bounded static passes. It found stale modal ancestry, physical-hint label rewriting and a build/session archive-lock gap. All were repaired; follow-up reports **no remaining blockers**. It also checked shared stock, retention and startup save-hook ordering. [Navigation review](CLAUDE_SESSION_NAVIGATION_REVIEW.md), [implementation and fixes](CLAUDE_SESSION_FOLLOWUP.md). Earlier alpha and sprint reviews remain archived. The review used the `orca-cli` skill; it was not a runtime or hardware test, and no current quota percentage is inferred.

## Commits and next launch

- `320f963`: menu ancestry, remembered focus and right-stick scrolling.
- `017f2ad`: native item artwork, mapped hints, sidebar polish and explicit backup management.
- `ef55e2a`: gameplay/shop validation, startup preservation, build locking, review fixes and setup/acceptance guidance.
- A final documentation commit records this combined report and current-state backlog.

To use the new build, Save & Quit the old game, then:

```bash
./scripts/prepare-build.sh
./scripts/launcher.sh
```

Continue selects an isolated character world; it does not silently import the old development world. The legacy development path is `./scripts/dev-run.sh --no-build`. Cache acquisition/extraction remains in [CACHE_SETUP.md](CACHE_SETUP.md), sourced from the pinned upstream maintainer README rather than an official Jagex asset distribution. Launching the client does not supply a missing server archive.

## Remaining work and recommended next step

The approved implementation/preparation list is in [CONSOLE_SESSION_TASKS.md](CONSOLE_SESSION_TASKS.md). Next, run the focused [physical acceptance matrix](CONSOLE_SESSION_ACCEPTANCE.md) and [existing quest route](CONSOLE_SESSION_ROUTE.md), recording specific awkward menu transitions and scroll behavior. Then fix those cases and measure representative Deck frame times/lifecycle before packaging or adding more systems.

Known limits: artwork is opportunistic; arbitrary server-modal reopening, complete quest/skill audits and all hardware checks remain pending. Save generations are retained and can consume space. Backup verification can be slow with a large history. Exchange files are individually atomic, not a multi-file transaction. Import is a CLI and launcher name entry uses desktop text entry. Unowned/manual JVMs or abnormal backend death can bypass the owned archive-lock guarantee. True pause, Deck suspend/resume, packaging/licence inventory and custom world graphics remain roadmap decisions.
