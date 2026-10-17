# Prebuilt native server closure — 17 October 2026

The actual native server can boot and confirm a clean shutdown from a private payload containing its fat jar plus runtime data, with no source checkout layout, Git metadata or Gradle files in that payload. This removes one runtime uncertainty for GitHub delivery. The graphical launcher still uses its existing source-build checks; a playable managed package is not implemented by this experiment.

## Inputs and evidence

Claude Haiku implemented a read-only data selector and 11 original temporary-repository boundary tests. Coordinator review ran it against the pinned/applied upstream tree: 3843 TOML/TXT files, 8,530,252 bytes. Tracked files and final patch additions are eligible; source deletions are respected. Cache, saves, errors, temp/log/exchange state and unrelated untracked files are excluded. No broad copy of the server data directory is used.

The coordinator's boot runner verifies the matched server 42/client 55 build identity, copies only the server jar and selected runtime data, makes that payload read-only, and copies the supplied compatible cache separately. The native JVM runs with an isolated home/temp/save/error/log tree and a minimal environment. No owner accounts or legacy saves are opened, and neither cache nor binary data is committed.

Observed on this Linux host:

| Measurement | Result |
| --- | ---: |
| Native ready marker after process start | 4.210 s |
| Normal shutdown and primary-save confirmation | 0.364 s |
| Process high-water RSS observed at readiness | 1,392,300 KiB (about 1.33 GiB) |
| Supplied cache copied privately | 39 files / 193,740,377 bytes |
| Payload and both cache inventories after run | unchanged |

The exact fresh native session receipt and normal SIGTERM exit are required. A no-account check uses the native top-level account layout, allowing separately nested Grand Exchange state. The first run reached ready/closure but failed an overbroad recursive account assertion; it is preserved, and the corrected run passes.

[Sanitized evidence](evidence/prebuilt-native-server-20261017.json) records exact jar/selector/runner hashes, pins, 42 server patches, counts and timings. [Tool and reproduction](../experiments/native-prebuilt-server/README.md). Private final report: `.runtime/prebuilt-server/1792261075033350219/summary.json`.

## Meaning and next gate

These are empty-world startup/closure and host memory observations, not Deck/gameplay FPS, sustained tick performance or an account persistence test. Cache revision 634 is the declared project requirement; presence/hashing is not a compatibility detector. Successful native loading is evidence for this supplied input only.

The source checkout is used to **prepare** the private payload. Java 21 is supplied externally. No JDK, cache, art, private configuration or owner state is a public package asset here. Existing dependency and distribution review remains required before any release.

Next separate the current launcher's runtime preflight from its source-build doctor, keep world recovery tied to the original build context, and define explicit shared cache/art/settings locations. Preserve optional external profile storage. Then test a complete disposable New/Continue/controller session before receiving or applying an update. M13 remains open.
