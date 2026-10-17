# Dungeoneering completion audit — 17 October 2026

Scope: source inspection of the enabled normal-player solo path (one player, small, complexity 1, floor 1) from boss spawn through boss death, end-trapdoor, reward, next-floor countdown, leave and normal save. No production source, data, cache or assets were changed. One native test file was added (patch 0031) and run; its results are in §6. Target: `/home/kannibalkiwi/orca/projects/SoloScape`. Source baseline: the inspected base is `60e6cb5`. This pass does not claim the source is unchanged since then. The SoloScape repo HEAD is `8bf0e23`. `upstream/game-server` is a separate git checkout (HEAD `9f91135`) that the SoloScape repo ignores, and `60e6cb5` is not an object in it, so git here cannot confirm the source is unchanged since `60e6cb5`.

Paths are under `upstream/game-server/game/src/main/kotlin/` unless shown otherwise. Data paths are under `upstream/game-server/data/`. Labels: **[Source]** = read directly in the cited lines; **[Hypothesis]** = inferred, needs a test or cache data to confirm.

## 1. Transition map

| # | Step | Code path (line refs) | Guard / state written | Status |
|---|------|-----------------------|-----------------------|--------|
| 1 | Ring + solo leader | `area/wilderness/daemonheim/DungeonEntrance.kt:44-66`; `DungeoneeringParty.kt:510-520` (`setLeader` sets floor to `DungeonFloor.maxFloor(player)`) | Needs `ring_of_kinship`; solo sets leader | **[Source]**; already covered by `SoloDungeonLifecycleTest` (docs) |
| 2 | Solo size and checks | `DungeonEntrance.kt:70-73` (1 member → `dungeonSize(1)`), `:159-163` (complexity 1 → Small), `:177-188` (non-admin guard: floor > 11 or complexity ≠ 1 rejected) | Floor/complexity gates | **[Source]** |
| 3 | Generate | `DungeonEntrance.kt:190-199`; `skill/dungeoneering/DungeonGenerator.kt:101-102` (last path room → `Boss`), `:160-166` (boss door locked with `bossDoorLockChance` 0.90), `:19-27` and `:391` (room name = template row id) | Boss room `name` must equal a row in `${theme}_c1_boss` | **[Source]** |
| 4 | Boss template | `data/skill/dungeoneering/floor/theme/dungeoneering_frozen_rooms.tables.toml:32-39`: only `[.icy_bones]` is enabled, `start_floor = 1`. All other boss rows are commented out (`:41-79`). | Exactly one enabled c1 boss: `icy_bones` | **[Source]** |
| 5 | Enter instance | `DungeonEntrance.kt:209-232` (instance, `generate` writes `dungeon`/`instance`), `:234-279` `enter()`: `DungeoneeringParty.clear(this)` (`:240`), `DungeonStartingItems.spawn` (`:252`) | `clear` resets `dungeon_reward_given` (`DungeoneeringParty.kt:334`) | **[Source]**; entry/supplies/bind/leave proven by tests, not boss |
| 6 | Boss room opens | Door: `skill/dungeoneering/DungeonDoors.kt:195` (`adj.open`). Admin bypass: `skill/dungeoneering/Dungeoneering.kt:51-59` (`unlock_dungeon`, opens all rooms; fixture only). Open: `DungeonRoom.kt:33-60` → `DungeonNPCs.spawn` (`:58`) | Room opens once (`open` flag) | **[Source]** |
| 7 | Boss spawn | `skill/dungeoneering/DungeonNPCs.kt:46-49` (`Boss` → `spawnBoss`), `:24-44`: row `boss_spawns.${room.name}` (`:28`) = `[boss_spawns.icy_bones]` in `data/skill/dungeoneering/boss/dungeon_boss_spawns.tables.toml:6-27`; ids `rand_ice_lord_boss_0..17`; picks highest combat ≤ solo combat, else `ids.first()` (`:30-35`); fixed tile (199,5015) → room-local (7,7) (`:37-41`); `room.monsters++` (`:43`) | Row lookup name chain resolves for `icy_bones` | **[Source]** (name chain); spawn at runtime **[Test]** for the seeded run: one spawn from the configured row (§6). The spawn tile comes from `DungeonMap.tile(room, x, y)`; see §6 for the rotation observation. |
| 8 | Boss kill | Unlock is `npcDeath("rand_ice_lord_boss_*")` in `skill/dungeoneering/DungeonDeaths.kt:47-69`. Death counter: `DungeonDeaths.kt:37-45`. Combat behaviour: `skill/dungeoneering/boss/IcyBones.kt` (spawn anim, box/cone attacks only). | Only the `rand_ice_lord_boss_*` name pattern | Kill handler **[Source]**; real combat kill **not tested** |
| 9 | Trapdoor unlock | `DungeonDeaths.kt:49` `findDoor(...,"rand_dungeon_end_trapdoor_locked_frozen")`; probes `DungeonDeaths.kt:74` = wall midpoints `(x, y+7)`, `(x+15, y+7)`, `(x+7, y)`, `(x+7, y+15)` where `x,y = room.minX-1, minY-1`; fallback `:50-58` scans only a 3×3 corner; success `replace` to `rand_dungeon_end_trapdoor_unlocked_frozen` at `:59`. Object ids: `data/skill/dungeoneering/boss/dungeon_boss.objs.toml:13-19`. | Object state only; no kill counter or flag | Code **[Source]**; placement **[Test]** for the seeded run only: the locked trapdoor is at the west midpoint probe `(x, y+7)`, and it unlocks after the controlled death (§6). The map data is not in the repo. |
| 10 | Reward gate on trapdoor | `skill/dungeoneering/DungeonComplete.kt:38-49`: `End-dungeon` on `rand_dungeon_end_trapdoor_unlocked_frozen`; returns early if `dungeon_move_on_vote`; solo (`dungeonMembers.size == 1`) calls `dungeonComplete()` directly (`:47-49`). No timer on the solo path. | No check of boss death: the object's unlocked state is the only gate | **[Source]** |
| 11 | Reward / floor credit | `DungeonComplete.kt:198-325`. Reward guard: `:279` (`!get("dungeon_reward_given")`), set `:309`. Floor unlock only if `floor == unlocked` and `floor+1 <= floorAtLevel` (`:294-308`). Floor progress: `:315-322` (`dungeon_floor_N_complete`, `dungeoneering_current_progress`). XP `:311`, tokens `:312`, audit `:313`. Tick-off / prestige: `:224-230`, `:327-334`. | Reward is per dungeon; guard cleared on entry (`DungeoneeringParty.kt:334`) | **[Source]** |
| 12 | Next-floor countdown | `DungeonComplete.kt:122-126` (`continueCountDown`: `dungeon_next_timer` = `dungeoneering.secondsBetweenDungeons`, default 30 s at `game.properties:258`), `:109-119` (tick), `DungeonEntrance.kt:108-118` (`timerStop("dungeon_continuation")`: increments floor, clamps to `maxFloor`, then `generate`) | Countdown is started for the leader only | **[Source]**; see finding F3 for the clamp |
| 13 | Leave | `DungeoneeringParty.kt:401-422` (`leave`, from `playerDespawn` at `:128-130` and the leave option at `:120-123`), `:351-379` `leaveDungeon` (drops items, `clear`, teleport to 3460,3721,1, `clearInstance` if last), `:424-437` `clearLeader` (clears `dungeon_continuation`, `dungeon_complete`, `dungeon_next_timer`, `dungeon_end_timer`) | `softTimers.clear` does **not** run the stop handler (`engine/.../timer/TimerQueue.kt:76`; stop only from `:70-72`), so leaving does not regenerate a floor | **[Source]** |
| 14 | Normal save | Persisted: `dungeoneering_floor_unlocked` (`data/skill/dungeoneering/dungeoneering.vars.toml:69-71`), `dungeon_floor_1_complete` (`:73-75`), `dungeoneering_tokens` (`:26-28`), `dungeoneering_current_progress` and `dungeoneering_previous_progress` (`dungeoneering.varcs.toml:11-19`), `dungeoneering_party_floor` (`:1-4`). **Not** persisted: `dungeon_reward_given` has no definition, so it lives in the non-persistent store (`engine/.../client/variable/PlayerVariables.kt:47`, `VariableDefinition.persist` at `engine/.../data/config/VariableDefinition.kt`). | Reward state survives logout via the persisted progress keys; the guard does not | **[Source]**; no test saves a completed reward |

Existing coverage (docs `DUNGEONEERING_TARGETED_PASS_20261017.md`, `DUNGEONEERING_NATIVE_ENTRY_20261017.md`): entry, supplies, bind, leave, and the logout-save of the bound item. A repo-wide search under `upstream/game-server/game/src/test` finds no reference to `End-dungeon`, `end_trapdoor`, `rand_ice_lord`, `dungeon_reward_given`, `dungeonComplete` or `unlock_dungeon`. **Boss kill, trapdoor, reward and countdown are not covered by any test.**

## 2. Findings

**F1. Multi-member completion cannot reach `dungeonComplete()` — [Source], out of solo scope.**
`DungeonComplete.kt:53-59`: the vote timer is started with `startIfAbsent("dungeon_complete")` (`:56`) only inside `if (leader.contains("dungeon_end_timer"))`. On the first vote that condition is false, so no timer starts and the `else` branch only decrements a variable. Even when the timer does start, the name `"dungeon_complete"` does not match the registered handlers `timerStart/Tick/Stop("dungeon_completion")` (`:66-83`), and nothing starts `"dungeon_completion"`. Soft-timer handlers are looked up by exact name (`engine/.../timer/TimerApi.kt:106-118`; `TimerQueue.kt:16-32`). Consequence: party completion is unreachable. Solo is unaffected because it skips the vote.
*Minimal repair (not applied):* start one correctly named timer on the first vote and use the same name in `startIfAbsent`, `timerStart`, `timerTick` and `timerStop`.

**F2. The solo reward is queued, not synchronous or immediate — [Source].**
`End-dungeon` calls `dungeonComplete()` (`DungeonComplete.kt:47-49`), which schedules `strongQueue("dungeon_info")` (`:198-199`) and may suspend for item dialogues. The same handler then calls `continueCountDown(leader)` without waiting for that queue. The reward (step 11) therefore runs later, and the countdown does not wait for it. Repeat clicks re-enter `continueCountDown` (`:122-126`; the reset is at `:123`). The reward block is guarded by `dungeon_reward_given` (`:279`) and the flag is set at `:309`, inside the same queued block. Whether two quick clicks can both pass `:279` before the first job reaches `:309` is **not verified**.

**F3. Floor-1 countdown may regenerate floor 1 for low-level accounts — [Source arithmetic] + [Hypothesis on the account state].**
`DungeonEntrance.kt:109` clamps the next floor to `dungeonMembers.maxOf { maxFloor(it) }`. `DungeonFloor.kt:81-89`: `floorAtLevel = (level+1)/2` and `maxFloor = min(floorAtLevel, dungeoneering_floor_unlocked)`. For a Dungeoneering level of 1 or 2, `floorAtLevel = 1`, so after completing floor 1 the clamp returns floor 1 and the countdown generates another floor 1. `DungeonComplete.kt:294-300` already shows the "next floor is not available at your level" branch for that case. The starting Dungeoneering level was not verified in this audit.

**F4. Unlock search is narrow, not dead — [Source].**
`DungeonDeaths.kt:74` probes four wall midpoints: `(x, y+7)`, `(x+15, y+7)`, `(x+7, y)`, `(x+7, y+15)`, where `x,y = minX-1, minY-1`. The fallback at `:50-56` uses `Rectangle(minX-1, minY-1, minX+1, minY+1)`. `Rectangle` takes `(minX, minY, maxX, maxY)` (`upstream/game-server/types/src/main/kotlin/world/gregs/voidps/type/area/Rectangle.kt:5-12`), so this is the 3×3 block at the room's minimum-x/minimum-y corner. Its tiles differ from the midpoints, so the fallback is reachable: it finds a trapdoor on any of those nine tiles, and the `replace` at `:59` then runs. Its coverage is narrow. If neither the probes nor the corner match, `door` stays null, the trapdoor never unlocks, and only a `logger.warn` (`:57`) is written. Runtime placement: in the seeded run (§6) the trapdoor sat at the west midpoint probe, so the fallback was not exercised. Whether the cached map places the trapdoor on a fallback tile elsewhere is **unverified**.

**F5. No reward on boss kill is the expected flow — [Source]; not a defect by itself.**
`DungeonDeaths.kt:60-61` has `TODO rewards`. The design routes the reward through the `End-dungeon` object (step 10), so a kill without a trapdoor click grants nothing by design. The TODO only records that a kill-time reward was considered.

## 3. Ranked uncertainties (at most three)

1. **Does a real combat kill of the spawned `rand_ice_lord_boss_*` unlock a locked trapdoor that the probes can find?** Partly answered for one seed (§6): a controlled `directHit` death through the native damage path unlocked the trapdoor at the west midpoint probe. Still open: an ordinary combat kill (the Icy Bones fight and its attacks), and any placement other than the one seen in this seed.
2. **Does the floor-1 countdown regenerate floor 1 for a level 1–2 account (F3), and what does the reward look like on the second floor-1 completion?** Confirm the starting Dungeoneering level and the `tickOffFloor` result (`DungeonComplete.kt:224`, `:327-334`). Impact: progression, not the first completion.
3. **Does a completed reward survive logout and relog correctly?** Progress and tokens persist (step 14). `dungeon_reward_given` does not, which is intended because `clear` resets it on entry anyway. Low risk, unproven.

## 4. One smallest native test (implemented as patch 0031)

**Name:** `SoloBossTrapdoorUnlockTest`, in `game/src/test/kotlin/content/skill/dungeoneering/`. It repeats the ordinary `InteractObject` entry from `SoloDungeonLifecycleTest` (that helper is private, so it is copied, not shared).

The proposal below is kept as written. The implementation differs in one way: the boss is killed with `directHit` (the native damage path), not by an ordinary combat fight.

**Steps, using only the paths the game uses:**
1. Enter the seeded small c1 floor-1 dungeon through the ring and entrance, as the existing lifecycle test does.
2. Open the boss room with `DungeonRoom.open(player, dungeon)` for the boss room only (the call `DungeonDoors.openDoor` makes). Do not use `unlock_dungeon`, which opens every room.
3. **Assert before the kill:** one `rand_ice_lord_boss_*` NPC exists at the expected room tile, and one `rand_dungeon_end_trapdoor_locked_frozen` object exists at one of the four `findDoor` probes (`DungeonDeaths.kt:74`). If the second assertion fails, the test has proven uncertainty 1(a) and the placement problem is the blocker.
4. Kill the boss through the normal combat or death event path, not by calling the `npcDeath` handler.
5. **Assert after the kill:** the probed object is `rand_dungeon_end_trapdoor_unlocked_frozen`.

Stop there. The reward assertions (`dungeon_floor_1_complete`, `dungeoneering_tokens`, `dungeon_reward_given`) belong to a second test, because they depend on the unlock succeeding first.

**Reproduce (from `upstream/game-server`, JDK 21, non-empty isolated `SOLOSCAPE_TEST_ROOT`, local cache present):**
```sh
./gradlew :game:test --tests 'content.skill.dungeoneering.*' --tests 'content.area.wilderness.daemonheim.*'
```
The existing filter already covers the new class's package.

## 5. Current limits

- One seed only (the WorldTest default `FakeRandom`). The cache map data is not in the repo; the trapdoor placement is seen in this run, not derived from data.
- Boss death is a controlled `directHit`, not an ordinary combat kill.
- No live client, no real combat, no walk to Daemonheim, no whole-process save and restart.
- Multi-member completion is unreachable per F1 and is not claimed as working.
- Only the frozen c1 boss template (`icy_bones`, floor 1+) is enabled. Other bosses are commented out and must not be assumed to work.
- Admin `unlock_dungeon` and `start_dungeon` bypass normal progression. Their results are not earned completion.
- Claims about the account's starting Dungeoneering level (F3) are not verified.

## 6. Native test result (patch 0031)

`SoloBossTrapdoorUnlockTest` (one test) passes with `SoloDungeonLifecycleTest` (four tests): 5 of 5 under explicit filters, with zero failures and zero errors. The run covers one seeded small c1 floor-1 solo dungeon: entry, a fixture-only opening of the boss room, the boss spawn, the locked trapdoor before the kill, a controlled `directHit` death, and the unlocked trapdoor after it. Details, fixtures and limits are in [DUNGEON_BOSS_TRAPDOOR_20261017.md](DUNGEON_BOSS_TRAPDOOR_20261017.md). Evidence: [dungeon-boss-trapdoor-20261017.json](evidence/dungeon-boss-trapdoor-20261017.json).

Observations from this run:
- **Trapdoor placement (seed-specific):** the locked trapdoor was at `base+(0,7)`, the west midpoint primary probe `(x, y+7)`. The F4 corner fallback was not exercised. The cached map is still not in the repo.
- **Rotation in the spawn tile (source-derived, not gameplay-verified):** the boss room has rotation 1. `DungeonMap.tile(room, x, y)` (`DungeonMap.kt:216-219`) passes the already-rotated X into `rotateY` as its x argument. The boss therefore spawned at `base+(8,8)`. With the correct rotation for rotation 1, the room-local (7,7) tile maps to `base+(8,7)`. `DungeonRoom.open` (`DungeonRoom.kt:33-60`) derives both copied coordinates from the original `sx, sy`, which is the consistent convention. The boss stays inside the room, so the trapdoor result is unaffected. This is not repaired here.
- **Death path:** the unlock happened after a `directHit` through the native damage path, with no test call to the `npcDeath` handler. This is a death-pipeline fixture, not combat. Ordinary combat with the Icy Bones attacks is still unproven.
