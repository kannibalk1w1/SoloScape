# Second controller sprint: planning audit

This is a read-only planning audit of the pinned sources under `upstream/`: the game-server
Kotlin code and data TOMLs, and the controller files in the client. I did not launch the game,
read the cache, build anything or edit source. I make no gameplay acceptance claims. The IDs
below come from the server `*.ifaces.toml` / `*.varbits.toml` files, which drive the packets
the server accepts. Before relying on them, confirm in game that the client widget hierarchy
matches.

## 1. Combat range, spell reach, line of sight

### What the server owns (none of it is visible to the client)
- **Melee vs ranged attack range.** `CombatMovement.attack()`
  (`engine/.../mode/combat/CombatMovement.kt:118-136`) uses `arrived(-1)` for melee and
  `arrived(attackRange)` otherwise. The player's range is the server variable `attack_range`,
  set in `content/skill/melee/Weapon.kt:34`: `10` when autocasting, else the item-def
  `attack_range` + the style bonus, capped at 10. The Wilderness rules
  (`Wilderness.kt:27`) can change it too.
- **Spell and interface-on-NPC reach.** Each spell script sets its own approach range, for
  example `approachRange(2)` for Energy Transfer, Cure Other and Vengeance Other, and
  `approachRange(8)` for Stat Spy and Monster Examine. The default approach range is
  `arrived(approachRange ?: 10)` (`Interact.kt:156`).
- **Line of sight.** The server uses rsmod `LineValidator` over the server collision map
  (`PathFinder.kt:35-57`, `Movement.kt:40`).

The client has none of these values: `attack_range` is not a varp or varbit, and the spell
ranges live in scripts. **Do not reproduce range or LOS on the client.**

### The current controller limitation (concrete)
`ControllerWorld` lists only targets within 5 tiles (`nearby`, `ControllerWorld.java:273-279`)
that the client can walk to (`reachable(...)`, `:320-340`). For an NPC that check needs a walk
route to a tile next to it. Both `candidates` and `interact` apply these filters. As a result,
an NPC across a fence, river or table is never offered for Attack or for a selected combat
spell, even though the native mouse menu would offer it and the server would accept it at range.

### Recommendation (keeps the server in charge)
1. Add a separate candidate class for **NPC attack options** (the option whose
   label matches the native attack string, which `defaultOption` already looks up through
   `Class274.aClass274_3506`; I did not map it to an `NPC_ACTIONS` number) and for **selected spell → NPC (30)**:
   - Use a widened radius of **10 tiles**, which is the server's own `attack_range` /
     approach cap, not a guess.
   - Skip the client walk check for this class only.
   - Keep the same plane, `npc.definition.interactive` and the token, `sameEntity` and option
     checks inside `interact`.
2. Mark these targets as "server will approach" in the overlay, for example with a dashed
   ring. Don't present them as reachable.
3. Leave object, ground and non-combat NPC options on the existing 5-tile + reachable filter.
4. Keep the 8-entry reachability cache bound. The new class skips the walk check, so a wider
   radius adds no path cost.

**Hazards**
- On a melee weapon, the server will walk the player around the obstacle, or answer "I can't
  reach that" after its unreachable timer. That matches the native mouse behaviour, so treat
  it as expected, not as a bug.
- Do not filter by a client-computed LOS. A wrong client LOS would hide valid targets or offer
  invalid ones with false confidence.
- Wider candidate sets put more NPCs on the LB/RB cycle. Score by the existing
  facing/area metric and limit the list (for example to the 6 best) so cycling stays usable.

## 2. Production interfaces

### 2a. Make-X (cooking, spinning, pottery, glass, smelting, fletching, dairy, bones, cannonballs)
All of these go through `makeAmountIndex` (`content/entity/player/dialogue/type/MakeAmount.kt`),
which opens **two** interfaces:
- **905 `dialogue_skill_creation`**, which is already in the client `DIALOGUES` set. Choices
  are components **14–23** (`choice1..10`). The server resumes on `continueDialogue(... choice*)`,
  so these are the type-16 Continue path that dialogue mode already handles. Component 6
  (`custom`) is hidden by the server.
- **916 `skill_creation_amount`**, which is **not** in `DIALOGUES` and not recorded, so the
  controller cannot change the amount today. Its components are:
  - 5 `create1` ("1")
  - 6 `create5` ("5")
  - 7 `create10` ("10")
  - 8 `all` (unlocked only when `allowAll`)
  - 19 `increment` ("+1")
  - 20 `decrement` ("-1")
  - 1 `line1` (text)

  These are ordinary interface ops (`interfaceOption`), so they use the existing type-18 path.

The amount is in **varbit 8095** `skill_creation_amount` (persisted, so it starts at the last
value used) and the maximum is in **varbit 8094**. The verb comes from varc 754
`skill_creation_type`.

**Recommendation**
- Record group 916 alongside 905 (similar to the 762/763 companion handling).
- In dialogue mode, when `dialogueId == 905`, show the choices as they are today, and add an
  amount row: LB/RB or X steps through `create1 → create5 → create10 → all`, each through
  `invoke` on the 916 widget.
- Show "Make N" in the prompt from varbit 8095, read through the client's native varbit
  lookup. Today A starts the action at an amount the player cannot see.
- **Do not expose `decrement` (20).** The server clamps it to **0**, not 1 (`MakeAmount.kt`,
  `current < 0 → 0`), so a controller could pick a zero amount. `increment` is safe but adds
  little next to the presets.
- Only show `all` when its op label resolves. `method3561` already hides it when it is locked.

**Overlap hazard:** dialogue mode takes the *first* open group found in `DIALOGUES`. Keep 916
out of `DIALOGUES` so it never becomes the dialogue id. Treat it only as an attachment of 905.
Otherwise the Continue choices disappear behind four buttons that have no Continue action.

### 2b. Modal production screens (main-screen modals; all close on Walk)
| Group | Name | Clickable components | Server mapping |
|---|---|---|---|
| **300** | smithing | Per item, a block of 8 components starting at 18: item 18 (model), name 19, bar 20, **all 21, x 22, 5 23, 1 24**. Next item at 26 (hatchet 26–32), then mace 34…, about 234 entries in total | `Anvil.kt:70`: component suffix `_1/_5/_x/_all`; `_x` → `intEntry` (type-7 entry, already supported). Many rows are hidden per metal or quest (`sendVisibility`) |
| **324** | tanner | Hide components 1–8 carry the ops directly (cowhide 1, cowhide_1 2, snake 3/4, green/blue/red/black d'hide 5–8) | `Ellis.kt:53`: op text "Tan 1/5/10/All/X" with an orange tag. The server matches the option string, and the client sends the op index, so this works |
| **438** | silver_mould | `*_button` components (holy 16, unholy 23, sickle 30, …), each with `_model` +1 and `_text` +2 | `SilverCasting.kt:55`: "Make 1/5/All/X"; "All" = 28 |
| **446 / 675** | make_mould_slayer / make_mould (446 is used when `World.members`) | 675: `make_ring_<gem>` 19,21,…,31 and `make_ring_option_<gem>` 20,…,32; necklace 38–51; amulet and bracelet blocks after the `_text` headers at 54 and 73 | `Jewellery.kt:41`: "Make 1/5/All/X" on `make*` |

**Recommendation:** generalise the bank/shop `panel()` into a small table of modal production
panels (`300, 324, 438, 446, 675`), each with one "Options" pane, reusing `PanelControls`.
Group-specific adapters:
- **Smithing 300:** make the item component (`18 + 8k`) the focus unit and list the actions of
  its sibling buttons (`+3 all, +4 x, +5 five, +6 one`). Each sibling must still be validated
  separately through `invoke` (fresh, `same`, permission-gated op). Set A to the `_1` sibling,
  never `_all`. Skip rows whose item component is hidden: `isVisible` already handles the
  server's `sendVisibility`.
- **Silver 438:** name each button from its `_text` (+2) or `_model` (+1) sibling. Without that,
  `describePanel` falls back to the first op label ("Make 1"), and every row reads the same.
- **Jewellery 446/675:** prefer the `make_*_option_*` component if it carries the ops, and take
  the name from the paired model's item.
- **Tanner 324:** works with the current `describePanel` as it is. The primary action should
  be "Tan 1".
- **Shared:** change the `primary()` preference to put `Make 1`/`Tan 1`/`Smith 1` before any
  "All" or "X". Today `primary` prefers labels starting with Buy, Sell or Take, then falls back
  to `actions[0]`.

**Hazards and limits**
- **Op permissions:** `Class368.method3561` hides ops the server hasn't unlocked unless a CS2
  op handler exists. If a production screen shows no actions in game, its ops are not unlocked
  for this revision. Don't fake them with raw packets.
- **"X" opens a type-7 entry.** Entry already has priority and is disarmed on open, so a held
  A won't type into it.
- **Close is a Walk.** The server's `interfaceClosed` sends `clear_dialogues`. The 1 s close
  timeout from the bank fix covers a dropped close (for example while the player has the
  `delay` flag).
- **Item-on-object opens the modal**, for example a bar used on an anvil or a hide given to a
  tanner NPC. The world input that opened it must not leak into it; the panel's disarm-on-open
  already prevents that.
- **Not covered:** construction, fletching-knife menus outside `makeAmount`, and Dungeoneering.
  Check `MoltenGlass`, `Furnace` and `Cannonballs` only through 905/916, as above.

## 3. Suggested sprint order and tests
1. **905/916 amount row plus varbit-8095 prompt** (smallest change with the largest reach).
   Tests: snapshot with 905 and 916 open → dialogue choices intact and the amount row listed;
   no decrement action; locked `all` hidden.
2. **Production panel table (300/324/438/446/675) with sibling-button adapters.**
   Tests: smithing row validation rejects a changed or hidden sibling; A maps to `_1`; X lists
   `_1/_5/_x/_all`.
3. **Ranged/spell NPC candidate class (10-tile radius, no walk check).**
   Tests: an NPC behind a blocked tile is offered for Attack or spell-30 but not for "Talk-to";
   interact still requires a token and `sameEntity` match; the token change still invalidates.

## Boundaries
- I did not check whether the client cache has CS2 onOp handlers on 300/324/438/446/675/916,
  so op availability must be checked in game.
- The component offsets for smithing rows after hatchet and mace follow the pattern visible in
  `smithing.ifaces.toml`. Read the TOML for each row rather than computing `18 + 8k` blindly.
  Some rows break the pattern (wire, studs, lantern, grapple).
- This audit does not cover the quick-actions work you are implementing.
