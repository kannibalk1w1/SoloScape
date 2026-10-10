# Early-game session route

The automated route uses **existing** Cook's Assistant content: speak to the Lumbridge cook and accept; buy a bucket and empty pot from the Lumbridge general store; milk the prized cow; collect the super large egg; ask Millie for extra-fine flour; pick wheat, put grain in the hopper, operate the controls and collect flour; return to the cook. The test then deposits/withdraws coins, nets shrimp, cooks, fights a chicken, eats and loads a native saved character. Only a small net and 10 coins are starting fixtures; ingredients, rewards, XP, quest progress and loot are obtained through ordinary validated instructions/content handlers. Valid deterministic random rolls remove chance from the assertions.

`SessionAdventureTest` runs these handlers on spaced disposable fixture tiles. It walks between the fixtures instead of teleporting, but does not prove real-map access to every ingredient or controller usability. A separate test follows actual upstream Lumbridge navigation edges on cache collision data, in both directions: courtyard (3222,3218), gate (3236,3218), bridge west (3236,3225), village (3230,3232), shop exterior (3222,3241), trees (3226,3245), north bridge (3235,3261). It does not open every route door or climb the mill.

The route found and repaired a concrete commerce bug: shared general-store inventory was sent to the client but unavailable to the native interface validator. The store now binds a transient inventory reference while open. It remains shared between shoppers, unbinds on close and never enters character-save inventories. Mismatched item identity in the correct stock slot still fails validation. Existing specialist-shop and sample/selling tests remain passing.

For the physical playthrough, use a disposable launcher character:

1. Get a small net and a few coins through normal play. Accept Cook's Assistant in Lumbridge castle's kitchen.
2. Open the general-store door and buy the bucket/pot. Try both native and custom shop surfaces; confirm quantities and prices before buying.
3. Follow the quest's own guidance for the milk, egg and flour. The supplied revision uses top-quality milk, a super large egg and extra-fine flour; ordinary versions will not complete it. Speak to Millie, use the hopper/controls and fill the pot. Check item-on-object selection and B behavior at every stage.
4. Return to the cook and confirm completion/rewards. Travel upstairs to bank; deposit and withdraw an item, including a quantity entry and cancellation.
5. Net shrimp at an appropriate fishing spot, cook some, fight a chicken and eat. Record item counts, XP, quest state and position.
6. Save & Quit, Continue and compare that record. Repeat with custom screens disabled, then check remapped hints and right-stick scroll with a populated bank.

Real-map locations are provided by upstream spawn/cache data. The cook is configured at (3209,3215); shopkeeper at (3214,3240); Millie at (3169,3306). Super-large eggs have configured spawns at (3191,3276) and (3227,3299). NPCs can wander. Gate/door, floor-change, quest-guide readability and every physical interaction in this route remain explicit acceptance checks. This is a targeted early-game audit, not a claim that all upstream content is complete.
