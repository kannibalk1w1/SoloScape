# WASM pixel transfer investigation — 17 October 2026

The earlier edge-kernel prototype made one JavaScript call per pixel. Two reviewed runs of the same scene show that replacing those calls with bulk transfer reduces synchronous conversion/transfer/upload cost by roughly five times at 1280×800. This is an experiment-only presentation change; no native renderer or game code changed.

## What ran

`experiments/wasm-raster` now has an optional `TransferProbe` entry point. It uses the same locally extracted `ha_Sub1.method3636` kernel and original synthetic geometry as the earlier probe. Native jar, extracted JVM and browser source-frame hashes still agree. Each resolution compares three presentation paths, with one warm-up and six measured samples:

| Transfer path | 765×503 total median range | 1280×800 total median range |
| --- | ---: | ---: |
| Per-pixel JavaScript calls | 12.3–14.5 ms | 25.2–32.1 ms |
| Automatic primitive-array bulk copy | 2.3–2.7 ms | 4.8–6.6 ms |
| Reusable direct NIO buffer | 2.2–2.4 ms | 4.5–6.5 ms |

Ranges span the medians from two independent clean experiment builds/runs. They include RGB/alpha conversion, transfer and synchronous `putImageData`; they exclude scene rasterization, checksum/readback verification, compositor/display scheduling and allocation/setup performed before sampling. The canvas is sized once per resolution for all variants. These figures are not directly interchangeable with the earlier one-sample presentation measurements, which resized the canvas on presentation.

Host: Intel i7-14700HX, Chromium 153 headless with GPU disabled, TeaVM 0.16.0 WasmGC, JDK 21. Real `performance.now` via a private CDP pipe; no virtual-time budget. Power, thermal state and competing host load were uncontrolled. No Deck, Chromebook, actual display, browser frame-tail or full-client memory result is claimed. [Recorded inputs, hashes and samples](evidence/wasm-transfer-20261017.json).

## Correctness and memory boundary

All variants receive the same unchanged native `int[]` framebuffer. Converted RGBA words match across variants, and independent Canvas readback byte hashes agree at both resolutions. The validator rejects missing/duplicate variants, non-finite timings and transport pixel differences; a deliberately altered bulk-copy hash was rejected. Canvas may normalize alpha representation, so readback is compared between variants separately from the source-word hash.

TeaVM documents primitive-array copying and direct NIO buffer interop for WasmGC; `@JSByRef` is unsupported for WasmGC. The direct-buffer annotation was also inspected in the pinned 0.16.0 source artifact. [Official TeaVM interop documentation](https://teavm.org/docs/runtime/jso.html#passing-nio-buffers).

The direct path converts/copies Java array pixels into an explicitly little-endian direct `IntBuffer`, then passes an `@JSBuffer(INT32)` view. The JavaScript view respects its byte offset and length. This removes per-pixel host calls, but **one full-frame conversion/copy remains** because the native rasterizer writes a Wasm GC `int[]`. No unsupported array aliasing or production renderer rewrite is involved. View-creation overhead can fall below timer resolution; that is not a claim of zero total cost.

Bulk-array copying is almost as fast in these small runs and simpler. It can allocate a marshalled typed array per transfer. The reusable direct buffer is worth retaining as a comparison until allocation/long-session behavior is measured; neither path has been selected for a product runtime.

## Reproduce and next decision

Use the existing explicit local-source/JAR command from [the experiment README](../experiments/wasm-raster/README.md), with `RASTER_ENTRY=TransferProbe`. No cache data or native source bodies are committed; generated outputs remain ignored. Running the default entry retains the original edge probe.

This clears one presentation uncertainty. The [actual triangle investigation](WASM_RENDERER_INVESTIGATION.md) answers a different question. A full 634 model/scene, textures, lighting, animation, native UI, browser networking and durable saves still need separate evidence before a web-client architecture is chosen. Steam Deck/native remains primary.
