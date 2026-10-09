# Shared menu navigation and right-stick scrolling: review

Scope:
- `patches/client/0020-menu-parents-and-right-stick-scrolling.patch`
- the current `UiControls`, `PanelControls`, `MenuNavigation`, `StickScroll` and
  `TabRadialControls`
- the controller handling in `SoloScapeControllerPlugin`

This was static only, inside this repo. I ran nothing, opened no saves, cache or credentials,
made no edits, used no network and made no commits. No gameplay acceptance is claimed.

## Verdict
**No correctness blockers.**
- Every new path only moves focus, scrolls the native view or opens a tab. None of them sends a
  native item or interface action.
- The parent stack stores identities only (`tab`, `panel`, `inventory`).
- Held input can't leak, because every handoff requires buttons or sticks to return to neutral
  first.

One **medium** issue: a stale parent can survive a modal that the server closed (finding 1).
The rest is polish.

## What I checked and found correct
- **B ancestry.**
  - From Home to the Settings tab (261), A opens a modal child such as 742. That pushes
    `(SETTINGS, 261, false)`.
  - B in the child closes it and sets `closingChild`. When the child disappears, the parent is
    popped, `openTab(SETTINGS)` runs, and the focus is restored from `positions`. This is a
    match on id and child only, so it never dispatches anything.
  - B in Settings (`exitRequested`) calls `homeBack`, and the plugin calls
    `radial.returnTo(SETTINGS)`. B on the wheel then exits to the world.
  - The inventory reached from Home returns to Home. The inventory reached directly does not,
    because `focusInventory` → `reset()` clears `home`. Both cases are tested.
- **Held-input leakage.** Each handoff requires a release first:
  - Popping a parent sets `armed = false`, and so does a newly adopted panel (`reset`).
  - `TabRadialControls.returnTo` sets `armed = false` and `stickArmed = false`, so the B used
    to exit must be released, and the left stick recentred, before the wheel acts.
  - `StickScroll` starts disarmed after every `PanelControls.reset`, so a right stick that is
    still held (from the camera, or while opening a panel) does nothing until it returns to
    neutral.
- **Right-stick repeat.**
  - Movement counts only when it is mostly vertical and above 0.3.
  - The first step happens immediately. After that it repeats every 350 to 80 ms, faster with
    more tilt.
  - After a pause there is no burst of missed steps, because `next` is relative to `now`.
  - Non-finite stick values reset it.
  - It is ignored while an actions list is open.
  - It uses the existing `mouseScroll` path, which moves to the next row or else calls the
    validated `ControllerUi.scroll`, so it never invokes an item. This is tested.
- **Camera handoff.**
  - Once any controller mode has been active, `cameraArmed` stays false until the right stick
    is back inside the deadzone (`plugin:350`).
  - Within one tick, `ui.update` = true always overwrites the camera input with zero before it
    is used, and the wheel, quick wheel and disconnect branches also clear `cameraArmed`. So
    when scrolling stops or a menu closes, the camera doesn't jump.
- **Parent identity.** `Parent` holds no widgets or actions. The stack holds at most 16
  entries. `ui.reset()` clears it, and `ui.reset()` runs on wheel use, remaps, disconnects and
  idle gaps.

## Findings (ranked)

### 1. Medium (stale parent ownership): a parent survives a modal the server closed
- A parent is pushed whenever a modal opens from a panel or from the inventory
  (`UiControls:169-172`).
- It is popped only after a **B-initiated** close (`closingChild`, `:157-159, :177`).
- If the server closes the modal instead (walk, teleport, combat, or an action that finishes),
  the entry stays on the stack.

Example:
1. Inventory → bank, which pushes `(-1, -1, inventory)`.
2. The bank is closed by the server.
3. Later, the player opens a shop from the world. No parent is pushed.
4. B closes the shop. Because `hasParent()` is still true, `closingChild` is set, and the old
   inventory parent is popped. The **inventory opens unexpectedly** instead of going back to
   the world.

This is safe (`armed = false`, no action is sent), but the navigation is wrong.

**Smallest fix:** store the child panel id in `Parent`, and pop only when the top entry's
child equals the panel that was closed. Alternatively, when a modal disappears while
`closingChild < 0`, discard the entries whose child was that modal.

### 2. Low: `closingChild` stays set after a failed close
If B's close is ignored (for example while the player is delayed), `closing` times out after
1 s but `closingChild` keeps its value. If the modal is then replaced directly by another
modal, `:157` pops the parent and resets the panel. On the next frame `previousPanel` is
`null`, so the new modal gets no parent, and B then goes to the world.

**Fix:** clear `closingChild` when `panel.closing()` becomes false while the same panel is
still open, or apply the child-id check from finding 1.

### 3. Low: a right-stick scroll step swallows A and X pressed on the same frame
`PanelControls:109-110` returns right after a stick step, before A and X are handled. (B,
LB and RB are handled earlier.) The button press is lost rather than misdirected, so this is
safe. `mouseScroll` also sets `armed = false`. That is harmless here, because the armed check
ignores the right stick. **Fix:** don't return. Fall through to A and X, or ignore the stick on
a frame that has a button press.

### 4. Low (UX): the inventory button also returns to Home
`leave()` now always calls `homeBack()`. So pressing the inventory button (`:220`) to *close*
an inventory that was opened from Home reopens the wheel, not just B (`:232`). Decide which you
want. Leaving to the world on that toggle seems the more natural choice.

### 5. Low: the stick's neutral threshold ignores the configured deadzone
`StickScroll` uses a fixed 0.25 for neutral, while camera arming uses `config.deadzone()`.
- On a stick that drifts above 0.25, menu scrolling never arms.
- With a deadzone set below the drift level, the camera never re-arms.

**Fix:** pass the configured deadzone to `StickScroll`, with 0.25 as the lowest value.

### 6. Low (polish): saved panel positions are never cleared
`PanelControls.positions` survives `reset()` and is never cleared, because nothing calls
`clearHistory()`. A bank, shop or Settings screen reopened after a logout or a profile switch
restores the earlier focus by child index. It is only focus, and the prompt shows the item, so
nothing unsafe happens. **Fix:** call `clearHistory()` on logout and on plugin `shutDown`.

### 7. Note: a modal parent goes back to its tab, not to the modal
A pop restores only the tab or the inventory. `openTab` is skipped while a modal is showing,
and server-owned modals can't be reopened. A modal→modal→B sequence therefore lands on the
original tab, or on the world. This is expected, but worth documenting.

## Limits
- I didn't inspect `client.openControllerTab`, so I don't know whether it refuses during a
  dialogue.
- I didn't verify in the game which settings children are modal (`extraModal`).
- I didn't review overlay text placement for "RS: scroll".
