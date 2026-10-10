# Console-alpha foundation: planning audit

A read-only source audit of the pinned Void server (`upstream/game-server`). I did not launch
the game or read or change any real save or cache file. I made no edits or builds. Paths below
are relative to `upstream/game-server/`.

## 1. Who writes what (file storage, `storage.type=files`)

| Data | Writer | Path setting (default) | When the path is resolved |
|---|---|---|---|
| Player saves `<name>.toml` | `FileStorage.save` → `PlayerSave.save` (`engine/.../data/PlayerSave.kt:60`) | `storage.players.path` (`./data/saves/`) | **Once**, when the `Storage` singleton is built (`game/.../GameModules.kt:62-66`) |
| Account index and clans | `FileStorage.names()` / `clans()`: they read **every `*.toml` at the top level** of the saves directory | same | at startup, and on account reload |
| Grand Exchange offers, claims, price history | `FileStorage.saveOffers/saveClaims/savePriceHistory` | **relative to the saves directory**: `grand_exchange/...` (`storage.grand.exchange.*`) | sub-path read on every call; base directory fixed |
| Abuse reports | `FileStorage.saveReport` | `<saves>/reports/` | per call |
| Failed saves (after `storage.save.retryMinutes`) | `SaveQueue` → `SafeStorage` (`EngineModules.kt:34`) | `storage.players.errors` (`./data/errors/`) | once |
| Audit logs | `SaveLogs` stage (`game/.../GameTick.kt:83`) and the shutdown hook `AuditLog.save()` (`Main.kt`) | `storage.players.logs` (`./data/saves/logs/`) | `SaveLogs` caches it at startup; **`AuditLog.save()` with no arguments reads `Settings` again at shutdown** |
| Derived temporary files | `ConfigFiles`, `Wildcards` | `storage.data.modified`, `storage.wildcards` (`./data/.temp/...`) | startup |

### When saves are flushed
- Autosave every `storage.autoSave.minutes` (5). It queues every player and calls
  `exchange.save()` (`content/entity/player/AutoSave.kt:41-55`).
- On shutdown: the JVM shutdown hook runs `World.shutdown()` → `Despawn.world()` → `worldDespawn`.
  That waits for any save in flight, runs `saveQueue.direct().join()` and then
  `exchange.save()` (`AutoSave.kt:23-28`). **SIGTERM or Ctrl-C saves everything. SIGKILL
  loses up to 5 minutes and can leave half-written files.**

### Traps
1. **Writes are not atomic.** `Config.fileWriter` is `BufferedWriter(FileWriter(file))`, which
   truncates the file before writing (`config/.../Config.kt:28`). `PlayerSave.save` and every
   GE writer use it. A kill or full disk during a write leaves a truncated save. On the next
   start, `names()` logs a warning and **drops that account** without stopping (`FileStorage.kt:41-43`).
2. **Any extra `*.toml` in the saves directory is treated as an account.** Backups or copies
   such as `alice-backup.toml` placed there would be loaded as accounts.
3. **Only one directory level is created.** `saves.mkdir()` (`GameModules.kt:63-65`) creates
   just the last level, so a nested profile path whose parent doesn't exist fails later, at
   the first write.
4. **Saves are skipped silently** for `player.contains("bot")` and when `storage.disabled=true`
   (`SaveQueue.kt:101`).

### Recommended source change (small server patch)
In `FileStorage.save` (`FileStorage.kt:335`), write each account to
`directory.resolve("$name.toml.tmp")`, then
`Files.move(tmp, target, ATOMIC_MOVE, REPLACE_EXISTING)`. The `.tmp` suffix stays out of
`names()`, because it doesn't end in `.toml`. Do the same for `saveClaims` and `saveOffers`'s
counter file, or put a shared `atomicWriter(file) { … }` helper into `Config` and switch the
callers to it. Change `saves.mkdir()` to `mkdirs()`.

### Python backup and profile manager (what this means for your work)
- Back up **only while the server is stopped**, or after a clean SIGTERM exit. Copy the whole
  saves directory, including `grand_exchange/` and `reports/`, plus the errors and logs
  directories.
- Store backups **outside** `storage.players.path`, or with a name that doesn't end in `.toml`.
- When the server starts, warn if the errors directory isn't empty (failed saves sit there
  until someone recovers them by hand).
- Stop the server with SIGTERM and wait for it to exit (the existing launcher's graceful stop).
  Never SIGKILL while a save may be running.

## 2. Settings: loading, overrides and isolated profiles

- `Main.settings()` (`game/.../Main.kt:105-109`) runs `Settings.load()`. That reads
  **`./game.properties` from the working directory**, or falls back to the bundled resource.
  It then runs `properties.putAll(System.getenv())`.
- **Environment variables override any key.** The variable name must match the key exactly,
  dots included, for example `storage.players.path`. A shell can't `export` such names, but
  Python `subprocess.Popen(env={...})` can set them. **This is the zero-patch isolation
  route.**
- Relative `./` paths resolve against the server's working directory (`SERVER`, set in
  `scripts/local_dev.py`). Nothing calls `Settings.rebase`.

### Keys to override per profile (use absolute paths)
`storage.players.path`, `storage.players.logs`, `storage.players.errors`. Grand Exchange and
reports follow `storage.players.path` automatically. Leave `storage.data*`, `storage.cache.*`,
`storage.wildcards` and `storage.scripts.path` shared: they are derived or read-only content.

Also consider:
- `bots.count` (default **30** bots are spawned)
- `development.admin.name` (default `Greg`: a player with that name is granted Admin,
  `content/entity/player/command/Rights.kt:22`)
- `world.members`
- `network.port`

### Traps
1. **The settings reload command drops environment overrides.** `::reload settings`
   (`content/entity/player/command/ServerCommands.kt:139`) runs `Settings.load()` again, which
   `putAll`s the file values over the environment ones. Paths fixed at startup (saves,
   errors, cached logs directory) are unaffected. However, the **shutdown hook
   `AuditLog.save()` then writes logs to the default `./data/saves/logs/`**, and any later
   per-call `Settings["storage.*"]` read returns file values. Minimal fix: in that branch,
   follow `Settings.load()` with `Settings.load(System.getenv().toMap())`. Alternatively,
   don't give admin rights to profile accounts (override `development.admin.name` to a value
   no account can have).
2. **Every inherited environment variable ends up in `Settings`.** That's harmless today, but
   pass the server a curated environment, not `os.environ` wholesale, so stray variables can't
   collide with setting keys.
3. **`DungeonGenerator.main` calls `Settings.load()`** without the environment. It's a
   development tool only and not on the server's run path.

### Optional patch (clearer than the environment)
In `Main.settings()`, after `Settings.load()`, read the system property
`-Dsoloscape.properties=/abs/profile.properties` and, if it is set,
`Settings.load(File(it).inputStream())`, then add the environment. Apply the same to the reload
branch. This lets each profile ship one readable overlay file.

## 3. Network bind and capability negotiation

- **The game server listens on every network interface.** `aSocket(selector).tcp().bind(port = port)`
  (`network/.../GameServer.kt:37`) has no host, so it binds `0.0.0.0` and the game is reachable
  from the LAN. The web server, by contrast, is hard-coded to `"localhost"` (`Main.kt:203`).
  **Fix:** `bind(hostname = Settings["network.host", "127.0.0.1"], port = port)`, passing the
  host through `GameServer.load`/`start`. LAN guest play would then need an explicit
  `network.host=0.0.0.0`.
- **Login.** `LoginServer` rejects any client whose `int` version isn't `server.revision`
  (634) (`LoginServer.kt:52-55`). Changing that int would break both directions, so don't use
  it for capabilities.
- **Capability negotiation without new opcodes.** I did not check which existing
  server-to-client message is safest to use here. Candidates:
  - a varp, varbit or varc the server already sends after login, set to a SoloScape feature
    value;
  - a client-script invocation of an existing script.

  Either needs proof that the ID isn't used by the 634 cache, so **I'm not naming IDs here**.
  The client should keep `serverFeatures` off until it has seen that value during the current
  login session.
- **Server-side gate.** The patched handlers for SoloScape's custom client packets could also
  check a `soloscape.features` setting, so a profile can turn the extensions off without a
  client change.

## 4. True solo pause: feasibility

The game loop (`engine/.../GameLoop.kt`) runs the stages from `getTickStages()` in this order:
- `PlayerResetTask`
- `NPCResetTask`
- bots
- hunting
- `grandExchange`
- **`ConnectionQueue`**
- NPC and floor-item registries
- **`InstructionTask`**
- `World`
- NPC and player tasks
- timers
- zones
- **`CharacterUpdateTask`**
- **`accountSave`**
- `SaveLogs`

**Feasible, if contained:** a `paused` flag checked inside `GameLoop.tick()`. While paused, run
only:
- `PlayerResetTask` and `NPCResetTask`, so update flags don't repeat;
- `ConnectionQueue`, so logins and logouts still happen;
- `CharacterUpdateTask`, so the client keeps receiving its normal per-tick updates;
- `accountSave` and `SaveLogs`.

Skip `World`, the NPC and player tasks, timers, hunting, `grandExchange` and bots.

**Rules and hazards**
- **Only pause when there is exactly one non-bot player.** Unpause automatically when the
  connection queue accepts a second human, so guests are never frozen.
- **Inputs queued while paused.** If `InstructionTask` is skipped, clicks queue up and all run
  on resume, which would be stale actions. Either drain and discard non-system instructions
  while paused, or keep `InstructionTask` running but only allow logout. **Logout must keep
  working** so the player can save and quit.
- **The shutdown path is unaffected.** It runs from the JVM hook (`World.shutdown()`), not from
  ticks. Check that `Despawn.world()` and `worldDespawn` don't wait for a tick-driven queue.
  I did not trace this.
- **Wall-clock content keeps running.** Some content uses wall-clock time and will advance
  during a pause. Files that read real time include `Gravestones.kt`, `EvilTree.kt`,
  `RandomEvents.kt`, `TzhaarFightCave.kt`, achievements and `BotManager`. Grand Exchange offer
  expiry (`grandExchange.offers.activeDays`) and buy limits (`buyLimit.hours`) are also
  time-based settings. A pause is therefore not a full time freeze. Document this, or make
  pause clear the grave timer as well.
- **Client idle and timeout.** I couldn't confirm from source how long the 634 client
  tolerates update-only ticks. Because `CharacterUpdateTask` keeps running, it should behave
  like standing still. Check this in game, including the idle-logout rule.
- **How to trigger pause.** A server command from the console, or a loopback-only admin
  request, rather than a new client packet. If a client-originated request is needed, reuse
  the existing server-features gate and don't invent an opcode here.

## Evidence limits
- This is source only. I did not verify the cache varp, varc or script IDs, the client's
  timeout, or the database-storage backend (it is only built with `-PincludeDb`).
- I did not trace `Despawn.world()` internals or the `PlayerAccountLoader` concurrency with
  pausing.
- I did not read the contents of `config/local.env`.
