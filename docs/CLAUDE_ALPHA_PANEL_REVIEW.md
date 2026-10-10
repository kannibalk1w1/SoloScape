# Alpha custom controller panels: correctness review

Scope: `patches/client/0017-custom-controller-panels.patch` and the current sources it touches:
- `ControllerUi` (snapshot, `scroll`, `invoke`)
- `input/controller/PanelControls`, `UiControls`, `PanelPresentation` and `PanelConfirmation`
- `plugins/soloscapecontroller/SoloScapeControllerPlugin` and `SoloScapePanelOverlay`

I also briefly re-checked the two medium findings from `CLAUDE_ALPHA_SAVE_REVIEW.md`. This was
static only: no builds, tests, game, saves, cache, credentials, network, edits or commits. I make
no gameplay acceptance claims.

## Verdict

**One blocker: the destructive-action confirmation runs the wrong action when Drop or Destroy
comes from the actions list** (finding 1). Everything else is fail-closed. The remaining
findings are UX issues or polish.

## What I checked and found correct

- **Native revalidation still governs every dispatch.**
  - Gamepad, mouse cell and mouse action paths all end in `gateway.invoke` → `invokeUi` →
    `client.invokeControllerUi`. That checks freshness (100 ms), `same()` identity (id, child,
    item, quantity, name) and the permission-gated action list.
  - The presented (re-laid-out) bounds never reach dispatch. `ControllerUi.invoke` clicks at the
    centre of the *native* `current.bounds`, and `same()` ignores bounds.
- **Mouse input.**
  - Presses inside the panel box are consumed, and so are the matching release, click and drag.
  - A hit map older than 150 ms is consumed and does nothing.
  - Cells outside the content area (off-page rows) can't be hit
    (`current.content.contains(widget.bounds)`).
  - Each action rectangle maps to the action of the focus *as rendered*.
  - All work runs through `clientThread.invokeLater`, which re-checks `customPanelActive()`,
    and `mouseFocus` requires `same()` against the current snapshot. If the item changed, the
    click does nothing.
- **Read-only equipment bonuses.**
  - The rows contain only fresh text widgets of group 667 that were rendered this frame, and
    they carry no actions.
  - A and X are guarded by `actions.length > 0` in both `PanelControls` and `customMouse`.
  - `PanelControls.prompt` no longer calls `primary()` on an empty widget, and
    `ControllerUi.invoke` rejects any action on these rows. The patch adds tests for this.
- **Bank and shop quantities.**
  - Quantities and actions are the native values (`anInt781` and the permission-gated ops).
  - `primary()` picks Buy, Sell or Take first, falling back to the first native action
    (Withdraw-1 or Deposit-1).
  - Because `same()` includes the quantity, a stack that changed before the click fails closed.
- **Native fallback.**
  - The four settings are independent and all default to off. With all four off,
    `presented()` returns the native state untouched.
  - The native UI overlay is hidden only while `customPanelActive()` is true.
  - Native widgets keep rendering underneath, so their freshness is preserved.
- **Confirmation lifecycle.** The pending confirmation is cleared by:
  - pressing B,
  - the custom panel becoming inactive,
  - a button remap,
  - `cancelSelection`,
  - turning the plugin off.

  It also expires after 3 s, and the hint disappears when the focus moves to another item.
- **Chat feedback hook.** Chat types arrive as boxed `Integer`, so `instanceof Number` matches.
  The only other chat message call is on a different code path, so nothing is posted twice.

## Findings (ranked)

### 1. BLOCKER: confirming Drop or Destroy from the actions list runs a different action
How it happens:
1. A destructive action is chosen from the X actions list (`UiControls.java` around line 217;
   `PanelControls.java:90-95`). The first press is blocked by `PanelConfirmation`, as intended.
2. Both callers then set `context = null` **whether or not the invoke succeeded**.
3. The overlay now says "A: confirm Drop <item>". But the next A press goes down the
   no-context path and invokes `actions[0]` or `primary(focus)`, for example Eat, Wield, Use or
   Withdraw-1.
4. `allow()` sees an action that isn't destructive, clears the pending Drop, and lets it
   through.

The mouse path has the same problem: `mouseInvoke` → `mouseFocus(expected, false)` also clears
the context. A gamepad A pressed after a blocked mouse Drop therefore runs `actions[0]`.

The result is that, by gamepad, Drop and Destroy can only be confirmed when they happen to be
the first action. In every other case, following the prompt sends an action the player didn't
choose. That action is native and non-destructive, but it can still use up consumables or
change worn equipment. The existing confirmation test only exercises `allow()` directly.

**Smallest fix:**
- Clear `context` only when `gateway.invoke` returns true (`UiControls` context branch and
  `PanelControls:94`). The second A then repeats the same context action.
- For the mouse path, when the invoke is blocked, reopen the context on that action (set
  `context` to the widget and `contextIndex` to the action's index).
- Add a test: X → choose Drop → A (blocked) → A again → exactly one Drop is dispatched and no
  `actions[0]`.

After this change, B with the context still open just closes the context (and clears the
confirmation). Today B with no context *leaves the inventory* even though the hint says
"B: cancel".

### 2. Medium (UX): focus jumps after a native bank scroll
When D-pad down reaches the last natively rendered row, `PanelControls:102-104` scrolls the
native widget. It then stores `scrollAnchor = focus.bounds`, which is in **presented** grid
coordinates. On the next frame, `closest(scrollAnchor)` picks whichever widget now sits at that
grid position.
- After the scroll, the item list shifts by roughly the number of items that scrolled out, and
  the page is recomputed from the old focus.
- The focus therefore lands at an unpredictable offset, and it can skip the items that just
  scrolled into view.

This is still fail-safe, because it only moves focus.

**Fix:** in presented panes, re-anchor by identity instead of by geometry.
- Keep `find(previous)`. Bank children are slot indices, so the item can still be found.
- Then move one presented row in the scroll direction, or pick the first widget whose `child`
  is greater (or, scrolling up, smaller) than the previous one.

### 3. Low (UX): "Page X / N" counts only the natively rendered window
The panel lists only items rendered this frame (`seen.frame == renderFrame`), so N covers just
the native bank viewport, not the whole bank. **Fix:** label it as the visible window, or hide N
for bank 762.

### 4. Low: a failed mouse click gives no feedback
`UiControls.mouseInvoke` returns early when `mouseFocus` fails. That happens when the item
changed between the render and the click, so `invokeUi` never sets its "Item or action changed"
message. **Fix:** set the same feedback text on that early return.

### 5. Low (polish): any game message in the next 6 s becomes action feedback
`onChatMessage` shows the first type 0/109/27–29 message within 6 s of any request. That can be
an unrelated message, such as a login reminder or a broadcast. **Fix:** shorten the window to
about one or two ticks, or label the message "Game:" rather than presenting it as the result of
the request.

### 6. Low (polish): the bonuses layout is fragile
- Rows are grouped by the exact `bounds.y`. If a label and its value differ by one pixel, they
  split into two rows. Group by row tolerance, for example `|dy| < height/2`.
- Headings are included as rows. That's harmless.
- The details grid has 14 rows, so each cell is about 20 px tall at scale 1 and 8 px at the
  0.5 minimum. Text overlaps at small scales. Consider 10 rows, or a minimum cell height.

### 7. Low (polish): hover is not consumed
`mouseMoved` passes through, so the native hover text and tooltips for widgets under the panel
box still update. This is cosmetic, but it could confuse mouse users. Consume it only inside
`hit.bounds`.

### 8. Note: the confirmation covers only "Drop" and labels starting with "Destroy"
This is reasonable for the alpha. I didn't verify the cache for other irreversible labels
(release, dismiss, empty and similar), so I'm not naming specific items. Extend the list only
after seeing the real labels in game.

## The two medium save-review findings (re-check)

| Finding | Status | Evidence |
|---|---|---|
| Oversized request desyncs the stdio protocol | **Fixed** | `launcher_backend.py:101-104` reads and discards until the newline, then sends exactly one error. |
| Unexpected exception types end the backend | **Fixed** | `except Exception` (`:110`). Unexpected types also print a traceback to stderr. |
| Grand Exchange, claims, price history and reports written non-atomically | **Fixed** | `0005`: every `Config.fileWriter` in `FileStorage` is now `atomicFileWriter`. The offer directories are no longer wiped with `deleteRecursively` first. Stale item files are removed only after every replacement has been written, and the filter only matches `*.toml`, so the atomic writer's temp files are left alone. |

New low issue in 0005 (it existed before the patch):
- **The save is atomic per file, not across the whole set.** `saveOffers` writes the counter
  *last*, and `loadOffers` restores `counter` only from that file (`FileStorage.kt:87-88`). A
  crash after the item files are written but before the counter is written would bring back an
  older counter. New offers could then reuse IDs that are already on disk.
  **Fix:** write the counter file first. It only ever increases, so an early counter is
  harmless. Alternatively, set `counter = max(counter, highest loaded id)` when loading.
- **A crash before stale files are removed** brings back offers that had already finished. The
  cross-file and cross-player consistency was never transactional, so it is recoverable with
  the backups.

## Limits
- Static review only. I did not check how RuneLite's `MouseManager` handles consumed events in
  this fork. I assumed a consumed event is not delivered to the game, as in upstream RuneLite.
- I did not check native bank row clipping, so I can't say which partly visible rows are
  recorded each frame.
- I did not re-review earlier batches or `GameEventBridgeHooks` subscribers in other plugins.

## Implementation follow-up by Codex

Finding 1 is fixed in client patch 0019: blocked context invocation retains the chosen action; a blocked mouse action reopens its exact native action. Regression tests exercise X → Drop → first A blocked → second A dispatches only Drop, plus mouse Drop → controller confirmation. Both pass. Finding 2 now anchors scroll continuation by native child identity/direction before geometry, including mouse edge scrolling. Finding 3 says “Visible page”; finding 5 prefixes feedback “Game:”; finding 7 consumes hover inside the custom surface. The exchange counter is written before item files, and loading raises it to at least the highest stored offer ID; a regression covers old and missing counters. Failed stale-pointer feedback and equipment row grouping/minimum-height polish remain tracked limitations. No full cross-file exchange transaction is claimed.
