# UI and playtest release — 13 October 2026

This release includes the playtest fixes, per-world XP/drop/run settings, Jagex-style launcher and controller UI, D-pad tab-bar focus, native skill artwork and levels, save sync, fullscreen and Deck pacing/profiling tooling. Client patches run through 0044; server patches through 0018.

![Native item artwork in the controller inventory](images/jagex-inventory-1280x800.png)
![Native skill artwork and levels](images/jagex-skills-1280x800.png)
![Native client Skills capture](images/jagex-live-skills.png)

Inventory and bank previews use actual sprites rendered from the compatible 634 cache; their data and selections are fixtures. Skill icons come from the client's existing resources. The live capture uses a disposable native world and scripted controller input. Individual cache sprites, character saves and authentication files remain private.

## Validation

- Client: 241 cases, zero failures/errors, one optional SDL skip.
- Tooling: all 99 tests pass.
- Patch reproduction: all 135 client and 50 server modified/patched files match the exported patch stacks.
- Native artwork and tab-bar smoke: 32 item sprites captured, real Skills tab opened, focus/highlight/A/B guards verified; New/Continue preserves save fields, four backups verified, cancelled startup preserves the entire saved world.
- Final playtest-two probe covers actual player-lit fire cooking and Blood Pact projection. The projection fix captures the world renderer state before interface model rendering overwrites it, so it applies across instances rather than special-casing Blood Pact. Untested instance layouts still need gameplay coverage.
- The adventure probe's existing “Settings disappeared on second tick” failure is documented in [UI overhaul](JAGEX_UI_OVERHAUL.md).

## Steam Deck deployment and performance

The private `deck-ui-20261013-r22` snapshot passed all 10,492 manifest file checks. The existing character received a verified pre-deployment backup; all 88 copied profile files matched their source hashes. The old r10 installation remains available. The copied profile enables **Deck 60 FPS target**; original preferences are retained separately. This selects OpenGL/60 FPS pacing and disables animated scenery shadows. Character/world data is unchanged.

The existing SoloScape Steam shortcut uses `/home/deck/SoloScape-test/launch.sh`; deployment switches that wrapper to r22. Select **Continue** in the launcher to test the existing character.

A temporary Steam shortcut launched `smoke-profile.sh --desktop --deck60-gl-only --tab-bar` in Gaming Mode. It passed native tab navigation, New/Continue save-field preservation, four verified backups and entire-world preservation on startup cancellation. The temporary shortcut is removed after testing. The initial background service run did not present its window and is excluded from measurements.

| 1280×800 OpenGL, 60 FPS cap | New | Continue |
| --- | ---: | ---: |
| Average FPS | 59.65 | 59.90 |
| Median frame interval | 16.71 ms | 16.66 ms |
| p95 frame interval | 18.67 ms | 18.05 ms |
| p99 frame interval | 23.89 ms | 19.81 ms |

The uncapped comparisons averaged 60.00 FPS under the compositor. Both samples confirm AMD hardware OpenGL, controller connected, canvas focused and actual 1280×800 native dimensions. Each stage lasts 25 seconds, with frame samples taken after its first ten seconds. Aggregate evidence: [New](performance/ui-r22-new.json) and [Continue](performance/ui-r22-continue.json).

These are short stationary disposable-world checks with the native inventory shown and custom controller panels closed during timing. They measure overlay callback intervals, not independent scanout; they do not establish sustained 60 FPS during routes or quantify the open Skills panel. The first capped p99 exceeds 20 ms. Physical D-pad/Steam Input mapping remains a user playtest check. AWT Robot captures from Gaming Mode returned black, so the published UI screenshots use the verified host native captures and clearly labelled renderer fixtures.

Previous sustained measurements, with their separate candidate and conditions, remain in [60 FPS report](DECK_60FPS_REPORT.md).

## Content build r24

The merged content batch from [PR #6](https://github.com/kannibalk1w1/SoloScape/pull/6), commit `7a95e1e65e235d1f61b0abd764cc744a760c59b2`, is installed as `deck-content-20261013-r24`. All **10,510** manifest files verified. The ended r22 session was explicitly recovered; a recovery snapshot and a separate pre-deployment backup verified. Recovery does not establish that the original session shut down cleanly.

All **95** copied profile files match their source hashes, and the character save is unchanged. The stable Steam shortcut now selects r24, and its launcher and backend were observed running after launch through Steam. Older builds and the previous wrapper remain available. Continue uses the transferred character and retains the Deck 60 FPS preference.

This build includes launcher mapped-controller navigation, controller **Save & Quit**, readable quest introductions/rewards and recipe names, and the pot-firing selection fix. See [coverage and native screenshots](CONTENT_COVERAGE.md). The performance measurements above were made on r22; r24 has no new sustained-FPS measurement. Physical controller navigation and gameplay remain playtest acceptance.

## Animated launcher and save-reader build r25

The owner Deck now uses `deck-charm-20261013-r25`, the exact merged [PR #9](https://github.com/kannibalk1w1/SoloScape/pull/9) build from commit `5e024750ea6ce682214cbcd8d4a45106e476f29b`. It includes the 22 px launcher supporting text, animated braziers, all five pottery recipe fixes/coverage, and the long-event save-reader fix found through [Druidic Ritual's graphical coverage](DRUIDIC_RITUAL_GRAPHICAL.md).

All **10,527** private payload files match the manifest. The ended r24 session received a verified recovery snapshot, followed by a verified pre-deployment backup. All **99** copied profile files match, and the character save is unchanged. Recovery does not establish clean closure of the earlier session. The old build and previous stable wrapper remain available.

The stable Steam shortcut selects r25. Launch through Steam succeeded; its launcher and backend were observed running from the new build, with the transferred profile ready for Continue. Deck 60 FPS settings are retained. The deployment did not overwrite a live game or save.

[Animated preview, screenshot and host paint measurements](JAGEX_UI_OVERHAUL.md#animated-launcher-braziers) accompany the pass. Host paint measurements and earlier r22 game-frame measurements have separate conditions; r25 has no new sustained Deck FPS acceptance or physical-pad playthrough claim.

## Reference-flame revisions r26 and r27

[PR #11](https://github.com/kannibalk1w1/SoloScape/pull/11) replaces procedural fire with the privately supplied eight-frame login sheet and uses the heavier RuneScape bold face for supporting text. Its r26 deployment verified 10,532 payload files and all 100 transferred profile files, preserving the character save. Wider character-frame insets expose both braziers.

Owner feedback then identified atlas-frame misalignment and excessive speed. [PR #12](https://github.com/kannibalk1w1/SoloScape/pull/12) normalizes the frames against their stationary bowl origins, maps them to the measured original backdrop rim, and doubles each pose's duration to approximately 198 ms. All eight poses were rendered and visually checked; [captures and host evidence](JAGEX_UI_OVERHAUL.md#stable-reference-alignment-and-slower-playback) are included. The original supplied sheet remains unchanged and private.

The active Deck build is now `deck-aligned-20261013-r27`, from commit `5d629baeba50394642d71385b3020d775395a64e`. All **10,536** payload files verified. A pre-deployment backup verified, all **101** copied profile files match, and the character save is unchanged. Existing launcher port settings are preserved when present. No live world was interrupted: the idle launcher/backend were closed under build/profile guards before promotion. Older builds and stable wrappers remain available.

The stable Steam shortcut was restarted into r27; its actual launcher/backend were observed running with the saved profile ready. The bold supporting text is retained. Host paint checks and rendered pose previews do not establish physical-controller acceptance or sustained Deck FPS.

## Launcher refresh correction r28

[PR #14](https://github.com/kannibalk1w1/SoloScape/pull/14) restores the launcher's 33 ms repaint target while keeping six ticks per flame pose, so slow playback remains approximately 198 ms per pose. Host Swing observation: 30.39 timer updates/second; this is not a presented-frame Deck measurement. [Evidence and details](JAGEX_UI_OVERHAUL.md#launcher-refresh-restored-independently-of-flame-speed).

The Deck now runs `deck-refresh-20261013-r28`, from commit `3803767b285c89ce4a63eed35fbd5d3c54e32ee4`. All **10,539** payload files verify; all **102** transferred profile files match, the character save is unchanged and a pre-deployment backup verifies. Existing launcher port settings are preserved when present. No live world was interrupted; only the guarded idle launcher/backend were closed. The stable shortcut was restarted through Steam, and the new launcher/backend were observed running with the saved profile ready.

The aligned slow flame loop, heavier supporting text and Deck gameplay pacing preferences remain. The [proposed next large sprint](NEXT_DECK_SESSION_SPRINT.md) covers complete controller-only routes, sustained gameplay performance and save/suspend reliability; it has not started.
