# Real Steam Deck checkpoint — 10 October 2026

The owner authorized SSH deployment and real-device tests. SteamOS and Steam configuration were preserved. Private test profiles, assets, JDKs, jars and raw evidence stay outside Git. The ordinary **SoloScape Test** launcher is installed and open in Desktop Mode; its normal character list was initially empty. The owner subsequently tested name entry and reported the keyboard conflict described below.

## Device and deployment

Steam Deck DMI `Jupiter`, AMD Custom APU 0405, eight logical CPUs, about 14 GiB usable RAM reported, SteamOS 3.8.28 (build 20260922.1). KDE Wayland Desktop/XWayland display is 1280×800. The final game's native interface and canvas both measured **892×529**; this is a windowed software-renderer test, not full-screen Gaming Mode.

The tested snapshot is `~/SoloScape-test/builds/deck-sprint-20261010-r6`, with source commit `f65584fc9f6a39421d680d57a4c38cf9241bf7be`. Its **10,358 listed files** match the private manifest, including after native sessions. Manifest SHA-256: `d56c294addea28628600335d8a302b7a4b1560cea9c4de4547dfeba8395dbd5b`. This checks transfer corruption against the host-recorded manifest, not a signed release. Mutable Git index stat data is intentionally excluded.

Doctor reports zero errors with project-local Java 21/8. Both source stacks reproduce on the Deck: **99 client and 33 server files**. Matched jars/patch stamp verify. The private owner-transferred runtime avoids system package installs, SteamOS unlocks, forced Proton and copying production saves. [Setup/update guide](DECK_SETUP.md).

## Passing automated evidence

- **78 root tests** pass on both the development machine and SteamOS/Python 3.13. This includes staged/unstaged private-blob exclusion, snapshot corruption/path/link/config refusal, identity-bounded metrics and existing lifecycle/recovery coverage.
- Actual Swing launcher entry/backend passes on the Deck: held-A neutral guard, account filter, form-preserving B/Y and backend errors. A live SDL timer race in the synthetic held-A assertion was repaired inside one EDT callback; no production input change was needed.
- Real SDL2 **2.32.56** detects **Steam Deck Controller**, connected in **100/100** five-second samples. No buttons were pressed; maximum resting stick reading was **0.0682**. This is hardware detection/polling, not physical action mapping or comfort acceptance.
- Native New/Continue/adventure passes on the real Desktop: ordinary login, native tabs/journal, real settings Gateway adoption over ticks, setting change/reversal, B-to-Home, logout/relogin and fresh session capabilities. Exact saved account/XP/inventories/tile fields survive; four completed-session backups verify. Cancelled pre-ready startup preserves every saved-world file and original server mutable-path size/mtime fingerprints.
- Desktop mouse steps use **synthetic AWT events through native canvas listeners**, not fabricated logout packets or OS pointer acceptance. Active interface/fresh label/bounds/scale checks apply. Exit/logout must not move the player, and both sessions observed **zero non-probe mouse clicks** during those steps. The client plugin's complete physical SDL input path is not established by these UI probes.
- Real ordinary-jar **client and server** survive their deliberately killed disposable Python parent, retain inherited guards and pass pidfd ownership checks. Recovery stops the client before the server and validates an `after-recovered-shutdown` snapshot while retaining `before-launch`. Clean shutdown is unconfirmed. This proves native JVM lifecycle, without a player-readiness claim for that recovery run. The client uses its private profile home/cache; the fingerprint comparison covers original server mutable paths, not all user-home state.
- Final local private-Xvfb/Robot adventure smoke also passes New/Continue/save/cancel after the harness changes. All four Java 8 harnesses compile; Python compilation, ShellCheck and whitespace checks pass. Production jars/patches are unchanged from the journeys build; **176 client cases** (one optional SDL skip) and **20 selected game cases** remain its retained baseline, not freshly rerun suites in this Deck batch.

Private evidence: final Deck `.runtime/alpha-tests/session-1791636076775423908/native-smoke-summary.json`; real two-JVM recovery in the retained r4 snapshot `.runtime/recovery-tests/1791635596589973945/summary.json`; launcher entry/backend in r2 `.runtime/launcher-tests/1791634494945471878`. The normal installed launcher also detects SDL and opens its Local Worlds window. Test characters live in separate probe roots.

## Measurements

Native overlay-render callbacks, approximately ten seconds of native scene and five seconds of custom journal per session. These are measured callback intervals, not GPU presentation timing, sustained gameplay FPS or input latency.

| Observation | New | Continue |
| --- | ---: | ---: |
| Native interval samples | 402 | 426 |
| Native median / p95, ms | 23.92 / 29.80 | 23.27 / 24.80 |
| Journal interval samples | 153 | 161 |
| Journal median / p95, ms | 31.91 / 37.73 | 30.53 / 33.48 |
| Complete session, seconds | 67.706 | 66.348 |
| Peak server RSS, MiB | 1552.18 | 1469.13 |
| Peak client RSS, MiB | 1460.93 | 1164.69 |
| Peak simultaneous RSS sum, MiB | 3013.02 | 2599.55 |
| Mean server CPU, 100% = one core | 63.65% | 56.33% |
| Mean client CPU, 100% = one core | 154.72% | 149.29% |
| Passive resource samples | 131 | 128 |

Resource samples cover startup/login/UI/save, not steady-state idle. PID/start checks prevent reuse contamination; the RSS sum double-counts shared pages and is not unique physical memory. Lifecycle phase timestamps are retained. No samples were truncated and both sampler workers exited. Host-wide amdgpu sensor peaks were 54/55°C and acpitz peaks 57/59°C. Battery status included both Charging and Discharging; no battery-life estimate follows. Other running desktop applications, charging behavior, CPU/GPU policy and window size were not controlled into a release benchmark.

The journal's added rendering cost is a candidate for measured optimization after Gaming Mode acceptance. These short measurements do not set a sustained thermal/frame-time budget.

## Failures retained and corrected

The first Desktop launcher held-A assertion ran after the real timer had already neutral-rearmed the keyboard. Activation and assertion now happen atomically on the EDT.

Robot global-pointer clicks on KDE Wayland initially failed logout, and later triggered movement immediately after Exit while logout/relogin itself passed. Strict tile/save comparison correctly rejected those runs. Per-stage tile traces exposed it. The Desktop harness now uses native canvas AWT listeners, requires unchanged tile around logout and verifies native/canvas dimensions. Failed r2/r3/r4 adventure runs remain private diagnostic evidence and are not passed checkpoints. No production movement, collision or content rule was changed to make this test pass.

Java Robot's window-region screenshots were mostly black despite visible rendering. A KDE Spectacle capture, taken only after checking that the active window was the game, showed the live native scene and custom journal. That inspected image contains only the test game window; raw screenshots are otherwise private because overlays/notifications can obscure a window.

## Independent review and remaining gates

Actual Claude completed a [design review](CLAUDE_DECK_DESIGN_REVIEW.md) and [bounded follow-up](CLAUDE_DECK_FOLLOWUP.md). Pin-reachable Git packing, index hash exclusion, parent/cache link refusal, config isolation, phase/identity/charging metric scope and native probe cleanup were addressed. Static review did not run the Deck or certify hardware acceptance.

Physical buttons/sticks/trackpads, launcher/game SDL coexistence, first-run discovery, sustained quest/combat play, completed journal rendering, Gaming Mode/window routing/Steam Input, OpenGL, battery/thermal/clock limits, reconnect and suspend/resume remain owner acceptance. No Steam Verified rating, packaged release or universal fresh-machine support is claimed. See [physical checklist](STEAM_DECK_TEST_CHECKLIST.md) and [approved tasks](DECK_SPRINT_TASKS.md).

## Owner-reported launcher keyboard correction

The first physical name-entry feedback exposed concurrent Steam keyboard and SoloScape SDL actions, plus desktop-mapped D-pad arrows moving the caret. Earlier synthetic adapter passes did not establish exclusive Steam keyboard ownership. Client patch 0029 introduces an explicit Steam/physical versus SoloScape keyboard choice. Deck launch defaults to Steam mode, requests its keyboard automatically for the first field, ignores launcher SDL while entry owns input, and requires neutral rearming afterwards. Enter advances/finishes; A or tapping a field reopens it. Merely navigating onto another field does not take over the controller.

Local fallback consumes mapped navigation keys; Deck launcher navigation also suppresses mapped arrows/confirm keys outside system-owned entry. A visible desktop-keyboard navigation option disables launcher SDL so native keyboard navigation can be selected exclusively. Steam invocation uses the URI transport in [SDL's upstream X11 implementation](https://discourse.libsdl.org/t/sdl-x11-add-support-for-the-steam-deck-on-screen-keyboard/39748), with a bounded request wait. URI requests do not prove visibility or provide a dismissal callback; Steam + X and the explicit fallback remain available.

Fresh client test/shadow build: **179 cases**, zero failures/errors, one existing optional SDL skip. Exact patch reproduction: **100 client / 33 server files**. The real Swing smoke exercises both local controller entry and system-mode text/SDL isolation, focus/Enter advance and ordered injected visibility requests. Actual Claude reviewed the fix and identified controller traversal and duplicate desktop navigation; these were addressed in the follow-up implementation. See [keyboard review](CLAUDE_DECK_KEYBOARD_REVIEW.md). The earlier r6 gameplay measurements remain the baseline; this launcher correction does not establish a new performance measurement or physical keyboard acceptance.

The owner explicitly requested the same ownership policy for **all in-game text entry**. That extension is now implemented for recognized prompts plus a manual native text path; remaining every-widget recognition/physical acceptance is recorded below.

Deployment of the launcher correction: verified private snapshot `~/SoloScape-test/builds/deck-sprint-20261010-r7`, source commit `8ccad023874777492a557ead1e758e61ea9e6e97`, **10,364 listed files**, manifest SHA-256 `a79b829675c5871da5806464c4fbeac20bc8770b0ebbda3d4e4657bea2913c96`. Deck doctor reports zero errors; 100/33 patch files match; fresh real Swing local/system-mode focus/Enter/backend probe passes with real SDL detection. Private probe evidence: `.runtime/launcher-tests/1791637534905529695`. After the owner confirmed launcher/game closed, the update checked for surviving old JVM/backend processes, outstanding session records and profile-copy equality before switching the shortcut. The old normal profile store was absent, so no user characters were copied or removed; all old snapshots/test fixtures remain. The shortcut now selects r7. Physical Steam keyboard visibility/action mapping remains owner acceptance.


## In-game text and classic UI deployment — r8

Verified private snapshot `~/SoloScape-test/builds/deck-sprint-20261010-r8`, source `0588ad6ec2e357859ba49551f8303408298b0195`: **10,380 listed files**, manifest SHA-256 `dd8ba770db3405f72c2e20c26714276e44c062e7602c6a3a76164eba80a489be`. Manifest was checked before tests and again before shortcut update. Doctor: zero errors. Exact 106-client/33-server source stacks and matched archives pass.

Actual Deck Desktop New/Continue full adventure/settings/text/save probe passes at `.runtime/alpha-tests/session-1791640040571556491`: native tabs/journal, Gateway settings adoption, keyboard/style/deadzone reversal and B-to-Home; CS2 types 7/8/9 edit/cancel; native received public-chat type 2 after Enter; Escape without submission and retained-text cleanup; unchanged tile throughout text and Exit; native logout/relog/fresh capabilities, exact save fields, four backups, original mutable fingerprints and whole-world early cancellation. Both sessions observe zero non-probe mouse clicks during native Exit/logout. Totals 89.245/88.077 seconds include the whole probe lifecycle and fixed waits, not launch-time or physical-performance targets.

Steam visibility is injected in text fixtures; controller is really detected/polled, but actions are synthetic/native adapter calls. Type-11 real-bank cancellation, real server Withdraw-X/cancel/logout and every native textbox are not proved. Native Cancel uses pinned close_entry 101 because the real cache's script112 Escape branch leaves ordinary types7/8/9 open; the server keeps its ordinary pending-action lifecycle. [Keyboard scope](IN_GAME_TEXT_INPUT.md).

Wayland/Robot journal/settings captures are black. They do not support a Deck visual-acceptance claim. The code renderer's classic/modern synthetic previews pass and are the published artwork-free fixtures. Physical Steam + X visibility, simultaneous SDL/AWT delivery, Gaming Mode and panel readability remain owner acceptance.

After the owner confirmed closed/awake, the r7/r8 archive guards and process/session records were checked; normal r7 profiles remained absent. The ordinary shortcut atomically switched to r8. All older snapshots and private test worlds remain; no Steam configuration, system Java or existing server-cache edits were made. SoloScape is left closed after the test batch.

The real Swing local/system-mode entry/backend probe also passes on r8 Desktop, with real built-in SDL detection, at `.runtime/launcher-tests/1791640279456729216`. Steam visibility remains injected.
