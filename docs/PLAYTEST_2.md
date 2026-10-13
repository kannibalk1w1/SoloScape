# Playtest 2 — 13 October 2026

Candidate source changes are client patch `0040-playtest-two.patch` and server patch
`0018-player-lit-fire-use.patch`. The local matched build includes these changes;
this does not promote the installed Steam Deck shortcut.

| Note | Change |
| --- | --- |
| Custom inventory skips empty slots | Custom inventory focus moves to the nearest occupied item in the requested direction. Opening or losing the focused item selects an occupied slot. An empty inventory remains safe. Native inventory keeps its existing grid navigation. |
| Invert left/right camera stick | Horizontal right-stick camera input is reversed. Vertical input and menu scrolling retain their existing direction. |
| Explain server approach | Approach wording is omitted from the HUD and action feedback (client patch 0041). The explanation below describes the underlying behavior. |
| Action prompt obscures health | The floating target text was removed. Actions appear in the corner HUD while the ground footprint remains highlighted. |
| Search loot piles | Aim at a pile and press **X** to browse all visible item stacks with LS/D-pad; **A** takes the selected stack and **B** returns. The menu follows the selected row through a seven-item window, including piles larger than the three rendered ground models. Actions are revalidated against live items. |
| World XP and drop rates | Select a character, then **World Settings**. Choose independent XP/drop multipliers from 1× to 100× and optionally unlimited run energy. LS/D-pad changes a rate, LB/RB moves between fields. Settings apply to that world on its next launch. |
| Cooking on player-lit fires | The matched server advertises `fire-use`; the client then exposes **Use Fire** for the six player-lit fire colours. The native validated object operation opens the existing cooking recipe flow. Item-on-fire cooking remains available. |
| Tiles disappear in Blood Pact | The projection bridge saves the actual scene camera, viewport and clip before native widget models overwrite them, then restores the renderer state after projecting tiles. The player tile also remains visible without an active destination marker. |
| Launcher page | The original mirrored brazier scene sits behind dark stone panels and gold controls. Character details show rates first and use readable storage sizes. |

## Server approach

SoloScape runs a local game server beside the graphical client. The launcher starts
both for the chosen character/world, connects through IPv4 localhost, and waits for
normal save hooks when closing. Each profile owns separate saves, world/exchange
state and backups. No hosted service is required for ordinary solo play.

The server owns movement, collision, combat range, XP, loot rolls and quest state.
The controller client handles input, target selection and presentation. For an
attack or targeted spell, the client can highlight a
nearby target without proving a complete local path; pressing A sends the normal
native action, and the server decides how to approach it and whether it is valid.
It does not mean the target is definitely reachable through a closed door.

World Settings live in the profile and become server settings at launch:
`world.experienceRate`, `world.itemDropRate`, and
`world.players.infiniteRunEnergy`. Defaults are 1×/1×/normal run. Changes require a
stopped world and cannot overwrite an active or unrecovered session. Backups,
restore/recovery and manual save transfer carry these settings. Older profiles
and backups without settings use the defaults.

The existing upstream drop multiplier favours rarer entries in supported weighted
loot tables; it can make common outcomes less likely. It changes chances rather
than multiplying stack quantities. Not every content-specific fixed reward uses
this multiplier. XP still follows the existing skill/quest reward code.

## Launcher artwork

The local artwork is `.runtime/launcher-art/brazier.jpg`, downloaded from
[RuneLite's original background endpoint](https://static.runelite.net/loginscreens/normal.jpg).
Its SHA-256 matches `NORMAL` in
[RuneLite's background definitions](https://github.com/runelite/runelite/blob/master/runelite-client/src/main/java/net/runelite/client/plugins/loginscreen/LoginScreenOverride.java):
`2db7f4e9f3a2fb85ee85211e7a21434697c2acde926b6916931dc58cf26d9272`.
The original half-scene is mirrored during painting. Game artwork is not stored in
tracked patches. To install it in a fresh owner workspace:

```bash
python3 scripts/setup_launcher_art.py
```

The private Deck exporter includes the local image when present. The launcher
remains usable with a dark background if the image is absent.

## Validation

- Client regressions: 230 cases, zero failures/errors, one existing optional SDL skip.
- Tooling regressions: 99 passing cases, including world isolation, invalid settings,
  active-session refusal, backup/restore and save-transfer rate preservation.
- Server cooking regressions: four passing cases, including a player-lit fire's
  direct native Use operation producing cooked food and XP.
- The real Swing launcher/backend check passes naming, validation, keyboard
  ownership, and saving XP 5×/drops 3× through the new World Settings dialog.
  Inspected preview: `.runtime/launcher-tests/1791882924034896483/launcher-scene.png`.
- Final native New/Continue check passes actual tinderbox-on-logs fire lighting,
  direct Use Fire, raw shrimps consumption and cooked shrimps increasing from one
  to two. Blood Pact's real instance on plane 1 produces a ground polygon, draws
  the player tile without a destination and retains a valid direct destination.
  Tested saves/XP/inventory/location survive Continue, four backups verify, and
  startup cancellation preserves the entire saved world. Original mutable world
  paths remain unchanged. Evidence:
  `.runtime/alpha-tests/session-1791883660474975411/`.
- Client/server source reproduction passes for all 127/50 modified or patched
  files. Matching jars/stamp, Python compilation and whitespace checks pass.

Run the specific native check with `./scripts/smoke-profile.sh --playtest-two`.
It creates disposable profiles and enables admin commands only on that fixture's
server to arrange food and enter the quest instance. It does not change normal
launcher permissions or play through the whole quest. The GUI evidence uses an
owned virtual display and native gateways; physical controller/Deck acceptance
and performance measurements for this candidate remain outstanding.
