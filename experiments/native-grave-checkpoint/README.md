# Native grave checkpoint: process-exit ordering proof

Disposable mechanism experiment. It asks whether a tiny immutable-generation publication keeps two native account snapshots and one grave/pile ledger coherent when the JVM exits abruptly at each publication boundary. It is not a production storage rewrite, not a save-format change, and not evidence that grave persistence works.

```sh
python3 experiments/native-grave-checkpoint/run.py \
  --server-jar /absolute/path/to/void-server-dev.jar \
  --sha256 YOUR_LOCALLY_VERIFIED_JAR_SHA256 \
  --java /absolute/path/to/jdk21/bin/java \
  --javac /absolute/path/to/jdk21/bin/javac
```

Each run writes to `.runtime/native-grave-checkpoint/<unique-run>/` (ignored). The runner verifies the jar digest before and after, refuses symlinked lab ancestors, refuses an existing run, never cleans up failures, and records the helper and runner hashes.

## Files

- `GraveCheckpointHelper.java`: fixture-only helper with modes `baseline ROOT`, `attempt ROOT POINT|none`, `recover ROOT`. Accounts are written through `PlayerSave.Companion.load` and `FileStorage.save(List)`. Coins are native `inventory` `Item` slots counted with `rawValue()`, which does not touch item definitions or the cache.
- `run.py`: stdlib runner. It compiles the helper against the trusted jar, runs 14 cases with fresh roots and separate JVMs, independently asserts every recovered field, and writes `summary.json`.

## Layout and ordering

`state/CURRENT` holds the generation name and the SHA-256 of that generation's `MANIFEST`. A generation holds `alpha.toml`, `beta.toml`, `ledger.txt`, and `MANIFEST` (SHA-256 and byte length per member). Publication stages in `state/partials/`, writes and fsyncs each file, fsyncs the directory, renames the stage to `state/generations/gen-NNNNNN`, writes and fsyncs `CURRENT.tmp-*`, atomically replaces `CURRENT`, and fsyncs `state/`.

Recovery reads only `CURRENT` (512-byte bound). It checks every ancestor path for links, then the exact pointer shape, the generation's entry set, the manifest hash, and the manifest regenerated from member bytes. Only after that does it native-load both accounts. It then requires after native loading, the exact tuple for one known generation: account names, coins, `state_version`, and ledger pile, remaining ticks, and version. Unknown labels refuse. Orphan or partial generations are never scanned.

## Results (coordinator run `1792259555968822957`, all14 cases passing)

Full helper/runner/jar hashes are recorded in the [sanitized evidence](../../docs/evidence/grave-checkpoint-process-exit-20261017.json). The server jar remains unchanged. All42 native phase PIDs are distinct. Coordinator review added PID assertions and bounded stream reads; the earlier valid Haiku inventory run `1792259369414933798` is retained privately.

| Case | Halt | Recovered | Exit (baseline / attempt / recover) |
|---|---|---|---|
| halt-1 alpha-write | 75 | BASELINE, alpha 10/v1, beta 0/v1, pile 2/1000 ticks/v1, total 12, 2 native loads | 0 / 75 / 0 |
| halt-2 beta-write | 75 | BASELINE (as above) | 0 / 75 / 0 |
| halt-3 ledger-write | 75 | BASELINE | 0 / 75 / 0 |
| halt-4 manifest-write | 75 | BASELINE | 0 / 75 / 0 |
| halt-5 generation-rename | 75 | BASELINE; complete orphan gen-000002 present but unused | 0 / 75 / 0 |
| halt-6 pointer-temp-fsync | 75 | BASELINE | 0 / 75 / 0 |
| halt-7 pointer-replace | 75 | AFTER, alpha 10/v2, beta 2/v2, pile 0/0 ticks/v2, total 12, 2 native loads | 0 / 75 / 0 |
| halt-8 parent-fsync | 75 | AFTER | 0 / 75 / 0 |
| control-no-fault | none | AFTER | 0 / 0 / 0 |
| corrupt-changed-account-bytes | orphan prep at 75 | refused: manifest does not match member bytes | 0 / 75 / 2 |
| corrupt-altered-manifest-pointer | orphan prep at 75 | refused: manifest hash does not match CURRENT | 0 / 75 / 2 |
| corrupt-symlink-member | orphan prep at 75 | refused: not a regular member: beta.toml | 0 / 75 / 2 |
| corrupt-traversal-pointer | orphan prep at 75 | refused: CURRENT is not the exact pointer shape | 0 / 75 / 2 |
| corrupt-linked-generations-ancestor | orphan prep at 75 | refused: linked path component (generations) | 0 / 75 / 2 |

The corruption controls refuse before any native account load and leave the unrelated `sentinel.txt` unchanged. Each halt case is a separate attempt JVM with `HALT <point>` on stdout and exit 75.

An earlier draft run, `1792259280753919870` (coins as variables, 13 cases, all passing), used a superseded helper and is kept as retained evidence. It is not the final result.

## Limits

- Process-exit ordering only. `Runtime.halt(75)` is a process-level cut, not a power loss. The fsync calls are present but make no durability claim.
- Accounts are fixture TOML with one `inventory` section containing a coins stack. Items are not validated beyond `getId()` and `rawValue()`, and nothing else in the native item model was exercised.
- The grave/pile ledger is a fixed-format fixture text file. It is not the original game ledger format.
- Fixtures are synthesized by the helper. No world, owner account, profile backup, `SaveQueue`, timers, live hooks, offline owners, or migrations were exercised.
- Each file in a generation is written by its own native `FileStorage.save` call. Cross-file atomicity comes only from the pointer, not from any native batch.
- Ancestor-link checking walks every path component up to `/`, so a symlinked home or system directory would also refuse.
- Unsupported: multi-generation retention, concurrent writers, cleanup of partials or orphans, and any non-fixture account.
