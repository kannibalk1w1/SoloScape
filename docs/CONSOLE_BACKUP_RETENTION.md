# Manage Backups

With a stopped character selected, choose **Manage Backups** in the graphical launcher. Choose how many automatic backups to retain (2–100, default 10). The launcher first displays the exact archive filenames and bytes proposed for removal. Confirming that list removes only verified automatic `before-launch` and `after-clean-shutdown` archives older than that retained count.

Manual and imported backups, damaged archives and every save generation remain retained. No pruning runs automatically. Cleanup holds the character's exclusive lock; it refuses a running world, symbolic-link backup storage and a changed preview. If another backup appears before confirmation, refresh the preview. Neither the active save nor previous generations are deleted.

Partial startup cancellation and unexpected client termination have disposable simulated-process tests. The launcher stops only owned child processes, waits for normal server save hooks, releases its profile lock after cleanup and records verified backups after a completed shutdown. It never forcibly kills a slow-saving server. These tests do not simulate every native-world load failure or power loss; the matched native New/Continue check supplies separate real-process evidence.
