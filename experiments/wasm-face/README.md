# WASM face spike (native 634 projected flat-face dispatch)

Isolated experiment for [docs/WASM_FACE_PROOF_20261017.md](../../docs/WASM_FACE_PROOF_20261017.md). Not a browser client; it adds nothing to the native product. It sits above [wasm-triangle](../wasm-triangle/README.md) (flat fill) and reuses that experiment's extractor helpers by import.

Requires JDK 21, Python 3, Node.js 18+, Chromium and the upstream Gradle wrapper (or installed Gradle). No npm packages.

`tools/extract_face_closure.py` copies, from a locally supplied native source tree, nine `Class64_Sub1` methods verbatim (`method654` projection with `i == -1`, `method650` face loop, `method643` face gates, `method635` flat dispatch, `method634`, `method632`, `method655`, `method629`, `method638`: 441 lines, 59 native instance fields) and the `Class109` flat fill (`method1018` → `method1026`, plus `method1023`) into the ignored `build/generated-src/`. Everything else is a labelled generated or hand-written stand-in:

- **Adapter (not verbatim):** `method657` is replaced by a same-signature guarded adapter (10 lines, state 2 only). It counts entries, throws on any other state, and reproduces the native state-2 effects on `aShortArray5311` (mask and `aFloatArrayArray5314` case) and `aByteArray5386`.
- **Counting stubs:** `method646` (clip branch), `method658` (lit branch), `ha_Sub1.method3720` (textured), `Class109.method1022/1024` and the wireframe line count and throw.
- **Glue:** a constructor and `harnessProject` that calls `method654(camera, null, -1, 0)`.
- Type stand-ins for `ha_Sub1`, `Class167`, `Class101(_Sub1)`, `Class126` (original synthetic palette) and the unused branch types.

The extractor **fails closed** on a changed nine-method set, more than 450 verbatim lines, more than 65 fields, more than 20 adapter lines, any unaudited callee, class or static member. The same original scene (a closed sphere and a cube, integer/rational geometry, per-face palette indices through an original synthetic palette) then runs against the real jar bytecode (reflection plus `sun.misc.Unsafe`), the extracted source on the JVM, and TeaVM WasmGC in headless Chromium. **Nothing native is committed and no Jagex asset is used.**

```bash
U=/absolute/path/to/upstream/runelite-client
JAVA_HOME=/path/to/jdk21 UPSTREAM_GRADLEW=$U/gradlew \
  bash experiments/wasm-face/run.sh $U/client/src $U/client/build/libs/void-client-0.2.0_a2.jar
```

The wrapper refuses missing or relative inputs, a non-21 JDK, and a jar or `Class64_Sub1`/`Class109` source whose SHA-256 differs from the audited files. It exits nonzero on any failed extraction, compile, JVM run, Gradle/TeaVM build, browser error or any mismatch.

Ten cases per runtime: two sizes (765×503, 1280×800), two cameras (a fast-path identity model matrix and a general rotated one), three adapter variants (mask clear, mask bit set, `aFloatArrayArray5314` non-null) and a perturbed-vertex control. The checker compares the projected x/y/depth integer arrays element for element and the colour/depth hashes, requires nonzero coverage and a culled back face, and rejects any stub or illegal adapter hit.

Self-tests (each must exit nonzero): `FACE_SELFTEST=` `jvm-vertex`, `browser-vertex` (one implementation gets a perturbed vertex), `illegal-state0|illegal-texture|illegal-lit|illegal-clip` (the extracted build enters the adapter or a stub illegally), and `browser-hash|browser-element|missing-browser|zero-coverage|counter-stub|counter-adapter|duplicate-case|control-equal|no-backface|missing-present|culling-equal` (evidence corrupted before the checker; `FACE_REUSE=1` reuses an existing `build/`).

Outputs (all ignored): `build/evidence.json`, `build/toolchain.json`, `build/closure.json`, `build/inputs.json`, `build/synthetic-face.png`.

Third-party: TeaVM 0.16.0 and `teavm-jso` (Apache-2.0), fetched by Gradle. Generated native files keep the JODE header and a provenance banner with the source SHA-256.
