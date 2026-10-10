# Private Steam Deck test build

This is an owner-to-device test installation, not a redistributable game release. SteamOS stays read-only. The source build remains the public delivery path; proprietary cache, local JDKs, jars, saves, credentials and remote-access details stay out of Git.

## Installed device

The tested device is a Steam Deck (DMI Jupiter, AMD Custom APU 0405, about 14 GiB usable RAM reported), SteamOS 3.8.28, KDE Wayland Desktop with XWayland at 1280×800. Project-local Java 21 and Java 8 run successfully; SDL2 2.32.56 detects the built-in Steam Deck Controller. The game uses its ordinary software renderer in a window. This does not establish OpenGL or Gaming Mode behavior.

The installation lives under `~/SoloScape-test/`. `launch.sh` opens the isolated profile launcher. The Desktop/application shortcut is **SoloScape Test**. New Character creates a fresh private world; the automated probe characters are in separate test folders and do not appear in your normal character list.

**SoloScape Controller** starts enabled with fresh settings. Home Settings provides controller preferences and the explicit first-run setup. Select the Steam Deck preset there if wanted. A saved disabled plugin preference is respected and can be changed in RuneLite Configuration. Ctrl+F11 toggles the RuneLite sidebar; Ctrl+F12 toggles its current/last-opened plugin panel. Direct movement, matched-server features and each adventure screen remain reversible choices; the launcher does not silently enable them. Native game graphics/audio remain under Game Settings.

## Add to Steam

1. In Desktop Mode, open Steam → Games → Add a Non-Steam Game → Browse.
2. Select `/home/deck/SoloScape-test/launch.sh`, or select **SoloScape Test** if Steam lists the application shortcut.
3. Name it SoloScape Test. Use the native Linux launch; leave forced Proton compatibility off.
4. Choose a Gamepad layout in Steam Input. Keep a trackpad available as a mouse for native/unsupported screens.
5. Save & Quit any running world before switching to Gaming Mode. Launch the new shortcut there.

### Blank white launcher in Gaming Mode

The Deck launch script exports `_JAVA_AWT_WM_NONREPARENTING=1` before starting
Java. Gamescope does not reparent X11 windows; without this setting Java AWT can
wait for a window event that never arrives and leave the launcher blank. The
launcher backend and game inherit the setting. This launch fix still needs
physical Gaming Mode acceptance on the Deck.

For an already installed snapshot with the older launch script, add this line
to `~/SoloScape-test/launch.sh` immediately before its existing `exec` line:

```bash
export _JAVA_AWT_WM_NONREPARENTING=1
```

Keep Steam's Target as `/home/deck/SoloScape-test/launch.sh`, Start In as
`/home/deck/SoloScape-test`, and Launch Options empty. The underscores in the
variable name are required. The installed launcher has this correction already.

Fully exit SoloScape and launch it again. Keep forced Proton compatibility off.
The setting does not require a rebuild or a change to your characters/worlds.
Java's window-manager behavior is documented in the
[upstream compositor discussion](https://github.com/Smithay/smithay/issues/389).

Valve documents adding installed applications through Steam’s Add a Non-Steam Game flow in its [Desktop FAQ](https://help.steampowered.com/en/faqs/view/671A-4453-E8D2-323C/). Adding the Steam shortcut and changing modes are owner acceptance steps. The automation did not edit Steam's shortcut database, restart Steam, change controller layouts, switch sessions or suspend the device. Please record whether the launcher and game receive the expected gamepad, whether the window fills appropriately, and whether touchpad/controller takeover behaves correctly.

## Reproduce a private deployment

On the development host, stop source preparation/builds and use the matched verified build with the compatible cache already installed. The normal [cache guide](CACHE_SETUP.md) explains the upstream-maintainer source and recorded checksum; this exporter does not download cache assets.

```bash
python3 scripts/deck_export.py
```

The printed private folder contains an allowlisted source snapshot, real pin-reachable Git metadata, matched jars/stamp, read-only cache inputs, project-local JDKs and `deck-manifest.json`. Saves, exchange state, credentials, logs, local config, stashes and dangling Git objects are excluded. Partial exports end in `.partial` and are never announced as complete. Record the manifest's SHA-256 on the host if comparing transfer provenance; its hashes check corruption, not an authenticated release signature.

Transfer the folder with SSH/rsync to a **new** empty build folder under `~/SoloScape-test/builds/`. Supply connection details interactively or through your own SSH configuration; never put them into project files or Git. An example target is `deck@your-deck`, not an address stored by the project. Avoid `--delete` against player data and never update a running snapshot in place.

On the Deck, inside that new snapshot:

```bash
python3 scripts/deck_runtime.py --configure
./scripts/doctor.sh
./scripts/deck-launch.sh
```

`--configure` writes only absolute local JDK paths when there is no existing config; existing files and symlink escapes are refused. Listed payload files, links, source pins and jar/patch hashes verify. Git's mutable index is excluded from manifest hashing so `git status` remains usable. Extra files are not an authenticity guarantee. No root password, system Java install or SteamOS unlock is required.

For SSH-driven display tests, obtain the live session's `DISPLAY` and `XAUTHORITY` from `systemctl --user show-environment`, and pass those explicitly. Do not hard-code an old authorization filename. Normal Desktop/Steam shortcut launches inherit their own display environment.

## Worlds and updates

Each snapshot retains its own `.runtime/profiles`; `launch.sh` points to one tested snapshot. Preserve that folder when updating. This sprint does not silently migrate worlds between builds. Save & Quit, make a verified manual backup, retain the earlier snapshot, then use the documented stopped-world import/restore workflow before changing which build your launcher uses. Do not replace a snapshot with outstanding session records or surviving owned JVMs. Recover those through its original launcher first.

Use Recover Session after an abnormal launcher death. Exact ownership/guard checks precede pidfd termination; recovered snapshots leave clean shutdown unconfirmed. The real Deck probe covered both native JVMs. See [launcher recovery](ALPHA_LAUNCHER.md), [Deck evidence](DECK_VALIDATION.md) and [physical checklist](STEAM_DECK_TEST_CHECKLIST.md).

## Automated tests and their limits

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
source config/local.env
export SERVER_JAVA CLIENT_JAVA
python3 scripts/smoke-launcher.py --desktop
./scripts/smoke-profile.sh --desktop --adventure
python3 scripts/smoke-recovery.py --client
```

Keep the Deck awake and hands off during these visible-window tests. Desktop UI input is synthetic: launcher adapter updates and AWT events through native canvas listeners. Robot pointer warps on this KDE Wayland session caused unintended test-character movement; those failed runs were retained and are not accepted evidence. The corrected probe checks exact save/tile state and unexpected mouse clicks. Default probes still use an owned private Xvfb and Robot mouse path.

Java Robot capture of the Wayland desktop can be black even when the game renders correctly. The inspected game-window evidence uses KDE Spectacle after checking the active window was the game. Keep raw screenshots private and inspect them before publishing; notifications or overlays can cover a window. Rendering callbacks and whole-session process/sensor samples are observations, not a sustained Gaming Mode/battery/GPU budget.

## Name entry and keyboard ownership

The updated Deck launcher prefers **Steam / physical keyboard**. New Character requests Steam's keyboard for the first field. Enter advances to the account field and then finishes entry. A on a focused field, or tapping it, opens typing again; Steam + X can reopen the system keyboard. Launcher SDL actions pause during this entry, including B, so the background form cannot process the keyboard's controller presses. Finish with Enter or tap another form control to leave entry.

The visible choice **SoloScape controller keyboard** enables the local grid instead: D-pad selects keys, A types, X deletes, Y advances and B leaves it. Its mapped arrow/confirm/delete/space keys are consumed, so physical typing with those keys requires switching back to the Steam/physical mode. Close Steam's keyboard before using the local fallback. Manually opening Steam's keyboard while the local fallback is selected is not supported exclusive ownership; select Steam mode first.

For USB/Bluetooth keyboard navigation across the launcher, select **Desktop keyboard navigation (disables launcher controller)**. This chooses Swing navigation instead of competing SDL navigation. It does not change the game controller setting. The launcher fix has automated coverage; physical Deck Desktop/Gaming Mode acceptance remains required. In-game text entry now has its own exclusive ownership setting: Home → Settings → Basics → Text keyboard. Automatic prefers Steam on Deck; Steam / physical or the local grid can be chosen explicitly. Recognized amount/name/string/bank-search prompts take ownership automatically. Unbound right-stick click, or Settings → Finish → Open text keyboard, starts manual chat/other entry. Reopen/Done/Cancel appear in a top-left touch panel; require neutral before resuming controls. See [scope and native behavior](IN_GAME_TEXT_INPUT.md). Classic controller UI, beside Text keyboard, toggles the new stone/brown/gold styling back to the old palette.
