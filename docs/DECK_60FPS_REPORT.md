# Deck 60 FPS investigation — in progress

The target is sustained 60 FPS at a real 1280×800 canvas in Gaming Mode. The installed player shortcut remains r10. All measurements below use disposable worlds; Desktop fullscreen results do not complete Gaming Mode/battery/physical-controller acceptance.

## Findings and implemented candidate

- The normal client renderer draws once per 50 Hz client cycle. The existing independent frame pacer is off by default. A requested cap of 180 alone does not enable it.
- The installed native `oa` toolkit uses `sw3d`, a CPU/software renderer. At a verified 1280×800 canvas, it reproduced approximately 28–29 FPS, with about 32 ms spent in rendering. Controller/plugin work contributed roughly 0.5–0.7 ms per frame rather than explaining most of the cost.
- The pacer calculated its post-render sleep from the pre-render clock reading. It now uses the current clock after rendering/plugins/event work, so already-spent frame time is not added again as sleep. Client/server simulation timing is unchanged.
- Capped frame waits now preserve nanosecond deadlines and immediately process overdue work, avoiding whole-millisecond rounding and a mandatory extra millisecond. Uncapped mode retains its yield; the client logic schedule is unchanged. Clock-controlled regression cases cover fractional waits, due logic and overruns. Hardware comparison is pending.
- The overlay bridge created a new full-canvas GPU texture every frame. OpenGL now reuses and updates one texture and one CPU upload buffer, with explicit release on renderer/size changes. Pixel tests cover row orientation, colours, partial alpha, and clearing old contents.
- Home > Settings > Basics now offers **Deck 60 FPS target**: OpenGL, full native viewport, a 60 FPS cap and visible native FPS readout, with animated scenery shadows disabled. Turning it off restores the graphics captured before enabling it in that session. The setting persists per profile; Draw distance and resolution are preserved; the shadow tradeoff is stated in the setting and status. Unsupported OpenGL restores the previous renderer and reports failure instead of retrying every tick.
- Opt-in phase timers (`-Dsoloscape.performance.timings=true`) record bounded client logic/plugin/overlay/render/presentation samples. Disabled production runs allocate no sample buffers. The native benchmark checks actual canvas dimensions and records real toolkit/vendor/pacing/controller/focus state.

## Short Desktop results

Two successful full-resolution r2 repeats, controller connected and canvas focused:

| Measurement | New | Continue |
| --- | ---: | ---: |
| OpenGL capped average FPS | 59.85 | 59.89 |
| Median frame interval | 16.82 ms | 16.76 ms |
| p99 frame interval | 21.10 ms | 20.84 ms |
| GL texture memory | 13.23 MB | 13.24 MB |
| Average rendering including overlays | 12.32 ms | 12.09 ms |
| Average overlay upload | 1.39 ms | 1.43 ms |

The cap-off comparison was still about 60 FPS under the Desktop compositor. Native logic samples remained approximately 50 cycles/second. Preset restoration, New/Continue save fields, four backups and whole-world startup cancellation passed.

These short intervals narrowly exceed the proposed 20 ms p99 allowance. Earlier fullscreen attempts also encountered intermittent roughly one-second rendering stalls; they remain a tracked issue until reproduced/localised and cleared by sustained runs. Reusable texture memory was stable in the successful runs; that does not by itself prove the cause of those intermittent stalls.

## Sustained-route investigation

The native route has passed castle/stairs and bank/shop navigation. The shop uses its east entrance; blocked direct targets and staircase cooldowns were fixture errors and were corrected without changing game collisions. Mill/dialogue, combat and the return/inventory/map segment have also been exercised. The return follows the eastern road used by the server adventure test. These diagnostic segments are not yet a single 30-minute acceptance route.

Movement toward the farm/mill produced recent five-second frame rates around 52–56 FPS with animated object shadows. A bounded Java Flight Recorder CPU/GC capture on the owned disposable client found native scene/shadow work prominent (`Class22.method295`, `Class169.method1301`, `Class235.method1668`); full-scene ground-item reads also appeared. One observed GPU utilisation reading was 24%; this is a host-wide sample, not proof of every frame's bottleneck. Both reported APU power caps were 12 W. Power settings have not been changed.

The labelled static-object-shadow comparison reached the mill/dialogue at 1280×800, with recent rates around 59.5–60 FPS through that segment. The candidate preset now caps native scenery shadows at static (preserving an existing disabled setting), and captures/restores the prior shadow setting when toggled off. This is a quality tradeoff: animated scenery silhouettes no longer update continuously. Long-run acceptance remains pending. Ground-item readers now share a snapshot between native logic updates, avoiding repeated scene scans and definition lookups; each caller still owns its list, and quantity/despawn/region changes invalidate the snapshot.

Tooling now preserves failed route traces, computes rolling five-second FPS alongside p99 and keeps loading frames. Server tick/stage profiling is opt-in, bounded, writes on normal loop shutdown, and leaves the 600 ms tick schedule unchanged. The separate Gaming Mode benchmark launcher uses disposable worlds and optional independent OpenGL frame logs via [MangoHud](https://github.com/flightlessmango/MangoHud); logs stay private and uploading is disabled. Desktop logs provide an independent frame measurement. Gaming Mode logs have not yet been validated after the native loading fix; overlay callback timing alone is not presentation evidence.

Latest checks: 226 client cases (one optional SDL skip), 95 root tooling cases, and 13 selected server movement/game-loop/timing cases (three pre-existing skips) pass. Host native New/Continue map/logout/text/save checks pass again, including four backups and startup cancellation. The corrected disposable Deck return/inventory/map segment also passes save/reload and startup cancellation. Client/server patch stacks reproduce the complete modified source, and matched jars build successfully. Hardware acceptance remains pending.

The 400-second static-shadow diagnostic averaged 59.36 FPS with p99 23.47 ms. Native rendering including overlays averaged 10.83 ms/frame, and presentation p99 was 5.54 ms, maximum 14.23 ms. Client logic contained a 716 ms outlier. A separate corrected return/UI diagnostic averaged 57.33 FPS over 132 seconds and included a 1.42-second first-map-loading frame. Both remain diagnostic results, and neither meets the full-trace sprint target. All loading/UI frames are retained rather than silently excluded.

## Gaming Mode startup regression

The first Steam-launched r6 benchmark crashed during native OpenGL initialisation. The faulting instruction was a write to the bridge's `glGenBuffersARB` function-pointer slot, resolved instead to executable memory in `libGL.so` preloaded by Steam's overlay. The owned disposable server still completed normal save/shutdown.

Candidate r7 loads the Linux `jaggl` library with `RTLD_NOW | RTLD_DEEPBIND` before JNI registration, retaining that handle. A subprocess regression fixture proves ordinary loading preempts the data slot and the protected loading updates its own slot without faulting. Native binaries and Steam settings are untouched. The real Steam-launched r7 passes OpenGL startup and begins the full route; its first minute through bank/stairs records about 60 FPS. Native loading may change interposition by GL instrumentation/overlay libraries, so independent Gaming Mode presentation and overlay/keyboard behaviour remain explicit acceptance checks.

The r7 Gaming Mode route subsequently stopped at the farm-road waypoint, outside its loaded scene. This was a fixture navigation timeout, not another native crash; the owned server saved normally. The route-only navigator now approaches distant waypoints through reachable native collision tiles so ordinary movement can reload the scene. A fork of that stopped disposable world has crossed the boundary and reached the farm at around 60 FPS. Automated camera input is now applied after controller processing on every client tick, with camera yaw recorded. Combat requires earned combat XP rather than only an accepted attack dispatch. The player reported that the physical right-stick camera check turned correctly and remained near 60 FPS; this is a limited physical input check, not long-run acceptance.

A passive, separate [XCB Present Complete](https://xcb.freedesktop.org/manual/group__XCB__Present__API.html) observer selected only the owned benchmark render windows on Gaming Mode XWayland `:1`. In a 20-second sample it received 1,198 pixmap completion events for the native GL window: 59.90 FPS, p99 presentation interval 16.75 ms, maximum 33.47 ms; all events reported flip mode. This supports XWayland presentation delivery during that short segment, not physical panel scanout or sustained acceptance. No window creation, swap requests or Steam statistics FIFO reads were used. Private raw evidence: `.runtime/deck60-evidence/r8-gaming-present-20s.csv`.

The corrected combat/return diagnostic completed on r11: earned combat XP, controller connected and canvas focused, return to origin, inventory/map close, no-action reload preserving account/XP/inventory/tile, four verified backups, unchanged original mutable paths and whole-world startup cancellation. Its 131.52-second trace averaged 57.50 FPS, p99 25.74 ms and maximum 1.37 seconds, including first-map loading. A separate 45-second Present completion sample during return/UI measured 58.20 FPS, p99 17.06 ms and maximum 814.70 ms; the average includes that stall. These results prove fixture behaviour and identify remaining loading/transition costs, not the 60 FPS target.

The fresh r12 route retained another fixture failure at the initial farm approach: native collision arrays contain a six-tile padded border, so their bounds are wider than the actual 104×104 loaded scene. Route navigation now uses the real scene dimensions and an intermediate farm-road waypoint; fresh combat opens the observed house doors as needed while approaching the pen. A subsequently tested approach tile inside the house was blocked by scenery and has been removed. Fresh full-loop preflight remains pending. The 336.68-second failed trace averaged 59.63 FPS, p99 23.06 ms and maximum 119.39 ms; an independent 201.22-second presentation sample measured 59.79 FPS, p99 16.78 ms and maximum 113.89 ms. Neither is sustained-route acceptance.

The owner unplugged the Deck for the next preflight. Actual AC sensor state is now logged separately from battery status: the battery can report discharging near its charge limit while `ACAD/online` is still 1. Gaming Mode reports both FPS limit and refresh feedback at 60. Battery and external-power runs will be labelled from the actual AC state and owner confirmation.

The r15 fresh full loop completed all route stages with earned combat XP, inventory/map close and save/reload/startup-cancellation checks. Its 439.89-second callback trace averaged 58.44 FPS, p99 24.19 ms and maximum 1.22 seconds. The following long run exited at map open because the probe cast every active renderer to OpenGL while writing progress. Native map open intentionally captures the old toolkit and selects Java software (`Class24.method298`); close restores it (`Class301.method2282`). The progress logger now tolerates this transition, records renderer changes and explicitly checks OpenGL restoration after close. Generic probe failures retain their frame trace. The r16 focused map regression passes: native OpenGL → software map → OpenGL, followed by verified save/reload and startup cancellation.

Independent XWayland GL presentation subscriptions also need to follow recreated GL windows across map transitions. GL-only samples do not measure software-map drawing. No independent whole-session presentation claim is made.

## Sustained battery result

The r16 Gaming Mode route completed five full loops over **2169.54 seconds (36.16 minutes)** at 1280×800. The owner confirmed unplugging; all recorded `ACAD/online` readings were 0. Save/reload, native saved-field equality, four backups, original mutable paths and startup cancellation passed. The map returned to OpenGL each time.

| Full native callback trace, including loading/UI | Result |
| --- | ---: |
| Average FPS | 58.76 |
| p95 interval | 19.54 ms |
| p99 interval | 22.79 ms |
| Maximum interval | 2409.90 ms |
| Minimum rolling five-second FPS | 6.38 |

The duration target passes; the full-trace 20 ms p99 and rolling 58 FPS thresholds fail. Ordinary route progress was commonly near 60, but loading/map transitions still cause large stalls. No solid-60 completion claim is made.

The separate GL observer followed five window lifetimes, recording 84,977 completion events over about 24 minutes of partial coverage. Four substantial lifetimes averaged 59.23–59.37 FPS with p99 16.77–16.80 ms, while retaining 867–965 ms stalls. The short final lifetime was 4.25 seconds at 38.12 FPS. Software-map drawing and physical panel scanout are not measured; this is not whole-session compositor acceptance. A compositor-wide MangoApp logging attempt produced no usable CSV and its configuration was restored exactly.

Whole New-session measurements: peak combined client/server RSS 2761.65 MiB; peak amdgpu sensor 56°C. Reported mean client CPU was 115.95% of one core, server 12.84%. Timed phase arrays reached their 120,000-sample bounds, so phase quantiles cover the stored prefix; totals/maxima and the separate full callback trace remain valid. Process-start GC totals include startup and all transitions (400 young, 54 full collections; 7.66 seconds combined pause time).

Private evidence: `.runtime/deck60-evidence/r16-battery/`. Raw loading/UI stalls remain in the trace.

## Fullscreen follow-up

Client patch 0039 adds configurable **F11** fullscreen entry/exit, current-monitor selection, window bounds/chrome/size-lock restoration and fullscreen-safe bounds persistence. Controller and graphics preset are independent. The native benchmark now calls this public UI operation rather than manipulating the frame through reflection. Host software New/Continue checks pass. The final r21 Gaming Mode OpenGL check passes repeated registered F11 toggles, autorepeat suppression, locked window-bounds restoration, saved-bounds preservation, game focus, title/sidebar toolbar restoration, native map open/close, save/reload and startup cancellation. New/Continue totals: 59.507/54.715 seconds, including readiness/save. Private evidence: `.runtime/deck60-evidence/r21-fullscreen/native-smoke-summary.json`. The size-lock preference stays effective while programmatic fullscreen sizing remains available; avoiding resizable-flag changes fixes the repeat-toggle focus regression. Gaming Mode uses a borderless display-sized window. Physical F11/Steam Input mapping remains a user check; the harness dispatches the registered native key adapter.

## Remaining acceptance

The owner requested shutdown after the final fullscreen check; no further test will start this session. The 30-minute external-power comparison remains pending. Investigate remaining loading/map stalls. Verify real controller input, suspend/resume, Steam overlay/keyboard and clean save/reload with the final candidate. No 60 FPS completion claim or player-shortcut update is made yet.
