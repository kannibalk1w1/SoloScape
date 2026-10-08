# Console alpha local-world launcher (development branch)

After the normal source/cache/runtime setup and a matched client/server build:

```bash
./scripts/launcher.sh
```

New Character creates a private local world under `.runtime/profiles/<id>/`. Continue
starts its server and client on IPv4 loopback, using private save/derived/log paths and
a private client home/cache. The launcher generates a local login credential file with
owner-only permissions; passwords are not placed in command arguments or metadata.
Existing legacy worlds are not migrated or changed by New Character.

The server binds before content loading is finished; the launcher waits for native world
readiness before connecting. Save & Quit, closing the game, or closing the launcher
stops only the owned processes, waits for normal shutdown hooks and verifies a backup.
There is no forced-kill timeout. A slow shutdown remains visible in session status.

Back Up/Restore Backup require a stopped profile. A restore validates the archive and
switches to a new save generation; the old generation is retained. Backups include the
world's exchange state and failed saves. Derived caches and routine logs are excluded.
Restore can recover a damaged character TOML; profile-manifest recovery and legacy-world
migration are still being strengthened and are not exposed in this launcher yet.

Launcher Settings selects a free game port. If an existing game already uses 43594,
choose another port (for example 43595); do not stop another session merely to test this
launcher. Gameplay controller settings remain in the SoloScape Controller plugin.
Controller navigation uses D-pad/stick, A to activate, B to return, and bumpers to move
between focus controls. Creating a name currently uses ordinary desktop text entry.
Mouse and keyboard work throughout. Missing SDL is reported without blocking the UI.

Diagnostics checks pinned source, runtimes, cache presence and local port availability.
These presence checks do not prove cache/content compatibility. The official cache
source/setup instructions remain in the main README; no assets are redistributed.

Evidence so far: actual launcher rendered and closed successfully on a private Xvfb
display, without launching a game; private credential permission/origin tests; 30 root
protocol/profile/lifecycle tests. The screenshot below is an actual empty launcher,
not a gameplay or physical controller acceptance test.

![Actual graphical launcher smoke test](images/alpha-launcher-preview.png)
