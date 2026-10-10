# Combined morning report — 10 October 2026

The controller journeys/recovery, Steam Deck deployment and in-game keyboard/classic UI sprints are delivered on `overnight/controller-sprint`. Public main remains unchanged. Physical controller and Steam keyboard acceptance remains separate from automated/native testing.

## Current project

SoloScape launches a pinned revision-634 client and local server into independent character worlds. Controller camera, aiming/interaction, movement feedback and reversible direct movement have owner acceptance. Home-tab radial, contextual B ancestry, right-stick menu scrolling, remapping/presets and optional inventory/equipment/bank/shop/quest/skills/combat/prayer/spellbook screens are implemented. Native game validation and actions remain authoritative.

The launcher supports character creation, New/Continue, verified backups/restore/import, retention and owned-session recovery. Complete Cook's Assistant and Rune Mysteries server routes/rewards/save-reload pass, alongside earlier gather/commerce/combat/food routes. These content fixtures do not replace physical playthrough acceptance.

The preserved [Deck report](MORNING_REPORT_DECK.md) records the previous deployment checkpoint. The [journeys report](MORNING_REPORT_JOURNEYS.md) contains the previous batch's full changes, content evidence and Claude findings. [Project handoff](PROJECT_HANDOFF.md) is the detailed context to take to ChatGPT; [roadmap](ROADMAP.md) is the proposed wider task list.

## What this Deck sprint added

- Private reproducible owner-to-device snapshots with allowlisted files, compatible cache, project-local Java 21/8, matched archives and SHA-256 manifest checks. Pinned Git packing excludes stashes and dangling private blobs; path/link/config checks guard export and setup. No cache, saves, credentials, binary bundle or remote-access details enter Git.
- A working **SoloScape Test** Desktop/application shortcut on the actual SteamOS Deck, without system installs or Steam configuration edits. Native software-renderer Desktop launch, SDL controller detection and isolated profiles work.
- Actual Deck New/Continue/adventure/settings/logout/relog/save/cancel probes, plus native client-and-server pidfd recovery after their disposable parent dies. Exact saves and backups pass. Wayland global-pointer probe failures were retained, diagnosed and replaced with explicitly scoped AWT native-canvas tests.
- Bounded native render-interval and PID-identity resource measurements, with honest limits on CPU, RSS, battery and host sensors.
- A Steam-preferred launcher keyboard choice following physical feedback. Steam mode pauses SDL entry/form actions; local mode consumes mapped cursor keys. Controller traversal can reach fields without auto-opening, Enter advances and neutral is required after entry. An explicit desktop-navigation choice prevents competing Swing/SDL navigation.

The installed **SoloScape Test** shortcut now selects verified private snapshot r8. The r8 update checked closed processes, archive locks and outstanding records; the normal r7 profile store remained absent. All old snapshots and disposable test evidence remain; no normal characters existed to migrate. The new local/system-mode Swing launcher probe and doctor also pass on the actual Deck.

## Verification and measurements

| Check | Result |
| --- | --- |
| Fresh client tests/shadow build after in-game keyboard fix | 192 cases; no failures/errors; one existing optional SDL skip |
| Root tooling tests | 78 passing on host and Deck in the deployment checkpoint |
| Selected content slice | 20 passing cases retained from journeys; not rerun for the launcher-only fix |
| Exact exported source stacks | 106 client files through 0030; 33 server through 0011 |
| Swing launcher | Local entry/backend and system-mode focus/Enter/input isolation pass |
| Real Deck native New/Continue | Exact saves, four backups, settings reversal, logout/relog and pre-ready cancellation pass |
| Real Deck native recovery | Both owned JVMs verified/recovered; recovered snapshot valid; clean shutdown unconfirmed |

Baseline r6 native render callbacks: median **23.92 / 23.27 ms** for New/Continue; custom journal **31.91 / 30.53 ms**. Whole-session peak simultaneous RSS sums **3013 / 2600 MiB**, with shared-page double counting. These are short windowed software-renderer Desktop observations, not GPU presentation FPS, input latency or sustained Gaming Mode/battery budgets. [Detailed evidence](DECK_VALIDATION.md) and [setup guide](DECK_SETUP.md) record methods and limits.

Actual Claude completed Deck design/follow-up and launcher keyboard static reviews through the existing Orca terminal. Reported findings drove export privacy, metric scope, probe ownership and keyboard navigation changes. Static review is separate from runtime and physical acceptance; no current usage-window percentage is inferred.

## In-game keyboard and classic UI sprint

- **Exclusive text ownership:** Automatic prefers Steam on a detected Deck, with Steam / physical and local controller alternatives. Recognized native amount/name/string/bank-search prompts pause world, camera, radials and the local key grid. Native typing stays native; replacement prompts reject stale taps and finish requires neutral rearming.
- **Chat and other native entry:** unbound right-stick click or Settings → Finish → Open text keyboard starts a deliberate session. Ordinary printable typing can take ownership without launching Steam. The text panel provides Reopen/Done/Cancel, with pointer capture limited to its bounds. Native Escape can preserve unsent text; this is documented.
- **Native cancellation correction:** real-cache testing found script 112 Escape does not close ordinary amount/name/string prompts. Guarded controller/panel Cancel now uses pinned native `close_entry` 101. This closes the client prompt; server suspension cancellation still follows native interaction/dialogue lifecycle, not an invented packet.
- **Claude's implemented visual pass:** optional classic stone/brown panels, bronze trim, gold focus, cream text, parchment tooltips and period-style headings. Home and quick radials share it. Geometry, action tokens and hitboxes stay native; **Classic controller UI** toggles back to the previous palette.
- **Discoverability:** Home → Settings → Basics contains both keyboard and style preferences. Right-stick chat activation respects remapped bindings. The explicit Settings action remains available.

192 client cases pass with one existing optional SDL skip; 78 root cases pass. Matched shadow jar/stamp and exact 106-client/33-server patch reproduction pass. Twenty synthetic previews render in both palettes at small and Deck sizes; representative layouts were visually inspected. Public fixture pictures contain no cache artwork. [UI details/previews](CLASSIC_CONTROLLER_UI.md) and [text ownership scope](IN_GAME_TEXT_INPUT.md) describe behavior.

The focused host New/Continue native batch passes real CS2 types 7/8/9 edit/cancel, native public-chat Enter delivery, Escape without submission, retained-text cleanup, unchanged player tile, logout/relogin, fresh capabilities, exact saves/four backups and early-startup cancellation. Steam visibility is injected in these fixtures. Full host and real Deck New/Continue adventure/settings checks also pass, including both keyboard/style preference reversals, B-to-Home and zero non-probe mouse clicks. Complete-session totals were host **88.200 / 85.997 s**, Deck **89.245 / 88.077 s**; these include login, probe waits, relog and save, and are not launch-time or performance targets. No physical keyboard visibility is inferred.

Actual Claude implemented the theme and completed several bounded keyboard/cancel/cleanup reviews. Its high/medium findings were fixed: physical-key swallowing, unwanted typed-key popups and full-canvas mouse capture. Follow-up found no blockers. Remaining notes cover arbitrary custom Steam mappings, server suspension after client-only cancellation and type-11 real-bank coverage. [Review](CLAUDE_INGAME_KEYBOARD_REVIEW.md).

Installed r8 source: `0588ad6ec2e357859ba49551f8303408298b0195`; **10,380** manifest files, SHA-256 `dd8ba770db3405f72c2e20c26714276e44c062e7602c6a3a76164eba80a489be`. Deck manifest/doctor and 106/33 source checks pass. Wayland screenshot capture returned black, so real-panel visual acceptance remains open; the published pictures are renderer fixtures. [Deployment evidence](DECK_VALIDATION.md) records the private test paths.

## Next work

1. Physically accept the updated launcher keyboard on Deck Desktop and Gaming Mode, including reopen, field traversal, local fallback and Steam + X.
2. Physically accept in-game text ownership for amounts/names/search/chat, then extend automatic recognition to remaining widget-specific text paths and verify server Withdraw-X cancellation/logout.
3. Play the quest/gather/commerce/combat slice from a fresh profile; confirm journal progress, source-to-target handoff, settings ancestry, scrolling and save/restart ergonomics.
4. Establish repeatable Gaming Mode frame-time/loading/memory/battery/suspend evidence, then select measured optimizations such as journal rendering.
5. Validate clean-machine setup/update/recovery and audit redistribution/dependency licences before publishing a packaged release.

Retain old private snapshots and verify stopped-world backups before updates. OpenGL, physical controller comfort, every crash timing, suspend/resume and exhaustive content remain unclaimed. Keep 6.1 Sol for this integration work; changing model cannot accelerate device transfers or tests.
