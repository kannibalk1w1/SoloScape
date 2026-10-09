# SoloScape 2011+ — proposed project roadmap and task list

Updated: 9 October 2026. Companion: [current-state handoff](PROJECT_HANDOFF.md).
This is a proposal to review, reorder and use as the working backlog. Later tasks
are not automatic authorization to build them. No dates or effort estimates are
promised before the relevant subsystem has been inspected.

## Product direction

A local RuneScape RPG with 2010–2011 mechanics, native console controls, a dependable
Steam Deck lifecycle and carefully selected later content. Single-player comes first;
small private co-op remains compatible. Preserve pre-EoC combat, tile rules and
server authority. Reuse upstream systems, keep experiments reversible, and deliver
playable increments. Proprietary cache/assets stay outside the source repository.

Custom art should first establish readability and a consistent identity. A wholesale
world art replacement or free-position movement rewrite is a separate decision,
not a prerequisite for a good console RuneScape experience.

## Tracking rules

- `[x]` means the specified implementation/check is complete. It does not replace
  a separate physical gameplay acceptance task.
- `[ ]` means pending, including built features awaiting user acceptance.
- IDs are stable task references. Do not renumber completed tasks when priorities change.
- For each task record a commit, validation evidence and any known limit in the PR/notes.
- Pick one small implementation batch at a time; finish its acceptance before expanding.
- Review this list after each milestone; update the handoff when project state changes.

## Current baseline

- [x] BASE-01 Pin the server/client sources and establish project-local Java runtimes.
- [x] BASE-02 Install the compatible cache with user authorization and validate startup.
- [x] BASE-03 Provide doctor, one-command launch and owned-process graceful shutdown.
- [x] BASE-04 Implement native camera, destination movement, targeting and scene feedback.
- [x] BASE-05 Implement inventory/dialogue navigation and input lifecycle gates.
- [x] BASE-06 Add reversible direct movement with authoritative server steps; user says it feels good.
- [x] BASE-07 Build X world menus, complete visible-pile loot targeting and B cancellation.
- [x] BASE-08 Preserve changes in reproducible client/server patches and pass current tests.
- [ ] BASE-09 Accept the newest interaction build in-game; see M0 below.
- [x] BASE-10 Fix review findings H1/M2/M3: B content cleanup and per-geometry target checks, with regression tests.
- [x] BASE-11 Build a reversible 16-slot home-tab radial proof of concept; native tab screens remain.

## Overnight controller sprint checkpoint

Both autonomous controller sprints are implemented on `overnight/controller-sprint`: reliability; bank/shop quantities/search; equipment/prayer/spell targeting; eight explicit quick-action slots; common production amount/smithing/tanning/jewellery controls; Combat/Skills/Quests/selected Settings handoff; scalable controller overlays, glyph labels, menu-button settings and a guide. Evidence: 121 client cases, 14 root cases, full 59/14-file patch exports; see [archived controller report](MORNING_REPORT_CONTROLLER_SPRINTS.md). Current automation and remaining hardware gates are in MORNING_REPORT.md. Physical controller/Deck acceptance remains pending. M1-04/05/06/07/09/10 and M2 stay open where their full scope exceeds these increments.

## Console alpha checkpoint

The larger approved alpha builds on both sprints: isolated profiles and verified generation recovery; graphical launcher; reusable custom panels and four independently reversible screens; eight bindings/presets/run thresholds; current-session capability negotiation and interruption guards; isolated native progression and graphical save/reload validation. See [approved alpha task list](CONSOLE_ALPHA_TASKS.md) and the combined morning report for precise evidence and limitations. Next priority is physical controller/Deck acceptance and concrete usability fixes, followed by measured performance, broader content auditing and packaging.

## Cohesive session checkpoint

The approved 9 October milestone connects Home/tab/modal B ancestry and remembered focus; adds active-pane right-stick scrolling and camera neutral handoff; displays opportunistic native item artwork and remapped physical hints; fixes shared general-store validation; tests Cook's Assistant/commerce/gathering/combat/save progression plus actual Lumbridge walking; strengthens startup preservation and previewed backup retention; provides a build-only setup/update path and archive locking. [Task list](CONSOLE_SESSION_TASKS.md), [combined report](MORNING_REPORT.md), [physical acceptance and performance](CONSOLE_SESSION_ACCEPTANCE.md). Physical acceptance, full real-map quest travel and sustained Deck measurements remain open. This implementation does not automatically complete every broader M0–M4 acceptance item.

## Controller-first adventure checkpoint

The delivered adventure implementation adds a shared readable theme and native artwork reuse; reversible quest journal/skills/combat/prayer/spellbook screens; native state, levels and cache-derived rune requirements; a native special-attack quick binding; controller preferences and first-run setup; selection-source feedback and origin return. Durable owned-JVM locks protect archives/profile storage after launcher death. Actual-map Restless Ghost and castle/banking routes save/reload natively. Repeated native desktop sessions and static Claude review are documented in [adventure tasks](ADVENTURE_SPRINT_TASKS.md), [route audit](ADVENTURE_ROUTE_AUDIT.md) and [native validation](ADVENTURE_NATIVE_VALIDATION.md). Physical controller/Deck acceptance, full Cook/Rune Mysteries travel and sustained hardware measurements remain open.

## M0 — finish the first reliable controller playable

Priority: now. Depends on the current built client and server.

- [ ] M0-01 Restart both processes and test X on NPCs/objects with multiple native actions.
- [ ] M0-02 Confirm D-pad selection, one A action per press, B menu back and second B cancel.
- [ ] M0-03 Drop at least 12 distinct items on one tile; cycle both directions, pick one up, and test stack changes/despawns and a blocked pile near a reachable target.
- [ ] M0-04 Test direct and destination modes, LT aiming, mouse takeover and held-input recovery.
- [ ] M0-05 Verify inventory/dialogue priority, fixed/resized layouts and plugin disable/re-enable.
- [ ] M0-06 Verify a real save roundtrip: location, inventory, equipment, XP and quest variables survive clean exit/restart.
- [ ] M0-07 Record reproducible gameplay issues and fix blockers before the next feature batch.
- [ ] M0-08 Test world B while morphed and during content cleanup/exit; confirm recovery without losing the exit route.
- [ ] M0-09 Check banker/shopkeeper targeting across counters and border-guard crossings in both movement modes.
- [ ] M0-10 Test dialogue B while a walking step is interpolating.
- [x] M0-11 Implement review follow-ups: explicit matched-server guard, jar/patch fingerprints, exception recovery and idle snapshot cost. Automatic server capability negotiation is implemented in the alpha.
- [ ] M0-12 Accept View/Select tab radial in both layouts: all available tabs, held input, Inventory handoff, focus/reconnect and dialogue priority.

Acceptance: controller walking, camera, action selection, loot, inventory and dialogue
work together, and the character survives a clean restart with expected state.

## M1 — complete the everyday controller gameplay loop

Priority: next. Depends on M0. Recommended implementation order: bank → shop →
equipment/prayer/spells → targeting/quick actions → special interfaces.

- [x] M1-01 Audit bank widgets and native actions; implement item focus, deposit/withdraw and quantity selection.
- [x] M1-02 Add bank search/tab navigation and visible focus through scrolling lists.
- [x] M1-03 Implement shop stock/player inventory focus, buy/sell amounts and insufficient funds/stock feedback.
- [ ] M1-04 Implement equipment, stats, quest, settings and world-map panel navigation using real widget metadata.
- [ ] M1-05 Implement prayer/spell navigation, selection state and clear feedback for missing requirements.
- [ ] M1-06 Finish inventory item-on-item and item/spell-on-world targeting, with explicit cancel and target revalidation.
- [ ] M1-07 Add configurable quick slots for food, potions, prayers, spells and supported special attacks. **Implemented:** eight assignable food/potion/prayer/spell slots; supported native special-attack assignment is now implemented; physical acceptance remains.
- [x] M1-08 Support number/text entry, including a Deck-friendly keyboard path, without advancing unrelated dialogues.
- [ ] M1-09 Audit special interfaces such as smithing/crafting lists, quest choices and familiar/Dungeoneering panels; implement the highest-use gaps. **Implemented:** common make-amount, smithing, tanning, silver and jewellery paths; niche interfaces and acceptance remain.
- [x] M1-10 Add remapping/presets and document button precedence across world, menus and widgets. **Implemented:** eight separate bindings, overlap/neutral guards, Xbox/PlayStation/Deck presets, defaults and documented precedence. Logical overlay hints still need automatic physical-label substitution after remapping (M2-07).

Acceptance: a normal session of gathering, fighting, looting, banking and buying supplies
can be completed without a mouse, with an intentional mouse/trackpad fallback for any remaining niche interface.

## M2 — readable console interface and accessibility

Priority: high, after core flows work. Depends on M1 for stable navigation targets.
Original button glyphs/panel designs can be explored earlier without blocking M1.

- [ ] M2-01 Define a consistent UI style: colours, typography, focus outlines, action feedback and spacing.
- [ ] M2-02 Accept controller glyphs, contextual hints and first-run setup on hardware. **Implemented:** mapped hints, glyph presets and controller preferences/setup guide.
- [ ] M2-03 Provide readable text/UI scale at 1280×800 and validate resized layouts.
- [ ] M2-04 Improve dense target selection, loot labels, obstructed/off-screen feedback and failed-action messages.
- [ ] M2-05 Prototype a radial quick-action menu and compare it with a simple list before choosing a default.
- [ ] M2-06 Add practical accessibility settings: contrast, text size, vibration if useful, inversion and movement/run thresholds.
- [x] M2-07 Map authored control hints to physical bindings and provide Xbox/PlayStation/Deck presets. Physical layout acceptance remains in M4.

Acceptance: the main gameplay flows are legible and discoverable on a physical Deck
without knowing desktop RuneScape shortcuts or reading implementation details.

## M3 — saves and console application lifecycle

Priority: high, before long-term progression. Depends on M0 save validation; can
advance alongside M1 where work is independent.

- [x] M3-01 Define world/profile/character ownership and which state is saved per world or per player.
- [x] M3-02 Add New Character, Continue, save selection and character metadata.
- [x] M3-03 Add versioned backups, validated restore, corruption handling and migration rules; test copies before touching real saves.
- [x] M3-04 Provide a launcher that hides normal local service startup and auto-connects to the chosen save.
- [x] M3-05 Implement Save & Quit with visible completion and recoverable startup/shutdown errors.
- [x] M3-06 Make loopback the default bind; expose explicit audited private-host configuration.
- [x] M3-07 Investigate true solo pause versus menu overlays and host/join behavior; record stage/clock/network/shutdown requirements. **Investigation delivered; working pause remains deferred.**
- [ ] M3-08 Validate abrupt client closure and interrupted startup; preserve saves and avoid orphan processes.
- [x] M3-09 Show actionable cache/runtime/configuration errors in the launcher and keep diagnostics accessible.

Acceptance: launch → Continue → play → Save & Quit → restart works without a terminal,
and a tested backup can restore a character/world after a simulated failure.

## M4 — Steam Deck performance and lifecycle

Priority: high. Depends on M3 lifecycle foundations and readable M2 UI.

- [ ] M4-01 Validate native controls in Steam Gaming Mode, including correct Steam Input layout and trackpad coexistence.
- [ ] M4-02 Measure frame times, server tick times, memory, loading, battery and thermal behavior in representative areas.
- [ ] M4-03 Create measured graphics/performance presets; assess software/OpenGL paths before selecting defaults.
- [ ] M4-04 Fix the largest measured performance problems; retest bot-heavy and combat scenes.
- [ ] M4-05 Define suspend/resume handling: stale input, lost focus, elapsed world time, reconnect and persistence.
- [ ] M4-06 Test repeated suspend/resume, battery-low exit and disconnect; avoid advancing a solo world unpredictably while suspended.
- [ ] M4-07 Set performance budgets from actual Deck measurements, not desktop assumptions.

Acceptance: a repeatable Gaming Mode session runs within agreed performance budgets,
and tested suspend/resume or an explicit safe fallback preserves the save.

## M5 — early private multiplayer compatibility check

Priority: before global economy, population or pause changes. This is a smoke test,
not a polished hosting product. Depends on M0/M3 and the matching protocol builds.

- [ ] M5-01 Connect two clients/accounts to one server and verify independent positions, inventories and persistence.
- [ ] M5-02 Test one controller player and one mouse player; include direct movement, world cancel and item ownership.
- [ ] M5-03 Test a private LAN connection using explicit host configuration.
- [ ] M5-04 Audit new features for shared/global state, target identity and per-player UI/controller state.
- [ ] M5-05 Define host authority, guest saves, world ownership, solo-only settings and disconnect behavior.
- [ ] M5-06 Record protocol compatibility requirements and gracefully reject mismatched builds where feasible.

Acceptance: two independent humans can play and restart in the same private world;
solo-specific behavior has a documented safe multiplayer policy.

## M6 — audit the existing game before expanding it

Priority: before solo redesigns or backports. Depends on a usable M1 controller loop.

- [ ] M6-01 Inventory playable skills, quests, combat systems, bosses and activities, with actual gameplay evidence.
- [ ] M6-02 Audit Dungeoneering: generation, floors, puzzles, rewards, persistence and solo/group dependencies.
- [ ] M6-03 Audit Summoning: acquisition, familiars, combat/skilling effects and controller interactions.
- [ ] M6-04 Classify MMO-dependent content as already solo, scalable, requiring companions, redesignable or deferred.
- [ ] M6-05 Audit drops, shops, travel and progression bottlenecks that assume trading or many humans.
- [ ] M6-06 Audit the upstream bot framework, activities, navigation, dialogue, saves and default population cost.
- [ ] M6-07 Select a short baseline progression route and document blockers and incomplete upstream behavior.

Deliverables: `SOLO_CONTENT_AUDIT.md`, `DUNGEONEERING_AUDIT.md`, `SUMMONING_AUDIT.md`,
`MMO_DEPENDENCY_AUDIT.md` and `AI_ADVENTURERS.md`.

Acceptance: we can distinguish working content from definitions/stubs and choose
one contained adaptation based on evidence.

## M7 — ship a complete solo gameplay slice

Priority: first content milestone. Depends on M6 and reliable saves.

- [ ] M7-01 Choose one bounded loop: a short quest/activity or gathering → crafting → combat progression route.
- [ ] M7-02 Specify requirements, rewards, solo changes, failure behavior and intended session length.
- [ ] M7-03 Fix its upstream blockers and implement only the necessary solo adaptation behind a toggle.
- [ ] M7-04 Validate all menus, travel, rewards, combat, inventory and save transitions on controller.
- [ ] M7-05 Playtest the slice from a fresh character/profile through completion and restart.
- [ ] M7-06 Verify its multiplayer policy and document deliberate deviations from the original mechanics.

Acceptance: one complete, enjoyable progression experience is playable on Deck
without developer intervention. Expand from this pattern rather than redesigning all content at once.

## M8 — original graphics and safe asset pipeline

Priority: after core playability; earlier UI artwork belongs in M2. Depends on stable
client/cache versioning and backed-up game data. This does not require a new renderer.

- [ ] M8-01 Decide visual scope: UI identity, selective scenery upgrades or a broader replacement aesthetic; create a small style guide.
- [ ] M8-02 Build a reversible sprite export/import workflow and prove one original panel/icon in-game.
- [ ] M8-03 Catalogue cache formats, tooling gaps and ID allocation; keep original asset sources and manifests in the project.
- [ ] M8-04 Prove one custom texture/terrain treatment and one static model through a tested conversion path.
- [ ] M8-05 Validate model scale, rotations, placement, collision definitions and both supported render paths.
- [ ] M8-06 Build one small coherent demonstration area with a few original assets and controller-readable composition.
- [ ] M8-07 Investigate animation/rig import separately; prove one animated asset before committing to custom creatures/characters.
- [ ] M8-08 Add deterministic cache patch/build/version checks and preserve an untouched recovery copy.
- [ ] M8-09 Record provenance and permitted distribution for every shipped original/imported asset.

Acceptance: original sources can reproducibly produce a visually coherent in-game
sample, and reverting the asset patch restores the working baseline. Full world replacement and shader work require a separate scope decision.

## M9 — a small persistent living world

Priority: after M5 compatibility and M6 bot audit. Depends on M4 performance budgets.

- [ ] M9-01 Reuse the upstream bot framework; document what must be extended rather than create a parallel AI engine.
- [ ] M9-02 Persist a small named pool with appearances, skills, inventories and activity preferences.
- [ ] M9-03 Prove one/two activities around Lumbridge/Draynor, including travel and banking.
- [ ] M9-04 Add a population director with active-zone budgets, schedules, stuck recovery and a clean enable/disable setting.
- [ ] M9-05 Add restrained contextual chat and presence without external model/network dependencies for normal offline play.
- [ ] M9-06 Verify restart persistence and behavior with two human players.
- [ ] M9-07 Benchmark several population sizes on Deck and set conservative defaults.

Acceptance: a small recognisable population survives restarts, performs real activities,
and makes the world feel inhabited within the agreed tick/memory budget. Economy participation is a separate milestone.

## M10 — believable offline economy

Priority: after progression/bot audits. Depends on reliable world saves and multiplayer ownership policy.

- [ ] M10-01 Research historical 2010–2012 price data; document coverage, gaps, provenance and usable snapshot rights.
- [ ] M10-02 Define a baseline price dataset and explicitly label approximations where evidence is missing.
- [ ] M10-03 Design bounded local liquidity, trade settlement, supply/demand and anti-exploit rules before implementing a GE simulation.
- [ ] M10-04 Prove a small item basket with deterministic simulations and save/reload tests.
- [ ] M10-05 Expose simple economy controls and explainable prices, with a reversible baseline mode.
- [ ] M10-06 Integrate limited bot trade/supply only after the base model is stable.
- [ ] M10-07 Playtest progression costs, resource availability and co-op behavior over repeated sessions.

Deliverable: `GE_HISTORICAL_DATA.md` and a documented economy model.

Acceptance: players can obtain/trade essential supplies offline without unexplained
price explosions or progression exploits; world economy state persists and remains tunable.

## M11 — one curated OSRS-style addition

Priority: after a stable solo loop and asset/content pipeline. Depends on M6–M8;
M10 is needed only if the chosen content depends on simulated trading.

- [ ] M11-01 Choose a small monster, quest/mechanic or skilling addition; avoid raids/new continents as the first import.
- [ ] M11-02 Write a manifest: references, requirements, XP, timing, formulas, drops, state, assets and solo deviations.
- [ ] M11-03 Implement behavior for the pre-EoC ruleset using compatible, appropriately licensed references.
- [ ] M11-04 Adapt presentation to the chosen 2010–2011 visual language and validate controller flows.
- [ ] M11-05 Test deterministic mechanics and probability tables with appropriate statistical bounds.
- [ ] M11-06 Playtest access, rewards, saves and private co-op behavior; keep the addition independently disableable.

Acceptance: one complete, documented addition proves the process for later curated
content. Larger candidates such as Motherlode Mine, rooftop agility or minigame adaptations are chosen individually afterwards.

## M12 — polished private host/join

Priority: secondary to solo quality. Depends on M5 and tested lifecycle/persistence.

- [ ] M12-01 Add explicit Continue Solo, Host Private World and Join Private World flows.
- [ ] M12-02 Make world ownership and guest character persistence clear in the UI.
- [ ] M12-03 Provide a simple trusted-friends connection workflow and actionable connection errors.
- [ ] M12-04 Handle guest disconnect, host Save & Quit and incompatible feature/protocol versions.
- [ ] M12-05 Disable or adapt solo pause/suspend behavior while guests are connected.
- [ ] M12-06 Test several sessions with independent saves and one abrupt disconnect.

Acceptance: a small group can reliably play a private hosted world without public-server infrastructure or ambiguous save ownership.

## M13 — reproducible packaging and release readiness

Priority: prototype packaging can begin after M4; release gates apply to the features
chosen for that release, not every optional future milestone.

- [ ] M13-01 Define an initial release scope and freeze its required feature set.
- [ ] M13-02 Audit code/dependency/native-library licences and retain required notices.
- [ ] M13-03 Package Linux/Deck runtime and launcher reproducibly, with game data supplied separately where required.
- [ ] M13-04 Test clean-machine install, fully offline play after setup and Steam library integration.
- [ ] M13-05 Add versioned upgrades, save backups/migrations and an explicit rollback path.
- [ ] M13-06 Run the full release acceptance matrix: controls, saves, content slice, graphics presets, suspend and hosting if included.
- [ ] M13-07 Document limitations, troubleshooting, changelog and recovery instructions.
- [ ] M13-08 Consider Windows only after the Linux/Deck release path is dependable.

Acceptance: another person can install, launch, play, save, update and recover the
selected release without the development workspace or undocumented setup steps.

## Decisions to discuss before widening scope

1. Keep direct movement optional, or make it the eventual default after more acceptance?
2. Which core interfaces are essential for the first mouse-free release?
3. Is a compact radial menu useful, or are lists and quick slots clearer?
4. What UI/art style should SoloScape adopt, and how much original world art is worth doing?
5. What is the first complete solo gameplay slice: quest route, skilling loop or Dungeoneering polish?
6. Should multiplayer remain compatibility-only until the solo release, or be part of that release?
7. How many AI adventurers improve atmosphere without hurting Deck performance?
8. What minimum economy solves solo availability before a richer GE model is justified?
9. What constitutes acceptable pause/suspend behavior with active local simulation?
10. What specifically belongs in the first distributable build versus later expansions?

## Proposed next working queue

1. Physically accept the adventure UI: toggles, real quest progress, combat/prayer/spells, source-to-target use/cancel, remapping and Settings → Game Settings → B ancestry.
2. Fix reproducible awkward transitions and accessibility/scroll issues; validate reconnect and changed-source focus on actual input.
3. Complete actual-map Cook’s Assistant and Rune Mysteries travel, gates, mill/tower floors and save/restart. Preserve the existing earned-progression fixture.
4. Measure Deck frame times, loading, memory, battery and suspend/resume against a repeatable route; select measured fixes.
5. Add safe orphan-owned-session recovery and controller-only launcher name entry, then verify install/update/recovery on a fresh machine.
6. Audit redistribution licences/dependencies and build a source-compatible Linux/Deck delivery path.
7. Choose the first fully accepted solo gameplay slice before approving broader art/AI/economy/backport systems.

Keep implemented preparation separate from physical acceptance. ROADMAP.md is the proposed backlog; the adventure task list records this approved batch.
