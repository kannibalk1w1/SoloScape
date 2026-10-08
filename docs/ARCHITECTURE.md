# Minimum-change architecture

SoloScape is an orchestration/documentation root with separately pinned,
unmodified upstream checkouts in `upstream/`. These are ignored so proprietary
caches, saves and upstream binary resources cannot accidentally enter the root
source repository. `docs/KICKOFF.md` preserves the supplied brief.

Initial launcher responsibilities: validate prerequisites; build source jars;
start a direct server JVM from its expected cwd; wait for world readiness; start
the Java 8 client with an explicit localhost address; stream logs; terminate its
own children gracefully when the client closes or the user interrupts. Use a
launcher lock and process sessions, not broad process-name kills. Preserve saves
in the upstream default location. Never automatically SIGKILL during shutdown.

No server engine/protocol/persistence changes in bootstrap. Wildcard upstream
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

When controller work begins, keep changes as small client commits and record
their upstream base. Root tooling must not overwrite dirty checkouts. A
maintained fork or patch workflow can then be chosen around actual changes;
no empty framework or speculative patch system is needed now.

The first playable milestone has not been achieved. Validation order:

1. Resolve JDKs/cache and any pinned Gradle/dependency resolution failures.
2. Build unchanged server/client; confirm local login and clean restart saves.
3. Validate Linux controller polling/hotplug and choose a licensed provider.
4. Add right-stick camera; test alongside keyboard/mouse.
5. Add movement via a verified normal walking adapter.
6. Add nearest sensible world focus/default action through normal menu dispatch.
7. Add inventory grid focus using verified slot/widget metadata.

OSRS content, economy, bots, suspend support and hosting UX remain out of scope.
