# Settings and targeting follow-up: verification

This was static only, covering the current `SoloScapeControllerPlugin`, `UiControls`,
`ControllerSettingsModel` and the related tests. I made no source edits, ran no game, build or
test, used no network, and touched no saves, cache or credentials.

## Verdict
**No remaining blockers.** All five findings from `CLAUDE_ADVENTURE_SETTINGS_TARGETING.md` are
fixed. One gap from finding 2 remains (tabs that aren't panels), plus a low note about the
code structure. Neither is a safety issue.

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Adopting the panel cleared `settingsOpen` | **Fixed** | `cancelSelection` now only clears the confirmation and the native selection (`SoloScapeControllerPlugin.java:178`). `leavePanel` (`:179`) clears `settingsOpen`, and `UiControls` calls it only from the root `exitRequested` B path (`UiControls.java:190`). The `Gateway` default delegates to `cancelSelection`, so other gateways behave as before. Adopting the 65534 model in `PanelControls` therefore no longer drops it. |
| 2 | Settings hid native tab changes | **Fixed for panel tabs** (see note A) | `canPresent` only allows no dialogue, no entry, and a panel that is `null` or non-modal 261/982 (`ControllerSettingsModel.java:35`). Any other native panel clears `settingsOpen` and `nativeSettingsChild` and resets the UI (`:80`). For 1 s after `openHomeTab`, a non-settings native panel is passed through untouched, and the grace ends as soon as 261/982 appears (`:76-79`), so a slow tab switch can't release it too early. |
| 3 | Quick casts returned to the spellbook | **Fixed** | `quick.invoke` no longer calls `selectionReturn.begin` (`:124-127`). Only `invokeUi` starts a return, and that runs only for UI-originated selections. |
| 4 | First-run prompt used up when Settings couldn't open | **Fixed** | `settingsPrompted = true` is set only inside `if (openHomeTab(...))` (`:378`). |
| 5 | Late `restoringSource` | **Fixed** | It now has a 1 s `restoringSourceUntil` (`:366`) and is dropped once that passes (`:425`), before it could be applied. |

The binding remap path still re-focuses Settings after the `ActionMap` reset (`:337`), and
`mappingArmed` still requires the controller to be neutral.

## Remaining notes
**A. Low/medium (UI capture): mouse switches to non-panel tabs aren't released.**
- `canPresent` accepts `panel == null`. That's needed while 261 hasn't rendered yet.
- But inventory, friends, clan, emotes, music, notes and similar tabs also produce
  `panel == null`. If the player clicks one of these by mouse while the controller settings
  are shown, the model keeps covering it.
- The per-tick rule `settingsOpen && focusedPanel()==null` (`:371`) also pulls controller
  focus back to Settings.
- Nothing is dispatched, and B or the inventory button still leaves.

**Fix:** once the grace has ended (`settingsOpeningUntil == 0` or expired), require the native
panel to be 261/982. Clear `settingsOpen` when `panel == null`, or when
`nativeState.inventoryVisible` is true.

**B. Low (structure): `ui.reset()` runs during `ui.update`.**
- `presented()` is reached through `UiControls.update` → `gateway.snapshot(...)` (`UiControls.java:150`).
- On release, it calls `ui.reset()` (`:80`) *during* that update. The update then carries on
  with the reset fields and the native snapshot it got back.
- I traced the result: `focusedTab = -1`, so the panel isn't adopted and control drops to the
  world with `armed = false`. That's consistent, but it's re-entrant and fragile.

**Optional:** set a `settingsReleased` flag in `presented()`, and call `ui.reset()` from the plugin
after `ui.update` returns.

## Limits
- I didn't run or see the tests, or the native probe that checks the real Gateway across two
  ticks and the config round-trip. Your description is consistent with the paths checked
  above.
- I didn't verify how 261/982 behave in game during the 1 s grace. No gameplay acceptance is
  claimed.
