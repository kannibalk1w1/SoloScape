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
- Earlier playtest-two probe covers actual player-lit fire cooking and Blood Pact projection. The projection fix captures the world renderer state before interface model rendering overwrites it, so it applies across instances rather than special-casing Blood Pact. Untested instance layouts still need gameplay coverage.
- The adventure probe's existing “Settings disappeared on second tick” failure is documented in [UI overhaul](JAGEX_UI_OVERHAUL.md).

## Steam Deck deployment and performance

Deployment results and measurements are added after testing the private candidate on the device. Previous sustained measurements, with their separate candidate and conditions, remain in [60 FPS report](DECK_60FPS_REPORT.md).
