# Surviving launcher failure

Owned server and client processes inherit the launcher's build and profile lock file descriptors. If the launcher is killed abruptly, those same kernel lock descriptions remain alive until the last owned JVM exits. A second launcher, restore, backup mutation or source preparation therefore cannot modify an active world's storage or replace its archives. Normal Save & Quit still waits for save hooks and then verifies a backup.

An abrupt launcher death does not perform a clean shutdown or create an after-clean-shutdown backup. Surviving game processes retain the original world; close the game normally before recovering through the launcher. Recovery never kills unrelated processes or claims a crash was a clean save.

Verified with a disposable launcher killed by SIGKILL: both simulated JVMs survived; profile backup and exclusive build lock acquisition were rejected; only the existing prelaunch backup existed. After graceful shutdown of those owned children both locks released. All 45 root tests pass. Separate real Java 8 and Java 21 child probes confirmed the native JVMs retain inherited lock descriptors. Full game process-death/reconnect acceptance is still pending.
