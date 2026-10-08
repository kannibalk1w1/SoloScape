# SoloScape 2011+

Bootstrap for a local RuneScape revision-634 experience, with Steam Deck native
experimental controller support. JDK 21, JDK 8 and the upstream cache are installed locally.
Both upstream builds pass, doctor passes, and the server reaches world readiness.
The controller prototype supports camera, precise walking, LT aiming, LB/RB target
cycling, scene highlights, inventory and dialogue controls, plus an optional direct
movement mode, world action menus, loot pickup, bank/shop panes, a controller keyboard, equipment/prayer/spell focus and a View/Select main-tab radial; see
[controller testing instructions](docs/CONTROLLER_TESTING.md) to enable it.

The [proposed roadmap](docs/ROADMAP.md) is the working task list.
The [current-state handoff](docs/PROJECT_HANDOFF.md) can be taken into ChatGPT for discussion.

The local Orca branch is `soloscape/bootstrap`, tracking remote `overnight/controller-sprint`; public `main` retains the preceding baseline. Source checkouts under `upstream/` are
ignored; tracked SoloScape patches reproduce the client changes and the server
directional movement extension. See [reconnaissance](docs/UPSTREAM_RECON.md),
[architecture](docs/ARCHITECTURE.md) and the original [brief](docs/KICKOFF.md).

For a fresh workspace, clone these public repositories into the named directories
and check out the exact commits in `docs/UPSTREAM_RECON.md`:

```bash
git clone https://github.com/2011Scape/game-server.git upstream/game-server
git clone https://github.com/2011Scape/runelite-client.git upstream/runelite-client
git clone https://github.com/2011Scape/634-client.git upstream/634-client
git -C upstream/game-server checkout 9f9113559eb686abd917893b5dca16404be07f93
git -C upstream/runelite-client checkout 297bc8a4861755b676855664d32859054779c067
git -C upstream/634-client checkout b39d45f49a0480f3f200fe3e31ad0798faf163ab
```

Install project-local JDK 21 for the server/build tools and JDK 8 for the client
(which still uses Java Applet APIs):

```bash
./scripts/setup-java.sh
```

The Linux x86_64 installer uses the [official Adoptium API](https://adoptium.net/en-GB/installation/ci-scripts),
verifies archive SHA-256 hashes and extracts into ignored `.runtime/jdks/`.
It creates `config/local.env` if absent and preserves existing configuration.
It does not change system Java. Python 3, Bash, Git, curl, tar, util-linux (flock) and a Linux graphical session with
X11/XWayland are required. Gradle wrappers resolve dependencies over the network
on the first build. No system Gradle installation is needed.

Alternatively copy `config/local.env.example` to `config/local.env` and set executable paths.
Follow [cache download and extraction instructions](docs/CACHE_SETUP.md), then
supply the compatible modified upstream cache in
`upstream/game-server/data/cache/`, including its index files. No scripts download
proprietary game assets. Do not commit cache data, saves or game resources.

```bash
./scripts/doctor.sh
./scripts/dev-run.sh
# Subsequent launches after successful builds:
./scripts/dev-run.sh --no-build
```

The launcher applies the tracked client/server patches, builds `:game:shadowJar` and
`:client:shadowJar`, starts the server,
waits for its loaded-world message and launches the client explicitly at
`127.0.0.1:43594`. Logs stream to the terminal and `.runtime/server.log` /
`.runtime/client.log` (one previous session retained). Closing the client or Ctrl+C stops
owned children with SIGTERM and waits for normal save/shutdown hooks. A hung
shutdown is reported and never forcibly killed. There is no separate stop
script because the foreground launcher owns this lifecycle.

**The upstream server binds all interfaces.** Restrict port 43594 with the host
firewall for local-only play. This launcher refuses root server `game.properties`
overrides until their paths/port/settings are audited. Bundled defaults include
normal account creation, Tutorial Island, file saves and 30 staggered bots.

Login with a new username/password to create a local upstream account. Saves
belong to this world in `upstream/game-server/data/saves/`. Preserve that folder
when updating source. Confirm restart persistence using the
[manual checklist](docs/STEAM_DECK_TEST_CHECKLIST.md) before treating it as tested.

The cache was downloaded with explicit user authorization from upstream's linked
MEGA folder. See [cache provenance](docs/CACHE_SETUP.md). Cache and archive remain
ignored by Git.

The user reports that launch/gameplay and physical controller camera panning work.
The user confirmed the walking/aiming usability pass feels better. Direct movement is optional and the user reports it feels good. The latest tab
radial and world-menu build needs an in-game acceptance pass after restarting. Save roundtrip and Steam Deck acceptance remain
pending. Dependency/binary licence inventory is required
before a distributable package.

Tooling validation: ShellCheck, Python compilation and four simulated-process
lifecycle tests pass. Run `python3 scripts/test_local_dev.py` to repeat them.
See [validation results](docs/VALIDATION.md) for the limits of those checks.


The overnight reliability build adds a local patch/base/jar stamp. Source builds
write it after success; `--no-build` refuses missing or mismatched stamps. Enable
**SoloScape server features** only for our patched server, then **Direct movement**
if desired. With server features off, the controller uses ordinary walking and
same-tile Walk cancellation. See [protocol extensions](docs/PROTOCOL_EXTENSIONS.md).


After changing source, export the patch stack and run `python3 scripts/verify_patches.py client` and `python3 scripts/verify_patches.py server`. These compare every modified/untracked source file with the reproduced stack, including native hooks. The root tests exercise missing files and changed contents. See `docs/MORNING_REPORT.md` for the current verified batch and acceptance steps.
