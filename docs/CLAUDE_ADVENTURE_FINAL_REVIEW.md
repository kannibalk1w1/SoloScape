# Adventure batch: final static review

This was static only. I made no source or configuration edits, ran no game, build or test,
used no network, made no commits, and touched no saves, cache or credentials. Scope:
- `patches/client/0027-native-spell-requirements.patch`
- `patches/server/0010-actual-adventure-route-audit.patch`
- `scripts/harness/NativeAdventureProbe.java` and `NativeSessionSmoke.java`
- `scripts/smoke_profile.py`
- the two settings notes from the last follow-up

## Verdict
**No correctness blockers.** The spell-requirement decoding matches both the pinned client
decoder and the server. The route test is isolated and checks a native save round-trip. The
harness only sends validated native actions and doesn't print secrets. Two low, actionable
harness findings follow. Neither affects shipped code.

## Verified
**Spell requirements (0027)**
- In `Class46` (`Class46.java:561-576`), the first script array after the settings
  (`aClass348_Sub44_748`) and the optional parameter table is `anObjectArray815`. In
  `InterfaceDecoderFull.kt:200-201` and `InterfaceDecoder.kt:137`, the field read straight after
  `setting` is `information`. They are the same field.
- On the server (`content/skill/magic/spell/SpellRunes.kt:226-245`), the level is
  `information[5]` and the items are `(id, amount)` pairs at 8..15 (`i in 8..14 step 2`), stopping
  at `id == -1 || amount <= 0`. `ControllerSpellDetails.read` uses the same indices and the same
  stop rule.
- It also rejects:
  - non-`Integer` entries,
  - arrays with fewer than 16 entries,
  - levels outside 0–120,
  - negative ids,
  - amounts above 1,000,000.
- It doesn't change the cache array (the test checks this), and it's applied only to spell
  components that already have an `adventure` detail.
- "Magic level too low" compares `Class161.anIntArray2145[6]`, the boosted Magic level, with the
  same `has(Skill.Magic, level)` meaning the server uses. It is display-only; native actions
  are unchanged.
- One display-only difference: the server returns `null` (unavailable) for members runes on a
  free-to-play world, but the client still lists the runes. Gameplay is unaffected.

**Route test (0010)**
- The class runs only when `SOLOSCAPE_TEST_ROOT` is set. `WorldTest` then points saves, logs,
  errors, caching, `data.modified` and `wildcards` at that isolated root, and already sets
  `storage.disabled=true`, `autoSave=0` and `bots.count=0`.
- `verifySave` writes through `SaveQueue(FileStorage(tempdir))`, reloads with `PlayerSave.load`,
  compares tile, quest variables, experience and every saved inventory, and then deletes the
  temp directory.
- The route uses ordinary `walk` with an 80-tick limit per waypoint and a clear "Route blocked"
  failure. Doors, stairs and NPCs are found natively, and the bank deposit uses the native
  `interfaceOption`.
- `openDoor` returns quietly when no closed door is present, so a door that is already open
  isn't treated as a failure.

**Harness**
- Exit and logout use `invokeControl`. That rebuilds the expected widget from the live
  `Class46` and still goes through `ControllerUi.invoke`, so freshness, open group, `same()`
  and type-18 permission-gated actions are all checked. Only fresh native actions are sent.
- Relogin reads `SOLOSCAPE_AUTH_FILE` with `LocalCredentials` and writes only into the
  client's login fields. The `.status` / `.adventure.json` output and the Python `print`s
  contain no account name or password.
- The config round-trip goes through the real `ConfigManager` proxy and returns `deadzone` to
  its earlier value. Settings adoption is checked across two `ui.update` ticks, and B →
  `leavePanel` → Home ancestry is asserted.
- The frame overlay is a measuring aid. `smoke_profile` and the JSON label the results as
  Xvfb/software observations, not hardware acceptance.

**Settings notes from the last follow-up: both fixed**
- `canPresent` now requires `panel != null`, non-modal, and id 261 or 982
  (`ControllerSettingsModel.java:35`). `panel == null` is accepted only inside the 1 s opening
  grace.
- `presented()` no longer calls `ui.reset()`. It only clears `settingsOpen` and
  `nativeSettingsChild`, and the next `PanelControls.update` releases the panel normally.

## Findings (low, harness only)
1. **The private display isn't guaranteed to be ours** (`smoke_profile.py:39-43`).
   - `Xvfb :197` is started and checked once with `poll()` after 0.3 s.
   - If `:197` is already in use (a stale harness, or another session's virtual display), that
     Xvfb may exit after the check.
   - `DISPLAY=:197` would then point at the *other* server, and the full-screen
     `Robot.createScreenCapture` in both Java files would save whatever is on it into the test
     root.
   - A slow start can also make the run flaky.

   **Fix:** start `Xvfb -displayfd <fd>`, or choose a display that is free (no
   `/tmp/.X<n>-lock`). Wait until the display accepts connections (the `-displayfd` handshake),
   and fail if the Xvfb process isn't the owner. Optionally capture only the client frame's
   bounds rather than the whole screen.
2. **The two-tick settings check bypasses part of the real plugin tick**
   (`NativeAdventureProbe.java:62-70`).
   - The probe sets `settingsOpen` by reflection and calls `ui.update` itself. That exercises
     the real `Gateway`, `presented()`, `canPresent`, `leavePanel` and `ConfigManager`.
   - It skips `openHomeTab` (so `settingsOpeningUntil` and the grace aren't covered).
   - It also skips the plugin's own `onClientTick` handling: the `ActionMap` neutral re-arm, the
     per-tick Settings re-focus, and the first-run prompt. Under Xvfb with no SDL gamepad, the
     plugin tick probably returns early.

   **Fix:** a wording change in the result. Label it `settings_gateway_two_tick_adoption` (or
   state the bypass in the note). Alternatively, drive the opening through
   `ControllerUi.openTab(SETTINGS)` plus the plugin's `openHomeTab` path, so the grace is
   covered too.

## Limits
- I didn't run any test, build or probe, and I didn't open their outputs. The pass counts
  (172 / 45 / 18 + 2) and the export checks come from your report.
- Whether the route and doors match the live cache rests on the route test you ran, not on
  this review.
- No gameplay or hardware (Steam Deck or physical controller) acceptance is claimed.
