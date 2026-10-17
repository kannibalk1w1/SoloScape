# Summoning audit — first batch, 17 October 2026

Status: substantial native implementation with fixture coverage; earned progression and physical controller acceptance remain open. Server source is under `upstream/game-server/`.

| Component | Inspected source / evidence | Gap |
| --- | --- | --- |
| Introduction | `game/src/main/kotlin/content/area/asgarnia/taverley/Pikkupstix.kt` explicitly says Wolf Whistle is not implemented; post-quest tutor dialogue is intentionally ungated | Quest metadata/reward text in `data/quest/quests.toml` is not a playable introduction. Do not introduce a quest gate that locks existing users out. |
| Supplies | Pikkupstix opens semantic `summoning_supplies`; its definition is in `data/area/kandarin/feldip_hills/gu_tanoth/gu_tanoth.shops.toml`, including shards/pouches | File location does not imply travel to that shop's directory. Actual coins/charm/tertiary acquisition needs an earned route. |
| Crafting | `content/skill/summoning/SummoningCrafting.kt`, 154 supplied-input pouch/scroll cases | Crafting tests do not gather materials or establish affordability. Dungeoneering enum/index handling is explicitly TODO. |
| Summoning | `Summoning.kt` uses real skill level for requirements and a separate points pool | Two gate regressions pass; draining points is not equivalent to losing the real level. |
| Familiar utility | `FamiliarUtilitySpecialEffectTest`, 44 representative cases | Not proof of every familiar, combat/skilling effect, beast-of-burden screen or native UI. |
| Other systems | Timers, pets, combat specials, burden inventory and enchanted headgear have separate source/test surfaces | Expiry, owner death, dismissal, bank-full recovery and save/Continue need connected acceptance. |

Proposed earned slice: buy pouch/shards through Pikkupstix, earn a gold charm from an audited native drop source and obtain the spirit-wolf tertiary, infuse at a real obelisk, summon, use its supported action, dismiss and save/reload. Verify the native recipe and level before scripting the route; no free-charm grant or new XP balance is authorized by this audit. Preserve the current ungated tutor as an explicit temporary SoloScape interpretation until an introduction is deliberately implemented.

The controller pass should cover pouch selection, scroll source ownership, familiar targeting, dismiss confirmation and return to inventory without movement leakage. A browser experiment provides no evidence for these native interactions. [M6 overview](SOLO_CONTENT_AUDIT.md).
