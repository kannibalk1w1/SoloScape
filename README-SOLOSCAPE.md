# SoloScape 2011+

Development source build for a local RuneScape revision-634 experience with native controller support and eventual Steam Deck delivery. The controller build includes reversible direct movement, target/movement feedback, native UI navigation, Home and quick-action radials, optional custom inventory/equipment/bank/shop screens, shared menu back navigation, active-pane right-stick scrolling and remapped physical hints.

The graphical launcher provides independent local worlds, verified backups/restore and explicit backup management. [Combined completion report](docs/MORNING_REPORT.md), [setup/update instructions](docs/CONSOLE_SETUP_UPDATE.md) and [physical acceptance checklist](docs/CONSOLE_SESSION_ACCEPTANCE.md) record evidence and remaining limits. No packaged release or completed Deck acceptance is claimed.

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
./scripts/prepare-build.sh
./scripts/launcher.sh
# Legacy development world instead of isolated profiles:
./scripts/dev-run.sh --no-build
```

Prepare applies the tracked client/server patches and builds `:game:shadowJar` and
`:client:shadowJar` without starting a world. The graphical launcher selects independent profiles. The legacy development launcher starts the server,
waits for its loaded-world message and launches the client explicitly at
`127.0.0.1:43594`. Logs stream to the terminal and `.runtime/server.log` /
`.runtime/client.log` (one previous session retained). Closing the client or Ctrl+C stops
owned children with SIGTERM and waits for normal save/shutdown hooks. A hung
shutdown is reported and never forcibly killed. There is no separate stop
script because the foreground launcher owns this lifecycle.

The patched server defaults to IPv4 loopback. Explicit LAN hosting is a separate audited configuration. The legacy development path uses upstream `data/saves/`; the graphical launcher uses private profiles with bots disabled. Preserve either world when updating source. Build locks prevent rebuilding jars during an owned session; Save & Quit before source updates. See [setup/update](docs/CONSOLE_SETUP_UPDATE.md).

The cache was downloaded with explicit user authorization from upstream's linked
MEGA folder. See [cache provenance](docs/CACHE_SETUP.md). Cache and archive remain
ignored by Git.

The owner confirms launch, camera, improved walking/aiming and optional direct movement. The latest menu/art/recovery milestone has 151 client cases (one optional SDL skip), 44 root tooling cases, 11 selected native game cases and isolated graphical New/Continue/cancellation evidence. These are not physical controller/Deck acceptance. Runtime/dependency licence review remains required before a distributable package.

Tooling validation: Python tests/compilation, ShellCheck and patch/whitespace checks pass. Run `python3 -m unittest discover -s scripts -p 'test_*.py'`. See [validation results](docs/VALIDATION.md) and the combined report for the limits of those checks.


The overnight reliability build adds a local patch/base/jar stamp. Source builds
write it after success; `--no-build` refuses missing or mismatched stamps. Enable
**SoloScape server features** only for our patched server, then **Direct movement**
if desired. With server features off, the controller uses ordinary walking and
same-tile Walk cancellation. See [protocol extensions](docs/PROTOCOL_EXTENSIONS.md).


After changing source, export the patch stack and run `python3 scripts/verify_patches.py client` and `python3 scripts/verify_patches.py server`. These compare every modified/untracked source file with the reproduced stack, including native hooks. The root tests exercise missing files and changed contents. See `docs/MORNING_REPORT.md` for the current verified batch and acceptance steps.
