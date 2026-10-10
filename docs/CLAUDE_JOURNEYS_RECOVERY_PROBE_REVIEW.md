# Journeys: real-server orphan recovery probe review

This was a bounded static review of `scripts/smoke-recovery.py`, with a brief second look at
`scripts/session_recovery.py`. I ran no probe, build or game, made no source, test, process, git
or network changes, and opened no saves, cache or credentials.

## Verdict
**No blockers.** Isolation, the parent-only crash, ownership-checked recovery and the evidence
fields are sound. There is **one medium cleanup gap**: if the disposable parent dies *before*
the probe kills it, the real server can be left orphaned (finding 1). Two low notes follow. I
found no severe ownership or restore risk left in `session_recovery.py`.

## Verified
- **Isolation.**
  - The profile is created under `.runtime/recovery-tests/<ns>/profiles`. That path is set in
    the probe and passed to the parent, so the server's mutable `storage.*` paths are private.
  - It uses a separate loopback port, 43596, checked first with `probe_port`.
  - The legacy `upstream/game-server/data/{saves,errors,.temp}` files are fingerprinted before
    and after, and must be unchanged.
  - The client is disabled.
- **Parent-only crash.**
  - The probe waits for `phase == 'playing'` with a registered `server` child.
  - It then `kill()`s **its own `Popen` child**, the Python parent. The server runs in its own
    session (`start_new_session`), so it survives holding the inherited guards.
  - No discovered or manual process is ever targeted.
- **Recovery.**
  - `inspect` must report `recoverable` and `active == ['server']`. That requires the full
    `verified()` check (boot, start time, uid, session, role and saves path in the environment,
    exact jar in argv, both `FLOCK` guards).
  - `recover` then stops the server through its pidfd with SIGTERM and no kill.
  - Afterwards the probe asserts that the record is gone, that the backup reasons are exactly
    `before-launch` and `after-recovered-shutdown`, that the legacy fingerprint is unchanged,
    and that the profile and build locks can be taken.
- **Truthful evidence.** `summary.json` is written only after every assertion passes, and it
  records `clean_shutdown_confirmed: False` with "Real native server only; no
  player/client/hardware claim". `inherited_guards_verified` really is implied by `inspect`'s
  `active` list.
- **Normal failure cleanup.** If the parent is still alive (for example a startup timeout),
  `finally` calls `terminate()`. The parent's SIGTERM handler sets `cancelled`, so
  `profile_session` runs its normal stop and save hooks, and `wait()` has no timeout.

## Findings
### 1. Medium: an early parent death leaves the real server orphaned
The ready loop raises when `parent.poll() is not None` (`smoke-recovery.py:49-50`). In that case
`orphaned` is still `False`, and `finally` does nothing more for an already-dead parent
(`:75-79`). If the parent died after `Popen` and `registered()` but before `playing` (for
example a Python exception in the parent, or the OOM killer), the native server keeps running.
It holds the disposable profile's lock, the **shared** `build.lock` and port 43596. While it
runs, every later `prepare`, building launch or exclusive `build_lock` is refused.

**Fix:** in `finally`, decide on `session_recovery.read(profile)` rather than the `orphaned`
flag. If a record exists and `inspect(profile)` reports `recoverable` with any `active` role,
call `recover(...)`. Keep it ownership-checked, as now. Otherwise report the record path so the
user can use the launcher's Recover or Archive.

### 2. Low: a second `recover` failure hides the first error
If `recover()` raises at `:57`, `orphaned` stays `True`, and `finally` calls `recover()` again.
That can raise a second exception, which replaces the original traceback. **Fix:** wrap the
cleanup `recover` in `try/except` and print its error to stderr, so the original failure
surfaces.

### 3. Low: the final exclusive build lock is affected by unrelated sessions
`with local_dev.build_lock(): pass` (`:68`) uses the real `.runtime/build.lock`. If the user is
playing a real world at the same time, it raises after a recovery that succeeded, and reports a
false failure (no unsafe effect). **Fix:** make the lock checks conditional, or note the
precondition that no other owned world may be running.

## `session_recovery.py` re-check
I found nothing new at high or medium severity:
- the owner is scoped by `owner_active`;
- restore is guarded by `session.json`;
- `archive_ended` renames under the recovery, build and profile locks after a full scan finds
  no live process;
- argv and environment comparisons are exact;
- every signal goes through a pidfd that was opened before verification.

## Limits
- Static only. I didn't execute the probe or the 176/61 test suites; those results are as you
  reported them.
- The probe covers the native **server** lifecycle only. Player New/Continue, the client, a
  physical controller and Steam Deck behaviour are not claimed.

## Codex changes following review

The probe now bases final cleanup on the durable session record rather than its intentional-crash flag. This also covers an unexpected early parent death and triggers ownership-checked discovery of a Popen/record crash gap. Cleanup errors are reported separately so the original probe failure survives. The native parent's SIGTERM handler sets its cancellation event and waits for normal owned hooks. The final exclusive global-build-lock assertion was removed: another legitimate owned world can share the archive guard without invalidating this probe. The recovered profile lock still has to be released, and process/guard identities were checked before the signal.
