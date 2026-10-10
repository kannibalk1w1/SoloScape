# SoloScape 2011+ — current state for ChatGPT discussion

Updated 10 October 2026. This is self-contained and can be pasted into ChatGPT together with ROADMAP.md and MORNING_REPORT.md. The roadmap is a proposal, not blanket authorization to build every item.

## Direction and constraints

SoloScape is a local, single-player-first RuneScape RPG based on revision 634 (December 2010), using pinned 2011Scape/Void server and RuneLite-style client sources. The desired feel is a 2010–2011 console RuneScape release: pre-EoC combat, tile-based world rules, Summoning/Dungeoneering-era potential, native controllers and Steam Deck UX. Later ambitions are carefully selected OSRS-style additions, solo adaptations, a small persistent AI population and optional private co-op. Those ambitions are not implemented yet.

Preserve normal server authority, native collision/pathfinding/transactions, existing saves and reversible experiments. Do not infer complete quest/skill coverage from the era or upstream project. Proprietary cache/assets, credentials, accounts, JDKs and jars are excluded from Git. Contributions are welcome with agreed scope and owner-controlled merges; the project remains maintainer-directed.

Public repository: https://github.com/kannibalk1w1/SoloScape. Current development: `overnight/controller-sprint`; local branch `soloscape/bootstrap`. Public main stays on the earlier baseline. Ignored upstream checkouts are reproduced by ordered tracked patches; do not switch stacks in the same patched checkout.

## What exists now

The two controller sprints, larger console alpha, cohesive menu/session milestone controller-first adventure implementation and controller journeys/recovery sprint are delivered. The owner has confirmed local launch, camera, movement feedback, improved walking/aiming/interaction and that direct movement feels good. The latest custom adventure screens, controller setup and source/target return require a physical acceptance pass; native desktop integration and isolated tests are recorded separately.

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

Native controller interfaces include inventory/dialogue, bank/shop stock and carried panes, quantities/search, controller text/amount entry, equipment/bonuses, prayer/spells and selection handoff, Combat/Skills/Quests/supported Settings, production amounts/smithing/tanning/jewellery. Nine independently optional custom surfaces cover inventory/equipment/bank/shop plus quests/journals, skills, combat, prayer and spellbooks. Read-only journal/skill details have no invented actions. Combat style/retaliation/special energy, prayer levels/active/quick states and pinned spell names with native-cache Magic/rune requirements are displayed. Existing native validation remains authoritative; rune display does not calculate staff substitutions or every server eligibility condition. They retain native identity, quantities, permissions and selected-item/spell semantics, mouse/trackpad input, game feedback and two-press Drop/Destroy confirmation.

Menu ancestry stores screen identities, never invokable actions. Settings child close is observed before restoring Settings focus; root tab B returns to Home; direct inventory returns to world. Server-closed modal ancestry is discarded. Right stick scrolls the active vertical pane at tilt-dependent speed with native edge validation; action/pane button presses take precedence. Generic server-modal-to-modal reopening is not supported for arbitrary screens; known parent-tab restoration is the fallback.

Custom screens use a bounded exact item/quantity cache of pixels already produced by native rendering. Names remain readable when icons are absent. A bounded weak cache republishes already converted native sprite-cache hits after relog; selected/high-outline variants are excluded. Items never rendered natively retain text fallback, with no added model renderer. Long action-list sidebars keep selected native indices visible with matching mouse targets.

The Home Settings tab now offers controller preferences and first-run setup: presets, bindings, deadzone, run threshold, scale, inversion, glyphs and screen toggles. Occupied bindings swap; first-run completion is explicit. Game Settings remains a child for native graphics/audio, with B returning to controller preferences, then Home. This custom settings surface can be disabled independently; custom adventure screens default off. No setup screen silently enables direct movement or matched-server features.

Item/spell source targeting shows the selected source and target phase. Ordinary panel selections remember their origin and restore it once on use/cancel, refreshing item identity/quantity before focus. Quick casts stay in world controls. Modal interruptions, focus loss, logout and changed selection tokens discard stale return state. Eight quick slots also support the validated native special-attack action; server restrictions remain intact.

## Launcher and saves

The graphical launcher provides New Character, Continue, private character/world selection, progress/errors, persisted port settings, diagnostics, Back Up, Restore Backup, Manage Backups and owned Save & Quit. Each profile has independent world generations, derived/log paths, private client home/settings and local credential file. New Character does not migrate or alter the old development world. New Character has a controller entry keyboard with D-pad/A, X delete, Y advance, Shift, form-preserving B and desktop keyboard/mouse coexistence. Inline backend errors preserve values; profile focus supports SDL navigation.

Backup archives include saves, exchange state and failed saves; checksums and native save structure are validated. Restore switches generations atomically and retains old data; damaged metadata can be recovered. Import uses a CLI over an independent stopped-world copy and preserves authentication hashes. No forgotten-password reset exists.

Manage Backups is explicit and previewed: keep 2–100 recent automatic archives; retain manual/import/damaged/restore-source archives and every generation. Apply locks the profile, revalidates and rejects changed previews. There is no automatic pruning or generation deletion.

Preload/world-start failures stop owned services and return. The world save hook is registered after successful world loading, so partial startup cannot save partially loaded shared state. Shutdown waits for native saves without forced kill. Owned sessions hold shared archive locks through shutdown/backup; builds take exclusive access. Profile and archive lock descriptors are inherited by owned JVMs, retaining protection if the launcher is killed. Locks release only after the last owned process exits; no clean backup is claimed after abnormal launcher death. Recover Session now checks boot/PID start, user, session/role identity, exact archive/save path and inherited guards before pidfd SIGTERM; it refuses active original owners or suspended/mismatched processes. Verified recovered snapshots retain earlier backups and explicitly leave clean shutdown unconfirmed. Ended records can be archived without claiming save validity, allowing Restore; outstanding records block generation changes. Backend SIGTERM/SIGHUP waits for normal owned shutdown. Manually launched JVMs remain outside this ownership guarantee. Port checks now tolerate normal TCP TIME_WAIT while rejecting a live listener.

## Content evidence

Existing Cook's Assistant can progress through native dialogue, general-store bucket/pot purchases, prized-cow milk, super-large egg, wheat/hopper/controls/extra-fine flour and return rewards. A combined disposable fixture test continues through banking, shrimp fishing/cooking, chicken combat/food and native save/load. Only a small net/10 coins are seeded; XP, ingredients, loot and quest state are earned. A second test verifies transient shared store binding, wrong-item rejection, two shoppers and unbinding. A separate test walks actual Lumbridge courtyard/village/north bridge collision paths in both directions.

The route found a real bug: native validation could not resolve shared general-store stock. It now binds transiently while open and never becomes a saved player inventory. The new actual-map audit completes The Restless Ghost through ordinary walking, its door/coffin/amulet/skull scenes, native reward and save/load. A second route starts Cook’s Assistant and Rune Mysteries, walks the castle’s real doors/north stairs and banks the talisman upstairs. The journeys sprint additionally completes actual-map Cook ingredient/gate/mill/reward travel and Rune Mysteries castle/tower/basement/Varrock/reward travel with native save/load. Test players begin in the quest-giver scene and use ordinary Walk/native interactions; no injected quest state/items, fixture scenery or teleport commands make these routes pass. Physical controller playthroughs remain required. See ADVENTURE_ROUTE_AUDIT.md for the exact evidence.

## Validation and delivery

Current checkpoint: 176 client cases (zero failures/errors, one optional SDL skip), 62 root tooling/profile/lifecycle/recovery cases and 20 selected game cases pass. Exact 99-file client/33-file server patch reproduction and matched shadow jars/stamp pass. Prior alpha evidence included 74 config, 249 networking and 49 selected engine cases; these were not newly rerun this milestone.

Private native New/Continue validation covers ordinary login/Continue, native panel details, real settings Gateway/openHomeTab adoption across ticks, configuration change/reversal, B-to-Home and normal native mouse logout followed by settled same-client relogin with fresh negotiated capabilities. Save/load fields, verified completed-session backups, whole-world early-loading cancellation and original mutable-path fingerprints are checked. Private Xvfb/software render intervals, heap/RSS and session totals are in ADVENTURE_NATIVE_VALIDATION.md; they do not establish GPU/Deck performance or physical SDL-driven first-run handling.

Actual Swing entry/backend validation and real orphan-server pidfd recovery also pass on disposable storage. Recovery checks real inherited guards and validates a recovered snapshot without a clean-shutdown claim; native orphan-client recovery remains unproved. See CONTROLLER_JOURNEYS_VALIDATION.md.

Actual Claude performed bounded static reviews of prior batches and four journeys reviews via the existing Orca terminal. Finished-worker ownership, restore generation protection, exact process identity, other-profile listing, stale Home ancestry and recovery-probe cleanup findings were fixed. Two Home ancestry regressions failed before the fix and pass after it. Stale parents, native-label mapping and build-under-live-session findings were fixed; final follow-up found no blockers. Reviews are source audits, not hardware tests. The original game, saves/cache and public main were preserved.

Use README-SOLOSCAPE.md and CACHE_SETUP.md for pinned clones/JDK/cache setup. The compatible cache comes from the pinned upstream maintainer's linked MEGA archive, not an official Jagex distribution. The recorded verified archive is `2026-08-02-void-634-cache.7z`; the guide includes extraction and checksum. The client fetches assets from the local server after its cache is installed; launching does not fetch a missing server archive.

After Save & Quit of existing owned sessions:

```bash
./scripts/prepare-build.sh
./scripts/launcher.sh
```

Prepare applies patches/builds/verifies the matched pair without starting a world. The development-only legacy-world path remains `./scripts/dev-run.sh --no-build`. Do not rebuild/update sources under a manually launched game.

## What remains and what to discuss next

- Physical controller and Steam Deck Gaming Mode acceptance, sustained frame times/battery/thermal budgets, suspend/resume and full reconnect campaign.
- Physical full-quest/journal acceptance, broader real-map content, concrete awkward menu/submenu cases, arbitrary modal ancestry and niche tab coverage.
- Wider artwork availability, readability/accessibility, physical launcher naming/recovery acceptance and exhaustive crash/native orphan-client coverage.
- True solo world pause: investigation exists, but clock/stage/network/guest/shutdown work is required before exposure. Menus currently do not freeze simulation.
- Packaging/runtime/dependency licence inventory and distributable installer; source builds remain the delivery path.
- Broader quests/skills, Summoning/Dungeoneering, co-op, economy/solo progression/bots/AI population and original world graphics remain future scope.

Recommended next step: accept the adventure screens, controller setup/remapping, native Settings child/B sequence, source targeting/return and special binding on a physical controller. Physically play the now-verified Cook/Rune routes and accept launcher naming/recovery, then measure Deck lifecycle/performance before packaging or widening systems. ROADMAP.md remains the full proposed backlog; CONTROLLER_JOURNEYS_TASKS.md records this approved milestone. MORNING_REPORT.md combines all completed batches and earlier reports remain archived.
