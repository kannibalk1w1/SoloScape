# Private prebuilt launcher contract — 17 October 2026

The real graphical launcher completes Start Character and Continue through an experimental prebuilt preflight, without a native source checkout or build toolchain inside the runtime payload. This is a **private experiment**; the normal source launcher is unchanged. The manifest/bootstrap lives under `experiments/prebuilt-runtime-contract`, rather than adding a partly accepted package mode to production.

Claude Haiku implemented the read-only manifest validator and original-fixture tests; coordinator review tightened patch labels, corrected a data namespace assumption and implemented the experimental adapter, builder and GUI/native probe. The real data check initially refused legitimate `data/social/trade/exchange` interface definitions because the cache/state exclusion was too broad. An independent failing regression preceded the correction: exclude the actual top-level mutable data paths while retaining nested immutable content definitions. The failed preparation is preserved.

## Observed result

| Private host observation | Result |
| --- | ---: |
| Graphical Start Character, total through verified closure | 24.734 s |
| Graphical Continue, total through verified closure | 24.931 s |
| Native account name, XP, inventories, tile after reload | equal |
| Verified before/after fixture backups | 4 |
| Version runtime contexts reused across the two sessions | 1 |
| Package and copied server-cache inventory after run | unchanged |
| Prebuilt preflight in normal checked session path | passed |

The original UI probe clicks real launcher buttons. The original native smoke instrumentation logs in normally and records verified world/server capabilities. After each session the coordinator verifies the stopped-world account before permitting Continue. These are complete host session durations, not frame times, FPS or Deck results. The native jars remain the matched client 56/server 42 pair.

Xvfb/software/no-audio is the explicit environment. No physical input, audio, Gaming Mode, orphan recovery, clean-machine installation, real update activation or release acceptance follows. The source tree remains mounted; this is not a filesystem sandbox or a syscall proof of inaccessible source paths. JREs, Python and host libraries are external dependencies. Instrumentation is compiled outside the package before runtime, not added to native jars. The [earlier native payload screenshot](PREBUILT_NATIVE_SESSION_20261017.md) shows the actual rendered fixture world.

## Contract proved and remaining gates

The manifest validates exact file membership, hashes/sizes, declared identities, safe paths and bounded counts. Only runtime scripts, both native jars and tracked/patch-applied server TOML/TXT data enter the private payload. Cache, artwork, profiles, Git, Gradle and native Java/Kotlin sources stay out. It declares revision 634 without detecting compatibility; metadata is not remote-source authentication or a distribution licence decision.

The adapter requires distinct external profile/cache/launcher homes. It derives mutable runtime/build-lock context from canonical code-root identity **and** manifest hash. Four original fixture cases exercise JRE-only preflight, same-version reuse, distinct-code-root isolation, invalid state and damaged payload refusal; 22 manifest cases cover read-only acceptance and boundary refusals. The root tooling suite has 241 cases with one optional skip. These are not native cross-version/orphan recovery acceptance.

A version-local backend preflight is not a trusted outer installer. The coordinator verifies/prepares this payload before running its code. Public updates must authenticate a candidate before executing any version script or jar, settle the original version's session context, preserve external state and test rollback. Shared grave/floor persistence remains unimplemented, so even clean account reload is not complete-world update safety. No public package or owner deployment is authorized by this result.

[Code and commands](../experiments/prebuilt-runtime-contract/README.md). [Sanitized evidence](evidence/prebuilt-launcher-contract-20261017.json) records exact source commit, manifest/jar/tool hashes, payload size, tests and observed results. Private accepted run: `.runtime/prebuilt-runtime/1792263763130383199/`; refused preparation: `.runtime/prebuilt-runtime/1792263711846692278/`. No proprietary binaries/assets or fixture credentials/saves are committed.
