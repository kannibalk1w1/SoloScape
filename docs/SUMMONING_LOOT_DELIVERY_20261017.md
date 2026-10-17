# Native Summoning ingredient loot delivery — 17 October 2026

The Stronghold wolf's native death and Take paths now have a connected ingredient-delivery check. In a members world, the controlled native kill publishes one gold charm and one wolf bones, and both reach the player's inventory exactly once through ordinary Take instructions. This closes one gap left by the [earlier table/shop audit](SUMMONING_ACQUISITION_20261017.md); it does not establish an earned Summoning journey.

## Fixtures and observed behaviour

The test creates `wolf_stronghold_of_security` at its configured spawn tile, **1873,5239**, with the player adjacent at **1873,5238**. It uses the real NPC definition, native `Character.hit` with explicitly supplied fatal damage equal to the native starting hitpoints, queued damage/death processing and `NPCDeath.dropLoot`. The random roll is controlled after launching the hit. Neither ingredient is manually created or added to inventory.

The native death is witnessed by zero hitpoints, the death state, the exact player as damage-attributed killer, and corpse hide/removal. A further tick publishes queued floor items. The members case takes each actual floor record through the normal instruction helper, checks amount one in inventory and removal from the floor, then verifies that further ticks do not duplicate either item.

The second case checks nonmembers through the same native death path. **Both gold charm and wolf bones are members-only in the authorized compatible cache.** The direct table roll can list wolf bones in a nonmember world, but `NPCDeath` subsequently filters member-only item definitions. Neither ingredient reaches the floor or inventory in that mode. The test records that existing behaviour; it changes no membership rule or drop table.

## Validation and earlier failures

Server patch 0046 adds only `SummoningLootDeliveryTest`; production Kotlin/data are unchanged. The selected Summoning group now passes **22 native cases, no failures or skips**, including the two new cases. Both source exports match: 93 server files and 140 client files. Matched native stack 46/56 is prepared; jar bytes remain identical to 45/56 because this patch changes tests only. The [sanitized evidence](evidence/summoning-loot-delivery-20261017.json) records those hashes and fresh selected-suite results.

Early probes asserted the death queue's internal presence/completion too soon and inspected loot before publication. The final test observes native death completion and actual floor results instead. An initial nonmember expectation assumed wolf bones were available because the table listed them; cache inspection and the final item filter disproved that test premise. Neither finding justified a production change. Gradle's configured `failFast = true` explains sibling tests being marked skipped after a failure; skipped cases never counted as acceptance. Failed logs/XML remain under the assigned private `.runtime/summoning-loot-delivery-20261017` directory.

## Remaining scope

Fatal damage and deterministic drop selection are explicit fixtures. This is not a full fight, a probability sample of the 9.845% charm roll, actual loaded-spawn validation, travel, earned coins, supplies purchase, infusion or summoning with these recovered ingredients. Wolf Whistle remains unimplemented. Earlier independent shop/infusion/lifecycle checks still retain their stated fixtures and limits.

No graphical controller, physical Deck, save/restore or stopped-world loot-persistence acceptance is added by this test. The [grave/floor persistence P1](GRAVE_PAUSE_PERSISTENCE_PLAN.md) stays open. Owner profiles and Deck installation were not used.
