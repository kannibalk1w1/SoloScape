# Managed updater native acceptance (private)

Private tooling for the managed updater described in [MANAGED_UPDATER_20261018.md](../../docs/MANAGED_UPDATER_20261018.md). Production code lives in `scripts/` (`managed_install.py`, `update_package.py`, `update_manager.py`, `runtime_manifest.py`, `managed_runtime.py`); this directory only holds what is needed to exercise it against real bytes. **Everything it produces contains the owner's authorized game data and jars and must never be uploaded, published or installed over an owner profile or Deck.**

- `build_packages.py` builds two private test packages (`private-test-a`, `private-test-b`) from a deck-export snapshot read as an immutable input, this checkout's built client jar and runtime scripts. The packages differ only by manifest release label. No cache is included.
- `fake_github.py` stands in for GitHub at exactly the backend's two network seams (release discovery and the asset transport) when the launcher spawns `python3 <backend>`. Its metadata says *PRIVATE TEST METADATA*. Production code has no feed or URL override.
- `acceptance.py` installs code-only package A (jars and data copied from a private stand-in build folder registered with `--supply-root`) into a fresh disposable install root with its own profile/cache/launcher homes, then runs the real bootstrap, real launcher (`scripts/harness/NativeManagedUpdateProbe.java`, mapped AWT Robot keys on an owned Xvfb display), real native server and client (`NativeSessionSmoke` for login) through: play a world; Check; cancel a download; Download; Install and Restart; Continue in the new version; refuse a save-incompatible candidate; roll back; Continue again. It checks the logical account fields, backups, cache inventory and install state after each stage and writes `acceptance.json`.

```sh
python3 experiments/managed-updater/acceptance.py \
  --snapshot /absolute/path/to/deck-export-snapshot \
  --cache /absolute/path/to/authorized-cache \
  --server-java /absolute/path/to/java21/bin/java \
  --client-java /absolute/path/to/java8/bin/java
```

The snapshot and cache are only read; the run copies the cache and works under `.runtime/managed-acceptance/<id>/`. Input is synthetic keyboard mapped to controller actions on a private display: it is not SDL, Steam Input or physical hardware acceptance, and audio is excluded.

`--real-checkout` builds the player and maintainer source folders with the real `scripts/prepare-build.sh` (see `real_checkout.py`: disposable copies of this checkout's sources, shared Gradle cache) and adds a Java-changing release (`private-test-j`, an inert comment-only server patch) that must be refused with an actionable message, then rebuilt with `managed_install.py rebuild`, downloaded, installed and continued. It takes about 25 minutes and three Gradle builds. It also checks that `login.json` stays byte-identical and the generated password never reaches the install root, launcher home, probe output or bootstrap log.
