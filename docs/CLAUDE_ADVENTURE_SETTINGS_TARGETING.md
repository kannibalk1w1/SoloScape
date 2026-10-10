# Controller settings, setup and source-return targeting: review

This was static only. I made no source edits, ran no game, build or test, used no network, and
opened no saves, cache, login data or config secrets. Scope:
- `patches/client/0025-controller-settings-setup.patch`
- current `SoloScapeControllerPlugin`, `UiControls`, `PanelControls`, `SelectionReturn`,
  `ControllerSelection`, `ControllerUi`, `GameClient` / `Applet_Sub1`
- `ControllerSettingsModelTest` and `UiControlsTest`

## Verdict
**One functional blocker: the controller settings screen cancels itself on the tick it is shown**
(finding 1). It is not a safety problem. Reserved IDs never reach native dispatch, and source
return never replays a cached action. There are also two medium and two low findings.

## Verified
- **Reserved settings IDs stay local.**
  - Every settings row is `65534<<16|n` with action type `-100`.
  - `invokeUi` catches group 65534 *before* the confirmation check and
    `client.invokeControllerUi` (`SoloScapeControllerPlugin` `invokeUi`). The gamepad A/X path,
    the actions list and `mouseInvoke` → `gateway.invoke` all go through `invokeUi`.
  - The quick wheel can't capture them, because `QuickBinding.of` has no 65534 group, and the
    wheel is disabled while `settingsOpen`.
  - `scroll` falls back to `ControllerUi.scroll`, which finds no recorded widget and returns
    false.
  - Even if a settings widget did leak through, `ControllerUi.invoke` would reject it: no
    `visible` entry, and type −100 isn't a native op.
- **Stale settings input is rejected.** `ControllerSettingsModel.invoke` rebuilds the snapshot
  and requires `same()` plus an exact `status` match and a permitted action. A repeated or
  stale press after a value has changed returns −1. The test covers this.
- **Button bindings stay distinct.**
  - A change in pane 1 gives the old value to whichever option already owned the new button,
    then sets `preset=CUSTOM`.
  - The fallbacks match the config defaults (A, B, X, LB, RB, Y, View, Start).
  - Non-CUSTOM presets are written into the config by `applyPreset`, so `value()` reads the
    bindings actually in effect.
  - A new `ActionMap` resets `mappingArmed`, which requires the controller to be neutral
    again. The test covers distinct owners.
- **Native settings ancestry.** "Game settings" sets `nativeSettingsChild` and opens tab 261.
  - A child modal such as 742 is pushed with parent tab SETTINGS. B pops back to it, and
    `openHomeTab` keeps `settingsOpen` false while `nativeSettingsChild` is set, so you land on
    native 261.
  - B from 261 then returns to the controller preferences instead of Home.
- **First-run timing.** The prompt runs only after the checks for connected controller,
  canvas focus, local player and neutral mapping. It also needs `interfaceControls`, no active
  targeting, no dialogue, no entry and no modal.
- **Source return.**
  - `SelectionReturn` stores only identities (id, child, item, quantity, name) together with
    the native revision token. It never stores actions.
  - A **new** non-zero token, meaning an outside or new selection, clears it without
    returning.
  - Only a transition to 0, meaning the selection ended or became invalid, returns the
    origin, and only once.
  - The restore runs only when there is no dialogue, entry or modal and neither wheel is
    active. Otherwise the origin is consumed and dropped, never put off until later.
  - Losing focus or the local player, `openHomeTab`, and turning `returnToSource` off all clear
    it.
  - `restoreSourceFocus` only moves focus (`slot`, or `panel.mouseFocus(..., false)`), and
    matches on identity against a fresh snapshot.

## Findings
### 1. BLOCKER (functional): adopting the settings panel clears `settingsOpen`
`PanelControls.update` calls `gateway.cancelSelection()` whenever it takes on a **new** panel id
(`PanelControls.java:56`). The plugin's `cancelSelection` now also does `settingsOpen = false`
(`SoloScapeControllerPlugin.java:174`). Here's what happens:
1. `openHomeTab(SETTINGS)` sets `settingsOpen = true`.
2. On the next `ui.update`, `presented()` swaps in the 65534 model, and `PanelControls` adopts
   it. That calls `cancelSelection()`, which sets `settingsOpen = false`.
3. On the following tick, `presented()` returns native 261. `PanelControls` adopts it as a new
   id and the native settings appear.

So Home > Settings, the first-run prompt and the "return to controller preferences" path all
show the controller screen for a single tick. The first-run prompt also sets
`settingsPrompted`, so it never comes back that session. Nothing unsafe is dispatched.

`UiControlsTest.localControllerSettingsRemainInMenuAndBackReturnsToHome` doesn't catch this,
because its `Fake.cancelSelection` doesn't have the plugin's side effect.

**Fix:** remove `settingsOpen = false` from `cancelSelection`. Clear it only on explicit exits:
- the `exitRequested` path or `takeHomeBack`,
- result 2,
- `openInventory`,
- `openHomeTab` for another tab, which already happens,
- the modal, dialogue or entry guard in `presented()`.

Add a plugin-level test, or a `Fake` whose `cancelSelection` mirrors the plugin, that keeps
the model across two `update` ticks.

### 2. Medium (UI capture), once 1 is fixed: the settings screen hides native tab changes
While `settingsOpen` is set, `presented()` replaces **any** panel that isn't modal or a
dialogue. That includes when the native side tab has changed by mouse, or by a server-driven tab
switch, to something other than 261/982. The per-tick rule `settingsOpen && focusedPanel()==null`
→ `focusHomeTab(SETTINGS)` then pulls the controller back into Settings. So clicking the Quest
tab still shows controller preferences.

**Fix:** in `presented()`, keep `settingsOpen` only while `nativeState.panel == null` or its id
is 261 or 982. Otherwise clear it.

### 3. Medium (UI capture): quick-wheel casts return the player to the spellbook
`quick.invoke` calls `selectionReturn.begin(..., SPELLBOOK, false, token)` for every type-13
selection. A quick-wheel combat spell that is aimed at an NPC in the world therefore ends with
`openControllerTab(SPELLBOOK)` and `ui.focusTab(...)`. That takes the player out of world mode
after each cast, which defeats the point of the quick wheel. The inventory-panel alchemy loop
(spellbook → target inventory → back to spellbook) is a different case, and returning there
makes sense.

**Fix:** don't `begin` from the quick gateway. Alternatively, only return when the origin UI
was actually focused when the selection began (`ui.focusedPanel() != null ||
ui.inventoryFocused()`).

### 4. Low: the first-run prompt is used up even if Settings can't open
`settingsPrompted = true` is set before `openHomeTab` is tried. If the tab can't open at that
moment (tabs hidden during a cutscene or tutorial step, or `availableTabs == 0`), the prompt is
skipped for the whole session. **Fix:** set `settingsPrompted` only when `openHomeTab` succeeds.

### 5. Low: `restoringSource` can be applied much later
`restoringSource` is only consumed once a panel or the inventory is focused
(`SoloScapeControllerPlugin:421`). If the tab focus times out (`tabOpeningUntil`), it stays set
until the next time that UI is focused, which may be minutes later, and then moves focus to the
old item or spell. It only moves focus and matches identities, so it's safe. **Fix:** clear it
when `ui.focusedTab()` falls back to −1, or after the same 1 s opening window.

## Limits
- I didn't check in game, or by tests, how `client.openControllerTab(SETTINGS)` behaves for
  261 versus 982, or whether the 742 and 743 children close back to 261.
- I didn't check that the config framework accepts the model's range values
  (`overlayScale` 75–175, `deadzone` up to 90) and enum names (`preset`, `glyphs`).
- I didn't see the test and build results. No gameplay acceptance is claimed.
