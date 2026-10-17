# Decoded original model to browser framebuffer — 17 October 2026

Original encoded tetrahedra now pass through the actual old-format model decoder, then the existing native projection/culling/flat-fill calculation, with matching results in the native client jar, extracted JVM and TeaVM WasmGC. This connects the earlier isolated decoder and raster proofs. It is not a playable web client and remains on draft PR27.

## Boundary

The [experiment](../experiments/wasm-decoded-face/README.md) reuses both existing extractors unchanged. They run into separate directories, then compose15 generated files without name collisions. The same small original adapter copies decoded vertex/face/colour arrays into the previous flat-face fixture. Native compilation sees only the frozen client jar; extracted/browser compilation sees only extracted model classes. The full native model constructor remains excluded; the native reference still uses the prior Unsafe-allocated rendering context.

The three encoded models contain64,66 and64 original bytes. One changes a vertex by200 units; another changes face0 colour from0x8000 to0x1234. Expected decoded arrays derive from the original geometry design. The65,536-entry palette is an original synthetic formula, not native HSL lighting or cache appearance data. No cache, Jagex model, generated native source or binary module is committed.

## Measured result

Coordinator reran the complete offline build and browser pipeline after review, then verified all29 experiment/reused-tool source fingerprints. Three models × two cameras × two sizes (765×503 and1280×800) give12 cases in each runtime. Decoded arrays, projected coordinates, front/back counts, colour/depth hashes and coverage agree. Direct front-only fill reproduces the pipeline. Both perturbations change native output in every camera/size pair.

Extracted/browser counters report one adapter entry and zero illegal/stub/decode-stub calls; native counters are unavailable. Camera0's all-faces bypass changes the image at both sizes. Camera1's depth test already hides its back face, so bypass and culled images agree there; counts exercise selection, but that image is not a culling sensitivity control.

One canonical base-model camera1/1280×800 frame is presented with explicit RGBA conversion, row stride and Canvas ImageData. Native/extracted/browser presented hash and Canvas readback agree at`a0bf99a6`; its pre-conversion ARGB hash is also bound to the correct pipeline case. Four actual corruption controls exit1 inside the checker: decoded array, browser projection, browser frame hash and palette. [Sanitized provenance/results](evidence/wasm-decoded-face-20261017.json).

The measured module is107,301 raw bytes and36,674 bytes under Python gzip9/mtime0/no filename. Runtime JavaScript is17,268 raw/6,091 gzip bytes. These are this fixture's bytes, not a client-size estimate. Toolchain: Java21.0.12.1, TeaVM0.16.0, Node26.11.1 and Chromium153.0.8010.52. No timing/FPS benchmark was run.

![Original tetrahedron rendered by the decoded-model browser proof](screenshots/wasm-decoded-face-20261017/original-tetra-canvas.png)

## Decision

The narrow decoder-to-raster connection is credible. Native lighting/model construction, optional streams/materials/animation, clipping integration, real authorized assets and full scene state remain separate uncertainties. Continue with one small constructor/lighting dependency audit before expanding the closure; stop if it drags in broad cache/client globals. Keep native Deck work primary. No browser architecture, transport rewrite or public asset distribution follows from this result.
