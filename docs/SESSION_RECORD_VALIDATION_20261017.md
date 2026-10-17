# Damaged session-record handling — 17 October 2026

Baseline: merged `8bf0e23`. A valid JSON session record with `children` set to a
list raised an uncaught `AttributeError` while the launcher listed characters.
Other malformed ownership fields could still be labelled recoverable. This was
reproduced with disposable profiles, not an owner's world.

The session reader now checks the shapes used by ownership verification before
returning a record: a string session identity, boot/phase strings, known child
roles, integer process identities, string jar paths and two integer lock
identities. Empty child records remain valid for the existing process-registration
crash gap. Unknown additional top-level fields remain untouched. These structural
checks do not replace the existing boot, process-start, environment, argv,
inherited-lock and pidfd checks.

Malformed records produce an unavailable-recovery status for that profile while
healthy characters remain listed. Recovery and ended-record archival refuse the
record before signalling or changing world state. The record is retained for
manual inspection; no automatic cleanup infers that a damaged record means its
processes have ended.

The regression covers eleven malformed forms, including invalid child containers,
unknown roles, boolean PIDs, non-integer start times, numeric session identities,
jar paths and lock shapes. It asserts:

- launcher character listing still succeeds for the healthy profile;
- automatic recovery is unavailable for the malformed record;
- recovery and archival raise validation errors without sending process signals;
- record bytes, healthy metadata and the backup directory remain unchanged.

Before the fix the new test produced five errors and six failed assertions.
Afterward all 16 recovery tests pass, including existing real-pidfd and inherited
lock checks against disposable simulated JVM processes. The full tooling suite
runs 132 tests successfully with one optional test skipped. These are lifecycle
harnesses, not proof of a real native server save, system suspend or Steam Stop.
Owner saves, cache and Deck installation remain untouched.

Reproduce:

```bash
python3 -m unittest discover -s scripts -p test_session_recovery.py
```

For physical follow-up, use only disposable copied profiles: a damaged record
should leave other characters usable and show recovery as unavailable. Do not
corrupt an active owner's record or infer that its processes can be stopped.
