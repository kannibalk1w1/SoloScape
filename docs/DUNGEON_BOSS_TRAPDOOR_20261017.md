# Dungeon boss trapdoor contract — 17 October 2026

One native contract for the enabled normal-player solo path: small, complexity 1, floor 1, one player. It checks that a configured `rand_ice_lord_boss_*` spawns in the cached boss room, that the locked end trapdoor is in that room before the kill, and that the trapdoor is unlocked after a controlled death. It stops there. Reward, the next-floor countdown and the full floor are not touched.

Result: **pass**. `SoloBossTrapdoorUnlockTest` (1/1) and `SoloDungeonLifecycleTest` (4/4) are green under explicit filters, with zero failures and zero errors. The unlock happened on the real cached map through the native death pipeline.

The source audit this extends is [DUNGEONEERING_COMPLETION_AUDIT_20261017.md](DUNGEONEERING_COMPLETION_AUDIT_20261017.md), §6. Evidence: [dungeon-boss-trapdoor-20261017.json](evidence/dungeon-boss-trapdoor-20261017.json).

## What the test does

| Step | Kind | What happens |
|------|------|--------------|
| Ring | **Supplied fixture** | `ring_of_kinship` is injected into the inventory. The tutor purchase is not exercised. |
| Entry | **Ordinary entry** | `Climb-down` from the legal western approach `(3454,3723,0)` of the eastern entrance: once to start the party, once to enter. The party choice uses the normal dialogue helper. The steps are copied from `SoloDungeonLifecycleTest`, because that helper is private. |
| Seed | **Fixed seed** | WorldTest's deterministic `FakeRandom`, set in `beforeEach`. No other seed is applied. |
| Boss room | **Fixture setup** | `DungeonRoom.open(player, dungeon)` is called for the boss room only. No other room is opened. `unlock_dungeon` and `start_dungeon` are not used. The player is not relocated. |
| Spawn | **Asserted** | Exactly one `rand_ice_lord_boss_*` spawns. Its id is in the configured `boss_spawns.icy_bones` ids. Its tile matches the native spawn formula. |
| Trapdoor, before | **Asserted on cached map** | Exactly one `rand_dungeon_end_trapdoor_locked_frozen` is found in the 16×16 boss room. No unlocked trapdoor exists yet. |
| Native search path | **Classified** | The test records whether the native search would find the trapdoor: a primary probe, the 3×3 corner fallback, or neither. Finding neither is a test failure. |
| Death | **Controlled death fixture (not combat)** | One `directHit` of the boss's full constitution through `CombatApi.damage`, the same call `TzhaarFightCaveTest` uses. The test does not call the `npcDeath` handler. No attacks, levels, equipment or walking are exercised. |
| Trapdoor, after | **Asserted** | The locked object is gone, and exactly one `rand_dungeon_end_trapdoor_unlocked_frozen` is in the room, on the same tile. |

## Results from the final run

Run with explicit filters, from the isolated runner:

```sh
bash .runtime/earned-lumbridge-20261017/run-tests.sh \
  'content.skill.dungeoneering.SoloBossTrapdoorUnlockTest' \
  'content.skill.dungeoneering.SoloDungeonLifecycleTest'
```

`.runtime/earned-lumbridge-20261017/run-tests.sh` is not executable in this checkout, so it was run as `bash <script> <filters>`. Its contents were not changed.

| Suite | Tests | Failures | Errors | Skipped |
|-------|------:|---------:|-------:|--------:|
| `SoloBossTrapdoorUnlockTest` | 1 | 0 | 0 | 0 |
| `SoloDungeonLifecycleTest` | 4 | 0 | 0 | 0 |

Trapdoor classification from the run:

- The room has rotation 1 and base `Tile(6496, 96, 0)`.
- The boss spawned at `Tile(6504, 104, 0)`, `rand_ice_lord_boss_0`.
- The locked trapdoor was at `Tile(6496, 103, 0)`, which is base `+(0,7)`: the west midpoint primary probe `(x, y+7)`.
- The corner fallback was not exercised.

The JUnit XML for both suites is archived privately under `.runtime/boss-trapdoor-20261017/` (git-ignored, not published). Digests are in the evidence JSON.

## Coordinator reproduction

The checked-in runner independently reproduces the same five cases with fresh
isolated XML and recorded patch hashes:

```bash
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group dungeon
```

All five pass without failures, errors or skips. Source/patch and the worker's
archived XML digests were independently checked before this rerun.

## Earlier runs (not product evidence)

Three runs before the final one failed in test authoring. None of them is product evidence.

1. A missing `inventory` import (compile error). Fixed.
2. The first object sweep used `DungeonMap.tile(room, x, y)`, which returned only about five distinct tiles. That helper's rotation logic is discussed below. The sweep was switched to base-relative tiles. Once the sweep covered the room, the trapdoor was found and the test passed. The diagnostic prints were then removed.
3. A `rm` step was blocked by a safety check and did not run. The archive copy overwrites the same filenames, so no removal was needed.

## Source observations (not repaired)

- **Spawn tile and rotation.** `DungeonMap.tile(room, x, y)` (`upstream/game-server/game/src/main/kotlin/content/skill/dungeoneering/DungeonMap.kt:216-219`) computes `rotY = rotateY(rotX, y, room.rotation, 15)`. It passes the already-rotated X in the x position. For rotations 1 and 3, the Y coordinate then depends on the wrong input. In this run, the boss spawned at base `+(8,8)`. Using the original coordinates, as `DungeonRoom.open` does for the copied zone, room-local (7,7) maps to base `+(8,7)` for rotation 1. This is derived from the helper formulas, not from a gameplay check. The boss stays inside the room, and the trapdoor result is unaffected.
- **F4 fallback.** The corner fallback is not dead. It searches a 3×3 block at the room's minimum-x/minimum-y corner (`DungeonDeaths.kt:50-56`). It did not fire in this run, so its runtime use is unverified.
- **Death path.** `DungeonDeaths.kt:59` runs `replace` before the `killer` check, so the unlock does not depend on the killer. The test attributes the hit to the player anyway.

## Digests

| Artifact | SHA-256 |
|----------|---------|
| `patches/server/0031-dungeon-boss-trapdoor-contract.patch` | `5bbdcae553d09be0d0671c6ddd6486e1770fecfd9b07e3c472f8f0187ca31da0` |
| `upstream/game-server/game/src/test/kotlin/content/skill/dungeoneering/SoloBossTrapdoorUnlockTest.kt` | `2710c23bc5faa3f4f01e9687b582ea6310cfce2bc21ed9f7223502b0ea7773ee` |

Patch checks: `git apply -R --check` passes against the tree. `python3 scripts/verify_patches.py server` reports that all 67 modified or patched source files match the exported stack. `git diff --check` is clean.

## Limitations

- One seed only (WorldTest's deterministic `FakeRandom`). Other seeds, and other trapdoor placements, are not tested.
- The boss is killed with `directHit`, not by ordinary combat. Attacks, Icy Bones' box and cone attacks, levels and equipment are not exercised.
- No walk to the room, no live client, and no whole-process save or restart.
- Reward, `dungeon_reward_given`, the countdown, the floor credit and the full floor are not tested.
- The cached map data is owner-supplied and read-only. It is not in the repo, and no assets or native source bodies were published. The only native source published is the new test in patch 0031.
- The cache-derived placement is seen in this run only, not derived from data.
