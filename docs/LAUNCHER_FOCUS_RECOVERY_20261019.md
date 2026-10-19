# Launcher dialog focus recovery — 19 October 2026

[Player report](https://www.reddit.com/r/SteamdeckGames/comments/1x55ui1/comment/phoasif/?context=1): in Steam Deck Gaming Mode, closing Launcher Settings or character creation removes the selection highlight and stops controller navigation. Mouse input still works; restarting restores navigation. The player uses `_JAVA_AWT_WM_NONREPARENTING=1` for the Gaming Mode white screen.

Client patch **0059** gives all owned launcher dialogs a shared return-focus lifecycle. Opening records the parent's current control; disposal restores it, or an enabled default if the original control is unavailable. This covers OK, Cancel, B, title-bar close and asynchronous successful character creation. Nested dialogs return to their immediate parent. The launcher also repairs a missing component focus in its active window, then waits for neutral input before accepting a fresh press. Another application's active window, a running game or a newer modal dialog prevents focus restoration. The listener is removed on launcher shutdown.

Previously only the controller B branch explicitly restored parent focus. Other exits depended entirely on the window manager, and the timer could remain unable to navigate with a null focus owner. The Deck source launch script already exports the player's AWT workaround; this change retains it. Host checks cannot establish whether that variable causes the Gaming Mode failure.

## Validation

- Client shadow jar builds successfully with JDK 21 and the JDK 8 client toolchain.
- `CLIENT_JAVA="$PWD/.runtime/jdks/jdk8/bin/java" _JAVA_AWT_WM_NONREPARENTING=1 python3 scripts/smoke-launcher.py --focus` passes using real Swing windows, the real backend and Steam-mapped key events on private Xvfb. It checks Settings OK/Cancel/title-bar/B, character cancel/successful creation, deliberately cleared component focus, resumed navigation and an unrelated-window focus guard. Private run: `.runtime/launcher-tests/1792410758018126620`.
- The existing `--updates` probe passes with the same AWT variable, including nested B ancestry and cancellation while an update check is pending. Private run: `.runtime/launcher-tests/1792410699763627656`.
- The original launcher, compiled into a disposable classpath before the rebuilt jar, fails the new probe at Settings focus restoration. The patched launcher passes that same probe.
- The existing character-entry probe also passes with the AWT variable: held-A guard, controller typing, account filtering, B preserving the form, Y advancing, backend rejection and exclusive Steam keyboard ownership. Private run: `.runtime/launcher-tests/1792410809044876432`.
- Both client and server source trees reproduce their exported patch stacks.
- Root tooling suite: 315 tests pass, one optional skip. The initial sandbox run denied two loopback-socket tests; the complete suite passes outside that restriction.

These are host regressions, not Steam Input hardware or Gamescope acceptance. The changed client has not been packaged, published or deployed to the player's Deck. Physical acceptance: in Gaming Mode, repeatedly open and close Settings and New Character using each available exit, including completing creation; release input between transitions and verify that the highlight returns and D-pad/A/B continue working. Repeat a nested update check and switching away to another app.

## v0.51 release integration

The fix is rebased onto the v0.5 installer/updater baseline (`b06c387`), exported as patch 0059 after managed updater patches 0057–0058, and prepared for v0.51. Both patch stacks reproduce, the complete matched source build succeeds, and all 523 tooling/installer tests pass (one optional skip). The real Swing focus probe and the current managed update-dialog probe both pass again with `_JAVA_AWT_WM_NONREPARENTING=1` on this combined source (`.runtime/launcher-tests/1792411047090938440` and `1792411045377006146`). Earlier counts and publication statements above describe the initial pre-release validation. v0.51 follows the existing installer-only distribution: the installer pins the final merged source commit and builds on the player's machine; physical Gaming Mode acceptance remains open.

## Other thread feedback

The wider thread asks about L-shaped movement, launcher updates, other handhelds and 2009scape/Android compatibility. Corner movement is already implemented with physical acceptance pending in [corner movement](CONTROLLER_CORNER_MOVEMENT.md). Release discovery is implemented; production download/apply/rollback remains tracked in [launcher updates](GITHUB_UPDATES.md). The current source uses desktop Java/AWT and SDL; a Deck preset does not establish Android or 2009scape compatibility. These compatibility requests need a separate port rather than an unverified installation claim. General content-completeness questions are bounded by [content coverage](CONTENT_COVERAGE.md). This fix addresses the concrete launcher failure in the linked comment.
