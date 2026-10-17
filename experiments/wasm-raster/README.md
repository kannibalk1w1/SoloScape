# Bounded WASM raster proof (native 634 face-edge kernel)

Isolated experiment for [docs/WASM_RASTER_POC.md](../../docs/WASM_RASTER_POC.md). It is not a browser client and adds no runtime dependency to the native product.

Requires JDK 21, Python 3, Node.js 18+, Chromium and the upstream Gradle wrapper (or installed Gradle). No npm packages are needed.

Inputs are read from absolute local paths and nothing native is committed: `tools/extract_face_kernel.py` writes the verbatim `ha_Sub1.method3636` body into the ignored `build/` directory at build time.

Run from the repository root with `JAVA_HOME` set to a JDK 21 directory (this is required; there is no default path):

```bash
JAVA_HOME=/path/to/jdk21 bash experiments/wasm-raster/run.sh \
  /absolute/path/to/upstream/runelite-client/client/src/ha_Sub1.java \
  /absolute/path/to/upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar
```

Build tool: the wrapper uses `upstream/runelite-client/gradlew`, run through `bash` because that checkout does not mark it executable. If that file is missing, it falls back to an installed `gradle` invoked directly. Neither is a `bash gradle` call. Set `UPSTREAM_GRADLEW` to point elsewhere if needed.

The wrapper runs, in order:

1. **Closure audit**: compiles the generated kernel with JDK 21 and no jar on the classpath. Only six `int`/`int[]` fields and two stub types (`aa`, `aa_Sub3`) are synthesised.
2. **JVM verbatim**: runs the generated kernel on the JVM.
3. **JVM native reference**: runs the real `ha_Sub1.method3636` bytecode from the client jar, via reflection and `Unsafe.allocateInstance`, with no constructor (its renderer needs a live `Canvas`).
4. **TeaVM 0.16.0 WasmGC**: compiles the verbatim kernel, the original-geometry scene and the Canvas `ImageData` adapter.
5. **Headless Chromium**: an ephemeral loopback server (`tools/serve_loopback.py`, port chosen by the OS, positive readiness probe on the page marker) serves only the generated output directory. The wrapper fails if Chromium exits nonzero, times out (`BROWSER_TIMEOUT`, default 180 s), or the DOM has no result.
6. **Validation**: `tools/check_evidence.py` requires both 765×503 and 1280×800 from all three sources (native jar bytecode, extracted JVM, browser) to match exactly, and writes `build/evidence.json` with hashes, timings and input digests. Any missing or mismatched result exits nonzero.

Scene: a triangular span mask and 6000 fixed-seed edges with opaque, alpha-blend and additive modes, at 765×503 and 1280×800. Geometry comes from an integer LCG. No cache data, assets or network are used.

Self-test for the rejection path: `RASTER_SELFTEST_MUTATE=browser-hash` or `missing-browser` must make the run fail. Forcing `CHROMIUM=/bin/false` or `/bin/true` exercises the browser-failure and no-result paths.

Known caveats: the hash is FNV-1a over 32-bit words, not a cryptographic digest. The browser timings use performance.now through a private CDP pipe, with no virtual-time budget. They are host micro-scene measurements. The reflection-based native reference is for correctness, not timing. The runner also captures an original synthetic-scene PNG in the ignored build directory.

## Pixel transfer comparison

Set `RASTER_ENTRY=TransferProbe` before the same command to compare per-pixel JavaScript calls, automatic primitive-array copying and a reusable direct NIO buffer. Each variant converts the same ARGB pixels to RGBA. The run checks both transferred-word and Canvas readback hashes, warms up once and measures six samples per variant at both resolutions. Results appear in `build/evidence.json` under `transfer_comparisons`.

The direct path still copies the native `int[]` framebuffer into the direct buffer. It avoids per-pixel JavaScript calls; it does not turn a Wasm GC array into zero-copy linear memory. See [the measured comparison](../../docs/WASM_TRANSFER_INVESTIGATION.md).
