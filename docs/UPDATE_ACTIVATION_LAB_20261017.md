# Update activation mechanism — 17 October 2026

A disposable, asset-free lab now proves that an active world lease excludes an updater and that code rollback can retain newer state bytes. It does not install updates in the launcher. [Mechanism and API](../experiments/update-activation/README.md); [sanitized evidence](evidence/update-activation-lab-20261017.json).

Claude Haiku implemented the initial module and multiprocess tests. Coordinator review found and fixed two prototype gaps before publication: concurrent shared holders could overwrite a pending marker, and opening a manifest-listed FIFO could block before its type was checked. A separate marker mutex and nonblocking/no-follow regular-file reads address those paths. The final tests include an actual contention barrier and exact owned-child cleanup through pidfds.

## Observed result

All14 mechanism cases pass. The full root suite runs261 cases with one existing optional skip and no failures. In a private copied module, deliberately changing exclusive requests to shared makes four assertions fail: world/apply exclusion, apply/start exclusion, ordered start and inherited-child exclusion. The actual module is unchanged by that negative control.

One stable installation guard sits outside immutable version directories. World/start leases are shared; apply/rollback is exclusive. A child inheriting the descriptor keeps the shared lease after its launcher exits; closing another descriptor never explicitly unlocks it. A start queued behind apply reads the new pointer only after acquiring its lease. The pointer names current and previous together and uses an expected-current comparison.

Sealed candidate verification bounds the manifest, membership, file sizes and digests. Tests reject tampering, malformed canonical JSON, extra files, links and a manifest-listed FIFO. A separate unresolved-session marker refuses activation even after every live lease is gone. Concurrent marker retention admits exactly one holder; wrong-identity clearing refuses.

Forced original coordinator exits immediately before and after pointer replacement leave the old or new complete pointer. Injecting directory-fsync failure after replacement reports an error even though the NEW pointer is visible: a caller must reread, rather than interpret every error as an unchanged version. Rollback changes pointers only, revalidates previous code, and preserves supplied newer state and both version directories.

## Limits and next gate

This is a cooperative filesystem protocol with stable guard inodes, not an adversarial same-user sandbox. It supports one lab marker; a real multi-profile installation needs an explicit session registry. No real candidate executes. Original inert children receive normal EOF or SIGTERM; no native game or owner process is touched.

Fsync calls, injected errors and process exits are not hardware power-loss acceptance. Real package authority, outer updater ownership, native multi-profile session/recovery checks, health confirmation, backup/compatibility policy and launcher/Deck integration remain open. The [prebuilt native lifecycle proof](PREBUILT_VERSION_LIFECYCLE_20261017.md) is separate evidence, not integration of this gate. [Grave/floor persistence](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains a P1. M13 stays open; no release or owner deployment occurred.
