# Controller build: camera, movement and world interaction

The experimental **disabled-by-default** RuneLite plugin now supports right-stick
camera, left-stick walking and A-button world interaction. The server/protocol are
unchanged. The user has confirmed physical right-stick panning works; movement
and interaction still need their gameplay check. Inventory focus is next.

## Try this build

1. Quit the running client cleanly, then relaunch from the workspace root:

   ```bash
   ./scripts/dev-run.sh --no-build
   ```

2. Open the RuneLite plugin settings, search **SoloScape Controller**, and enable
   it. Open its settings using the usual plugin configuration button.
3. Connect an SDL-mapped gamepad, log in, and click the game canvas so it owns
   focus. Move the **right stick** to rotate/pitch the camera.
4. Release both sticks and A once after login/reconnect/focus regain. Move the
   **left stick** to walk relative to the camera. Try a wall and a diagonal corner;
   the character should stop before blocked tiles. Release the stick: new requests
   stop, but the short path already queued can finish.
5. Aim the left stick toward a nearby NPC/object, then release it. The overlay
   shows **A: action target**. Press **A** (Xbox / Deck; bottom face button on other
   pads) to perform that displayed action once. Release A and neutralize the left
   stick before walking again, so movement does not immediately cancel the action.
   Try an NPC conversation, a tree and a door. Right-stick rotation also changes
   targeting direction. A currently handles world actions, not dialogue choices.
6. Test ordinary mouse walking/interaction and camera controls. Unplug while
   moving, switch focus while holding A, then reconnect/refocus. Input should stop
   and held world inputs must not resume until the stick and A are released.
7. Disable the plugin to return to ordinary client input.

The already-built jar is `upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar`.
Restart is required to load the new code if an older client is still open.

| Setting | Default | Purpose |
| --- | --- | --- |
| Stick deadzone | 18% | Radial deadzone; increase if the stick drifts |
| Camera turn speed | 120°/s | Horizontal speed at full tilt |
| Camera pitch speed | 70°/s | Vertical speed at full tilt |
| Invert vertical camera | Off | Reverse vertical direction |
| Controller diagnostics | Off | Log processed stick values at most once per second |

No native code loads until the plugin is enabled. It polls the first available
SDL-mapped controller, retains that device while attached, and scans again after
disconnect. Device name/GUID and connection changes appear in `.runtime/client.log`.
A uses SDL button 0 and dispatches only on its press edge. Targets are within
3.5 tiles and a forward cone; a small retention bias stabilizes focus. The client
checks native pathfinding (maximum eight path steps) and revalidates the displayed
target immediately before dispatch. Selected spells/items, open context menus
and scripted camera modes block world actions.

SDL2 **2.0.22+** must be installed on Linux (`libSDL2-2.0.so.0`). This machine's
SDL **2.32.74** successfully runs the native tests. If SDL is missing or fails,
the plugin logs a warning and stops its own input; keyboard/mouse remain usable.
Resolve the native-library/device issue and toggle the plugin off/on to retry.

For Steam Deck, select a Steam Input layout that exposes a gamepad. A layout
mapping the right stick to mouse/keyboard can cause duplicate input; use a plain
gamepad layout for native testing. The trackpads can remain mouse fallbacks.
Built-in Deck control access and mappings still need physical hardware validation.

## Implemented and verified

- Shared mutable axes/triggers/button-edge buffer; no new state object per poll.
- SDL native polling, connect/disconnect detection and handle cleanup on the
  client thread. UI plugin enable/disable is marshalled through `ClientThread`.
- Radial deadzone with continuous scaling and bounded diagonal magnitude.
- Additive right-stick intent into the existing normal camera update, followed
  by its existing wrap/pitch clamp. Mouse/keyboard velocities remain independent.
- Canvas focus/player presence checks and a 100ms stale-input watchdog. Per-frame
  camera contribution caps elapsed time at 50ms to avoid jumps after a hitch.
- Login/scripted/free-camera modes do not receive controller camera updates.
- Camera-relative walking projects two to four tiles ahead and checks the exact
  revision-634 collision masks, including both side tiles for diagonals. Native
  walking requests are limited to one per 150ms and duplicate destinations are
  suppressed. Existing mouse destinations can override controller destinations.
- Nearby NPC/object actions use `Class325.method2599`, the normal menu dispatcher.
  Action IDs come from the actual 634 builders, not RuneLite's generic enum.
  No click emulation or invented server packets are used.
- Twenty client tests pass without skips: math/state, actual camera bridge,
  projection/collision/focus scoring, lifecycle/action-edge tests, three native
  pathfinder/gate tests and real SDL virtual-controller polling. SDL checks both
  sticks, A edges, hotplug and unplug reset.
- Three patch-stack tests cover fresh application, upgrade/idempotence and
  preserving conflicting local edits.
- Client Shadow jar builds with the plugin, JNA dispatch resources and notices.
- Patch reproduces modified files exactly on the pinned base and is reversible.

The user confirmed camera panning. Movement/interaction feel, Gaming Mode focus
and Deck acceptance still require manual testing. Native tests do not establish
those. Inventory navigation, dialogue confirmation and context/back bindings are
not implemented in this build.

## Reproduce the source change

The checkout remains at upstream base `297bc8a4861755b676855664d32859054779c067`.
SoloScape owns `patches/client/0001-controller-camera.patch` and
`patches/client/0002-controller-world.patch`. Source builds apply the patch stack
automatically before compiling. To apply separately:

```bash
./scripts/apply-client-patches.sh
```

Application is idempotent and refuses conflicting edits rather than resetting
the checkout. The initial upstream checkout now intentionally has controller
changes; all server source remains unchanged. `--no-build` uses the existing jar.

To run tests, with `SERVER_JAVA` and `CLIENT_JAVA` configured:

```bash
source config/local.env
export JAVA_HOME="$(dirname "$(dirname "$SERVER_JAVA")")"
export GRADLE_USER_HOME="$PWD/.gradle"
cd upstream/runelite-client
bash gradlew --no-daemon \
  "-Dorg.gradle.java.installations.paths=$JAVA_HOME,$(dirname "$(dirname "$CLIENT_JAVA")")" \
  :client:test :client:shadowJar -PcontrollerNativeTest=true
```

Native virtual-device tests require SDL2 and no connected physical gamepads.
Without the opt-in property, the native integration test is skipped; pure tests run.
