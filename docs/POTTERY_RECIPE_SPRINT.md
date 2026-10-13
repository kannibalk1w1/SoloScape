# Pottery recipe follow-up — 13 October 2026

The first follow-up after the r24 Deck deployment fixes unfired pie dishes producing bowls. They now produce pie dishes with the missing level-7/10-XP firing row. Fired pot lids now require level 25, matching their shaping recipe.

The [archived 2011 Crafting–Pottery knowledge base](https://2011.rs/kb/crafting_pottery) lists pie dishes at level 7, with 15 XP shaping and 10 XP firing, and pot lids at level 25 with 20 XP per stage. These values also appear in the [RuneHQ item reference](https://www.runehq.com/item/pie-dish-unfired).

Server patch `0020-pottery-recipe-products-and-levels.patch` adds all five shaping and firing cases with exact product/XP assertions. Firing uses mixed inventories with an existing finished pot and soft clay before the unfired item; unrelated items remain unchanged. Below-level cases preserve the unfired pie dish/pot lid and grant no XP.

All **53 selected native-server cases pass**, including **15 pottery cases**, with no failures, errors or skips. The [aggregate summary](evidence/server-pottery-recipes.json) contains no saves or authentication. All 53 modified/patched server files reproduce from the exported patch stack.

This is server regression coverage with supplied materials and levels. The Deck remains on merged content build r24 for the current playtest; these follow-up recipe changes have not been deployed or graphically accepted. Druidic Ritual's native graphical route, physical recipe navigation, pottery breakage probabilities and the One Small Favour prerequisite for pot lids remain further coverage/work.
