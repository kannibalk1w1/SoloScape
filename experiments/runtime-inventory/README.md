# Offline runtime metadata inventory

This read-only product audit records the resolved server/client runtime artifacts and the contents of the matched fat jars. It lists candidate notice files and embedded native libraries by path, byte count and SHA-256. It extracts no files and copies no proprietary assets into Git. It grants no distribution clearance and is not a complete SBOM or vulnerability scan.

Run from a prepared source checkout with its existing matched jars and local JDKs:

```sh
python3 experiments/runtime-inventory/run.py \
  --server-java /absolute/path/to/java21/bin/java \
  --client-java /absolute/path/to/java8/bin/java
```

The runner holds the source build guard, verifies the matched stamp before and after inspection, and invokes only a private Gradle inventory task with `--offline --no-configuration-cache`. It does not launch the game or build a release. Gradle can update its own build/configuration scratch files. Failure to resolve an uncached artifact fails the report and preserves the private logs. Output is a fresh `.runtime/runtime-inventory/<timestamp>/summary.json`; input source commit and tool hashes identify the observation.

The Gradle task records both module/project artifacts and additional resolved files. The latter matters: legacy `implementation(files(...))` jars are absent from `resolvedArtifacts` alone. Unattributed file dependencies remain explicit, with no invented Maven identity. A resolved runtime graph is a superset for a minimized shadow jar, not proof that every dependency is embedded or used. Notice filenames are a heuristic, not an interpretation of their text or completeness. Duplicate ZIP names, oversized archives/notice entries and missing/ambiguous Gradle inventories fail rather than producing an apparently complete report.

A release review still needs to reconcile dependencies and native libraries with retained notices, versions, permissions and source obligations; identify opaque local jars; review the inherited game/client source and server data; and separately inventory JDK/Python/system dependencies, fonts, artwork and user-supplied cache inputs. An upstream root licence does not itself establish provenance for every file. No public package is approved by a successful metadata scan.

Five original-fixture tests cover hashes without extraction, duplicate/oversized notice refusal, filename classification, retention of unattributed file dependencies and missing/ambiguous resolver output. Native artifact observations are recorded separately after an actual offline run.
