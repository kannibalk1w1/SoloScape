# WASM triangle spike (native 634 flat-colour triangle fill)

Isolated experiment for [docs/WASM_RENDERER_INVESTIGATION.md](../../docs/WASM_RENDERER_INVESTIGATION.md). Not a browser client; it adds nothing to the native product.

Requires JDK 21, Python 3, Node.js 18+, Chromium and the upstream Gradle wrapper (or installed Gradle). No npm packages.

What it does: `tools/extract_triangle_closure.py` copies, from a locally supplied native source tree, the field block, the constructor, `method1018` (flat-colour triangle set-up, clipping, scan conversion) and `method1026` (depth-tested span fill) of `Class109.java` verbatim into the ignored `build/generated-src/`, beside two tiny generated stand-ins (`ha_Sub1`, `Class167`). The same original scene then runs against the real jar bytecode, the extracted source on the JVM, and TeaVM WasmGC in headless Chromium. **Nothing native is committed.**

```bash
U=/absolute/path/to/upstream/runelite-client
JAVA_HOME=/path/to/jdk21 GRADLE_USER_HOME=/path/to/.gradle UPSTREAM_GRADLEW=$U/gradlew \
  bash experiments/wasm-triangle/run.sh $U/client/src $U/client/build/libs/void-client-0.2.0_a2.jar
```

`UPSTREAM_GRADLEW` is run through `bash` (the checkout does not mark it executable). `CHROMIUM` and `BROWSER_TIMEOUT` (default 240 s) can be overridden. The run exits nonzero on a failed extraction, compile, JVM run, Gradle/TeaVM build, browser error/timeout, or any hash/triangle-count/coverage mismatch. Self-test: `TRIANGLE_SELFTEST_MUTATE=browser-hash|missing-browser|zero-timing` must fail.

Browser timing uses a private CDP pipe and real `performance.now()` (no virtual time); the loopback server serves only `build/teavm-out`. Outputs: `build/evidence.json`, `build/closure.json` (reachable methods, call sites), `build/synthetic-mesh.png`.

Scenes (original integer-LCG geometry, scaled to the frame, no models or assets): `single` (one triangle), `single64` (the same triangle 64× at decreasing depth, so it is timeable), `mesh` (2,180 triangles: perspective height-field, two depth-crossing triangles, edge-clipped triangles, translucent overlays, random overlapping small triangles).

Third-party: TeaVM 0.16.0 and `teavm-jso` (Apache-2.0), fetched by Gradle. The generated `Class109.java` keeps the native file's JODE header and a provenance banner with the source SHA-256.
