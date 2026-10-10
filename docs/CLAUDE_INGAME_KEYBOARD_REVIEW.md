# In-game keyboard ownership: static review

This was a bounded, read-only review. I read:
- `SystemEntryControls`, `SteamKeyboard`, `KeyboardMode`
- in `SoloScapeControllerPlugin`: `textKeys`, `textEntryAction`, `openTextKeyboard`, the
  ownership block in `onClientTick`, and `reset`
- `SoloScapeTextEntryOverlay`
- `ControllerEntry.nativeKey`, `ControllerUi.entryReady`
- `GameClient`/`Applet_Sub1.finishControllerNativeText`
- the keyboard rows in `ControllerSettingsModel`
- the native `Class346_Sub1` key listener, for context

I ran no build or tests, used no Git or SSH, and changed no source. No Deck or controller
hardware behaviour is claimed.

## Verdict
**One high and two medium defects.** The rest looks sound:
- **Ownership is properly exclusive.** While `systemEntry.active()`, the tick returns before
  any controller handling. It zeroes the camera, resets world, UI and the radials, and disarms
  the mapping. The tick on which ownership is released also returns, so the next tick needs a
  neutral controller again. `customPanelActive()` stays off throughout.
- **Ending a session.** A recognized prompt is released only when its native snapshot
  disappears. A config switch to controller mode, or losing the local player (logout, a
  reconnect gap), resets the session and closes the keyboard. `reset()` clears everything when
  the plugin stops.
- **Stale UI actions are blocked.** Overlay buttons carry the render `revision`. `owns()` and
  `sameSession()` reject stale or cross-session taps, and Done/Cancel on a prompt use the native
  submit and cancel after a same-session check.
- **Manual Done/Cancel sends native keys only.** `nativeKey` sends a native Enter or Escape
  through the client's own `synchronized` key listener, so the normal native key mapping and the
  RuneLite hooks apply. No chat packet is made up.
- **The Steam requests are bounded.** They are queued in order, wait at most 3 s, and destroy
  the process on timeout. A non-zero exit is reported in the overlay. Mode 3 is used for numeric
  prompts.

## Findings

### H1. High: controller mode swallows every physical key in a native prompt, even with no controller
`localTextEntry = nativeEntry != null && !steamTextMode && interfaceControls`
(`SoloScapeControllerPlugin.java`, `onClientTick`). This is computed **before** the checks for a
connected controller, canvas focus and `ui.entry().active()`.

`textKeys.keyPressed` and `keyTyped` then call `consume()` for **every** key. Native input goes
through `InputHooks.keyPressed` (`Class346_Sub1.java:64`), so the client never sees any of them:
not digits, not letters, not Enter, not Escape.

The defaults are `keyboardMode=AUTO` (which means controller mode off a Deck) and
`interfaceControls=true`. So on an ordinary PC with the plugin enabled, any native prompt can't
be typed into or cancelled from the keyboard, even when no controller is connected. When no
controller is connected the controller grid never updates either (the tick returns at
`!state.connected`), so the prompt can only be answered by mouse, if at all.

**Trigger:** use a desktop PC (no Deck, no controller), enable the plugin, open a bank, choose
Withdraw-X, and type `5` then Enter. Nothing reaches the prompt.

**Smallest fix:** add `state.connected && canvas.isFocusOwner() && ui.entry().active()` to the
`localTextEntry` condition, and consume only the keys the Deck desktop layout produces (arrows,
Enter, Escape, Space, Backspace). Let letters and digits through, so native keys stay the ones
that count, as you intend.

### M1. Medium: any typed Space or character latches Steam ownership and opens the Steam keyboard
`keyTyped` calls `beginManual` for any `keyChar >= 32` while in Steam mode with a local player.
Two consequences:
- **A controller button can freeze the controller.** If Steam's desktop layout maps a controller
  button to **Space** (the launcher dispatcher consumes Space for this reason), pressing that
  button in game latches manual ownership. The controller then pauses until Enter, Escape or a
  tap.
- **The Steam keyboard pops up for physical-keyboard users.** On a Deck with a keyboard
  attached, or in STEAM mode on a desktop, the first typed character also calls
  `keyboard.visible(true)`, which opens the Steam on-screen keyboard over the game while the
  user is already typing on real keys.

**Fix:**
- Ignore a typed character that arrives while `rawState.buttonsHeld != 0`, or within about one
  frame of an SDL button edge, so it can't come from the controller's desktop mapping.
- For a typed-character latch, set ownership **without** opening the Steam keyboard. Open it
  only for a recognized prompt, RS click or the settings action.

### M2. Medium: the text overlay swallows every mouse press across the whole canvas
`SoloScapeTextEntryOverlay.mousePressed` consumes any press while `systemTextActive()`, not
just presses inside its 460×150 box. Its released, clicked and dragged handlers do the same.

During a recognized prompt, or after a typed-character latch (M1), touch and mouse can't reach
the native prompt, the chatbox or the world until the session ends. On a Deck, a single stray
latch makes the touchscreen useless for the game.

**Fix:** consume only when the event point falls inside the last painted box, and keep
`captured` for a press that started inside it.

### Low notes
- **L1. Manual Cancel may leave chat text behind.** It sends a native Escape. I couldn't confirm
  statically that the 634 client clears the chat input on Escape. If it doesn't, the typed text
  stays, ownership ends, and the next typed character latches again. Worth one native probe
  assertion.
- **L2. A manual session followed by a recognized prompt flickers the Steam keyboard.**
  `update` treats `entry==null` as a new session, so it sends close then open. That's harmless,
  but you could skip the close when switching from a manual session to a prompt.
- **L3. Done/Cancel through `nativeKey` also hit `textKeys`.** The injected Enter or Escape goes
  through `InputHooks` → `textKeys.keyPressed`, which schedules a second `finishManual`. The
  revision check makes that a no-op, so it's fine, but don't add any side effect to that path.
- **L4. Theme setter.** As you noted, `ControllerTheme.classic(config.classicTheme())` runs every
  tick, and it currently reallocates every colour each time. The unchanged-value guard you plan
  fixes that (`if(enabled==classic&&BACKGROUND!=null)return;`).

## Limits
- Static only. I didn't confirm that the native chat responds to an injected Enter or Escape on
  the client thread (it is `synchronized`, so it should be thread-safe), what the Deck desktop
  layout maps to keys, or how the Steam keyboard behaves.
- I didn't re-audit `ControllerEntry` editing or the controller-grid path beyond the
  ownership interplay above.

## Follow-up after the fixes (static, read-only)
I re-read `KeyboardInputPolicy`, `SystemEntryControls`, the plugin's `textKeys` and ownership
tick, `SoloScapeTextEntryOverlay` and the new `scripts/harness/NativeTextProbe.java` (wired from
`NativeAdventureProbe` step 15). I ran no build or tests, made no source changes, and make no
hardware claim. The client suite and native smoke results are as you reported them.

| Finding | Status | Evidence |
|---|---|---|
| H1: physical keys swallowed | **Resolved** | `localTextEntry` now requires a native entry, controller mode, `interfaceControls`, `rawState.connected`, canvas focus and an active entry grid. It is recomputed every tick before any return, and re-derived after `ui.update` (`SoloScapeControllerPlugin.java:381, :420`). `textKeys` consumes only `KeyboardInputPolicy.localNavigation` keys, so letters, digits and every key release still reach the client. |
| M1: typed latch | **Resolved** | `adoptTyped` accepts only printable `KEY_TYPED` characters with code above 32 (so not Space, Enter or control characters), only with no controller button held, and only at least 100 ms after the last controller button activity. The latch uses `beginManual(...,false)`. With `requested=false`, `reset()` sends no close either. A recognized prompt that follows still opens the keyboard (`update` sets `requested=true` and skips the close when nothing was requested). |
| M2: overlay swallows clicks | **Resolved** | Presses are consumed only inside the last painted `bounds`. Release and drag are consumed only for a press that started there, and click only inside the bounds. |
| L4: theme allocations | **Reported fixed** | I didn't re-read this. |

### Remaining notes (low)
- **F1. A physical keyboard loses Enter, Escape and Backspace while the controller grid is
  active.** That is by design: with a controller connected and the grid active, the grid owns
  editing. A mixed user (controller connected, typing digits on a real keyboard) still can't
  submit with the real Enter key until the controller disconnects or focus leaves. Consider
  mentioning this in the setting's description.
- **F2. The 100 ms recent-button guard only looks backwards.** A desktop-mapped key event can
  reach AWT **before** the next client tick polls SDL, so `held==0` and the last button time is
  old. Excluding Space and control characters makes this harmless with the usual Deck desktop
  layout. It only matters if a controller button is ever mapped to a printable character.
- **F3. `NativeTextProbe` leaves typed text in the chat input when Escape keeps it.**
  `native_chat_escape_retains_text` is recorded truthfully but isn't cleared. Afterwards the
  adventure probe goes back to step 11 (Exit, then logout). Nothing there sends Enter, so it's
  harmless today. Any later step that submits a native Enter would post `solo_cancel_probe`.
  **Fix:** clear the native chat buffer, or send Backspaces through the native listener, in
  `cleanup()`.
- **F4. The probe runs `onClientTick` a second time each frame and doesn't close SDL.**
  `poll()` calls `onClientTick` in addition to the event-bus subscription. That's idempotent
  here, but each frame's ownership update runs twice. If the plugin wasn't active (`priorActive`
  false), forcing `active=true` makes `pollController()` create and initialize an `SdlGamepad`,
  and `cleanup()` restores `active` without closing it. Because of that SDL step, a probe on an
  SDL-less host could set `failed` and skip the rest of the plugin's work. **Fix:** in
  `cleanup()`, when `!priorActive`, close the created gamepad, or have the probe skip polling.
- **F5. Probe coverage.** The probe swaps the `private final systemEntry` by reflection. That
  works on Java 8 for instance fields, and the `textKeys` lambda reads the field each time, so
  the swap takes effect. It doesn't exercise the three fixes themselves (H1 consumption, the M1
  Space exclusion and button guard, M2 bounds). Those rely on the unit cases you reported.
  Config changes persist only to the disposable profile's `client_home` (`profile_session.py:95`).

No new high or medium findings.

## Follow-up: native `close_entry` cancel and the probe cleanup (static)
I read `ControllerEntry.cancel`, `observe` and `snapshot`, the server's `DialogueInput.kt`,
`Interfaces.closeDialogue`, `Interact.start` and `ActionQueue.logout`, and the probe's
cleanup. I didn't build or run anything, and this doesn't claim the fixtures pass.

**Verdict: no blockers.**

### Cancel freshness and identity: sound
- `cancel` takes a fresh `snapshot()` on the client thread. It runs `{101}` only when the
  current entry is the **same session** as the one the caller held, so a stale overlay tap or
  controller B after the prompt changed does nothing.
- The value isn't compared, which is correct: cancelling doesn't depend on the text.
- Running 101 goes through the observed script path (`observe` bumps `revision` for
  101/108/109/110/1472), so any later stale `edit` or `submit` against the old session fails
  `sameSession`.
- Physical Escape keeps its native meaning, and Enter is still the native script 112.
- No packet is made up: 101 is the same script the server itself sends as `close_entry`.

### C1. Low: cancelling closes the prompt on the client only; the server keeps waiting
The 634 protocol has no cancel message for an entry prompt. The server clears
`Suspension.IntEntry`/`NameEntry`/`StringEntry` only in these cases:
- an answer arrives (`DialogueInput.kt:44-56`);
- `closeDialogue()` runs (`Interfaces.kt:283-289`, which also covers `closeInterfaces`);
- a new interaction starts (`Interact.start`, `:71-73`).

After a controller Cancel, the waiting server action (for example a withdraw-X) stays pending
until one of those happens. While it is pending, `walkTrigger` and `Interact` treat the player
as busy (`Character.kt:67`, `Interact.kt:103/190`). This is the same server state a native
player gets by ignoring a prompt, so it is not a new class of state. But the controller copy
shouldn't suggest that the server action was cancelled.

A related point I found, which this change doesn't cause: `ActionQueue.logout()` spins
`while (suspension != null)` and handles only Continue, Custom and Delay
(`ActionQueue.kt:114-121`). If a pending **long-priority** queued action is waiting on an
Int/Name/String entry at logout, that loop doesn't end. I didn't check whether the logout path
calls `closeDialogue` before this point. It is worth one native fixture: start a Withdraw-X,
press controller Cancel, then log out.

### C2. Low: type 11 isn't covered
`active()` also accepts entry type **11**. Neither the old Escape route (script 112 handled
only 12 and 14) nor the new `{101}` has a fixture for type 11. **Fix:** either exclude 11 from
controller cancel or add a fixture that proves `close_entry` closes it.

### Harness cleanup
- **H1. Possible false cleanup failure.** `retainedChat()` searches **every** entry of
  `Class258_Sub2.aStringArray8532` for `solo_cancel_probe`. That array also holds the entry
  value at index 22, so it is a general client string table, not only the chat input. If the
  client also keeps the cancelled line in another slot (history, or a "last typed" value),
  Backspace can't clear that slot, and stage 11 fails after 5 s even though the chat input is
  empty. **Fix:** record the index where the text was found at stage 10, wait only on that
  index, and put the index in the failure message.
- **H2. `cleanup()` runs only on success.** The probe's stage throws or `require` failures go
  through `NativeAdventureProbe`/`NativeSessionSmoke`, which exit without calling
  `NativeTextProbe.cleanup()`. The SDL close, the field restore and the config restore are
  then skipped. The process exits and the config is the disposable profile's, so this is
  contained. Calling `cleanup()` in the harness's failure path would still make it
  deterministic.
- **H3. Cleanup ordering is correct.** The SDL provider is closed only when it is a new object
  created by the probe while the plugin was inactive, and the plugin's own controller is never
  touched. `failed` and `gamepad` are restored before `active`. With the duplicate tick
  removed, an active plugin's event-bus tick (on the `systemEntry` swapped by reflection)
  drives ownership between probe calls, which are about 500 ms apart.
