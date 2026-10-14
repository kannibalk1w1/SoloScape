# Deck loading and transition stall diagnosis — 14 October 2026 (revised)

Analysis of the private r29 five-loop route traces (`.runtime/deck-controller-evidence/r29-route/`: `route-new.csv` 128,025 frames, `route-new.json` aggregate phase timings, `present-route.csv` 106,274 compositor events) plus the prepared client source (`upstream/runelite-client/client/src`, cited below). No production code changed; nothing was built or run on the Deck. Reproduce with `scripts/analyse_deck_stall_clusters.py route-new.csv`; the tests include a full-trace check enabled by `SOLOSCAPE_R29_ROUTE_CSV=<path>`. Interval = time between consecutive overlay `render()` callbacks, not scanout.

**Revision note.** The first version of this report (a) called the compositor trace a different run, (b) treated aggregate and truncated phase maxima as ruling out overlay, plugin and GC causes, and (c) bounded GC by its average pause. All three were wrong; they are corrected below.

## What the trace shows

**1. The worst gaps are client map-region loads, repeating every loop.** 40 frames are ≥300 ms and 38 sit within two frames after a `client_state=11` frame (29 at +1 frame, 5 at +2, 4 at 0). The 29 state-11 frames pair with 20 walk stalls (4 per loop × 5) plus 9 map open/close transitions. In every loop the walk stalls fall at the end of `farm_road` (≈178–193 s into a loop, 686–1,007 ms), `mill_road` (≈237–244 s, 607–683 ms), `road_return` (≈331–340 s, 671–761 ms) and `courtyard_return` (≈373–382 s, 774–805 ms). The tile is not logged, so "scene edge" is inferred from waypoints beyond y≈3260.

**2. Map open/close is the longest single cost.** Renderer transitions go `ha_Sub2 → ha_Sub1 → ha_Sub2` (OpenGL → software → OpenGL) at every map open and close. Open gives 0.5–1.0 s gaps; close gives 1,344 ms the first time and 0.8–0.86 s later, plus a ~300 ms neighbour.

**3. The compositor trace is the same r29 process, observed concurrently.** The passive XWayland observer ran for 1,800.01 s against that game process, so it covers the first 1,800 s of the 2,168.6 s route. Its five GL window lifetimes match the four map opens (437, 866, 1,298 and 1,732 s). Epoch 1 stalls (983, 664, 746, 783 ms) pair with the first loop's walk stalls (1,007, 683, 761, 805 ms), roughly 20–25 ms shorter. Compositor events over 20 ms are about 2%, versus 4.0% of overlay frames; compositor p99 is 16.8–16.9 ms versus 22.35 ms for overlay callbacks. The stalls are therefore visible to the compositor, but part of the 20–25 ms jitter is not (it excludes software-map frames and unobserved gaps).

**4. Stalls fully explain the rolling-FPS failure but not the p99 miss.** The 49 frames ≥100 ms add 27.8 s of excess (1.3% of run time; average FPS stays 59.04) and produce the 15.76 FPS minimum. Removing them leaves p99 at 22.28 ms: about 5,000 frames of 20–100 ms (mostly 20–25 ms) concentrated in walking steps (`courtyard` 8.5%, `farm_road` 7.3%, `shop_approach` 7.2% against `farm` 1.6%). They are typically six frames apart (1,790 of 5,021 gaps). Six 60 Hz frames equal five 50 Hz logic cycles, and the logic loop ran 107,185 cycles over 128,026 frames. A logic/pacing beat is a **hypothesis**; the data does not test it.

## Source evidence: synchronous work on the client thread

The probe samples the game state from `Class240.anInt4674` (`NativeDeckRouteProbe.java:174`).

- **Region rebuild** — `client.java:1790` calls `Canvas_Sub1.method123` whenever `mapRegionDirty` is set and the state is 10 or 11. That function (`Canvas_Sub1.java:129-~310`) clears and re-reads the scene's map/loc/NPC data, builds `Class237_Sub1` scene structures (`:249-:280`, via `Class44.method385` or `Class348_Sub1_Sub1.method2727`), then runs `Class108.method1015` and `Class122.method1090`, and **calls `System.gc()` unconditionally at `Canvas_Sub1.java:238`**. Everything runs in one client-thread call, so it appears as a single long logic phase (`Applet_Sub1.java` logic block bracketed by `FrameTimings.LOGIC`). A full collection on a heap this size (client RSS peak 1.3 GiB) is a plausible large part of the stall, but its share is not measured.
- **Map open** — the CS2 interpreter (`Class66.java:511, 664, 713`, plus `Class348_Sub1.java:38`) calls `Class24.method298`, which saves the current toolkit in `Class111.anInt1720` and calls `Class367_Sub10.method3553(true, …, 0)`. That runs `Class258_Sub3_Sub1.method1971` → `Class348_Sub23.method2965`, which creates a new `ha_Sub1`, then rebuilds renderer-dependent state. The `method1971` tail calls `Class170.method1311`, `Class369.method3568`, `ObjTypeList.method1933(…, true)` (object type caches), `Class101.method901`, `Class354.method3466` and `Class348_Sub40.method3038`, then steps the game state to 11 (`Packet.method3379(2, 11)`).
- **Map close** — `Class66.java:798` / `Class348_Sub42_Sub8_Sub2.java:1521` call `Class130_Sub1.method1134` (`Class130_Sub1.java:31-36`): `Packet.method3379(2, 11)`, `Class301.method2282` (restores the saved toolkit through the same `method3553` path, creating a new OpenGL `ha_Sub2`, including the 140 MiB `method3702(146800640)` allocation at `Class348_Sub23.java:107`, `Class97.method873` and `Class76.method773`), then **`System.gc()` at `Class130_Sub1.java:35`**. The first close is also the longest gap (1,344 ms), when OpenGL and texture caches are cold.
- Other explicit GCs sit on logout/state reset (`Class348_Sub40_Sub34.java:36`) and on heap-pressure checks (`ha_Sub2.java:1435`, `Class164.java:40`). I did not check whether the route reaches them.

I did not find a rate limit or concurrency on any of these: each is a synchronous call from the client loop. I could not confirm whether `Class367_Sub10.method3553` is the only way the map reaches software mode, and I have not timed any step inside them.

## What the existing data cannot say

- `route-new.csv` has step, interval and state only: no tile, no per-frame phase times, no GC event times.
- `FrameTimings` stores 120,000 samples per phase but counts 141,205 logic calls, so phase maxima (logic 977.5 ms, frame 762.6 ms, present 96.5 ms, plugin 44.0 ms, overlay paint 23.9 ms) come from the first 120,000 calls and cannot place the *later* stalls. Aggregates cannot rule any phase out. One logic call also includes catch-up cycles after a delay.
- GC: 55 `PS MarkSweep` collections totalled 4,251 ms (≈77 ms mean), but a mean says nothing about the largest event; one 600 ms pause would hide in that total. With explicit `System.gc()` calls on every rebuild and map close, a pause of several hundred milliseconds is not excluded.

## Cause confidence

| Claim | Confidence |
| --- | --- |
| Walk and map stalls coincide with client loading state | High (38/40, offset +1 for 29) |
| Walk stalls are synchronous region rebuilds in `Canvas_Sub1.method123` | Medium-high (source path and timing agree; tile and phase not recorded) |
| Map stalls are the synchronous OpenGL ↔ software toolkit switches | Medium-high (renderer log, code path) |
| `System.gc()` is a large component of those stalls | Plausible, not measured |
| p99 miss is a separate steady-jitter cause | High |
| 50 Hz/60 Hz beat is its mechanism | Low (hypothesis) |

## Bounded optimisation candidates (not recommended until measured)

1. **Remove or gate the explicit `System.gc()` calls** at `Canvas_Sub1.java:238` and `Class130_Sub1.java:35`. Smallest change, but a full collection is cheap to skip only if heap headroom is adequate on the Deck; measure GC share first.
2. **Skip the software toolkit swap for the Deck map**, if the map can render under OpenGL, which avoids two toolkit creations per open/close. This touches rendering, so it needs a visual check. Do not attempt it without the measurement.
3. **Spread `method123` across frames.** Highest risk (it is a single state-machine call); only after phase attribution.

## One bounded next measurement (a client patch and one run; needs coordinator agreement)

Reuse the route as-is: `scripts/smoke_profile.py --desktop --deck-route-seconds 60` (60 is the minimum; the loop finishes first, about 433 s, and `deck-controller-validation.sh` route mode accepts `SOLOSCAPE_BENCHMARK_SECONDS=60`). `soloscape.deck60.route.startStep` and `.singleLoop` exist only as JVM properties in `NativeDeckRouteProbe.java:31,121`; `smoke_profile.py:200` does not forward them, so there is **no `--startStep` CLI** to recommend.

**Timestamp semantics.** The interval row at overlay callback N measures everything since callback N−1: logic cycles, scene draw, present and plugin work of iteration N. It is *not* the cost of the work whose state is read at N. State 11 is read at callback N, and the stall usually arrives in the next interval, so attribute by phase columns, not by the state flag.

**Per-frame columns** (preallocated primitive arrays, written without allocation, flushed at loop end), all in the frame loop in `Applet_Sub1.java` around the existing `FrameTimings` calls:

| Column | Source | Cost |
| --- | --- | --- |
| callback_ns, state | existing `render()` | free |
| logic_ns, logic_cycles | existing `FrameTimings.LOGIC` / `cycles()` | 1 `nanoTime` pair |
| draw_ns, present_ns | `FrameTimings.FRAME`, `PRESENT` | pair each |
| overlay_ns, plugins_ns | existing phases | pair each |
| tile_x, tile_y, plane | `tile()` in the route probe | 3 field reads |
| gc_total_ms_delta, gc_count_delta | sum of `GarbageCollectorMXBean.getCollectionTime/Count` between callbacks | 2 bean calls per frame, ≈ microseconds; may be sampled only when interval >40 ms |

**Rare-event timers** (zero steady-state cost): wall time around `Canvas_Sub1.method123` as a whole and around its `System.gc()`; around `Class348_Sub23.method2965` (new toolkit, 140 MiB `method3702`, `Class97.method873`), the `method1971` tail, and `Class130_Sub1.java:35`. Add a `GarbageCollectionNotificationInfo` listener recording cause, duration and start time per collection, which is the only way to bound the largest GC pause. It will also show whether those pauses are `System.gc()`-caused.

**Expected readout.** Each of the 29 loading events should show which of {rebuild, toolkit create, `System.gc()`, other logic} holds most of its 0.6–1.3 s; the `courtyard`/`farm_road` jitter frames should show whether the extra 3–8 ms sits in logic cycles (beat hypothesis) or in draw/present. The analyser would then read tile and `gc_total_ms_delta` as optional columns, which is a plan for the next version, not part of this one.
