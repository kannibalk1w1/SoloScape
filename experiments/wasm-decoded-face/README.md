# WASM decoded face bridge (original encoded model -> real Class124 decode -> existing face math)

Isolated, draft experiment on DRAFT27 only. It stitches two bounded proofs: [wasm-model-decode](../wasm-model-decode/README.md)
(old-format `Class124(byte[])` decode of original encoded bytes) and [wasm-face](../wasm-face/README.md) (native
`Class64_Sub1.method654` projection, culling and flat fill through `FaceRig`/`NativeFace.JarRig`). It adds nothing to the
native product, does not port a model constructor or lighting, and makes no FPS or full-client claim.

Pipeline, for three original tetrahedra (64, 66 and 64 bytes, `tetra`, `tetra_vertex`, `tetra_colour`):

1. `tools/encode_bridge_fixtures.py` writes each design (vertices, outward faces, colours) and encodes it with the existing
   `encode()` from `wasm-model-decode/tools` (imported by path, unmodified). Expected arrays come from the design only.
2. Native: the frozen jar's real `Class124(byte[])` decodes the bytes (reflection-free, package access in the default
   package); `DecodeMesh` copies the decoded X/Y/Z and A/B/C arrays into `FaceMesh.custom` and sets `colourIndex` from the
   decoded short `& 0xffff`; `BridgeScene` runs the projection through `NativeFace.JarRig` (the prior Unsafe-allocated
   context and model, unchanged).
3. Extracted JVM and TeaVM WasmGC: the same `DecodeMesh`, compiled against only the generated `Class124`, then
   `ExtractedRig` over the extracted face closure.
4. The three runtimes project 3 fixtures x 2 cameras x 2 sizes (765x503, 1280x800) = 12 cases each, and present one
   1280x800 camera-1 frame (RGBA words, `w*4` byte rows, `ImageData` on a canvas as in wasm-face).

`run.sh` runs both existing extractors **unchanged** into separate directories (each writes `closure.json` next to its
output, so they cannot share one), checks their budgets and digests, and composes their generated files with no name
collision (15 files: 12 face, 3 decode). The adapter and scene are the only new original code under `src/`.

## Shared sources and adapters

- Reused read-only: `FaceMesh`, `FaceRig` (with `FaceCase`/`Observed`), `FaceScene` (`fnv`, `covered`) and `FaceMesh.palette`, `FaceCounters`,
  `ExtractedRig`, and for the native run `ClipScene` and `NativeFace` (`JarRig`). They are copied into `build/` and
  byte-compared with their sources in the provenance record. Nothing in `wasm-face` or `wasm-model-decode` is edited.
- New: `DecodeMesh` (field-only adapter; no flags, texture, priority or label state), `BridgeScene` (the `FaceScene.run` checks
  on a decoded mesh, also emitting the decoded arrays), `BridgeRun` (the shared 12-case matrix and presented frame), and
  the three entry points `NativeBridge`, `ExtractedBridgeJvm` and `BridgeProbe`.
- Compile separation: the native run compiles `DecodeMesh` against `client.jar` only; the extracted and browser runs compile it
  against the generated `Class124` only; no generated model classes are on the native classpath and no jar on the extracted one.
- Palette: the existing original synthetic 65,536-entry palette (`FaceMesh.palette`), **not** the native HSL lighting or
  actual cache appearance data. The checker recomputes that palette from its formula and compares the FNV of each runtime's copy.
- Not included, as before: `Class64_Sub1` model constructor (still excluded), `JarRig`'s Unsafe allocation of the context, and
  the new-format `Class124.method1106` path (it throws and is counted in the extracted run; no new-format fixture is run).

## Checks (tools/check_bridge_evidence.py)

- Exact case set and matching camera/size metadata per runtime; decoded counts, maxVertexPlusOne, X/Y/Z, A/B/C and colour shorts against the original design.
- Front/back recomputed from the projected coordinates with the scene's formula; each case has at least one front and one back
  face, nonzero coverage, and a near-plane minimum of at least 50.
- Projected X/Y/Z element for element, plus pipeline colour/depth FNV, direct re-render, all-faces, coverage and distinct counts,
  across native, extracted and browser.
- Counters: the extracted and browser runs have one adapter entry, no illegal state, no stub or decode-stub call. The native jar
  reports none (absent, `null`).
- Perturbations visibly change native output (tetra_vertex moves a vertex by 200 units; tetra_colour changes face 0's colour index
  from 0x8000 to 0x1234) in both cameras and both sizes.
- The all-faces bypass must differ from the culled frame in at least one canonical case per size (see the limit below).
- Presented frame: its ARGB hash must equal the canonical tetra/camera1/1280x800 pipeline case; native, extracted and browser RGBA FNV agree, and browser canvas readback equals its presented FNV. Native camera0/1 projected arrays must differ at both sizes.

Controls (each run inside the checker and must exit 1 with a `FAIL:` line; `run.sh` runs them at the end):

```bash
BRIDGE_REUSE=1 BRIDGE_SELFTEST=decoded-array|browser-projected|browser-frame|palette bash run.sh <same args>
```

- `decoded-array`: native decoded y[0] + 1 -> FAIL at the design comparison.
- `browser-projected`: browser projX[0] + 1 -> FAIL at the cross-runtime projection comparison.
- `browser-frame`: browser case hash changed -> FAIL at the direct re-render comparison (the first hash check it hits).
- `palette`: browser palette FNV changed -> FAIL at the original-palette check.

## Usage

```bash
U=/absolute/path/to/upstream/runelite-client
JAVA_HOME=/absolute/path/to/jdk21 UPSTREAM_GRADLEW=$U/gradlew \
  bash experiments/wasm-decoded-face/run.sh $U/client/src /absolute/path/to/frozen-client.jar
```

Requires JDK 21, Python 3, Node.js 18+, Chromium and the upstream Gradle wrapper, all offline. The TeaVM plugin 0.16.0 must be in
the offline Gradle cache (`GRADLE_USER_HOME` defaults to the checkout's `.gradle`; set it explicitly when reusing a different local cache). Logs go to the
ignored private `.runtime/wasm-decoded-face-20261017/` (checker log, controls, provenance.json); generated output stays in `build/`.

## Limits

- Old-format, flat, untextured tetrahedra only (texture count 0, all optional flags 0). Three fixtures, all original synthetic.
  No cache data, no Jagex asset and no arbitrary input. The decoder has no bounds checks; no untrusted or truncated input is run.
- Camera 0 and camera 1 transforms (fixed matrices from wasm-face), mask0 adapter variant only. No clipping, no
  maskbit/floatarr variants, no lit/textured/material branch, no near-plane crossing case.
- Culling and bypass: camera 0 has two front and two back faces, and the all-faces bypass differs from the culled frame. Camera 1
  has three front and one back face, and the depth test already hides that back face, so its bypass equals the culled frame at
  both sizes. The checker records this (`bypassEqualToCulledFrame`) instead of failing it; the culling is exercised by counts.
- Native face-loop exceptions remain swallowed by the original method, so agreement establishes only these fixtures; native
  counters do not exist and their absence is checked, not measured.
- The browser presentation covers one frame (1280x800, camera 1, base tetrahedron). No Deck, FPS or hardware acceptance is claimed.
- No performance numbers are reported. Module sizes are recorded in `build/provenance.json` and the private log.
