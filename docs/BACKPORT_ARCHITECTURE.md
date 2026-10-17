# Curated later-content backport architecture

Reviewed 17 October 2026 against `main` `502df96`. **Backport content, not an entire revision.** No cache replacement, imported gameplay, converter or compatibility runtime is delivered by this research. Native 2010–2011 SoloScape remains the product. [Research source inventory](RESEARCH_SOURCES_20261017.md) pins the inspected external code; source licences do not grant rights to game assets.

Follow-up: the [read-only occupancy catalogue](BACKPORT_CATALOGUE_20261017.md) now inventories four supplied-cache definition namespaces. Conversion, safe allocation, dependency closure and cache patching below remain designs.

## What the precedents establish

| Inspected project/code | Useful lesson | Boundary for SoloScape |
| --- | --- | --- |
| [OSDC mirror](https://github.com/Rune-Status/scape-tools-osrs-data-converter), `OsrcController.kt`, `task/MapTask.kt` | Revision-request code and explicit gzip/map-index reconstruction show real format-specific work, not a universal cache rename. | The inspected mirror last pushed in 2019. Its embedded `openrs.jar` and downloader were not run/audited. Never fetch “latest” automatically or assume 317 output is 634-compatible. |
| [Elvarg public client](https://github.com/Elvarg-Community/Elvarg-Client-Public), `ObjectDefinition.decode` | New data is handled by explicit opcode/model/texture/client changes. The README identifies data 206, despite the broader “latest data” description. | Reference architecture only; GPL-3.0 code and bundled data are not drop-in BSD additions. A working 317 client does not verify our 634 opcodes or mechanics. |
| [Valius WIP fork](https://github.com/UndeadStudios/Valius-Client) | Another maintained-by-fork example of newer definitions in an older client; inspected item/NPC definitions, not just its revision-214 description. | Fork identity and actual files must be pinned. No claim that every Valius release works; no binary cache downloaded or copied. |
| [Dodian/ub3r](https://github.com/dodian-community/ub3r-monorepo), `CacheBootstrapService`, `ObjectDefinitionDecoder` | Decoded spatial bounds/interactions feed server collision. Its decoder explicitly handles a particular packed `loc.idx` format and opcode exceptions. | Rendering success is not collision correctness. Root licence was not identified by GitHub metadata; reuse requires per-file review. |
| [Displee](https://github.com/Displee/rs-cache-library), `CacheLibrary`, `Index317` | Container/index/archive manipulation is separable from game definitions and their semantics. | Already pinned by SoloScape server dependencies at 7.1.7. Reuse after checking that exact version; current upstream API/source is not proof for our pin. |
| [OpenRune FileStore](https://github.com/OpenRune/OpenRune-FileStore), separate `ItemCodec`/`ItemCodec718` | Separate revision codecs, shared definitions and staged packing are the right shape. | There is no inspected 634 codec guaranteeing compatibility; root licence metadata is absent. Do not import its aggregate modern data/tooling dependency. |
| [OpenRS2](https://github.com/openrs2/openrs2), `DiskStore`, [archive API](https://archive.openrs2.org/api) | Sector/archive integrity, revisions, hashes and source identity are useful independent tools. | Archive availability is not permission to redistribute. Tool ISC licence and asset rights are distinct; use owner-supplied data. |
| [RSMod](https://github.com/rsmod/rsmod), `ObjTypeBuilder` | Typed definition builders separate logical content references from encoded data. | Do not replace native SoloScape pre-EoC combat/pathfinding with a newer server runtime. Its pathfinder is already a dependency, not a mandate to migrate. |
| [LostCity Engine-TS](https://github.com/LostCityRS/Engine-TS), `ConfigType`, `ObjType` | ID plus semantic `debugname`/name lookup is an established useful pattern. The Server repository is a bootstrapper for separate engine/content/client revisions. | TypeScript implementation is not a portable replacement for our Java client/Kotlin simulation. Learn the boundary; do not copy an entire stack. |

[2009scape's own historical account](https://2009scape.org/updates/2021-05-05-The-halt-on-updates.html) describes removing mixed OSRS material while restoring a pure 530 baseline. This is the project's account, not an independent forensic audit. Lesson: define era boundaries and provenance before additions accumulate. It does not prove every mixed-revision project is unstable.

## Start with the architecture already present

`upstream/game-server/engine/.../data/definition/ItemDefinitions.kt` loads semantic string IDs from TOML, rejects duplicate names and resolves clone metadata. NPC/object definitions use the same family of mechanisms. `cache/.../definition/decoder/ItemDecoder.kt` maps native items to index 19 with archive `id >> 8` and file `id & 255`; `ItemDecoderFull`/`ItemEncoder` expose fuller encode/decode information. Native client decoding, model loading, sprites and packet widths remain separate contracts. The lightweight `ItemDecoder.read` has no fail-fast unknown-opcode branch; do not feed modern data to it and assume compatibility. The lab needs an explicit supported-opcode contract around the selected full codecs.

Therefore add an **authoring/build compatibility layer**, not another live content database. Existing gameplay keeps semantic server keys; new `SoloContent` references can be generated wrappers over those keys. The client receives only resolved native target IDs, preserving ordinary native action validation and controller adapters. Never scatter OSRS source IDs through scripts, drop tables, client UI or saves.

### A. Behaviour

Implement a selected mechanic in existing Kotlin scripts/events, task/damage/drop ownership and tick rules. References specify experience, not a second runtime. Explicitly resolve pre-EoC damage, attack styles/accuracy, prayer, timing, energy, Summoning interactions, task credit and private co-op. Use a disabled-by-default per-world feature gate; keep data policy separate from unlock UI.

Use deterministic tests for eligibility, one-time spawn/task credit, death/cleanup, collision-valid placement, ownership, cancellation and save/reload. A source feature's mechanic may require no imported definition or art at all. A convincing controller/combat test is more valuable than a large asset dump.

### B. Definitions and identity

Proposed versioned JSON manifests are dependency-free to inspect in Python and straightforward to validate. See [example](BACKPORT_MANIFEST_EXAMPLE.md). YAML/TOML are also viable, but a second syntax is unnecessary here. Tooling produces:

- `registry.lock.json`: semantic key → native target ID **per definition namespace**, pinned cache/source/tool hashes and retired-ID tombstones;
- generated Kotlin semantic wrappers and server TOML mapping fragments;
- a resolved dependency graph and cache-entry change allowlist;
- a local patch plan plus provenance/integrity report.

Allocation must scan **the actual modified 634 baseline**, not a stock historical maximum: cache slots (including unnamed/placeholder entries), server TOML, client hardcoded overrides, noted/lent/stack variants, interface scripts and existing custom reservations. Audit each native decoder, packet field width, signedness and sentinel separately. Item/NPC/object/model/sprite/sequence namespaces need independent policies. Some 634 fields encode references in unsigned shorts; this is not proof that every type can safely use every value up to 65535.

Do not declare an arbitrary global “60000+” range safe. After the audit, reserve a small contiguous append-only range where array growth and all consumers support it. A deterministic sorted-key allocator proposes IDs once; commit a reviewed lock so adding an alphabetically earlier key cannot renumber existing content. Reject collisions, range exhaustion and a changed baseline until rebased explicitly. `PlayerSave` writes item IDs as semantic strings (`Item.id: String`), so keep those keys stable as well as native allocations. Tombstone retired allocations; do not recycle IDs that can appear in profiles or old caches. Dependency cycles/incomplete references fail before encoding.

### C. Assets and cache patching

Import only a selected dependency closure. Reuse suitable 634 assets first. Pin source revision **and bytes**, decoder/converter revisions and transformation rules; revision numbers alone do not identify customized caches.

| Data | Conversion checks |
| --- | --- |
| Items/NPCs/objects | Explicit opcode mapping; sizes/interactions/collision, options, variants, bas/combat params, notes/lending and referenced definitions. Decode unknown opcode → fail, not byte-skip guessing. |
| Models/textures | Vertex/face formats, colour/material/texture mappings, alpha/priorities, coordinate scale and attachments. Test native software and OpenGL, examine/worn/ground contexts as applicable. |
| Animation | Sequence → frame → skeleton/base closure, rig/skin compatibility and interpolation. New skeletal systems may need unavailable client support; prefer baseline animation and fail unsupported formats. |
| Sprites/interfaces | Palette/alpha/offsets, font and widget/CS2 references, click identity and controller adapter. Importing a modern interface graph is a separate feature, not a free side effect. |
| Maps/landscape | Terrain, locations, region coordinates, XTEA requirements where relevant, collision flags, instancing and server clipping. Defer from the first proof. |
| Audio/music | Sound IDs, instruments/samples or codecs and native audio paths; avoid new imports initially. |

The packer reads immutable sources and writes a **new disposable cache copy**. Stable ordering, deterministic compression settings and frozen allocation produce reproducible bytes for the selected tool version. Rebuild affected archive reference tables, CRC/Whirlpool/version metadata and JS5 delivery expectations. Sector repacking can change `.dat2` offsets for untouched entries: prove original **decoded entry bytes/hashes** and integrity are unchanged outside the allowlist, rather than requiring the entire original container to remain byte-identical. Require both clean-rebuild determinism and an unchanged-baseline fingerprint.

No packer writes the installed cache, profile cache or a running world's files. Existing build/profile locks remain mandatory; cache identity must join the build stamp/diagnostics before any real backport is enabled. Server definitions, client definitions and delivered cache version must agree; a stale client cache should reject/reload predictably.

## Backport Lab acceptance sequence

The tracked [lab directory](../backport/README.md) contains design/example manifests and narrowly scoped original inspection tools. Private inputs, keys, converted binaries and test cache copies live under ignored `.runtime/backport-lab/`. The [occupancy catalogue](BACKPORT_CATALOGUE_20261017.md) and [original codec probe](BACKPORT_ITEM_CODEC_20261017.md) supply partial inspection/definition evidence. Those two inspectors do not allocate an ID or patch a cache. The [original Lab token proof](BACKPORT_LAB_TOKEN_20261017.md) now adds one temporary definition to two disposable cache copies with deterministic output, integrity checks and an allowlisted change. It does not reserve a shipped ID, convert assets or enable gameplay. **The ten complete gates below remain open for an actual later-content import.** They are observable gates for a later bounded implementation.

| Gate | Smallest experiment / evidence |
| --- | --- |
| 1. Inspect source | Original synthetic definition first; then one authorized pinned source definition. Emit named opcode/value inspection and input digest; no network download. |
| 2. Dependencies | Emit transitive definition/model/texture/animation/etc. graph; reject unknown opcodes and unresolved/cyclic references. Include reused 634 dependencies. |
| 3. Allocate | Inventory baseline/overrides and audited consumer limits; test occupied/reserved/sentinel IDs, duplicate keys and stable allocations after adding a new entry. |
| 4. Convert definition | Synthetic “Lab token” with original text, stackability and existing 634 appearance. Round-trip through explicit source/target codec versions and both actual native decoders. |
| 5. Asset boundary | First reuse a baseline model unchanged. If proving actual conversion, use one tiny **originally authored** model or sprite with known colours/vertices; synthetic reuse alone does not prove an animation/model converter. |
| 6. Patch | Deterministic staged entry bundle and integrity metadata; apply to disposable copy twice from clean baseline, compare output hashes. |
| 7. Reproduce | Clean source checkout + pinned tools + separately supplied authorized cache reproduce the report/output; dependency resolution and input hashes documented. |
| 8. Remove | Disable feature, switch cache build back, clear only disposable derived client cache; original-entry hashes match. Also test affected profile migration/tombstone policy before promising uninstall after real gameplay. |
| 9. Protect baseline | Hash/read original cache before/after; decoded entry allowlist diff on candidate; native login/render/collision and existing-content smoke on copied profile. |
| 10. Provenance | Emit source/target digests, revision and codec/tool pins, operation graph, allocation, warnings, permission/source notes and result. Sanitize report before publishing. |

Stop if target codecs cannot encode the selected subset, the server/client interpret it differently, an asset requires new renderer support, or IDs cannot be safely reserved. Do not use a giant current cache as the recovery path. A definition-only token proves plumbing, not real OSRS feature compatibility.

## First feature candidates

Estimates are relative **dependency surface**, not scheduled delivery promises. A compact native implementation can still expose difficult persistence/combat edges.

| Candidate | Architectural value | Dependency surface / risks | Recommendation |
| --- | --- | --- | --- |
| Superior Slayer-style enhanced spawn for one existing task monster | High: semantic identity, native combat, spawn/loot ownership, optional content and controller targeting | Low–medium initially: existing location/models/animations/drops. Audit task eligibility/credit, collision-valid spawn, non-recursion, cleanup and guests. Distinct NPC name/scale may need one definition. | First **later-content** proof after M6 Slayer audit and Lab token. No OSRS unique drops/unlock currency initially. |
| One optional enhanced monster with a small existing drop table | Medium: NPC allocation, combat params and drop mapping | Low–medium; existing map and visuals; bounded AI, kill credit and loot rules | Good fallback if Slayer is incomplete, but proves less progression integration. |
| Compact skilling processing recipe using existing inputs/output/tool | Medium–high: semantics, timing, requirements, Make-X and saved effects | Low if no map/new UI. Avoid globally changing 2011 skill XP/economy. | Strong second candidate and controller production regression. |
| Later-style bank quantity/search QoL adapted to native 634 widgets | Medium: controller/native interface compatibility | Low assets, potentially high widget/CS2/input risk; much already exists | Audit first; do not “backport” a feature SoloScape already supplies. |
| Tiny optional gathering bonus using an existing resource node | Medium: event hook, drop ownership, deterministic balancing | Low–medium if no map/animation; economy and multiplayer eligibility need explicit policy | Useful only after the solo progression audit establishes the need. |

Do not begin with raids, Zeah, modern spellbooks, broad map packs, a skill rewrite or hundreds of imported definitions. First accept native sessions, audit an existing slice and prove the cache/definition boundaries separately. See [roadmap ordering](ROADMAP.md#reviewed-working-order--17-october-2026).
