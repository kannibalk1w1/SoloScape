# Native grave/pile record codec experiment — 17 October 2026

A bounded original record snapshot survives the native `PlayerSave` variable writer, `FileStorage.save` and a different JVM's native loader without changing its supplied fields. The final experiment passes **12 scenarios with 22 distinct JVMs**; one scenario contains **53 named validation and immutability checks**. It uses the matched server 51 jar, freezes the helper/jar inputs and verifies their hashes after the run.

The fixture has three graves, including two at the same tile, and three independent floor piles. One pile represents a supplied merged coin quantity; it is not recreated separately for each grave. A weapon retains quantity 1 and charges 12,345. A public pile retains its original source account independently of its empty visible owner. Grave lifetime is in seconds, while reveal/disappearance remain separate tick counters. These are supplied records, not an observed live death/merge/timer event.

## What the checks establish

The cold reader's entire decoded record must equal an independent Python literal. Exact keys/types, collection/number bounds, duplicate identities, ownership, latest-grave references and unsupported versions are checked without silent defaults. Selected mutation attempts are refused; changes to caller collections and replacement snapshots leave the earlier encoded checkpoint unchanged.

Four edits to native-written fixture files are refused without rewriting them. Four actual file controls exercise linked members, linked parent directories, files larger than 1 MiB and FIFOs. Directory/link fingerprints avoid following links, and unrelated sentinel bytes remain unchanged. The first expanded coordinator run caught the linked-parent gap; checking the complete account path fixed it before qualification. That failed run is excluded from successful results.

A separate sensitivity control changes a schema-valid weapon charge to 0. Native loading/decoding accepts that valid shape, while the independent record oracle detects exactly the charge loss. This tests the comparison's sensitivity; it is not evidence that the codec can infer a weapon's intended charge from schema alone.

Claude Haiku implemented the initial helper/runner and seven-scenario proof using frozen server 50. Coordinator review tightened bounds/identity observations, added file controls and the sensitivity control, fixed the linked-parent gap and independently ran the final matrix against current server 51. [Sanitized results, identities and hashes](evidence/grave-record-codec-20261017.json); [source and exact reproduction](../experiments/native-grave-codec/README.md). Final private report: `.runtime/native-grave-codec/1792276351385574852/summary.json`.

## What remains open

This is a prototype subset and a serialization prerequisite, not a production format or a choice between account files and a coherent world generation. The fixture carrier variable is not registered for live `Player.copy`/`SaveQueue`. NPC direction/appearance, gender/display text, actual definition validation, instance destinations, offline owners, live capture/restoration, primary-save acknowledgement, guest/public pickup consistency and backup/import recovery remain unproved. Ordinary process exits do not establish crash-point or power-loss durability.

The [pause-while-closed persistence P1](GRAVE_PAUSE_PERSISTENCE_PLAN.md) stays open. Preserve the earlier publication experiments and choose the production layout/recovery contract before activating any live record. No owner save/profile, installed Deck build, cache or release was changed by this experiment; generated jars and native fixture files remain ignored.
