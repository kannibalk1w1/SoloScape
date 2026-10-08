# SoloScape 2011+ — current state and ChatGPT handoff

Updated: 8 October 2026. This document is self-contained: it can be uploaded or
pasted into ChatGPT alongside `ROADMAP.md` without granting access to the repository.
The roadmap is a proposal for discussion, not approval to implement every feature.

## What we are building

SoloScape is a local, single-player-first RuneScape RPG based on revision 634
(December 2010), using the 2011Scape/Void server and its RuneLite-style client.
The intended feel is a 2010–2011 console RuneScape release, with pre-EoC combat,
Summoning/Dungeoneering-era progression, native controller input and Steam Deck UX.
Later ambitions include carefully selected OSRS-style additions, solo adaptations,
a small persistent population of AI adventurers and optional private co-op.
It is not intended to become a public MMO or wholesale modern OSRS clone.

The upstream cache and much of the existing game/content come from the supplied
upstream project. We have not audited the completeness of every quest or skill.
Revision 634 being from the right era does not prove those systems are complete.

## What the user has confirmed

- Local launch and gameplay work.
- Controller camera panning works.
- Ground movement markers work.
- The first walking/aiming controls were difficult; the usability pass improved them.
- The optional direct movement build feels good.

Inventory/dialogue have been implemented and tested in code, but there is no
recorded detailed acceptance pass for every action/layout. The newest X world
menus, loot targeting and B world cancellation are built and tested and still
need an in-game acceptance pass after restarting both client and server.

## Implemented controller controls

| Input | Behavior |
| --- | --- |
| View/Select | Toggle the 16-slot main-tab radial; left stick highlights, A opens, B cancels |
| Start/Menu | Separate eight-slot quick-action wheel; all slots start empty, X assigns the focused supported native action, Y clears that slot |
| Right stick | Native camera yaw/pitch, configurable speed, deadzone and inversion |
| Left stick, destination mode | Camera-relative, collision-checked one-to-three-tile walks |
| Left stick, direct mode | Held eight-way server directional intent; gentle tilt walks, full tilt requests running |
| LT | Aim without issuing new movement |
| LB/RB | Cycle eligible nearby world targets |
| A, world | Invoke the highlighted target's normal default action, including Take for loot |
| X, world | Open the highlighted NPC/object/ground-item's native action list |
| D-pad, world action list | Select an action; A confirms, B backs out |
| B, world without action list | Cancel the normal current approach, walking or interaction |
| Y | Open/focus inventory; Y or B can leave inventory focus |
| D-pad, inventory | Navigate the four-column inventory grid |
| A/X/B, inventory | Default action / item action list / back |
| A/D-pad/B, dialogue | Continue or confirm / choose response / close normal conversation |

The controller plugin itself defaults disabled. **Direct movement** is a separate
checkbox in **SoloScape Controller settings**, defaults off and can be changed
in-game. Turning it off restores the destination controls. Camera and targeting
are native input, not joystick mouse emulation; keyboard/mouse remain usable.

Ground feedback includes a green requested destination/next direct step, a light
blue player tile while moving, and a gold target footprint/action label. Focus
stays stable when the stick rests and the camera rotates. Moving NPCs keep identity;
ground-item identity includes tile/plane, so an identical item elsewhere is distinct.
The latest build cycles every entry on an evaluated pile, including those beyond the three
rendered models, with deterministic tie-breaking for items on the same tile.

Actions use the revision-634 native menu dispatcher and live definitions. Controller
lists are not independent gameplay implementations. Options, identity, location,
quantity/name, visibility and reachability are revalidated as applicable. Menus close
when their contents become stale. Inventory/dialogue take priority over world input.
Buttons dispatch on press edges, while D-pad navigation can repeat.

## Movement and cancellation architecture

The simulation still uses tiles and **600 ms server ticks**. Direct movement changes
how intent reaches the server; it does not introduce free analogue physics or
continuous server positions. There is no client prediction of authoritative movement.
A released stick stops future direct steps at a server update; movement already
confirmed and rendering can finish.

Direct mode sends custom opcode **85**, a three-byte payload containing signed dx,
signed dy (-1..1) and a run request (0/1). Changes send immediately; held input sends
a heartbeat every 200 ms. The server queues only one/two local steps for that tick,
using normal collision, delay, viewport, animation and energy paths. Input expires
when its network receipt is at least 750 ms old, checked on a game tick. The ordinary
run-toggle preference is preserved; energy and equipment restrictions still apply.
A plain directional stop cannot cancel a newer mouse walk or interaction.

With **SoloScape server features** explicitly enabled, B world cancellation uses custom opcode **86**, with no payload or client
position. It clears normal movement/interaction, watch, weak actions and suspension.
After clearing the old action it runs pending walk cleanup once, allowing unmorph
or content exits and preserving any route the callback installs. It respects the
ordinary busy/delay gate; it is not an escape from forced actions such as agility.
The server-features setting defaults off; ordinary cancellation uses native Walk. Direct movement requires both that opt-in and the Direct movement toggle. Dialogue B uses the already-verified ordinary same-tile Walk cancellation path, not opcode 86.

Focus loss, disconnect, UI modes, A, LT, shutdown and mode changes stop direct input.
A native mouse menu action takes over and blocks held direct input until neutral.
The newest B behavior pauses held walking intent so it does not immediately restart.

## Technical baseline

Workspace: `/home/kannibalkiwi/orca/projects/SoloScape` on Linux.
Root branch: `soloscape/bootstrap`.

| Component | Pinned base / runtime |
| --- | --- |
| Server | `2011Scape/game-server`, commit `9f9113559eb686abd917893b5dca16404be07f93`, Kotlin/JDK 21 |
| Active client | `2011Scape/runelite-client`, commit `297bc8a4861755b676855664d32859054779c067`, Java 8 runtime |
| Reference client | `2011Scape/634-client`, commit `b39d45f49a0480f3f200fe3e31ad0798faf163ab` |
| Controller backend | SDL2 via JNA; local SDL 2.32.74 passes native virtual-device tests |
| Installed Java | Project-local JDK 21.0.12.1+1 and JDK 8u504-b01 |
| Local connection | Launcher connects client to `127.0.0.1:43594` |

The root repository owns code patches, scripts and documentation. Upstream
checkouts, downloaded cache, runtime binaries/logs and saves remain ignored.
Thirteen client patches and three server patches reproduce the current modifications.
The launcher applies missing patches before source builds, checks pinned bases,
and refuses conflicting local changes rather than resetting them.

`config/local.env` selects the installed Java executables. The launcher starts
its own server, waits for world readiness, then starts the client. Closing the
client or interrupting the launcher stops only its owned processes gracefully.
A running old client/server does not acquire new code from a rebuilt jar.

The compatible full cache was downloaded with explicit user authorization from
the upstream-linked source and installed in `upstream/game-server/data/cache/`.
It is not part of the source repository. No cache import pipeline for our own
models/textures has been implemented. Existing tools can dump sprites and edit
several cache definitions. The player was wiped once at the user's request;
that was a one-off operation, not launcher behavior.

## Latest build and checks

Both Shadow jars are rebuilt:

- `upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar`
- `upstream/game-server/game/build/libs/void-server-dev.jar`

Current checks pass with zero failures or errors:

- **121 client test cases**, with one SDL virtual-device test
  deliberately skipped in this batch. Native camera,
  pathfinder, widget tests, world-menu input, actual loot tables, NPC options,
  12-item cycling, blocked-pile starvation, cache freshness and encrypted
  directional/cancel packet encoding are covered. Earlier SDL validation passed.
- **247 network tests** and **61 selected engine movement/decoder/cancel tests**, without skips.
- **14 root tooling tests** cover patch application, launcher lifecycle, jar/patch fingerprints, log retention and full-tree patch export.
- Client/server source reproduction matches all **59 / 14** affected files on
  fresh bases, upgrades, sequential reverse application and repeated application.

These establish automated behavior, not Steam Deck performance or complete
physical gameplay acceptance. Some UI closing is mocked in the server cancel tests;
its actual in-game result still needs the new build to be played.

To try the latest code, quit the running game/launcher cleanly and run from the root:

```bash
./scripts/dev-run.sh --no-build
```

This starts both updated processes. Keep the controller plugin enabled and choose
Direct movement and SoloScape server features if desired (only for this patched server). Try X on an NPC with several options, D-pad/A confirmation,
B back/cancel, dropped loot, stacked pile cycling, inventory/dialogue handoff and
ordinary mouse actions. See `docs/CONTROLLER_TESTING.md` for more detailed checks.

## Important gaps

- Confirm real character persistence across a clean restart, not just server startup.
- Bank/shop/deposit-box focus, scrolling, native amounts, tabs/search, a bounded controller keyboard, equipment/prayer/spell focus and native targeting are implemented but still need physical acceptance. Quick actions, common production and Combat/Skills/Quests/selected Settings focus are now implemented. Bank PIN, niche/special interfaces, remaining home tabs, quick special attacks and player/PvP targeting remain pending. Combat/selected-NPC-spell targets defer approach to the server; no client LOS or weapon range simulation is added. The keyboard uses printable ASCII; native physical keyboard input remains available.
- No console launcher, Continue/New Character save UI, backups/restore UI, pause,
  Steam Gaming Mode packaging or suspend/resume behavior has been completed.
- No physical Deck performance/thermal/battery benchmark or two-client/LAN smoke test.
- The upstream server still binds broadly; a narrow loopback-default option is pending.
- No complete audit of content, Dungeoneering, Summoning, bots, bot persistence,
  economy or multiplayer assumptions. Upstream bot support/default bots do not
  constitute our designed living-world system.
- No custom art import pipeline, renderer overhaul, simulated GE, curated content
  backport, or redistributable asset package has been delivered.

## Recommended next steps

1. Accept the newest world action/loot/cancel build and verify a real save restart.
2. Accept bank/shop, quick actions, production and the added tabs; then fix gameplay findings and fill remaining interface gaps.
3. Accept the implemented overlay scaling, glyph labels, optional guide and menu bindings at Deck resolution; broader remapping/presets remain proposed.
4. Build reliable save/launcher lifecycle, then validate it on actual Steam Deck hardware.
5. Verify two independent players before changes to global simulation or solo behavior.
6. Audit existing content, then ship one complete solo gameplay slice.
7. Prove a small original-asset pipeline, persistent AI population and historical-data
   economy in separate bounded experiments before combining them.
8. Add one small curated backport; polish private hosting and packaging afterwards.

## Suggested prompt to accompany this in ChatGPT

> I am building SoloScape, a local single-player-first pre-EoC RuneScape RPG for
> Steam Deck, with optional private co-op and future AI adventurers/curated OSRS
> additions. Below are the current-state handoff and proposed roadmap. Treat user
> confirmations separately from automated tests and proposals separately from
> implemented features. Help me refine scope, milestone order and acceptance criteria.
> Keep the next sprint concrete and playable, preserve existing saves and normal
> RuneScape mechanics, and flag dependencies or decisions that need resolving.
> Do not assume access to my repository or invent upstream content completeness.


## Independent review and follow-up

Claude reviewed the pre-fix build; its full findings are in `CLAUDE_REVIEW.md`.
Client patch 0008 and server patch 0003 now fix B discarding content cleanup (H1),
piles larger than eight items being inaccessible (M2), and a blocked pile hiding
reachable targets (M3). Reachability is cached per geometry for one scan, capped
at eight distinct geometries; every item on an evaluated pile shares the result.
The new build has not yet been accepted in gameplay.

The overnight reliability batch now implements jar/patch fingerprint checks, separate SDL and game-adapter exception handling, reduced idle inventory snapshots and queued-tile dialogue cancellation. Automatic server capability negotiation, border-passage gameplay checks and a complete combat range/line-of-sight policy remain pending. Restart both client and server
with `./scripts/dev-run.sh --no-build` after quitting the current session to use
both rebuilt jars, then complete M0 (including a real save roundtrip).


## Tab radial proof of concept

Client patch 0009 adds a reversible **Tab radial menu** setting (default on within
SoloScape Controller). View/Select toggles a 16-sector wheel; left stick selects,
A opens and B cancels. D-pad or bumpers cycle without held-button repeat. Existing
Y inventory focus remains; choosing Inventory on the wheel enters that focus too.
The wheel consumes controller movement/camera/actions, resets world focus, and
requires neutral/released input before gameplay resumes. Already queued destination
walking can finish; direct movement is stopped.

Tabs use the actual fixed (548) and resized (746) native button IDs and ordinary
widget operation dispatch. Hidden, stale or replaced buttons cannot dispatch;
dialogues block the wheel. There are no new server packets. The Objectives slot
maps to the layout's native objectives/familiar position and is available only if
its native button is visible/actionable. Native logout remains separate.

The original radial prototype switched existing tabs. Patch 0013 now adds controller handoff inside Inventory, Equipment, Prayer and Spellbook; patch 0014 additionally covers Combat, Skills, Quests and supported Settings. Other tabs retain native mouse controls. The
renderer was visually checked at 765×503 and 1280×800 on a plain background; it
has not yet been accepted in-game. The README includes that labelled preview.

Public development repository: `https://github.com/kannibalk1w1/SoloScape`.
The project remains maintainer-directed; see `CONTRIBUTING.md`. Cache acquisition
is documented in `CACHE_SETUP.md`; no assets, saves or runtime files are published.


## Overnight reliability checkpoint (2026-10-08)

Client patch 0010 implements the reliability changes described in `MORNING_REPORT.md` and `PROTOCOL_EXTENSIONS.md`. Client test/build: 76 cases, zero failures/errors, one SDL skip. Root tooling: 11 cases pass. Fresh, upgrade, reverse and repeated patch application reproduce all 41 affected client files. Claude found no blockers; minor follow-ups were applied. Direct movement now requires both Direct movement and SoloScape server features settings. Automatic remote capability negotiation and physical gameplay acceptance remain pending.


## Overnight controller-interface completion

Development branch: `overnight/controller-sprint`, implementation commit `bb1aca0`. Reliability (`daf577c`), bank/shop focus (`40cc0a0`), entry/recovery (`237e5be`) and tab/spell targeting (`bb1aca0`) are pushed. Read `MORNING_REPORT.md` for the complete session report and acceptance checklist.

Bank/shop focus activates automatically when their main interface opens. D-pad navigates and scrolls the visible native grid; LB/RB changes item/inventory/control panes. A withdraws/deposits or buys/sells; X exposes native quantities and actions. B leaves the action list, then closes; ignored closes recover for retry. Bank tabs, note/swap and deposit-carried/worn buttons use native actions.

Choose Equipment, Prayer or Spellbook on the radial to navigate their actionable widgets. A removes/toggles/selects; X exposes alternatives; B returns to the world. Equipment bonuses window 667 and side inventory 670 also have panes. Immediate spells use their ordinary actions; targeted spells preserve their selected source and hand off to eligible world targets or inventory. Selected targeting makes the stick aim without walking. Native masks/parameters, source item/quantity, widget identity and selection revision are checked again before dispatch. B cancels; an invalid selection never becomes a normal Eat/Drop action. Nearby world targets keep the existing conservative approach-path policy; this is not a full ranged-combat redesign.

Amount/name/string/bank-search prompts use a controller keyboard: D-pad chooses keys, A enters, X deletes, Y submits, B uses native Escape. Native CS2 handles editing and packet dispatch; only explicit controller Search requests trigger its armed key callback. Settings → SoloScape Controller → Native interface navigation disables these additions while retaining the original inventory/dialogue and radial behavior.

Three bounded Claude checks found no remaining blockers. Reported close/redraw/search and test issues were fixed; original reviews are retained in `CLAUDE_RELIABILITY_REVIEW.md`, `CLAUDE_BANK_SHOP_REVIEW.md` and `CLAUDE_ENTRY_SELECTION_REVIEW.md`. Automated checks and plain-background renderer previews are not proof of physical gameplay acceptance. No cache, accounts or running session was changed.


## Second autonomous sprint checkpoint

Client patch 0014 adds an independent eight-slot Start/Menu wheel. Focus food/potion in inventory, or a prayer/spell via home-tab focus; open the quick wheel, choose a slot and X assigns the focused native action (including an action selected in X's list). A uses it once after opening its native tab and revalidating the rendered widget; B cancels, including the pending handoff. Y restores the highlighted slot to its empty default. All slots start empty. Potion family bindings survive dose changes and prefer the lowest dose; cakes/pies that change item ID need reassigning.

Production dialogue 905 now includes native amount controls from 916: LB/RB chooses 1/5/10/All, the prompt shows the native amount and A confirms the recipe. Zero-producing decrement is not exposed. Smithing 300 groups exact pinned product/quantity widgets; A prefers one, X offers five/X/all through separately validated native sibling buttons. Tanning, silver casting and jewellery 324/438/446/675 use native permissions/actions. Quantity-X hands off to the existing controller keyboard.

Combat/Skills/Quests/selected Settings handoff uses groups 884/320/190/261/982. Native graphics/audio, quest and skill detail screens are supported where they expose ordinary actionable widgets; arbitrary sliders, drag controls and niche pages retain native input.

Attack options and selected NPC spells can be offered within a ten-tile selection radius across walking obstacles. Up to six such candidates are cycled; dashed highlights say “server approach”. This is a selection radius, not a claim that a weapon or spell can reach or see the target. The pinned server keeps its actual approach, weapon/spell range, collision and LOS decisions. Other world actions retain the bounded walking check. Failed/stale actions and cancellation have controller feedback.

Settings add auxiliary button choices for home wheel, quick wheel and inventory, overlap feedback, 75–175% controller overlay size, Xbox/PlayStation face labels and an optional controller guide. Native game UI text itself is not rescaled. Plugin Reset restores menu controls/empty slots; the wheel can restore one slot. A full remapping editor, first-run onboarding and custom native UI replacement remain future work.

Final automated evidence: 121 client cases (0 failures/errors, 1 SDL skip), 14 root cases, client Shadow jar and exact 59/14-file patch reproduction. No server code changed in either interface sprint. Actual Claude's planning audit, implementation review and follow-up are in the three `CLAUDE_SECOND_SPRINT_*.md` files; its medium default-consumable finding was fixed, and follow-up reports no blockers. Production cache/CS2 op availability and all new physical gameplay remain unaccepted. Read `MORNING_REPORT.md` for the combined report; the first report is archived as `MORNING_REPORT_SPRINT_1.md`.
