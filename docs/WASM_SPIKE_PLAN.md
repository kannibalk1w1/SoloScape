# Smallest useful next WASM spike

Status: **planned, later**. The compiler sanity/kernel and negative native-presenter tests are recorded in [feasibility](WASM_FEASIBILITY.md) and [the reproducible experiment](../experiments/wasm-kernel/README.md). They do not enable a browser game. Keep this track separate from the native release.

## Decision and uncertainty

The strongest uncertainty is whether a **useful real 634 software-raster closure** can run without AWT/Applet, RuneLite startup, native libraries and the full global client. Successful StickMath compilation does not answer that; the unmodified AWT presenter has already failed.

Choose one experiment: **one actual software-raster path → browser framebuffer**, through TeaVM WasmGC. No login, server port, world simulation, full cache conversion, large UI or WebGPU implementation. Prefer a small original model/triangle using the native raster algorithm; then one locally supplied authorized model if permitted. A stock PNG drawn with Canvas proves presentation only and must not count as success for the raster gate.

## Scope and procedure

1. Preserve matched baseline and use a separate ignored experiment build/output. Pin TeaVM 0.16.0 and the source/patch/jar digests; retain notices. Native build tasks/configuration remain unchanged.
2. Start with `ha_Sub1`/its raster context dependency graph and the native pixel-buffer contract (`Class348_Sub31_Sub1.method3008`, `Class348_Sub31`). Enumerate reachable constructors/static initializers. Identify the smallest triangle/model path independent of live client state. Do not stub collision, game state or rendering behaviour merely to get a green compiler run.
3. Replace **only experimental presentation/platform entry points** with an explicitly named adapter that takes pixels and dimensions. No production renderer refactor. Record every excluded dependency and what functionality is consequently absent. If a real raster closure cannot be isolated in one small patch, stop with that evidence rather than porting hundreds of classes.
4. Compile that closure to WasmGC. Use the same original geometry, camera/clipping and colours on the JVM and browser. Compare framebuffer hashes on integer-only scenes; where floating-point/raster boundaries differ, document pixel-difference bounds and inspect edges/alpha/texture handling rather than silently accepting any output.
5. Present through Canvas ImageData first. Use explicit RGB→RGBA conversion and dimensions/row stride. Then, only if upload cost dominates, compare uploading the same framebuffer as a WebGL texture. Browser GPU translation is not required for this gate.
6. Measure locally at 765×503 and 1280×800: module/loader compressed and raw bytes, cold/warm load, raster ms, conversion/upload ms, callback frame tails, peak allocated buffers/heap if available. Separate browser scheduling from renderer work; document power, browser and hardware. Do not extrapolate native or host-headless performance to Deck/Chromebook.
7. Delete imported data/output and rebuild from a clean checkout plus explicit local input. No server, network or asset downloader should be needed to demonstrate the isolated frame. Record SHA-256 of inputs and output, compiler result and limitations.

A timebox is a scope limit, not a deadline promise: stop after the raster dependency audit plus one minimal adapter attempt. No automatic expansion into a whole client, transport hierarchy or new renderer if it fails.

## Observable success/failure

| Gate | Pass condition | Stop condition |
| --- | --- | --- |
| Code boundary | One explainable native raster path compiles with a small explicit browser adapter | AWT/Applet/Guice/JNI/global client closure remains large or requires rewriting unrelated systems |
| Correctness | Same original scene is recognizably correct; pixel comparisons and intentional tolerances recorded | Missing geometry, wrong colour/alpha, unexplained clipping/precision differences |
| Performance | Actual measured frame/copy budget leaves credible room for scene/UI/input; show data, do not assume 60 FPS | Micro-scene alone exceeds the selected device budget after presentation cost is separated |
| Distribution | Only permitted source and original assets in public artifacts; authorized real input stays private/local | Requires shipping proprietary cache or opaque bundled native code without permission |
| Reversibility | Remove experiment without changing native jars/patch stack/profiles | Native product becomes dependent on the experiment |

An original triangle is a compiler/raster gate, **not** proof that a full 634 scene, animated NPC or game client is viable. If it passes, the next separately approved gate is a static locally imported model/region with real texture/material decoding. If that passes, evaluate minimal browser transport to the existing JVM server. Strategy C/D, multiplayer integration, storage migrations and PWA release remain separate work.

## Later transport and persistence gates

Do not implement them in this spike. Before a browser session, validate an ordered-byte bridge (including native login/cache, fragmentation, bounded queues and close), then a disposable profile's versioned save/export/recovery and tab-discard cases. The first browser session may use an existing JVM server; that preserves authority but is not offline self-contained deployment.

## What was actually run in this research

- Tiny unchanged `StickMath` bytecode compiled with TeaVM 0.16.0 and executed its expected-value assertion in Chromium 153.
- Native 765×503 software presenter root failed on AWT image/rectangle and reachable Applet classes. Failure retained; no source replacements were used to hide it.
- Native client/server/cache sizes and Java/AWT source counts were inspected. No full scene/browser-server benchmark, physical browser gamepad campaign or playable web client was run.

The public [probe result](evidence/research-20261017/wasm-probe.json) distinguishes measured facts from plans. Native Deck acceptance remains the next product task.
