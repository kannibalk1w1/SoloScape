# Surviving launcher failure

Owned server and client processes inherit the launcher's build and profile lock file descriptors. If the launcher is killed abruptly, those same kernel lock descriptions remain alive until the last owned JVM exits. A second launcher, restore, backup mutation or source preparation therefore cannot modify an active world's storage or replace its archives. Normal Save & Quit still waits for save hooks and then verifies a backup.

An abrupt launcher death does not perform a clean shutdown or create an after-clean-shutdown backup. Surviving game processes retain the original world; the launcher now offers ownership-checked Recover Session to request graceful shutdown. Recovery never kills unrelated processes or claims a crash was a clean save.

Verified with a disposable launcher killed by SIGKILL: both simulated JVMs survived; profile backup and exclusive build lock acquisition were rejected; only the existing prelaunch backup existed. After graceful shutdown of those owned children both locks released. All 45 root tests pass. Separate real Java 8 and Java 21 child probes confirmed the native JVMs retain inherited lock descriptors. Full game process-death/reconnect acceptance is still pending.

## Journeys recovery checkpoint — 10 October 2026

Private durable session records and Linux pidfd identity checks now enable explicit Recover Session; recovered snapshots are verified and retain previous backups, with clean shutdown unconfirmed. Outstanding records block restore generation changes; ended records can be explicitly archived and preserved. See [launcher recovery](ALPHA_LAUNCHER.md). The real Java 21 server probe passed inherited-guard/identity verification, graceful recovery and snapshot validation. Repeated native graphical New/Continue and early cancellation passed separately. The root suite now has 62 cases; earlier 45-case evidence above is historical. Native orphan-client and exhaustive crash timings remain unclaimed. [Current validation](CONTROLLER_JOURNEYS_VALIDATION.md) records the precise scope.
