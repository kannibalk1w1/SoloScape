# Persisted list save snapshots — 17 October 2026

Queued account saves now own a copy of each persisted list container. Native bitwise variables use mutable lists for music unlocks, quick prayers, found penguins and other flags. Previously `Player.copy` copied the outer variables map but retained the live list, so later gameplay changes could alter an earlier captured save. The fix copies those native list containers into the existing native mutable list type. Scalar and temporary-variable behavior is preserved; no save schema changes.

Claude Haiku traced the actual mutation/copy/codec path and added five native cases through public `SaveQueue` and real `FileStorage`. Three failed before the fix and two controls passed:

| Ordering | Before on disk | Capture-time value now saved |
| --- | --- | --- |
| Capture penguin 0, then add penguin 1 | penguins 0 and 1 | penguin 0 |
| Capture two quick prayers, then remove thick skin | rock skin only | thick skin and rock skin |
| Pause IO writer after capture, add penguin 1 on test/game thread, release writer | penguins 0 and 1 | penguin 0 |

The controls verify a persisted scalar remains its captured value and non-persistent variables stay excluded. All use configured native variable names/definitions, literal expected values and private primary/fallback directories. The barrier always releases and drains in `finally`. This proves snapshot fidelity under a deterministic ordering; concurrent-writer exception frequency was not measured.

Fresh final validation: five snapshot cases, fifteen engine save cases and three existing native journey cases pass without skips (23 total). The new standard `--group snapshot` runner archives fresh selected XML, rather than relying on an ad hoc reproduction command. Server 44/client 56 patch reproduction matches 90/140 files, and matched jars/stamp rebuild passes. The initial red run only used a private Gradle override to disable fail-fast and observe all cases; final validation uses the normal runner.

The change covers the current flat native persisted-list values; it does not define a recursive snapshot contract for arbitrary nested object graphs or clone temporary runtime references. The database backend is not exercised here. Account snapshot fidelity does not establish whole-world transactionality or grave/floor persistence, which remain separate requirements. No owner account, installation or Deck data was used. Physical play remains unaccepted for the new build.

[Sanitized evidence](evidence/save-variable-snapshots-20261017.json). Private archived reds and saved files: `.runtime/save-variable-snapshot-20261017/repro/`. Reproduce with `SERVER_JAVA=/absolute/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group snapshot`.
