# Getting and installing the game cache

The compatible download is the **pre-modified cache linked by the 2011Scape/Void
maintainers** in their [pinned server README](https://github.com/2011Scape/game-server/blob/9f9113559eb686abd917893b5dca16404be07f93/README.md#quick-setup).
This is an upstream-project source, not an official Jagex distribution.
The pinned README link was reverified through GitHub's API on 8 October 2026.

## Download

1. Open the [upstream cache folder on MEGA](https://mega.nz/folder/ZMN2AQaZ#4rJgfzbVW0_mWsr1oPLh1A).
2. Download the complete pre-modified revision-634 cache archive. The archive
   verified with our pinned builds is **`2026-08-02-void-634-cache.7z`**. Prefer that
   exact archive if it is still available; a newer archive is not automatically
   verified against these pinned commits. The older README calls it `cache.zip`,
   but the verified archive is `.7z`.
3. Use MEGA's browser download or its official desktop/command-line client if the
   browser has problems with a large download. If the link or archive is
   unavailable, check the upstream README/support channels rather than using an
   unrelated cache mirror.

## Extract into the server checkout

Use 7-Zip or another tool supporting `.7z`. From the SoloScape repository root,
with the upstream server already cloned:

```bash
mkdir -p upstream/game-server/data/cache
7z x "$HOME/Downloads/2026-08-02-void-634-cache.7z" -oupstream/game-server/data/cache
```

The verified archive contains the cache files directly. If an archive has a
wrapping folder, move its **contents** into `data/cache`, not another nested
`cache/` directory. Confirm these files are directly in that directory, alongside
all the other index files:

```text
upstream/game-server/data/cache/main_file_cache.dat2
upstream/game-server/data/cache/main_file_cache.idx255
upstream/game-server/data/cache/main_file_cache.idx0
... other main_file_cache.idx* files ...
```

For the exact archive above, optionally compare its bytes before extraction:

```bash
sha256sum "$HOME/Downloads/2026-08-02-void-634-cache.7z"
```

Expected locally recorded SHA-256:
`3d68394915bfbc717182d4924a9bd7c307ed070622853c4936333c75e345cc71`.
This is our recorded download hash, not a separately published upstream signature.

## Validate and launch

```bash
./scripts/doctor.sh
./scripts/dev-run.sh
```

Run doctor while no existing SoloScape server is occupying port 43594. It checks
cache file presence, Java and the local setup; it does not prove every asset is
compatible. A successful world load and playable login are the next checks.

**Launching the game does not fetch the server's missing archive.** Install it
first. After the server starts, the client downloads its assets from that local
server as needed. Initial client loading can therefore take longer.

The cache and download archive are not in the GitHub repository. Keep them,
player saves and local configuration out of commits and pull requests. There is
no automatic asset downloader in the launcher.

## Provenance of the development install

Downloaded 2026-10-08 with explicit user authorization, using the public folder
linked by the [pinned upstream README](https://github.com/2011Scape/game-server/blob/9f9113559eb686abd917893b5dca16404be07f93/README.md#quick-setup):

- Source: [upstream MEGA cache folder](https://mega.nz/folder/ZMN2AQaZ#4rJgfzbVW0_mWsr1oPLh1A).
- Selected archive: `2026-08-02-void-634-cache.7z`, the newest full cache listed.
- Archive size: **160,832,267 bytes**.
- Locally computed SHA-256:
  `3d68394915bfbc717182d4924a9bd7c307ed070622853c4936333c75e345cc71`.
  This records the downloaded bytes; it is not a separately published upstream hash.
- MEGA download integrity check passed; 7-Zip extraction completed without errors.
- Extracted 39 files, **193,740,377 bytes**, into
  `upstream/game-server/data/cache/`.
- Archive retained in `.runtime/cache-download/`; both locations are Git-ignored.

No automatic game-asset download was added to doctor or launcher. For a fresh
workspace, obtain the archive from the upstream link and extract its files
directly into the server cache directory. The client obtains its cache data from
the running local server.

Verification: doctor passes; the pinned server reaches world readiness in 3561ms
and runs save/shutdown hooks on SIGTERM. This establishes startup compatibility;
client rendering and per-character save/restart still require manual acceptance.
