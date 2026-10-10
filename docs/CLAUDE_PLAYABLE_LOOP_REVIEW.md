# Playable loop: typed-entry cancellation and menu lifecycle (static review)

This was a bounded, read-only review. I read:
- **Client:** `ControllerEntry`, `ServerCapabilities`, `SoloScapeConnection.entryCancel`, the
  plugin's ownership tick, `UiControls.reset`, `PanelControls.reset`/`remember`, `MenuNavigation`.
- **Server:** `CancelTextEntry`, `CancelTextEntryDecoder` (+ test), `CancelTextEntryHandler`,
  `Suspension.kt`, `ActionQueue.logout`, `pauseInt`, the capability command, and the new
  `BankTest` case.

I made no edits and ran no builds or tests, and I didn't use Git or SSH.

## Summary
- **Confirmed defects:** one (D1). Steam text ownership wipes the Home ancestry.
- **Possible concerns:** four (P1–P4).
- **Sound:** the protocol framing, the capability gating, bank preservation, the guard against a
  `finally` block replacing the suspension, and the logout hang I raised earlier.

## Verified sound
- **Wire format matches.** The client's `Class351(87,1)` writes one byte, the entry type.
  Server decoder slot 87 is `Decoder(1)` and accepts only 7–9; the test covers 0–15 and checks
  that the packet is fully consumed. The types match what the probe established: 108→7
  (IntEntry), 109→8 (NameEntry), 110→9 (StringEntry).
- **The packet is gated on the client.** It is sent only when **all** of these hold:
  - a fresh `snapshot()` is the same session as the caller's;
  - the type is 7–9;
  - real native scripts are in use;
  - `serverEntryCancel` is set in config;
  - the session has verified `entry-cancel` (nonce-bound, within 10 s, the exact reply string).

  An older server falls back to the local `close_entry` only.
- **Type mismatch is rejected on the server.** The handler cancels only when the pending
  suspension's class matches the type, and does nothing while `delay` is set. The test checks
  that a type-8 cancel leaves an amount prompt pending.
- **A `finally` replacing the suspension is handled.** The action scope is
  `Dispatchers.Unconfined`, so `continuation.cancel()` runs the coroutine's cancellation, and
  any `finally` block, synchronously from the handler. `pauseInt`'s `suspension = null` is
  skipped by the exception. The handler calls `closeDialogue()` only if
  `player.suspension === pending`, so a suspension that `finally` installed survives.
- **The bank is preserved.** `closeDialogue()` closes only `dialogue_box`/`dialogue_box_small`
  and sends `close_entry`. The test checks that `bank` and `bank_side` stay open, the item
  counts are unchanged, and a later Withdraw-1 works.
- **The logout hang is fixed.** `ActionQueue.logout()` now cancels Int, Name and String
  entries and nulls the suspension, so the loop ends.
- **Bank focus survives.** `PanelControls.reset()` calls `remember()` first, so the
  per-panel focused slot comes back after an entry.

## Confirmed defect

### D1. Medium: Steam-mode text ownership erases Home ancestry and the parent stack
While `systemEntry` owns input, the plugin calls `ui.reset()` on **every tick**
(`SoloScapeControllerPlugin.java:385-387`). `UiControls.reset()` (`:55-61`) calls
`navigation.reset()`, which clears `MenuNavigation.home` and the parent stack, and also clears
`focusedTab`. Controller-keyboard mode doesn't do this: that path calls `ui.update` with the
entry and keeps navigation.

Steam mode is the default on a Deck (AUTO), so after any Steam-owned prompt opened from a
Home-opened tab:
- B no longer returns to the Home wheel;
- a child modal's parent tab is no longer restored on B;
- controller focus on the tab is dropped, and the user has to reopen it from Home.

The bank slot is preserved by `remember()`. The menu path isn't.

**Trigger:** in Steam mode, open Home → Friends → "Add friend" (name entry, type 8). Type a
name or cancel. When ownership releases, press B. Expected: the Home wheel. Actual: nothing, or
the world.

**Smallest fix:** while the system keyboard owns input, use a pause that clears only transient
input instead of `ui.reset()`:
- clear `armed`, repeat timers, `heldDirection`, the `context` menu, `entry`, and in
  `PanelControls` `armed`/`repeatAt`/`stickScroll`;
- keep `navigation`, `focusedTab` and the panel's remembered focus.

Fresh snapshots and `same()` identity still revalidate everything on the first tick after
ownership releases.

**Regression test** (`UiControlsTest`, fake gateway): call `focusHomeTab(FRIENDS)`, then call
the new pause for N ticks while the snapshot has an entry. Remove the entry, press B, and
assert `takeHomeBack()==FRIENDS`. Add a parent-stack variant: open a child modal from the tab,
then run an entry and B.

## Possible concerns (not confirmed)
- **P1. The cancel packet carries no prompt identity.** The server matches only on the
  suspension class. If the server replaces the pending prompt with another of the same class
  while a cancel is in flight, the new prompt is cancelled instead. The client gating makes
  this narrow, because it sends either an answer or a cancel, never both. Only a server-driven
  replacement can hit it. If it matters, echo a server-issued prompt counter, for example
  through `int_entry` arguments, which would need protocol work.
- **P2. Server refusal is silent while the client already closed.** When the handler returns
  early (`delay` set, or the type doesn't match), the client has already run `close_entry`
  locally. The server's action stays pending, as in the earlier "client-only close" case, and
  the user isn't told. Consider sending the cancel only, and leaving the local
  `close_entry` to the server's own `close_entry` reply when the capability is verified. Keep
  the local `{101}` only for servers without `entry-cancel`.
- **P3. Entry type 11 still closes on the client only.** `active()` includes 11, and the
  packet is limited to 7–9, so a type-11 cancel stays client-side. Either exclude type 11 from
  controller cancel or add a fixture for it.
- **P4. `logout()` overwrites a suspension installed by `finally`.** After `cancel()`, it sets
  `character.suspension = null` unconditionally (`ActionQueue.kt`). With the Unconfined
  dispatcher, a `finally` that suspends again (for example to show a Continue dialogue) loses
  that suspension, and its coroutine never resumes. That leaks memory rather than hanging,
  because logout clears the queue anyway. To match the handler, null the suspension only
  `if (character.suspension === suspension)`.

## Suggested regressions
1. **The D1 test above**, with Home → Friends plus a parent-modal variant.
2. **Logout while waiting on an entry.** A Long-priority queued action awaiting `pauseInt` →
   `queue.logout()` → ends, the suspension is null, and no further handler runs. The current
   `BankTest` logs out only **after** cancelling, so this path is untested.
3. **A `finally` that suspends again.** An action with
   `try { pauseInt() } finally { player.suspension = Suspension.Continue(...) }` → after
   `CancelTextEntry(7)`, the Continue is still pending and `closeDialogue` was not called.
4. **The client packet path.** Tests replace `scripts`, so the `scripts==NATIVE` branch that
   writes opcode 87 is never exercised. Cover it with a fake packet sink, or let the native
   probe assert that the server suspension is null after a controller Cancel.
5. **Capability downgrade.** A server reply without `,entry-cancel` sends no packet and still
   closes locally.

## Limits
- Static only. I didn't check the `menu` lifecycle beyond the reset path and the parent and
  Home navigation, and I didn't re-audit `PanelControls` selection or context behaviour.
- Unconfined dispatch behaving synchronously assumes the handler isn't itself called from
  inside an Unconfined coroutine. In that case kotlinx defers the resume to its event loop, and
  the `===` guard still keeps the handler safe.

## Resolution follow-up (static, read-only)
I re-read `UiControls.pauseForText` and its use in the plugin's ownership block, the
`pausedPanel` hand-off in `UiControls.update`, the `ControllerEntry.Cancellation` sink, the
context revalidation in `PanelControls.update`, and `ActionQueue.logout`. I made no edits and
ran no builds or tests. Test results are as you reported them.

| Item | Status | Evidence |
|---|---|---|
| D1: Home ancestry erased by Steam text | **Resolved, with one residual (P5)** | While a player exists and the controller is connected, the plugin calls `ui.pauseForText()` instead of `reset()` (`SoloScapeControllerPlugin.java:387`). The pause records the adopted panel's id and modal flag, resets only `PanelControls` (which `remember()`s the slot), the entry and the transient input (`context`, `armed`, `heldDirection`, `repeatAt`), and drops the snapshot. It keeps `navigation` and `focusedTab`. On the first tick after release, `previousId`/`previousModal` fall back to `pausedPanel`, so a modal that is still open isn't pushed again, and a modal closed during the text is discarded from the parent stack (`UiControls.java:173-189`). If there's no player or no controller, it still does a full reset, which is correct. |
| P2: cancel ignored by the server, client already closed | **Accepted residual** | The client still runs `close_entry` locally after sending. Bounded: the outcome is the same as a native player ignoring a prompt. |
| P3: type 11 | **Resolved by classification** | Type 11 is the client-only bank search, which has no server `StringEntry`. Sending the packet only for 7–9 is correct. The native bank-route fixture you're adding is the right proof. |
| P4: logout overwriting a replacement suspension | **Resolved** | The suspension is now nulled only `if (character.suspension === suspension)` for Int, Name and String entries, matching the handler, and you report a NonCancellable cleanup Continue regression. |
| Client packet path untested | **Resolved** | The `Cancellation` sink replaces the `scripts==NATIVE` guard. The native sink checks `SoloScapeConnection.entryCancel()` and the session object for `available()`. `cancel()` sends only on a same-session snapshot, with `serverCancel` set and a type of 7–9, then always runs `{101}`. |
| P1: no prompt identity on the wire | **Accepted residual** | It needs a server-driven same-class replacement during the round trip. I don't consider it serious for a single-player local server. |
| Panel action menus (new) | **Sound** | On a fresh snapshot, an open context is kept only if `context.same(focus)` **and** the selected action is still among `focus.actions` by `Action.same`. Then the index is remapped. Otherwise the menu is closed and `armed=false`, so neutral is required (`PanelControls.java:92-96`). A removed or reordered action therefore can't be invoked through a stale index. |

### P5. Low (possible): a long text session can still drop a non-modal Home tab on resume
`pauseForText()` keeps `focusedTab`, but it doesn't refresh `tabOpeningUntil`. That was set
when the tab was opened, typically more than 1 s before the text ends.

On the first tick after release, if `panel.update` doesn't adopt the tab's panel, the
`focusedTab >= 0` branch finds the opening window expired and runs `navigation.reset();
focusedTab=-1` (`UiControls.java:207-210`), which drops the ancestry D1 meant to keep. Two ways
this can happen: the tab isn't a custom-presented group, or its native panel is briefly absent
or in a dialogue while the chatbox closes.

**Fix:** on the first update after a pause, re-arm `tabOpeningUntil = now + 1 s` (for example
when `pausedPanel >= 0` or a "paused" flag is set). Do the same in `pauseForText()` for
non-panel tabs.

**Regression test:** `focusHomeTab(X)` with a snapshot that has **no** adoptable panel for X.
Pause for more than 1 s of fake time, release, deliver one snapshot without the panel and then
one with it, press B, and assert `takeHomeBack()==X`.

### Final assessment
**No blockers.** D1, P3, P4 and the client packet coverage are resolved. P1 and P2 are
bounded residual limitations and aren't serious for this local single-player loop: the server
outcome matches a native ignored prompt, and the bank is preserved. P5 is the only remaining
code-level risk I see, and it is small and testable. Physical Deck, Steam keyboard and native
bank-route behaviour remain to be confirmed by the native harness and on the device.

## Final resolution check: P5 and the manual keyboard (static, read-only)
I re-read `UiControls.pauseForText`, the resume block at the top of `UiControls.update`
(`:157-166`), `openTextKeyboard`, and `UiControlsTest.longExternalTextAllowsNativePanelToRepaintBeforeDroppingHome`.
I made no edits and ran no builds or tests.

| Item | Status | Evidence |
|---|---|---|
| P5: long text drops a Home tab on resume | **Resolved** | `pauseForText()` sets `paused` and clears `resumeUntil`. The plugin calls it on every owned tick, so the resume window starts only when ownership ends. On the first update after that, if a panel **was** adopted (`pausedPanel >= 0`) and the snapshot has no panel, no dialogue and no entry, the update returns early for at most 1 s while the native panel repaints. After that, or as soon as anything appears, it refreshes `tabOpeningUntil` (and `openingUntil` for the inventory) to `now + 1 s` before the normal logic runs. A non-panel Home tab (`pausedPanel < 0`) therefore gets the ordinary one-second opening grace instead of the stale expired deadline. `reset()` clears `paused`/`resumeUntil`, so a disconnect or focus loss still does a full reset. |
| Input during the resume wait | **Sound** | The early return ignores input for at most 1 s. The plugin has already set `mappingArmed=false` on the owned ticks, so the controller needs a neutral state before any action. Nothing is invoked from a stale snapshot, and `pausedPanel`/`pausedModal` stay for the parent-stack hand-off after the wait. |
| Manual keyboard (RS click or Settings "Open text keyboard") | **Sound** | `openTextKeyboard()` now calls `ui.pauseForText()` and leaves `settingsOpen` as it was. When the manual session ends, the existing `settingsOpen && focusedPanel()==null` rule refocuses Home → Settings. The user goes back to where they opened chat from, and the Home ancestry is kept. |
| Regression | **Appropriate** | The test pauses on an adopted Settings panel, resumes about 20 s later with an empty snapshot (still `fromHome()`), then delivers the panel and presses B, and asserts `takeHomeBack()==SETTINGS`. **Optional extra case:** a non-panel Home tab (`pausedPanel < 0`) whose native tab appears within 1 s of the resume. That would pin the `tabOpeningUntil` refresh separately from the repaint wait. |

### Final assessment
**No blockers, and no remaining confirmed defects** in the typed-entry cancellation or the
menu lifecycle. P1 (no prompt identity on the wire) and P2 (a server refusal after the client
has already closed) are the documented residual limitations of the 634 protocol. I don't
consider them serious for this local single-player loop.

Still pending, and not claimed here: the built-client native route (Steam text → resume →
B → Home, bank Withdraw-X cancel with an empty server suspension, and logout during an entry)
and physical Deck behaviour.
