# Deck readability pass (controller panels and wheels)

This pass covers the custom panel and the two radial wheels only, in their existing classic and
modern styles. Nothing has been compiled, tested or rendered by me. The tests below are written
for the integration owner's build. **Physical Deck acceptance is still pending.**

## Files changed
In `upstream/runelite-client/client/src/net/runelite/client/`:
- `input/controller/PanelPresentation.java`: new `pages(widgets)`.
- `plugins/soloscapecontroller/SoloScapePanelOverlay.java`: cell layout, details/action
  layout, page and hint lines.
- `plugins/soloscapecontroller/ControllerTheme.java`: an accent bar on the selected action row.
- `plugins/soloscapecontroller/SoloScapeTabRadialOverlay.java`: label fitting and hub spacing.
- `plugins/soloscapecontroller/SoloScapeQuickRadialOverlay.java`: hub spacing and a correct
  ellipsis.

Tests in `upstream/runelite-client/client/test/net/runelite/client/`:
- `input/controller/PanelPresentationTest.java`:
  - `pageCountFollowsTheLaidOutGridNotTheGroupPageSize`
  - `twoColumnBonusPagesStayExactOnSmallScales`
- `plugins/soloscapecontroller/PanelOverlayTest.java`:
  - `longDetailsNeverPushTheSelectedActionOutOfTheColumn`
  - `shortCellsAndSmallCanvasesKeepHitMapsInsideThePanel`

I didn't touch the plugin, `UiControls`, `PanelControls`, entry, server or harness code.

## Problems fixed (found by reading the code)
1. **The page counter was wrong for grids that don't use the group's page size.** The overlay
   counted pages as `widgets.length / view.pageSize`. The inventory is always one 4×7 page,
   but a one-column group view (quests, journal, settings) has `pageSize` 7. So all 28 inventory
   items were visible while the counter said "page 1 / 4 ↓".

   `PanelPresentation.pages()` now derives {current, total} from the laid-out bounds. Grids use
   7 rows, or 14 for the two-column detail grid. `cellHeight = floor(content.height/rows)`, so
   the row count can be recovered exactly. That is pinned by a small-scale case where a naive
   `content.height/cellHeight` gives 15.
2. **Two-line cells overlapped in short cells.** The two-column Bonuses grid has 14 rows, about
   20 px per cell at scale 1, and small resized canvases with `scale < 1` keep a 12 px font
   minimum. In both, the second line's baseline sat **above** the name's, so the text was
   garbled.

   Cells now use two lines only when `2·inset + 2·ascent` fits. Otherwise they use one line: the
   name on the left and the quantity or status right-aligned, each fitted with an ellipsis.
3. **Long details could hide the selected action and its hit box.** A long name, status or
   detail (spell requirements, quest text) pushed `y` past the column. Then `shown` became 1 and
   the loop's bottom check drew **no** action rows, so `paint()` returned `null` for the
   selected action and the mouse couldn't use it.

   The details text is now cut with an ellipsis, so that the "Actions" header and up to three
   action rows (or all of them, if fewer) always fit. The action list and its scrolling are
   unchanged.
4. **The bottom hint could be clipped mid-line.** It used a fixed `bottom − 48·scale` baseline
   with a clip. At `scale < 1` (with the 12 px font minimum), the second line was cut through.
   The hint now sits against the frame bottom, keeps only whole lines that fit between the
   content and the frame, and ends the last kept line with "…".
5. **Tab-wheel labels could run into the next wedge.** With 16 tabs (22.5° each), the chord at
   the label radius is about 64 px at radius 210. Labels now start at 12·scale (up from
   11·scale), shrink to a 10 px minimum, and are ellipsized to 92% of their wedge chord.
6. **Hub text collided at large overlay sizes.** The hub offsets (−9/+15/+38 on the tab wheel,
   −16/+8/+30 on the quick wheel) didn't scale with the fonts. At the 175% overlay size the
   title and the "A" line touched. The offsets now scale with `max(1, scale)`, and hub text is
   fitted to the hub's width. The wheel heading and footer are fitted to the canvas width.
7. **The quick wheel's ellipsis could still be too wide.** It cut to fit, then replaced two
   characters with "…", so the result could still exceed the limit. It now uses the same
   measured ellipsis loop as the panel.
8. **Clearer selected action.** The selected row now has a solid three-pixel FOCUS bar inside
   its left edge in both palettes. That is in addition to the existing fill, text colour and
   classic gold outline, so it doesn't rely on hue alone. Action text moved from `x+4` to `x+6`
   to clear the bar. With more than one action, the header reads "Actions · n / m".

## Contracts preserved
- **Hit boxes.** `paint()` still returns one action rectangle per native action, the same
  `Rectangle(x, y, width, line+3)` rows spaced `line+5`, at the same width and column. Positions
  move only in the overflow case of fix 3, which previously returned `null`. The existing
  `longActionListKeepsSelectedNativeActionVisibleAndHitMapped` scenario takes the same path.
- **Identity.** Widget identity, actions, selection tokens, `present()`, `visible()`, the grid
  geometry and the body font are all unchanged. `pages()` is presentation-only.
- **Palettes.** Classic and modern both still work through `ControllerTheme.classic(boolean)`.
  The only shared change is the accent bar.

## Not changed, and recommendations for integration
- **Default Deck size.** At 1280×800 and the default `overlayScale` of 100, the panel is
  720×460 with 14 px body text. On a 7-inch screen that is small. I didn't change the scale
  rules because they are the user's setting (owned by config). **Recommendation:** default
  `overlayScale` to about 130–140 when the client is detected as running on a Deck, or offer it
  in the first-run setup. The layout above stays clipped and hit-mapped up to 175%.
- **Pane names.** The panel `paint()` receives only the title, so it can't show a strip of pane
  tabs. "Panel / Pane" in the title plus the "LB/RB: pane" hint stay as the cues. Showing every
  pane name would need the pane list passed in through the plugin, which I don't own.
- **Keyboard and context menu overlay.** `SoloScapeUiOverlay` (the on-screen keyboard and
  context menu) is outside this pass.

## Physical acceptance still open
- Legibility at arm's length on the Deck LCD and OLED, in daylight and at low brightness, for
  both palettes.
- Whether 12–14 px text is comfortable, which feeds the default-scale decision.
- Touch hit accuracy on action rows at each scale.
- Wheel label fitting and the hub at 75–175% on the real 1280×800 canvas, and in resized
  windows.
- Gaming Mode and suspend/resume rendering.

No gameplay, controller hardware, GPU or Steam Deck acceptance is claimed.
