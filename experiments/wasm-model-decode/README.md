# WASM model decode: decode-only equality proof (old format, flat untextured)

Isolated, draft experiment. It proves only that the **old-format** `Class124(byte[])` decode path produces the same
vertex, face, colour and count arrays on the native jar, on the extracted JVM closure and in TeaVM WasmGC, over five
**original synthetic** encoded models whose expected arrays come from an independent design. It does not render, does
not run a full model or client, and makes no performance claim. It adds nothing to the native product.

Requires JDK 21 (`.runtime/jdks/jdk21`), Python 3, Node.js 18+, Chromium and the upstream Gradle wrapper, all offline.
Tooling reused by path, without edits: `../wasm-face/tools/browser_probe.mjs` (headless Chromium over a loopback URL)
and `../wasm-face/tools/serve_loopback.py` (loaded by `tools/serve_decode.py`).

```bash
U=/absolute/path/to/upstream/runelite-client
JAVA_HOME=/absolute/path/to/jdk21 UPSTREAM_GRADLEW=$U/gradlew \
  bash experiments/wasm-model-decode/run.sh $U/client/src /absolute/path/to/frozen-client.jar
```

The wrapper checks the frozen jar digest (`ac6e2671…f918`) and the three native source digests, then runs: verbatim
closure extraction, fixture encoding, a standalone `-Xlint:all` compile of the extracted closure (no jar on the
classpath), the extracted JVM run, the native-jar reflection run, the offline TeaVM 0.16.0 WasmGC build, the headless
browser run (loopback only), the checker and exact tooling/source provenance. It exits nonzero on any failure. Logs go to
`.runtime/wasm-model-boundary-20261017/` (private, ignored). Generated output stays in `build/` (ignored).

Controls (checker only, reuse the finished build, each must exit nonzero with a `FAIL:` line):

```bash
DECODE_REUSE=1 DECODE_SELFTEST=native-design|extracted-vertex|browser-face|browser-colour bash run.sh <same args>
```

## Provenance

`tools/extract_decode_closure.py` copies these native spans **verbatim** (line numbers in the audited sources):

- `Class124.java`: `method1103` (226–423, old format) and `Class124(byte[])` (830–837; its dispatch is kept).
- `Packet.java`: `Packet(byte[])` (757–760), `readUnsignedShort` (88–93), `method3362` (356–362), `readUnsignedByte` (643–647), `readByte` (649–653).
- `Class348_Sub21.java`: `method2955` (69–71, the XOR helper).

Audited digests (sha256): `Class124.java` `26284febbb937e5a…4d3e`, `Packet.java` `3e217a1d08e82e2f…960d`,
`Class348_Sub21.java` `2b9ab115d669baaf…b7d7`. The extractor fails closed on a different digest, a span whose first or
last line moved, an unbalanced span, a body over 350 lines or more than 40 declared fields. The per-span hashes and the
declared-field list with native line numbers are in `build/closure.json`. Only fields and counters the spans reference
are declared (32 in the last run).

## Adapters (not native text, all labelled `ADAPTER` in the generated source)

- `Class124.method1106` (new format, footer ends `-1,-1`) is an explicit throw. It counts into `newFormatStubCalls`.
  No new-format fixture is run: the native jar would run its real new-format parser, so such a comparison is not a
  decode-only equality. The dispatch in the copied constructor is unchanged.
- `Packet.writeBytes` and `Packet.writeByteAdd` (the bad-magic paths reached from `readUnsignedByte` and `readByte`) count into `badMagicStubCalls` and throw. The success path never reaches them. Their native bodies are not copied because the brief limits the closure to the decode readers; they are not needed for the success path.
- The Packet and XOR-helper class headers drop `extends Node` (no `Node`, no `Packet` static initializer, no `Class223`). Native static initialization therefore differs: the native jar runs the `Packet` static initializer (`Class223`, `long[32]`); the extracted closure has fields only.

## Fixtures (original synthetic, encoded by `tools/encode_decode_fixtures.py`)

The encoder declares each design (vertices, faces with type 1–4, colours) independently and does not read native source or
decoder output. It writes the old-format layout read by `method1103`: vertex flags, face types, face index deltas,
big-endian u16 colours, vertex X/Y/Z delta streams, and an 18-byte footer with texture count 0 and all optional flags 0.
Deltas use signedSmart: one byte for −64..63, two bytes for −16384..16383. It asserts that each design is expressible
(type 2/3/4 transitions match the running state), that the footer never equals `-1,-1`, and that each fixture is at most 1 KiB.

| fixture | purpose |
| --- | --- |
| `triangle` | one type-1 face, unsigned colour `0xF00D` (stored as a signed short) |
| `strip_types_1_4` | face types 1, 2, 3, 4, 1 with the running (A, B, C) state |
| `signed_smart_boundaries` | deltas 63/64, −64/−65, 16383/−16384 on coordinates, explicit zero deltas with the bit set, index deltas 63/64/−64/−65/0 |
| `vertex_perturbed` | triangle with one vertex moved; native must change exactly `y[2]` |
| `colour_index_perturbed` | strip with one colour and one face index changed; native must change exactly `colour[2]` and `c[4]` |

## Checker

`tools/check_decode_evidence.py` compares every array and count from each runtime with the design, not with another
runtime: native jar reflection, the extracted JVM, and the TeaVM WasmGC browser run. Colours are compared after an
explicit unsigned-to-signed conversion (`v − 65536` for `v ≥ 32768`) because the native field is a signed short. It
also requires that the extracted and browser runs report zero adapter calls, and it measures the perturbation effects
on the native decoded arrays.

## Limits

- Old format only, flat untextured only (texture count 0, all optional flags 0). No priority, alpha, face-int, texture or label streams.
- Five fixtures, all original synthetic. No cache data, Jagex assets, arbitrary user files, or untrusted-input parser claim.
- Native `Packet` and `Class124` read without bounds checks: a truncated or crafted stream throws an unchecked exception. No
  such input is run here.
- Decode only. No render integration, no full-model claim, no performance or FPS estimate.
- Sizes and compile results are recorded in the private run log and build/provenance.json, not estimated here. Provenance gzip sizes use level9, mtime0 and no filename header. The checker requires exactly the expected five case names per runtime.
