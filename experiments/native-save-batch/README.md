# Native account batch boundary diagnostic

This invokes the actual native `FileStorage.save(List<PlayerSave>)` from a trusted locally built server jar, with original fixture accounts in a new ignored lab directory. It is a persistence design experiment, not a game/session or power-cut test.

```sh
python3 experiments/native-save-batch/run.py \
  --server-jar /absolute/path/to/void-server-dev.jar \
  --sha256 YOUR_LOCALLY_VERIFIED_JAR_SHA256 \
  --java /absolute/path/to/java21/bin/java \
  --javac /absolute/path/to/java21/bin/javac
```

The probe uses native `PlayerSave.load/save` for two original accounts. After establishing their original files, it retains the second file separately and replaces its target with a nonempty directory. It attempts a two-account update, requires native refusal, verifies the sentinel and retained original bytes, then reports whether the first file nevertheless advanced. It does not assert that partial commit is desirable: `observed_partial_commit: true` is evidence of a limitation.

The diagnostic leaves every original fixture and failure artifact under `.runtime/native-save-batch/<unique-run>/`; it never cleans, overwrites an existing run, loads user accounts or opens a cache. It hashes the supplied jar before and after, records the probe/runner hashes, and runs no network world or launcher. Use a trusted locally built jar that will not change during execution. No binaries are committed.

An individual atomic account replacement does not establish a transaction across accounts and a shared grave ledger. This experiment deliberately makes the second target invalid. It does not simulate an actual interrupted write, exercise `SaveQueue` or prove crash recovery. A future implementation must separately demonstrate its commit/recovery protocol and profile backup closure.
