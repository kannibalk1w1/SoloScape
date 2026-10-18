# Release content classification — 18 October 2026

This sorts everything in a managed SoloScape version into what a public release could carry and what each player supplies from a build made on their own computer. It records facts and open questions. **It is not a licence review, and it decides nothing about what may be published.** No release or package has been uploaded.

## Why a "locally supplied" kind of file exists

A full private package is 61 MB, of which 99.9 % is two fat jars and the server data. Those are exactly the parts with unresolved provenance (see [the notice inventory](RUNTIME_NOTICE_INVENTORY_20261017.md)). A player who builds SoloScape from source once (the existing `./scripts/dev-run.sh` flow, which writes `.runtime/build-stamp.json`) already has those files. A release can therefore be only the runtime scripts plus the pins and patch hashes the build must match, and the installer copies the jars and data from the player's own build.

## Classification of the observed payload

Counts are from the private test payload built from the deck-export snapshot (3 859 files, 111 recorded patch hashes).

| Group | Files | Bytes | In a code-only package | Open questions |
| --- | ---: | ---: | --- | --- |
| Runtime scripts and `launcher.sh` | 14 | 178 603 | **Released** (`scripts/*.py`, `launcher.sh`) | The repository has no licence file for its own code. Publishing it needs a licence statement from the owner; none is assumed here. |
| Server jar `void-server-*.jar` | 1 | 49 860 585 | **Local** | Fat jar of the 2011Scape/Void game server (BSD 3-Clause per the retained notice) plus its dependencies. 52 server runtime artifacts have no detected notice file, and 15 native entries (Jansi) are embedded. |
| Client jar `void-client-*.jar` | 1 | 14 362 417 | **Local** | Includes three local file dependencies with no recorded source or terms (`clientlibs.jar`, `graphics.jar`, `trident-1.5.00.jar`), 17 artifacts with no detected notice file, and 25 embedded JNA native entries. |
| Server data (`upstream/game-server/data/**.toml, .txt`) | 3 843 | 8 530 507 | **Local** | Inherited game-server data; its provenance relative to the original game is not established anywhere in this repository. |
| Patch hashes in the manifest | 111 | — | **Released** (hashes only) | The patch files stay in the repository, not in the package. They modify BSD/RuneLite-licensed upstream files and carry those notices. |
| Game cache, art, fonts | — | — | Never packaged | Supplied externally by the player; rights not addressed here. |
| JDK 8 / 21, Python, Gradle | — | — | Never packaged | Each has its own terms; the player installs them. |

A code-only package built from the same payload is **under 1 MiB** and contains no jar, data file, cache or art.

## What this does and does not settle

- It removes the two fat jars, the embedded natives and the server data from anything uploaded, so the three unattributed jars, the missing notices and the data provenance no longer gate a **code-only** release. They still gate any release that ships those files.
- It does not decide that the scripts may be published (no repository licence yet) or that the patches may be (they modify upstream files; their redistribution terms follow those files).
- It leaves the game programs and data **outside the release's integrity check**. See the trust section of the [managed updater document](MANAGED_UPDATER_20261018.md#locally-supplied-files).

## Why the jars are not pinned by hash

A release cannot name the jar hashes a player will produce. The built client jar's entries are not name-ordered, and over a thousand of its 7 438 entries carry the wall-clock time of the build (the rest keep their source jars' times), so two builds of the same source differ. Making the build reproducible across machines would mean changing the Gradle configuration and depending on the exact JDK; nothing here attempts that. The release instead pins the **source**: the same server and client pins and the same patch hashes, recorded in the manifest. The installer accepts a local build only if its build record carries exactly those pins and patch hashes, and the jars match the hashes in that record.

## Consequences a player will see

- A release that changes only scripts or launcher behaviour installs automatically.
- A release that changes a patch or a pin needs a new local build first. Download then stops with *"Your local build … was made from different source than release …. Update that source folder, rebuild, and try again."* and the installed version keeps working.
- A player with no registered build sees *"This release does not include the game programs or game data. Build SoloScape from source on this computer, then register that source folder with the managed_install.py supply-root command."*
