# Private prebuilt server closure experiment

This builds a **private test payload** from an already matched local server jar and the pinned/applied runtime data sources, then boots an empty native world with a separate private cache copy and mutable state. It is not a release builder, updater, installable launcher or distribution approval.

```sh
python3 experiments/native-prebuilt-server/run.py \
  --cache /absolute/path/to/authorized-compatible-cache \
  --java /absolute/path/to/java21/bin/java
```

Preparation uses the source checkout, Git and exported patches to verify/select inputs. The resulting JVM payload contains only `server.jar` and runtime `data/` files, with no source, `.git`, Gradle or `config/local.env`. The native subprocess receives a minimal environment, an explicit loopback port, external copied-cache path and isolated save/error/log/temp/home paths. Java 21 is supplied separately; no compiler or Gradle runs inside the payload.

`runtime_inputs.collect_data(repo, patches)` selects tracked data plus sequential patch additions/modifications/deletions. It excludes `data/cache`, `saves`, `errors`, `.temp`, `logs` and `exchange`, ignores other untracked files, refuses links/special files/missing inputs and supports only TOML/TXT source files. File/count/size caps and descriptor metadata checks guard its read-only hashes. Eleven temporary-repository tests exercise those boundaries, including canaries and patch hunk/header confusion.

The payload is made read-only. The source cache is copied into ignored runtime storage and is never passed to the game JVM. Native readiness must precede graceful stop; the exact fresh native primary-save receipt is required. Logs, snapshots and failures remain under `.runtime/prebuilt-server/<unique-run>/`. Only the Popen-created fixture JVM is stopped; forced stop is a failed experiment.

Final result: `.runtime/prebuilt-server/1792261075033350219/summary.json`. The native server boots from 3843 data files (8,530,252 bytes), confirms closure and leaves payload/source-cache/private-cache bytes unchanged. The initial run is retained: its overbroad character-file assertion mistook nested Grand Exchange files for accounts; the corrected guard matches the native top-level account layout.

Limits: empty server only, no client/login/character/launcher, no public packaging/licence decision, no new cache compatibility detector or target-device performance acceptance. The runner's source-checkout preparation is not a claim that the current graphical launcher works without a checkout. Timings describe this host boot/closure, not game FPS.
