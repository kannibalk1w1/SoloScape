# Controller entry and selection: review

Scope: the uncommitted batch after `237e5be` in the ignored
`upstream/runelite-client/client/{src,test}`. I covered `ControllerEntry` with its `Class66.method705`
hook, `ControllerSelection` with its `Class339.method2666` hook, the `ControllerUi`
spell/item/target-inventory paths, `ControllerWorld` selected targeting,
`UiControls`/`PanelControls`/`EntryControls`/`EntryState`, `WorldControls` aiming/B handling,
and the `GameClient.ControllerTarget.selection` token. Script claims rely only on the source
and the read-only dumps `/tmp/soloscape-entry-scripts.txt` and `/tmp/soloscape-extra-scripts.txt`.
I did not run, build or test anything, made no source edits, and make no gameplay acceptance claims.

## Verdict

**No blockers found.** The findings below are low severity: fail-closed strictness, one side
effect inside a read path, and one missing test.

## What I checked and found correct

**Entry**
- `edit` → `{1564, value}`. The dump shows 1564 setting the text on `49283077`, setting
  `varcstr22` and redrawing through 1557.
- `submit` → `{112, 84, 0}` (Enter) and `cancel` → `{112, 13, 0}` (Escape).
- Script 112 branches on `varc5`, and its Enter path closes through 1548 / `varc5 = 0`.
- Only types 7, 8, 9 and 11 are exposed (`ControllerEntry.active`, `EntryState.valid`). Type 7
  is digits only and capped at `Integer.MAX_VALUE`. Type 8 is capped at 12 characters, and
  types 9/11 at 80 printable ASCII characters.
- Edit and submit both require the same session (type, revision and prompt) and an unchanged
  value, so typing on the keyboard at the same time makes them fail safely.
- Entry has top priority in `UiControls.update`. While it is active, `ControllerUi.invoke`,
  the tabs and world input are blocked (`ControllerWorld.ready` checks `!ControllerEntry.active()`).
- Entry starts disarmed, so a held A or a stick deflection from Withdraw-X or Buy-X cannot type
  a character.
- Tests cover the script argument shapes, overflow, a changed value, a replaced prompt with an
  identical type, text and value, and hidden or unsupported types.

**Selection binding**
- `Class339.method2666` is the only place that sets `r.aBoolean9722` or `Class149.anInt2046`, and
  the hook runs after every native global is assigned.
- `valid()` re-checks the live widget identity, item, quantity, target mask (`method3307(14)`),
  param and select label.
- Every re-selection bumps `revision`. The token is carried on world targets
  (`ControllerTarget.sameSubject`/`same`) and on `UiState.Action.same` for item targets.
- `ControllerWorld.interact` re-enumerates targets and matches them with `sameEntity`, which
  includes the token. `ready()` requires `ControllerSelection.valid()` whenever a selection exists.

**Targets and action IDs**
- NPC 30, object 2 and ground 49 are gated by the mask bits 2/4/1 and the param filters, which
  mirror the native ones.
- The widget target (action 6) matches the native builder `Class239_Sub17.method1797` (`method3303(1)`,
  `anInt500 & 0x20`, the `method428` param check). The native builder doesn't exclude the source
  slot either, so the two behave the same.
- The ground-49 dispatch sends the live `Class9.anInt169`, `Class301.anInt3829` and
  `Class149.anInt2046`, so validation and dispatch use the same selection.

**Movement and B**
- `walk()` returns early while a selection is active, and `WorldControls` treats `targeting()`
  as aiming (`resetWalk`/`stopDirect`), so walking and direct movement stay suppressed.
- B with a selection, even an invalid one, reaches `cancelAction`. That cancels the selection
  before any `ready()` gate, and `WorldControls:61` forwards B even when the world isn't ready.

**Radial handoff**
- A panel's `selectionRequested` with mask & 32 opens the inventory through
  `openTargetInventory`, which uses the tab op without Class325's trailing deselect. The test
  checks that the token is preserved.
- `exitRequested` cancels the selection.

**Prior bank findings: confirmed fixed**
- The close latch now times out after about 1 s (`PanelControls:58-61`, `:74`).
- The scroll anchor now waits for the next render frame (`state.frame != scrollFrame`).
- Focus falls back to `closest(previous.bounds)` instead of the first widget.
- `Class328_Sub3.method2615` is now called for static scroll containers (`ControllerUi:213`).

## Findings (ranked, all non-blocking)

### 1. Low: bank search starts from inside a snapshot (a read path)
`ControllerEntry.snapshot()` runs script 1471 whenever the bank is open and `varc190 == 1`
(`ControllerEntry.java:35-36`). It runs on every `ControllerUi.snapshot`, and also on the
re-snapshots inside `edit`, `submit` and `cancel`.

The dump shows 1471 clearing the key listener and setting `varc190 = 0` before it branches to
1473 or 1474. That makes it one-shot and equivalent to the native "next key press" step, so I
see no loop. Two side effects remain:
- With a gamepad connected and the canvas focused, a mouse click on Search immediately opens
  the search prompt.
- Script execution is hidden inside a read path.

**Smallest fix (optional):** run 1471 only when the controller invoked the Search control,
for example by passing a flag from `invoke` for widget `49938449`. Otherwise, add a comment
and a test. See finding 4.

### 2. Low: the revision bump only sees prompts started through `Class66.method705`
`observe` counts scripts 108/109/110/101/1472 only when they go through `method705`. Prompts
opened by other script paths are detected only through `varc5` type changes. A same-type
prompt replacement that no snapshot observed in between would keep `sameSession` true. In
practice the risk is minimal: `EntryControls` always acts on the snapshot from the same tick,
and `edit`/`submit` also require an unchanged value. No change needed; worth a comment.

### 3. Low: selection validity is stricter than the native client
`ControllerSelection.valid()` also requires the source quantity to be unchanged
(`ControllerSelection.java:17`). When a stackable "Use" source changes count while selected,
the hint shows "Selection changed" and world targeting stops until B. This fails safely, so
no fix is needed. Mention it in the UI hints you're writing.

### 4. Low: missing test for the 1471 bank search hand-off
`ControllerEntryTest` covers 1564, 112/84 and 112/13, but nothing covers script 1471.

**Suggested test:** with the recorder `Scripts`, a fake bank group 762 and `varc190 = 1`, a
snapshot records `{1471}` once. With `varc190 = 0`, or with no bank open, it records nothing.

### 5. Plausible, low: a panel could appear empty for one tick
Panel widgets now also require `seen.frame == renderFrame` (`ControllerUi:169`, `:178`). If a
`ClientTick` ever ran after `Class88.method842` began a frame but before interfaces were drawn,
or on a frame that skipped interface drawing, the panes would be empty for that tick. The new
`closest(previous.bounds)` fallback limits the effect. I did not confirm the frame and tick
ordering. Check during gameplay acceptance that the cursor doesn't flicker.

## Boundaries
- The script semantics come from the provided dumps only. I did not scan the cache, so I did
  not verify the other branches of 112 or the 1473/1474/1478 bodies.
- I did not trace the action-6 dispatch argument mapping (`Class348_Sub42_Sub12` child/id fields
  → `Class325` i_74_/i_75_) beyond seeing that it reuses the same constructor shape as the
  already-reviewed op-18/1011 path.
- Not covered: UI hints, documentation, overlays, server-side handling of the
  item/spell-on-target packets, and all in-game behaviour.
