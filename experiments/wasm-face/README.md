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

## Opt-in near-plane clipping experiment

`FACE_CLIP=1` selects a separate `build-clip/` result directory and adds only the native `Class64_Sub1.method646` body to the existing generated closure. The Class64 budget is 574 native lines (cap 580), 59 instance fields (cap 65), plus one disclosed clip-output counter line. Clip mode also adds one disclosed flat-fill entry counter to generated `Class109.method1018`; deleting each counter must restore its exact native method span. Default extraction contains neither counter and retains its earlier scope.

Original synthetic cases at 765×503 and 1280×800, 28 rows per runtime. The nine camera-0 cases (fast path, mask0 adapter) cover one-behind quads, two-behind triangles, reversed winding, exact near-plane depth 50, 49.8/50.2 threshold crossings, whole-model rejection and an all-behind face with a visible companion. Five camera-1 cases take the general matrix path of method654 (not the fast path): a one-behind quad, its culled reverse, a two-behind triangle, a one-behind quad with the maskbit adapter (`anInt5316` bit 0x1000) and a two-behind triangle with the floatarr adapter (non-null `aFloatArrayArray5314`). Each row records its requested camera and variant. The checker rejects a row whose recorded matrices are not the design for its requested camera, and whose adapter state (`aShortArray5311` cleared only for mask0) differs from the requested variant. Native jar, extracted JVM and WasmGC must match projected/camera arrays and framebuffer/depth hashes. An independent Python oracle re-implements method654's expression order with float32 rounding from the recorded model and view matrices and the vertices. It derives camera arrays, projections, the model and screen bounds, eligibility, clip outputs and fill entries, and refuses any intermediate integer overflow. Actual extracted and Wasm fill-entry counts must match the derived counts. Native counters remain absent; their expectations are derived, not measured. The threshold crossing and the camera-1 reversal must visibly change native output.

Camera-1 design: the model matrix is 16384 × [[0.8, 0, 0.6], [0, 1, 0], [−0.6, 0, 0.8]] and the view matrix has rows (1/16384, 0, 0), (0, 12/13/16384, −5/13/16384), (0, 5/13/16384, 12/13/16384) with depth offset 2400. Camera space is therefore X = 0.8x + 0.6z, Y = (12/13)y − (5/13)w and depth = 2400 + (5/13)y + (12/13)w, where w = −0.6x + 0.8z. The fixtures invert this for targets at depth 800 (front) and depth 30 (behind): quad X = −80, 80, 0 and triangle X = 0, −40, 40. The integer model vertices are rounded, and the oracle reports integer camera depths 799 (front, truncated from just under 800) and 30 with X within one unit of the targets. Winding: quad `{1,0,2}` is eligible (triple product > 0) and `{0,1,2}` is culled; triangle `{0,1,2}` is eligible.

```sh
FACE_CLIP=1 JAVA_HOME=/absolute/path/to/jdk21 \
  UPSTREAM_GRADLEW=/absolute/path/to/upstream/gradlew \
  bash run.sh /absolute/path/to/client/src /absolute/path/to/frozen-client.jar
```

`FACE_REUSE=1 FACE_CLIP=1 FACE_SELFTEST=<name>` corrupts the collected evidence before the checker runs and must exit nonzero with a `FAIL:` message: `clip-count`, `clip-fill-count` (a measured fill count), `clip-browser-element`, `clip-visible`, `clip-camera1-projection` (one camera-1 browser projection element) and `clip-variant-state` (a maskbit row reporting the mask0 adapter state). A bad command-line argument is not a control: it exits with argparse status 2 and is never counted as a rejection. `illegal-clip` is a refusal in clip mode because that mode deliberately includes clipping.

Limits: camera 0 (fast path) and camera 1 (general path) only, with the adapter variants listed above. Five camera-1 cases spot-check the camera and adapter interaction; they do not exhaust it. No 49.99 depth fixture, no independent clipped-polygon re-render, no lit/textured/material branches, no assets or real model/scene/client port. Native face-loop exceptions remain swallowed by the original method, so agreement plus positive instrumentation establishes only these fixtures. No browser, Deck FPS or hardware acceptance is claimed.
