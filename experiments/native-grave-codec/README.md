# Native grave codec: one bounded, versioned snapshot

Disposable fixture experiment. It asks one question: can a single bounded, versioned, immutable grave/pile snapshot survive a real native `PlayerSave` variable, a real `FileStorage` write and a cold JVM `PlayerSave.Companion.load` without losing charges, timers, original provenance or separate pile identities?

It is not a production persistence format, not a per-account versus world-generation layout decision, and not a claim about `Player.copy`, `SaveQueue`, persistent-variable registration, live timers, restoration or backup integration.

```sh
python3 experiments/native-grave-codec/run.py \
  --server-jar upstream/game-server/game/build/libs/void-server-dev.jar \
  --sha256 d5c5143031c38ea0b344d75660597eb2ea003d6642f62735b9356849071e991e \
  --java .runtime/jdks/jdk21/bin/java \
  --javac .runtime/jdks/jdk21/bin/javac
```

Every run writes to `.runtime/native-grave-codec/<unique-run>/` (ignored). The runner refuses an existing run, refuses symlinked ancestors, holds a shared lock on `.runtime/build.lock` only while it copies the jar and helper source into the run, compiles and runs against those frozen copies, verifies the input digest, helper and runner hashes before and after, and never cleans up failures.

## Files

- `GraveCodecHelper.java`: fixture-only codec and native harness. Modes: `write ROOT`, `read ROOT`, `checks`.
- `run.py`: stdlib runner. It runs 12 scenarios with 22 distinct JVMs, including one JVM containing 53 named in-memory checks.

## Snapshot shape (version 1)

Root keys are exactly `version`, `graves`, `piles`, `latest`.

- `graves` (max 64): `id`, `account`, `kind`, `x`, `y`, `level`, `remaining_seconds` (native grave timer, seconds, `>= 0`), `blessed`.
- `piles` (max 256): independent records with no grave link and no per-grave cloning: `id`, `source_account` (original provenance), `visible_owner` (empty string means public), `item`, `amount` (`1..INT_MAX`), `charges` (`0..INT_MAX`), `x`, `y`, `level`, `reveal_ticks`, `disappear_ticks`.
- `latest` (max 64 entries): account to the grave it owns. It must name an existing grave with that same account.

Rules: tile `x`/`y` are `0..16383`, `level` is `0..3`. Pile counters `reveal_ticks` and `disappear_ticks` accept `-1..INT_MAX`. Private piles require `visible_owner == source_account` and a positive reveal or `-1`. Public piles require an empty owner and `reveal_ticks <= 0`. Identifiers are bounded ASCII. Accounts use a fixture-only pattern. Missing or unknown fields, non-integer numbers, booleans used as numbers, negative or overflowing values, wrong containers, unsupported versions, oversize collections, duplicate ids and nulls all refuse.

Encoding returns deeply unmodifiable maps and lists. Decoding copies every nested collection, so a caller's mutable input cannot change a decoded snapshot.

## Native path

The helper builds a carrier `PlayerSave` named `gravelab` from a fixture TOML source with empty inventories. It puts the encoded snapshot into `variables['grave_lab_state']` and saves through `FileStorage.save`. The reader is a separate JVM that calls `PlayerSave.Companion.load`, requires native inventories to be empty, requires no variable keys other than `grave_lab_state`, refuses a missing key rather than defaulting it, decodes strictly, and prints the canonical JSON. No custom JSON is used as the save format. The native TOML writer serialises the nested data as an inline table.

## Cases

| Case | Expectation |
|---|---|
| `valid-cold-roundtrip` | Writer and reader are separate JVMs. The decoded snapshot equals the runner's independent literal exactly. |
| `checks` | 53 named in-memory outcomes match exactly (validation refusals, accepted boundaries, immutability, caller-mutation independence). |
| `write-existing-refused` | A second writer on an existing root refuses (exit 2), with no timeout or missing PID, and leaves every fixture byte unchanged. |
| `corrupt-schema_version_two` | The reader refuses (exit 2, empty stdout) and the fixture bytes are unchanged after the read. |
| `corrupt-unknown_grave_field` | Same, for an unknown grave field. |
| `corrupt-missing_latest` | Same, for a missing `latest`. |
| `corrupt-bool_as_number` | Same, for a numeric `blessed` value. |
| Four `guard-*` scenarios | Linked member, linked ancestor, file larger than 1 MiB and FIFO refuse before native loading, without rewriting the fixture. |
| `control-charge-loss-detected` | The codec accepts a schema-valid charge change; the independent full-record oracle detects exactly that change. This is a sensitivity control, not a corruption refusal. |

Each corruption edits only the fresh fixture file, requires exactly one match in the native-written file, and checks an unrelated sentinel file afterwards. The runner also checks that PIDs are non-null and unique across the whole run, and that each JVM is distinct.

## Result

Final coordinator run `.runtime/native-grave-codec/1792276351385574852/summary.json`: all 12 scenarios pass, with 53 exact named checks inside the checks scenario. Native input is the matched server51 jar above; source, runner and input jar remain unchanged during the run. Build that matched source through the normal repository setup first; this lab itself starts neither a world nor a cache. For a different verified build, pass and record its actual digest rather than assuming this one applies.

The preliminary Haiku run used frozen server50 and passed seven scenarios. Coordinator review added actual file guards and a charge-loss sensitivity control. The first expanded run (`1792276305942221943`) caught a real linked-parent gap: the helper accepted a regular file beneath a linked directory. The helper now checks every ancestor of the complete account path. Only the corrected final run qualifies the new guards. Fingerprints record files, directories and link targets without following links.

## Limits

- Process-level only. These are ordinary completed JVM runs, with no forced-exit, partial-write or power-loss proof.
- Not a production format and not a layout decision. The `gravelab` carrier account is only a container for one fixture snapshot.
- Not `Player.copy`, `SaveQueue`, persistent-variable registration, live timers, restoration or backup integration.
- Grave `remaining_seconds` is native grave-timer seconds. Pile ticks are a separate counter and are not simulated against wall-clock time.
- Native normalised instance destinations are not proved. No claim is made that a pile or grave definition is valid in a live world.
- The snapshot is a prototype subset. NPC direction, transform stage, player male flag, display name and instance normalisation are not captured.
- Account naming is a fixture subset, not proven coverage for real account names.
- Supplied records, not earned or native death snapshots.
- Key order: the native reader returned `latest` keys in a different order from the one written. The encoder therefore emits `latest` in sorted key order so the canonical output is stable.
- File guards are cooperative local checks, not an adversarial filesystem sandbox or a general untrusted-account parser. No native storage path is changed.
