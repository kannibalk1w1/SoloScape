# Connected spirit wolf supplies — 17 October 2026

One native test now connects wolf ingredient drops, Take, supplies purchases, pouch infusion and summoning on the **same level-1 player and inventory**. It strengthens the joins between the earlier [loot-delivery](SUMMONING_LOOT_DELIVERY_20261017.md), [shop/table](SUMMONING_ACQUISITION_20261017.md) and lifecycle checks. It is not an earned Summoning journey and introduces no production gameplay change.

## Actual connected path

The test creates the Stronghold wolf at its configured tile 1873,5239, supplies a fatal native hit equal to its observed hitpoints, and controls the native drop roll. It waits for zero hitpoints, death state, the exact player as killer and corpse completion. Native NPCDeath then publishes a gold charm and wolf bones. Ordinary Take instructions move each actual floor record into the player's inventory once; neither ingredient is added by the test.

An explicit fixture teleport takes that same player to Pikkupstix. Only 1000 coins are supplied. Native Talk-to, dialogue choice 2 and Buy-1 instructions purchase the cache recipe's seven spirit shards and one blank pouch. Assertions cover native prices, stock decrements, coins and retention of both recovered ingredients. The native interface-close API closes the shop; no controller/button acceptance is implied.

A second fixture teleport takes the player to the existing obelisk. Native object/interface instructions infuse one spirit wolf pouch, consuming those actual recovered/purchased materials and granting exactly the cached infusion XP. Native Summon consumes that pouch, spends the cached point cost and grants exactly the cached summon XP. Exactly one spirit wolf exists, and the native owner resolver returns the same Player object. Twenty further ticks leave one owned familiar and no duplicated material, pouch or floor ingredients.

The recipe is explicitly checked as 1 gold charm, 1 wolf bones, 7 spirit shards and 1 blank pouch. Both wolf ingredients are members-only in the supplied compatible cache, so this case uses a members world. Summoning starts at level 1 with zero XP; no skill is raised to bypass the recipe requirement. Membership/RNG fixture changes are restored.

## Validation and authoring corrections

Claude Haiku authored the compact connected case. Coordinator review added explicit native shop identity, the recorded recipe, death-completion assertions, exact summon XP, live familiar ownership and further-tick checks, then independently reran it. The first worker run addressed a nonexistent shop Close component and failed at that test instruction; switching to the existing native interface-close API fixed the fixture. No production defect or new Close widget was inferred.

Server patch 0047 adds only `ConnectedSpiritWolfSupplyTest`. The standard runner's Summoning group now includes it and passes **23 native cases, zero failures/errors/skips**. Source exports match 94 server / 140 client files. Matched native 47/56 preparation passes, with production jar bytes unchanged from 46/56. Root tooling passes 276 cases with one existing optional skip. [Sanitized evidence](evidence/connected-summoning-20261017.json).

```sh
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group summoning
```

Final fresh selected XML/patch identities are archived under `.runtime/content-coverage/1792272596212457992/`; standalone review logs and superseded worker evidence remain in `.runtime/connected-summoning-20261017/`. No native binary, cache or owner state is committed.

## Still unproven

Fatal damage, drop RNG, coins and travel are supplied fixtures. This does not prove a balanced fight, 9.845% sampling, an earned coin source, walking to the locations, loaded NPC spawn configuration, Wolf Whistle, physical controller use or a complete solo progression route. The connected case does not save/reload; the separate spirit-wolf lifecycle cases retain their own supplied-material and same-JVM reload limits. [Grave/floor persistence while closed](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains a P1. No Deck install, save transfer or release publishing occurred.
