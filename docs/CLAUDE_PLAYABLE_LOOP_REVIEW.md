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

## Harness audit: `NativePlayableLoopProbe` and `--journey` (static, read-only)
I read `NativePlayableLoopProbe.java`, its hooks in `NativeAdventureProbe` (status line and
step 16), the `NativeSessionSmoke` deadline, and the `--journey` wiring in `smoke_profile.py`.
I didn't run the probe, and this doesn't claim a pass.

**Verdict: no blockers.** One medium finding is about how truthfully the evidence is labelled.
The rest are low.

### Sound
- **Isolation.** `--journey` only adds `-Dsoloscape.playable.probe=true` to the client inside
  the existing disposable `.runtime/alpha-tests/session-*` profile, on port 43595, with the
  existing fingerprint check of the original world. `enableServerCancel(true)` is static to
  that client process. Each New and Continue iteration is a new client JVM, so the static
  `step`/`since`/`sent` state can't carry over.
- **Identity and freshness.**
  - Every item or panel action re-reads `ControllerUi.snapshot()` the same tick and goes
    through `ControllerUi.invoke(widget, action)`, so the adapter's freshness and `same()`
    checks apply.
  - World actions go through the adapter's own `candidates(true)` and
    `ControllerWorld.interact`, with an exact name, option and world tile (the banker isn't
    tile-checked).
  - Movement is the ordinary `ControllerWorld.walk` adapter, so no packet is invented.
- **Search and cancel paths.** Withdraw-X has to produce a type-7 prompt with a verified
  `entryCancel` capability, then edit, then cancel on a fresh snapshot. Search has to be type
  11, keep the filtered pot for 1 s, then cancel through the local `{101}`.
- **Repeatable New and Continue.** New takes the pot into the first free slot. Deposit-1 then
  Withdraw-1 returns it to that same slot and leaves the bank without it. The journey ends on
  the original tile. Continue reuses the existing pot (`existing_pot_reused`). So the save
  fields `smoke_profile` compares (account, experience, inventories, tile) should be equal
  across the two runs.
- **Deadlines.** Each stage fails after 60 s with the stage and tile in the message.
  `NativeSessionSmoke` gives journey runs 420 s instead of 150 s, and any exception exits 2
  with its stack trace.
- **BFS.** It searches the player's plane with the same collision flags as the adapter
  (`WorldInput.canStep`), within a 32-tile radius, using corrected parent links. If there's no
  path, it doesn't walk, and the stage times out with a clear message instead of steering into
  scenery.

### J1. Medium: the cancellation evidence claims more than it observes
`real_withdraw_x_cancel_sent` and `cancel_preserved_bank_and_items` are recorded once the
client has **issued** the cancel and the bank and items look unchanged after 1.5 s. But a
client-only `close_entry` gives exactly the same picture. That happens if the plugin tick
flips `enableServerCancel` back (config `serverEntryCancel=false`), or if the server ignores
the packet (`delay` set, or a type mismatch). Neither result shows that the server's
`IntEntry` suspension was cleared.

**Fix:**
- Rename the keys to `client_withdraw_x_cancel_issued`, or similar.
- Record `ControllerEntry` `serverCancel`, `cancellation.available()` and the type at send
  time.
- For real server proof, add a reply that exists only on the disposable server (like
  `soloscape_capabilities`), for example `::soloscape_pending_entry <nonce>` answering
  none/int/name/string. Assert `none` after cancel and `int` before it.

### Low notes
- **J2. The search-toggle result isn't checked.** Step 17 records
  `actual_bank_search_edit_cancel_toggle` 2 s after re-invoking Search, without checking that
  search mode actually ended. **Fix:** require the same varp that `ControllerEntry.prepare()`
  reads (`Isaac.anIntArray1303[190]==0`), or require that the unfiltered bank layout is back,
  before recording it.
- **J3. The door stages pass blind.** Steps 5 and 24 move on after 1.5 s whether or not the
  door opened (for example if `interact` found no Open option because the door was already
  open). That's safe, because the BFS then fails with a 60 s stage timeout if the door is still
  shut. But the failure is reported at the next walk stage. **Fix:** record `door_open_sent`,
  or check the door's collision flag before moving on.
- **J4. The stick magnitude is used as a step count.** `nextStep` turns 1/2/3 straight tiles
  into a stick magnitude of 0.4/0.7/1.0. That relies on the adapter mapping magnitude to
  distance. At full tilt, the adapter's run threshold can also turn on running, which changes
  run energy and the run setting in the disposable save. The fields compared aren't affected,
  but it is a side effect. **Fix:** cap the magnitude below `runThreshold`, or record that run
  mode was used.
- **J5. A total-time failure gets the wrong message.** If the 420 s budget runs out in a slow
  but progressing journey, `NativeSessionSmoke` prints "Private login did not reach in-game
  state". **Fix:** print `NativePlayableLoopProbe.progress()` in that branch.
- **J6. The plugin also writes `enableServerCancel` every tick.** The probe sets it once.
  Because the plugin tick writes `setControllerEntryCancelEnabled(config.serverEntryCancel())`
  each tick, the probe's setting holds only because the config default is `true`. Assert the
  config value at the start, or record it next to the J1 fields.

### Limits
- Static only. Native collision, door and staircase behaviour, and whether the adapter's
  magnitude-to-distance mapping holds in Lumbridge, need the running host or Deck route you're
  doing now.

## Harness evidence follow-up: `soloscape_probe_entry` gating and the new assertions (static)
I read the new `PlayerCommands.soloscape_probe_entry` command, `ExecuteCommandHandler`, the
`env` injection in `smoke_profile.py`, and the journey stages 13–17 with `pendingEntry()`. I
didn't run anything.

| Item | Status | Evidence |
|---|---|---|
| J1: cancellation evidence | **Resolved** | See the notes below. |
| J2: search toggle | **Resolved** | It now requires the native search-arm varp `Isaac.anIntArray1303[190]==0` before recording the toggle. |
| J5: timeout message | **Resolved** | `NativeSessionSmoke` prints `NativePlayableLoopProbe.progress()` (stage and tile) when the overall budget runs out during a journey. |
| J6: config overwrite | **Resolved** | Covered by the `serverCancel` assertion described under J1. |
| J3, J4 | **Open (low)** | Unchanged: the door stages pass on time, and the stick magnitude can switch on running. Both fail safe through the BFS and stage timeouts. |

**J1 in detail:**
- **What the reply reveals, and to whom.** The command answers only the **requesting player's** own
  `suspension` class (none/int/name/string/other). It answers only when the **server process**
  environment has `SOLOSCAPE_NATIVE_PROBE=1`, and only for a 32-hex nonce. It is read-only:
  `ExecuteCommandHandler` runs it in a separate `Script.launch` with no `closeInterfaces`,
  `closeDialogue` or queue work, so asking can't itself clear the suspension it reports.
- **Where the variable is set.** `smoke_profile.py` adds the variable only to the `void-server`
  `Popen` and only with `--journey`, merging it into the session environment. The client and
  the ordinary launcher never set it.
- **What the probe now asserts.**
  - A fresh nonce for each stage (`next()` clears `probeNonce`), so step 14 can't read step 13's
    `int` reply.
  - `int` **before** the cancel. That proves the server was waiting.
  - `ControllerEntry.serverCancel` is true (this also resolves J6).
  - `none` **after** the client prompt has gone and 1.5 s have passed.

  A client-only close, or a server that ignored the packet, now fails with "Server suspension
  survived Cancel".

### Remaining notes (low, not blockers)
- **Q1. The opt-in rests on an inherited variable.** If a user's own shell exports
  `SOLOSCAPE_NATIVE_PROBE=1`, ordinary launcher worlds inherit it through `os.environ` and
  answer the query. It's read-only and reveals only the asker's own state, so there's no
  integrity risk. To make the opt-in strict, have `profile_session` remove the variable from
  the server environment unless a probe explicitly asks for it.
- **Q2. The replies are visible.** `SOLOSCAPE-PROBE|…` replies don't match the
  `ServerCapabilities.receive` prefix (`SOLOSCAPE|`), so they show up as ordinary game chat and
  stay in the disposable profile's chat history. That's harmless, but suppressing that prefix
  too would keep probe screenshots clean.
- **Q3. The command is always registered.** It's registered on every server and simply does
  nothing without the variable, so it may appear in command listings or autofill on ordinary
  worlds. That's cosmetic.

### Final resolution
**No blockers in the harness evidence path.** J1, J2, J5 and J6 are resolved. J3 and J4 remain
as low-severity notes that fail safe. The server-side cancel can now be distinguished from a
client-only close in the native run. The outcome of the actual host and Deck journeys is still
pending and is not claimed here.

## Idempotent inventory open (`ControllerUi.openTab(INVENTORY)`): static check
I read `ControllerUi.openTab` (`:527-543`), `snapshot(true)` and `inventoryVisible`
(`:184-202`), `UiState.hasInventory`, the callers (the plugin's `openHomeTab`, selection-return
restore, the radial and quick gateways, and `NativePlayableLoopProbe` step 0), and
`openingVisibleInventoryIsIdempotentWithoutReclickingNativeTab`. I ran nothing.

**Verdict: sound, no blockers.**
- **The check is live.** `inventoryVisible` requires that interface 149 is open **and** that
  `isVisible(loadedWidget(INVENTORY))` is true on the current widget tree. So when a resized
  side panel is collapsed, or another side tab is selected (a hidden ancestor), it reports
  false and the native type-18 tab action is still invoked. Only an inventory that is already
  showing becomes a no-op, which is exactly the case where re-clicking would collapse it.
- **The guards are unchanged and come first.** `ready()`, the dialogue check, the modal check
  (so a bank still returns false), the entry check and the index bounds all run before the
  shortcut. The inventory shortcut doesn't bypass any of them.
- **Callers want "ensure open", not "toggle".** Home and radial focus, selection-return
  restore (`origin.tab`), and the probe all treat `true` as "the inventory is showing". No
  caller uses `openTab(INVENTORY)` to close it. `settingsOpen` is set only for SETTINGS.
- **Native integrity holds.** The no-op sends no packet and leaves the visible slots alone. It
  fixes the probe's hidden-slot problem, where a duplicate open collapsed the slots so the
  existing starter Empty pot was never observed.

### Low notes
- **K1. The hidden-to-open branch isn't covered by a test.** The new test checks the visible
  case and that `openInventory()` returns false once `outer` is hidden. It doesn't assert that
  `openTab(INVENTORY)` **does** dispatch the native tab action when the inventory is hidden or
  collapsed. **Fix:** add that assertion (for example the type-18 invoke or the recorded native
  operation, as in `radialDispatchesTheOrdinaryNativeTabOperationPacket`), so a future change
  can't turn the shortcut into "always true".
- **K2. Other tabs still toggle.** Re-selecting an already selected non-inventory tab (for
  example Spellbook from Home while it's showing) still re-clicks the native tab, and that
  could collapse it in the same resized frame. If that is the native behaviour for every
  side tab, the same "already visible" check could be generalised using that tab's root. Worth
  one native observation before changing anything.

## Stage 8 staircase stall: object reach semantics (static; hypotheses pending the candidate dump)
I read `ControllerWorld.reachable(ControllerTarget)` and `reachable(x,y,w,h,shape,rot,access)`,
`interact`, `nearby` and `candidates`. On the native side I read `Class309` (the object route
dispatch), `Class298.method2252`, `Class59_Sub2_Sub2.method574`, `Class5_Sub1.method187`,
`Class361.method3495/3497/3503/3504` and `Class239_Sub28.method1842`. I made no edits.

### Established by code reading
1. **How the native route-finder dispatches on its "shape" code** (`Class5_Sub1.method187`,
   player size 1):

   | Code | Check | Meaning |
   |---|---|---|
   | `-4` | exact tile | |
   | `-3` | `method1842` | rectangle overlap |
   | `-2` | `Class361.method3497` | edge adjacency to a w×h rectangle with an access mask, excluding the inside (actor/NPC style) |
   | `-1` | `Class361.method3503` | object rectangle: inside, or edge-adjacent with access-mask and wall-flag checks; for size > 1 it delegates to `method1842` + `method3497` |
   | `0,1,2,3,9` | `method3495` | **wall** reach for that wall shape and rotation; **ignores width, height and access** |
   | `4–8` (and anything else, including 10, 11 and 22 if passed raw) | `method3504` | wall decoration |
2. **The native client passes code 0 for shapes 10, 11 and 22, with dimensions and access, and
   `nearest=true`.** `Class309` computes width and height (swapped for odd rotation) and the
   rotated access, then calls `method2252(true, x, y, …, height=…, access, width=…, shape 0,
   rotation 0)`. So the native exact-reach test for these objects is "wall shape 0 at rotation
   0" at the **origin tile**. The rectangle data only feeds the **nearest-tile fallback**
   (`method574` scores candidate tiles by distance to the w×h rectangle). In practice the native
   client walks next to the rectangle, and the server decides the actual interaction approach.
3. **`ControllerWorld` reproduces the native arguments exactly, but with `nearest=false`.**
   - The width/height swap for odd rotations matches `Class309`.
   - The rotated access `(access<<rot & 15) + (access >> (4-rot))` matches native precedence.
   - Rotation `(id>>20)&3` equals native `(0x37d8b0 & id) >> 20`.
   - Shape 0 and rotation 0 are passed.

   With `nearest=false`, the strict guard therefore accepts a 10/11/22 object **only** if the
   BFS reaches one of these, within 8 tiles of path:
   - the origin tile;
   - the tile **west** of the origin (`x-1, y`; no flag check);
   - the tile **north** (`x, y+1`; wall mask `0x2c0120` clear);
   - the tile **south** (`x, y-1`; wall mask `0x2c0102` clear).

   Standing next to any **other** edge of a multi-tile footprint, such as the east side or the
   south side beyond the origin column, isn't accepted. Wall-shape objects (0–3 and 9) and
   decorations (4–8) receive their real shape and rotation, which is correct.
4. **`interact()` enforces this guard for objects.** It requires
   `nearby && (serverApproach || reachable(current))`. `serverApproach` is true only for attacks
   and selected-spell casts, so a staircase "Climb-up" always goes through the wall-0 test.

### Likely cause of the stage 8 stall (hypothesis; check against the dump)
The player stands at (3205,3228), and the staircase origin is (3204,3229). That tile is
diagonal to the origin and is none of origin, west, north or south. If the origin's south tile
(3204,3228), west tile (3203,3229) and north tile (3204,3230) are all blocked (wall flags,
stair footprint, castle wall), or BFS can't reach them within 8 tiles, then
`reachable(staircase)` is false. `interact("Staircase","Climb-up",3204,3229)` then never
dispatches, and the stage waits until its 60 s timeout.

That fits what you saw, but it **isn't established**. Other causes the candidate dump can rule
in or out:
- **Option text.** The real label might be "Climb up" or similar, rather than "Climb-up".
- **Origin coordinates.** The target's `x+baseX`/`y+baseY` might differ from (3204,3229), for
  example if the dump shows a rotated footprint whose origin isn't the tile in the probe.
- **Object type.** The staircase might not be shape 10/11/22 at all.

### On your question: wall-0 against rectangular −2
- For a strict, no-fallback guard on 10/11/22 objects, the native code that matches what the
  rectangle data means is **−1 (`method3503`)**, not −2. For a size-1 player, −1 accepts the
  inside of the w×h footprint or any edge-adjacent tile. It checks the rotated access mask per
  side (`0x8`/`0x2`/`0x4`/`0x1`) and the destination-side wall flags. For larger movers it
  delegates to the −2 logic (`method1842` + `method3497`).
- **−2 (`method3497`)** is the actor variant. It excludes the inside, and it's what native
  uses for NPC and player targets.
- Either way, the call would become `reachable(x, y, width, height, -1, 0, access)` for shapes
  10, 11 and 22, keeping the existing dimension and rotated-access computation.
- This deliberately **departs** from native, which uses wall-0 plus nearest. It's a stricter
  but footprint-correct exact guard. It also lines up better with the server, whose object
  reach for rectangle locations uses the footprint and the block/access flags.

**Suggested regression, before changing behaviour:** a `ControllerWorldTest` collision fixture
with a 2×2 rectangle at (10,10) and access 0. The player at (12,10) (east-adjacent) and at
(11,9) (south of the non-origin column) should be reachable under −1 and not reachable under
the current shape-0 call. Add a case with the access bit set on one side, which must stay
unreachable.

### Limits
- Static. I haven't seen the staircase's id, shape, rotation, size, access or the collision
  flags around (3204..3206, 3228..3230). The candidate and collision dump should confirm or
  refute the hypothesis before the guard is changed.

## Footprint reach fix (`reachableFootprint`, −2) and the K1 test: static review
I read `ControllerWorld.reachable(ControllerTarget)` → `reachableFootprint`, the native
`Class361.method3497` (−2) and `method3503` (−1) with their argument mapping from
`Class5_Sub1.method187`, `ControllerWorldTest.rectangularObjectCanUseAnOpenEdgeWhenItsAnchorIsAgainstAWall`,
and `ControllerUiTest.collapsedInventoryStillDispatchesTheOrdinaryNativeOpenPacket`. I ran
nothing.

**Verdict: correct. −2 is an appropriate choice, and I withdraw my earlier preference for −1.**
For a size-1 player, the two give the same answer except for one edge case that doesn't matter.

### Native semantics, with arguments mapped from `method187`
`method3497(…, destX, access, 1, height, curX, 1, curY, destY, width)`:
- **Player just east** (`destX+width == curX`, access bit `0x2` clear): accept if some
  overlapping row has the footprint's east column tile without wall bit `0x8`.
- **Player just west** (`destX == curX+1`, access `0x8` clear): footprint west column without
  `0x80`.
- **Player just north** (`destY+height == curY`, access `0x1` clear): footprint top row without
  `0x2`.
- **Player just south** (`destY == curY+1`, access `0x4` clear): footprint bottom row without
  `0x20`.
- Rows and columns must overlap, so diagonal tiles and the inside are rejected.

`method3503` for size 1 accepts the **inside**, then makes the same four side tests with the
**same access bits**. The only difference is that it reads the opposite face of each wall from
the **player's** tile (`0x8`/`0x80`/`0x2`/`0x20` swapped). RS collision marks both faces of
a wall, so the two agree on real map data. The only behavioural difference is "player inside
the footprint", which is impossible for solid 10/11 objects. For walkable 22 decorations, −2
just requires a one-step move onto an edge, and the BFS supplies that.

−2 is also the code native already uses for NPC and player approach, so it's the
better-exercised path.

### The rest is unchanged and consistent
- **Wall shapes.** 0–3 and 9 still use their real shape and rotation, and 4–8 the decoration
  path.
- **Size and access.** The width/height swap and the rotated access come before the new call
  and match `Class309`.
- **Path limits.** The 8-tile path-distance bound and the `paths` cache (at most 8 geometries)
  still apply.
- **`interact()`.** It still re-enumerates, then requires `nearby` and a reachable target.

### The regression is sound
The fixture: a fully blocked column at x=62, the anchor's south tile (63,64) blocked, and a 2×3
footprint `0x40000000` (blocks movement, no wall bits). The player at (64,64) is south of the
second column.
- **Old shape-0 call: false.** The anchor's west and south tiles are blocked, and north is inside
  the footprint.
- **`reachableFootprint`, access 0: true.** This is case 4: `destY == curY+1`, and the
  footprint tile (64,65) has no `0x20` bit.
- **Access 15: false.**
- **Player at y=62 behind a fully blocked row 64: false.**

**Optional additions:**
- **(a) East or north side with an odd rotation, end to end.** Go through
  `reachable(ControllerTarget)` with a fake `Class51`, so the dimension swap and access rotation
  are pinned against an asymmetric footprint (e.g. 1×3 at rotation 1 → 3×1), with one access bit
  set.
- **(b) A wall face on the open edge.** Set `0x20` on footprint tile (64,65) and expect false,
  which checks the wall-bit side rather than only the access mask.

### K1
**Resolved.** `openInventory()` delegates to `openTab(INVENTORY)` (`ControllerUi.java:487-490`),
so the new test exercises the collapsed branch of the idempotent shortcut. It hides the
container, asserts `hasInventory()` is false, and requires exactly one queued packet whose
decoded opcode is the ordinary native interface-button packet (`Class27.aClass351_398`). It
restores the queue, cipher and byte counter in `finally`.

No blockers. The native staircase stage still needs your rebuilt host run to confirm it.

## Final clarification: −1 in the final code
The final code uses `reachableFootprint(...) → reachable(x, y, w, h, -1, 0, access)`
(`ControllerWorld.java:353-355`). To be clear about the record: my first analysis recommended
−1, and the follow-up called −2 equally acceptable. **Both are correct for a size-1 player.**

−1 is the native **object** rectangle check (`method3503`). It accepts the inside of the
footprint, then makes the same four edge tests as −2, with identical access bits (`0x8` west,
`0x2` east, `0x4` south, `0x1` north). The only other difference is that it reads each wall
face from the player's tile, and RS collision sets both faces, so this agrees with −2 on real
map data. Accepting the inside is the one behavioural difference. It matters only for walkable
footprints (for example shape-22 decorations), and it ignores the access mask there, as native
does.

- **The existing tests still hold under −1:**
  - `rectangularObjectCanUseAnOpenEdgeWhenItsAnchorIsAgainstAWall`: the player is outside,
    the south edge passes with access bit `0x4` clear, and the player's tile has no `0x2`.
  - The access-15 case is still false.
  - The case with the player behind the wall is still false.
- **The new test `walkableObjectFootprintCanBeUsedWhileStandingInside`** (1×1 at the player's
  tile, access 15 → true) correctly pins the inside branch.

No further code findings. The 208-case suite, the K1 packet case and the rebuild stamp are as
you reported them. The native staircase and Lumbridge round-trip results are pending and not
claimed here.

## Cancellation cleanup follow-up (actual Claude, 10 October)

Claude reviewed the new Script cancellation catch/test and native coin-stack Cancel probe read-only through the existing Orca Claude terminal. No blockers: rethrowing CancellationException retains cancellation and cleanup without a false error log; Unconfined makes the continuation/job regression deterministic. Real exceptions from finally still reach the error logger. The native probe must select bank coins specifically; that ambiguity was removed. Native bank diagnostics reported int before Cancel and none afterward, bank open and coins unchanged. Search and full-route acceptance were still pending at this review.

## Final static review: Bank Search ordering and the stronger search assertions
I read `ControllerUi.invoke` (`:615-618`), `ControllerEntry.observe`/`prepare`,
`Class348_Sub9.method2780`, the server's `BankOpen.kt` Search option (`armBankSearch()`, the
`bank_searching` toggle, and the resend on toggle-off), and probe stages 15–17 with
`bankItem()`. I ran nothing.

### Ordering (final)
- **The native click runs its script synchronously.** `method2780` runs the button's click
  script (1471) through `Class66.method705`, which calls `observe`, and then queues the
  ordinary IF_BUTTON packet. My earlier guess that the click script was **queued** for a later
  cycle was wrong. The synchronous order is what the fix relies on.
- **The fix.** `requestBankSearch()` now runs **before** the native dispatch, and `observe`
  clears the request when it sees 1471. A native toggle therefore always uses up the request,
  so `prepare()` can't run 1471 a second time.
- **What the fallback is now for.** It covers only a dispatch that ran no click script (no
  handler, or the widget vanished). It acts only while varc 190 is 1 and only within the
  2-second window.
- **Re-arming.** On each Search the server calls `armBankSearch()`, which sets varc 190 back to
  1, and toggles `bank_searching`. On toggle-off it resends `bank` and runs
  `update_bank_slots`. So varc 190 being 1 after toggle-off is **intended**, and the old
  stage-17 assertion (`varc190==0`) was wrong. That matches the native result.

### The stronger assertions are sound
- **Stage 16: search filters for real.** With "pot" searched, the pot must still be visible in
  the bank, and `bankItem(state, 995)` must be **null**. That helper is limited to widgets of
  group 762, so inventory-side coins can't satisfy it. Steps 13–14 already proved bank coins
  exist, so null can only mean the filter worked.
- **Stage 17: search fully toggled off.** It requires all three:
  - varc 5 (entry type) is 0;
  - varc 188 (client search mode) is 0;
  - bank coins are visible again, which depends on the server's resend.

  That checks both the client state and the server's toggle. `native_search_button_rearmed`
  records varc 190 for information only.
- **Ordering of search, cancel and toggle.** Stage 16's cancel is local (`close_entry` for type
  11; no server message, by design). Server `bank_searching` stays true, so the stage-17 click
  turns it off on both sides, and the client and server agree.

### Low notes
- **S1. Stage 17 checks once instead of polling.** It runs its `require` once, about 1 s after
  the Search dispatch (the window is measured from stage entry, and the dispatch happens at
  least 1 s in). A slow server resend would fail it falsely. Poll until the condition holds,
  within the stage deadline, and measure from the dispatch time.
- **S2. The fallback can desynchronise client and server.** If `prepare()` ever runs 1471
  itself, no IF_BUTTON packet is sent, so client search mode flips while server
  `bank_searching` doesn't. The next toggle-off would then skip the bank resend. The fix makes
  this path rare. Recording when the fallback fires (a counter in the probe results) would show
  whether it ever happens natively.

### Status
No blockers in the static search and cancel path. Native Search with type 11, edit and cancel
was observed on the host, and stage 17 failed only on the corrected varc-190 assertion. **The
complete native New/Continue journey is still pending**; the root rerun is live. No pass is
claimed here.

## Search filter after a controller edit (client patch 0035): static review
I read `ControllerEntry.edit` (`:80-92`) and three `ControllerEntryTest` cases:
`bankSearchEditRunsNativeFilterAndRejectsStaleText`,
`searchFilterIsNotAppliedToAReplacementPromptDuringEdit` and the existing
`replacedPromptInvalidatesSnapshotEvenIfTypeTextAndValueAreIdentical`. I ran nothing.

**Verdict: correct, no blockers.**
- **Why it was needed.** The native key path (script 112) runs 1475 after a type-11 edit, which
  is what refreshes the bank filter. Script 1564 only rewrites the text and caret. A controller
  edit that ran only 1564 therefore changed the text but never filtered, which is the stage-16
  "pot typed, coins still shown" failure. Running 1475 after 1564 for type 11 reproduces the
  native order.
- **The extra script runs only for the same prompt.** After 1564, `edit` takes a **fresh**
  snapshot and runs 1475 only if it is still the same session (`revision` unchanged) **and**
  the value equals the text just written. A prompt replaced during 1564 (`observe` bumps
  `revision` on 108/109/110/1471/1472/101), or text that didn't take, skips the filter. The
  pre-edit checks (same session and unchanged value) are kept, so stale edits are still
  rejected before anything runs.
- **Scope.** Types 7, 8 and 9 are unchanged: no 1475 and no extra snapshot. Physical typing
  still goes through native 112. Running 1475 on each controller edit matches native per-key
  behaviour.
- **The tests pin the right things:**
  - the normal type-11 order is `[1564,"pot"]` then `[1475]`;
  - a stale second edit against the original snapshot is rejected with no script run;
  - a 1472 observed during 1564 (a replacement) suppresses 1475, with only one call.

### Low notes
- **E1. 1475 must take no arguments.** `scripts.run(new Object[]{1475})` passes no arguments.
  Please confirm from the cache script header that 1475's int and string argument counts are
  0, and that 112 calls it via a bare `gosub 1475`. If it expects arguments, for example the
  key code or char, the interpreter would read past its stack. The fast native bank diagnostic
  will show this: an exception in the client log, or no filtering.
- **E2. `edit` returns true even when the filter is skipped.** When the prompt is replaced
  during the edit, `edit` still returns true. That's harmless, because the old session is gone
  and the caller's next snapshot sees the new prompt. Just note that "edit true" doesn't mean
  "filter applied". The probe's stage-16 `bankItem(995)==null` check covers the actual
  outcome.

### Status
The fix is statically sound. The fast native bank diagnostic and the **complete native
New/Continue journey are still pending**. No pass is claimed.

## Reported native evidence: fast bank-only diagnostic (scope recorded exactly)
**Source.** These results come from the root's terminal report. I didn't run or observe them,
and this entry only records their scope against the static review above.

**What passed.** The fast native **bank-only** diagnostic exited 0 with a saved and verified
world, covering:
- **Banker:** the real banker opened the bank.
- **Withdraw-X cancel:** the server reported pending `int` before Cancel and `none` after it,
  with the bank and bank coins unchanged.
- **Search filtering:** with "pot" searched, bank coins were excluded. This exercises the
  patch-0035 `1564` → `1475` path.
- **Search toggle-off:** entry type 0 and search mode 0, the coins restored by the server
  resend, and varc 190 = 1 (the server's deliberate re-arm).
- **Withdrawal:** a normal withdrawal after cancel.
- **Exit:** the bank closed, followed by native logout and relog.

**What this does *not* cover:**
- the complete New/Continue journey;
- the kitchen pot gathering, courtyard walking, door and castle staircase stages (including
  the footprint-reach fix in a live run), and the return trip;
- the New/Continue save comparison;
- the Deck.

**Harness changes reported since, not yet seen in a native run:**
- **E1:** the full harness asserts that script 1475's int and string argument counts are both 0.
- **S1:** stage 17 now polls from the Search dispatch time within the stage deadline, instead
  of checking once.

**Status.** The full fresh host and Deck New/Continue runs are **live and pending**. No full
journey pass is claimed. The remaining low items (J3/J4 door and run side effects, S2 fallback
desync visibility, Q1–Q3 probe-command hygiene) are unchanged.

## Final integration evidence (root, after Claude review)

Full host and actual Deck New/Continue runs both exit zero: all castle/bank/search/source/equipment routes, native logout/relog, exact tested save fields, four verified backups, original mutable fingerprints and cancelled-startup whole-world preservation. Native cache script 1475 has zero int/string arguments (E1 resolved); both filter/restore checks pass. Stage17 polls from actual dispatch time within the deadline (S1 resolved). Remaining S2 fallback desynchronisation concern is unobserved; normal dispatch sends its original native button packet and consumes the fallback synchronously. No physical/Gaming Mode/suspend result is inferred.

Claude also authored the standalone first-time Deck player guide, then incorporated root corrections for B scope, action-list D-pad versus pane scrolling, Steam amount cancellation, input layout/Proton and exact New/Continue status. Root checked the fork's actual Configuration UI: ConfigPlugin labels the button Configuration and PluginListPanel has a scrolling plugin list with no search field; guide instructions were corrected to scroll to SoloScape Controller. The plugin defaults disabled and must be enabled once per new character.
