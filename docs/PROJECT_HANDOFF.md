# SoloScape 2011+ — current state for ChatGPT discussion

Updated 9 October 2026. This is self-contained and can be pasted into ChatGPT together with ROADMAP.md and MORNING_REPORT.md. The roadmap is a proposal, not blanket authorization to build every item.

## Direction and constraints

SoloScape is a local, single-player-first RuneScape RPG based on revision 634 (December 2010), using pinned 2011Scape/Void server and RuneLite-style client sources. The desired feel is a 2010–2011 console RuneScape release: pre-EoC combat, tile-based world rules, Summoning/Dungeoneering-era potential, native controllers and Steam Deck UX. Later ambitions are carefully selected OSRS-style additions, solo adaptations, a small persistent AI population and optional private co-op. Those ambitions are not implemented yet.

Preserve normal server authority, native collision/pathfinding/transactions, existing saves and reversible experiments. Do not infer complete quest/skill coverage from the era or upstream project. Proprietary cache/assets, credentials, accounts, JDKs and jars are excluded from Git. Contributions are welcome with agreed scope and owner-controlled merges; the project remains maintainer-directed.

Public repository: https://github.com/kannibalk1w1/SoloScape. Current development: `overnight/controller-sprint`; local branch `soloscape/bootstrap`. Public main stays on the earlier baseline. Ignored upstream checkouts are reproduced by ordered tracked patches; do not switch stacks in the same patched checkout.

## What exists now

The two controller sprints, larger console alpha and cohesive menu/session milestone are implemented. The owner has confirmed local launch, camera, movement feedback, improved walking/aiming/interaction and that direct movement feels good. New menu/back/scroll/art changes require a fresh physical acceptance pass.

| Default input | Behavior |
| --- | --- |
| Left stick | Camera-relative destination walking, or optional eight-way server direct intent; gentle tilt walks, strong tilt requests running |
| Right stick | Camera in world; vertical focus/scroll in active supported menus; neutral required at ownership handoff |
| LT | Aim without new movement |
| LB/RB | World targets, UI panes, radial slots or production amount as appropriate |
| A | Normal fresh native action/confirm |
| X | Native alternatives; quick-slot assignment |
| B | Action list, entry/dialogue or native modal back/close; known parent tab/Home restoration; world cancellation |
| Y | Inventory focus; quick-slot clear |
| View/Select | Sixteen-slot Home-tab radial using actual available native tabs |
| Start/Menu | Eight explicit quick-action slots; initially empty |
| D-pad | UI/grid/action/keyboard focus and native scroll edges |

Eight logical actions are remappable with conflict feedback. Xbox, PlayStation and Deck presets, inversion/deadzone, overlay scale and direct run threshold are available. Live authored hints use physical mappings without rewriting native action labels. Native game UI text itself is not universally rescaled.

World input includes target/movement overlays, visible-pile loot cycling, NPC/object/item action menus, native approach/range/LOS handling and cancellation. Direct movement is a reversible plugin setting, gated by the matched server's current-session nonce capability acknowledgement. Long input gaps/focus loss clear intention and require neutral rearming. No free-position physics rewrite was introduced.

Native controller interfaces include inventory/dialogue, bank/shop stock and carried panes, quantities/search, controller text/amount entry, equipment/bonuses, prayer/spells and selection handoff, Combat/Skills/Quests/supported Settings, production amounts/smithing/tanning/jewellery. Four optional custom surfaces independently replace inventory/equipment/bank/shop presentation. They retain native identity, quantities, permissions and selected-item/spell semantics, mouse/trackpad input, game feedback and two-press Drop/Destroy confirmation.

Menu ancestry stores screen identities, never invokable actions. Settings child close is observed before restoring Settings focus; root tab B returns to Home; direct inventory returns to world. Server-closed modal ancestry is discarded. Right stick scrolls the active vertical pane at tilt-dependent speed with native edge validation; action/pane button presses take precedence. Generic server-modal-to-modal reopening is not supported for arbitrary screens; known parent-tab restoration is the fallback.

Custom screens use a bounded exact item/quantity cache of pixels already produced by native rendering. Names remain readable when icons are absent. Native-cache hits after relog/offscreen items and selected-outline variants still need artwork refinement. Long action-list sidebars keep selected native indices visible with matching mouse targets.

## Launcher and saves

The graphical launcher provides New Character, Continue, private character/world selection, progress/errors, persisted port settings, diagnostics, Back Up, Restore Backup, Manage Backups and owned Save & Quit. Each profile has independent world generations, derived/log paths, private client home/settings and local credential file. New Character does not migrate or alter the old development world. Launcher name entry still uses the desktop keyboard; profile focus supports SDL navigation.

Backup archives include saves, exchange state and failed saves; checksums and native save structure are validated. Restore switches generations atomically and retains old data; damaged metadata can be recovered. Import uses a CLI over an independent stopped-world copy and preserves authentication hashes. No forgotten-password reset exists.

Manage Backups is explicit and previewed: keep 2–100 recent automatic archives; retain manual/import/damaged/restore-source archives and every generation. Apply locks the profile, revalidates and rejects changed previews. There is no automatic pruning or generation deletion.

Preload/world-start failures stop owned services and return. The world save hook is registered after successful world loading, so partial startup cannot save partially loaded shared state. Shutdown waits for native saves without forced kill. Owned sessions hold shared archive locks through shutdown/backup; builds take exclusive access. Manually launched JVMs or abnormal backend death remain outside that guarantee.

## Content evidence

Existing Cook's Assistant can progress through native dialogue, general-store bucket/pot purchases, prized-cow milk, super-large egg, wheat/hopper/controls/extra-fine flour and return rewards. A combined disposable fixture test continues through banking, shrimp fishing/cooking, chicken combat/food and native save/load. Only a small net/10 coins are seeded; XP, ingredients, loot and quest state are earned. A second test verifies transient shared store binding, wrong-item rejection, two shoppers and unbinding. A separate test walks actual Lumbridge courtyard/village/north bridge collision paths in both directions.

The route found a real bug: native validation could not resolve shared general-store stock. It now binds transiently while open and never becomes a saved player inventory. The full actual-map quest route, doors/gates and mill floor changes still need a physical controller playthrough. This is targeted evidence, not an all-content audit.

## Validation and delivery

Current checkpoint: 151 client cases (zero failures/errors, one optional SDL skip), 44 root tooling/profile/lifecycle cases and 11 selected game cases all pass. Exact 87-file client/31-file server patch reproduction and matched shadow jars/stamp pass. Prior alpha evidence included 74 config, 249 networking and 49 selected engine cases; these were not newly rerun this milestone.

Private native New/Continue reached the rendered world, normal login/Continue and negotiated capabilities, preserved save/load fields and created four verified completed-session backups. Early native loading cancellation preserved every saved-world file. Original saves/errors/derived size/mtime fingerprints stayed unchanged. Prepare refused during the private session, then succeeded afterward. Private Xvfb/software complete-session totals were 27.407/25.532 seconds, including readiness waits and save/shutdown; not FPS/latency/Deck benchmarks.

Actual Claude performed bounded static reviews via the existing Orca terminal. Stale parents, native-label mapping and build-under-live-session findings were fixed; final follow-up found no blockers. Reviews are source audits, not hardware tests. The original game, saves/cache and public main were preserved.

Use README-SOLOSCAPE.md and CACHE_SETUP.md for pinned clones/JDK/cache setup. The compatible cache comes from the pinned upstream maintainer's linked MEGA archive, not an official Jagex distribution. The recorded verified archive is `2026-08-02-void-634-cache.7z`; the guide includes extraction and checksum. The client fetches assets from the local server after its cache is installed; launching does not fetch a missing server archive.

After Save & Quit of existing owned sessions:

```bash
./scripts/prepare-build.sh
./scripts/launcher.sh
```

Prepare applies patches/builds/verifies the matched pair without starting a world. The development-only legacy-world path remains `./scripts/dev-run.sh --no-build`. Do not rebuild/update sources under a manually launched game.

## What remains and what to discuss next

- Physical controller and Steam Deck Gaming Mode acceptance, sustained frame times/battery/thermal budgets, suspend/resume and full reconnect campaign.
- Complete real-map quest route and concrete awkward menu/submenu cases; arbitrary modal ancestry and niche tab coverage.
- Artwork cache/outline refinement, tooltip/readability/accessibility polish, first-run discovery and controller-only launcher text entry.
- True solo world pause: investigation exists, but clock/stage/network/guest/shutdown work is required before exposure. Menus currently do not freeze simulation.
- Packaging/runtime/dependency licence inventory and distributable installer; source builds remain the delivery path.
- Broader quests/skills, Summoning/Dungeoneering, co-op, economy/solo progression/bots/AI population and original world graphics remain future scope.

Recommended next step: run CONSOLE_SESSION_ACCEPTANCE.md plus CONSOLE_SESSION_ROUTE.md on a physical controller, fix concrete issues, then measure Deck lifecycle/performance before adding more systems. ROADMAP.md remains the full proposed backlog; CONSOLE_SESSION_TASKS.md records this approved milestone. MORNING_REPORT.md combines all completed batches and earlier reports remain archived.
