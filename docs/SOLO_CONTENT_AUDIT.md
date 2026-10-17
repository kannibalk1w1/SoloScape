# M6 first audit batch — 17 October 2026

Baseline: merged `502df96`, research `5592130`, client stack 0053/server 0022 before this batch. This is a bounded audit, not completion of M6 or a claim that all upstream content works. Source paths below are relative to `upstream/game-server/` at the pinned revision with SoloScape patches.

The owner reports being happy with current Deck testing so far. That is positive general play feedback; the exact installed build, tested activities, suspend, battery and abrupt-exit cases were not supplied. It does not close individual acceptance campaigns. Subsequent corner-running/RT changes have not been physically accepted.

## Evidence inventory

| Surface | What is actually established | Remaining gap |
| --- | --- | --- |
| Quest catalogue | `data/quest/quests.toml` has 195 top-level metadata tables. Source directories are not completion evidence; some contain only travel/items. | Do not label 195 quests playable. |
| Cook's Assistant, Rune Mysteries, Restless Ghost | Existing actual-map journeys walk through native doors, ladders, resources and dialogue; completion/reward and native save/reload assertions. | Physical controller completion and session pacing. |
| Blood Pact | Earlier earned graphical/controller-gateway route; native completion fixture. | Broader human combat/instance acceptance. |
| Imp Catcher, Druidic Ritual | Supplied-material completion fixtures and graphical evidence in historical reports. | Earned bead/meat acquisition and full controller travel. |
| Production | Fresh early suite: 53 cases, including every pottery recipe and level gates. | Gathering-to-recipe travel and interruption on a physical pad. |
| Slayer | Masters, task kills, XP/streak/points and combat formulas have representative tests. | Level-one earned master journey, varied terrain and target persistence. |
| Summoning | Pouch/scroll recipes, real-level gating and representative familiar utility effects tested. | Earned introduction/resources, native panel ownership, expiry/dismissal/save. See [audit](SUMMONING_AUDIT.md). |
| Dungeoneering | Real-template small c1 floors 1/6/11 now checked with three seeds each, plus party and topology cases. | Full entry/combat/boss/reward/exit/save journey. See [audit](DUNGEONEERING_AUDIT.md). |
| Bosses, broad skills and activities | Source exists across combat/skills/activities, but this batch does not enumerate or validate every activity. | M6-01 remains open; sample shared combat/production contracts before expanding. |

Fresh native M6 selection: **273 cases across 12 suites**, zero failures/errors/skips, before the subsequent movement change. [Public summary](evidence/m6-content-20261017.json). Source-backed counts and fixture limits supersede historical totals; reports themselves remain unchanged. Reproduce with `bash scripts/test-content-coverage.sh --group m6`. The default group retains early quest/production coverage. Each run uses isolated mutable storage, discards selected old XML, archives fresh results, rejects missing/empty suites and records patch hashes. No profile or cache binary is published.

## First progression slice

Choose **Lumbridge self-sufficiency**, using existing native content: obtain basic containers/tools, gather Cook's ingredients, complete the actual mill/quest journey, gather and cook food, bank supplies, fight a low-level enemy, then save/Continue with XP, items, quest state and tile preserved. Aim for one comfortable handheld session; measure its duration rather than asserting a time before playtesting.

Keep the earned Cook journey separate from `SessionAdventureTest`, whose commerce/food/combat coverage uses spaced fixtures and a declared starting allowance. Combining their passing reports does not prove a single earned journey. The next implementation batch should connect the missing earned gathering/food/combat segment, with no spawned resources, admin travel or quest-item injection. Start from the actual profile starter inventory and document any deliberate allowance. Fix only reproducible blockers; no new XP formula, quest rewrite or loot rebalance is justified yet.

## Queue after this batch

1. Finish the small [corner movement/precision](CONTROLLER_CORNER_MOVEMENT.md) change and local regressions; human safe-spot acceptance follows.
2. Connect the one earned progression slice above, including inventory-full, cancellation, death and save/reload boundaries.
3. Exercise one complete supported Dungeoneering floor through native interactions before adding floors or puzzles.
4. Prove one earned Summoning resource/craft/summon/dismiss/reload route before rebuilding its introduction.
5. Measure representative region transitions and suspend/shutdown on Deck; then consider the isolated backport lab.

MMO classification and bot constraints are in [MMO dependencies](MMO_DEPENDENCY_AUDIT.md) and [AI adventurers](AI_ADVENTURERS.md). M6 checkboxes remain open where this batch provides only a first sample.
