# Original model decoding in WasmGC — 17 October 2026

Five original encoded old-format models now decode to the same counts, vertices, faces and colours in the real native client jar, an extracted Java closure and TeaVM WasmGC. The expected arrays come from separately declared original geometry. This adds a bounded decoder gate to the earlier raster/projection/clipping work; it does not render a decoded model or port a client.

## Boundary and provenance

The [new experiment](../experiments/wasm-model-decode/README.md) extracts unchanged `Class124.method1103`, its byte-array constructor, four Packet readers plus its byte-array constructor, and the XOR helper. Source digests and exact spans are checked before extraction. The closure copies **236 native span lines**; its bounded body totals **283 lines including declarations/adapters**, with 32 fields/counters. Limits remain 350 body lines and 40 fields.

The constructor retains the native format dispatch. New-format `method1106` and two Packet bad-magic writer paths are explicitly labelled, counted throwing adapters. All extracted/browser positive cases report zero adapter calls. The native jar runs its original class initialization, including Packet/Node helpers; the extracted classes omit unrelated members and those initializers. Equality is scoped to the observed decoder output, not initialization side effects or all class behaviour. Native adapter counters are not measured.

No generated native source, compiled output, cache data or proprietary model is committed. The frozen jar input remains local with SHA-256 `ac6e2671ed548c73ad4dcaf8e4446789f29c2780236059de12e6132795a6f918`. The [sanitized evidence](evidence/wasm-model-decode-20261017.json) records native inputs/spans, toolchain, output hashes, all experiment/reused-tool fingerprints and decoded-array hashes.

## Cases and checks

| Original fixture | Encoded bytes | Purpose |
| --- | ---: | --- |
| triangle | 33 | Type-1 face and unsigned colour stored as signed short |
| strip | 55 | Face-index transitions 1, 2, 3, 4, then 1 |
| signed-smart boundaries | 288 | One/two-byte positive/negative deltas, range edges and explicit zero deltas |
| perturbed vertex | 33 | Exactly one native Y coordinate changes |
| perturbed colour/index | 55 | Exactly one native colour and face index change |

Every runtime must report exactly these five case names. Every array element and count is compared with the original design, including explicit unsigned-to-signed colour conversion. The native run constructs the real jar's `Class124` by reflection on a classpath containing no extracted model class. The extracted JVM compile has no native jar. The browser executes the extracted decoder on original encoded bytes; expected arrays are never sent to the page.

Coordinator review tightened exact case-set validation and added reproducible provenance recording, then rebuilt the full pipeline and verified all 15 experiment fingerprints. Native JVM, extracted JVM and Chromium each pass all five cases. Four deliberate corruptions fail inside the checker with exit 1: native vertex versus design, extracted vertex, browser face index and browser colour. Argument-validation failures do not count as controls.

The measured WasmGC module is **36,749 raw bytes**; runtime JavaScript is **17,268 bytes**. Python-standard-library gzip level9 with mtime0/no filename produces 13,636 and 6,091 bytes respectively on this host. Those normalized measurements differ from the shell gzip header/implementation measurements retained in the private log. They are fixture payload observations, not a complete-client size or performance estimate. The actual toolchain is Java21.0.12.1, TeaVM0.16.0, Node26.11.1 and Chromium153.0.8010.52 on this host.

## Limits and next decision

Only old-format, untextured geometry with optional flags clear is covered. New-format models, texture/priority/alpha/label streams, normals, lighting, animation, scene construction and rendering integration remain unproven. Native readers perform unchecked array accesses; the experiment offers no safe arbitrary-file/cache import. Original fixtures are small and fixed.

An initial checker incorrectly required distinct colours on single-face models; its rule was corrected without changing the decoder. An earlier corruption command failed on placeholder input paths and is excluded from successful controls. Worker evidence was archived before the coordinator's final rerun; failed attempts remain private.

The next small uncertainty is whether these decoded arrays can feed the existing flat-face raster proof through a documented minimal adapter, while preserving the native render calculations and acknowledging that the full model constructor remains outside the closure. Do that before attempting real asset imports, broad model versions, network/storage or a browser architecture. Native Deck development remains primary; this proof stays on draft PR27.
