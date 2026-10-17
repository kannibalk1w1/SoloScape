# WASM clipping with general matrix and adapter inputs — 17 October 2026

The original clipping matrix now has 28 rows: the earlier 18 plus ten rows for five new fixtures at 765×503 and 1280×800. Frozen native jar, extracted Java and TeaVM WasmGC agree on camera/projected arrays and colour/depth hashes. The separate ten-case default face proof still passes. No native method, retained field or closure budget was added.

The new fixtures use the existing camera-1 input design: a nontrivial model rotation and view matrix that takes `method654`'s general composition branch. This is a synthetic matrix-path check, not integration with the real game's camera/platform state.

| Added fixture at each size | Required result |
| --- | --- |
| General matrix, one vertex behind | quad, 2 measured extracted fills |
| Reversed winding, same inputs | cull, 0 fills, different native output |
| General matrix, two behind | triangle, 1 fill |
| Alternate mask bit, same quad | 2 fills, native temporary short-array state retained |
| Non-null float-array input, triangle | 1 fill, native temporary short-array state retained |

Every row records requested camera/variant and exact binary32 matrix bits. A separate Python oracle derives composition, bounded projection, camera arrays, facing and fill expectations using explicit float32 operation order and in-range integer truncation. It also checks that recorded matrices match the requested design. Native bytecode output is compared element for element, rather than treating a case name as proof that a branch ran. The two other native auxiliary model arrays remain null in this harness; the oracle's camera-buffer rule is scoped accordingly.

Actual extracted JVM and Wasm fill counts equal the independently derived counts in all cases. Native counters remain absent. The camera-1 rows yield four quads and four triangles across both sizes, with 12 actual extracted fills. Six coordinator corruption controls reach a checker `FAIL` with exit 1: output count, fill count, projected element, visible crossing, camera-1 projection and variant cleanup state. No invalid CLI argument is counted as a rejection test.

Haiku implemented the bounded cases/checker; coordinator review clarified the auxiliary-array and finite-cast scope, rebuilt both positive pipelines and verified every recorded experiment-source fingerprint against the final files. Native spans remain 574 Class64 lines/59 fields, with the same disclosed two instrumentation lines. The clip fixture produces 87,400 raw Wasm bytes plus 17,268 bytes runtime JS. Payload sizes are not complete-client size or performance estimates.

[Evidence and exact tool/input hashes](evidence/wasm-general-clipping-20261017.json). [Reproduction](../experiments/wasm-face/README.md). The [earlier camera-0 proof](WASM_CLIPPING_PROOF_20261017.md) remains evidence for its dated scope.

Limits: five general-matrix fixtures do not exhaust arbitrary matrices, flags, overflow, Java cast saturation/NaN semantics or all model layouts. No 49.99 fixture, independent polygon-intersection re-render, real assets/model decoding, complete scene, AWT replacement, browser input/network/storage, FPS or Deck acceptance. Native face-loop exceptions remain swallowed by the original code. Keep this on draft PR27 and audit a single decode/model boundary before any further closure expansion.
