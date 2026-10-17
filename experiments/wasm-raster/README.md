# Bounded WASM raster proof (native 634 face-edge kernel)

Isolated experiment for [docs/WASM_RASTER_POC.md](../../docs/WASM_RASTER_POC.md). It is not a browser client and adds no runtime dependency to the native product.

Inputs are read from absolute local paths and nothing native is committed: `tools/extract_face_kernel.py` writes the verbatim `ha_Sub1.method3636` body into the ignored `build/` directory at build time.

```bash
bash experiments/wasm-raster/run.sh \
  /absolute/path/to/upstream/runelite-client/client/src/ha_Sub1.java \
  /absolute/path/to/upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar
```

The wrapper runs, in order:

1. **Closure audit**: compiles the generated kernel with JDK 21 and no jar on the classpath. Only six `int`/`int[]` fields and two stub types (`aa`, `aa_Sub3`) are synthesised.
2. **JVM verbatim**: runs the generated kernel on the JVM.
3. **JVM native reference**: runs the real `ha_Sub1.method3636` bytecode from the client jar, via reflection and `Unsafe.allocateInstance`, with no constructor (its renderer needs a live `Canvas`).
4. **TeaVM 0.16.0 WasmGC**: compiles the verbatim kernel, the original-geometry scene and the Canvas `ImageData` adapter.
5. **Headless Chromium**: serves only the generated output directory on `127.0.0.1` and reports hashes and timings from the page.

Scene: a triangular span mask and 6000 fixed-seed edges with opaque, alpha-blend and additive modes, at 765×503 and 1280×800. Geometry comes from an integer LCG. No cache data, assets or network are used.

Known caveats: the hash is FNV-1a over 32-bit words, not a cryptographic digest. The browser timings come from a headless run with a virtual-time budget, and the reflection-based native reference is for correctness, not timing.
