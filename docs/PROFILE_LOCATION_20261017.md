# External profile location — 17 October 2026

An optional `SOLOSCAPE_PROFILE_HOME` now lets a managed launcher version use a stable directory containing its profiles. With the variable unset, the location remains `.runtime/profiles` under the current code root. This is a GitHub-update prerequisite, not an installer or migration. No existing directory is moved or copied automatically.

An explicit value must be a nonempty absolute directory path, without NUL, and cannot itself be a link or existing regular file. Invalid configuration fails before profile writes; it never silently falls back to another empty character list. As before, ancestor links are not newly prohibited. Configuration is read once when the Python backend imports its profile module.

For an intentionally selected profile directory:

```sh
SOLOSCAPE_PROFILE_HOME=/absolute/path/to/profiles ./scripts/launcher.sh
```

Choose the directory containing profile-ID folders, not an individual character or generation. An empty directory gives an empty character list; it does not import the old profiles. Save & Quit and resolve recorded sessions in their original code/build context before changing versions or choosing another location. Native recovery records retain absolute jar paths and build-lock identity. This change does not rewrite those records or authorize a new build to stop processes owned by an old build.

## Evidence

Claude Haiku implemented the small location selector and five disposable subprocess tests. Copies of `profiles.py` in two different code roots create/save/back up/restore/discover one external profile through the existing checksummed native-save format. The old default directory remains byte-for-byte unchanged. Invalid paths fail both direct selection and the actual module-import/create path without profile writes. Tests suppress Python bytecode output to keep their filesystem snapshots specific to this boundary.

Coordinator review adds environment isolation for simulated backend children and launcher smokes. The variable is removed from owned game JVM environments, where the already resolved per-profile storage paths are authoritative. The real Swing launcher regression runs with an inherited **disposable** profile-home canary; the probe still creates its own private fixture profile and leaves the unselected canary unchanged.

A simulated owned-session regression also changes the build-lock context while keeping the same profile: the other context cannot recover, signal or archive the live earlier world, and its record remains identical. Returning to the original context recovers normally. This is a process/lock fixture, not a network game/version-rollback test.

All165 root tooling cases pass, with one existing optional skip. Native launcher evidence: `.runtime/profile-location-20261017/native-ui-1792256379031704056/summary.json`; full-suite log `coordinator-tooling-final.log` in the same private directory. [Sanitized evidence](evidence/profile-location-20261017.json) records the canary fingerprints and scope. No owner path, Deck installation, real save migration or game-world deployment was used.

## Remaining updater work

Profiles, generations, backups, session logs and per-profile client homes can now stay in one selected directory across code roots. Cache, legacy saves, runtimes, launcher settings and build/install locks still need an explicit managed-install contract. Package staging, global apply locking, version pointer changes, save migration and rollback are not implemented here. A live/recoverable earlier session must be settled before any future installer switches builds. This does not resolve the separate [unrecovered grave persistence gap](GRAVE_COLD_JVM_PROBE_20261017.md).
