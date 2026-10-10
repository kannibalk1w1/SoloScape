# Launcher keyboard ownership (patch 0029): static review

This was a read-only review of the uncommitted changes. I read:
- `LauncherKeyboard.java`
- `SoloScapeLauncher.java` (`newCharacter` and the controller timer)
- `LauncherKeyboardTest.java`
- `scripts/deck-launch.sh`
- the file list of `patches/client/0029-launcher-keyboard-ownership.patch`

I ran no tests or builds and used no Git. The Deck hardware behaviour is **not validated**.

## Verdict
**No blockers.** The fix targets the reported problems directly:
- **Steam typing also typed a SoloScape key.** In Steam mode, the timer hands the controller
  state to `keyboard.update`, which ignores it (`LauncherKeyboard.java:108`). The timer then
  returns without arming (`SoloScapeLauncher.java:267`).
- **The D-pad moved the caret.** In SoloScape mode, a `KeyEventDispatcher` consumes the
  navigation keys that the desktop layout produces.

There are two **medium** findings. Both are about controller-only navigation, and neither puts
data at risk.

## Verified
- **Java 8.** Everything used is available in Java 8:
  - `ProcessBuilder.Redirect.to(File)`, not the Java 9 `Redirect.DISCARD`;
  - a method reference in a field initializer;
  - `requests::add` used as a `Consumer<Boolean>`;
  - `IdentityHashMap`, `Executors.newSingleThreadExecutor(ThreadFactory)`.
- **Ownership transitions.**
  - `activate` returns early for the same field, so the same field can't send a second open
    request (the test covers this).
  - `deactivate` sends a close request only when a field was active, and only in Steam mode.
  - The dispatcher is added and removed exactly once, guarded by `dispatching`. Switching modes
    and the dialog's final `entry.deactivate()` (`:186`) both remove it.
  - Steam open and close requests go through a **single-thread executor**, so they reach
    `xdg-open` in order. When focus moves from label to account, the close for the label is
    queued before the open for the account.
- **Neutral re-arm.** Every activate or deactivate increments `revision`, and the timer then sets
  `armed=false` (`:266`). After Enter on the Steam keyboard moves focus to Create, the timer
  needs `buttonsHeld==0` before the next A. So the A that pressed Enter can't also click Create.
- **Focus.**
  - Focus going to another window (for example the Steam keyboard) has a `null` or foreign
    opposite component, so it doesn't deactivate the field.
  - Clicking the mode combo (inside the keyboard panel) doesn't deactivate either. The mode
    listener deactivates, switches mode, then refocuses and re-activates the earlier field.
- **Validation** is still the `DocumentFilter` (the test covers `bad-name`).
- **The Steam keyboard URI** matches SDL's X11 Steam Deck approach (`steam://open/keyboard?...`
  and `steam://close/keyboard`). The comment correctly says that a request isn't proof the
  keyboard appeared.
- **`deck-launch.sh` now runs the JDK 8 client directly** with `steamKeyboard=true`, so it no
  longer sources `config/local.env`. That also resolves my earlier finding about precedence
  (`CLAUDE_DECK_DESIGN_REVIEW.md` finding 4).
- **The patch covers** both source files and the new test.

## Findings

### M1. Medium: in Steam mode, moving onto a field traps the controller, and the label can't be reached again
Three things combine here:
- `focusGained` → `activate` (`LauncherKeyboard.java:62`) runs for **any** focus arrival,
  including the timer's own D-pad `transferFocus`;
- Steam mode then ignores all controller input until Enter or a focus change;
- each field's Enter advances forward only (label → account → Create).

So, using only the controller:
- From Create, D-pad up reaches the tutorial checkbox, then the account field. The account field
  takes the controller, and Enter returns to Create. **The label field can't be reached again.**
- B can't close the dialog while a field is active.
- If the user dismisses the Steam keyboard without pressing Enter, the only way out is
  Steam + X, then Enter.
- The mode combo and the "Open Steam keyboard" button can only be used with touch or the mouse.

**Physical trigger:** run `deck-launch.sh`, open New Character, press Enter on the Steam keyboard
twice to reach Create, then try to edit the label using only the controller.

**Smallest fix:** in Steam mode, don't take the controller on `focusGained` when the focus came
from controller navigation. Activate on **A** instead; the branch at `SoloScapeLauncher.java:271`
already does this. Keep auto-activation for the first field when the dialog opens. Optionally,
let LB/RB pass through while Steam owns the controller, so the user can leave the field.

### M2. Medium: the desktop D-pad still doubles up outside an active entry field
The user's report shows that Steam's desktop layout turns the D-pad into arrow keys. The new
dispatcher consumes them only when **SoloScape mode is active and the event targets the active
field** (`:88`). Everywhere else, both inputs still act:
- **The character list (main frame):**
  1. the timer moves the selection by one (`:278`);
  2. the arrow key reaches the focused `JList` and moves it again.

  One D-pad press can skip a row, so the wrong character is selected when A then calls **Play**.
- **A field after B has left the SoloScape keyboard:** the arrows move the caret again while the
  timer moves focus.
- If the desktop layout maps a face button to **Space**, a focused `JButton` also activates on
  Space while the timer's A calls `doClick()`. This depends on the mapping, which I didn't check.

**Fix:** while a controller is connected and the launcher window is active, install one
launcher-wide dispatcher that consumes the arrow, Space, Enter and Escape `KEY_PRESSED`,
`KEY_TYPED` and `KEY_RELEASED` events that come from the mapped controller. Alternatively, drop
the timer's own D-pad handling and let the desktop keys drive Swing. Physical keyboard users need
a way to opt out; the existing mode choice could be reused.

### L1. Low: SoloScape mode blocks physical-keyboard Backspace, Space and Enter in the field
While the SoloScape keyboard is active, a USB or Bluetooth keyboard (or the Steam keyboard
opened with Steam + X) can't delete or type spaces, even though spaces are valid for both
fields. This is acceptable because the mode is the user's choice, but the prompt should say so.
Steam + X in this mode also brings back double input: the Steam keyboard and the SDL grid both
act.

### L2. Low: Steam requests can block or start Steam
`process.waitFor()` has no timeout. If `xdg-open` blocks, for example because the `steam://`
handler starts the Steam client when Steam isn't running, later requests queue behind it, and a
close can arrive late. A failure is printed only to stderr, so the UI doesn't show it.

**Fix:** wait with a bounded `waitFor` (Java 8 `waitFor(long, TimeUnit)`). After the first
failure, set a status line suggesting Steam + X or SoloScape mode.

### L3. Low: test gaps
The tests cover the keyboard alone. These parts are not covered:
- the timer's suppress, return and re-arm path in `SoloScapeLauncher` (`:266-268`);
- focus-driven activation (the M1 trap);
- the ordering of open and close across a field change (the test calls the consumer
  synchronously).

A small launcher-level test with a fake `GamepadState` sequence on the EDT would catch M1 and
check that no A is duplicated after Enter.

## Limits
- Static only. I didn't check whether the patch content matches the working tree byte for byte,
  because that needs Git.
- Several points are inferred from your report and general SteamOS knowledge, not verified on
  the device:
  - what the Steam desktop layout maps;
  - whether SDL sees buttons pressed while the Steam keyboard is up;
  - whether the Steam keyboard steals X11 focus.
- No Deck hardware, Gaming Mode or ergonomics validation is claimed.

## Follow-up after the patch 0029 revision (static, read-only)
I re-read `LauncherKeyboard.java`, `SoloScapeLauncher.java` (`newCharacter` and
`startController`) and the new Steam-mode steps in `NativeLauncherProbe.java`. I ran no tests or
builds, used no Git, and make no hardware claim.

| Finding | Status | Evidence |
|---|---|---|
| M1: controller trapped in Steam mode | **Resolved** | `focusGained` now activates only in SoloScape mode (`LauncherKeyboard.java:63`). In Steam mode a field takes the controller only in these cases: (a) the explicit first activation of the label (`SoloScapeLauncher.java:187`); (b) A on a focused field (`:282`); (c) a mouse or touch release on the field (`:60`); (d) Enter on the label, which explicitly activates the account field (`:173`). D-pad traversal no longer takes the controller, so the label can be reached again. |
| M2: desktop D-pad doubled up | **Resolved on the Deck path** | A launcher-wide `KeyEventDispatcher` (`:262-271`) consumes the arrow, Enter, Space and Escape events (`PRESSED`/`RELEASED`, and `TYPED` `'\n'`/`' '`) in launcher windows. It does this only when all of these hold: `steamKeyboard=true`, a controller is connected, the checkbox is off, and the Steam keyboard doesn't currently own the field. It is removed on close (`:273`). The `JList` double step and the Space double click are covered. |
| L1: physical keyboard blocked | **Addressed by choice** | The visible "Desktop keyboard navigation" checkbox turns off both the timer and the dispatcher. |
| L2: request blocking | **Partly** | `waitFor(3, SECONDS)` (Java 8) bounds the wait. |
| L3: test gaps | **Partly** | The probe now drives Steam-mode exclusivity and Enter → account → finish through real Swing focus, with an injected visibility consumer. |

### Remaining notes (all low)
- **F1. The controller can switch itself off.** `nativeNavigation` is a focusable checkbox in the
  frame header (`:37, :64`). D-pad traversal can reach it, and the timer's A calls `doClick()`.
  Once it's ticked, the timer returns early, so the controller can't untick it. Recovery needs
  touch, the trackpad or a keyboard.

  **Fix:** call `nativeNavigation.setFocusable(false)`, so it can only be toggled by touch or
  the mouse. Alternatively, ignore A on that checkbox in the timer.
- **F2. Spaces from a manually opened Steam keyboard are dropped while the field is inactive.**
  On the Deck path, when a field has focus but isn't active (the user moved there with the
  D-pad), the launcher-wide dispatcher consumes Space and Enter. If the user then opens the Steam
  keyboard with Steam + X instead of pressing A, spaces are swallowed and Enter does nothing.

  **Fix:** treat the focused text field as excluded from the dispatcher, apart from the arrow
  keys. Or update the prompt to say "press A on a field to type".
- **F3. A timed-out Steam request isn't stopped.** The process isn't destroyed after the 3 s
  timeout, so a slow `open` can still finish after the later `close`, and the keyboard is left
  showing. Failures still go only to stderr. **Fix:** call `process.destroy()` on timeout, and
  show the hint in the dialog's `problem` label once.
- **F4. B still can't close the dialog while the Steam keyboard owns the field.** This applies
  only after an explicit activation now. The way out is Enter or a tap elsewhere, which matches
  the prompt text, so I'm not treating it as a defect.

Java 8 compatibility, ordered requests, re-arm on revision change and the active-window gating
are unchanged and still correct. Physical Deck behaviour, including what the desktop layout
actually maps and whether SDL sees buttons while the Steam keyboard is up, is **not validated**.

## Maintainer implementation after the follow-up

F1: the desktop-navigation checkbox is now non-focusable, requiring intentional pointer/touch selection rather than accidental controller activation. F2: native typing/Space/Enter in a registered Steam-mode field adopts system ownership before dispatch, including manually invoked Steam + X after traversal; mapped arrow-only navigation does not auto-open the field. F3: timeout now sends normal termination to the exact xdg-open request process, without killing Steam or a game. URI invocation still provides no reliable dismissal/visibility callback. These final small changes are maintainer-verified separately; they are not additional Claude hardware evidence.
