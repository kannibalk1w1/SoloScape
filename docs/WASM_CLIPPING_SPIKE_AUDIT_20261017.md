# WASM near-plane clipping boundary audit — 17 October 2026

**Source audit only.** No clipping port, browser run, benchmark or new rendering acceptance is claimed. This proposes a bounded next experiment after the [flat-face proof](WASM_FACE_PROOF_20261017.md); it does not widen that proof's existing all-vertices-in-front scope.

Claude Haiku inspected the source and frozen native bytecode. Coordinator review corrected the initial facing, threshold and field-count conclusions before publication. The unpublished draft is retained privately. No native source body or proprietary data is included here.

## Verified boundary

The existing harness refuses `Class64_Sub1.method646` through a counting stub. `method643` first identifies a clipped face using the projected-x sentinel **−5000**. It then computes a camera-space cross product and dot product, and calls `method646` **only if that dot product is positive**. Clipped faces therefore do have a facing test. The later projected 2D signed-area test applies to the ordinary path. A clip oracle must reproduce the 3D test, including Java signed-integer arithmetic, or constrain original fixtures to avoid overflow.

`method654` computes `bool_657_` from the model bound and the renderer near plane. `bool_658_` combines that result with the presence of the two auxiliary model arrays; under that condition it writes the camera-space arrays used by clipping. The near threshold `i_661_` comes from `ha_Sub1.anInt7482`. The existing original fixture sets that near plane to **50**, not5000. Projection uses a float-depth threshold; clipping consumes integer camera-depth arrays, so a 49.99/50 pair also needs explicit truncation accounting.

The model bounds/frustum checks can reject an all-behind model before its face loop. To exercise a zero-output clipped face, include another visible face so the overall model passes those checks, and independently prove the camera-space facing predicate. Do not assume every behind face enters the clip method.

Source anchors in the pinned client: `Class64_Sub1.method643` around1359–1403; `method646` around1897–2029; `method654` around2488 onward. Frozen native jar SHA-256: `ac6e2671ed548c73ad4dcaf8e4446789f29c2780236059de12e6132795a6f918`. Bytecode inspection checked field/callee names, not arithmetic equivalence.

## Measured closure delta

Coordinator field extraction against the actual existing adapter/glue yields59 retained `Class64_Sub1` fields both before and after adding the clipping body: **no new fields**. The existing initialization already retains the clipping scratch arrays. Keep the field budget65 until a real compilation demonstrates a reason to change it.

The clipping body contributes133 verbatim lines:441 becomes574. A future bounded prototype would need an explicit method-line budget around580 instead of450. Native method bodies remain generated in ignored directories from the user's checkout. The measured delta is recorded privately in `.runtime/clip-coordinator-delta-20261017.json`.

Existing fill stand-ins cover the method's referenced types. Lit/textured branches must remain counting refusals. This is a dependency inspection, not proof that the expanded stand-ins compile and execute correctly.

## Smallest useful experiment

1. Add the one clipping body to the isolated generated closure. Keep original models/colours, no cache, and fail on every lit/textured/material branch.
2. Exercise the existing projection and camera-buffer setup, rather than only preloading the clipping scratch arrays. A direct-buffer experiment would prove only the clipping kernel.
3. Use front controls, one-behind quads, two-behind triangles, reversed winding, exact-near vertices, threshold crossings and a qualified zero-output face. Independently derive camera-facing eligibility before predicting entries or output counts.
4. Compare native jar, extracted JVM and WasmGC framebuffer/depth results. Require positive counters for each intended clipped shape and fail on excluded branch hits. Native reference counters are not instrumented; derive expected entries from its camera/projection state and an independent oracle.
5. Show a visible native output change when moving a vertex across the plane. A clipped reversed-winding face must be rejected by the native camera-space predicate; never require it to fill. Test all-behind model rejection separately from face-level zero output.

Stop if the closure requires real assets, palette/material decoding, lit/textured branches, an unexplained field increase, or a new scene/client architecture. Do not infer game FPS or browser-client feasibility from this small kernel.

## Remaining uncertainty

Actual clipping arithmetic, precision/rounding across runtimes, expanded stand-in compilation, projection-to-clip integration and meaningful native sensitivity controls remain untested. No build or experiment was run for this audit. The earlier face proof remains evidence only for its published scope. Native Steam Deck work remains primary; this document stays on draft PR27.
