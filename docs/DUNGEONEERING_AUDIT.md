# Dungeoneering audit — first batch, 17 October 2026

Status: partial native implementation, partial automated evidence, physical acceptance required. Paths below are under `upstream/game-server/game/src/main/kotlin/`.

`content/area/wilderness/daemonheim/DungeonEntrance.kt` explicitly restricts normal players to **floors 1–11 and complexity 1**. Solo entry chooses a small dungeon with player count 1. Admin commands can bypass the restriction; an admin success cannot establish normal-player availability. The entry message itself labels the activity experimental.

| Component | Source finding | Evidence / limitation |
| --- | --- | --- |
| Entry/party | Ring of kinship, inventory/equipment checks, leader ownership, one-person party branch | Six existing party tests cover invitation, settings and leaving, not a full floor. |
| Generation | `content/skill/dungeoneering/DungeonGenerator.kt`: critical/bonus paths, keys, locks and real room templates | Nine new real-template small c1 cases: floors 1/6/11 × seeds 0/1/42. All generate non-null populated rooms with a boss reachable by acquiring accessible keys. |
| Earlier solvability claim | `DungeonGeneratorTest` used `generate() ?: return` with synthetic key tables but no real room templates | Three vacuous high-complexity cases replaced by nine native-config cases in patch 0023. Pure topology cases retained. |
| Rooms/puzzles/NPCs | Room copying, doors, table supplies and NPC spawning exist; generation has estimated chances and TODOs; only Icy Bones has a dedicated boss implementation in this directory | No assertion of complete bosses/puzzles, high complexities or all floor themes. |
| Rewards | `DungeonComplete.kt`: XP, tokens, prestige, floor credit and reward-given guard | Source inspection only in this batch. Need full completion, repeat/reconnect and token persistence checks. |
| Binding/logout | `ItemBinding.kt` maintains bound inventory/ammo; party `playerDespawn` calls `leave`; entry uses an instance and stores kinship/spellbook | This is not resumable floor persistence. Need exit, disconnect, death and bank-full stow checks against real saves. |

The new graph tests treat non-key doors as traversable. They do not walk collision tiles, fight guardians, verify client projection or prove every possible seed. They deliberately cover the currently enabled floor/complexity surface, not hypothetical full Dungeoneering.

Next bounded task: a normal one-player small c1 floor-1 journey, entering through the actual ring/entrance, consuming native starting supplies, binding one item, reaching/fighting the boss, receiving one reward, leaving and saving/reloading. Add failure/quit coverage before enabling more content. Group-required puzzles and high complexities stay deferred. [M6 overview](SOLO_CONTENT_AUDIT.md).
