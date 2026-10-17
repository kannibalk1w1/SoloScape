# Private prebuilt launcher contract experiment

This is a separate experiment, not a production launcher/updater mode. It prepares a private binary/data payload and supplies a prebuilt preflight adapter to the existing launcher backend. Native/source launch behavior is unchanged.

`manifest.py` is a read-only bounded validator for `soloscape-runtime.json`: exact file membership and SHA-256/size, strict schema, safe relative paths and descriptor-based no-follow traversal. Only the two native jar roles, launcher/runtime scripts and allowlisted TOML/TXT server data may be present. Cache, owner state, artwork, native source, Git and Gradle files are excluded. Metadata declares source commit/pins/patches/cache revision; the validator authenticates none of those against a remote source, compatible cache or licensing inventory. Limits: 4 MiB manifest, 10000 files/directories, depth 32, 512 MiB/file, 2 GiB total. Hardlinks and concurrent ancestor replacement are not fully defended; this is not a filesystem sandbox.

The experimental adapter requires explicit distinct external `SOLOSCAPE_PROFILE_HOME`, `SOLOSCAPE_CACHE_HOME` and `SOLOSCAPE_LAUNCHER_HOME`. It derives the version's mutable runtime/lock directory from **both canonical code-root identity and immutable manifest hash**, under the selected launcher home. Another code root cannot inherit the same recovery/build context merely by sharing profiles. The manifest, scripts, jars and data remain immutable; build commands are refused. Its preflight requires JRE versions, X11/XWayland, cache inputs and a free game port, without demanding Git/Gradle/JDK compilers. Original-version recovery and stopped-world activation still need explicit acceptance before a managed installer could use this design.

Preparation requires committed exact runtime sources, matched native jars/stamp and the original source checkout. It copies only verified data, creates a private cache copy and then makes the payload read-only. Nothing from this output may be uploaded as a public release. Game/dependency distribution review remains open; no JDK, cache, artwork or save is included in the payload or Git.

```sh
python3 experiments/prebuilt-runtime-contract/prepare.py --cache /absolute/path/to/authorized-cache
python3 experiments/prebuilt-runtime-contract/probe.py \
  --run /absolute/path/to/the/new/private/run \
  --server-java /absolute/path/to/java21/bin/java \
  --client-java /absolute/path/to/java8/bin/java
```

The probe uses an owned Xvfb display, software rendering and no audio (empty private ALSA configuration). Its original `LauncherProbe.java` drives real launcher buttons and the real copied backend. The existing original `NativeSessionSmoke` instrumentation is compiled outside the payload and drives native login/readiness. JRE forwarding wrappers preserve process identity and guards; no native jar is rewritten. The coordinator checks each stopped-world save checkpoint before Continue. This is not physical controller, audio, orphan-recovery, clean-machine, FPS or update-activation acceptance. It does not prove that the mounted source tree is inaccessible.

A manifest check inside a version's own backend is **not a trust boundary before executing package code**. An eventual trusted outer updater must authenticate/validate a candidate before running any of its scripts or jars. The private builder/coordinator provides that trust for this experiment; public download/activation is absent.

Automated checks use original disposable payloads: `test_prebuilt_manifest.py` and `test_prebuilt_bootstrap.py`. Native/GUI results are recorded separately after actual probe execution; preparing or validating a payload alone does not establish a playable package.
