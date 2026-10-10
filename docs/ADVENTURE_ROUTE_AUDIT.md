# Early-game adventure audit

The pinned server already implements Cook's Assistant, Rune Mysteries and The Restless Ghost. This sprint ran their five existing completion/recovery tests in isolated mutable storage; all passed. Those upstream tests teleport between scenes, so they establish quest logic rather than route accessibility.

Two additional actual-map tests use ordinary walking and native interactions throughout:

- **The Restless Ghost:** start with Father Aereck, accept the quest, walk through the village/swamp, open Father Urhney's real door, obtain and equip the ghostspeak amulet, return to the graveyard, open the coffin and speak to the ghost, walk to the rocks, recover the skull, flee along the route and complete the coffin scene. Verify the completed state and 1,125 Prayer XP, then save/load the native character and compare quest state, location, all instantiated persistent inventories and XP.
- **Castle and banking:** start Cook's Assistant from the actual cook, walk through the castle to the north stairs, open the real doors, reach the Duke upstairs and start Rune Mysteries. Walk back through the Duke's door, climb to the bank floor and deposit the talisman through native banking validation. Save/load and compare both quest states, talisman storage, XP, inventories and location.

The route audit required real doorway approaches and the correct north staircase. Several coordinates used by teleport fixtures cannot be reached by walking from the previous room. No collision flags, objects, quest progress or quest reward items were injected to make these routes pass. These were route corrections in the test, not gameplay fixes.

The broader selected slice also retains the existing gather/mill/Cook completion/commerce/combat/food/save fixture, actual courtyard/village/bridge walking, shared-shop validation and the level-one progression test. Eighteen selected game cases pass; after adding save comparisons the two actual-map route cases were rerun and passed again. The server shadow jar builds and the complete patch stack reproduces 32 files.

Remaining acceptance: broader content, physical controller playthroughs and completed live quest progress rendering. These tests do not establish all upstream content as complete.


## Full journeys continuation — 10 October

Two new `FullAdventureJourneyTest` cases now pass individually on the actual map:

- **Cook's Assistant:** native empty pot; courtyard/north bridge; cow gates, bucket and prized cow milk; chicken gate and egg; west-bank mill route; Millie dialogue; actual wheat; both native mill ladder levels; hopper fill/controls and flour collection; return and reward; completed state, coins, noted sardines and Cooking XP; native save/load of quest, tile, XP and persistent inventories.
- **Rune Mysteries:** Duke dialogue/item; castle door/north stairs; west road and tower doors; native basement ladder and Sedridor delivery/package; outside travel and native border crossings; Varrock gates and Aubury's actual shop/research notes; return via the same doors/gates/borders/tower; Sedridor completion/air talisman; native save/load of quest, tile, XP and persistent inventories.

The existing earned-progression fixture is retained. New journeys do not create NPC/scenery fixtures, grant quest items or progress, change collision or use teleport commands. The test player begins in the quest-giver's scene; native object transitions perform the normal scene changes. Raw cache ladder IDs are looked up by integer rather than assuming an assigned string name.

The harness waits for real doors to change state, for native three-tick border delays to end, and for each crossing's actual opposite-side endpoint. A new Walk sent during a delay is correctly ignored by the native server. The test must wait rather than change that behavior. One diagnostic region-acknowledgement hypothesis was ruled out and removed; the headless player is not a networked graphical client.

Several reference/guessed tiles were blocked by native scenery; ordinary walking diagnostics and a private collision plot corrected the route. A valid mill hopper approach was required. These are harness changes; no production movement/content/cache data was repaired in this continuation. Final combined-suite/export/native evidence is in [journeys validation](CONTROLLER_JOURNEYS_VALIDATION.md) and the [combined report](MORNING_REPORT.md).
