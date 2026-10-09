# Adventure sprint: controller UI foundation review

This was static only. I ran no game, build or test, used no network, opened no saves, cache,
login data or config secrets, made no source edits and no commits. Scope, in the current client
working tree (`upstream/runelite-client/client/src`):
- `ControllerPanelDetails.java`
- the journal and read-only additions to `ControllerUi.java` (`describePanel`, `panel`)
- `UiState.Widget` `detail` and `status`
- `PanelPresentation` (the new groups and column layouts)
- `SoloScapePanelOverlay` (theme, details viewport, tooltip)
- `ObjTypeList` and `ControllerItemImages`, which reuse native cached pixels

## Verdict
**No correctness blockers. No fabricated actions.** All the new metadata is display-only, and
every invocation still goes through `ControllerUi.invoke`, which re-checks the item, the open
group and the native permission-gated actions.

One **medium** issue affects the native fallback: with the custom quest or skill screens turned
off, the synthetic journal pane comes first and has made-up geometry (finding 1). The rest is
low severity.

## Verified
- **No fabricated actions.**
  - Journal and detail rows are built with `new UiState.Action[0]` (`ControllerUi.java:374-378`).
  - Bonuses rows are unchanged and also have no actions.
  - Skill, quest and journal changes to `describePanel` (`:263-269`) only change
    `name`, `detail` or `status`. `options` still comes from `actions(w, true)`.
  - Because `describePanel` runs on both sides of `same()` (snapshot and invoke), the
    overridden names compare equally.
  - The overlay labels rows without actions as "Read only" (`SoloScapePanelOverlay:75, :94`),
    and the A/X/mouse guards (`actions.length > 0`) are unchanged.
- **Closed or hidden journals.**
  - A panel can only be one of the groups in `openGroups()`. 275, 499 and 741 are in
    `extraModal` (`:228`).
  - Journal text is read from the loaded interface `Class348_Sub40_Sub33.aClass46ArrayArray9427[id]`.
    Only type-4 text that passes `isVisible` is used, and `isVisible` checks every ancestor up
    to 32 levels, so a hidden parent hides the row. Component 275 is limited to 16–315, and
    rows with empty plain text are skipped.
  - When the group closes, the panel becomes `null`, so no stale journal survives.
  - Reading text that has scrolled out of view but is still loaded is intended and
    display-only.
  - `status()` reports only `<str>`, exact green, yellow or red, or nothing. It never guesses
    from other colours.
- **XP index mapping.** `COMPONENTS` (`ControllerPanelDetails.java:7`) matches every `[stats]`
  component in the pinned `game-server/data/skill/skill.ifaces.toml`, in the native skill
  order:
  - attack 200, defence 28, strength 11, constitution 193, ranged 52, prayer 76, magic 93
  - cooking 68, woodcutting 165, fletching 101, fishing 44, firemaking 172, crafting 84
  - smithing 179, mining 186, herblore 36, agility 19, thieving 60, slayer 118, farming 126
  - runecrafting 110, hunter 142, construction 134, summoning 150, dungeoneering 158

  The arrays match `Applet_Sub1.java:1284-1288` → `SkillSnapshot(xp, level, boostedLevel)`:
  - `Class186.anIntArray2497` = XP
  - `Class256.anIntArray3295` = base level
  - `Class161.anIntArray2145` = boosted level

  So "Level boosted / base · Experience" is correct. A null or short array, as at logout
  (`Class161:65`), shows "loading".
- **Independent custom toggles.** `presented()` returns the native state unless
  `customInventory` or the open group's own toggle is on. `customGroup` → `supported(...)`
  covers quests (190, 275, 178), skills (320, 134, 499, 741), combat (884), prayer (271) and
  spells (192, 193, 430). Every toggle defaults to `false`.
- **Paging and focus.**
  - `columns` is 1 for list-like groups and 3 for skills, with 7 rows. The overlay's
    presentation is built from `ui.focusedPanel().id`, and the grid from
    `nativeState.panel.id`. These are the same panel in a given frame, so `pageSize`, the page
    counter and the hit map agree.
  - The 2×14 Bonuses grid still equals the 28-cell page size for 667.
  - `detail` and `status` now survive `grid()`, which passes all fields through (`:61`).
  - The details column is clipped to the content height (`:80-81, :107`), and the action
    hit map still maps to the action index.
- **Bounded artwork memory.**
  - `images` holds at most 128 entries in an access-order LRU. `nativeImages` holds at most 256,
    keyed by the native sprite object (`ControllerItemImages.java:8-17`). Each 36×32 ARGB copy
    is about 4.6 KB, so the total is about 1.8 MB at most.
  - `attach` runs only for `i_6_ <= 1 && !bool_5_` (`ObjTypeList.java:76`). `reuse` requires
    `i <= 1` (which is `i_6_`, the outline mode, mapped through `method1941`). It also requires
    that the identical sprite object was attached with the same item and amount.
  - Outline modes of 2 and above, and `bool_5_` variants, never become a primary image.
  - Everything is `synchronized` and runs on the client thread, with no model rendering and no
    GPU readback.

## Findings
### 1. Medium (native fallback): the synthetic journal pane comes first with made-up geometry
`ControllerUi.panel` always adds the Journal or Details pane for 275, 499 and 741
(`:372-379, :406`). It does this **whatever the custom toggles say**, puts it at **index 0**,
and gives each row a made-up rectangle `Rectangle(0, component*32, 400, 28)`. With
`customQuests` or `customSkills` off:
- `presented()` returns that native state unchanged, so the native overlay opens on the
  journal pane;
- the focus outline is drawn at x 0–400 and y from 512 up to about 10,000, which is off screen
  or over unrelated UI;
- D-pad navigation runs on those made-up coordinates;
- the controller-scroll fallback finds no recorded widget, so it does nothing.

Nothing can be dispatched, because the rows have no actions. But the "independent fallback"
promise is broken for these groups: before this change, the native panel opened on its real
items.

**Smallest fix:** add the synthetic pane only when the matching custom toggle is on (pass a
flag into `panel`, or let the presentation add it). Alternatively, append it after the native
pane and use the real `seen.bounds` when the text widget was recorded this frame.

### 2. Low: the inventory grid follows the open panel's column count
`presented()` builds a single `PanelPresentation` from `nativeState.panel.id` and uses it to lay
out the **inventory** as well (`SoloScapeControllerPlugin.java:60-61`). The overlay paints the
inventory with `-1` (4 columns). If the inventory is focused while the native snapshot holds a
1- or 3-column group, inventory cells from 8 or 22 onwards are placed off the content area.
They then can't be drawn or clicked, while `moveSlot` still moves through all 28 slots. Side
tabs are exclusive, so this is rarely reachable. **Fix:** lay out the inventory with a
`PanelPresentation(..., -1)`.

### 3. Low: the native sprite map keeps native sprite objects alive
`nativeImages` holds strong references to up to 256 `Class105` sprites after the native cache
(250) has evicted them, and `clear()` keeps them, by design, for reuse after relog. This is
bounded, but on a renderer switch the old renderer's sprite objects (which may hold texture
handles) stay referenced until the LRU evicts them. **Optional:** clear `nativeImages` when the
renderer changes, or use weak identity keys with the same bound.

### 4. Low (display): the journal's selected name is also its detail
`name = detail = plain(text)` for 275, 499 and 741 (`:268`). The overlay suppresses a detail
equal to the name (`:89`), so long lines are shown only through `fit()` (cut short) and the
tooltip. **Optional:** wrap `focus.name` in the details column for read-only rows. It already
goes through `text(...)`, so this is mostly fine as it is.

## Limits
- I didn't verify the 499/741 skill-guide and 178 component layouts, or whether the 275 text
  range of 16–315 covers every quest, against the cache or in game.
- I didn't verify the native sprite-cache semantics beyond the `method1941` and `method1932`
  argument mapping (`i_6_` = outline mode, `i_4_` = item, `i_0_` = amount). The sizes you
  stated (native 250, own 256 / 128) match the code.
- The client tests and build were running and I didn't see their results. No gameplay
  acceptance is claimed.
