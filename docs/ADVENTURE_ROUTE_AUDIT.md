# Early-game adventure audit

The pinned server already implements Cook's Assistant, Rune Mysteries and The Restless Ghost. This sprint ran their five existing completion/recovery tests in isolated mutable storage; all passed. Those upstream tests teleport between scenes, so they establish quest logic rather than route accessibility.

Two additional actual-map tests use ordinary walking and native interactions throughout:

- **The Restless Ghost:** start with Father Aereck, accept the quest, walk through the village/swamp, open Father Urhney's real door, obtain and equip the ghostspeak amulet, return to the graveyard, open the coffin and speak to the ghost, walk to the rocks, recover the skull, flee along the route and complete the coffin scene. Verify the completed state and 1,125 Prayer XP, then save/load the native character and compare quest state, location, all instantiated persistent inventories and XP.
- **Castle and banking:** start Cook's Assistant from the actual cook, walk through the castle to the north stairs, open the real doors, reach the Duke upstairs and start Rune Mysteries. Walk back through the Duke's door, climb to the bank floor and deposit the talisman through native banking validation. Save/load and compare both quest states, talisman storage, XP, inventories and location.

The route audit required real doorway approaches and the correct north staircase. Several coordinates used by teleport fixtures cannot be reached by walking from the previous room. No collision flags, objects, quest progress or quest reward items were injected to make these routes pass. These were route corrections in the test, not gameplay fixes.

The broader selected slice also retains the existing gather/mill/Cook completion/commerce/combat/food/save fixture, actual courtyard/village/bridge walking, shared-shop validation and the level-one progression test. Eighteen selected game cases pass; after adding save comparisons the two actual-map route cases were rerun and passed again. The server shadow jar builds and the complete patch stack reproduces 32 files.

Remaining acceptance: complete Cook's Assistant and Rune Mysteries travel entirely on the actual map, further gates/mill and wizard-tower floors, broader content, physical controller playthroughs and live quest progress rendering. These tests do not establish all upstream content as complete.
