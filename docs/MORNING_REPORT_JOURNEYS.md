# SoloScape — combined morning / completion report

10 October 2026. **Approved journeys/recovery sprint completed.** This combines the original two controller sprints, console alpha, cohesive menu/session milestone, controller-first adventure sprint and controller journeys/recovery work. Development is on [overnight/controller-sprint](https://github.com/kannibalk1w1/SoloScape/tree/overnight/controller-sprint); local branch is `soloscape/bootstrap`. Public main remains `07e789bfa05f48989698d7200577a331e47183ab`.

Original worlds/cache were preserved; verification uses disposable storage and private displays. Earlier reports are archived: [controller sprints](MORNING_REPORT_CONTROLLER_SPRINTS.md), [console alpha](MORNING_REPORT_CONSOLE_ALPHA.md), [cohesive session](MORNING_REPORT_COHESIVE_SESSION.md), [adventure](MORNING_REPORT_ADVENTURE.md). [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) is the self-contained discussion handoff and [ROADMAP.md](ROADMAP.md) remains the full proposed backlog, not blanket authorization for future systems.

## Current state for ChatGPT discussion

SoloScape is a playable local, single-player-first revision-634 RuneScape project using reproducible patches over pinned 2011Scape/Void server and RuneLite-style client sources. The intended experience is pre-EoC RuneScape with console controls and eventual Steam Deck support. The server retains authority over movement, collision, combat, progression and transactions. Cache/assets, credentials, saves, runtimes and jars are excluded from Git. Contributions remain maintainer-directed.

The owner has confirmed local launch, camera, movement feedback, improved walking/aiming/interaction and optional direct movement. Current adventure screens, remapping, first-run setup, source targeting and the new launcher keyboard need physical controller acceptance. There is no packaged release or established Deck performance budget. Original world graphics, AI adventurers, solo economy, exposed world pause, selected content backports and private multiplayer remain proposed future scope.

## Combined delivery

| Area | Earlier delivered work | Journeys additions |
| --- | --- | --- |
| World controls | SDL input, camera-relative walking/direct toggle, tile/target feedback, LT aim, target cycling, normal action menus, loot and B cancellation | Native quest-route verification retains ordinary collision/interaction rules |
| Menus | Home radial, inventory/dialogue, bank/shop quantities/search, text/amount entry, equipment, prayer/spells, production, contextual B ancestry and right-stick scrolling | Reproduced and fixed stale Home ancestry after spell selection and tab timeout; later directly opened inventory B returns to world |
| Presentation | Independently reversible inventory/equipment/bank/shop/journal/skills/combat/prayer/spellbook surfaces, mouse/trackpad support, native icons/names/details and destructive confirmation | Actual Swing name-entry keyboard with form-preserving B, Y advance, Shift, desktop coexistence, account filtering and inline errors |
| Setup | Eight bindings, presets/glyphs, deadzone/inversion/scale/run threshold, Home Controller Settings, first-run setup and Game Settings parent return | Launcher character creation can be completed through the entry adapter without typing on a physical keyboard |
| Targeting | Explicit quick slots, validated native special-attack binding, source/target feedback and identity-checked source return | Navigation history clears at selection handoff and independent inventory entry; existing return/scroll coverage remains green |
| Sessions/saves | Isolated worlds/generations, credentials, native New/Continue, verified backups/restore/import, previewed retention, build-only Prepare and inherited profile/archive guards | Durable session records; verified pidfd recovery; honest recovered snapshots; restore generation guard; explicit ended-record archival; backend SIGTERM/SIGHUP waits for normal hooks |
| Content | Earned gather/mill/Cook/shop/bank/fish/cook/combat/food/save fixture, shared-store fix, actual Lumbridge walking, full Restless Ghost and castle/banking routes | Full actual-map Cook and Rune Mysteries routes, native rewards and save/reload pass |
| Delivery | Pinned setup/cache instructions, patch export/verification, matched jars/stamp and repeated actual Claude review | New launcher/recovery harnesses, further real Claude findings reproduced/fixed, combined report and updated task/backlog evidence |

## How to try the new behavior

After Save & Quit of an existing owned world, run `./scripts/prepare-build.sh`, then `./scripts/launcher.sh`. Prepare builds/verifies the matched pair without starting a world. New Character and Continue use isolated profile worlds; they do not silently import the legacy development world. The legacy path remains `./scripts/dev-run.sh --no-build`. Never replace archives underneath a manually launched JVM.

**Character naming:** New Character opens the local keyboard. D-pad chooses keys; A types; X deletes; Y advances; Shift changes case; B first leaves the keyboard and preserves the form. LB/RB moves between form controls. Desktop typing and pointer buttons coexist. A failed backend create keeps the values and shows an inline message. The native in-game entry types retain their prior validation.

**Recovery:** after an abnormal launcher death, an affected character offers Recover Session instead of Continue. It checks boot, PID start, same user, unique session/role environment, exact archive argv, isolated save path and both inherited guards before using a pidfd to send SIGTERM. It stops the client before the server, waits for normal hooks and refuses live original launchers, changed identities and suspended processes. It never adopts manual/unrelated worlds or uses a forced-kill save timeout.

A verified recovered snapshot is labelled `after-recovered-shutdown`; earlier backups remain and **clean shutdown is unconfirmed**. Save errors or unfinished save files retain the record for inspection. An ended damaged world can explicitly Archive ended record, which preserves the record and enables Restore Backup. Restore refuses an outstanding record before switching generations. [Launcher guide](ALPHA_LAUNCHER.md) explains these flows.

**Gameplay settings:** Home Settings opens controller preferences and Game Settings opens native settings as a child. Independent custom screen toggles default off for adventure screens. Native actions, IDs, state and permission checks remain authoritative. Special-attack quick assignment and ordinary item/spell source return are described in the [adventure UI](ADVENTURE_UI.md), [setup](ADVENTURE_CONTROLLER_SETTINGS.md) and [targeting](ADVENTURE_TARGETING.md) guides.

## Current verification

| Check | Evidence |
| --- | --- |
| Client test/shadow jar | 176 cases; zero failures/errors; one existing optional SDL skip |
| Root tooling/profile/lifecycle/recovery | 62 passing disposable cases, including real pidfds/flocks around simulated JVMs |
| Menu regression | Two added cases fail before the ancestry fix and pass after it; full client suite stays green |
| Actual Swing launcher | Native entry adapter/backend create, cancel/preserve, account-filter and inline-error probe passes on its own private display |
| Selected native-cache game slice | 20 selected cases pass; zero failures/errors/skips; server shadow build passes |
| Exact exported stacks | 99 client files through patch 0028; 33 server files through patch 0011; matched jars/stamp verify |
| Native orphan server | Real server recovered through verified pidfd identity/inherited guards; recovered snapshot validated; original mutable-path fingerprints unchanged |
| Native New/Continue/adventure | Repeated graphical sessions pass native save/reload, four verified backups and pre-ready cancellation preserving every saved-world file |

[Journeys validation](CONTROLLER_JOURNEYS_VALIDATION.md) records the methods and reproduction commands. The native recovery probe covers a real server with no player/client claim; the separate native profile smoke covers graphical player New/Continue, capabilities, save/reload, settings adoption and early startup cancellation. Historical broader alpha results (74 config, 249 networking, 49 selected engine cases) have not been rerun in this checkpoint.

Server/content tests use native objects/NPCs/cache and normal instructions. Their test characters start in the quest-giver scenes. Native stairs/ladders change scene normally. Door helpers wait for the object change and walking waits for a native border delay before issuing another instruction. No fixture scenery, reward items, quest state, collision overrides or teleport commands make the new routes pass. These are headless server/content checks, not a physical controller playthrough.

## Actual Claude review and fixes

Actual Claude performed four bounded static reviews in the existing Orca terminal. No current usage-window percentage is inferred. The reviews did not run gameplay or establish hardware acceptance.

- [Recovery design](CLAUDE_JOURNEYS_DESIGN_REVIEW.md): identity/guard/ownership design and reuse of native entry logic.
- [Implementation](CLAUDE_JOURNEYS_IMPLEMENTATION_REVIEW.md): finished-worker ownership, restore generation protection and exact argv/save-path identity findings were fixed.
- [Menu/follow-up](CLAUDE_JOURNEYS_MENU_REVIEW.md): stale Home ancestry was reproduced in two failing tests and fixed; other-profile ownership listing was fixed and tested.
- [Native recovery probe](CLAUDE_JOURNEYS_RECOVERY_PROBE_REVIEW.md): early-parent-death cleanup now uses the durable record, cleanup errors preserve the original failure, and another legitimate shared archive holder cannot invalidate this probe's profile result.

Previous adventure/session review reports remain linked from the archived reports. Native display scope and original-world preservation are recorded separately from static review.

## Delivery and remaining acceptance

`1f219f2` commits/pushes controller character entry, ownership-checked recovery, launcher guidance and the reproduced menu fix. `03fa279` commits/pushes the full native quest routes and final 20-case content slice. The final native probes, Claude follow-up and documentation are committed separately in Git history. Development pushes remain on `overnight/controller-sprint`; public main is preserved.

Remaining work, in practical order:

1. Physically test naming, independent inventory B, Settings → Game Settings → B, scrolling/large text, targeting/use/cancel and mouse/controller takeover. Keep concrete awkward cases for focused fixes.
2. Play the accepted quest/gather/commerce/combat slice from a fresh profile and restart; verify completed journal rendering and tutorial/first-run on actual hardware.
3. Measure Steam Deck/Gaming Mode frame times, loading, memory, battery/thermals and suspend/resume against a repeatable route.
4. Verify fresh-machine setup/update/recovery and audit redistribution/dependency licences before packaging.
5. Choose the first fully accepted solo gameplay slice before authorizing broader art/AI/economy/backport/multiplayer systems.

Recovered snapshot validity does not certify every native save-hook outcome. Real orphan-client recovery, every crash timing, physical SDL timer behavior, exhaustive upstream content and long-duration performance remain unclaimed. The proposed full project task list is in [ROADMAP.md](ROADMAP.md).
