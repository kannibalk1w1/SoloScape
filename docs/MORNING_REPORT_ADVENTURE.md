# SoloScape — combined morning / completion report

9 October 2026. This combines both original controller sprints, the console alpha, cohesive menu/session work and the approved controller-first adventure sprint. Development is on [overnight/controller-sprint](https://github.com/kannibalk1w1/SoloScape/tree/overnight/controller-sprint). Public main remains at `07e789bfa05f48989698d7200577a331e47183ab`. Original player data and cache were preserved; gameplay verification used disposable storage and an owned private virtual display.

Earlier reports are archived: [controller sprints](MORNING_REPORT_CONTROLLER_SPRINTS.md), [console alpha](MORNING_REPORT_CONSOLE_ALPHA.md), [cohesive session](MORNING_REPORT_COHESIVE_SESSION.md). This report and [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) describe current state. [ROADMAP.md](ROADMAP.md) is the full proposed task backlog, not blanket approval to implement every future system.

## Current state for discussion

SoloScape is a playable local, single-player-first revision-634 RuneScape project, delivered as reproducible patches over pinned 2011Scape/Void server and RuneLite-style client sources. The intended experience is pre-EoC RuneScape with console controls and eventual Steam Deck support. World tiles, collision, combat and transactions retain native server rules. Game assets, saves, credentials, runtimes and jars are excluded from the public source repository. Contributions remain maintainer-directed.

The owner has confirmed local launch, camera, movement feedback, improved walking/aiming/interaction and optional direct movement. Latest adventure UI, source targeting and setup need physical controller acceptance. There is no packaged release or established Deck performance budget. Complete upstream content, AI adventurers, solo-economy changes, exposed world pause and original world graphics remain future scope.

## Combined delivery

| Area | Earlier delivered work | Adventure sprint additions |
| --- | --- | --- |
| Movement and world | SDL input, camera-relative walking/direct toggle, movement overlays, aim/target cycling, native action menus, loot and cancellation | Source/target phase feedback, fresh source identity on return; quick casts retain world control |
| Interfaces | Inventory/dialogue, bank/shop quantities/search, text/amount entry, equipment, prayer/spells and production; Home radial, contextual B ancestry, right-stick scrolling | Optional journal/quests, skills, combat, prayer and spellbook surfaces with readable native detail/state |
| Presentation | Optional custom inventory/equipment/bank/shop, mouse/trackpad support, native names/icons and destructive confirmation | Shared readable styling, detail wrapping, pointer tooltips/page hints, bounded weak reuse of native sprite-cache artwork |
| Controller setup | Eight bindings, presets, glyphs, deadzone/inversion/scale and run threshold | Home Controller Settings and first-run setup; swap occupied mappings; Game Settings child/B return; validated native special-attack quick binding |
| Sessions and saves | Graphical New/Continue, isolated worlds/generations, verified backups/restore/import, previewed retention and matched build-only Prepare | Owned JVMs inherit profile/archive locks after launcher death; restart port check handles TCP TIME_WAIT while rejecting listeners |
| Content | Earned Cook/shop/mill/bank/fishing/cooking/combat/food/save fixture; actual Lumbridge walking; shared-store validation fix | Full actual-map Restless Ghost completion/save; actual castle Cook/Rune starts, doors/north stairs, upstairs talisman banking/save |
| Delivery | Pinned patch reproduction, setup/cache instructions, checks and actual Claude reviews | Further bounded actual Claude review/fixes, isolated native adventure validation and updated combined report/handoff/backlog |

## Adventure behavior and how to try it

**Screens:** enable Custom quest journal, Custom skills screen, Custom combat screen, Custom prayer screen or Custom spellbook screen in SoloScape Controller preferences. Each is independent and defaults off. Existing inventory/equipment/bank/shop toggles remain. Native IDs, actions, quantities, eligibility checks and mouse interaction are retained; read-only journal/skill detail offers no fabricated action. Native UI is available by disabling its custom presentation.

**Native details:** skills show boosted/base levels and XP; journals use loaded visible native objective text. Combat shows selected style, retaliation and special energy/state. Prayer/curse labels, levels and state follow pinned definitions and native masks. Spell labels follow pinned components; Magic/rune requirements come from the same cache information fields the server reads. Staff substitutions, quest/target restrictions, free-to-play membership restrictions and final casting availability remain native checks; the overlay does not calculate every eligibility condition.

**Settings and B:** Home Settings opens controller preferences, including presets, eight bindings, deadzone, run threshold, scale, inversion, glyphs and screen toggles. Game Settings opens native graphics/audio as a child. B returns through preferences → Home → world. First-run completion is explicit; it does not silently enable direct movement or matched-server features. Custom controller settings can be disabled independently. Adoption across ticks no longer cancels the local menu.

**Selection:** item/spell selections originating in an ordinary panel remember the source tab and identity. Use/cancel can restore it once with fresh item/quantity checks. Quick casts stay in world. New selections, external modals, focus loss/logout and expired or changed sources discard obsolete return state. Focus restoration stores identity, never invokable actions.

**Special quick action:** focus the native combat Special attack Use control, open the quick wheel and assign it as usual. Dispatch requires the exact supported component and fresh native permission. The server still owns energy and weapon behavior.

**Owned lifecycle:** launcher/profile/build guards survive abnormal launcher death through inherited JVM file descriptors. They remain held while owned children can save or load classes. No clean backup is claimed for a killed launcher; an orphan-session recovery UI remains future work. Manually launched JVMs remain outside ownership protection.

Guides: [adventure UI](ADVENTURE_UI.md), [controller setup](ADVENTURE_CONTROLLER_SETTINGS.md), [selection return](ADVENTURE_TARGETING.md), [session guards](ADVENTURE_SESSION_GUARDS.md), [route audit](ADVENTURE_ROUTE_AUDIT.md), [native evidence](ADVENTURE_NATIVE_VALIDATION.md).

## Validation

| Check | Latest result and scope |
| --- | --- |
| Client suite / shadow jar | 172 cases, zero failures/errors; one existing optional SDL skip |
| Root tooling/profile/lifecycle/socket suite | 47 cases, all passing; includes launcher-kill lock inheritance, live-listener rejection and normal shutdown restart |
| Selected game slice / shadow jar | 18 cases, all passing: existing quest/recovery logic, shops/progression/session and two actual-map routes; strengthened saves reran the same two route cases |
| Reproducible patch export | Entire ordered stack reproduces exactly: 98 client files and 32 server files; fresh/upgrade/reverse/idempotence checks pass |
| Matched pair | Both archives build and the jar/base/patch fingerprint stamp verifies |
| Native integration | New/Continue, settings adoption/config reversal/B, settled same-client relogin with fresh capability nonce, four verified backups, save fields and whole-world startup cancellation pass; original mutable-path fingerprints unchanged |
| Historical broader modules | Alpha recorded 74 config, 249 networking and 49 selected engine cases; these are historical results, not newly rerun claims |

Private complete-session totals were **66.282 / 63.783 seconds**, including the adventure probe and save/shutdown. Baseline render-interval p95 was **29.34 / 24.44 ms**; journal-state p95 **32.68 / 31.48 ms**. Full memory/sample/interval values and actual captures are in [native evidence](ADVENTURE_NATIVE_VALIDATION.md).

Hardware limits remain explicit. Native desktop measurements use Xvfb/software rendering, with different native states for baseline and journal. They are not a controlled GPU A/B or Deck benchmark. Heap/RSS from short sessions does not establish a leak or long-term memory budget. Real Settings Gateway/openHomeTab and synthetic B input are exercised; the SDL-driven onClientTick path and first-run physical discovery are not accepted by this harness.

## Actual Claude review

Actual Claude reviewed successive bounded batches in the existing Orca terminal via the orca-cli skill. Foundation native fallback/artwork, combat/session guards, settings adoption and selection-return issues were repaired. Settings follow-up found no blockers; native Settings ownership and reentrant reset were also corrected. Final spell/route/harness review and follow-up found no correctness blockers, with private-display ownership, honest settings-probe scope and logout label validation addressed. These are static audits, not gameplay or hardware acceptance; no current Claude quota percentage is inferred.

Reports: [foundation](CLAUDE_ADVENTURE_UI_FOUNDATION.md), [foundation follow-up](CLAUDE_ADVENTURE_UI_FOLLOWUP.md), [combat/session](CLAUDE_ADVENTURE_COMBAT_SESSION.md), [settings/targeting](CLAUDE_ADVENTURE_SETTINGS_TARGETING.md), [settings follow-up](CLAUDE_ADVENTURE_SETTINGS_FOLLOWUP.md), [final review](CLAUDE_ADVENTURE_FINAL_REVIEW.md), [final follow-up](CLAUDE_ADVENTURE_FINAL_FOLLOWUP.md). Their descriptions reflect code at review time; later native clicks and logout settling are explained in the native evidence.

## Commits and next launch

Verified implementation batches already on the development branch:

- `d1d67f6`: UI foundation, quest journal/skills and artwork reuse.
- `82c24bf`: combat/prayer/spells state, native special quick binding and durable session guards.
- `7cf06ef`: controller preferences and first-run setup.
- `6ff8cce`: source/target return and settings review fixes.
- `4c51e14`: native spell requirements, actual-map adventure/save audit, restart probe and final static reviews.
- Subsequent native validation/documentation commits finish this report; Git history records their exact hashes.

After Save & Quit of an existing owned session:

```bash
./scripts/prepare-build.sh
./scripts/launcher.sh
```

Prepare applies tracked patches and builds/verifies the matched pair without launching a world. Continue selects an isolated profile world; it does not silently import the old development world. The legacy development path remains `./scripts/dev-run.sh --no-build`. Do not update archives beneath a manually launched game.

Cache acquisition/extraction is in [CACHE_SETUP.md](CACHE_SETUP.md), using the pinned upstream maintainer’s linked compatible archive. It is not an official Jagex distribution. Launching the client downloads from the local server after that server cache is installed; it cannot supply the missing server archive.

## Remaining work

The [adventure task list](ADVENTURE_SPRINT_TASKS.md) separates delivered preparation from acceptance. Next: physical adventure/setup/targeting/B/scroll and special-binding acceptance; full actual-map Cook’s Assistant/Rune Mysteries travel and save restart; then repeatable Deck loading/frame/memory/suspend measurements and concrete fixes.

Arbitrary server-modal reopening, niche interfaces, wider native artwork availability, controller-only launcher naming, orphan-session recovery and accessibility remain open. Save generations are retained and can consume space; backup verification scales with history. Exchange files are individually atomic rather than a multi-file transaction. Import remains a stopped-copy CLI. True world pause, packaging/licence audits, broader content and larger art/AI/economy/backport work require later decisions.
