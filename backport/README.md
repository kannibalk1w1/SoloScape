# Backport Lab — design stage

This directory contains **proposal manifests**, not an enabled feature, converter or patched cache. [Architecture](../docs/BACKPORT_ARCHITECTURE.md) defines the gated pipeline and ten acceptance checks. [Manifest guide](../docs/BACKPORT_MANIFEST_EXAMPLE.md) explains unresolved fields.

Keep all user-supplied data and generated binary outputs outside Git, preferably in `.runtime/backport-lab/<experiment>/`:

```
source-data/     # immutable authorized caches, keys, catalogues; never downloaded automatically
converted/       # staged minimal definition/asset outputs, never a live cache
reports/         # dependency closure, codecs, fingerprints, changes, provenance
cache-copy/      # disposable candidate, rebuilt from a separately verified baseline
```

An original synthetic item is the first plumbing test. A behaviour-only Superior Slayer-style proposal is the first later-content candidate after native acceptance. Neither is implemented here. Do not reserve or deploy a target ID until the actual modified 634 cache, server data, client overrides and protocol limits have been audited together.
