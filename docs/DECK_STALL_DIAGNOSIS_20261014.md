# Deck loading and transition stall diagnosis — 14 October 2026

Read-only analysis of the private r29 five-loop route traces (`.runtime/deck-controller-evidence/r29-route/`: `route-new.csv` 128,025 frames, `route-new.json` phase timings, `present-route.csv` 106,274 compositor events). No production code changed, nothing was built or run on the Deck. Reproduce with `scripts/analyse_deck_stall_clusters.py route-new.csv` (tests: `scripts/test_deck_stall_clusters.py`). Frame intervals are native overlay callbacks, not scanout.

## Findings

**1. Worst gaps are client map-region loads, and they repeat identically every loop.** 40 frames are ≥300 ms; 38 sit within five frames of a `client_state=11` (loading) frame. The 29 state-11 frames match 20 walk stalls (4 per loop × 5) plus 9 map open/close transitions. The walk stalls land at the end of four steps in every loop, at nearly the same loop offset: `farm_road` (≈178–193 s, 686–1007 ms), `mill_road` (≈237–244 s, 607–683 ms), `road_return` (≈331–340 s, 671–761 ms) and `courtyard_return` (≈373–382 s, 774–805 ms). Outbound crossings are about 0.6–1.0 s; so are the returns. Route waypoints put these steps beyond y≈3260 and back, consistent with scene rebuilds as the player nears the loaded-area edge. The player's tile at the stall is **not** recorded, so this is inferred.

**2. Map open/close is the longest single cost.** The renderer transitions show `ha_Sub2 → ha_Sub1 → ha_Sub2` (OpenGL → software → OpenGL) at every map open/close, each pair taking ~2 s of wall time. Open produces 0.5–1.0 s gaps (two adjacent frames, e.g. 998 + 766 ms). Close produces up to 1,344 ms (first loop) and 0.8–0.86 s afterward, plus a ~300 ms gap. The passive compositor trace agrees: five GL window lifetimes for four map opens, with 4–5 stalls of 0.58–0.98 s per lifetime.

**3. Stalls cost little average time but fully explain the rolling-FPS failure.** The 49 frames ≥100 ms contribute 27.8 s of excess (1.3% of the 2,168.6 s run), which is why average FPS stays at 59.04. Each 0.7–1.3 s stall drops its 5 s window below 58 FPS and produced the 15.76 minimum.

**4. The p99 ≤20 ms miss is a separate cause: ~4% steady jitter, not loading.** Removing every frame ≥100 ms leaves p99 at 22.28 ms. 5,021 frames fall in 20–100 ms (mostly 20–25 ms), concentrated in walking steps: `courtyard` 8.5%, `farm_road` 7.3%, `shop_approach` 7.2%, `origin_return` 6.5%, versus ~1.6% in `farm`. The gaps between them are modally exactly six frames (1,790 of 5,021), with 5 and 12 next. Six 60 Hz frames equal five 50 Hz logic cycles (100 ms), and logic ran 107,185 cycles over 128,026 frames (0.84 per frame). That points to a beat between 50 Hz logic and 60 Hz pacing: the frames carrying a logic cycle plus a ~13.9 ms median draw sometimes overshoot 16.7 ms. The compositor trace reports only 1.9% of events over 20 ms and p99 of 16.8–16.9 ms, so much of this may be callback-side rather than visible. **Medium-low confidence; this mechanism is a hypothesis.**

**5. Phase timings point at the logic phase for load stalls but cannot attribute individual frames.** The phase report is aggregate: logic max 977.5 ms, frame-including-overlays max 762.6 ms, present max 96.5 ms, overlay paint max 23.9 ms, plugins max 44.0 ms. Overlay and plugin work are ruled out as the stall source. GC is unlikely: 55 full collections totalled 4,251 ms (≈77 ms each) over the run, below the 600–1,300 ms gaps, but GC logs were not captured per event.

## Limits

- `route-new.csv` has step, interval and client state only. No tile, logic cycles, draw or present time per frame.
- `FrameTimings` keeps 120,000 samples per phase; 141,205 logic calls means maxima come from the first 120,000 calls (`truncated: true`). A logic call also covers catch-up cycles after a delay, so 977 ms could include them.
- The compositor trace is a different run and excludes software-map frames and unobserved gaps.
- No source for the region-load path is in this checkout (patches only). I did not read the obfuscated scene-rebuild code, so which sub-step dominates is unknown.

## Cause confidence

| Claim | Confidence |
| --- | --- |
| Walk and map stalls coincide with client loading state | High (38/40) |
| Walk stalls are map-region rebuilds near scene edges | Medium-high (tile not recorded) |
| Map stalls come from the OpenGL ↔ software renderer switch | Medium-high (renderer log plus timing) |
| p99 miss is separate steady jitter | High |
| 50 Hz/60 Hz beat is its mechanism | Medium-low |

## One bounded next measurement (needs coordinator agreement; a client patch and build)

Extend the route trace only, behind the existing `soloscape.performance.timings` flag, with per-frame columns: logic cycles run, logic ms, draw ms, present ms, player tile, and the JVM GC pause total delta. Run **one** 8-minute loop with the existing route (`--startStep` can begin at `road`) on the same Deck, no new quest or endurance rerun. It tells us:

- which phase holds each load stall, and the tile where it starts (rebuild versus renderer switch);
- whether the 6-frame 20–25 ms frames are logic-cycle frames (the beat hypothesis).

Do not change pacing or preload logic until this identifies the phase. If rebuild dominates, the candidate fix is to spread region work across frames or avoid the OpenGL → software swap for map open; neither is justified yet.
