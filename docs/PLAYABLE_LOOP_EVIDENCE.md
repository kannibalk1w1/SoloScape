# Controller-first playable loop evidence — 10 October 2026

Evidence is kept separate by what was exercised. Normal worlds, cache, public main and old Deck snapshots remain preserved. Native test worlds live only under private `.runtime/alpha-tests/session-*` roots. Raw logs, screenshots, saves, credentials and cache artwork are excluded from Git.

## Built client and source stack

208 client tests: zero failures/errors, one existing optional SDL skip. Matched Java 8 client and Java 21 server shadow jars/stamp pass. Ordered source stacks reproduce 106 client and 41 server files through client 0033/server 0013. Root launcher/profile/recovery/metrics tooling: 78 cases pass.

Regressions cover per-pane selection and refreshed quantity/actions, context action removal/reordering without stale dispatch or held-A fallback, external text child-to-parent-to-Home return, long text plus delayed panel repaint, fresh/hidden/replaced prompt cancellation, capability downgrade/reset and reversible cancellation preference, and idempotent opening of visible inventory. Existing equipment/source-return/quick-binding tests are included in the full client run.

## Real engine and content

- Network decoder: opcode 87 consumes exactly one byte and accepts native types 7–9 only.
- Engine: 11 latest ActionQueue cases pass, including logout cancelling unanswered integer/name/string entries without answers and draining a NonCancellable cleanup Continue installed during cancellation. Earlier selected world-cancel cases also passed in this sprint.
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

Final host/Deck native results and deployment identity are recorded in the combined morning report once the batch is complete.
