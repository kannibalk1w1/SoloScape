# Controller-first playable loop evidence — 10 October 2026

Evidence is kept separate by what was exercised. Normal worlds, cache, public main and old Deck snapshots remain preserved. Native test worlds live only under private `.runtime/alpha-tests/session-*` roots. Raw logs, screenshots, saves, credentials and cache artwork are excluded from Git.

## Built client and source stack

211 client tests: zero failures/errors, one existing optional SDL skip. Matched Java 8 client and Java 21 server shadow jars/stamp pass. Ordered source stacks reproduce 106 client and 43 server files through client 0035/server 0014. Root launcher/profile/recovery/metrics tooling: 78 cases pass.

Regressions cover per-pane selection and refreshed quantity/actions, context action removal/reordering without stale dispatch or held-A fallback, external text child-to-parent-to-Home return, long text plus delayed panel repaint, fresh/hidden/replaced prompt cancellation, capability downgrade/reset and reversible cancellation preference, and idempotent opening of visible inventory. Existing equipment/source-return/quick-binding tests are included in the full client run.

## Real engine and content

- Network decoder: opcode 87 consumes exactly one byte and accepts native types 7–9 only.
- Engine: 12 selected engine cases pass (11 ActionQueue and one ScriptCancellation), including logout cancelling unanswered integer/name/string entries without answers and draining a NonCancellable cleanup Continue installed during cancellation. Normal Script cancellation now propagates without a false error log; its regression verifies cleanup and cancelled/completed Job state. Earlier selected world-cancel cases also passed in this sprint.
- Game: 24 selected Bank/content.soloscape cases pass. The Withdraw-X regression checks a mismatched cancellation leaves the pending amount untouched, correct cancellation clears it, bank/side panes and quantities remain, and a normal withdrawal then logout works.
- Selected actual server routes include Lumbridge travel, earned gathering/production/equipment/combat/food/save reload, Cook's Assistant and Rune Mysteries completion/reload, and the Restless Ghost/actual castle floors. Server-route tests do not establish controller comfort or native client quest completion.

## Native harness scope

`python3 scripts/smoke_profile.py --journey` includes the earlier adventure/settings/text stages and the gameplay round trip. `--journey --text` skips tab/render measurements and runs the focused text plus gameplay/logout/relog/save checks. `--desktop` uses only the explicitly authorized existing display; the default owns a private Xvfb display.

The gameplay probe reads actual scene candidates and native widgets, uses ordinary controller Walk/Use/Wield/Remove/door/stair/banker/bank operations, and uses loaded native collision masks to route around scenery. It reuses the ordinary starter pot if present; otherwise it can take the actual kitchen spawn. It must return the item and player to their original inventory slot/tile so New and Continue can compare actual save fields.

Disposable journey servers explicitly opt into the read-only `soloscape_probe_entry <nonce>` diagnostic using `SOLOSCAPE_NATIVE_PROBE=1`. The normal launcher does not set it. The command answers only pending-entry class, cannot mutate a world, and answers nothing without the flag. The journey requires a fresh `int` reply before native Withdraw-X Cancel and `none` afterward, then checks bank/items, real search edit/cancel/toggle, normal withdrawal and return. This avoids mistaking a local prompt close for server cancellation.

Early probes improved the harness's scene navigation and null-slot handling and exposed the genuine native resized-frame inventory re-click/collapse defect. Client 0032 fixes the open request. The actual staircase candidate was also present but rejected by the wall-anchor reach guard; client 0033 uses the native object-rectangle check, retaining dimensions, access faces and collision walls. Native source/use cancellation and sword wield/remove were observed before that earlier run failed; full journey evidence must be recorded separately from partial observations.

## Hardware and acceptance limits

The real Deck SDL provider initialized and detected its Steam Deck Controller for all 100 passive samples. No buttons were pressed; maximum observed stick magnitude was 0.0431. Detection is not physical mapping or gameplay acceptance. Twenty synthetic classic/modern previews rendered; representative inventory, journal and Home layouts were visually inspected and public cache-free fixture pictures refreshed.

Gaming Mode, physical Steam keyboard visibility, simultaneous physical button/key delivery, touch hit accuracy, arm's-length readability, OpenGL/GPU presentation timing, sustained input latency, battery life and suspend/resume remain unclaimed. Native software callback measurements and own-process RSS/CPU/sysfs samples are bounded observations, not performance targets or per-game GPU/power attribution.

Final host/Deck native results and deployment identity are recorded in the combined morning report and Deck validation log.

## Native Search correction

Loaded cache script 1472 installs Search onOp 1471; native Class348_Sub9 dispatch executes it synchronously. The old adapter registered its fallback after dispatch and called the toggle again after a delayed server re-arm, closing the newly opened search prompt. Client 0034 registers before dispatch; observing 1471 consumes the request and revises prompt identity. Opening and closing delayed-rearm regressions pass. The fallback remains only for a native click that did not execute the script; it never runs just because the server later re-arms Search. Claude reviewed the concrete ordering fix read-only and found no blockers.

Client 0035 also invokes bank-filter script 1475 after local text script 1564 only for the same fresh type-11 session/value. Actual native key script 112 does this refresh; direct text replacement did not. Two regressions cover normal filtering dispatch and replacement suppression. The bank-only diagnostic passed cancellation, matching-item/coin exclusion, Search-off restoration, button re-arm, normal withdrawal, close and logout/relog. It is separate from full-route/New/Continue results.

## Complete host New/Continue

Private Xvfb/software run `.runtime/alpha-tests/session-1791645357090009172` passes both complete routes. Whole-session totals: 270.231 / 265.419 seconds, including readiness, fixed probe waits, native logout/relog and save. Actual gameplay round trips: 210.121 / 207.108 seconds, 78 native walk dispatches each. Both observed pending int → none, pot search excluding coins, Search-off restoration, ordinary withdrawal, both castle floors and exact origin return. Cache filter argument counts are both zero. Exact account name/experience/inventories/tile compare, four verified backups, original mutable fingerprints and early-startup whole-saved-world preservation pass. These route totals are not latency or FPS targets.

## Complete actual Deck New/Continue

Desktop/software run `.runtime/alpha-tests/session-1791645380914144829` inside private r9 passes both complete adventure/settings/text/gameplay/save routes. Whole-session totals 295.515 / 296.860 seconds; gameplay 204.103 / 207.097 seconds, 78 native walk dispatches each. Both confirm zero-argument filter header, int → none cancellation, matching pot/coin exclusion, Search-off contents restored and ordinary withdrawal. Exact account name/experience/inventories/tile, four verified backups, original mutable fingerprints and cancelled-startup whole-world preservation pass. Keyboard/style/deadzone preferences reverse, Settings Gateway and B-to-Home, native text/chat and native logout/relog are included.

Bounded callback intervals: baseline median 24.30 / 22.89 ms (417 / 431 samples), journal 29.18 / 28.02 ms (184 / 193 samples). Whole-session peak simultaneous JVM RSS sums 8840.24 / 8943.36 MiB; client peaks 7298.41 / 7718.86 MiB, server 1542.93 / 1225.14 MiB. One-core-100 CPU means client 119.63 / 117.42%, server 23.88 / 19.06%. Resource workers ended; no samples truncated. Longer-session memory behavior requires further measurement; host-wide sensors/Not charging status do not establish per-game power or battery life.

r9 is selected by the Desktop launcher and a Steam non-Steam entry named SoloScape using the stable launcher. The Steam-launched r9 launcher/backend/window were observed and closed normally without starting a normal world. Steam keyboard visibility/Gaming Mode/physical controller acceptance remain unclaimed.
