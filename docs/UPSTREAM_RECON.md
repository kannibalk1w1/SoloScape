# Upstream reconnaissance

Inspected 2026-10-08 from unmodified source checkouts. This is a code audit, not
a successful gameplay report. JDK 21 and JDK 8 have now been installed locally;
the upstream cache has been downloaded with explicit user authorization. Server
startup now succeeds; see `CACHE_SETUP.md` and `VALIDATION.md`.

## Pinned repositories

| Repository | Commit | Role | Repository licence |
| --- | --- | --- | --- |
| [game-server](https://github.com/2011Scape/game-server) | `9f9113559eb686abd917893b5dca16404be07f93` | Primary server; Void fork | BSD-3-Clause |
| [runelite-client](https://github.com/2011Scape/runelite-client) | `297bc8a4861755b676855664d32859054779c067` | Selected client | BSD-3-Clause; retain individual file notices |
| [634-client](https://github.com/2011Scape/634-client) | `b39d45f49a0480f3f200fe3e31ad0798faf163ab` | Plain client comparison | BSD-3-Clause |

All paths below are relative to the named repository. Checkouts are ignored by
the SoloScape root repository; pins above and in the launcher are authoritative.
Archived 667 repositories have not been cloned or modified.

## Server

- Revision is **634** in `game/src/main/resources/game.properties`.
- `buildSrc/src/main/kotlin/shared.gradle.kts` targets Java/JVM 21.
  `gradle/libs.versions.toml` selects Kotlin **2.4.0**; the wrapper selects
  Gradle **9.6.0**. Both upstream Gradle distributions downloaded successfully;
  full build results are recorded in `VALIDATION.md`. Do not silently downgrade pins.
- Application entry is `Main`, `game/src/main/kotlin/Main.kt`.
  Build `:game:shadowJar` and run the resulting jar with server root as cwd.
  The same cwd is configured by `:game:run`.
- `Settings.load()` reads root `game.properties` if present, otherwise bundled
  defaults. It does not merge an external partial file into defaults. The first
  launcher refuses external overrides so its paths/port/readiness assumptions
  remain consistent.
- Default cache is `./data/cache/`, loaded by `CacheLoader` and `FileCache`.
  Required base files are `main_file_cache.dat2` and `.idx255`, alongside the
  actual index files. Presence alone is insufficient: supply the compatible
  modified cache expected by upstream. No asset download has been attempted.
  The internal file server serves cache data to the client.
- `storage.type=files`, `storage.players.path=./data/saves/` and five-minute
  autosave are defaults. `GameModules.kt` creates `FileStorage`; it reads/writes
  `<lowercase-account>.toml` via `PlayerSave`. Database storage is optional and
  requires `-PincludeDb`. Preserve the file backend for bootstrap.
- `Main.preload()` registers a shutdown hook calling `World.shutdown()` and
  `AuditLog.save()`. `World.shutdown()` despawns players/world without clearing
  the player list first. `GameServer` also registers a network shutdown hook.
  Actual save completion on SIGTERM/restart still requires gameplay testing.
- Development defaults permit account creation on login, set `server.live=false`,
  disable the web server, and enable internal cache serving. This is a normal
  multiplayer world; no dedicated single-player pause/save mode was established.
- `network/GameServer.kt` binds `aSocket(selector).tcp().bind(port = port)` with
  no hostname: wildcard binding, not a localhost restriction. Port is **43594**.
  The launcher connects the client to localhost but does not narrow server binding.
  For local-only testing, restrict access with the host firewall. LAN clients
  need the host's reachable address and port; no public hosting automation added.
- TCP opens before preload, login-server assignment and world startup. Readiness
  must wait for `Void loaded in ...ms`, not merely an open port.
- `network.maxClientPerIP=10`, `world.players.max=2048` and login throughput
  limits already exist. `PlayerAccountLoader` uses per-account state and rejects
  concurrent/stale sessions with `ACCOUNT_ONLINE`; separate accounts are supported.
- Walk instructions flow through `InstructionHandlers` to
  `game/.../content/entity/Movement.kt`, then normal `player.walkTo` logic.
  NPC/object options use `engine/.../client/instruction/handle/NPCOptionHandler.kt`
  and `ObjectOptionHandler.kt`; interface actions use `InterfaceOptionHandler.kt`.
- Dungeoneering has a substantial `content/skill/dungeoneering` tree: generator,
  rooms/types, shops, binding, NPCs, map, doors, completion and bosses, plus
  generator/binding tests and data definitions. Existence does not establish
  completeness or working solo runs; a gameplay audit remains required.
- Bots are already implemented under `content/bot`, with manager, activities,
  navigation, setups/templates and chat. The default configuration starts **30**
  bots, staggered by 60 seconds. This first launcher preserves upstream defaults.
  Persistent identities, full activity coverage and Deck costs are not verified.
- Trade/lending/Grand Exchange and social code already exists. Preserve player
  collections, per-account saves, parties and authoritative shared world state.
  Global single-human variables would break independent interactions, inventory,
  hosted saves and shared bots. Content/event hooks are the preferred extension
  points; controller support needs no server changes.

## Client choice and insertion paths

Use **runelite-client**. Both clients target 634, but the selected repository has
recent development plus actual plugin/input/event/overlay integrations. This
decision is based on source inspection, not its name.

- Gradle **8.14.4**; Java **8** source/target and toolchain in
  `client/build.gradle.kts`. Run Gradle with JDK 21; supply a separate JDK 8
  toolchain/runtime. Foojay toolchain resolution exists upstream. Linux graphics
  and native library compatibility still need testing; start with software mode.
- `Loader.main` accepts `--address 127.0.0.1 --port 43594`. Its default is a
  remote IP; always provide an explicit address. Client/server public RSA moduli
  match the pinned source. No official Jagex servers were contacted.
- Keyboard: `Class346_Sub1` implements AWT `KeyListener`/`FocusListener`.
  Mouse: `Class373_Sub1`/`Class373_Sub2`; RuneLite `input/KeyManager` and
  `MouseManager` provide listeners. These are keyboard/mouse abstractions, not
  gamepad support.
- Tick/callback infrastructure: `net/runelite/client/callback/Hooks.java` and
  `game/GameEventBridgeHooks.java`, with `ClientTick`/`PostClientTick` events.
  Polling hardware must remain separate from client-thread action dispatch.
- Camera: `Canvas_Sub1.method119` and `Class82` integrate yaw/pitch velocities
  `Class205.aFloat2687` and `Class348_Sub27.aFloat6898` into
  `Class314.aFloat3938` / `Class76.aFloat1287`, then apply existing clamps.
  `Applet_Sub1.getCameraYaw/Pitch` expose final render values; writing those
  getters' fields would bypass the normal camera intent path.
- Menu dispatch: `Class325.method2599` consumes `Class348_Sub42_Sub12`, normalises
  the action ID and posts `MenuOptionClicked` before dispatching normal actions.
  `GameEventBridgeHooks.getMenuEntries` exposes entries. No confirmed public
  arbitrary-action invocation adapter exists. Add a narrow adapter only after
  validating revision-634 action IDs; RuneLite `MenuAction` labels alone are not
  proof of protocol compatibility.
- Walk menu branch (action 19) calls `Class348_Sub14.method2807` and
  `Class298.method2252`. Their parameters are still obfuscated. Follow this exact
  normal walking path; don't introduce direct-coordinate writes or new packets.
- `com/GameClient` exposes NPC/ground-item snapshots and projection helpers.
  Reuse those for focus where sufficient; comprehensive object picking and
  off-cursor action construction require further tracing.
- Existing `plugins/inventorygrid` provides slot bounds, canvas/overlay rendering
  and drag previews, including fixed/resizable interface handling. It is not
  controller navigation. Reuse its rendering knowledge, but validate actual
  revision-634 widget IDs and item actions before dispatching them.
- Rendering already has software/OpenGL/DirectX code and resizable UI paths;
  actual Linux renderer operation and 1280×800 behaviour remain untested.
- No gamepad provider was found in declared dependencies/source. Selecting a
  Linux/Deck provider is deferred until the client builds and runs. Compare SDL
  game-controller bindings against a small Java provider; explicitly verify
  current maintenance, licences, native deployment and Deck mappings before
  adding a dependency. No heavyweight framework has been introduced.

## Licensing and remaining verification

Root licences and sampled RuneLite file notices are BSD-3-Clause. Do not assume
those notices grant rights over Jagex assets or every bundled binary. The existing
`clientlibs.jar`, `graphics.jar`, `trident-1.5.00.jar`, native libraries and Maven
transitive dependencies need a distribution licence inventory before packaging.
No source has been copied across upstream repositories and no new dependency
has been added. An exhaustive dependency licence report awaits dependency
resolution. Historical GE research, bot performance/persistence and complete
Dungeoneering audits remain later milestones, not fabricated results here.

Server/client builds now pass unchanged. Local login, restart persistence, controller detection and Deck
acceptance remain **unverified**, not passed. Doctor and server startup now pass.
Next experiment: launch the built sources and create a
test character. Complete the restart checklist before controller implementation.
