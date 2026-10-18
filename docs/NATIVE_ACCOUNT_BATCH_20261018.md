# Death-loot persistence integration: native account commit boundary

**Draft first implementation, 18 October 2026. The death-loot P1 remains open.**
This change is deliberately not merged or deployed until its surrounding recovery
contracts are reviewed. It replaces the actual native `FileStorage` account-save
loop, rather than adding another separate fixture-only storage algorithm. It does
not yet capture or restore a running world's graves or floor piles.

Baseline: native main `99f044a`, server 52/client 56. The incremental
[server patch 0053](../patches/server/0053-recover-native-account-save-batches.patch)
contains the storage change and native tests. Existing prepared build 52/56 and
owner installation are untouched; no production jar was rebuilt for this draft.

## Reproduced failure and implemented behavior

A new regression saves one original account, then asks native storage to update it
and a second account whose target is deliberately a nonempty directory. On the
previous production loop the first file advances before the second refuses. The
regression fails on that changed first-file byte comparison. With this draft,
preflight refuses the batch and both original targets remain unchanged.

For a valid batch, the new native `AccountSaveBatch`:

1. Replays any previously published pending batch before accepting a new save.
2. Serializes every supplied `PlayerSave` into a private staging directory. Checks
   account identity, bounded file size and SHA-256; forces each member and a sorted,
   versioned manifest to disk. No canonical account file has changed yet.
3. Atomically renames that complete directory to `.soloscape-account-save` and
   forces its parent. This is the commit decision; a fresh native reader must replay
   the entire committed batch before returning any account.
4. Validates every journal member and destination before installing any of them.
   Copies each through its own forced temporary file and atomic replacement, then
   forces the account directory. An exit during installation leaves a replayable
   complete journal, not a success receipt.
5. Atomically retires the journal after installation. Cleanup of the now-inert
   completed directory is best effort. A second exit during replay repeats the
   same exact installation instead of adding inventory quantities again.

`FileStorage.save`, `load`, `exists`, `names` and `clans` share the instance monitor;
account readers invoke recovery before using canonical files. Source inspection
found no production `PlayerSave.load` call outside these file-storage paths and
the batch verifier. Unpublished crash-stage directories are inert and may remain
for investigation. A published damaged journal refuses account access and stays
intact; it is never silently skipped in favor of mixed canonical files.

The native account TOML shape is unchanged. The journal is a new storage/recovery
contract, not a new account section. One owned server/storage instance is assumed,
as with existing launcher ownership; this is not protection against two independent
servers writing the same directory or an adversarial concurrent filesystem writer.

## Measured native tests

The checked-in coverage runner's `save` group now runs these four native suites:

| Suite | Cases | Failures / errors / skips |
| --- | ---: | --- |
| FileStorageTest, including the partial-write reproduction | 15 | 0 / 0 / 0 |
| AccountBatchRecoveryTest | 8 | 0 / 0 / 0 |
| Existing SaveQueueTest | 13 | 0 / 0 / 0 |
| Existing PlayerSaveTest | 2 | 0 / 0 / 0 |
| **Total** | **38** | **0 / 0 / 0** |

The crash test starts separate JVMs against original disposable account files.
Eight `Runtime.halt(73)` points cover both staged members, prepared state, published
decision, both installed members, materialization and retirement. Before publication,
the independent expected quantities are 10/0 coins. After publication/replay they
are 2/8. Native account readers must return the whole expected pair and total 10;
returning a merely schema-valid mixed pair fails. Another case exits during replay
and then performs two fresh reads. The qualified run uses 20 child JVM executions.
These are account storage fixtures, not actual death or guest-pickup simulations.

Further native cases preserve evidence while refusing corrupted complete/partly
installed journals, linked members, unknown/missing members, foreign account identity
even with recomputed checksums, and case-equivalent duplicate batch accounts.
Existing queue fallback/retry/confirmation tests remain passing. All 278 root
tooling cases pass with one existing optional skip. No graphical game or Deck
acceptance was run for this draft.

Reproduce with the supplied setup and a configured Java 21:

```bash
SERVER_JAVA=/absolute/path/to/jdk21/bin/java \
  bash scripts/test-content-coverage.sh --group save
python3 scripts/verify_patches.py server
python3 scripts/verify_patches.py client
```

Qualified private result:
`.runtime/content-coverage/1792312054251374246/summary.json`.
Source reproduction matches 107 server/140 client files. Earlier red and preliminary
green outputs remain in `.runtime/death-loot-integration-20261018/`; the final
runner selection and source/patch/XML/log digests are in the
[sanitized evidence](evidence/native-account-batch-20261018.json).
These forced process exits are not physical power-loss durability acceptance.

## Required next integration, before merging/deployment

- Capture grave and independent pile state from the live world, preserving charges,
  original ownership, merged piles, private/public counters, appearance, latest-grave
  marker ancestry and normalized instance destination. Add the world snapshot to the
  same durable commit decision as the relevant account snapshots; do not save it later
  in an unrelated file. Capture a logically coherent tick, not arbitrary queued account
  snapshots from different times beside a newer world ledger.
- Restore once at startup and reattach player UI on login, including offline owners;
  same-process relog and repeated cold restarts must never duplicate entities.
- Include pending journal interpretation in profile backup validation and recovery.
  Existing recursive backups copy these files but do not understand the journal's
  checksum/identity/commit semantics. A self-consistent ZIP alone is insufficient.
  The launcher's pre-launch backup and Save & Quit ordering must handle a pending
  committed batch without blocking the native recovery it needs.
- Explicitly gate incompatible older builds while a pending journal/new world format
  exists; older `FileStorage` versions do not replay this journal. Existing successful
  server 42/45 rollback evidence does not accept this new failure-state boundary.
- Route world-capture/write failures through current-session primary-save confirmation;
  do not confirm only the accounts. Prove actual native death, partial/failed pickup,
  offline-owner/public pickup, clean/forced restart, conservation and pause-while-closed
  timers through the original cold-JVM regression.
- Verify backup/export/import/corruption recovery, then physical controller/Deck use.
  No owner save transfer or deployment is authorized by this draft.

This first patch closes the reproduced per-batch account partial-write behavior in
its tested native storage path. It does **not** close the integrated death-loot issue,
choose every world-ledger field or authorize a broad storage rewrite.
