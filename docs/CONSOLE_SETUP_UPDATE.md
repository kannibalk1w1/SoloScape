# Repeatable local build and update

Start with README-SOLOSCAPE.md for the three pinned upstream clones, Python/Bash/Git/flock, project-local JDK 21 + 8 and the authorized modified cache. CACHE_SETUP.md records the upstream-project source and exact verified archive/hash. This repository does not redistribute game assets or provide a packaged release.

## First build, or after taking a development-branch update

```bash
./scripts/prepare-build.sh
./scripts/launcher.sh
```

Prepare validates runtime/source/cache prerequisites without needing a graphical display or a free game port, applies the ordered patches, builds the matched client/server pair and writes/verifies their patch/base/jar stamp. It never launches a world, rotates session logs or migrates/deletes a character. The first Gradle dependency resolution may need network access. Subsequent cached builds are incremental. A failed build never advertises a new valid stamp.

Save & Quit **all owned sessions before updating or rebuilding**. The GUI and development launchers hold an archive lock through child shutdown and saved-world verification, so Prepare refuses a live owned world. There is no safety claim for a manually started JVM that bypasses these launchers. Do not update sources under an unrelated manually launched game.

For a clean checkout of the existing development branch:

```bash
git status --short
git pull --ff-only
./scripts/prepare-build.sh
```

Only pull after committing/stashing your own tracked changes; do not discard local work. The local branch name can differ from the tracked remote `overnight/controller-sprint`. Do not switch back to public main in the same patched source checkout: use a fresh checkout for the older stack. Do not update upstream pins casually; the patch stack and compatible cache are audited against exact commits.

New Character/Continue in the graphical launcher uses private per-character worlds. Existing legacy saves stay in `upstream/game-server/data/saves/`; importing uses the stopped-world-copy workflow in ALPHA_LAUNCHER.md/PROJECT_HANDOFF.md. Take a manual verified backup before an upgrade. If a save is damaged, restore a verified backup into a new generation; prior generations stay on disk. Manage Backups provides explicit previewed cleanup of older automatic archives.

If the game port is occupied, select another in Launcher Settings. Prepare does not probe or stop that listener. Gameplay controller settings are per-profile in the SoloScape Controller plugin, separate from Launcher Settings.

For contributors, validate root tooling and exported sources:

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/verify_patches.py client
python3 scripts/verify_patches.py server
```

Native gameplay smoke requires Xvfb and the matched local cache/build: `./scripts/smoke-profile.sh`. It uses a separate display, port and disposable world; it preserves the existing game and compares original mutable paths. Native client/server suites require the pinned checkouts and project-local Java toolchains; the repository CI runs the asset-free root checks, shell/patch syntax and whitespace only.

See CONSOLE_SESSION_ACCEPTANCE.md for physical controller/Deck checks and reproducible performance records. A desktop source build remains the supported development delivery; installer/distributable licences and Steam Gaming Mode release packaging are future work.
