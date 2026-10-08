# Local cache installation

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
