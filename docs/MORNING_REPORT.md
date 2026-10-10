# Combined morning report — 10 October 2026

The controller journeys/recovery sprint and real Steam Deck deployment sprint are delivered on `overnight/controller-sprint`. Public main remains unchanged. The latest physical launcher feedback prompted a focused keyboard correction; its automated checks pass, with physical acceptance still needed.

## Current project

SoloScape launches a pinned revision-634 client and local server into independent character worlds. Controller camera, aiming/interaction, movement feedback and reversible direct movement have owner acceptance. Home-tab radial, contextual B ancestry, right-stick menu scrolling, remapping/presets and optional inventory/equipment/bank/shop/quest/skills/combat/prayer/spellbook screens are implemented. Native game validation and actions remain authoritative.

The launcher supports character creation, New/Continue, verified backups/restore/import, retention and owned-session recovery. Complete Cook's Assistant and Rune Mysteries server routes/rewards/save-reload pass, alongside earlier gather/commerce/combat/food routes. These content fixtures do not replace physical playthrough acceptance.

The preserved [journeys report](MORNING_REPORT_JOURNEYS.md) contains the previous batch's full changes, content evidence and Claude findings. [Project handoff](PROJECT_HANDOFF.md) is the detailed context to take to ChatGPT; [roadmap](ROADMAP.md) is the proposed wider task list.

## What this Deck sprint added

- Private reproducible owner-to-device snapshots with allowlisted files, compatible cache, project-local Java 21/8, matched archives and SHA-256 manifest checks. Pinned Git packing excludes stashes and dangling private blobs; path/link/config checks guard export and setup. No cache, saves, credentials, binary bundle or remote-access details enter Git.
- A working **SoloScape Test** Desktop/application shortcut on the actual SteamOS Deck, without system installs or Steam configuration edits. Native software-renderer Desktop launch, SDL controller detection and isolated profiles work.
- Actual Deck New/Continue/adventure/settings/logout/relog/save/cancel probes, plus native client-and-server pidfd recovery after their disposable parent dies. Exact saves and backups pass. Wayland global-pointer probe failures were retained, diagnosed and replaced with explicitly scoped AWT native-canvas tests.
- Bounded native render-interval and PID-identity resource measurements, with honest limits on CPU, RSS, battery and host sensors.
- A Steam-preferred launcher keyboard choice following physical feedback. Steam mode pauses SDL entry/form actions; local mode consumes mapped cursor keys. Controller traversal can reach fields without auto-opening, Enter advances and neutral is required after entry. An explicit desktop-navigation choice prevents competing Swing/SDL navigation.

## Verification and measurements

| Check | Result |
| --- | --- |
| Fresh client tests/shadow build after keyboard fix | 179 cases; no failures/errors; one existing optional SDL skip |
| Root tooling tests | 78 passing on host and Deck in the deployment checkpoint |
| Selected content slice | 20 passing cases retained from journeys; not rerun for the launcher-only fix |
| Exact exported source stacks | 100 client files through 0029; 33 server through 0011 |
| Swing launcher | Local entry/backend and system-mode focus/Enter/input isolation pass |
| Real Deck native New/Continue | Exact saves, four backups, settings reversal, logout/relog and pre-ready cancellation pass |
| Real Deck native recovery | Both owned JVMs verified/recovered; recovered snapshot valid; clean shutdown unconfirmed |

Baseline r6 native render callbacks: median **23.92 / 23.27 ms** for New/Continue; custom journal **31.91 / 30.53 ms**. Whole-session peak simultaneous RSS sums **3013 / 2600 MiB**, with shared-page double counting. These are short windowed software-renderer Desktop observations, not GPU presentation FPS, input latency or sustained Gaming Mode/battery budgets. [Detailed evidence](DECK_VALIDATION.md) and [setup guide](DECK_SETUP.md) record methods and limits.

Actual Claude completed Deck design/follow-up and launcher keyboard static reviews through the existing Orca terminal. Reported findings drove export privacy, metric scope, probe ownership and keyboard navigation changes. Static review is separate from runtime and physical acceptance; no current usage-window percentage is inferred.

## Next work

1. Physically accept the updated launcher keyboard on Deck Desktop and Gaming Mode, including reopen, field traversal, local fallback and Steam + X.
2. **Extend exclusive keyboard ownership to all in-game text entry**, explicitly requested and parked in the roadmap: chat, searches, names/dialogue and numeric prompts.
3. Play the quest/gather/commerce/combat slice from a fresh profile; confirm journal progress, source-to-target handoff, settings ancestry, scrolling and save/restart ergonomics.
4. Establish repeatable Gaming Mode frame-time/loading/memory/battery/suspend evidence, then select measured optimizations such as journal rendering.
5. Validate clean-machine setup/update/recovery and audit redistribution/dependency licences before publishing a packaged release.

Retain old private snapshots and verify stopped-world backups before updates. OpenGL, physical controller comfort, every crash timing, suspend/resume and exhaustive content remain unclaimed. Keep 6.1 Sol for this integration work; changing model cannot accelerate device transfers or tests.
