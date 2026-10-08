# SoloScape — combined morning / completion report

8 October 2026. This combines the two earlier controller sprints and the larger approved console-alpha milestone. All implementation batches are committed and pushed to [overnight/controller-sprint](https://github.com/kannibalk1w1/SoloScape/tree/overnight/controller-sprint). Public main remains at the earlier radial prototype. Your original running game, characters, cache and world were preserved. Private validation servers used disposable worlds, a separate port and virtual display.

The earlier combined report is preserved in [MORNING_REPORT_CONTROLLER_SPRINTS.md](MORNING_REPORT_CONTROLLER_SPRINTS.md); the first sprint also has its own [archive](MORNING_REPORT_SPRINT_1.md). This document supersedes their current-state instructions.

## Current state for ChatGPT discussion

SoloScape is a playable, single-player-first revision-634 RuneScape project, implemented as reproducible patches over pinned 2011Scape/Void server and RuneLite-style client sources. It targets a pre-EoC 2010–2011 console-style experience with native controller controls and eventual Steam Deck support. Native tile simulation, collision, combat requirements and inventory transactions remain authoritative. Proprietary cache/assets, account data, credentials, runtimes and built jars stay outside the public source repository.

The owner has physically confirmed local launch, controller camera, movement feedback, improved aiming/interaction and that optional direct movement feels good. The newer custom interfaces and profile lifecycle have automated evidence; they still need physical acceptance. There is no packaged release, measured Deck performance budget, full content audit, AI population, solo-economy redesign or complete original graphics replacement yet. Contributions remain maintainer-directed, with agreed scope and owner-controlled merges.

The project now has a graphical launcher and isolated independent world profiles, reversible custom controller screens, broad control configuration, server compatibility negotiation, reliable backup recovery, and repeatable native gameplay/save validation. Read [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) and [ROADMAP.md](ROADMAP.md) alongside this report when discussing direction in ChatGPT.

## Work delivered across all three batches

| Area | Earlier two sprints | Larger alpha |
|---|---|---|
| World input | Native camera, destination/direct movement, movement/target overlays, LT aim, cycling, X menus, loot and B cancel; exception recovery and cheaper idle snapshots | Eight remappable actions, overlap rejection, neutral rearming, Xbox/PlayStation/Deck presets and configurable direct-run threshold |
| Native interface flows | Inventory/dialogue; bank/shop quantities, search and scrolling; equipment/prayer/spells and selection handoffs | Reusable custom presentation and four independent inventory/equipment/bank/shop toggles; names/quantities/native actions, worn items/bonus text, confirmation and mouse coexistence |
| Wheels and production | Sixteen-tab Home wheel; eight explicit food/potion/prayer/spell quick slots; common Make amount, smithing/tanning/silver/jewellery navigation | Clear quick-slot wording; preserved native eligibility/selection; native special-attack investigation |
| Readability | Scalable overlays, Xbox/PlayStation labels, keyboard, guide and three menu bindings | Canvas-fitted text-first grids, selected-item action sidebar, visible-window paging and native game/examine feedback |
| Saves | Build fingerprints and retained logs; manual owned-process launch/shutdown | Independent profile/world generations, metadata, private authentication/client home, versioned verified backups, atomic restore, damaged-manifest recovery and stopped-world-copy import |
| Application | Doctor and development launcher | Swing New/Continue launcher, progress, diagnostics, persisted local port, backups/restore and owned graceful Save & Quit |
| Server lifecycle | Explicit matched-server opt-in, directional timeout/cancel gates | Loopback default, reload-stable environment ownership, atomic character/exchange writes, offer-counter crash recovery, per-session nonce capability negotiation and long-input-gap guards |
| Gameplay evidence | Unit/renderer checks and limited known owner acceptance | Level-one native fishing→cooking→equipment→combat→food→save/load fixture; private fully rendered native New→Continue with verified capabilities and four checked backups |
| Delivery/review | Patches through client 0014/server 0003, bounded actual Claude reviews | Client patches 0015–0019/server 0004–0008, additional actual Claude foundation/save/panel/follow-up audits, implementation fixes and full exported-stack verification |

## How to try this build

The current checkout already has matched client/server jars. Do not stop another game merely to inspect the launcher:

```bash
./scripts/launcher.sh
```

If another local world occupies 43594, choose an unused port in **Launcher Settings** before starting an independent profile. New Character creates an independent world; it does not migrate your existing character. Continue uses that profile's save generation. Save & Quit waits for the owned server's normal save hooks and verifies its backup. Each profile has a private client home, so enable **SoloScape Controller** inside a new profile as needed.

Custom Inventory, Equipment, Bank and Shop each default off in the plugin settings; enable them independently to test and disable for native fallback. Direct Movement and SoloScape Server Features remain optional; extension packets additionally require the current server's capability acknowledgement. Home and Quick wheels remain separate. D-pad focuses items/pages, LB/RB switches panes, A invokes the native primary action and X opens alternatives. Drop/Destroy needs a second separate press on the same unchanged chosen action. Quick wheel X assigns and Y clears. Configurable hints currently name logical actions; consult bindings after remapping.

New Character's text fields currently use a desktop keyboard. Profile selection and launcher focus support SDL controller navigation. The desktop development path remains available with `./scripts/dev-run.sh --no-build`; it uses the legacy world, unlike the isolated profile launcher.

Fresh clones must use the development branch, pinned-source/runtime instructions in [README-SOLOSCAPE.md](../README-SOLOSCAPE.md), and [CACHE_SETUP.md](CACHE_SETUP.md). The cache guide includes the upstream-maintainer download source, archive/extraction instructions and recorded checksum. Launching the game does not fetch the server cache. Neither caches nor jars are published in this repository.

An independent copy of a stopped world's saves can be imported with `python3 scripts/import-profile.py /path/to/stopped-world-copy --label "My character" --account "AccountName"`. All accounts and exchange files are retained; password hashes are unchanged. Login is manual unless `--remember-password` privately captures the existing password. Import refuses original upstream data and active profile storage. See [save validation/migration instructions](ALPHA_SAVE_VALIDATION.md).

## Final validation evidence

| Check | Result |
|---|---|
| Client unit cases | 139, zero failures/errors; one existing optional SDL virtual-controller skip |
| Root tooling/profile/launcher cases | 37, all passing; disposable fixtures only |
| Config cases | 74, all passing |
| Networking cases | 249, all passing |
| Selected engine cases | 49, all passing: saves, movement, cancellation and file storage |
| Native content progression | One complete isolated route passing; native handlers and native save/reload, no seeded XP |
| Native graphical profile harness | New and Continue reach rendered world and verified capabilities; normal shutdown, save/reload fields and four verified backups checked |
| Original mutable-world comparison | Unchanged file size/mtime fingerprints before/after private native sessions |
| Build/export checks | Matched client/server shadow jars; full client 78-file/server 28-file exported stacks; fresh/upgrade/reverse/idempotent patch verification |
| Tooling hygiene | Python compile, shellcheck and git whitespace checks pass |

The native content fixture starts level one (native Constitution ten), seeds only a small net and bronze sword, catches shrimp, cooks it, equips the sword, defeats a chicken, receives attack XP and bones, eats food, saves and reloads. It calls ordinary native handlers on isolated content fixtures. It does not prove controller travel around the complete map.

The graphical harness uses its own profiles, Xvfb display :197 and port 43595. It starts the actual server/client, follows ordinary login and fresh Continue, waits for a rendered world and current-session capability acknowledgement, then exits through normal server saving. See [save evidence](ALPHA_SAVE_VALIDATION.md), [controls/connection evidence](ALPHA_CONTROLS_AND_CONNECTION.md), [launcher](ALPHA_LAUNCHER.md) and [custom screens](ALPHA_CUSTOM_SCREENS.md). Renderer fixture previews are labelled; they are not physical gameplay screenshots.

## Claude reviews and changes made

Actual Claude reviewed the foundation, save implementation, custom screens and final fixes in the existing Orca terminal. These were bounded static audits, not claims of live gameplay testing. Review files:

- [Foundation audit](CLAUDE_ALPHA_FOUNDATION_AUDIT.md)
- [Save review](CLAUDE_ALPHA_SAVE_REVIEW.md)
- [Custom panel review](CLAUDE_ALPHA_PANEL_REVIEW.md)
- [Final follow-up](CLAUDE_ALPHA_FINAL_FOLLOWUP.md)

The important panel finding was that a blocked Drop confirmation closed its chosen context, allowing the next A to run the primary action. This is fixed with exact gamepad and mouse→gamepad regression tests. Other changes include identity-based scroll continuation, explicit visible-page labels, consumed hover, labelled game feedback, atomic exchange writes, monotonic offer-ID recovery, oversized stdio request draining, retained damaged metadata, and hidden import staging before publication. Claude's final follow-up found no blockers; subsequent low recovery/import notes were also addressed.

## Limits and next task list

- Physical controller and Steam Deck/Gaming Mode acceptance remain required. Suspend/reconnect guards have automated evidence, not a completed hardware campaign.
- Custom screens are text-first; item artwork, tooltip polish, minimum-scale equipment readability and stale-pointer feedback need refinement. Native hidden bank rows require scrolling; visible-page counts cover the current rendered window.
- True solo world pause remains unexposed. The [contained investigation](ALPHA_SOLO_PAUSE_INVESTIGATION.md) specifies simulation-clock separation, continued network/save handling, discarded queued actions, guest resume and shutdown tests. Menus do not freeze the world.
- Profile backups and old generations are retained. Storage size/count are visible, but pruning controls are deferred. Atomic exchange files do not form a multi-file transaction; consistent whole-world backups require a stopped world. Historical claim-only offer IDs remain an edge case for old snapshots.
- Import uses a CLI and requires an independent stopped-world copy. New-character text entry is desktop-based; no forgotten-password reset is provided.
- Eight logical bindings work, but overlay glyph text does not yet automatically substitute every remapped physical button. Special attack is available through fresh native Combat controls; no universal quick shortcut is claimed.
- Broad quest/skill, Summoning/Dungeoneering, private co-op, economy/bots, packaging and original art remain proposed roadmap work.

Next: accept the profile/custom-screen build on a physical controller, record concrete issues, improve readability and button-label discovery, then measure Deck performance and lifecycle behavior. The full proposed backlog remains in [ROADMAP.md](ROADMAP.md); the approved alpha implementation checklist is [CONSOLE_ALPHA_TASKS.md](CONSOLE_ALPHA_TASKS.md).
