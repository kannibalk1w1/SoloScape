# Launcher input and Save & Quit — 13 October 2026

19 October follow-up: [dialog focus recovery](LAUNCHER_FOCUS_RECOVERY_20261019.md) covers Settings and character creation exits, missing component focus and nested dialogs. Host regression checks pass; Gaming Mode physical acceptance remains open.

The owner reported that neither launcher navigation nor A responded on the Deck. The launcher discarded Steam-mapped navigation keys as soon as SDL reported a connected controller, even if that controller supplied no usable button state. Client patch 0045 merges Steam navigation mappings with SDL before computing press/release edges. Enter/Space maps to A, Escape to B and arrows to the D-pad; native keyboard navigation and Steam text-entry ownership retain their existing modes. A mapped and SDL version of the same held button produces one action.

Right from the character list moves to the first enabled action button. Up/down still selects characters; the visible button rows support directional navigation and skip disabled actions. Up from the top row, left from Continue or B returns to the character list. Bumpers retain focus traversal.

## Exit from a controller

Open **Home → Settings**, use **LB/RB** to select **Finish**, then select **Save & Quit**. Press **A**, release it, and press **A** again to confirm; **B** cancels. Settings can also be opened through D-pad tab-bar focus.

Confirmed quit calls the normal client shutdown event without opening a mouse-only confirmation dialog. The launcher detects the client exit, stops its owned local server normally, verifies the save and makes a post-shutdown backup before returning to Continue. This action remains local and never sends a fabricated widget packet.

## Validation

- Client regressions: 245 cases; zero failures/errors, one optional SDL skip. New cases cover Steam-mapped input with neutral/disconnected SDL, duplicate mapped/SDL presses, focus clearing, text ownership, local quit tokens and second-press/cancellation guards.
- The actual Swing launcher probe uses AWT navigation events through the real dispatcher to move from the empty character list to its first enabled button and open New Character with mapped A. Existing controller name entry and exclusive Steam entry checks remain.
- Native `--save-quit` checks that the first quit press is blocked, the second calls shutdown, and the profile owner completes normal save/reload, four verified backups and startup cancellation with unchanged legacy mutable paths.
- Complete client patch reproduction covers 138 modified/patched files.

Hardware input acceptance still requires the owner to retry the installed launcher. The fix is tested with real Swing events and SDL state fixtures; those do not prove every Steam Input layout.
