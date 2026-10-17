# Cold-JVM unrecovered grave diagnostic

This diagnostic checks a known source-inferred save boundary. It is not a gameplay feature or a passing grave-persistence regression. It supplies four items, applies native lethal damage at Lumbridge, observes the unexpired grave/drop, invokes real `World.shutdown` and then boots a second native `WorldTest` JVM against the same private storage root. It reports whether the grave/drop survived while checking the kept account inventory, XP and position.

From the repository root, after the normal authorized cache/source setup:

```sh
python3 experiments/native-grave-boundary/run.py
```

The default JDK is `.runtime/jdks/jdk21`; `JAVA_HOME` can select the native JDK21 installation. Offline Gradle requires the usual resolved build dependencies. The runner verifies the native source/patch match, holds the build lock throughout, temporarily injects only its own uniquely named test source, and removes it only if its bytes are unchanged. An existing source is never overwritten. A failed build retains private logs and removes only the verified injected source.

Both native test JVMs use one new ignored `.runtime/grave-boundary/<run>/world` root. `WorldTest.afterAll` deletes its account-save directory as fixture cleanup, so the runner restores the byte-for-byte retained account into that same directory before the second boot. Other private files remain in place, including the shared shutdown exchange paths. The second JVM gets no in-memory entity lists or grave variables. JUnit teardown's entity clearing is not the restart operation; distinct JVM PIDs and native startup establish that boundary.

The game clock remains zero in both phases and the recorded grave expires at300 seconds, excluding ordinary timer expiry. Actual account files are checked against native saved/restored state. Both shutdowns execute the native primary-save gate. Input cache file hashes are checked before/after; assets and save files are never committed.

This uses native game configuration/scripts/world startup, damage, account login and shutdown with FileStorage, without a network server `Main`, graphical client or physical controller. Supplied items/API damage are explicit fixtures. A true `observed_gap` identifies lost unrecovered world state and must not be interpreted as product acceptance. A false value needs investigation rather than an automatic success claim. Save policy, migration and no-duplication behaviour require a separate implementation decision.
