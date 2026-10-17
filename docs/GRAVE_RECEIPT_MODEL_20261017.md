# Native whole-pile receipt model — 17 October 2026

An isolated per-account receipt experiment passes its restricted publication/recovery cases, but exposes an important limit: erasing a receipt after the collected item is consumed can restore the same loot. The protocol accepts that schema-valid state; an independent quantity oracle catches the duplication. This is evidence for a design decision, not permission to ship grave persistence.

## Mechanism and result

Claude Haiku implemented original fixture accounts using actual native `PlayerSave`/`FileStorage` inventory serialization. Owner death saves inventory8 plus a pile base2 in one account file; a guest pickup saves inventory2 plus a receipt in the guest file. Total value starts at10. Receipt records remain independent of the current inventory, so supplied banking/consumption mutations do not restore the floor pile.

The critical source barrier requires the owner inventory loss and matching source record in primary storage before a guest claim can publish. Deliberately bypassing it produces owner10 plus guest2. A lower owner death sequence with a newer receipt refuses instead of assuming that missing source was already retired. This also protects the demonstrated stale/mixed owner-file fixture.

Cold-boot fixture GC retires the owner record before removing the guest receipt. Crashes between those writes leave a harmless extra receipt. This depends on an exclusive phase and ordered native writes; it is not a live SaveQueue integration.

Coordinator review adds repeated pickup refusal, repeated GC idempotence and a halt immediately before receipt cleanup. The final20-case matrix contains18 expected protected/guard outcomes and two deliberately unsafe sensitivity controls. Each phase uses a fresh native JVM, checks its PID/exit/halt marker, and compares native reloads with an independent Python quantity calculation. Banking uses native saved slot arrays; consumption uses an explicit fixture sink counter. Neither is an earned game action.

[Sanitized evidence](evidence/grave-receipt-model-20261017.json) binds exact helper/runner/frozen-jar hashes and all outcomes. [Reproduction and protocol](../experiments/native-grave-receipt/README.md). Private final report: `.runtime/native-grave-receipt/1792260876776172274/summary.json`. The frozen server41 jar remains unchanged; later queue patch0042 is not exercised by this experiment.

## What remains unresolved

The erased-receipt control is accepted by the protocol and yields total12; only the independent oracle detects it. Retaining receipts is a correctness invariant, not something this codec can reconstruct from current inventories. Source-primary acknowledgements, stale writer protection, live/offline hooks, actual timers, merged/repeated piles, source identity allocation, schema/backup validation and target failure recovery remain unimplemented. Whole-world generation publication has a simpler coherent-snapshot invariant but changes the current account-path contract; the [checkpoint comparator](GRAVE_CHECKPOINT_PROCESS_EXIT_20261017.md) proves only that mechanism.

The [pause-while-closed plan](GRAVE_PAUSE_PERSISTENCE_PLAN.md) stays open. Neither experiment is a production save format or proof of power-loss safety. No owner account, cache, installation or Deck was accessed by the receipt experiment, and no proprietary binaries are committed.
