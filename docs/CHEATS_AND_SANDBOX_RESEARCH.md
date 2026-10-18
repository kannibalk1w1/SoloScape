# Cheats, sandbox and debug conveniences: research

Research only. No runtime code, saves, settings, patches, indexes or commits were changed. Date of research: 18 October 2026 (refinement pass).

Scope: optional sandbox conveniences for solo and co-op play of a pre-EoC/2011-style RuneScape-like product, and what the current SoloScape code can support cheaply. The owner's principle governs every entry: the product should not impose a playstyle. Game capability limits and overflow validation are necessary. Arbitrary restrictive caps, mandatory backups, achievement penalties, permanent taint flags, compulsory difficulty, cloud accounts and anti-cheat services are not recommended. Backups are offered, not required. Irreversible clear or reset actions stay available behind an explicit player choice.

Line numbers were read on 18 October 2026 from a working tree that other workers are actively editing (`scripts/profiles.py` and the death-loot code are modified). Treat them as approximate and re-check symbols before implementation.

## Overview

- **Three per-profile world settings already work**: XP multiplier, drop multiplier and infinite run energy (`scripts/profiles.py:137-160`). They reach the server at start through the environment mapping (`scripts/profiles.py:245-250`).
- **The admin command set is not reachable by owned profiles.** Command rights are checked in `Commands.find` (`upstream/game-server/engine/src/main/kotlin/world/gregs/voidps/engine/client/command/Commands.kt:78`). The auto-admin grant keys on `development.admin.name` (`upstream/game-server/game/src/main/kotlin/content/entity/player/command/Rights.kt:22`), and the launcher sets it to an empty string (`scripts/profiles.py:246`). I found no launcher path that grants Admin. A hand-edited or imported save could carry a `rights` variable; I did not verify this and did not scan save data.
- **Cheapest route**: reuse existing handlers behind a per-profile flag that the server reads at execution time. Rights stay unchanged. The owner sets the flag in the launcher.
- **Some conveniences need no new command at all**: death keep-rule tuning and charge top-up are small changes to existing server code, described below.
- **Co-op is not a current launcher feature.** The owned server binds `127.0.0.1` (`scripts/profiles.py:245`), and `README-SOLOSCAPE.md:70` describes LAN hosting as a separate audited configuration.

## Labels

- **Current setting**: a user-visible option that works today.
- **Admin primitive**: an existing handler, gated to Admin rights, so owned players cannot reach it today.
- **Primitive, no command**: an existing engine or content function with no player or admin command wrapped around it.
- **New feature**: needs new code.
- **Unverified preference**: a plausible player want with no source in this pass. Not evidence of popularity.

## Candidate controls (14)

Effort: LOW is a parameter or handler reuse with a flag check. MEDIUM is handler changes plus tests and launcher wiring. HIGH is new persistent state or world-mutation logic.

Source keys: **M** = Microsoft Minecraft game-rule documentation plus original player requests; **S** = UESP, Skyrim:Console; **T** = Terraria Wiki, Journey Mode. Full links are in Sources.

| # | Control | Evidence (desire, see keys) | Current primitive (path) | Status | Effort |
|---|---|---|---|---|---|
| 1 | XP multiplier per world | Unverified preference; no XP-rate source | `world.experienceRate` (`engine/.../skill/exp/Experience.kt:49`); launcher `xp` 1–100 | Current setting | 0 |
| 2 | Drop-rate multiplier | Unverified preference. Terraria's slider is enemy spawn rate, not drops (T) | `world.itemDropRate` at `game/.../entity/death/NPCDeath.kt:111`, `DropCommands.kt:78`; launcher `drops` 1–100. Applies to the listed roll sites (`game.properties:78-81`), not every item source | Current setting | 0 |
| 3 | Infinite run energy | Unverified preference. Terraria's God Mode is a related control (T) | `world.players.infiniteRunEnergy` (`content/entity/player/effect/energy/Energy.kt:40`); launcher `infinite_run` | Current setting | 0 |
| 4 | Self-restore run energy, special attack, prayer, stats | Unverified preference. Terraria Journey lists unlimited breath and mana as a God Mode effect (T) | `rest`, `spec`, `pray`, `restore` (`content/entity/player/command/PlayerCommands.kt:76-79`, handlers `124-145`), all `adminCommand` | Admin primitive | LOW: self-only `playerCommand` behind the flag |
| 5 | God mode (no damage) | Terraria God Mode: no damage or knockback (T) | `god_mode` checked in `content/entity/combat/hit/Damage.kt:163`; toggle `SkillCommands.kt:31,84` (admin). `god_mode` also suppresses run drain (`Energy.kt:40`) | Admin primitive | LOW–MEDIUM: flag-gated self toggle |
| 6 | Spawn item with quantity, including coins | Skyrim `additem <id> <count>` (S). Terraria research-then-duplicate (T). Coins below | `/item` (`ItemCommands.kt:43-48`, `itemSpawn` `:83`, `spawn` `:98`; uses `inventory.transaction` at `:101`; surfaces errors at `:117-118`) | Admin primitive | LOW: reuse `spawn` behind the flag. Amount is already clamped to `Int.MAX_VALUE` (`:85`) |
| 7 | Top up charged items to maximum | Unverified preference | `charge` transaction clamps to `charges_max` (`engine/.../inv/transact/TransactionOperations.kt:25-46`); `Item.charges()` (`engine/.../inv/InventoryOperations.kt:111-125`). No admin charge command exists (searched `content/entity/player/command` and `content/skill`) | Primitive, no command | LOW–MEDIUM: wrap a loop over inventory and equipment, using the existing clamp |
| 8 | Keep items on death (rule tuning) | Minecraft inventory protection is documented officially; players request a visible toggle and finer choice (M) | Hard-coded in `content/entity/player/kept/ItemsKeptOnDeath.kt:23-31` (see Death section). Not read from `Settings` | Primitive, not configurable | LOW–MEDIUM as an optional per-profile toggle. Correctness prerequisites are listed below; none are blocked by the root persistence work |
| 9 | Set one skill's level and XP (self) | Skyrim `advlevel` adds a level without skill or perk gains, and the page warns levelled content gets harder (S) | `/level` → `SkillCommands.set` (`SkillCommands.kt:45,54-69`): sets XP and level, suppresses level-up dialogue | Admin primitive | MEDIUM: check quest requirement checks and level-up flags. Not `master` (`:71-81`, sets 14,000,000 XP for every skill) |
| 10 | Self-teleport by coordinates or area | Unverified preference; no teleport source | `tele`, `tele_to` (`TeleportCommands.kt:79-95`) | Admin primitive | LOW for self. A saved waypoint list is MEDIUM (new state) |
| 11 | Clear inventory or bank, explicit choice | Unverified preference (undo or reset) | `clear` (`InventoryCommands.kt:20`, `modCommand`); `removeToLimit` pattern (`QuestCommands.kt:82-86`). Bank removal has no existing command | Mod primitive (inventory). Bank: primitive, no command | LOW for inventory with an explicit confirm. Irreversible: offered as a choice, not refused |
| 12 | Reset one quest | Unverified preference (testing). Quest-state risk | `quest_reset` (`QuestCommands.kt:34-40`, `reset` `:60-80`). Its own docstring says players can "reclaim rewards (such as XP)" (`:58`) | Admin primitive | MEDIUM: decide reward handling first, or label clearly |
| 13 | Meet a quest's prerequisites | Quest-state risk. Skyrim's `caqs`/`saq` unlock quest achievements, showing side effects (S) | `quest_prep` (`QuestCommands.kt:41-44`, `prepare` `:99`): raises skill XP to requirements, sets prerequisites `completed` (`:116`), gives items | Admin primitive | MEDIUM with a reward-consistency review. Do not expose as "complete quest" |
| 14 | Time and tick speed | Terraria Journey: freeze time or speed up to 24× (T) | None found. Searched engine and game sources and `game.properties` for tick or time scaling | Speculation | HIGH: affects timers, skills and saves. Defer |

## Death rules (control 8)

Facts from source:

- `ItemsKeptOnDeath.kept` (`content/entity/player/kept/ItemsKeptOnDeath.kt:23-31`) sets the keep count. The base is `3`. Skulled players, and players in the Clan Wars FFA dangerous arena, get `0`. The `protect_item` prayer adds `1` (`praying("protect_item")`).
- Items are ordered by value, descending (`getAllOrdered`, `:17-21`). The `items_lost_on_death` enum (`:35`) forces loss. Item `kept` definition values `Never` and `Vanish` are always dropped. `Wilderness` items are dropped in full PvP (`:37-44`).
- `PlayerDeath.dropItems` (`content/entity/death/PlayerDeath.kt:110-155`) runs in this order: it returns early for admins (`:111-113`), removes kept items, releases Dragonfire shield charges (`:125`), spawns the grave, drops bones, inventory and equipment, clears them, then returns kept items through `inventory.transaction`. Charged items keep their stored value on return (`:147-152`).
- Drop placement is in `drop()` (`:165-185`), which calls `FloorItems.add` with `charges` and `owner`. Death-loot persistence work touches this area. I did not change it.

Cheap optional toggle, and what it touches:

- **Changes needed**: read a per-profile setting (for example `keep_all` or the base count) server-side inside `kept()`. The existing keep-count function is the starting point. A true keep-everything mode also needs an explicit decision for definition-forced loss (`Never`, `Vanish`, Wilderness and `items_lost_on_death`), which increasing the count alone does not override. Review `dropItems` side effects such as Dragonfire shield charges and familiar spills; test the chosen rule through a real death.
- **Owner choices, not policy**: "keep everything" (Minecraft-style), a higher base count, or a prayer-only rule. The toggle should not impose one as default.
- **Correctness prerequisites** (these are not reasons to call the feature HIGH): kept items must still be removed before the drop and returned after it, which is the existing code path. Charge values must survive return (`:147-152`). Admin early-return must stay. Alongside any toggle, add a test that kept items are never duplicated or lost across the return path.
- **Interaction with root work**: if root's death-loot persistence changes what `dropItems` drops, a keep-all toggle must not bypass its ordering. Recommend landing the toggle after that merge, as a follow-up, not as a dependency.

## Charge convenience (control 7)

- Definition keys: `charges` (current or base), `charges_max` (ceiling), and `charge` (name of a player variable that holds the count) (`TransactionOperations.kt:25-46`). Without `charge`, the count is the item's own value through `chargeToLimit`.
- The transaction clamps to `charges_max` (`coerceAtMost`, `:38-42`). That is the overflow validation already present. A top-up convenience can rely on it; no extra cap is needed.
- Spawning a charged item sets its charges and stops at 28 inventory slots (`ItemCommands.kt:98-115`). That is a real inventory limit, not a policy cap.
- Not verified: whether every charged item has `charge` or `charges_max` defined. A top-up should skip items with neither, instead of assuming one form.

## Coins (control 6)

- Coins use the string id `"coins"` directly across content: for example `inventory.add("coins", 180)` (`content/area/asgarnia/falador/Doric.kt:152`) and `add("coins", coins)` (`content/activity/evil_tree/EvilTreeLeprechaun.kt:101`). `/item coins <n>` therefore resolves through `ItemDefinitions` by the same id. This was verified by source use, not by running the server.
- Quantity is parsed with `toSILong` and clamped to `Int.MAX_VALUE` (`ItemCommands.kt:85`). Stacking follows `addToLimit` (`InventoryOperations.kt:60`).
- "Set coins to N" would be remove-then-add, which is a small extra step; "add N" is the cheapest form.

## Recommendations (first pass, 4)

1. **Keep the three existing world settings unchanged and document them.** LOW, no state risk.
2. **Add an opt-in per-profile sandbox flag, read server-side at execution.** Gate only self-scope controls: restore (4), god mode (5), item and coin spawn (6), and charge top-up (7). Pass it through `scripts/profiles.py:245-250`. Rights are unchanged. LOW–MEDIUM.
3. **Offer a per-profile death-keep option (8) after root's death-loot work lands.** Limit changes to `ItemsKeptOnDeath.kept`. Let the owner pick the rule. LOW–MEDIUM.
4. **Offer backup and restore as a visible option, never a precondition.** The existing actions are `Profile.backup` (`scripts/profiles.py:276`), `list_backups` (`:525`), `restore_profile` (`:540`), and retention (`:623`, `:651`), exposed through `scripts/launcher_backend.py:85-91`. Nothing is blocked if the player does not use them.

## Defer

- **Quest completion (13) and quest reset (12).** Needs a reward-consistency decision first. Quest reset's own docstring says rewards can be reclaimed (`QuestCommands.kt:58`).
- **Raw variable write (`var`, `VariableCommands.kt:34-36`).** Writes any variable with no validation. Not a player control. Admin-only debugging only.
- **Time and tick speed (14).** No primitive; affects everything.
- **Skill XP beyond self (9, `master`).** Not a first-pass candidate.
- **Bank clearing (11).** Available only as an explicit irreversible choice, not as a default.

## Controller-friendly optional UI

- A **Sandbox** section under each profile's world settings, below the XP, drops and run controls. Collapsed by default, labelled "optional."
- Each toggle shows one line about its effect and one line about what it does not change (for example: "Restores run, special and prayer. Does not change skill XP or quest state.").
- Navigation: D-pad moves, A toggles, B goes back, Start saves. Changes apply on next start, matching `scripts/profiles.py:160`. See `docs/CONTROLLER_DESIGN.md` and `docs/LAUNCHER_INPUT_AND_QUIT.md`.
- An in-session indicator while a flag is on (not a stored tag). A log line for each sandbox command run. No achievement penalty and no permanent taint flag.
- Irreversible actions (bank clear, quest reset) show a plain confirm with the consequence stated. They are never hidden, and never refused by default.

## Co-op policy choices left to players

Not decided here:

- Who owns the world: the host. Who may toggle sandbox controls: the host alone, or each profile for itself?
- Guest opt-in versus host grant, per guest or per session.
- Whether other players can see that a flag is on, and how.
- Server authority: every sandbox command is checked on the server at execution (`docs/ARCHITECTURE.md`, "server authority").
- Whether self-scope controls are allowed in shared areas, and whether spawned items or NPCs are visible to others.

## Evidence review

The initial cheap-agent pass found mostly secondary documentation. Coordinator verification added Microsoft's official game-rule reference and two original player requests. These support inventory protection and accessible controls as real wants, but do not establish demand among SoloScape players. The other candidate controls remain inferred preferences based on the native primitives and comparable games. There is no popularity ranking or survey.

## Sources and evidence

### Repository (read on 18 October 2026)

- `upstream/game-server` at commit `9f91135` (ignored, pinned checkout; read-only).
- Commands and rights: `engine/.../client/command/Commands.kt:21,58,78,172-182`; `engine/.../entity/character/player/PlayerRights.kt:11-19`; `game/.../command/Rights.kt:18-25`.
- Skills and god mode: `game/.../command/SkillCommands.kt:30-31,45-47,54-95`; `game/.../combat/hit/Damage.kt:163`.
- Items and inventory: `game/.../command/ItemCommands.kt:29-40,43-118`; `engine/.../inv/InventoryOperations.kt:60,111-125`; `engine/.../inv/transact/TransactionOperations.kt:25-46`.
- Inventory and variable commands: `game/.../command/InventoryCommands.kt:20,24`; `VariableCommands.kt:34-36`.
- Player restore, unlock: `game/.../command/PlayerCommands.kt:76-79,88-120,124-145`.
- Quests: `game/.../content/quest/QuestCommands.kt:34-44,58,60-80,82-86,99-116`.
- Teleport and NPC: `game/.../command/TeleportCommands.kt:79-95`; `NPCCommands.kt:21`.
- Death: `game/.../content/entity/death/PlayerDeath.kt:110-155,165-185`; `game/.../content/entity/player/kept/ItemsKeptOnDeath.kt:17-44`.
- Rates: `engine/.../skill/exp/Experience.kt:49`; `game/src/main/resources/game.properties:76-92`; `game/.../death/NPCDeath.kt:111`; `game/.../command/DropCommands.kt:78`.
- Energy and bonus XP: `game/.../effect/energy/Energy.kt:40`; `game/.../stat/BonusExperience.kt:12-42`.
- Launcher world settings and env: `scripts/profiles.py:98-133` (save validation), `:137-160` (world defaults and write block), `:245-250` (env mapping).
- Backups: `scripts/profiles.py:276,525,540,623,651`; `scripts/launcher_backend.py:85-91`.
- Client UI for world settings: `patches/client/0040-playtest-two.patch` (around lines 395-404), `patches/client/0042-jagex-ui-overhaul.patch` (around 1359-1360).
- Networking: `README-SOLOSCAPE.md:70`; `docs/ARCHITECTURE.md`.

### Web (accessed 18 October 2026)

- **[M] [Microsoft Minecraft game-rule reference](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/gamerule?view=minecraft-bedrock-stable), updated 21 April 2026. Officially documents inventory retention, damage, spawning, regeneration and PvP toggles. This establishes a shipped design precedent, not SoloScape demand.
- **[M] [Original player request on the Minecraft Education support forum](https://edusupport.minecraft.net/hc/en-us/community/posts/360072417591-Keep-Inventory-SOLVED), displayed 16 August 2020. A player asks for inventory protection and describes expecting an accessible UI option. One anecdote, not population data.
- **[M] [Original Reddit suggestion for finer inventory-retention choices](https://www.reddit.com/r/minecraftsuggestions/comments/11st9si/keepinventory_for_only_itemsxp/). A player describes enjoying the game more with retention enabled while wanting finer control. Minecraft XP loss is a different rule: SoloScape's native death does not remove earned skill XP. This is evidence for optional choice, not a proposal to introduce XP loss.
- **[S] UESP, Skyrim:Console**: https://en.uesp.net/wiki/Skyrim:Console (redirected from https://uesp.net/wiki/Skyrim:Console). `additem`, `removeitem`, `advlevel`, and targeted `setlevel` for NPCs. Says nothing about `player.setlevel` or whether `setlevel` affects XP. `caqs` and `saq` are noted as unlocking quest-related Steam achievements. Warns that console commands can malfunction and advises archiving a save first. No date shown.
- **[T] Terraria Wiki, Journey Mode**: https://terraria.wiki.gg/wiki/Journey_Mode. Research-then-duplicate, time freeze and speed up to 24×, weather control, God Mode (no damage or knockback), enemy difficulty slider 0.5×–3×, enemy spawn-rate slider, team sharing of research (not retroactive). Last-edit date shown: 17 October 2026. Based on the 1.4.4.9 source; details may lag. Restricted to Journey characters and worlds.

### Searches without primary results

- RuneScape 2007 or Old School RuneScape admin or cheat commands: none found (only client utility `::` commands on the OSRS wiki).
- Terraria Journey Mode release notes: only secondary sites (for example The Sixth Axis, 2020 coverage of Journey's End). Not used as primary evidence.

## Limitations

- **No popularity data.** Two original Minecraft requests support retention and discoverability. Broader SoloScape preferences still need player feedback.
- **Mixed source strength.** Microsoft documentation and original player posts were verified by the coordinator. Terraria and Skyrim details remain secondary wiki references from the research agent.
- **Line drift**: line numbers are as read on 18 October 2026 in a tree under active edits; re-check symbols before implementing.
- **Not verified**: whether every charged item defines `charge` or `charges_max`; whether NPC spawns persist; whether an imported save can carry admin rights; summoning and familiar resources; equipment durability beyond the `charges` parameter; the coins item's full definition beyond its use as a string id.
- **No build or run was done.** Behavior claims rest on reading source, not on executing it.
- **Not checked, per brief**: `.runtime/`, saves, data and private profile content, caches, and root's in-progress edits.
