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

The latest B world action uses custom opcode **86**, with no payload or client
position. It clears normal movement/interaction, watch, weak actions and suspension.
After clearing the old action it runs pending walk cleanup once, allowing unmorph
or content exits and preserving any route the callback installs. It respects the
ordinary busy/delay gate; it is not an escape from forced actions such as agility.
Dialogue B currently uses the already-verified ordinary same-tile Walk cancellation path, not opcode 86.

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
Seven client patches and two server patches reproduce the current modifications.
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

- **71 client test cases (68 distinct methods)**, with one SDL virtual-device test
  deliberately skipped in this batch. Native camera,
  pathfinder, widget tests, world-menu input, actual loot tables, NPC options,
  12-item cycling, blocked-pile starvation, cache freshness and encrypted
  directional/cancel packet encoding are covered. Earlier SDL validation passed.
- **247 network tests** and **61 selected engine movement/decoder/cancel tests**, without skips.
- Three patch-helper tests and four simulated launcher lifecycle tests.
- Client/server source reproduction matches all **41 / 14** affected files on
  fresh bases, upgrades, sequential reverse application and repeated application.

These establish automated behavior, not Steam Deck performance or complete
physical gameplay acceptance. Some UI closing is mocked in the server cancel tests;
its actual in-game result still needs the new build to be played.

To try the latest code, quit the running game/launcher cleanly and run from the root:

```bash
./scripts/dev-run.sh --no-build
```

This starts both updated processes. Keep the controller plugin enabled and choose
Direct movement if desired. Try X on an NPC with several options, D-pad/A confirmation,
B back/cancel, dropped loot, stacked pile cycling, inventory/dialogue handoff and
ordinary mouse actions. See `docs/CONTROLLER_TESTING.md` for more detailed checks.

## Important gaps

- Confirm real character persistence across a clean restart, not just server startup.
- Banks, shops, equipment/prayer/spell panels, quick actions, and many special
  interfaces still need controller navigation. Inventory Use has limited widget
  selection support; full item/spell targeting and numeric/text entry remain unfinished.
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
2. Complete banks and shops, then prayer/spells/equipment and quick combat actions.
3. Make the UI readable and discoverable at Deck resolution; add glyphs and presets.
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

Remaining proposals include server capability negotiation/jar mismatch detection,
separate SDL and game-adapter exception handling, reducing idle inventory snapshot
work, and checking dialogue cancellation coordinates and border passages. Combat
range/line-of-sight targeting needs its own policy before controller combat work.
These are not implemented by the review-fix batch. Restart both client and server
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

This prototype switches existing tabs; only Inventory has controller navigation
inside it today. Other opened tabs still use their existing mouse controls. The
renderer was visually checked at 765×503 and 1280×800 on a plain background; it
has not yet been accepted in-game. The README includes that labelled preview.

Public development repository: `https://github.com/kannibalk1w1/SoloScape`.
The project remains maintainer-directed; see `CONTRIBUTING.md`. Cache acquisition
is documented in `CACHE_SETUP.md`; no assets, saves or runtime files are published.
