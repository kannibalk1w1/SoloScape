# Native account batch boundary — 17 October 2026

A small native diagnostic confirms that individually atomic account files are not an atomic batch. A valid two-account update advances both files. After restoring the original fixture state and deliberately making the second target invalid, `FileStorage.save` refuses that write while the first account has already advanced to its new snapshot.

The experiment uses actual `PlayerSave.load/save` and `FileStorage.save` from the locally matched server jar through patch0041. Both accounts and all paths are original disposable fixtures in ignored runtime storage. The second original account is retained separately; a nonempty directory at its former target induces native `FileSystemException`. Its sentinel and retained original bytes remain unchanged.

Two fresh JVM runs produce identical report fields/hashes except process elapsed time. The expected first-account new hash matches the advanced file after the failed batch. A wrong expected jar digest is refused before a new run is created; hashes of every existing experiment file remain unchanged. [Sanitized evidence](evidence/native-save-batch-boundary-20261017.json) records the exact trusted jar, tool hashes, pinned sources and41 server patch identities. Code and reproduction instructions: [native batch diagnostic](../experiments/native-save-batch/README.md).

## Meaning and limits

`observed_partial_commit: true` is a storage limitation, not passing world-persistence acceptance. The controlled native exception is not a power cut, disk-full test, live world, `SaveQueue` run or launcher recovery test. The0.395s process duration is not a game-performance benchmark. No owner account, cache, installation or Deck was opened.

The existing primary-save confirmation correctly requires primary batch success; this experiment does not bypass or weaken it. The result means a future shared grave ledger cannot assume that saving the taker account and the owner's account separately creates one transaction. The [pause-while-closed persistence plan](GRAVE_PAUSE_PERSISTENCE_PLAN.md) keeps that boundary explicit and requires recovery/quantity-conservation proof before adding a new production writer.

Private results: `.runtime/native-save-batch/1792258747987243453/summary.json` and `.runtime/native-save-batch/1792258777484289509/summary.json`. All original inputs and controlled failure artifacts are preserved there. No proprietary binaries are committed, and no gameplay/save format is changed by this diagnostic.
