# WASM material spike (native 634 shaded and textured triangle fills)

Isolated experiment for [docs/WASM_MATERIAL_INVESTIGATION.md](../../docs/WASM_MATERIAL_INVESTIGATION.md). Not a browser client; it adds nothing to the native product. Sibling of [wasm-triangle](../wasm-triangle/README.md), which covers the flat-colour fill.

Requires JDK 21, Python 3, Node.js 18+, Chromium and the upstream Gradle wrapper (or installed Gradle). No npm packages.

`tools/extract_material_closure.py` copies, from a locally supplied native source tree, the `Class109` field block, constructor and the eight methods reachable from `method1022` (palette-shaded), `method1027` (RGB Gouraud), `method1024` (single texture) and `method1020` (three-layer texture), plus `Class6.method206`, verbatim into the ignored `build/generated-src/`, beside generated stand-ins for `ha_Sub1`, `Class167` and `Class126`. The extractor **fails closed**: any reference to a member outside its explicit allow-list aborts the run and names the member. The same original scene (original geometry, original synthetic palette and textures in `SynthAssets`) then runs against the real jar bytecode (through the jar's own texture-cache code), the extracted source on the JVM, and TeaVM WasmGC in headless Chromium. **Nothing native is committed and no Jagex asset is used.**

```bash
U=/absolute/path/to/upstream/runelite-client
JAVA_HOME=/path/to/jdk21 GRADLE_USER_HOME=/path/to/.gradle UPSTREAM_GRADLEW=$U/gradlew \
  bash experiments/wasm-material/run.sh $U/client/src $U/client/build/libs/void-client-0.2.0_a2.jar
```

The run exits nonzero on any failed extraction, closure audit, compile, JVM run, Gradle/TeaVM build, browser error or any hash, count or control mismatch. Self-test: `MATERIAL_SELFTEST_MUTATE=browser-hash|missing-browser|zero-timing|flat-standin|duplicate-case|nan-timing|control-equal` must fail.

Scenes (`shaded`, `gouraud`, `tex1`, `tex3`, `mixed`; 980 triangles each at 765×503 and 1280×800): perspective height-field, depth-crossing triangles, edge-clipped triangles, translucent and fog-tinted triangles, random small triangles, and in the textured scenes about one in ten triangles referencing an unloaded texture so the native null-texture fallback runs. Controls re-render with a changed palette/texel variant; the pixels must change identically on all three runtimes.

Outputs (all ignored): `build/evidence.json`, `build/toolchain.json` (digests, closure), `build/closure.json`, `build/synthetic-material.png`.

Third-party: TeaVM 0.16.0 and `teavm-jso` (Apache-2.0), fetched by Gradle. Generated native files keep the JODE header and a provenance banner with the source SHA-256.
