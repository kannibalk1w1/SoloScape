# Minimum-change architecture

## Current boundary review — 17 October 2026

Merged main is authoritative; [CURRENT_STATUS](CURRENT_STATUS.md) indexes implementation/evidence. The native product currently has a Java 8 client, Java 21 Kotlin server, Swing launcher/Python ownership backend, semantic server definitions, revision-specific native UI bridges and ordered 0053/0022 patch stacks. Loopback binding, profiles, build stamps, negotiated direct movement and verified recovery were added after the original bootstrap design below.

Retain pure controller states plus native adapters and server authority; do not rewrite the coordinator on style grounds. [Playtest/architecture risks](PLAYTEST_DIRECTION.md) rank ownership, stale native identities, text, same-type cancellation and lifecycle uncertainty. Native menus are not world pause. [Backports](BACKPORT_ARCHITECTURE.md) extend existing semantic definitions through proposed authoring manifests; [browser research](WASM_FEASIBILITY.md) does not add a production transport/runtime.

## Original bootstrap design (historical)

The following records the initial plan, not current deployment or binding/acceptance status.

SoloScape is an orchestration/documentation root with separately pinned,
upstream checkouts with tracked SoloScape patch stacks in `upstream/`. These are ignored so proprietary
caches, saves and upstream binary resources cannot accidentally enter the root
source repository. `docs/KICKOFF.md` preserves the supplied brief.

Initial launcher responsibilities: validate prerequisites; build source jars;
start a direct server JVM from its expected cwd; wait for world readiness; start
the Java 8 client with an explicit localhost address; stream logs; terminate its
own children gracefully when the client closes or the user interrupts. Use a
launcher lock and process sessions, not broad process-name kills. Preserve saves
in the upstream default location. Never automatically SIGKILL during shutdown.

Bootstrap initially left the server unchanged. The opt-in direct movement build
adds authenticated directional/cancel instructions and a server movement mode; persistence
and ordinary walking remain unchanged. Wildcard upstream
binding remains a documented limitation. A later narrow bind-host option should
default to loopback and allow explicit LAN hosting. Preserve authoritative
world state and independent player accounts; client controller input works
identically for solo, host and guest.

Controller work belongs in the selected client's existing plugin/config/event
system. Keep polling/hotplug separate from pure stick maths and client-thread
action adapters. A disabled-by-default plugin/config gate is sufficient; do not
add unused `soloscape.*` settings yet. Reuse existing camera integration, walking,
menu dispatch and inventory overlays. Native gamepad library selection and small
bridges into obfuscated code require successful unchanged gameplay first.

Client changes are recorded as the numbered patches in `patches/client/` against
the pinned upstream base, covering camera, movement, tile markers and UI controls.
The direct movement server patch lives in `patches/server/` against its pinned
base. Source builds validate both stacks in a disposable tree, apply missing patches
idempotently and refuse conflicting local edits. See `CONTROLLER_TESTING.md`. The patch contains source,
tests and notices, with no game assets. Keep subsequent changes small.

The user confirmed launch, controller input and improved walking/aiming gameplay.
The optional direct movement build still needs physical acceptance. Initial validation order:

1. Prerequisites complete: JDK 21 + JDK 8 and upstream cache installed; doctor passes.
2. Build unchanged server/client; confirm local login and clean restart saves.
3. Validate Linux controller polling/hotplug and choose a licensed provider.
4. Add right-stick camera; test alongside keyboard/mouse.
5. Add movement via a verified normal walking adapter.
6. Add nearest sensible world focus/default action through normal menu dispatch.
7. Add inventory grid focus using verified slot/widget metadata.

OSRS content, economy, bots, suspend support and hosting UX remain out of scope.
