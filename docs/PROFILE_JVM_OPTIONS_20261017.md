# Owned profile JVM option precedence — 17 October 2026

Owned game sessions now remove inherited `_JAVA_OPTIONS`. The supported HotSpot Java 8 runtime applies this variable after explicit command-line properties, so it could override the profile's `-Duser.home` and `-Dsoloscape.cache.root`. The client consumes those properties for settings/cache, so an inherited override could redirect them despite the launcher supplying the correct owned paths.

A read-only actual Java 8 probe reproduced this through the original `owned_environment`: both properties resolved to foreign fixture paths. After the filter, the actual owned environment keeps both explicit private paths. A deliberate unsafe control restores the variable and reproduces the override. The probe reads properties only and verifies that no owned/foreign fixture directory was created. It never loads game data or reads owner profiles. [Exact evidence](evidence/profile-jvm-options-20261017.json).

A disposable process-lifecycle regression also starts an actual simulated owned server child, checks the key was removed, and completes the normal verified fixture save/backup path. Other inherited environment keys retain their existing behavior; this is ownership protection against the verified late HotSpot override, not a sandbox against arbitrary Java agents or an environment-security audit. General `JAVA_TOOL_OPTIONS`/`JDK_JAVA_OPTIONS` behavior is not changed. The development-only legacy-world launch is outside the profile helper.

Reproduce with `python3 experiments/profile-jvm-options/run.py --java /absolute/path/to/jdk8/bin/java`. The original helper compiles using that JDK; no JDK, binary, cache or save is committed. This establishes actual JVM property precedence and owned-child environment behavior, not a graphical/controller or Deck acceptance result.

All 242 root tooling cases pass with one optional skip.
