# Item-ID consumer audit — 17 October 2026

Claude Haiku traced the pinned native source; coordinator review confirms the boundaries below. Server paths are relative to `upstream/game-server/` (pin `9f911355`); client paths to `upstream/runelite-client/client/src/` (pin `297bc8a`). Source and patch changes after those pins remain relevant. No cache values, models or other proprietary assets were inspected for this audit. This is not a safe allocation policy.

| Consumer | Inspected source / method | Finding / remaining limit |
| --- | --- | --- |
| Note/lend links | `cache/.../decoder/ItemDecoderFull.kt`, `ItemDecoder.kt`, opcode reads; `buffer/.../read/Reader.kt.readShort` | Native server readers interpret note/lend short references as signed. Values at or above 32768 become negative. |
| Client note/lend links | `ObjType.readValues`, opcodes 97/98 and 121/122; `Packet.readUnsignedShort` | Client reads unsigned values; 65535 is retained by these branches. Defaults of -1 do not make an explicit 65535 equivalent. |
| Stack variants | Same decoders, opcodes 100–109 | Source shows the same signed/unsigned difference for variant IDs and amounts. This has not been probed at runtime. |
| Definition encoder | `cache/.../encoder/ItemEncoder.kt`, note/lend writes | Emitting two bytes does not establish a round trip through every reader. The writer omits absent -1 links; boundary-valued links need explicit validation. |
| Inventory and interface containers | `network/.../encode/ContainerEncoders.kt.sendInventoryItems`, relevant `InterfaceEncoders.kt` sends | Some paths encode item+1 in 16 bits. Item65535 wraps to the empty encoding. Item65534 fits the writer, but complete client handler/inbound coverage remains unaudited. |
| Equipment appearance | `engine/.../equip/BodyParts.update`, `network/.../visual/encode/player/AppearanceEncoder.kt` | Appearance carries equipIndex OR 0x8000, **not the raw item ID**. Adding a raw item ID does not directly describe the appearance constraint. |
| Equipment table | `ItemDecoder.load`; client `Class150.method1202`, `Class25.anIntArray369` | Both sides construct an ordered table of wearable items. This requires the same definitions/predicate/order; cache identity and custom overrides still need auditing. |
| Appearance read | `Player.method2452` | Flagged values index the wearable-item table. Additionally, 0xFFFF in the first slot is a transformation sentinel. The nominal 15-bit index width alone therefore does not prove index32767 safe in all slots. |
| Inbound actions | `network/.../decode/InterfaceOnInterfaceDecoder.kt`, `FloorItemOption4Decoder.kt`, `FloorItemOption5Decoder.kt` and their read helpers | Several paths use signed short reads for numeric item IDs. Others use differently named helpers. Exact client sender, helper semantics, sentinels and server validation must be checked for each action. |

## What the runtime probe establishes

The separately reproducible [original-item codec probe](BACKPORT_ITEM_CODEC_20261017.md) exercises opcode97 against the actual full server, gameplay server and client decoders. A reference32767 agrees; 32768,65534 and65535 disagree as the source predicts. It does not certify the lend, stack-variant, equipment or packet paths above. No allocation or asset conversion is inferred from that result.

## Before allocating one target item

1. Finish client container/GE and inbound action traces, including signedness, offsets, sentinels and validation.
2. Count and compare actual wearable tables and test the first-slot transformation sentinel separately from numeric item IDs.
3. Audit the supplied cache, semantic server TOML, client/server overrides, existing reservations and saved identities together. Include placeholders/unnamed slots from the [occupancy catalogue](BACKPORT_CATALOGUE_20261017.md).
4. Fail unsupported opcodes and unresolved dependencies before encoding. Source-only support for an opcode is insufficient: for example the server encoder supports later single-note opcodes139/140, while the inspected client decoder has no matching branches. Actual occurrence in the supplied cache is unverified.
5. Review a frozen append-only allocation with tombstones and matched cache delivery. No arbitrary high range is reserved by this report.

Future controls should cover note/lend and stack variant boundaries, actual container and item-on-item/floor packets, wearable-table ordering and sentinel cases. Native saves use stable semantic item strings; do not scatter source numeric IDs into gameplay or profiles. This audit redistributes no source bodies or assets and grants no rights to cache data.
