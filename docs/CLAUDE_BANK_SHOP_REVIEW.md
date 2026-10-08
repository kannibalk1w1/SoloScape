# Bank and shop controller batch: review

Scope: commit `40cc0a0` / `patches/client/0011-bank-shop-focus.patch`, checked against the
ignored `upstream/runelite-client` sources. I read only the native scroll path (`Class66`
op 1100, `Class348_Sub24` change type 12), the op-label permission helper
(`Class368.method3561`) and the server `Walk` handler (`game/.../content/entity/Movement.kt:51`).
I did not run anything and changed no source. I left text entry out of scope. Paths below are
relative to `upstream/runelite-client/client/src/` unless shown otherwise.

## Verdict

**No hard blockers.** No path lets a stale or unpermitted action through. Finding 1 is a
lifecycle bug that can soft-lock controller input while a bank or shop is open; fix it before
gameplay acceptance.

## What I checked and found correct

- **Actions are re-validated when invoked.** `invoke()` checks `fresh()` (100 ms and native
  identity), confirms the group is still open, and checks `describePanel(...).same(expected)`
  (id, child, itemId, quantity, name). It also requires the action to match an op the widget
  lists right now. A slot whose item or quantity changed is rejected. Tests cover this.
- **Permissions.** Panel ops come from `actions(w, true)` → `Class368.method3561(op, w, true)`,
  which returns `null` unless the server's widget settings allow the op (`method3301`) or the
  widget has a CS2 op handler. The `dialogue=true` path leaves out "Use selected item with"
  (type 6) and the Select/target op (type 13). Empty dynamic slots are skipped. The op→opcode
  mapping (18 for op < 5, 1011 above that) is the same as the inventory path.
- **Modal priority.** Dialogue comes before the panel (`panel.update` runs only when
  `!inDialogue()`, and a dialogue resets the panel). An open panel blocks world input
  (`ControllerWorld.ready`), the tab radial and `openTab`. Opening and closing a panel both
  disarm input, so a held world A cannot leak into the panel.
- **Scrolling.** The scroll position is clamped to `[0, anInt791 - anInt789]`, the same bound
  the native code uses, and marks the widget dirty with `Class251.method1916`.

## Findings (ranked)

### 1. Medium: the "Closing…" state has no timeout and can swallow all panel input
At `PanelControls.java:65`, `closing = true` is set after `gateway.closePanel()`. At line 54,
`if (closing) return true;` then returns before any input is handled, and only a `null`
snapshot clears it.

The close is a same-tile Walk (`ControllerUi.cancelWorld`). That close can be dropped:
- On the server, `instruction<Walk>` returns before `closeInterfaces()` when the player has the
  `delay` flag (`Movement.kt:52`). The bank or shop stays open.
- On the client, `cancelWorld()` returns early if `ControllerUi.ready()` is false.
  `closeControllerPanel` (`Applet_Sub1.java:1054`) also does nothing unless `hasModalPanel()`.

In each case the panel stays open with the "Closing…" prompt and ignores B, A and movement
until the mouse closes it or the plugin resets.

**Smallest fix:** store a `closingUntil = now + ~1s`. When it expires, clear `closing` and
`armed`, so a second B retries. Add a `PanelControlsTest` case where `closePanel()` has no
effect.

### 2. Low/medium: focus after a scroll can stick to stale bounds or jump to the top
After an edge scroll, focus is re-chosen with `closest(scrollAnchor)` 30 ms later
(`PanelControls.java:50`, `:91`). The focused widget's own `Seen` entry keeps its old bounds
until a frame records it again, and it stays "fresh" for up to 100 ms. Without a frame in
between (low FPS or a frame hitch), the old widget is still at distance 0 from the anchor, so
focus does not move to the newly visible row. If that old row has scrolled out of view, its
entry expires. `find()` then fails and line 52 falls back to `widgets[0]`, so the cursor jumps
to the top of the pane.

**Smallest fix:** resolve the anchor only after `Seen.frame` has moved past the frame at scroll
time, instead of using a fixed 30 ms. Separately, when `find(previous)` fails, use
`closest(previous.bounds)` instead of `widgets[0]`.

### 3. Low: the controller scroll skips a step that the native scroll performs
The native script scroll (`Class66.java:2804-2810`) also calls `Class328_Sub3.method2615` for
static widgets, which drops any stored type-12 (scroll) interface change. `ControllerUi.java:175`
does not. A stored server scroll change could later be re-applied and undo the controller's
position. I also suspect the bank's script-driven scrollbar thumb may not update, because no
`onScroll` script runs, but I did not verify this in game.

**Smallest fix:** after setting the position, add
`if (w.anInt704 == -1) Class328_Sub3.method2615(-91, w.anInt830);`. Check the thumb during
gameplay acceptance.

### 4. Low: focus follows the slot, not the item, so A can act on a different item
`find()` (`PanelControls.java:104`) matches only on `id`/`child`. When stock or bank contents
shift, for example after Withdraw-All or a shop restock, focus stays on the same slot index,
which now holds a different item. The prompt updates, and `invoke` acts only on what the
current snapshot shows, so this is not a stale action. Still, an A pressed on the tick the
contents change buys or withdraws the next item. This matters most in shops, where A is the
"Buy" op chosen by `primary()`.

**Smallest fix (optional):** when the item at the slot changes, keep focus but skip A for one
tick (set `armed = false`). Alternatively, prefer a widget with the same `itemId` in `find()`.

### 5. Low: bank tab icons may land in the "Bank" items pane
`panel()` puts any group-762 widget with `anInt812 >= 0` into `items`. Bank tab buttons that
display an item icon would sort first, by y, among the withdrawable items, with "View tab" or
"Collapse" as A. Nothing destructive happens, but D-pad navigation becomes confusing. I could
not confirm whether the 634 tab components carry `anInt812` without running the game.

**Fix if confirmed:** put the tab container's children into "Controls / tabs".

## Out of scope / boundary notes
- Withdraw-X, Buy-X and bank search open the native text prompt. That interaction belongs to
  the text-entry work in progress, so I did not review it here.
- I made no gameplay acceptance claims: server acceptance of the ops, whether the scrollbar
  thumb updates, and the actual group IDs 11/620/621 in the pinned cache all still need to be
  checked in game.
