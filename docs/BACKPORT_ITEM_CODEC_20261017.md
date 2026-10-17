# Original-item codec boundary — 17 October 2026

An original synthetic definition now round-trips through the actual native encoder and three actual native readers, without opening a cache or allocating an ID. The probe finds a signedness disagreement at note-reference32768. It therefore supplies evidence for a compatibility gate, not permission to allocate high IDs or enable an imported item.

## Result

`OriginalItemCodec.java` authors the name “SoloScape Lab token”, cost37, stackability1 and sprite scale2200. The native `ItemEncoder` produces bytes read by `ItemDecoderFull`, gameplay `ItemDecoder` and client `ObjType.decode`. Every reader must consume the entire stream; name, cost and stackability must agree, and the full server/client scale must agree. Model0 is only a default numeric field: no model or linked definition is loaded. Fixture ID0 is an in-memory identity, not a target allocation.

| Numeric note reference | Full/gameplay server | Client | Interpretation |
| --- | ---: | ---: | --- |
| absent (-1) | -1 | -1 | Agrees; absent link is omitted by encoder |
| 32767 | 32767 | 32767 | Agrees for this raw opcode |
| 32768 | -32768 | 32768 | Disagrees |
| 65534 | -2 | 65534 | Disagrees |
| 65535 | -1 | 65535 | Disagrees; explicit65535 differs from absent |

A sixth case changes cost to38 and requires different encoded bytes plus matching decoded cost. Re-encoding each case must produce identical bytes. Six malformed controls reject an unsupported opcode, unterminated string, truncated integer, missing terminator, trailing bytes and duplicate opcode. The explicit subset inspector accepts only opcodes2/4/11/12/97/0; it is deliberately not a general definition validator.

Two fresh Java compilations/executions produce byte-identical JSON reports, including input/tool digests. Three high-reference disagreements are **expected findings**, not successful conversions. [Sanitized results and digests](evidence/backport-item-codec-20261017.json) contain no definition binary or proprietary asset. The [consumer audit](BACKPORT_ITEM_ID_AUDIT_20261017.md) describes the additional packet, wearable-table and sentinel boundaries that still block allocation.

## Reproduce

From a normal native source build with JDK21 and the separately supplied authorized cache available for that build:

```sh
python3 scripts/backport_item_codec.py \
  --cache-jar upstream/game-server/cache/build/libs/cache-dev.jar \
  --server-jar upstream/game-server/game/build/libs/void-server-dev.jar \
  --client-jar upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar \
  --java-home .runtime/jdks/jdk21
```

Use the actual locally built filenames if these change. No cache path is passed to this probe. The separate cache module jar is required because minimization removes the unused full encoder/decoder from the server fat jar; it precedes the server and client jars on the classpath. Java21 runs this isolated probe, including the Java8-compatible client classes, without launching either game process.

The wrapper freezes jar copies in a temporary ignored lab directory, compiles the original Java harness, runs it headlessly and checks input/tool hashes before and after. Reports use new filenames under ignored `.runtime/backport-lab/`. Copies/classes are removed afterward; user-supplied jars are untouched. This is a locally built executable-code trust boundary, not a sandbox for arbitrary downloaded jars. Digests identify inputs; they do not certify arbitrary jars against source pins. Tested inputs and private report paths are recorded in the sanitized result.

## Remaining gates

This tests raw opcode decoding only. It does not exercise cache loading/link normalization, dependency discovery, item allocation, definition overrides, wearable-table agreement, container/action packets, sprites/models, staged cache writes, native login or uninstall/save migration. It imports no later content and changes no production codec. Reusing the same two bytes in different readers is insufficient evidence of compatibility. Future conversion must reject unsupported values per consumer until an explicit, reversible mapping is proven.
