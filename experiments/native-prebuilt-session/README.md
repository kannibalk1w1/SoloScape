# Private prebuilt native session experiment

This prepares an immutable private payload from verified local matched jars and the tracked/patch-applied runtime-data allowlist, then runs actual New and Continue sessions from that payload. Cache and profiles are external private copies. Only the preparation uses Git, source and `javac`; the game JVM working directories contain no source, Gradle scripts or Git metadata.

```sh
python3 experiments/native-prebuilt-session/run.py \
  --cache /absolute/path/to/authorized-compatible-cache \
  --server-java /absolute/path/to/java21/bin/java \
  --client-java /absolute/path/to/java8/bin/java
```

Requires the matched build stamp, exported source stacks, JDK 21+ and JDK 8, Python and Xvfb. Uses the existing original `NativeSessionSmoke` instrumentation, compiled outside the runtime; native client/server jars are unchanged. The native client logs in through the ordinary profile credential/native login path, dismisses fresh Continue dialogues and records real world/capability readiness. Client exit triggers the actual owned session's graceful server closure, exact primary-save receipt and verified backup flow. It compares account name, XP, inventories and tile across fresh JVMs. It does not change a player's inventory or teleport a character.

The coordinator bypasses the production **source-build doctor** after separately verifying its inputs; this is explicitly not a working prebuilt graphical launcher/preflight. `profile_session` uses copied jars and payload working directories, with minimal environment and all state directed to the new fixture. Build/recovery locks belong to the coordinator's original build context. The temporary classpath instrumentation is not an orphan-recovery test. The source checkout remains mounted, so this is not a filesystem sandbox or a syscall audit.

Payload files/directories are read-only. Before/after hashes check payload, input cache and private copied server cache. Per-profile client cache is deliberately writable. All evidence, fixture credentials/saves, private logs and screenshots remain under ignored `.runtime/prebuilt-session/<unique-run>/`. No owner profiles, legacy saves or Deck installation are scanned. Inputs must not be symlinks/special files, as checked by the shared payload selector/tree helpers. Cache presence/hash does not identify a compatible revision.

Audio is **excluded** using an empty private ALSA configuration: Java enumerates no audio mixers. An earlier run reached New but stalled during Continue in native audio-device discovery without the host sound-service environment. It was stopped normally and retained. Independent tiny JVM probes found 0 mixers with empty ALSA configuration and 11 with the host runtime environment; neither proves audible audio. The final no-audio run is `.runtime/prebuilt-session/1792262812432617514/summary.json`.

No public package, cache/art/JDK redistribution, networking download, update activation, controller acceptance, Deck FPS, audio acceptance, clean-machine support or release readiness is established here. Publishing and owner deployment stay held.
