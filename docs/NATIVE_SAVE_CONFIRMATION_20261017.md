# Native primary world save confirmation (2026-10-17)

## Problem

`SaveQueue` catches primary storage errors and, when fallback storage also fails, logs and returns. A `direct().join()` could therefore complete normally with neither the latest primary nor the fallback written. `Main`'s shutdown hook exited with the same status either way, so artifact checks could not prove a current primary save when error artifacts also could not be written.

## Change (patch 0034)

- `SaveQueue.direct` takes an optional `onPrimaryResult: (Boolean) -> Unit` callback, default `{}`. Existing `direct().join()` callers are unchanged.
- The callback is invoked once per direct save, inside the existing launched job:
  - `true` after primary `storage.save` succeeds and pending/failing bookkeeping has completed.
  - `false` after primary `storage.save` throws, whether or not the fallback then succeeds.
- Launch behaviour, retry semantics, fallback recovery bytes and the pending queue are unchanged. There is no mutable global last-result.
- `AutoSave` `worldDespawn`: await in-flight saves, join the direct save with a per-call result, attempt `exchange.save()`, then reject an unconfirmed primary result. Coordinator review moved the check after the exchange attempt to preserve the best available exchange snapshot when player storage fails. Either failure still prevents confirmation.
- `Main` shutdown hook: `GameLoop.shutdown` (cancelAndJoin then save) is unchanged. Inside the save lambda, after `World.shutdown()` returns successfully, it prints `SOLOSCAPE_WORLD_SAVED_V1 <session>` when `SOLOSCAPE_SESSION_ID` matches `[0-9a-f]{32}`, then calls `AuditLog.save()`. The marker is emitted before the audit save because audit output is not part of the world save.
- No marker on failure (the exception propagates out of `World.shutdown`, so the marker line is never reached). No marker without a valid owned-session id. Standalone runs without the env var are unaffected.

## Tests

- `:engine:test --tests world.gregs.voidps.engine.data.SaveQueueTest` (JDK 21, `--offline`, under `.runtime/build.lock`): 10 tests, 0 failures, 0 errors. The 3 new tests cover primary success (`[true]`), primary failure with fallback success (`[false]`), and primary plus fallback failure (`[false]`), each asserting exactly one callback after the joined job. The 7 existing tests remain green, including fallback and save serialization.
- `:game:compileKotlin` (JDK 21, offline, build lock): BUILD SUCCESSFUL. This verifies `AutoSave` and `Main` compile. No game tests were run.
- `scripts/verify_patches.py server`: all 74 modified/patched source files match the exported stack.
- Patch 0034 applies forward to the pre-edit snapshot and reproduces the edited files byte for byte. It reverse-checks cleanly against the applied tree.

## Launcher integration and actual native verification

Normal and orphan-session shutdown now require the exact current-session receipt
before publishing a verified post-stop backup or clearing the session record.
Missing receipts, another session's receipt and a marker embedded in unrelated
text are rejected. Existing pidfd, ownership, artifact and structural-save checks
remain necessary. Early cancellation before world readiness has its own path.

The first real native run found an integration defect: the console logger leaves
ANSI colour resets before raw `println` output, so strict raw-line matching rejected
a correct receipt. The parser now removes only ANSI SGR sequences before requiring
the exact whole line. Positive harness receipts use that native colour format.
All 140 tooling tests pass with one optional skip.

A matched pair was rebuilt, then run through the checked-in private-display probe:

```bash
bash scripts/prepare-build.sh
bash scripts/smoke-profile.sh --save-quit --save-failure
```

New and Continue complete-session times were 21.961 and 22.722 seconds. These
include native readiness and save/shutdown on an uncontrolled host, not FPS or
Deck timing. XP, inventory and tile match across the real JVM restart. Early
startup cancellation preserves the entire saved world's bytes.

The additional run makes only the disposable profile's primary and fallback
directories unwritable after verified native login. Both native writes fail and
produce no save-error/temporary artifact; the earlier primary remains readable
and byte-identical. The save callback reports failure, the native hook emits no
receipt, and the launcher refuses clean closure despite an expected JVM exit.
Only the pre-launch backup is added. The unverified record survives, then the
existing explicit ended-session archive and verified backup restore recover a
clean generation while preserving the failed generation. Permissions are restored
after the owned processes have stopped. The probe refuses root execution, linked
storage and profiles outside its private smoke directory.

[Evidence](evidence/native-save-confirmation-20261017.json) records source, patch,
jar identities and the native success/failure summary. Owner/legacy mutable-path
fingerprints are unchanged. No Deck installation or owner character is modified.

## Compatibility and limits

The reader is deliberately conservative: an older running native server that
cannot emit the receipt cannot confirm a recovered session automatically. Its
record and backups remain available to the existing ended-session archive/restore
workflow. Rebuild the matched local pair before testing these source changes.
Standalone server execution without a launcher session does not emit a marker.

The receipt reports the primary player snapshot plus successful world-despawn
hooks, including exchange storage. It is emitted before audit-log persistence;
audit output is outside this world-save confirmation. It does not prove every
last intended controller input reached the server, nor that a browser/device
suspend is safe. Human Save & Quit, Steam Stop and Gaming Mode acceptance remain
open. No deliberate failure was injected into owner data.
