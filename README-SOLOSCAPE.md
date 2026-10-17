# SoloScape 2011+

Latest prepared private native test build: [51/56 snapshot, screenshot, New/Continue and sampled resource evidence](docs/NATIVE_TEST_BUILD_51_20261017.md). The local payload is for owner testing; it is not a public release or an installed Deck update.

Development source build for a local RuneScape revision-634 experience with native controller support and eventual Steam Deck delivery. The controller build includes reversible direct movement, target/movement feedback, native UI navigation, Home and quick-action radials, optional custom inventory/equipment/bank/shop screens, shared menu back navigation, active-pane right-stick scrolling, remapped physical hints, exclusive in-game text ownership and a reversible classic controller UI theme.

The graphical launcher provides controller character naming, independent local worlds, verified backups/restore, explicit backup management and ownership-checked Recover Session. [Historical 10 October completion report](docs/MORNING_REPORT.md), [setup/update instructions](docs/CONSOLE_SETUP_UPDATE.md) and [physical acceptance checklist](docs/CONSOLE_SESSION_ACCEPTANCE.md) record evidence and remaining limits. No packaged release or completed Deck acceptance is claimed.

Start at [current status and evidence](docs/CURRENT_STATUS.md), then [playtest direction](docs/PLAYTEST_DIRECTION.md). The [roadmap](docs/ROADMAP.md) is the proposed working task list; its 17 October review keeps native 2010–2011/Deck acceptance first. [Backport architecture](docs/BACKPORT_ARCHITECTURE.md) and [WASM feasibility](docs/WASM_FEASIBILITY.md) are research tracks, not a cache replacement or web port.
The current work batch adds [corner running and RT precision walking](docs/CONTROLLER_CORNER_MOVEMENT.md), a [bounded solo-content audit](docs/SOLO_CONTENT_AUDIT.md), and an [isolated WASM edge-kernel result](docs/WASM_RASTER_POC.md). New movement still requires physical Deck acceptance.

The [Steam Deck player guide](docs/SOLOSCAPE_STEAM_DECK_PLAYER_GUIDE.md) is standalone Markdown for first-time play and Obsidian.
The [10 October handoff](docs/PROJECT_HANDOFF.md) is a historical discussion snapshot; branch/build/test-count claims there are superseded by the current status index.

The completed controller/Deck work is integrated into the GitHub default branch `main`. Source checkouts under `upstream/` are
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

The owner has confirmed basic launch/camera/movement in earlier sessions. Newer scripted Deck, save/recovery and performance evidence is indexed in [CURRENT_STATUS](docs/CURRENT_STATUS.md); it does not establish full physical controller acceptance. Runtime/dependency licence review remains required before distribution.

Tooling validation: Python tests/compilation, ShellCheck and patch/whitespace checks pass. Run `python3 -m unittest discover -s scripts -p 'test_*.py'`. See [validation results](docs/VALIDATION.md) and the combined report for the limits of those checks.


The overnight reliability build adds a local patch/base/jar stamp. Source builds
write it after success; `--no-build` refuses missing or mismatched stamps. Enable
**SoloScape server features** only for our patched server, then **Direct movement**
if desired. With server features off, the controller uses ordinary walking and
same-tile Walk cancellation. See [protocol extensions](docs/PROTOCOL_EXTENSIONS.md).


After changing source, export the patch stack and run `python3 scripts/verify_patches.py client` and `python3 scripts/verify_patches.py server`. These compare every modified/untracked source file with the reproduced stack, including native hooks. The root tests exercise missing files and changed contents. See [CURRENT_STATUS](docs/CURRENT_STATUS.md) for the reviewed evidence index and acceptance limits.

## Current player and contributor entry points

- [Physical acceptance](docs/CONSOLE_SESSION_ACCEPTANCE.md), [human playtest workflow](docs/PLAYTEST_DIRECTION.md) and the GitHub **Human playtest finding** issue form.
- [Latest recorded Deck validation and diagnostic screenshots](docs/DECK_CONTROLLER_VALIDATION_20261014.md). Installed build claims are dated evidence, not live device discovery.
- [Controller input and in-game Save & Quit](docs/LAUNCHER_INPUT_AND_QUIT.md): Home → Settings → Finish → Save & Quit, then fresh A to confirm.
- F11 toggles fullscreen; configure Fullscreen Toggle Key in RuneLite Window settings or map a Deck rear button. Returning restores window bounds/size lock.
- [Text ownership](docs/IN_GAME_TEXT_INPUT.md), [representative content coverage](docs/CONTENT_COVERAGE.md), [manual verified save transfer](docs/SAVE_SYNC.md) and [controller acceptance contracts](docs/CONTROLLER_INTERACTION_ACCEPTANCE.md).
- Historical [playtest 2](docs/PLAYTEST_2.md), [classic UI/art pass](docs/JAGEX_UI_OVERHAUL.md) and [UI Deck release](docs/UI_DECK_RELEASE.md) retain their own scope and dates. They do not replace current acceptance status.

Generate the evidence index with `python3 scripts/current_status.py`; CI checks it with `--check`. Edit `docs/current-status.json` when reviewed evidence changes. Historical reports stay unchanged.
