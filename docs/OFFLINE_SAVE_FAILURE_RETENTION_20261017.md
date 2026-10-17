# Failed offline save remains retryable — 17 October 2026

A failed logout snapshot could disappear from the pending queue after its retry window, even if both primary and fallback storage failed. At shutdown, that offline player was absent from the live collection and the pending set. The native primary writer accepted an empty batch and final confirmation reported success. A successful fallback also wrongly retired the primary retry and allowed the existing login gate to stop protecting the account.

Server patch0042 retains previously queued snapshots after fallback handling. Only a successful primary write retires the matching pending snapshot. Existing `saving(name)` therefore continues to block stale relogin. Primary retries continue; clearing the fallback failure timestamp restarts its existing cooldown so ordinary repeated failures do not dump fallback every tick. Fallback files remain recovery evidence.

## Native reproduction and checks

Three independent red tests use the actual `SaveQueue` and `FileStorage`, not a writer mock. Original account paths are deliberately made nonempty directories to refuse native atomic replacement. With both paths refused, and separately with a working fallback, the pre-fix final primary callback incorrectly returns true. The third test proves the offline snapshot was dropped instead of remaining retryable.

After the fix, both final callbacks return false. Opening only the test's primary target lets a later queue tick save the original snapshot, clear pending and retain the fallback evidence. Existing in-flight/newer-snapshot and primary-confirmation regressions pass too.

The native SaveQueue suite passes13 cases. A new official `--group save` routes the coverage runner to the engine module, alongside the two PlayerSave snapshot cases:15 selected cases, no failures or skips. All87 modified/patched server source files match the exported stack. [Sanitized evidence](evidence/offline-save-failure-retention-20261017.json) includes the three red failures, fresh suite counts and42 patch identities.

```sh
SERVER_JAVA=/path/to/java21/bin/java bash scripts/test-content-coverage.sh --group save
```

Private artifacts: `.runtime/offline-save-failure-20261017/`; official summary: `.runtime/content-coverage/1792259966859702518/summary.json`. These exercise the real native queue and disk writer through API calls. They do not perform a network logout, issue a Main-process shutdown receipt, simulate a power cut or establish Deck acceptance. The source-wired login/AutoSave consequences follow from those callers' existing pending/primary-result gates. Grave restart persistence remains a separate open P1.
