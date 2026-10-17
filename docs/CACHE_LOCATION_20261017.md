# External cache input — 17 October 2026

`SOLOSCAPE_CACHE_HOME` selects a shared cache directory outside a replaceable code tree. The existing source default stays `upstream/game-server/data/cache`. The selector reads configuration without creating, copying or migrating data. Doctor checks the selected input; source and profile launches explicitly pass it as the native server's `storage.cache.path`. An inherited dotted property cannot redirect a profile launch. The client still uses its profile-owned writable cache and receives content from the local server.

Invalid explicit configuration fails before the profile backup, session record or child process is created. Empty/relative/NUL paths, files and a symbolic link at the selected directory are refused. Missing input files remain doctor errors. This is not a cache revision detector, a filesystem race defence or a claim that arbitrary supplied caches are compatible.

Seven additional tooling cases cover selection/no writes, invalid configuration, doctor diagnostics, inherited-path removal, actual simulated child environment and refusal before session mutation. All 207 root tests pass with one optional skip.

The real `profile_session.run` path was also exercised with doctor enabled, a new disposable profile, client disabled and the private cache copy from the prebuilt-server probe. An intentionally unavailable inherited cache property was overridden. The native server reached ready, confirmed its fresh primary-save receipt, produced two verified fixture backups and closed normally in 5.041 seconds overall. All 39 cache file hashes stayed unchanged. No account logged in or was saved; this does not establish character, GUI, controller or Deck acceptance.

[Sanitized evidence](evidence/cache-location-20261017.json). No owner installation/accounts were accessed, and no cache bytes or binaries are committed. Profile storage and original-version recovery/build locks keep their existing contracts. Public package construction, shared art/settings and update activation remain separate work.
