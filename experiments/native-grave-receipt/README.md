# Native grave receipt: whole-pile restricted model

Disposable fixture experiment. It asks whether one durable **whole-pile receipt** stored inside the existing per-account `PlayerSave` files can recover a guest pickup without a new world-directory layout. It is a restricted model with process-exit cuts, not a production storage format, not a save-format decision, not a SaveQueue test, and not evidence that grave persistence works.

```sh
python3 experiments/native-grave-receipt/run.py \
  --server-jar /absolute/path/to/frozen/server-41.jar \
  --sha256 90c350b5d97ee93be4c96ba1706e912ec0d2c4355b89cab084c6478300f3d88a \
  --java /absolute/path/to/jdk21/bin/java \
  --javac /absolute/path/to/jdk21/bin/javac
```

Every run writes to `.runtime/native-grave-receipt/<unique-run>/` (ignored). The runner refuses an existing run, refuses symlinked lab ancestors, verifies the jar digest before and after, records the helper and runner hashes before and after, and never cleans up failures.

## Files

- `GraveReceiptHelper.java`: fixture-only native helper. Modes: `baseline ROOT`, `step ROOT ACTION HALT|none`, `gc ROOT HALT|none`, `dump ROOT`, `recover ROOT`.
- `run.py`: stdlib runner. It runs20 cases with fresh roots and a separate JVM for every baseline, step, dump and recover. It checks PIDs, exit codes, halt markers, unchanged files on refusal, unchanged files across recovery, and the independent conservation oracle.

## Layout: existing per-account files only

```
root/saves/alpha.toml   owner PlayerSave: inventory/bank coins, death_sequence, source_high_water,
                        save_generation, piles = [pile records], receipts = []
root/saves/beta.toml    guest PlayerSave: inventory/bank coins, consumed_coins (fixture sink),
                        save_generation, receipts = [receipt records], piles = []
root/errors/beta.toml   fallback location, written only by the fallback case; never read by recovery
root/sentinel.txt       unrelated bytes that must survive refusal and recovery
```

Records are fixed-member typed maps in `PlayerSave.variables`, written by the native `FileStorage` and read by `PlayerSave.Companion.load`. Each account TOML is a fixture source loaded through the native reader before saving. Coins are native inventory `Item` stacks counted with `rawValue()`. No fake coin variable replaces inventory, and no separate owner ledger file exists.

## Protocol under test

- **Source barrier.** A guest pickup is refused unless the primary owner file already holds the matching pile record (`source_seq`) with `death_sequence >= source_seq`. The pile record and the owner's inventory loss are in one atomic owner file, so the record's presence proves both.
- **Whole-pile claim.** The receipt quantity is the remaining floor of the single pile. The owner's pile base is never rewritten by a pickup.
- **Recovery.** Floor is `base - sum(receipts matching pile id and source_seq)`. Each receipt counts once. Recovery never scans inventories.
- **Missing owner record.** If `death_sequence < receipt.source_seq`, recovery refuses. If `death_sequence >= source_seq` and `source_high_water >= source_seq`, the receipt is `retired`. Otherwise it refuses.
- **Retirement and GC.** Only the exclusive `gc` boot mode runs. It first reconciles (refusals write nothing), then removes a fully claimed pile from the owner while keeping `source_high_water`, and only then removes receipts whose pile is retired. A crash between the two leaves an extra harmless receipt.

## Oracle

Python reads the native `dump` output, checks the pile base stays at 2, and computes:

`total = owner coins + guest coins (inventory + bank) + consumed_coins + floor`

Protocol cases must equal 10. Controls must yield the bad total the case predicts. Java's `recover` tuple is compared with Python's tuple, and Java never checks the total.

## Results

Coordinator-reviewable run: `.runtime/native-grave-receipt/1792260876776172274/summary.json` (`all_passed: true`,20 cases,18 restricted protocol cases passed,2 deliberately unsafe controls detected).

| Case | Halt / action | Oracle tuple (owner, guest, consumed, floor) | Outcome |
|---|---|---|---|
| 1a death-before-save | halt 75 | pre-death 10,0,0,0 | passed |
| 1b death-after-save | halt 75 | 8,0,0,2 | passed |
| 2a pickup-before-save | halt 75 | 8,0,0,2 | passed |
| 2b pickup-after-save | halt 75 | 8,2,0,0 claimed, receipt 2 | passed |
| 2c barrier | pickup before death refused, exit 2 | pre-death 10,0,0,0 | passed |
| 3 owner re-save | resave after claim | 8,2,0,0, base still 2, applied once | passed |
| 4a claimed coins banked | bank 2 | 8,2 (bank 2, inventory 0),0,0 | passed |
| 4b consumed | consume 2 to sink | 8,0,2,0 | passed |
| 5a halt after owner retirement | gc halt 75 | 8,2,0,0; receipt `retired` | passed |
| 5b halt after receipt GC | gc halt 75 | 8,2,0,0; no receipt, no pile | passed |
| 5c GC no-fault control | gc exit 0 | 8,2,0,0 | passed |
| 6 stale backup owner | pre-death owner + receipt 1, gc refused exit 2, files unchanged | raw total 12, refused | passed |
| 7 fallback file | receipt only in `errors/beta.toml` | 8,0,0,2 (primary) | passed |
| 8a bypass barrier | receipt with no owner record | raw total 12, recover refused | control detected |
| 8b erased receipt | receipt erased after consume | raw total 12, floor 2 | control detected |
| 9a symlinked guest | refused before native load | n/a | passed |
| 9b traversal owner id | refused | n/a | passed |

Coordinator review adds repeated-pickup refusal, repeated GC idempotence and a halt immediately before receipt GC; all pass with unchanged evidence where required. The prior17-case Haiku run is retained privately.

Case 8b is the important negative finding. After the receipt is erased, the protocol accepts the state as an ordinary unclaimed pile with floor 2. The protocol alone cannot tell it apart from a pile that was never claimed. Only the independent conservation check (raw 12) detects it.

## Superseded run

`.runtime/native-grave-receipt/1792260586739174809/` is retained. It was a failed run: the helper rejected empty slots, which the native reader returns as `Item` objects with an empty id. The helper was fixed, and the run was repeated. The retained run has no summary.

## Limits

- Process-exit ordering only. `Runtime.halt(75)` is not power loss. The fixture does not claim fsync durability.
- The fixture does not exercise `SaveQueue`, online or offline callbacks, native death or pickup hooks, live timers, concurrent writers, backup or import, or source-ID allocation. It does not test the pending patch0042 queue fix and does not depend on it.
- `bank`, `consumed_coins` and the pile/receipt records are fixture constructs, not native game storage. Consumption and banking are supplied account mutations, not native actions.
- Only one owner, one guest and one whole pile are modeled. Partial claims, merged piles and multiple graves are unimplemented.
- The helper refuses non-coin items and unknown inventories, so item identity and charges are out of scope.

## Minimum remaining barriers before production

1. Durable ordering across the owner and guest files, with the owner primary save confirmed before any guest receipt is published, enforced by the real save path rather than the fixture.
2. Protection against stale writers, including an offline `Player` snapshot overwriting a newer owner file.
3. A conservation or consumed-sink link that detects an erased receipt (case 8b), or an invariant that makes receipts non-erasable while their pile base remains live.
4. Exclusive-boot enforcement for `gc`, and a claim-ID uniqueness rule across all guest files.
5. Backup and import contracts that include `piles` and `receipts`, and a validated schema version.
6. Power-loss durability evidence for the per-account atomic writes, which this process-exit model does not establish.

No recommendation to ship or change saves is made here. The coordinator reviews the results before any merge.
