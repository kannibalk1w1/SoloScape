# Release delivery repair — 20 October 2026

The [player's report](https://www.reddit.com/r/SteamdeckGames/comments/1x55ui1/comment/phpxjyc/) is reproducible: Check and Close were the only available update actions. Both v0.5 and the initial v0.51 release had only installer assets. The installed updater accepts a `soloscape-package-<tag>.zip` asset; even its source-rebuild flow starts from that package's verified manifest. Instructions suggesting that Source and Rebuild works without that package were incorrect.

## Existing installs: repaired v0.51 release

The missing code-only [v0.51 update package](https://github.com/kannibalk1w1/SoloScape/releases/tag/v0.51) is attached now. Its SHA-256 is `b270e298eaf7f5aad887ca0cd63e50b76fdfb26c0097ee39196b3a73b35429bf`; it targets the original v0.51 source commit `a1c3d8c0f99a45fe46d611d51185e9c890de48b2`. The tag, source and original installer were not replaced.

The ZIP is 105,088 bytes: the manifest and 19 SoloScape runtime scripts, with the MIT notice in the ZIP comment. Jars and all server data are marked locally supplied in the manifest, and their bytes are absent. No game cache, art, fonts, Java runtimes, saves or local configuration are published. Downloaded release bytes and the GitHub API digest match the audited ZIP.

For a managed v0.5 install: **Launcher Settings → Updates → Check for updates → Download**. If the local build differs, **Update Source and Rebuild** becomes available. Let that finish, then choose **Install and Restart**. Keep the player's current Gaming Mode launch options. A first install has no previous version, so Roll Back remains unavailable until an update succeeds.

The original v0.5 Python updater, loaded from the v0.5 tag in a disposable directory, accepts this exact package. The check enables Download; a missing build enables Rebuild; source verification, staging, activation and rollback succeed with a synthetic profile/save unchanged. This check supplies the already prepared real local build through the rebuild callback: it does not claim a fresh native rebuild, physical Steam Deck input, or a real player's save was tested. A separate check of the live GitHub release confirms Download is now enabled for a managed v0.5 installation.

## Installer upgrade and future release assets

The installer previously skipped any valid existing install, regardless of its release. It now compares both release and source commit. A different target is built and staged under an exclusive install guard, then activated with the existing save-storage checks and rollback pointer. The old program remains available as the previous version. Same-target reruns remain idempotent; build failure, cancellation, incompatible saves and a running launcher refuse without changing the active version or saves. The installer never removes a valid install to upgrade it.

`scripts/build_release.py` creates the installer **and** code-only update ZIP together, with matching source identity, SHA-256 sidecars, `LICENSE.txt` and `release-assets.json`. It requires a clean committed source tree and a matching prepared build, audits the entire ZIP member list, checks script bytes against source and refuses shipped jars/data. Both ZIP-based artifacts include the MIT notice. Existing v0.5 manifest paths and format are retained for compatibility.

Release procedure:

1. Validate the change and commit the reviewed source. Run `./scripts/prepare-build.sh`.
2. Run `python3 scripts/build_release.py --release <tag> --out /tmp/soloscape-<tag>` using a new directory.
3. Create a draft release targeting that exact commit. Upload **every generated artifact**; do not substitute a deck export or a full private package.
4. Download both installer and package from the draft; compare bytes, API digests and `release-assets.json`. Verify the installer `--plan`, the package manifest's source identity and the legacy updater path before publishing.
5. Publish only after checks pass. Keep release notes explicit about local builds and physical acceptance.

Original regression tests cover installer upgrade/rollback, mutable homes unchanged, same-target reuse, changed source under the same label, busy launcher refusal, build failure/cancellation and storage mismatch. Release tests cover both artifact paths, source identity, dirty-tree refusal and refusing private payloads. Physical Gaming Mode acceptance remains separate.

All 533 tooling/installer tests pass (one optional skip). The new upgrade-activation regression fails against the original v0.5 installer because it returns early instead of switching versions, and passes after the fix. Both client/server patch stacks reproduce; the matched native source build remains unchanged by these Python delivery fixes.
