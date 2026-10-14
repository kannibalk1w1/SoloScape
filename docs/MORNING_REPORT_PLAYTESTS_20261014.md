# Morning report: overnight sequential playtests, 13–14 October 2026

Worker: Claude Sonnet 5.5 (`claude-sonnet-5-5`, medium effort, as shown in the launch banner) for everything. No Haiku, no Opus, no sub-agents, no escalation. Ledger: [OVERNIGHT_PLAYTEST_QUEUE_20261013.md](OVERNIGHT_PLAYTEST_QUEUE_20261013.md). Detailed results and caveats per batch: [DECK_SESSION_SPRINT.md](DECK_SESSION_SPRINT.md). Raw evidence (route JSON, resource summaries, reviewed screenshots): `docs/evidence/overnight/`.

**Everything below is host evidence**: private Xvfb 892×529 or 1280×800, software renderer, synthetic gamepad input through the controller plugin's own input tick, disposable AlphaTest profiles. None of it is physical Deck, Steam Input, GPU, battery or suspend/resume evidence. The owner's character and profile were never touched. No world is running.

## Outcome by queue item

| # | Item | Result | Reproduce | Evidence | Git |
| --- | --- | --- | --- | --- | --- |
| 1 | Blood Pact staff magic | **Passed.** Reese beaten with Caitlin's staff and the spellbook's native Autocast on Wind Strike. Magic XP 0 → 20 in the fight, Attack XP unchanged (no melee), mind runes 15 → 11 (the staff supplies air). Staff still wielded and Magic above the 100 XP reward after Continue. | `scripts/smoke-profile.sh --blood-pact-magic` | `blood-pact-magic-*`, [fight screenshot](evidence/overnight/blood-pact-magic-fight.png) | PR #20 merged (`9dd8ff9`) |
| 2 | Mixed Blood Pact choices | **Passed once per route:** spare Kayle/kill Caitlin, kill Kayle/spare Caitlin, Reese "I'm not killing you" (he still dies by poison). Saved fates checked per cultist; mixed fates use Reese's mixed-only pre-fight line. | `--blood-pact-kayle spare --blood-pact-caitlin kill`, `--blood-pact-kayle kill --blood-pact-caitlin spare`, `--blood-pact-reese spare` | `mixed-*`, `reese-mercy-*` | PR #20 |
| 3 | Druidic Ritual earned route | **Partial / blocked.** See below. | `--druidic-ritual` (earned), `--druidic-dev-stage N` (labelled admin fixture, debugging only) | `druidic-earned-partial-native.json` | PR #21 |
| 4 | Gather, firemaking, cooking | **Passed, with a controller gap.** Logs, player-lit fire, cooked and burnt chicken, XP saved through Continue. B did not close the cooking menu. | `--gather-cook` | `gather-cook-run1-cooked-native.json`, `gather-cook-run2-burnt-native.json`, [fire](evidence/overnight/gather-cook/fire.png), [cooked](evidence/overnight/gather-cook/cooked.png) | PR #21 |
| 5 | Bank, shop, pottery | **Partial.** Bank round trip, Withdraw-X cancel and bank search passed. A shop sale passed; the purchase was blocked because the panel exposed no stock widgets. Pottery not attempted. | `--text --journey`, `--shop-trade` | `bank-journey-native.json`, `shop-sell-native.json` | PR #21 |
| 6 | Per-world settings and lifecycle | **Partial.** XP rate scaling exact and isolated across two worlds; synthetic launcher smoke passed. Drop rate, infinite run, SDL/Steam hardware not covered. | `--world-xp-check 5 --world-infinite-run`, `--world-xp-check 1`, `scripts/smoke-launcher.py` | `xp-rate-*` | PR #21 |
| 7 | Sustained host session | **OpenGL route blocked on Xvfb; software-renderer variant passed (35 min).** | `--deck-route-seconds 1800 --deck-route-software` | `sustained/`, [screenshot](evidence/overnight/sustained/route-end-screenshot.png) | PR #21 |
| 8 | Deck delivery | **Blocked: Deck unreachable.** Matched local export made and hash-verified; nothing activated. | see below | — | — |
| 9 | Report and Git | This file. | — | — | see Git |

### Item 3 in detail (Druidic Ritual)

Earned from a fresh character with no admin commands, grants or teleports: stick travel to the Lumbridge cow field (gates opened through the native Open action), raw beef, trees chopped, seven chickens, a player-lit fire, cooking and a second fire, giant rats east of Varrock (raw rat meat). Long stick travel from Varrock via Barbarian Village round Falador to its west gate worked in a labelled fixture run.

**Blocked on:**
1. **Raw bear meat.** The only reachable bear is the level-19 black bear east of Varrock. A fresh character (10 Constitution, bronze sword, two cooked chickens, bread, shrimps) over 30 minutes landed about 6 damage and survived only by retreating; it cannot win. Needs either a much stronger character (hundreds of kills) or a food stock (fishing shrimps with the starter net first).
2. **The final approach to Taverley.** Waypoints beyond Falador's west gate (2925,3392 and 2900,3404) were unreachable on the client collision map from the places the walker ended up, so Kaqemeex, Sanfew and the dungeon cauldron were never reached. A recorded route is needed.

The quest logic itself is covered by the existing graphical fixture (`--content-coverage`) and the server `DruidicRitualTest`; neither was re-run tonight. Machinery now in the probe for later routes: a long-distance stick walker (collision-map waypoints with visited-block penalty plus road waypoints), gate/door opening toward a goal, melee reachability that ignores animals behind fences, pile pick-up through the X menu, tree chopping, fire lighting on a bare tile, relighting and cooking.

### Findings worth the owner's attention

- **Pad B does not close the native cooking menu (dialogue 905)** in the synthetic harness. After a neutral frame (the UI re-arms only from neutral), two B presses left the menu open; the same close through the native gateway (the "Walk here" B sends) closed it with nothing cooked. Not isolated further; needs a physical or deeper synthetic check. Recorded as `b_cancel_gateway_fallback`, never as pad success.
- **The shop panel exposed zero Stock widgets** for the Lumbridge general store (the server has 11+ entries). Selling works. Probably a controller-panel gap; not confirmed on real hardware.
- **Item-use freezes world movement** while an item is selected; fires cannot be lit on tiles with items; fires burn about 35 s.
- **The Deck 60 route cannot start OpenGL on Xvfb** ("Deck 60 unavailable: OpenGL could not start") although llvmpipe GLX works for `glxinfo`. I did not use the owner's desktop display.
- A new character already holds 25 air and 15 mind runes; Caitlin's staff supplies air itself.
- Plain `--journey` still stops at the pre-existing adventure step 10 ("Settings disappeared on second tick"); `--text --journey` skips it.

## Performance observations (host, software renderer)

| Run | Duration | Canvas | Client peak RSS | Server peak RSS | Notes |
| --- | --- | --- | --- | --- | --- |
| Blood Pact magic, New | 263 s | 892×529 | 2,533 MiB | 1,779 MiB | mean CPU one core: client 81 %, server 13 % |
| Mixed/mercy routes | 245–251 s | 892×529 | see `*-resources.json` | | Continue ≈ 22.6 s each |
| Druidic earned (killed at timeout) | 54 min | 892×529 | 1,572 MiB | 1,756 MiB | client mean first/last third 1,216 → 1,240 MiB (+2 %), server flat |
| Sustained route (`--deck-route-software`) | 2,100 s, 5 loops | 1280×800 | 5,339 MiB | 1,686 MiB | no growth: client last-5-min mean 3,008 vs first 3,636 MiB; server +34 MiB |

Sustained-route frame intervals (102,897 frames, software `oa` renderer, not Deck FPS): average 48.995 fps, p95 22.84 ms, p99 25.77 ms, max 776 ms, minimum rolling 5 s 26.9 fps, 30 frames in the loading state; the probe's own 60 fps targets were, as expected, not met in software. GC: 354 young and 62 full collections. Continue took 44 s. Previous reference: Blood Pact New peaked about 2,396 MiB client and 1,718 MiB server; tonight's 892×529 run was comparable, and the 1280×800 canvas costs roughly double client memory.

## Deck delivery (item 8)

`ssh soloscape-deck` at 03:09 BST: `No route to host`, so no hardware work was attempted and nothing was installed, staged or activated. r28, its launcher and the real save are untouched.

A private matched candidate export exists at `.runtime/deck-exports/1791955387489072518` (not committed): source commit `52618e2` on `coverage/overnight-playtests-20261013`, 10,579 manifest entries. I re-hashed every file independently: all 10,372 hashed files match the manifest, and the other 207 entries are symlinks in the bundled JDK legal directory. The build stamp was valid at export (client 0052 and server 0022 patch stacks, jars unchanged since the morning). Hand-off steps are the guarded r28 procedure in `DECK_SESSION_SPRINT.md`: confirm idle, back up and hash-verify the real profile, count raw backslashes in the real save without printing it (server 0022 changes escape parsing), install reversibly, keep rollback.

## Git and verification

- `python3 scripts/verify_patches.py client` matched 138 files, server 60. No production source changed tonight; no new patch was exported and the build stamp is still valid.
- Tooling tests: 110 pass (added validators for the new routes). Shell/patch syntax and whitespace checks pass in CI.
- **PR #20** (items 1–2) was merged with CI green. **PR #21** (`coverage/overnight-playtests-20261013` → main: ledger, Druidic, cook, XP, shop, sustained-route probes, evidence, this report) has green CI but **is not merged**: the permission classifier refused `gh pr merge 21 --squash --admin` ("merge without review"). I did not work around it. Please merge it, or tell me to retry.
- The first batch's commit `25c2102` (the queue brief) was already on the branch before the handoff.

## Unfinished, with blockers

1. Druidic Ritual: bear meat (needs a stronger character or food) and the Taverley route.
2. Shop purchase (panel exposes no stock) and the whole pottery chain, plus the unfired pie dish/bowl mapping.
3. Pad B closing the cooking menu.
4. Drop-rate server fixtures and in-game run-energy check; real SDL/Steam gamepad, physical suspend/resume and Gaming Mode.
5. Occupied-slot inventory D-pad navigation was not exercised.
6. Deck: reachability, idle check, install, sustained Gaming Mode probes, power comparisons.
