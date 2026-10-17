# WASM flat near-plane clipping proof — 17 October 2026

The isolated flat-face pipeline now includes native near-plane clipping. Eighteen original synthetic cases agree across the frozen native client jar, extracted Java on JDK 21 and TeaVM WasmGC in headless Chromium: projected/camera arrays, colour/depth framebuffer hashes, derived facing/output shape and measured extracted fill-entry counts. The earlier ten-case default face proof still passes. This is an opt-in experiment on draft PR27, not a game/model/scene port.

[Reproduction](../experiments/wasm-face/README.md). [Exact sanitized evidence](evidence/wasm-clipping-20261017.json). The [preceding source audit](WASM_CLIPPING_SPIKE_AUDIT_20261017.md) remains historical; its untested boundary is resolved only for the scope below.

| Case at each of 765×503 and 1280×800 | Required outcome |
| --- | --- |
| One vertex behind | clipped quad; 2 actual flat-fill entries |
| Two vertices behind | clipped triangle; 1 actual flat-fill entry |
| Reversed winding for either | camera-space cull; 0 fills |
| Exact near depth 50 | ordinary front triangle; 1 fill |
| 49.8 behind / 50.2 front crossing | integer depths 49/50; native colour and depth hashes visibly change |
| Whole model behind | bounds rejection, no array writes or fills |
| All-behind face with visible companion | one eligible zero-output clipped face, companion still fills |

Clipped facing uses the native camera-space 3D cross/dot predicate; ordinary faces use projected 2D area. The independent Python oracle derives expected eligibility/output counts from native arrays and refuses every intermediate integer overflow in its tested arithmetic. Actual extracted JVM/Wasm fill entries must match `2 × quads + triangles + ordinary front faces`. The native jar is uninstrumented: its fill/branch counts remain absent, and expectations are derived rather than presented as native measurements.

The closure adds only the 133-line `Class64_Sub1.method646` span: 574 native Class64 lines (cap 580), 59 retained instance fields (cap 65). Two disclosed harness lines count output shapes and flat-fill entries, one each in generated Class64/Class109; removing each must restore the exact native method span. Default mode contains neither counter. Lit/textured/material/wireframe paths remain counting refusals. Original source bodies and binaries stay in ignored local outputs.

Coordinator review required actual fill counts after the first pass only counted output-bin selection. The final positive/default pipelines were rebuilt after those changes; recorded experiment-source fingerprints match the final files. Four deliberate corruptions fail inside the checker: output-bin count, visible crossing, browser projection element and measured fill count. An earlier invalid control argument is retained privately and is not counted as a rejection test. Haiku also ran default checker controls and excluded-branch/state negatives; the final public evidence distinguishes the coordinator's four checked mutations.

OpenJDK 21.0.12.1, TeaVM 0.16.0, Chromium 153.0.8010.52 and Node 26.11.1. The clip WasmGC module is 85,449 bytes raw plus 17,268 bytes runtime JS. These are fixture payload sizes, not an estimate of a complete browser game. No frame-time or hardware performance measurement is claimed.

Limits: camera 0 fast path and mask0 adapter only; 49.99 is not tested (the integer geometry fixtures use 49.8/50.2 and float-exact 50); no independent polygon intersection re-render, no real cache/models/assets and no browser input/network/storage integration. Native `method650` swallows exceptions, so positive counters and native comparison establish these fixtures rather than arbitrary renderer correctness. This removes one narrow renderer uncertainty; AWT/RuneLite/platform integration remains unresolved.

Next, audit one bounded general-camera/adapter clipping case or a single model decode boundary before adding another closure. Do not turn this result into permission for a full browser client, renderer rewrite, WebGPU or moving WASM into the native release path.
