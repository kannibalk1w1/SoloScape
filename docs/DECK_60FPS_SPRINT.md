# Deck 60 FPS sprint

Approved 12 October 2026 following owner feedback: sustained 60 FPS is the target. This sprint takes priority over broader content expansion. Implementation and diagnostics are underway; the target is not yet achieved. Current evidence is in [the performance report](DECK_60FPS_REPORT.md).

## Target and acceptance

Use 1280×800 in Gaming Mode as the initial target, with controller support and the normal gameplay UI enabled. Record actual canvas and internal render resolution; windowed Desktop results are diagnostic comparisons, not acceptance. Any reduction in internal resolution, detail or draw distance must be visible in the selected preset and reported with results.

Aim for a capped, consistently paced 60 FPS: a 16.67 ms frame budget, no sustained periods below 58 FPS during ordinary gameplay, and a proposed p99 frame-time ceiling of 20 ms after warm-up. Record loading/region-transition stalls separately without hiding them from the full trace. The p99 tolerance is a proposed practical acceptance allowance, not a claim that every frame meets 16.67 ms.

Acceptance requires a reproducible 30-minute route after warm-up, repeated on battery and external power at recorded power/refresh settings. Track frame-time distribution, CPU/GPU utilisation, temperatures, memory/GC, server tick timing and battery drain. Preserve server timing, gameplay speed, input reliability and saved progress. Include movement, camera turns, inventory, dialogue, combat, bank/shop and map open/close.

## Baseline evidence

Owner reports roughly 20–30 FPS on Deck. Short 892×529 Desktop native comparisons measured approximately 35–37 FPS with controller support and 42–43 without; the early target-acquisition optimisation did not demonstrate an improvement in that stationary scene. The samples were sequential, so repeat with alternating A/B/A order to distinguish controller overhead from warm-up or changing clock rates.

The vanilla render loop draws once per 50 Hz client cycle. Existing `DetachedRenderer` supports independently paced frames on the same client thread while keeping logic at 50 Hz. Its Experimental renderer plugin is disabled by default; a configured FPS target alone does not establish that it is active. Measure actual pacing state and toolkit on each run before attributing a ceiling to hardware. The observed toolkit class was `oa`; do not label that as a GPU or Java software backend without verifying its actual path.

## Work sequence

- [ ] D60-01 Record the installed build, renderer/toolkit, active pacing state, native settings, resolution, refresh rate, power configuration and connected-controller state. Verify the FPS measurement against presented-frame timing.
- [ ] D60-02 Reproduce a fixed Lumbridge → castle/stairs → mill → bank/shop → combat route in a disposable world; include standing idle, continuous walking, camera turning and UI interactions. Capture warm-up and 30-minute frame traces.
- [ ] D60-03 Check normal versus independently paced rendering at a 60 FPS target. Confirm 50 Hz client logic and unchanged server/gameplay timing; check animation/input cadence and resize/reconnect behaviour.
- [ ] D60-04 Profile client logic, controller polling, target/reachability searches, widget snapshots, overlay drawing, native rendering/presentation, GC and server work separately. Compare controller enabled/disabled and overlays individually in alternating order. Explain where the 16.67 ms budget is exceeded.
- [x] D60-05 Fix the largest measured costs in small reversible patches. Avoid premature renderer/threading rewrites. Recheck the same route and frame-time tails after each change; retain fixes supported by evidence or independent correctness improvements.
- [x] D60-06 Compare supported renderer paths and measured quality settings if necessary. Deliver a clearly labelled Deck 60 FPS preset, visible pacing/FPS controls and a diagnostic report. Use internal resolution scaling only if needed and document the resulting resolution/readability tradeoff.
- [ ] D60-07 Repeat sustained Gaming Mode runs on battery/external power, plus suspend/resume and save/reload. Verify controller playtest fixes on hardware. Package a matched candidate and report passes/failures against the target before changing the installed shortcut.

## Deliverables and boundaries

Deliver a reproducible benchmark route, reusable frame/CPU/GPU/tick traces, measured performance fixes, a tested Deck preset and a short before/after report including stalls and quality tradeoffs. If 60 FPS remains unattainable on a supported path, report the limiting subsystem and next required change; a lower cap does not satisfy the sprint goal.

Keep this sprint focused on performance and validating the current playtest fixes. Automatic cross-device save syncing and richer controller map navigation follow once the everyday Deck session is stable. Manual verified save transfers remain available during testing.
