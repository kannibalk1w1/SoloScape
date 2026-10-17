# Update staging lab — 17 October 2026

A small asset-free experiment now verifies an archive before publishing a new candidate directory. It is a package-staging boundary, not an updater or production package specification. See the [tool and provisional format](../experiments/update-staging/README.md).

Claude Haiku implemented the initial prototype and review fixes. Coordinator review added actual encrypted/unsupported ZIP-header controls, corrupt-DEFLATE cleanup after earlier writes, and a direct run of the repository CLI. The tests use original dummy launcher/client/server bytes. No real jar, cache, profile or owner installation is staged.

## Evidence

All24 staging tests pass; the full root suite runs189 cases with one existing optional skip and no failures. Rejected archives leave the input and unrelated lab sentinel unchanged. Cases include path traversal, private paths, symlinks/special entries, duplicate names/JSON keys, size/hash mismatch, limits, lock contention and partial-write cleanup. A raw NUL-name ZIP control demonstrates Python's name truncation; removing the guard in a private copy makes that same otherwise valid archive stage successfully.

The actual repository CLI stages one verified original fixture under ignored `.runtime/update-lab/<archive SHA-256>`. Repeating the command refuses the existing candidate and leaves its files and input unchanged. [Sanitized evidence](evidence/update-staging-lab-20261017.json) records exact input/tool hashes and scope. Private logs are under `.runtime/update-staging-20261017/`.

## Limits and next gate

Hash verification checks integrity against a supplied digest; it does not authenticate a publisher. Source commit, platform and cache revision are declarations, not detected runtime identities. There is no network request, execution, active-version pointer, real package builder, save migration or rollback. The small limits intentionally do not accommodate current game jars.

The final rename publishes a complete directory under a local lock. Files/directories are not fsynced, so power-loss durability is unproven. Tests cover a competing lock, not adversarial same-user filesystem mutation. The CLI confines itself to its ignored lab; its API accepts a disposable test directory.

Next define and validate a matched, asset-separated real package and its distribution notices, then prove stopped-world apply and code rollback on disposable state. M13 remains open. No release or owner deployment was performed.
