# GitHub launcher updates

Requested17 October2026. The first implemented increment is **manual release discovery**, under Launcher Settings → Check for updates. Receiving and applying a complete playable update remains separate work. No GitHub release has been published by this workflow; the live public check on17 October returns `no_public_release`.

## What works now

The launcher requests metadata only from `kannibalk1w1/SoloScape`'s stable latest-release endpoint. It displays published release text as plain text, or a clear no-public-release/offline result. It never downloads an asset, pulls Git, executes release instructions or changes a profile. There is no installed release identity yet, so a published tag is not presented as proof that an installed development build is older or current.

The check is explicit, with no network requirement at launcher startup. A check from this backend is refused while its world worker is active, keeping network waits out of the Save & Quit request path. A bounded response size, socket timeout, fixed repository URL and rejected redirects constrain discovery. Rate limits and connection failures leave the installed version usable through its existing launch flow.

The real Swing probe exposed a controller problem beyond updates: calling modal button actions directly inside the controller timer prevents that timer from reading subsequent input. Button activation now runs on the next UI event after verifying window/focus ownership. Nested launcher dialogs belong to the same controller owner chain; B closes one dialog and restores its parent's focus. The probe checks settings navigation, A, nested B ancestry and a late response after Settings was cancelled. This is mapped input on private Xvfb, not SDL/hardware acceptance.

GitHub documents stable release metadata and asset digests in its [Releases API](https://docs.github.com/en/rest/releases/releases?apiVersion=latest). The current checker uses no account token and accepts no user-supplied feed or download URL. Release notes are data, not trusted instructions. Asset digests are for a later package verifier; none is downloaded by this increment.

## Why installation is a separate stage

Current delivery is a development checkout/private Deck snapshot. `scripts/deck_export.py` deliberately includes the owner's authorized cache, launcher art and local JDKs. **It is not a public release builder.** Do not upload its output to GitHub Releases.

Profiles and backups currently live at `.runtime/profiles` inside the installation. Shared cache and legacy saves also live under that tree; launcher settings and local runtime paths are installation-relative. A blanket directory replacement or clean can destroy state. An ordinary Git pull does not itself delete ignored profiles, but it supplies neither a verified playable bundle nor a rollback transaction.

A normal build stamp proves matched local pins, patches and jar bytes. It is not a release manifest. The public repository currently has no approved playable package, stable installed release identity, distribution licence inventory or tested version rollback. M13 remains open.

## Next implementation order

1. **Stable saved-state location:** [optional external profile storage](PROFILE_LOCATION_20261017.md) is implemented and tested without moving existing defaults. The managed installer must select/preserve that location and settle earlier session records before changing versions. Other mutable/shared paths still need their own contract.
2. **Asset-separated package contract:** a manifest identifies exact source commit, supported platform, both client/server builds, pins/patches, save-format compatibility and required separately supplied cache identity. The [private prebuilt-server closure probe](PREBUILT_NATIVE_SERVER_20261017.md) boots the real empty server from its jar plus selected data and a separate cache copy. Graphical launcher/preflight integration is still open. Public package contents and dependency/runtime notices need distribution review. Never bundle private cache, art, credentials, configuration or saves.
3. **Stage a candidate:** download only declared assets from the fixed release repository, verify size/hash and manifest, reject traversal/links/unlisted files, and unpack to a new version directory. Interrupted/invalid staging leaves the active version untouched. The [original-fixture staging lab](UPDATE_STAGING_LAB_20261017.md) now proves bounded local verification, candidate publication and rejection cleanup. Real package identities, network download, interruption durability and apply remain open.
4. **Explicit stopped-world apply:** a persistent updater outside replaceable versions takes its install lock and verifies all owned sessions/recovery records are resolved before switching a version pointer. Revalidate the candidate and prepare verified pre-update backups. No background overwrite of a running launcher, client or server.
5. **Health check and code rollback:** retain the previous version, launch the matched candidate, record confirmation and offer rollback on failure. Code rollback must not silently restore an older character backup and discard subsequent progress. Incompatible save migrations need a separate explicit recovery path.
6. **Controller/Deck acceptance:** inspect update notes, cancel checks/staging, resume after interrupted downloads, apply, continue an existing character and roll back on a disposable world before any owner install is changed.

No automatic release publishing, paid service, cache redistribution or owner deployment is authorized by adding discovery. Publishing and installing remain held until there is a concrete reviewed package and acceptance evidence. The updater should eventually make routine updates easy; it should not turn daily play into a source-build workflow.

## Verification

Seven asset-free tests cover valid/null metadata, malformed or oversized input, alternate repository URLs/tags, redirects, no-release/offline/rate-limit/server responses, an active-world check followed by Stop, and rejected apply/custom-feed requests. The full root suite passes159 cases with one optional skip. The real API check returns no public release. Native Swing evidence and screenshots are recorded in the dated [discovery report](GITHUB_UPDATE_DISCOVERY_20261017.md).

Account backups currently do not retain unrecovered grave/floor state. The [cold-JVM grave probe](GRAVE_COLD_JVM_PROBE_20261017.md) reproduces that gap. The owner selected pause-while-closed grave expiry on17 October: preserve loot and its remaining lifetime while the local world is stopped. The [persistence plan and native storage boundary](GRAVE_PAUSE_PERSISTENCE_PLAN.md) record that policy and its recovery requirements; persistence is still unimplemented. Resolve the gap before describing a full update as preserving all world progress.
