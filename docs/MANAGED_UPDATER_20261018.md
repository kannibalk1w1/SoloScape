# Managed updater — 18 October 2026

The graphical launcher can now check for, download, verify and install a SoloScape update into a **managed install**, then continue the same characters in the new version. This is the smallest usable production path, built from the merged lab mechanisms. It is verified privately; **no public release exists, nothing was published, and no owner install, Deck or profile was touched.** See [limits](#limits-and-open-questions) before relying on it.

## What a player sees

Launcher Settings → **Updates…** opens one dialog (Settings is its owner, the launcher window its owner's owner):

- **Installed:** release label and the first 12 characters of the version id. **Downloaded and verified:** the staged candidate, if any, with its own label and id.
- **Check for updates** reads the fixed project's latest stable release. Offline, rate-limited, no-release and no-package outcomes are plain messages; the installed version stays usable. There is **no network access at launcher startup**.
- **Download** streams the one declared package with a progress bar (stage, MiB done of total). **Cancel Download** stops it and removes every partial file. A whole-job time limit (30 minutes) applies on top of the socket timeout, so a trickling server cannot hold it open.
- **Install and Restart** is enabled only for a verified staged candidate with no world running and no download in flight. It records a single-use request and quits the launcher with exit status 75. The bootstrap then applies the update and relaunches.
- B (mapped) closes only the top dialog and restores its parent's focus; closing the dialog never cancels a download. The result of the last apply (installed, refused, or rolled back) appears once at the next launch.

A source/development checkout shows the same dialog but explains that it cannot install; Check still works.

## Install layout

A managed install is one folder, separate from the external profile, cache and launcher-settings homes:

```text
install/
  install.json            absolute external profile / cache / launcher homes (+ optional java paths)
  install.guard           the one lock file
  active.json             {current, previous} version ids, replaced atomically
  versions/<id>/          sealed read-only payload; <id> = SHA-256 of its soloscape-runtime.json bytes
  staging/                downloads and extraction scratch (single-writer lock)
  bootstrap/              managed_install.py, runtime_manifest.py, update_package.py (trusted outer; not version-owned)
  candidate.json          the staged, not yet installed candidate (kept by pruning)
  update-request.json     single-use consent from a stopped launcher
  trial.json, last-update.json
```

`python3 install/bootstrap/managed_install.py run install` is the entry point: it takes a **shared** lease on `install.guard`, resolves `active.json` only after the lease is held, verifies that version against its manifest, and launches `scripts/launcher.sh` with the lease descriptor inherited plus `SOLOSCAPE_MANAGED_ROOT` and the three external homes. Other commands: `init`, `status`, `activate`, `rollback`.

The payload keeps the prebuilt hierarchical layout (`upstream/...`, `scripts/...`); nothing is flattened and no gameplay code changed. Profiles, backups, `launcher-settings.json`, the supplied cache and per-version recovery contexts stay outside every version directory.

## Package and manifest (format 2)

A package is a ZIP of exactly `soloscape-runtime.json` plus the files it lists, at their payload paths. Format 2 extends the prebuilt format-1 manifest with `release` (a short label) and `storage_versions` (the sorted list of logical save-storage versions this payload can read, e.g. `[0, 1]`). Limits: archive 768 MiB; 512 MiB per file; 2 GiB and 10 000 files in total; 4 MiB manifest. They are validated before and after extraction; unlisted, linked, special-file, traversal, `cache`/`saves`/`.git`-style, duplicate, encrypted, size-lying and digest-lying entries are refused. Modes come from the installer (scripts/launcher.sh `0555`, everything else `0444`), never from the archive.

The historical format-1 manifest, the staging lab (8 MiB / 4 MiB / 16 MiB bounds) and the activation lab (flat 1 MiB files) stay unchanged for their own tests. `scripts/runtime_manifest.py`, `update_package.py` and `managed_install.py` are the production adaptations.

## Locally supplied files

A package need not carry the game programs. A manifest entry written `{"supply": "local"}` (no digest, no bytes in the ZIP) is allowed only for the server jar, the client jar and server data files; the runtime scripts and `launcher.sh` must always be released and hashed. The intent: a player builds SoloScape from source once, and later releases ship only scripts plus the pins and patch hashes that build must match. See [the content classification](RELEASE_CONTENT_CLASSIFICATION_20261018.md) for what each group is and which questions stay open.

- **Registration:** `managed_install.py init … --supply-root <built source folder>` (up to four) or `managed_install.py supply-root <install> <folder>…`, which needs the exclusive lease. They are kept in `install.json`, which only the bootstrap writes.
- **Acceptance of a build:** at download time the first registered folder whose `.runtime/build-stamp.json` has exactly the manifest's `pins` and `patches` and whose jars still hash to that record is used. Otherwise nothing is staged and the player is told to update the source folder and rebuild, or to register one. Each local file is opened without following any link, must be an ordinary file under 512 MiB, and is copied with cancellation and the whole-job deadline; a file that grows or changes while copying is refused.
- **Result:** the copies land in the new version at their hierarchical paths and `supplied.json` records their sizes and SHA-256. The sealed version is then complete and independent of the source folder; validation, activation, rollback, pruning and the launch-time check are unchanged and re-verify it.
- **Trust:** a locally supplied file is trusted exactly as far as the player's own build is. The manifest pins its path and the source it must come from, not its bytes, because the jars are not reproducible across builds. `supplied.json` catches accidental damage and a mismatch with the recorded copy; it does not stop a user who can write to the install. A digest still proves only that the scripts are what GitHub listed.
- **Limits:** the updater never builds. A release that changes a patch or pin needs a local rebuild first and is refused with a plain message until then. An update that only changes scripts installs by itself.

## Update flow

1. **Check** (`release_updates.check`, 4 s socket timeout, 256 KiB bound, no redirects). A release may declare one `soloscape-package-*.zip` asset with `size` and `sha256:` digest, at exactly the fixed project's release-download URL.
2. **Download** on its own thread into a private scratch directory under the install's `staging/`; refuse growth beyond, or an early end before, the declared size; verify the SHA-256; honour cancel and the deadline on every chunk; follow redirects only to GitHub's two object hosts over HTTPS.
3. **Extract and validate** into a scratch directory, re-validate the whole tree with the manifest validator, require `release == tag`, then rename into `versions/<id>` and seal it read-only. An interrupted run leaves only scratch that the next run removes. Nothing runs from a candidate before the bootstrap has verified it.
4. **Install and Restart:** the launcher's advisory pre-check (no running world, no unresolved session records, saves readable by the candidate) writes `update-request.json`; the launcher stops its backend normally and exits 75.
5. **Apply** (bootstrap, no launcher running): acquire the **exclusive** lease without blocking, re-verify the candidate, repeat the checks below, write `trial.json`, publish `active.json` (temp file, fsync, atomic replace, directory fsync), prune versions that are neither current, previous nor the staged candidate, and relaunch.
6. **Trial:** if the new version exits with an error within 60 seconds of its first launch, the bootstrap rolls back (same checks) and relaunches the previous version, and the player sees why.

## Safety gates (all enforced by the bootstrap under the lease)

- **Live holders:** a shared lease held by a launcher, a world's game JVMs (each opens its own description of the guard and inherits it), or any other inherited copy makes apply/rollback fail with *still running*. A running profile lock is refused as well.
- **Unresolved sessions:** any profile with `session.json` blocks apply and rollback. The recorded original version, its context and its processes are kept (versions are not pruned out from under them, because apply cannot succeed while they exist).
- **Save format:** the bootstrap computes each profile's logical storage version from `saves/*.toml` with the pending `.soloscape-account-save` journal overriding canonical files (stdlib only, read-only) and refuses a candidate or rollback target whose `storage_versions` does not list it, an unreadable or inconsistent save, or a storage-version-1 world without its death-loot world file. Content is still fully validated by the version itself at launch.
- **No data movement:** apply and rollback change the pointer only. Nothing is restored, copied, migrated or deleted in profiles, backups, settings or cache, so rollback keeps progress made in the newer version; if the older version cannot read it, rollback is refused instead.

## Trust boundary

The package digest is taken from the same GitHub API response that names the asset. It shows the bytes are what GitHub listed for the release; it does **not** authenticate the publisher. The explicit trust source is GitHub HTTPS for `kannibalk1w1/SoloScape`: anyone who can publish a release there can publish an installable package. Independent signing is a possible later hardening, not required here. Manifest identities (`source_commit`, pins, patch hashes, `cache_revision`) are declared, not verified. The bootstrap is stdlib-only and is **not** updated by an update; changing it needs a reinstall. This is a cooperative single-user protocol, not a sandbox against a hostile local user.

## Evidence

### Tooling tests (original fixtures, production entrypoints)

The root suite passes **409 cases** (one existing optional skip), up from 315; `test_managed_supply.py` (30) covers locally supplied files. New files: `test_managed_install.py` (26), `test_update_package.py` (17), `test_update_manager.py` (13), `test_managed_runtime.py` (4) and one backend test for guard inheritance. All bytes are synthetic and labelled TEST; real-sized cases use 60 MiB random data. They cover:

- **Good update:** first install; stage; request; the bootstrap's `run` loop applies it and launches the new version with the external homes; saves untouched; old and new versions retained, third version pruned. CLI `init/status/activate/rollback` through the installed bootstrap copy.
- **No release / offline / no package / same label:** nothing is downloaded or changed; the installed version stays usable.
- **Corrupt, interrupted, hostile:** wrong or truncated or oversized or empty download, broken socket, HTTP error, lying digest/size, traversal, unlisted/missing files, `cache`/`.git` paths, format 1 manifest, symlink, FIFO and directory entries, duplicates, encryption, an inflated entry, a FIFO or link as the archive, a symlinked staging folder, a second staging run, leftovers of an interrupted run. None leaves a version, partial file or pointer change.
- **Bounds:** 60 MiB files install; cancel at start and during a blocked read (including a cancel racing the end of a read); a trickling server hits the whole-job deadline; closing the backend stops a download within two seconds.
- **Refusals:** unresolved session record, running profile lock, held lease, a lease inherited by an orphan after its parent closed, tampered candidate or current version, already-installed version, candidate that cannot read the logical save version (including a pending journal that overrides the canonical file), storage version 1 without a world file, damaged or non-integer saves, and a rollback target that cannot read newer saves. Refusals leave pointer and saves unchanged.
- **Crash recovery:** a forced process exit before and after the atomic pointer replacement leaves a parseable old or new pointer; the next run clears temp files and a stale trial record, and the new version stays rollback-able. A new version that dies at once is rolled back automatically unless the save format forbids it. A leftover request is single-use.
- **Rollback keeps newer progress:** bytes written in the newer version are still there after rollback.
- **Real backend over its stdio protocol:** managed identity, staged candidate, apply request, orphan-session refusal; owned game JVMs hold their own copy of the install guard.

### Private native acceptance

`experiments/managed-updater/acceptance.py` (see its [README](../experiments/managed-updater/README.md)) drove the **real** bootstrap, graphical launcher, native server (patch stack 54) and native client (stack 57) on an owned Xvfb display with mapped keyboard input, a disposable profile and copied cache, and two private packages. Two rounds are recorded: the first used two full 58.6 MiB packages built from the immutable 54/56 deck-export snapshot; the current one uses **code-only packages of about 87 KiB** (scripts, pins and patch hashes) plus a private stand-in build folder holding the snapshot's server jar and data, this checkout's built client jar and a matching build record, registered at `init` and used by the Download step for the 61 MB of jars and data. The build record is synthesized from the snapshot rather than produced by a Gradle rebuild, so this round does not exercise `prepare`. GitHub was replaced only at the backend's two network seams, with metadata labelled *PRIVATE TEST METADATA*. Sequence and result for either round (all checks true, [sanitized evidence](evidence/managed-updater-20261018.json)):

1. Install `private-test-a`; create a character through the real backend; **Start Character** logs in and saves (account `storage_version = 1`, native capabilities verified); stopped-world account fields recorded.
2. Updates dialog (A opens Settings, directional input to **Updates…**, A): identity shown; **Check** (A); B closes only the nested dialog and restores Settings focus, B returns to the launcher; reopen.
3. **Download** with progress; **Cancel Download** leaves no partial file or version; **Download** again to a verified staged candidate; while the launcher runs, activation is refused.
4. **Install and Restart**: the launcher exits 75, the bootstrap applies `private-test-b` under the exclusive lease, the relaunched launcher shows *Updated. Your characters, backups and settings were kept.* once.
5. **Continue** in `private-test-b` on the same world: compared account fields (name, experience, inventories, tile, storage version) equal; second native session verified.
6. A `private-test-c` candidate that only reads storage version 0 is staged and **refused** with the saves untouched. `rollback` returns the pointer to `private-test-a`; **Continue** there works with equal fields.
7. Six verified backups remain valid; the cache inventory is unchanged; both version payloads verify; two distinct version contexts exist; no staging leftovers.

![Download in progress, with a cancel button](images/managed-updater-downloading-20261018.png)
![Candidate downloaded and verified, ready to install](images/managed-updater-ready-20261018.png)

The same controller-modal ownership check (`scripts/harness/NativeLauncherUpdateProbe.java`, run by `scripts/smoke-launcher.py --updates`) covers a source copy: A opens Settings and Updates, notes stay plain text, the dialog explains that a source copy cannot install, nested B restores the parent, and a late check response never reopens a cancelled dialog. It passed 15 of 15 runs after lengthening the synthetic key hold (it had failed about one run in four before). The managed acceptance needed four earlier attempts before passing, each a harness or orchestration defect fixed in the tooling rather than the product: a `python3` PATH shim that also intercepted `python3 -c`, launcher focus after the game window closed on a display with no window manager, a lost synthetic navigation press, and a bookkeeping assertion about the one-time apply result. The final harness then passed on consecutive runs, the last on the committed code. This is **synthetic AWT key input mapped to controller actions, not SDL, Steam Input or hardware**.

Client patch stack 0001–0057 applies cleanly to a fresh clone of the pinned client and reproduces the built tree exactly (`scripts/verify_patches.py client` matches all modified files).

## Limits and open questions

- **Packaging and licensing are unresolved.** Full packages made by `package_builder.py --payload` / `experiments/managed-updater/build_packages.py` from a deck export contain the owner's authorized cache-free game data and jars and are **private test inputs, not releasable**. A code-only package (`package_builder.py --checkout`) contains only this project's scripts, so the items below gate it far less; see [the classification](RELEASE_CONTENT_CLASSIFICATION_20261018.md). The repository also has no licence file for its own code. The [runtime/notice inventory](RUNTIME_NOTICE_INVENTORY_20261017.md) still lists three unattributed local client jars (`clientlibs.jar`, `graphics.jar`, `trident-1.5.00.jar`), 52 server and 17 client artifacts with no detected notice file, embedded native libraries, inherited game/client/server-data provenance, and the separately supplied JDK/Python/font/art/cache inputs. Nobody has decided what a public package may contain. This blocks publishing, not the updater.
- **No public release has been published.** Fetching from real GitHub is covered by fake-transport tests and a native run whose GitHub seams are replaced; the live check still returns no public release.
- **First install** is `managed_install.py init` from a local package zip plus its digest. There is no graphical first-run installer, no Windows/macOS support (Linux x86_64, `flock`, `/proc`), and the owner's existing source/Deck install is not migrated.
- **Rollback is a command** (`managed_install.py rollback`) or the automatic first-launch trial; the launcher has no rollback button.
- The bootstrap's own code, Java 8/21 runtimes and the supplied cache are not updated by this path.
- Physical Deck, SDL controller, Steam Gaming Mode and audio acceptance were not run; the native probe uses synthetic AWT key events on a private Xvfb display.
- Disk-full and power-loss behaviour is not proven. The fsync/atomic-replace sequence and process-kill cut tests model a crashed coordinator only.
- Concurrent installs sharing profiles but not an install guard are not coordinated.
