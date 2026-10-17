# World transient save audit — 2026-10-17

Read-only source audit. No source, test, script, Git, Gradle, launch, save, or Deck access. No physical or JVM restart was run.

## Question

Does a clean local-world shutdown preserve unrecovered gravestone and death floor loot?

## Short answer (source-inferred, not run)

No, by source reading: no writer persists the grave NPC, its timer, or the floor loot. The player's grave marker keys are also not persisted, because they have no persistent variable definition. Kept inventory items do persist, through the normal account save.

Source paths below are relative to `upstream/game-server/`. This audit concerns runtime world entities, separately from the verified account/Grand Exchange save receipt.

## Source map (fact)

Death and grave creation
- `game/src/main/kotlin/content/entity/death/PlayerDeath.kt:90-94` runs `dropItems` on death. Kept items are removed first.
- `PlayerDeath.kt:132` calls `Gravestone.spawn(player, tile)`. Its return value is the floor timer.
- `PlayerDeath.kt:177` adds each death drop as a `FloorItems` entry with `revealTicks = time`, `disappearTicks = time + 60`, and the owner's name.
- `game/src/main/kotlin/content/area/misthalin/lumbridge/church/Gravestone.kt:25` adds the grave NPC with `NPCs.add`. Lines 27-28 set `player_name` and `player_male` on the NPC.
- `Gravestone.kt:29-30` writes `player["gravestone_time"]` and `player["gravestone_tile"]`, the player's variables.

Grave timer and restore
- `game/src/main/kotlin/content/area/misthalin/lumbridge/church/Gravestones.kt:29-40` (`playerSpawn`) reads `gravestone_tile` and `gravestone_time`, then re-adds the map marker when time remains. It does not restore an NPC or floor items.
- `Gravestones.kt:46-51` (`npcSpawn "gravestone_*"`) starts the NPC's `grave_timer`. Lines 158-190 handle the timer tick, stop, and removal.
- `Gravestones.kt:207-213` (`updateItems`) changes reveal and disappear ticks for owned floor items on repair or bless.

Persistence boundary for player variables
- `engine/src/main/kotlin/world/gregs/voidps/engine/client/variable/Variables.kt:42-47`: `set` writes through `data(key)`.
- `engine/src/main/kotlin/world/gregs/voidps/engine/client/variable/PlayerVariables.kt:47`: `data(key)` returns the persisted map only if `VariableDefinitions.get(key).persist`. Otherwise it returns `temp`, which is never serialized.
- `engine/src/main/kotlin/world/gregs/voidps/engine/data/definition/VariableDefinitions.kt:35`: `get(key)` returns `definitions[key]`, which is null for undefined keys.
- `engine/src/main/kotlin/world/gregs/voidps/engine/data/config/VariableDefinition.kt:49-50`: `persist` is false when the definition is null.
- `data/area/misthalin/lumbridge/church/gravestone.varbits.toml` defines `[gravestone_current]` with `persist = true`. A repo-wide search finds no TOML definition for `gravestone_time` or `gravestone_tile`. Their only data hit is client-side `cache/.../Params.kt:1007`.

Save writer and load
- `engine/src/main/kotlin/world/gregs/voidps/engine/data/PlayerSave.kt:81-84` writes the `variables` map. `PlayerSave.kt:472-482` (`Player.copy`) copies `variables.data`, which is the persisted map only.
- `engine/src/main/kotlin/world/gregs/voidps/engine/data/SaveQueue.kt:12-17` (`save(player)`) queues a copy in `pending`. Lines 43-48 (`direct`) save every online non-bot player plus queued accounts.
- `engine/src/main/kotlin/world/gregs/voidps/engine/client/PlayerAccountLoader.kt:66` loads `save?.toPlayer()` on login.

Save triggers
- `engine/src/main/kotlin/world/gregs/voidps/engine/data/AccountManager.kt:110-145` (`logout`): `Despawn.player`, then `saveQueue.save(player)`, after `Players.remove`.
- `game/src/main/kotlin/content/entity/player/AutoSave.kt:20-33`: `worldDespawn` awaits in-flight saves, runs `saveQueue.direct`, saves the Grand Exchange, and checks that primary save was confirmed.
- `AutoSave.kt:45-59` (`autoSave`): every `storage.autoSave.minutes` (5 in `game.properties:457`), it queues all players and the Grand Exchange.
- `engine/src/main/kotlin/world/gregs/voidps/engine/entity/World.kt:80-88` (`shutdown`): `Despawn.player` for each player, then `Despawn.world()`.

Despawn scope
- `engine/src/main/kotlin/world/gregs/voidps/engine/entity/Despawn.kt:60-125`: `player(...)` runs player despawn handlers, the queue, and timers. It does not touch floor items or NPCs. `floorItem(...)` and `npc(...)` are separate handlers.

Floor items and NPCs
- `engine/src/main/kotlin/world/gregs/voidps/engine/entity/item/floor/FloorItems.kt` has no save or load method. The grep finds no persistence there.
- `engine/src/main/kotlin/world/gregs/voidps/engine/entity/item/floor/ItemSpawns.kt:38` reads static spawn configuration only.
- `engine/src/main/kotlin/world/gregs/voidps/engine/data/definition/MapDefinitions.kt:43-53` loads and saves `GameObjects` to `storage.caching.objects` (`map_objects.dat`). This is the cache-derived static map, not runtime state.
- `game/src/main/kotlin/content/entity/player/inv/item/drop/ItemDropping.kt:42-45` (player Drop) creates floor items the same way, with no persistence.

Patches and existing tests
- No file under `patches/server/` mentions `gravestone_time` or `gravestone_tile`.
- The death-recovery fresh-load test (`DeathLootRecoveryTest`, added in 0036) saves after recovery and removes the recovered item from the ground before the save. It proves only that post-recovery inventory, XP, and tile persist. It does not prove pre-recovery loot persistence.

## Distinctions

- **Player logout and relogin in one live process:** the account save is written, and login reloads it. The grave NPC and floor loot stay in memory, because nothing removes them. The grave marker keys are temp variables, so the reloaded player has no marker, and `playerSpawn` cannot restore it. Inferred, not run.
- **Full server restart:** the grave NPC, floor loot, and grave marker are all absent after boot. Kept inventory items return. Inferred, not run.
- **Normal ground drops (player Drop):** not persisted, same as death drops. Inferred from `ItemDropping.kt` and the absence of any `FloorItems` writer.
- **Static respawns:** reloaded from spawn configuration on boot (`ItemSpawns.kt:38`), so they return by design.
- **Death drops with a grave:** not persisted through restart, and the grave marker is lost on relogin.

## Inferred risk (tentative)

Player-facing loss of unrecovered death loot on any server restart. It needs no duplication path and is bounded by grave timers of 5 to 15 minutes unless blessed. No P0 is claimed. Severity stays tentative until a restart experiment runs.

## Why the post-recovery fresh-load test does not prove pre-recovery persistence

It saves only after the loot was taken back, so the save never contains the grave or floor state. Its checks cover the inventory, XP, and tile, and the grave variables are not in it at all. Passing it says nothing about unrecovered loot.

## Smallest disposable restart experiment (not run)

Two JVMs on a copy of `./data/saves/` in a temp directory, with `storage.disabled` false:
1. JVM 1: create a player with a Lumbridge death, unrecovered. Run the same sequence as `World.shutdown` (`Despawn.player` plus `saveQueue.direct`). Record the grave NPC, `FloorItems` at the grave tile, and the persisted variable keys.
2. JVM 2: boot the same data path with no other state. Check the same tile for the grave NPC and floor items, and check whether `gravestone_time` and `gravestone_tile` exist on the reloaded player.

Expected from source: the grave and floor items are absent in JVM 2, and the grave keys are absent from the save file. The experiment must distinguish a missing restored record from expiry or incomplete startup before confirming the inferred risk.

## Two bounded policies (not chosen, not implemented)

- **Policy A, persist remaining grave loot and timer.** A server-owned world-state file, written atomically on `worldDespawn` and autosave, holds grave records. Each record has tile, owner, item list, and absolute expiry epoch. Boot recreates the NPC and floor items, and the record is removed on take, expiry, or demolish. Needs no-duplicate guarantees and a migration. Larger change.
- **Policy B, explicit pre-quit notice and safe fallback.** On logout or shutdown countdown, tell an owner with an unrecovered grave that its loot will not survive a restart. Shutdown countdown already exists (`ServerCommands.kt:189`). No new persistence. Preserves server authority and avoids duplication, but does not recover the loss.

Both policies require an explicit local-world lifecycle decision; neither is implemented here. Whether the original game kept graves across restarts is not verified here and must not be assumed.

## Not done

- No source, test, script, Git, Gradle, launch, save, or Deck action.
- No restart reproduction.
- No change to historical reports.
