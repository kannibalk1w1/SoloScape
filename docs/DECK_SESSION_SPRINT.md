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

## Batch 3 — Kayle/Caitlin kill choices (13 October 2026)

Claude identified these choices as uncovered. `scripts/smoke-profile.sh --blood-pact-kill-cultists` now runs the same earned route but chooses **Yes. Now die!** for Kayle and **Time for you to die!** for Caitlin. The original `--blood-pact` route still spares both. The saved-state validator checks the selected fates rather than accepting either outcome.

The kill route passed on an isolated native world without admin commands, supplied items, teleports or injected damage. It earned all three fights, opened/browsed/cancelled each loot pile, collected the weapons, rescued Ilona and claimed the reward. Save & Quit and Continue preserved all three killed states, the quest point, weapons, equipment and XP. Four backups verified; cancelling a subsequent startup preserved the entire saved world, and the original mutable paths were unchanged.

Evidence: [native results and host resource observations](evidence/blood-pact-kill-native.json), and [actual native gameplay screenshot during the Reese fight](evidence/blood-pact-kill-gameplay.png). The screenshot uses a disposable AlphaTest character and shows both health bars clear of the corner action HUD, plus the movement tiles. The canvas was 892×529 on a private Xvfb display.

The New session took 253.428 s and Continue took 22.627 s, including readiness and shutdown. Sampled peak RSS during New was 2,395.66 MiB for the client and 1,718.45 MiB for the server. These are host software-renderer observations, not Deck FPS or memory measurements; full private 0.5-second resource samples remain under `.runtime/alpha-tests/session-1791912830249121971/`. Tooling: 104 tests pass; both complete patch stacks match their source trees; shell and patch syntax checks pass. No production input behaviour changed.

Still open: Caitlin's staff magic route, mixed spare/kill combinations, physical controls, Gaming Mode performance and suspend/resume. The owner confirmed that release-and-push after transitions should remain in place. Before any further Claude task, request the lowest suitable model/tool tier and confirm the active model; Druidic Ritual remains an approved next route. This preference was queued to Claude's inbox without submitting its existing terminal draft.

## Deck deployment status

A matched private candidate was exported from main `cfad366` on 13 October 2026. It contains 10,547 manifest files, server 0022, client 0052 and the Blood Pact probe. The Deck did not answer ping or SSH, so nothing was staged or activated. The r28 installation, its stable wrapper and the real character save are untouched.

Before activation, follow the guarded r28 procedure:
1. Confirm no world, launcher session or `session.json` is active.
2. Take and verify a fresh backup, copy the profile with hash checks under build/profile locks, and switch `launch.sh` reversibly.
3. **Server 0022 adds one precondition.** Count raw backslashes in the real save without printing its contents. If there are none, the new reader decodes the save exactly as before. If there are any, review them first, because `\n`-style sequences now decode as TOML escapes.

## Next priorities

1. Druidic Ritual with real ingredient gathering and travel, and a bank/shop/crafting round trip, reusing the Blood Pact probe's stick travel and pad gateways.
2. The 30-minute 1280×800 Gaming Mode route on battery and external power, once the Deck is reachable. Include combat and loot from this batch.
3. Suspend/resume and controller reconnection across a saved session, with owner participation for physical acceptance.
4. Blood Pact variants not yet covered: magic combat with Caitlin's staff and mixed spare/kill choices. The all-kill route passed in batch 3.
5. Owner decision resolved: retain release-and-push after cutscenes and fades. World input still requires a neutral stick before re-arming (see batch 2).

## Overnight batch A — staff magic and mixed Blood Pact choices (13 October 2026)

Run by Claude Sonnet 5.5 from [the overnight queue](OVERNIGHT_PLAYTEST_QUEUE_20261013.md). All routes are earned on isolated native worlds with no admin commands, grants, teleports or injected damage; synthetic gamepad input on a private Xvfb display (892×529, software rendering), not physical Deck evidence.

| Route | Command | Result |
| --- | --- | --- |
| Reese beaten with Caitlin's staff | `scripts/smoke-profile.sh --blood-pact-magic` | passed; 4 Wind Strike casts |
| Spare Kayle, kill Caitlin | `--blood-pact-kayle spare --blood-pact-caitlin kill` | passed |
| Kill Kayle, spare Caitlin | `--blood-pact-kayle kill --blood-pact-caitlin spare` | passed |
| Reese "I'm not killing you" | `--blood-pact-reese spare` | passed; he still dies by poison, state `killed` |

**Magic.** The new character already carries 25 air and 15 mind runes (the Magic instructor refuses a second grant, so no errand is needed). The probe wields Caitlin's staff from the native inventory, opens the spellbook tab and uses Wind Strike's native `Autocast` action, then attacks Reese with A. Evidence: Magic XP 0 → 20 during the fight while Attack XP stayed 8 (so the staff did not melee), mind runes 15 → 11 in the saved file, air runes unchanged at 25 (Caitlin's staff supplies air). After Save & Quit and Continue the staff is still wielded, Magic XP exceeds the 100 XP quest reward, the quest is complete and all backups verified. [Fight screenshot](evidence/overnight/blood-pact-magic-fight.png) (disposable AlphaTest character, reviewed). No production code changed; the probe, `smoke_profile.py` validators and their unit tests did.

**Mixed fates.** The saved validators now check each cultist separately, and the Reese pre-fight choice takes the mixed-only line "I'm the one who defeated your lackeys". Each route verified native saved fates, sling/staff/sword drops with B-cancelled loot piles, reward panel and Continue.

Evidence and per-run resource peaks: `docs/evidence/overnight/`. Peak sampled RSS on the magic New run was 2,533 MiB client and 1,779 MiB server (host software renderer). Routes took 245–263 s for New and about 22.6 s for Continue.

## Overnight batch B — Druidic Ritual earned route, partial (14 October 2026)

`scripts/smoke-profile.sh --druidic-ritual` reuses the Blood Pact probe's pad, travel, targeting and dialogue helpers (`-Dsoloscape.bloodpact.route=druidic`). A fresh character, no admin commands, supplied items or teleports, walked and fought through:

| Step | Result |
| --- | --- |
| Lumbridge cow field (gate opened through the native Open action), raw beef | earned |
| Trees by the cow field, logs | earned |
| Seven raw chickens, player-lit fire, cooking through native item-use, second fire from a second log | earned (fires burn about 35 s) |
| Giant rats east of Varrock, raw rat meat | earned (about 15 minutes with rests) |
| Black bear, raw bear meat | **not achieved**: the character cannot out-fight it |
| Varrock → Barbarian Village → Falador west gate by stick | worked in a labelled fixture run (`--druidic-dev-stage 15`) |
| Taverley, Sanfew, the dungeon cauldron | not reached |

New probe machinery that later routes can reuse: a long-distance stick walker (waypoint choice on the client's own collision map with a visited-block penalty and road waypoints), gate/door opening toward the goal, melee reachability that ignores fenced animals, pile pick-up through the X menu (the pile's focus can name another item), tree chopping, fire lighting on a bare tile, relighting, and cooking. Observations: inventory space is tight (17 starter items), a selected item freezes world movement, fires cannot be lit on tiles with items, and `ControllerWorld` Attack on a fenced animal only reports "I can't reach that." Evidence: [partial run](evidence/overnight/druidic-earned-partial-native.json).

## Overnight batch C — gather/fire/cook, per-world XP, software sustained route (14 October 2026)

All on isolated native worlds, private Xvfb, synthetic input, software renderer. Not Deck evidence.

**Gather, firemaking and cooking** (`scripts/smoke-profile.sh --gather-cook`, passed). A fresh character, no fixtures: walks to the trees by the Lumbridge cow field (opening gates through the native Open action), chops two logs, kills chickens until it holds four raw, lights a fire on a bare tile (fires cannot be lit on tiles holding items; a selected item freezes world movement), cooks through native item-use, and relights from the second log when the first fire dies after about 35 s. Two passing runs: run 1 produced 2 cooked chicken and 1 burnt (Woodcutting 50, Firemaking 80, Cooking 60 XP), run 2 burnt all three (Woodcutting 50, Firemaking 40, Cooking 0, as a level-1 cook can). Saved XP and food survived Save & Quit and Continue in both; the validator requires Woodcutting and Firemaking XP and cooked or burnt food. Screenshots from run 2: [fire lit](evidence/overnight/gather-cook/fire.png) and [after cooking](evidence/overnight/gather-cook/cooked.png) (inventory shows the burnt chickens). One other attempt timed out at its first walk (stage limit) and is not counted.

**Controller gap found.** After using a raw item on the fire the native cooking menu opens (`Raw chicken / Cook 1`, dialogue 905). The probe waited for a neutral frame (the UI re-arms only from neutral) and pressed B twice; the menu did **not** close. The same close action through the native gateway (`ControllerUi.cancelWorld`, the "Walk here" the controller sends for B) did close it, and nothing was cooked. The pad path was not isolated further (feedback null, UI active, dialogue input armed); it needs a physical or deeper synthetic check. The probe records `b_cancel_gateway_fallback` so the result is never read as pad B working.

**Per-world XP scaling** (`--world-xp-check 5 --world-infinite-run`, then `--world-xp-check 1`, passed). Two disposable worlds: two logs gave exactly 250 XP at rate 5 and 50 XP at rate 1 (25 XP per log), and each saved value survived Continue. The rate-1 world, created after the rate-5 world, was unaffected, so settings are isolated per profile. Drop-rate and infinite-run behaviour were configured but not natively sampled (a few kills do not establish a rate; no server fixture was written). The synthetic launcher smoke (`scripts/smoke-launcher.py`) also passed: held-A guard, controller name entry, B preserving the form, Y advancing, private creation, inline backend rejection and exclusive Steam-mode focus/Enter. No SDL or hardware.

**Sustained route** (`--deck-route-seconds 1800 --deck-route-software`, passed). The Deck 60 route requires the client's OpenGL toolkit, which cannot start on the private Xvfb ("Deck 60 unavailable: OpenGL could not start"), so a `soloscape.deck60.route.software` option runs the same real-map route (Lumbridge courtyard, castle door, stairs, bank, shop, dialogue, combat) on the software renderer. 2,100 s, 5 loops, 102,897 frames at 1280×800: average 48.995 fps, p95 22.84 ms, p99 25.77 ms, max 776 ms, minimum rolling 5 s 26.9 fps; 30 frames in the loading state. Client RSS peaked at 5,339 MiB (software framebuffer) and ended lower than it began (no growth); server peaked 1,686 MiB, +34 MiB over the run. Continue took 44 s. GC: 354 young and 62 full collections. These are host llvmpipe/software numbers, not Deck FPS, GPU, battery or physical-controller evidence. Evidence: [`docs/evidence/overnight/sustained/`](evidence/overnight/sustained/) and the [route-end screenshot](evidence/overnight/sustained/route-end-screenshot.png).

**Bank and shop** (item 5, partial).
- `scripts/smoke-profile.sh --text --journey` passed (the plain `--journey` still stops at the pre-existing adventure step 10, "Settings disappeared on second tick"; `--text` skips it): real Lumbridge castle stairs to the bank, banker opened, a Withdraw-X amount prompt cancelled with no server suspension left and bank and inventory unchanged, bank search filter and cancel/toggle, then a normal withdraw. It ran again after Continue with the same results. [Results](evidence/overnight/bank-journey-native.json).
- `scripts/smoke-profile.sh --shop-trade` passed: a fresh character walks to the Lumbridge general store, opens the door and Trade with the shopkeeper through the native interaction, and sells its Bronze dagger with the panel's native `Sell 1` action (coins 0 → 4, dagger gone, both saved through Continue). **Gap:** the native shop panel exposed zero Stock widgets (the server's general store has 11+ entries), so no purchase could be made; the probe records `buy_blocked` and the run is not claimed as a full sell/buy loop. [Results](evidence/overnight/shop-sell-native.json).
- Not done: earned clay, softening, shaping, firing a pot, the unfired pie dish/bowl mapping, and a bank deposit of earned materials.
