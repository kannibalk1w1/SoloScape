# WASM face-boundary audit: Class64_Sub1 projection to Class109 fills — 17 October 2026

Status: **source audit only (revised after coordinator review). No experiment was run, nothing was ported or compiled, and no runtime or performance claim is made.** The smallest real model path that feeds the already-extracted `Class109` fills is the flat-colour projected face loop: `Class64_Sub1.method654` (the `i == -1` branch) → `method650` → `method643` → `method635` → `Class109.method1018`. Its closure is about **441 verbatim `Class64_Sub1` lines plus one labelled guarded adapter** that replaces `method657`'s state-2 branch, with about 59 instance fields. That is borderline small. Keeping `method657` verbatim pulls in about 344 more lines and is too broad for one experiment.

Builds on [WASM_RENDERER_INVESTIGATION](WASM_RENDERER_INVESTIGATION.md) (flat fill, 2 methods), [WASM_MATERIAL_INVESTIGATION](WASM_MATERIAL_INVESTIGATION.md) (shaded and textured fills) and [WASM_RASTER_POC](WASM_RASTER_POC.md) (edge kernel, a different path). Source paths are relative to the read-only `upstream/runelite-client/client/src/` checkout and were not copied into Git.

## 1. Scope and inputs

Native sources were read only. Their digests match the earlier reports:

| File | SHA-256 (verified 2026-10-17) |
| --- | --- |
| `Class64_Sub1.java` (3,227 lines) | `e02518708ff51fc07c42e1f3fa587810c40c715948054c344b90484afda91398` |
| `Class109.java` (4,467 lines) | `058b9ffd636007796f75dd50f25a422e173e820f7dcee135b6b71989d874308a` |
| `Class167.java` | `d76c65b840aaca9bf042581c68c6e5c4b5bcd037f00c19a72f82edacbd1a5975` |
| `ha_Sub1.java` | `f3f01437c28ad160ca356311ab021d9d4cfbc4759cb367435f0209eba4b0bae7` |
| `ha.java` | `f50efd45125feb64dfee81a3dcbe6b25324550b1a8d5701f6121d0b91a8d2a6b` |

Other files inspected, all in this worktree: `docs/WASM_RENDERER_INVESTIGATION.md`, `docs/WASM_MATERIAL_INVESTIGATION.md` (closure table, limits, next step), `docs/WASM_RASTER_POC.md`, `docs/WASM_TRANSFER_INVESTIGATION.md`, `experiments/wasm-raster/README.md` and `tools/extract_face_kernel.py`, and the closure extractor header in `experiments/wasm-material/tools/extract_material_closure.py`. `experiments/wasm-material/build/closure.json` was checked for `Class64_Sub1` references (call sites only, no `method654`). No `AGENTS.md` or `CLAUDE.md` exists in the worktree.

Method: line-by-line reading of method bodies and call sites. Brace nesting was counted per line, not inferred from indentation. Line counts and field sets come from read-only scripts in the scratchpad, outside Git. Fields are matched by name, so counts are approximate.

Bytecode: the coordinator's JDK 21 `javap` (`/home/kannibalkiwi/orca/projects/SoloScape/.runtime/jdks/jdk21/bin/javap`) was used read-only on `Class64_Sub1` from the client jar. The output is in the scratchpad, outside Git. It was used to check **`method643` only** (§3, §7). `method634`, `method657`, `method654` and `method650` were **not** bytecode-checked and remain source-only.

## 2. Boundary map (source-verified)

Line numbers refer to `Class64_Sub1.java` unless marked otherwise.

| Layer | Method, lines | What it does | Direct callees |
| --- | --- | --- | --- |
| Entry | `method615(Class101, Class318_Sub3, int)`, 385–387 | Package-private draw entry; passes `i = -1` and the flags as `i_632_` | `method654` |
| Entry selector | `Class305.aBoolean3870` chooses `method608` or `method615` (e.g. `Class318_Sub1_Sub3_Sub1.java:277-278`) | Scaled (`i != -1`) or unscaled path | 16 files call `method615`, 15 call `method608` |
| Projection | `method654(Class101, Class318_Sub3, int i, int flags)`, 2400–2665 | Gates, camera-space transform, projection to `anIntArray5321/5343/5355` | `method655`, `method632`, `Class109.method1023`, `method634`, `method650` |
| Projection, `i == -1` | 2498–2542 (loop 2499–2520) | Transforms each vertex, sets depth `anIntArray5355`, perspective divide, `-5000` for near-plane misses | — |
| Projection, `i != -1` | 2543–2560 | Same with a fixed divisor `i` | — |
| Face loop | `method650(bool, bool, int, int)`, 2283–2316 | Iterates faces; the flat path is the else branch (2312–2315), faces in index order | `method643` |
| Face dispatch | `method643(int i, boolean bool, boolean bool_317_)`, 1359–1403 | Per-face gates and dispatch (§3) | `method646`, `method658`, `method635`, `ha_Sub1.method3720` (textured only) |
| Flat fill dispatch | `method635(int i)`, 363–383 | Flat or textured `Class109` call; flat when `anIntArray5366[i] == -1` | `Class109.method1018` (371), `method1022` (373), `method1024` (379, 381) |
| Clip branch | `method646(int i)`, 1897–2029 | Faces with a vertex behind the near plane (`-5000`); fill calls at 1993–2025 | `method1018/1022/1024` |
| Lit branch | `method658(int i)`, 2864–2930 | Used when `aClass167.aBoolean2195` or the `bool_317_` flag is set; `method635` fallback at 2909 | `method1024`, `method1027`, `method635` |
| Colour pre-pass | `method634(boolean)`, 346–352 → `method657(boolean)`, 2714–2821 | **`method634` calls `method657` unconditionally** (349 under the sync, 351 otherwise). `method657` fills `anIntArray5368/5337/5366` in state 0 only | `method647`, `method636`, `Class25.method303`, `Class291.method2198`, `method656`, `method642` |
| Colour state | `anInt5354` (declared line 49) | State 0 runs the colour pass; state 1 runs `method647`; **state 2 skips the pass**; set to 2 at 2819 after the first colour pass | — |
| Colour set-up | `method636` 1108–1116 → `method649` 2173–2227 | Builds per-model `Class360` objects when `anInt5354 == 0` | — |
| Per-thread state | `method632(Thread)`, 121–144 | Gets `Class167` through `ha_Sub1.method3724(Thread)` (`ha_Sub1.java:1939`), sets `aClass109_5383` | — |
| Bounds | `method655()`, 2671–2706 | Lazily computes model bounds; uses `Math.sqrt` | — |
| Setup | constructor `Class64_Sub1(ha_Sub1, Class124, int, int, int, int)`, 2943 to the end of the class | Copies vertex, face and colour arrays from `Class124` (2958–2967) and sets `anInt5354 = 0` (2944) | not audited in full |
| Helpers | `method629` 97–100, `method638` 1146–1149 | Translucency and texture predicates used by `method650` | — |

Fill-side callees from the earlier reports:

- `Class109.method1018` (`Class109.java:127`) → `method1026` (3811, span). `method1026` reads the clip flag `aBoolean1671` (3812–3813) and translucency `anInt1674` (3821, 3852, 3871–3872). No new fill is needed for the flat path.
- `Class109.method1023(boolean)` (2782–2784) sets `aBoolean1675` (wireframe). It is called at 2488; the wireframe branch at `Class109.java:128` is already stubbed.

Other callers of the same fills, outside this boundary: `ha_Sub1.java:972–980` (`method1027`), `ha_Sub1.java:1766/1768` (`method1018`), and `s_Sub1.java:573–882` (terrain). Not audited.

## 3. Face selection and projection (source-verified; `method643` bytecode-checked)

**Projection (`method654`, `i == -1`).** The camera-space transform uses the twelve `Class101_Sub1` floats (`aFloat5655`–`aFloat5686`) read at 2408–2475. Per vertex, 2503–2513:

- `anIntArray5355[v] = (int) depth`
- if `depth >= anInt7482` (near plane), `anIntArray5321[v] = anInt2229 + (int)(x * anInt7491 / depth)` and `anIntArray5343[v] = anInt2215 + (int)(y * anInt7497 / depth)`
- otherwise `anIntArray5321[v] = -5000` and `bool_656_ = true`

`anInt2229` and `anInt2215` come from `Class109.anInt1665` and `anInt1668` (2492–2494). The visibility test at 2421 and early returns at 2436–2437 and 2452–2453 can end the whole draw before any face is processed.

**Argument order into `Class109`.** `method635` passes `anIntArray5343` values first and `anIntArray5321` second. The first three `float` arguments of `Class109.method1018` are therefore rows (y). `Class109.java:133–140` agrees: the slope `(f_44_ - f_43_) / (f_41_ - f)` is x-difference over y-difference, using arguments 4–5 and 1–2.

**Face gates (`method643`), confirmed in bytecode** (`javap -c -p`, offsets refer to that disassembly):

- 1360: faces with `anIntArray5366[i] == -2` are skipped.
- Clipped faces (`bool` set and a vertex at `-5000`) call `method646` and return (274–277).
- Textured faces (`anIntArray5400[i] != -1`) jump straight into the body (287).
- Untextured faces compute the signed screen-area sum from `anIntArray5321` (x) and `anIntArray5343` (y) at 290–332, and return when it is `<= 0` (`ifle`, 333). This is the untextured back-face cull; the source braces at 1387–1400 agree.
- Only then is `aBoolean1671` written (396). It is the clip flag: some x outside `[0, anInt2221]`. `Class109` uses it to clamp x to `anInt1679`.
- 399–400: `bool_317_` selects `method658` (lit) or `method635` (flat); textured faces also go to `ha_Sub1.method3720` (1398).

**Face order.** `method650` draws faces in index order (2313–2314). The `aByteArray5358` buckets are used only inside the `aBoolean5382 || aClass6Array5361 != null` branch, outside the flat path.

## 4. Colour pre-pass decision and closure

**What `method657` does on the first draw.** State 0 (the constructor sets `anInt5354 = 0`, 2944) runs the colour pass. It allocates `anIntArray5368/5337/5366` (2727–2730) and fills them through `Class25.method303`, `Class291.method2198`, `Class360` and `Class41` (2748–2805). It then sets state 2 (2819). **In steady state (state 2), `method657` only runs lines 2716–2718**: it clears `aShortArray5311` when `(anInt5316 & 0x97098) == 0 && aFloatArrayArray5314 == null`, and clears `aByteArray5386` when `bool` is true. It writes no colours.

**Consequence for the prototype.** Because `method634` calls `method657` on every draw, the flat prototype cannot stub `method657` to throw or to do nothing. Two options exist; the audit compares them on counts:

| Option | Closure effect | Verdict |
| --- | --- | --- |
| **A. Verbatim `method657`** with its state-0 and state-1 branches kept, so the static closure includes `method636`, `method649`, `method647` and its state machine (`method640`, `method641`, `method644`, `method651`–`method653`), `method656`, `method642`, `method637`, and the `Class25`, `Class291`, `Class360`, `Class41` types and their fields. Guarded at run time so only state 2 executes. | `method657` (108) + helpers (~236) ≈ **344 extra verbatim lines**, plus about 9 more fields. Total ≈ 785 verbatim lines. | **Rejected for a small experiment.** The count exceeds the 450-line budget, and most of it is unreachable in the prototype. |
| **B. Labelled guarded adapter** `method657Adapter(boolean bool)`, hand-written, that reproduces lines 2716–2718 exactly. It counts entries, **throws on any state other than 2**, and never runs the colour pass. | ~10 hand-written lines. No extra verbatim lines. Three new fields: `anInt5354`, `aShortArray5311`, `aByteArray5386`. `anInt5316` and `aFloatArrayArray5314` are already in the core. | **Proposed.** It is not verbatim, so the adapter must be checked against the native state-2 branch by G3 (counts and side effects) and by G1/G2. |

The adapter is deliberately limited to state 2. The state-0 path is never reached in the prototype because the harness supplies the colour arrays directly and starts in state 2. This matches the steady state the native code reaches after one draw (2819).

**Harness requirements that follow from option B.** Because state 2 does not allocate, the harness must allocate `anIntArray5368`, `anIntArray5337` and `anIntArray5366` itself (length `anInt5351`) and fill them with synthetic values. The native reference must receive the same arrays before its verbatim `method654` runs.

**Closure table (verbatim lines and approximate field counts):**

| Set | Methods (lines) | Lines | Fields (approx.) | Decision |
| --- | --- | --- | --- | --- |
| **Flat core** | `method654` (266), `method650` (34), `method643` (45), `method635` (21), `method634` (7), `method632` (24), `method655` (36), `method629` (4), `method638` (4) | **441** | **~56** (includes `anInt5316`, `aFloatArrayArray5314`) | Verbatim. `method634` is verbatim and calls the adapter. |
| **Adapter (B)** | `method657Adapter` (hand-written, ~10 lines; replaces verbatim `method657`) | ~10 (hand-written) | +3 (`anInt5354`, `aShortArray5311`, `aByteArray5386`) | Labelled guarded adapter; state 2 only. |
| Colour chain (A only) | `method657` (108), `method636` (7), `method649` (55), `method647` (8), `method640` (22), `method641` (30), `method644` (10), `method651` (9), `method652` (26), `method653` (30), `method656` (5), `method642` (26), `method637` (6) | ~344 | +~8 | Not included under B. Included under A, which exceeds budget. |
| Clip branch | `method646` (133); helpers already in the core | 133 | 23 | **Guarded throw.** The scene must have no near-plane misses. |
| Lit branch | `method658` (67) | 67 | 16 | **Guarded throw.** Requires `aBoolean2195` false and `bool_317_` false. |
| Textured | `method1020`, `method1024`, Class6 texture state (`method643` 1394–1398, `method635` 376–382) | not counted | — | **Excluded.** Textures are a separate closure, already covered for the fills by the material experiment. |
| Not in path | `method645` (1794–1896, bounding test for `method623`/`method628`), `method630`, `method605`, `method622`, `I`, `P` | — | — | Excluded. |

Stand-ins needed by the flat core, in the style of the earlier closures:

- `ha_Sub1` (12 fields read by `method654`): `anInt7482`, `anInt7485`, `anInt7490`, `anInt7491`, `anInt7494`, `anInt7497`, `anInt7504`, `anInt7506`, `anInt7508`, `anInt7509`, `anInt7510`, `aClass101_Sub1_7492`. Plus `method3724(Thread)` (returns the stand-in `Class167`) and `method3720` (throws; textured only). `anInt7485` must be 1 (single thread).
- `Class167`: `method632` (121–144) aliases 17 `Class167` arrays, and `method635`/`method654` read `anInt2192`, `aBoolean2195`, `aBoolean2201`, `anInt2210`, `anInt2215`, `anInt2221`, `anInt2229`. Verified defaults: `aBoolean2195 = false` (10), `anInt2210 = anIntFogEnd - 255` (202), `anIntArray2242` filled with `-1` (214–216), `aClass109_2220` created at 74 and 203.
- `Class101_Sub1`: twelve `float` fields, set by the harness.
- `Class126.anIntArray4983`: palette stand-in. The native builder is not reproducible (`Math.random` jitter, per the renderer report), so the harness writes a synthetic palette.
- Type-only stubs: `Class6` (texture branch only), `Class350`, `Class318_Sub3` (null, so the guard at 2582 skips it), `Class129`, `Class342`, `Thread`.
- `Class109`: `method1022` and `method1024` are referenced from `method635` (373, 379, 381). The flat prototype stubs them to throw, as the wireframe branch is stubbed. Otherwise the material closure (3,868 lines) is pulled in.

## 5. Recommendation: one smallest prototype

**Name:** flat projected-face gate (`experiments/wasm-face/`, not created).

**Scene:** original synthetic geometry only. A small closed mesh of untextured faces, one solid colour per face written into `anIntArray5368` by the harness, `anIntArray5366 = -1`, `aByteArray5325 = null`, `aShortArray5388 = null`, `aClass6Array5361 = null`. Use a fixed-seed integer LCG for vertices, as the material experiment does. All vertices start in front of the near plane (`depth >= anInt7482`), so `bool_656_` is false. Sizes 765×503 and 1280×800. No cache data, `Class124` decoding, lighting or animation.

**Fixed inputs on both sides:** `anInt5354 = 2` (steady state); `anInt7485 = 1`; `aClass167.aBoolean2195 = false`; `aBoolean2201 = false`; `anInt5387 >= 1`; `class318_sub3 = null`; the harness-allocated colour arrays described in §4.

**Steps:**

1. Native reference: reflectively call the real jar `method654(class101, null, -1, flags)` on a `Class64_Sub1` allocated with `Unsafe.allocateInstance`, as in the earlier experiments. The real `method657` runs verbatim in state 2. Record `anIntArray5321`, `anIntArray5343`, `anIntArray5355` and the colour and depth buffers.
2. JVM verbatim: run the extracted flat core and the adapter on the JVM.
3. WasmGC: compile the same core and adapter with the stand-ins above in TeaVM 0.16.0, render in headless Chromium.
4. Compare with FNV hashes through the existing `Fill` seam.

**Pass/fail gates:**

| Gate | Pass condition |
| --- | --- |
| G0 closure | The extractor fails closed on any reference outside the allow-list. The extracted core and adapter compile with `javac` and no jar on the classpath. Verbatim flat core ≤ 450 lines (441 measured), hand-written adapter ≤ 20 lines, and ≤ 65 `Class64_Sub1` fields (≈ 59 measured). |
| G1 projection | After `method654`, `anIntArray5321/5343/5355` equal the native reference element for element at both sizes. |
| G2 framebuffer | Colour and depth FNV hashes match across native jar, JVM verbatim and WasmGC at both sizes. |
| G3 adapter and coverage | (a) Adapter entry count equals the `method634` call count on both sides. (b) Adapter throws on any `anInt5354 != 2`; zero throws expected. (c) For `aShortArray5311` and `aByteArray5386`, the post-call values equal the native reference's post-call values, including the case where `aFloatArrayArray5314` is non-null. (d) Counters show `method643` reached for every face, and the untextured back-face test rejects at least one face in the mesh. (e) Zero hits for `method646`, `method658`, `ha_Sub1.method3720`, `method1022`, `method1024`. (f) Zero swallowed exceptions in the `try` at 2647–2651. |
| G4 negative control | Before the run, move one vertex by a visible amount (for example +50 world units in x), and confirm that the **native** `anIntArray5321` changes. A one-ULP camera-float change is **not** a valid control: it may vanish in the `(int)` truncation. With the mutation in the WasmGC or JVM build but not the native reference, G1 or G2 must fail. A mismatch must be reported as a failure. |
| G5 numerics | `float`-to-`int` casts agree on JVM and WasmGC, as in the material experiment. |

Timing is **not** a gate. This experiment makes no performance claim.

**Stop conditions (stop and report; do not widen):**

- Any vertex is partly in front of the near plane, or any face is clipped, so `method646` is reached.
- Any face needs `aShortArray5388`, `aClass6Array5361`, lighting, or a non-null `class318_sub3`.
- The adapter is entered in any state other than 2 (G3b), or the native post-call `aShortArray5311` or `aByteArray5386` differs (G3c).
- The verbatim core grows past 450 lines or the field count past 65.
- The native reference needs real `Class124` data, the real palette, or any cache file.
- A stub is reached (G3e), or a `method650` exception is swallowed (G3f).

If the owner wants the lit, clipped, textured or real-model path, or wants `method657` kept verbatim (option A), that is a separate and broader decision.

## 6. Proprietary-data boundary

- Native source and the client jar are read at absolute local paths. Extracted method bodies go only to ignored `build/` directories. The `javap` output for this audit is in the scratchpad, outside Git.
- Nothing from the native source, jar bytes, cache data or assets is committed. Evidence records digests, hashes and timings only.
- The scene uses original synthetic geometry and an original synthetic palette (65,536 entries, as in the material experiment). No `Class124` decode, cache read, server or network access.
- The native reference bypasses constructors with `Unsafe`, for correctness only. That code is not in the browser build.
- The WasmGC build gets generated stand-ins and the hand-written adapter only.

## 7. Source observations versus hypotheses

**Source observations (verified by reading the lines named above):**

- The flat fill is reached only through `method650` → `method643` → `method635` → `Class109.method1018`, with `method654` (`i == -1`) providing the screen coordinates.
- `method634` calls `method657` unconditionally (346–352).
- In state 2, `method657` executes only 2716–2718 and writes no colours. In state 0 it allocates and fills the colour arrays (2727–2819) and then sets state 2 (2819).
- The constructor sets `anInt5354 = 0` (2944). State 2 is the steady state after one draw.
- Near-plane misses are the only trigger for `method646`, because `bool_656_` is set from `anIntArray5321 == -5000`.
- `method643` control flow is confirmed in bytecode (`javap -c -p`, read only): clipped faces call `method646` and return (274–277); textured faces jump into the body (287); untextured faces are culled by the signed-area test (290–333); the `aBoolean1671` clip flag is written (396) before the `bool_317_` dispatch (399–548). This matches the source braces at 1387–1400.
- `method650`'s call to `method643` is inside a `try` that swallows `Exception` (2647–2651).
- `anIntArray5400` is initialised to `-1` by `Class167` (214–216) and reset to `-1` after each draw when `aClass6Array5361` is non-null (2652–2655).
- `Class109.method1026` reads `aBoolean1671`, `anInt1679` and `anInt1674`, all inside the already-extracted closure.

**Untested hypotheses (need a run or a bytecode check):**

- `method654`, `method650`, `method634` and `method657` match the bytecode. Only `method643` was checked.
- A flat-only scene reaches no `method646`, `method658` or other lit or clipped branch. G3 tests this.
- The back-face test removes a visible share of faces in a closed mesh. The G3(d) counter tests this.
- The state-2 adapter, given the same arrays, reproduces the native post-call state exactly. G3(c) tests this.
- The `-1` initial state of `anIntArray5400` in `Class167` is enough when `aClass6Array5361` is null. G3 tests this.
- Float arithmetic in `method654` matches on JVM and WasmGC. Earlier experiments matched on simpler arithmetic only.

## 8. Unproven dependencies (named)

- **Camera matrix:** how the `Class101_Sub1` floats are derived (caller side; not audited).
- **`Class124` model decode:** vertex, face and colour arrays and their counts (`anInt1836`, `anInt1821`, `anInt1817` and the array fields 1841–1863 in the constructor). Not audited.
- **`method655` details:** the bounds math with `Math.sqrt`. Read only for its effect on the `aShort` bounds fields.
- **`ha_Sub1` setup:** constructor and clip set-up (`method3713` per the renderer report). The values of `anInt7482`, `anInt7491/7497`, `anInt7510/7504` and the clip fields are not audited.
- **`anIntFogEnd`:** used in `Class167`'s `anInt2210`. Its origin is not audited.
- **Colour pass (state 0):** `Class25.method303`, `Class291.method2198`, `Class360`, `Class41`, `Class10`, `Class12`, and the `method647`/`method640` state machine. Excluded from the prototype.
- **Palette:** `Class126.anIntArray4983` builder (`Class239_Sub25.method1827`). Not re-read here; the renderer report cites its `Math.random` jitter.
- **Wireframe:** `ha.method3645`. Already stubbed in the earlier closure.
- **Other callers:** `ha_Sub1.java:972–980`, `ha_Sub1.java:1766/1768`, `s_Sub1.java:573–882` (terrain).
- **Full constructor:** `Class64_Sub1(ha_Sub1, Class124, ...)`, 2943 to the end of the class. Its effects on textures and `aClass6Array5361` are not audited.

## 9. Changes and verification

- Changed: this file only, `docs/WASM_FACE_BOUNDARY_AUDIT_20261017.md`.
- No experiment run, no build, no test suite, no package install, no renderer port, no change to gameplay, client or server code, and no change to existing reports or the status ledger.
- Git: no commit, push, branch switch or merge.
- Whitespace check: `git diff --check` (reported with the task).
