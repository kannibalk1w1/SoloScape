# Manage Backups

With a stopped character selected, choose **Manage Backups** in the graphical launcher. Choose how many automatic backups to retain (2–100, default 10). The launcher first displays the exact archive filenames and bytes proposed for removal. Confirming that list removes only verified automatic `before-launch` and `after-clean-shutdown` archives older than that retained count.

Manual and imported backups, damaged archives and every save generation remain retained. No pruning runs automatically. Cleanup holds the character's exclusive lock; it refuses a running world, symbolic-link backup storage and a changed preview. If another backup appears before confirmation, refresh the preview. Neither the active save nor previous generations are deleted.

Partial startup cancellation and unexpected client termination have disposable simulated-process tests. The launcher stops only owned child processes, waits for normal server save hooks, releases its profile lock after cleanup and records verified backups after a completed shutdown. It never forcibly kills a slow-saving server. These tests do not simulate every native-world load failure or power loss; the matched native New/Continue check supplies separate real-process evidence.

The native startup audit also fixed two server ordering issues: preload failures return immediately, and the shared-world save hook is installed only after `World.start` finishes. This avoids running world-save callbacks against partially loaded state during startup cancellation. Ready-world shutdown still uses the same normal save callback. The private smoke script now checks an observed early cancellation in a real JVM and compares every saved-world file; cancellation at every possible loading phase and sudden power loss remain separate risks.

The backup recorded by the latest restore's `restored_from` field is also protected. Verification may take time with a large backup history; the launcher reports work in progress while archives are checked. Automatic archive deletion remains opt-in.
