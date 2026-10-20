# One-command installer — 18 October 2026

20 October follow-up: [delivery repair](RELEASE_DELIVERY_20261020.md) supersedes the publication and rerun limits below. Code-only v0.51 update assets are published; newer installers upgrade a valid existing install through guarded activation and preserve rollback and saves. Generate both delivery assets with `scripts/build_release.py`.

For people who will not build SoloScape from source by hand. One file, `soloscape-installer.sh`, installs Java, builds the game from the fixed source on the player's own computer, asks for the one input it cannot supply (the game cache), and registers the result with the managed launcher so the Update dialog keeps it current. **No installer has been published.** This describes what the code does and what has been tested.

## What the player does

1. Download the installer (once a release publishes one) and the game cache archive (`2026-08-02-void-634-cache.7z`) from the 2011Scape/Void maintainers' published folder, which the installer prints.
2. Run `sh soloscape-installer.sh` (or `--plan` first to see everything it will fetch). It asks `Continue? [y/N]`; `--yes` skips the question.
3. Give it the cache with `--cache <file or folder>`. Without that it looks for the exact archive in `~/Downloads`, `~/Desktop` and the current folder, then asks for a path, and otherwise stops with the download instructions (exit code 3). The Java toolchains are installed before that step, so a stop here leaves them in place for the next run.
4. Wait: about the length of a first Gradle build. Interrupt it with Ctrl-C at any time; the next run resumes (verified downloads, the source folder, a finished build and a finished install are reused).
5. Start SoloScape with `~/.local/share/soloscape/soloscape` or the application-menu entry.

## No Python or git needed

Stock SteamOS has neither Python 3 nor git, and both are needed (Python runs the launcher backend and updater, git fetches and verifies the source). The installer file is a shell script followed by a Python zipapp. If the computer lacks either program, the script first downloads micromamba (mamba-org, pinned SHA-256) and 42 pinned conda-forge packages (Python 3.12, git, 7-Zip and their libraries, about 100 MB), checks each file's SHA-256 against the list recorded in the script, and installs them into `<data>/tools/env`. No root access, no `pacman`, no change to the read-only system. The generated `soloscape` launcher puts that folder first on its `PATH`, so the launcher, updater and rebuild flow use the same private Python and git. `scripts/lock_tools.py` regenerates the pinned list. A computer that already has Python 3.9+ and git uses its own and downloads none of this.

## What it downloads, from where, and how it is checked

SoloScape hosts none of these bytes. The player's computer fetches each one over HTTPS (redirects must stay HTTPS) from the publisher named below, with a size cap and timeouts. JDKs and 7-Zip are kept only if their SHA-256 matches `scripts/installer_inputs.json`; the 7-Zip program is also re-checked before every use. Upstream sources are fetched by pinned commit id. **Gradle dependencies are not hash-pinned.**

| Input | Source | Check |
| --- | --- | --- |
| JDK 21 and JDK 8 | Eclipse Adoptium Temurin 21.0.12.1+1 and 8u504-b01 (GitHub releases) | pinned SHA-256; the unpacked `java -version` must report the right major version |
| 7-Zip 23.01 static Linux build | 7-zip.org | pinned SHA-256; only the `7zzs` member is taken |
| SoloScape source | `github.com/kannibalk1w1/SoloScape` at the release's exact commit | fetched by commit id, fetched id must equal it, no links or submodules |
| Upstream projects | `github.com/2011Scape/game-server` and `runelite-client` at the pinned commits | fetched by id, HEAD must equal the pin |
| Python 3.12, git, 7-Zip (only if missing) | micromamba from github.com/mamba-org and conda-forge packages | pinned SHA-256 for every file, checked before install |
| Build dependencies | Maven Central, Gradle, repo.runelite.net, as the project's own Gradle build resolves them | **not hash-pinned** (see limits) |

The game cache is **not downloaded**. A supplied folder is accepted only if all 39 files match the pinned names, sizes and SHA-256 values, with nothing extra and no links; it is copied to a scratch folder, checked again there, and only then moved into place. A `.7z` must be exactly the archive hash recorded in `installer_inputs.json` (a different archive is refused before it is unpacked; unpack it yourself and give the installer the folder). The hashes identify the copy this project tested on 8 October 2026, not an upstream signature or a grant of permission.

## What it builds and where it goes

Everything lives under `~/.local/share/soloscape` (or `--data`): `jdks/`, `tools/`, `downloads/`, `source/` (the clone, which becomes the install's registered source folder), `cache/`, `install/` (the managed layout), `profiles/`, `launcher/`, `logs/`. It uses the project's own `scripts/prepare-build.sh`, then builds a code-only package from the finished build and installs it with the same verified path as an update. The install has the same layout the update acceptance tests used, with the source folder registered, so the launcher's Check / Download / Update Source and Rebuild / Roll Back are available. The installer's own cold run proved the install and that the launcher opens from it; the update and rollback acceptance was run on installs made by the earlier package path, not on this one. The installer does not touch Steam, the system Java, or anything outside its folder (plus the optional menu entry, `--no-shortcut` to skip it).

## Why the cache stays player-supplied

The cache is not Jagex's official distribution; it is the revision-634 cache the 2011Scape maintainers link from their README. No licence or permission for redistributing it has been established, so SoloScape neither hosts nor fetches it. See [CACHE_SETUP](CACHE_SETUP.md) for the download.

## Repair

The installer keeps a copy of itself as `soloscape-installer.sh` in its data folder. Running it again is safe: it reuses everything that is still verified and redoes only what is missing, so a lost cache is `soloscape-installer.sh --cache <file or folder> --yes`. An interrupted install is recognised (configuration, guard, pointer and current version must all be sound) and rebuilt from the verified package rather than trusted. A resumed source folder is restored to exactly the release commit, with nothing untracked left where Python imports from, before any of its code runs.

## Limits

- Linux x86_64 only. A computer needs `sh`, `curl`, `sha256sum`, `bash`, `flock` and ordinary coreutils; it says so plainly if `curl` or `sha256sum` is missing. These are the Arch-base tools a stock SteamOS has (not itself verified here). Python 3 and git are **not** required: see below.
- Dependency downloads are not hash-pinned. A malicious or changed upstream artifact would be built into the game. The next hardening step is Gradle dependency verification with reviewed metadata, which has not been done.
- The installer file itself is only as trustworthy as where it is downloaded from; hashes inside it cannot authenticate it.
- The pinned `634-client` commit can no longer be fetched from GitHub. No patch or build step reads that project, so it is now a reference-only pin that is skipped when unavailable.
- Rights to the jars, server data, cache and fonts are unresolved (see the release classification document). The installer avoids redistributing them but does not make them cleared.
