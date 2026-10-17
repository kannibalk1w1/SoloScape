# Summoning supply acquisition audit: spirit wolf materials, 17 October 2026

Baseline: `9a473c3` on `validation/summoning-acquisition-20261017`, with server patches through 0028 applied. Patch: `patches/server/0029-summoning-supply-acquisition.patch` (new test file only; no production change). Machine-readable results: `docs/evidence/summoning-acquisition-20261017.json`.

## Source-backed audit

**Recipe (read from the cache, not the TOML).** The test reads the same `spirit_wolf_pouch` parameters `SummoningCrafting` uses. Measured values:

| Ingredient | Item | Quantity | Shop sells it | Native source |
| --- | --- | --- | --- | --- |
| Charm | `gold_charm` (12158) | 1 | no | white wolf charm table, see below |
| Shards | `spirit_shards` (12183) | 7 | yes | summoning supplies shop |
| Blank pouch | `pouch` (12155) | 1 | yes | summoning supplies shop |
| Tertiary | `wolf_bones` (2859) | 1 | no | white wolf drop table, guaranteed |

The tertiary is `summoning_pouch_req_item_id_1`, so `wolf_bones` is the tertiary.

**Pikkupstix and the shop.**
- Spawn: `data/area/asgarnia/taverley/taverley.npc-spawns.toml:4`, `{ id = "pikkupstix", x = 2925, y = 3443 }`.
- NPC shop link: `data/area/asgarnia/taverley/taverley.npcs.toml:6`, `shop = "summoning_supplies"`.
- Shop definition: `data/area/kandarin/feldip_hills/gu_tanoth/gu_tanoth.shops.toml:23`. The Gu'Tanoth NPC also uses this shop, and `WishingWell.kt` opens it.
- Dialogue: `game/src/main/kotlin/content/area/asgarnia/taverley/Pikkupstix.kt`. The menu order is "So, what's Summoning all about" (choice 1) and "Can I buy some Summoning supplies, please?" (choice 2), which calls `openShop("summoning_supplies")`.
- Stock defaults: antlers 10, lizard skull 10, five feather headdresses at 0, spirit shards 65000, pouch 5000, spirit shard pack 65000. No charm or wolf bones are stocked.

**Prices.** The native charge matches `Price.of`, which is the cache item cost: spirit shards 25 each and blank pouch 1 each. The TOML `price` values disagree: `data/skill/summoning/summoning.items.toml` has spirit shards `price = 24` (line 1029) and pouch `price = 4` (line 902). The test asserts the charge against the native cost, so the discrepancy is recorded here and was not rebalanced. I did not trace where `ItemDefinition.cost` is loaded.

**Charm and tertiary source.**
- `data/entity/npc/animal/wolf/wolf.npcs.toml:60-70`: `wolf_stronghold_of_security` uses `drop_table = "white_wolf"`. The cache confirms `drop_table=white_wolf` and that it resolves to `white_wolf_drop_table`.
- Spawns: `data/area/misthalin/barbarian_village/stronghold_of_security/stronghold_of_security.npc-spawns.toml:6-8`.
- `data/entity/npc/animal/wolf/wolf.drops.toml`: `white_wolf_drop_table` (type all) always drops `wolf_bones`. It also rolls `white_wolf_charms` with `members = true`. That table has roll 100000 and `gold_charm` at chance 9845, which is 9.845%.
- `DropTable.random` uses the global `random`, so tests can control the roll with `setRandom`.
- `NPCDeath.dropLoot` also filters members-only items through `World.members || !it.def.members` after the roll.

## What the new tests cover

Test class: `upstream/game-server/game/src/test/kotlin/content/skill/summoning/SummoningSupplyAcquisitionTest.kt`, four tests.

1. **Pikkupstix opens the summoning supplies shop from the second choice.** The NPC is created at the configured Taverley tile `2925,3443`. The player talks to him through `npcOption("Talk-to")`, and each dialogue stage is asserted: the tutor's greeting, the choice menu (`dialogue_multi`), the player's chosen line (`dialogue_chat`), then the tutor's reply. Then choice 2 (`dialogueOption(2)`) opens `summoning_supplies`.
2. **Recipe quantities of blank pouch and spirit shards buy through shop packets.** Coins are supplied as 1000. The test buys shards with `Buy-5`, `Buy-1`, `Buy-1` and then the blank pouch with `Buy-1`, all through the shop stock interface. It asserts the inventory counts, the shop stock decreases, and the coins decrease by the native cost of 7 shards at 25 and 1 pouch at 1.
3. **Insufficient coins grant and consume nothing.** The test supplies 24 coins, one short of a shard. `Buy-5` of spirit shards must show "You don't have enough coins.", leave the shard count and coins unchanged, and leave the shard stock unchanged.
4. **White wolf charm drops only for members, with a controlled roll.** `setRandom` returns the lowest value. With `world.members` set to `true`, the table yields `gold_charm` and `wolf_bones`. With it set to `false`, the table yields `wolf_bones` only. The test also asserts that `wolf_stronghold_of_security` maps to `white_wolf_drop_table`.

**Fixtures are explicit.** Coins are supplied and stated as such. The charm and wolf bones are never added to the inventory. The drop test is a table check, not a kill.

No test in this class writes a save, so `SOLOSCAPE_TEST_ROOT` is not used by it. The wrapper still sets it for the other classes run in the same invocation.

## Commands and results

The checked-in runner now exposes this bounded group:

```bash
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group summoning
```

Coordinator verification used that command with the local JDK 21. All 14 cases
passed with fresh XML archived under the isolated coverage directory. The runner
removes selected historical XML before invocation, records patch digests and
rejects missing, failing or skipped selected results. This is a second run;
the worker invocation below records the original evidence.

```
bash .runtime/earned-lumbridge-20261017/run-tests.sh \
  content.skill.summoning.SummoningSupplyAcquisitionTest \
  content.area.asgarnia.taverley.PikkupstixTest \
  content.skill.summoning.SummoningObeliskTest \
  content.skill.summoning.SoloSpiritWolfLifecycleTest \
  content.skill.summoning.SummoningLevelGateTest
```

`BUILD SUCCESSFUL in 16s`. Fresh XML, copied to `.runtime/earned-lumbridge-20261017/acq-xml/`:

| Class | Tests | Failures | Errors | Skipped |
| --- | --- | --- | --- | --- |
| SummoningSupplyAcquisitionTest | 4 | 0 | 0 | 0 |
| PikkupstixTest | 2 | 0 | 0 | 0 |
| SummoningObeliskTest | 4 | 0 | 0 | 0 |
| SoloSpiritWolfLifecycleTest | 2 | 0 | 0 | 0 |
| SummoningLevelGateTest | 2 | 0 | 0 | 0 |

Total: 14 tests, all passing.

**Patch.** The new file was exported on its own with `git diff --no-index /dev/null`, with the `upstream/game-server/` prefix stripped. `scripts/verify_patches.py server` reports `all 65 modified/patched source files match the exported stack`, including the new test. `git apply -R --check` on 0029 passes.

**Earlier attempts.** Several runs failed before the final one, all in the test code:
- Compile errors from missing imports (`shop()`, `hasOpen`, `dialogue`).
- A wrong Gradle filter that matched no tests.
- Shop-open failures caused by one continue too few after choice 2. The per-step diagnostics showed `dialogue_chat1` (the player's line) before the tutor's reply. The helper now asserts each stage, as the coordinator asked.

## Limitations

- **Created NPC at configured coordinates.** The Pikkupstix NPC is created at the configured spawn tile. The test does not load the world spawn files.
- **Coins are supplied.** 1000 coins for the purchase, 24 for the insufficient case. No coin source is tested.
- **The charm and bones roll is controlled.** The test forces the roll to the lowest value. It does not sample the 9.845% chance, and it does not kill a wolf or run `NPCDeath.dropLoot`.
- **No travel or combat.** No walk to Taverley or the Stronghold of Security, and no fight.
- **Summoning-item price discrepancy** (see the audit above) is recorded, not corrected.
- **Not exercised here:** Wolf Whistle (not implemented), the infuse-and-summon lifecycle with these shop materials (covered by `SoloSpiritWolfLifecycleTest` with supplied materials), and the Gu'Tanoth shop.

## Remaining connected earned-path gap

The shop and table each have a native source, but they are not connected by an earned route. The connected path is: a real wolf kill at the Stronghold of Security, which rolls the charm (9.845%) and always gives wolf bones, plus coins that were earned, then a shop purchase of 7 shards and 1 pouch, then infusion and summoning. Each leg is only partly proven. The drop table is proven only with a controlled roll; the kill is unproven, the coins are supplied, and the purchase uses supplied coins at Pikkupstix. The smallest next action is a test that kills a white wolf through the native combat path with a controlled roll, and then checks that the loot reaches the player's inventory.
