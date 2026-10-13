# Dependable Deck sessions: sprint progress

Started 13 October 2026 from the [proposal](NEXT_DECK_SESSION_SPRINT.md). This log records completed batches and what each one does and does not establish. Physical controller, suspend/resume and Gaming Mode acceptance still come from owner playtests.

## Batch 1: save string serialization (server patch 0022)

**Problem.** `ConfigWriter.writeValue` wrapped strings in quotes without escaping them. A clan name, friend, ignore or recent-event text containing `"` ended the string early. A trailing `\` turned the closing quote into an escaped quote, so the rest of the save was read as one string. The profile tools validate saves with Python's strict `tomllib` before backup, import and Continue. Raw backslashes such as `C:\Clan` or raw control characters made the whole save fail validation there.

**Fix.**
- The writer emits TOML basic strings. It escapes `\\`, `\"`, `\b \t \n \f \r` and other control characters (`\uXXXX`). Plain strings and keys keep exactly the same bytes as before.
- Keys outside TOML's bare-key alphabet are quoted automatically: empty keys, spaces, quotes, dots, `quest:` prefixes and similar. Previously spaces were quoted only when a caller asked.
- The native reader decodes the same TOML escapes, including `\UXXXXXXXX`, and decodes text explicitly as UTF-8. Unknown legacy sequences such as `\p` and `\users` keep their old literal meaning. A string without a closing quote is now rejected instead of silently swallowing the rest of the save; failed loads keep the existing backups intact.
- Atomic replacement is unchanged: a failed write leaves the previous save.

**Compatibility boundary.** Older saves containing a raw `\` followed by `b t n f r u U \` or `"` now decode those as TOML escapes, matching what `tomllib` already did. Shipped game data contains none of these sequences; its only escape is `\"`, which still decodes the same. Upstream's four reader expectations that deliberately kept `\n`, `\t` and `\u00E9` undecoded were updated to the TOML meaning.

**Evidence (host, isolated worktree).**

| Check | Result |
| --- | --- |
| Server `:config:test` | 104 pass, 0 fail |
| Server `:engine:test` (includes new `PlayerSaveEscapeTest`) | 1261 pass, 0 fail, 3 skipped |
| Server `:game:test` | 3855 pass, 0 fail, 9 skipped |
| `scripts/test_profiles.py` (new strict-`tomllib` cross-check) | 20 pass |
| `verify_patches.py server` | all 60 modified/patched files reproduce |
| Fresh, repeated and upgrade application of the full stack on the pinned base | byte-identical to the working tree |

New regressions cover:
- quotes, backslashes, trailing backslashes, control characters, Unicode/emoji and 99/100-byte buffer boundaries;
- escaped values inside lists and maps followed by further fields;
- quoted friend keys;
- legacy raw backslashes and invalid `\u` escapes;
- unterminated strings;
- full `PlayerSave` save/reload, three repeated Save & Quit cycles, and reload from a copied backup;
- the exact writer bytes decoded by `tomllib`.

**Not established.** This batch has no Deck deployment yet and no physical session. Saves are not byte-identical across Save & Quit even without this change, because variable order follows a hash map. The tests therefore compare decoded content.

## Batch 2: earned Blood Pact through controller input (client patch 0052, `--blood-pact` probe)

`scripts/smoke-profile.sh --blood-pact` plays The Blood Pact from a fresh disposable character with **no admin commands, item grants, teleports or injected damage**. World movement, aiming, target cycling, attacks, loot-pile browsing and B cancellation run as scripted gamepad states through the controller plugin's own input tick: left stick, LT aim, LB/RB, A, X, B and D-pad. Dialogue rows and inventory actions go through the native widget gateway. A choice that the probe does not expect fails the run instead of being picked blindly. The only position changes not walked are the quest's own stairs, fades and cutscene.

**Route covered, in order:**
1. Wield the starter sword from the inventory, then walk about 30 tiles from the Lumbridge spawn to Xenia by stick. Movement steers on the client's own collision map with the plugin's native destination projection.
2. Talk to Xenia, accept with the quest intro's native Yes, and climb down the catacomb entrance. The intro cutscene plays through ordinary Continue.
3. Walk onto Kayle's trigger tile, which starts Xenia's wounding. Aim at Kayle with LT and attack with A; win earned melee combat. Spare him, browse the pile with X/D-pad, back out with B, then take the sling with X and A.
4. Start a walk and press B: the player stops and the native destination clears.
5. Wield Kayle's sling, as Xenia advises against magic users, and defeat Caitlin across the gallery bars. Operate the winch to open the gates, walk in, and spare her. Loot the staff the same way.
6. Climb down the stairs and re-wield the sword. Open the tomb door, answer Reese, and win the fight. Kill him, loot the sword, untie Ilona and take the reward.
7. The quest journal shows QUEST COMPLETE.

**Checks recorded** in [evidence](evidence/blood-pact-native.json):
- **Target focus:** the shown focus matched Xenia/Talk-to, Kayle/Caitlin/Reese/Attack, the winch, stairs and door before each A.
- **Movement tiles:** these render inside the instance on both plane 1 (about 1,900 px) and plane 0 (about 2,200 px).
- **Health visibility:** during each fight, the corner HUD bounds never overlap the region above the cultist's head where the native health bar draws.
- **Loot:** each pile menu lists whole-pile entries, and the first B closes it without taking anything.
- **Earned XP:** Attack 116 and Ranged 108 include combat XP beyond the 100 XP quest rewards.
- **Save & Quit → Continue:** quest state (spared/spared/killed), the quest point, all three weapons, the worn sword and XP survive. The run also verified 4 backups, and a cancelled startup preserved the world.
- **Reproducibility:** three consecutive full passes, each about 250 s plus a 23 s Continue.

**Product fix found by the probe: dropped walks were never re-sent.** The quest script still held its one-tick `delay` when the first post-cutscene Walk arrived, so the server dropped it as designed. The server log diagnostic was temporary and has been removed. `ControllerWorld.walk` suppressed any repeat walk to the same destination while the native flag still pointed there. A held stick therefore never re-sent it. Client patch 0052 re-sends an identical walk once the player has made no progress for two server ticks. A unit regression covers this; client suite: 249 pass, 0 fail, 1 optional SDL skip.

**Observed controller behaviour, left unchanged for owner review.** World input deliberately re-arms only after the stick returns to neutral following any readiness change: dialogue, fades, tab refreshes and cutscene ends. A player holding the stick through the post-cutscene fade does not move until they let go and push again. This safeguard prevents acting on stale input, so the probe releases the stick after 1.5 s without progress, like a player would. The run recorded 3 releases.

**Not established:**
- physical pad or Steam Input layout;
- Gaming Mode/GPU presentation, Deck frame pacing and suspend/resume;
- magic combat with Caitlin's staff (Reese was beaten with melee);
- the kill branches for Kayle and Caitlin.

The health check is geometric, not a reviewed screenshot.
