# First controller build: detection + right-stick camera

The first controller feature is built. It is an experimental **disabled-by-default**
RuneLite plugin, not yet the full controller scheme. The server/protocol are
unchanged. Left-stick movement, A interaction and inventory focus are next steps.

## Try this build

1. Quit the running client cleanly, then relaunch from the workspace root:

   ```bash
   ./scripts/dev-run.sh --no-build
   ```

2. Open the RuneLite plugin settings, search **SoloScape Controller**, and enable
   it. Open its settings using the usual plugin configuration button.
3. Connect an SDL-mapped gamepad, log in, and click the game canvas so it owns
   focus. Move the **right stick** to rotate/pitch the camera.
4. Test keyboard/mouse camera controls as well, then unplug the controller while
   holding the right stick. Camera input should stop. Reconnect and try again.
5. Disable the plugin to return to ordinary client input.

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
No actions are bound to controller buttons yet; their edge state is available for
later features.

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
- Nine tests pass: six input/state/math tests, two tests against the actual game
  camera bridge, and one real SDL virtual-controller integration test (not skipped).
  The latter checks hotplug, both right-stick axes, button edges and unplug reset.
- Client Shadow jar builds with the plugin, JNA dispatch resources and notices.
- Patch reproduces modified files exactly on the pinned base and is reversible.

Physical gamepad/Deck feel, focus behaviour in Gaming Mode and visual camera
limits still require manual testing. Native test results do not establish those.

## Reproduce the source change

The checkout remains at upstream base `297bc8a4861755b676855664d32859054779c067`.
SoloScape owns `patches/client/0001-controller-camera.patch`. Source builds apply
it automatically before compiling. To apply separately:

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
