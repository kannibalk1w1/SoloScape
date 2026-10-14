# Settings harness ownership, 14 October 2026

Worker: Claude Sonnet 5.5 (`claude-sonnet-5-5`), no Opus/Haiku. Follow-up to [CONTROLLER_PANEL_LESSONS_20261014.md](CONTROLLER_PANEL_LESSONS_20261014.md). Harness-only change: **no product source or patch changed** (client 0053 / server 0022 stacks and jars untouched). Host evidence only (private Xvfb 892×529, software renderer, disposable profile, virtual pad); not hardware.

## Cause (confirmed)

`NativeAdventureProbe` steps 9/10 called `ui.update(new GamepadState(), …)` from the probe thread. On a no-pad host the plugin's own ClientTick runs between probe ticks, finds `rawState.connected == false` (SDL polling clears it) and, by design, calls `ui.reset()` every tick. So the adopted Settings panel was gone by the next probe call: `settingsOpen=true focusedPanel=none native=261 canvasFocus=true padConnected=false`. Production keeps that disconnect reset; only the harness was wrong. Setting `rawState.connected=true` alone does not help, because the plugin's own `poll` overwrites it on the next tick.

## Fix

- A scoped virtual pad: `padOn()` pauses only SDL polling (the plugin's `failed` flag, same as the other pad probes), then a `ClientTick` listener (priority −1000) sets a connected, neutral `rawState` and calls the plugin's real `processInput` every client tick. `padOff()` unregisters it and restores polling; it runs on the success path and in the probe's failure handler. The run asserts `sdl_polling_restored`.
- Release-and-push is kept: after adoption the pad stays neutral for 3 plugin ticks (the UI re-arms only from neutral), then B is held for exactly one tick and released.
- Home ancestry is observed where production consumes it: after B the plugin hands `takeHomeBack()` to the tab radial, so the probe checks `radial.active()` and `radial.selected() == SETTINGS` (it can no longer call `takeHomeBack()` itself).
- New focused mode `scripts/smoke-profile.sh --settings` (`-Dsoloscape.settings.probe=true`): skips tabs, journal and text stages, then runs the normal relog tail. About 20 s per session.

## Acceptance (repeatable)

```sh
export $(grep -v '^#' config/local.env | xargs)
scripts/smoke-profile.sh --settings     # focused, ~1.5 min total with New + Continue
scripts/smoke-profile.sh --adventure    # full run; previously stopped at "Settings disappeared on second tick", now passes
cd scripts && python3 -m unittest discover -p 'test_*.py'
```

Evidence in `docs/evidence/settings-ownership/`: `settings-only-new.json` / `settings-only-continue.json` (both sessions: `settings_gateway_two_tick_adoption`, `settings_config_round_trip`, `keyboard_classic_settings_round_trip`, `settings_back_to_home`, `sdl_polling_restored`, about 150 plugin ticks before B), `live-settings.png` (reviewed: local Controller setup / Basics panel adopted, hints show `[B]: back`).

What the run proves: Settings stays adopted for at least two real plugin ticks; a preference change and its reversal reach the config proxy; one-tick B closes local settings and returns to Home Settings; polling and plugin input resume afterwards. `scripts/test_settings_probe.py` pins the contract (scoped pause, restore on both paths, no direct `ui.update`, one-tick B after a neutral beat, flag wiring).

## Remaining

Physical pad and Steam Input not exercised; the virtual pad is neutral except the single B pulse, so stick/D-pad navigation inside Settings is still only covered by the model tests.
