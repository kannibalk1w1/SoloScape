# Runtime artifact and notice inventory — 17 October 2026

A reproducible offline scan now records the actual resolved native runtime dependencies and matched jar contents. It is preparation for M13-02, not completed distribution review. No binaries, licence texts, caches or proprietary assets are committed by the scan; public evidence contains metadata and hashes only.

## Observed inventory

| Scope | Runtime artifacts | Named notice candidates in matched fat jar | Embedded native libraries in matched fat jar |
| --- | ---: | ---: | ---: |
| Server45 | 55 | 2 | 15 |
| Client56 | 24 | 11 | 25 |

The server graph includes seven local project modules. The client graph includes **three unattributed local file dependencies**: `clientlibs.jar`, `graphics.jar` and `trident-1.5.00.jar`. They have no detected named notice file. Their coordinates/permissions are not inferred from filenames. The native entries observed in the server jar are Jansi platform libraries; the client entries are JNA dispatch libraries. Their presence does not establish which libraries load on a particular machine.

Fifty-two server runtime artifacts and seventeen client artifacts contain no filename matching the notice heuristic. That does **not** mean they have no licence or cannot be distributed: notices may be elsewhere and source/project modules are included in this count. Conversely, a notice file in a fat jar does not prove that every embedded component is covered. Both conclusions require component-by-component review.

Resolved versions can differ from literal build declarations. For example, the client resolves Commons Lang 3.11 and SLF4J API 1.7.32. The [metadata evidence](evidence/runtime-notice-inventory-20261017.json) identifies exact coordinates, artifact hashes, notice candidates, native entries, source licence-file hashes and matched native build identity. It includes the complete observed lists, without host artifact paths.

## Method and validation

The [small inventory tool](../experiments/runtime-inventory/README.md) verifies the matched stamp, holds the source build guard, and resolves `runtimeClasspath` offline through a temporary Gradle task. It inspects ZIP metadata and streams bounded selected entries for hashes without extraction. It verifies the stamp again afterward. Gradle may update its own scratch/configuration outputs; the game is never launched.

The initial resolver-only query omitted all three file dependencies. The final task explicitly includes resolved files absent from the module artifact view, retaining unattributed entries. A first Gradle invocation also failed because its inspection task is incompatible with configuration-cache execution; the documented final command disables configuration caching. A notice-classification control includes the prefixed SoloScape controller notices so the final scan retains that file. Earlier exploratory outputs remain private and are superseded by the final evidence.

Five original-archive tests pass: notice filename classification, hashes without extraction, duplicate/oversized compressed notice refusal, inclusion of unattributed file dependencies and rejection of missing/ambiguous resolver output. The full root suite passes 247 cases with one optional skip. The final offline run resolves all 79 artifacts and inventories both matched fat jars; tool fingerprints match the recorded evidence.

## Remaining review

This is not a complete SBOM, vulnerability assessment or permission to publish a binary package. Shadow minimization means the resolved graph can contain dependencies absent from the final jar; the scan does not attribute every class/resource to an upstream artifact or reconcile duplicate resources discarded during shading.

Before a public package, review the local jars' provenance, each included component's notices and obligations, inherited game/client source and server-data provenance, and separately supplied JDK/Python/system dependencies, fonts, artwork and cache inputs. The observed upstream root licence files do not establish provenance for every inherited file. Public package rights and contents remain unresolved; no legal conclusion is invented here.

The private native runtime and [version recovery/rollback proof](PREBUILT_VERSION_LIFECYCLE_20261017.md) remain useful technical evidence. They do not close this distribution gate. Owner deployment and release publication remain held.
