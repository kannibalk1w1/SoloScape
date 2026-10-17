# Backport Lab: read-only definition occupancy — 17 October 2026

The lab can now inspect the supplied 634-compatible cache's reference-table slots for items, NPCs, objects and sequences. It deliberately includes unnamed/default definitions. A declared slot is treated as occupied even when no human-readable server key exists; this avoids the unsafe assumption that the largest named ID describes the cache.

This is an input catalogue, not an allocation policy or converter. No target ID is reserved, no gameplay or save schema changes, and no cache entry is written. The existing Superior Slayer proposal remains unbuildable. It advances the catalogue groundwork of M8-03; it does not complete that milestone or any complete ten-stage asset-import gate.

## Source boundary

`CacheSlots.java` calls the project's actual compiled `FileCache`/`ReadOnlyCache` reference-table loader, whose data and index handles use `RandomAccessFile(..., "r")`. It reads archive/file metadata, not definition opcode bodies or proprietary models. The index255 descriptor is also explicitly closed by the tool. Raw intermediate output uses exclusive creation. The Python wrapper hashes every recognized cache data/index file before and after, plus the jar and eight relevant source files, and withholds a report if they change. Reports include digests and declared IDs but no local source paths or timestamps; full reports stay ignored.

The mapping comes from the pinned native source, not an OSRS convention:

| Kind | Index | Definition ID from archive/file |
| --- | ---: | --- |
| Item | 19 | `(archive << 8) | file` |
| NPC | 18 | `(archive << 7) | file` |
| Object | 16 | `(archive << 8) | file` |
| Sequence | 20 | `(archive << 7) | file` |

The extractor rejects files outside those splits, duplicate IDs, missing namespaces and overflow. The wrapper validates exact namespace/index/split matches, sorted unique nonnegative IDs and supported schema. Output is confined to ignored `.runtime/backport-lab/` outside the cache; existing output is refused.

## Actual supplied-cache result

| Kind | Declared occupied slots | Highest occupied ID |
| --- | ---: | ---: |
| Item | 20,178 | 20,178 |
| NPC | 13,984 | 15,511 |
| Object | 57,203 | 57,264 |
| Sequence | 15,237 | 15,259 |

These figures describe this particular supplied input, not every historical revision-634 cache. No hole or number above a maximum is declared safe. Cache fingerprint: `a4293ba42198ed092f8db93f2b9c2dc8e755db1d6c16bdd91f4dcf0ad68c43fd` (canonical JSON of recognized filenames, sizes and SHA-256 hashes; not a single container digest).

Two fresh native runs produce byte-identical reports; before/after input hashes match. An independent reference-table parser, the already pinned Displee `rs-cache-library` 7.1.7, agrees on **every ID in all four arrays**. It ran only on a disposable cache copy because its constructor opens write-capable handles. Its lab-only path/output guards also reject the original-cache argument and an existing report. No update/packing method is called.

Seven dependency-free fixture tests cover catalogue validation, sparse/zero IDs, all-index fingerprinting, missing/symlinked files, changed cache/jar/source inputs, deterministic sanitized output and refusal to replace input/existing evidence. These boundary tests mock subprocesses; the actual Java/cache execution and independent parser are separate local experiments. All 148 root tooling cases pass with one existing optional skip. See the sanitized [evidence](evidence/backport-catalogue-20261017.json); private catalogue files, dependency jars and cache copies are not committed.

## Limits and next gate

Reference-table presence does not certify an entry's decompression, opcodes, integrity, dependencies or runtime rendering. This tool does not autodetect cache revision. Source and jar digests are recorded separately; they are not proof that an arbitrary jar matches those sources. CI has original metadata fixtures only, not a bundled cache or native jar.

The remaining allocation audit must include semantic server TOML, native client overrides, consumer field widths/sentinels, existing reservations, saved identities and all other required asset namespaces. Then prove one original synthetic definition through explicit codecs on a disposable cache copy. Do not expand into a real later-content feature until those boundaries and native session acceptance are met. No Deck deployment or owner profile access occurred.
