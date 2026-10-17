# Grave checkpoint publication experiment — 17 October 2026

An isolated immutable-generation experiment preserves a coherent pair of native account snapshots plus an original pile ledger across eight forced JVM exits. This proves a publication mechanism; it does not implement grave persistence or select the production storage layout.

Claude Haiku built the helper/runner. Coordinator review required actual native inventory slots, exact old/new state checks, linked-ancestor rejection, a complete write loop, bounded reads and explicit native process identities. The superseded variable-counter fixture is retained privately and is not the accepted proof.

## What ran

The final matrix runs14 scenarios with42 distinct native JVM PIDs. Each scenario creates a fresh baseline, runs a separate update JVM and runs recovery in another JVM. Native `PlayerSave` and `FileStorage` write/load the original account files. The supplied server jar matches client55/server41 build evidence and remains byte-identical; no cache or world is started.

Before: Alpha inventory10 coins, Beta0, floor2, ledger1000 remaining ticks, version1. After: Alpha10, Beta2, floor0, ledger0 remaining ticks, version2. Recovery independently checks the exact tuple and total12. These are supplied snapshots, not an actual pickup/timer simulation.

The helper halts with exit75 after each account write, ledger write, manifest write, completed-generation rename, pointer-temp sync, pointer replacement and final parent sync. Before pointer replacement, recovery selects the complete baseline; after replacement it selects the complete new state. A no-fault control publishes the new state normally.

Five controls corrupt account bytes, manifest identity, a member link, a traversal pointer or a generations ancestor link. Each refuses the active snapshot while preserving an unrelated sentinel. A complete orphan generation is deliberately available and is never selected as a convenient fallback. The reader validates CURRENT, fixed members and byte hashes/lengths before native loading.

[Sanitized evidence](evidence/grave-checkpoint-process-exit-20261017.json) records every expected/recovered tuple, exit code, process ID and tool/jar hash. Reproduction: [experiment README](../experiments/native-grave-checkpoint/README.md). Private final report: `.runtime/native-grave-checkpoint/1792259555968822957/summary.json`.

## Practical limit and next decision

Process death is not a power cut. Fsync calls do not establish crash durability on target hardware. There is no live world, concurrent writer, SaveQueue integration, offline-owner lifecycle, actual grave codec, profile backup/restore or migration acceptance. The fixed two-generation fixture format is not a proposed general save format.

The mechanism answers the individual-file batch gap from the [native storage diagnostic](NATIVE_SAVE_BATCH_BOUNDARY_20261017.md), but adopting a pointer affects the existing fixed account paths and launcher save-generation contract. Compare that cost with a durable receipt protocol before changing production storage. The [pause-while-closed persistence plan](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains open, with exact item conservation and failure recovery required through the real native lifecycle.
