# Backport Lab — inspection and original codec probes

The first executable step is a read-only catalogue of occupied item, NPC, object and sequence slots from an owner-supplied 634-compatible cache. It includes unnamed slots using the native reference-table parser. It does not allocate IDs, decode/convert assets, patch caches or enable content. [Dated evidence and limits](../docs/BACKPORT_CATALOGUE_20261017.md).

From the repository root, after the normal native source/build setup:

```sh
python3 scripts/backport_catalogue.py \
  --cache /path/to/authorized/634-cache \
  --server-jar upstream/game-server/game/build/libs/void-server-dev.jar \
  --java-home .runtime/jdks/jdk21
```

The report is confined to ignored `.runtime/backport-lab/`; an existing report is never overwritten. Use `--output .runtime/backport-lab/<new-name>.json` for an explicit name. The jar must contain the native `FileCache` implementation; use the project's normal matched build, not a downloaded runtime. No network fetch occurs. Input fingerprints are checked before and after; a changed input withholds the report. Source digests and jar digest are recorded independently; they do not certify that an arbitrary jar matches the supplied source.

Private inputs, generated catalogues, binaries and test copies stay outside Git:

```
source-data/     # immutable authorized inputs, no automatic downloads
converted/       # future staged minimal outputs, never a live cache
reports/         # private catalogues, future dependency/provenance reports
cache-copy/      # disposable candidate only
```

`CacheSlotsOracle.java` is an optional cross-check against the already pinned Displee 7.1.7 parser. It must run from the repository root on a directory named `cache-copy` inside `.runtime/backport-lab/`; it refuses the installed cache and existing/inside-cache outputs. Displee opens files for writing, so copy the supplied cache first. Compile with the existing native server jar plus pinned rs-cache-library 7.1.7, disio 2.2, ant 1.10.14 and lzma-java 1.3 jars; run with the same classpath plus the compiled class directory. Pass the disposable copy and a new report pathname. No `update`/packing method is called. Compare all four `occupied_ids` arrays, not only counts. The primary inspector does not depend on Displee.

[Architecture](../docs/BACKPORT_ARCHITECTURE.md) defines the remaining gates. [The feature proposal](manifests/superior-slayer.example.json) remains deliberately unbuildable. An original synthetic token is still the first conversion experiment; no later-content feature or synthetic token is enabled. Audit server definitions, client overrides, packet/decoder limits, reservations and save compatibility before reserving any target ID. Missing metadata slots are not safe allocations.

The next isolated step is an [original-item codec probe](../docs/BACKPORT_ITEM_CODEC_20261017.md), run with `scripts/backport_item_codec.py`. It opens no cache and allocates no item; it proves a server/client note-reference disagreement rather than a safe high ID range. The [item consumer audit](../docs/BACKPORT_ITEM_ID_AUDIT_20261017.md) keeps allocation blocked pending packet, appearance, override and save checks.
