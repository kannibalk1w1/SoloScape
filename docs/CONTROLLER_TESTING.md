# Controller build: world, inventory and dialogue controls

The experimental **disabled-by-default** RuneLite plugin now supports right-stick
camera, left-stick walking, A-button world interaction, inventory navigation and
dialogue controls. The server/protocol are unchanged. The user confirmed camera
panning and the movement tile overlay work. This usability build adds precise walking, LT aiming, stable focus, LB/RB target
cycling and gold scene highlights. Gameplay feel remains the next check.

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
   the character should stop before blocked tiles. Gentle tilt walks one tile,
   medium tilt two and full tilt three. Release the stick: new requests
   stop, but the short path already queued can finish. A bright green tile marks
   the actual requested destination, and a light blue outline marks your current
   tile while walking. The destination stays visible until arrival or another
   action overrides it.
5. **Hold LT** and point the left stick at a nearby NPC/object to aim without
   issuing walks. A gold footprint and **A: action target** label mark the selection.
   Tap **LB/RB** to cycle eligible targets in that direction. Release the left
   stick and pan with the right stick: focus should stay on the same entity.
   Press **A** to perform the displayed action once. Holding the same walking
   direction after A pauses movement so it cannot immediately cancel the action;
   release A and neutralize or change the left-stick direction to walk again.
   Try an NPC conversation, a tree and a door. Aim-only mode stops new requests;
   a short walk already queued can still finish. Dialogue widgets take priority.
6. Test ordinary mouse walking/interaction and camera controls. Unplug while
   moving, switch focus while holding A, then reconnect/refocus. Input should stop
   and held world inputs must not resume until the stick and A are released.
7. Press **Y** to open/focus the inventory (top face button on other pads).
   **D-pad** moves the yellow slot outline, including empty slots. Hold a direction
   for repeated navigation. **A** performs the displayed normal action, such as
   Eat or Wear. **X** opens the item's action list; D-pad chooses, A confirms,
   and **B** backs out one level. B or Y exits inventory focus and returns to
   world controls. Neutralize the left stick before walking again.
8. Talk to an NPC. **A** continues a page, or confirms the highlighted response;
   **D-pad** changes the response. **B** closes the conversation through the normal
   same-tile walking action. Held A must not advance several pages. Try a food
   item, equipment, an X action list, an empty slot, a choice dialogue and focus
   loss while A is held. Test fixed/resized layouts and mouse tab changes too.
9. Disable the plugin to return to ordinary client input.

The already-built jar is `upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar`.
Restart is required to load the new code if an older client is still open.

| Setting | Default | Purpose |
| --- | --- | --- |
| Stick deadzone | 18% | Radial deadzone; increase if the stick drifts |
| Camera turn speed | 120°/s | Horizontal speed at full tilt |
| Camera pitch speed | 70°/s | Vertical speed at full tilt |
| Invert vertical camera | Off | Reverse vertical direction |
| Controller diagnostics | Off | Log processed stick values at most once per second |
| Show movement tiles | On | Green walking destination and light blue player tile |

No native code loads until the plugin is enabled. It polls the first available
SDL-mapped controller, retains that device while attached, and scans again after
disconnect. Device name/GUID and connection changes appear in `.runtime/client.log`.
A uses SDL button 0 and dispatches only on its press edge. Targets are within
five tiles from their footprint edges and a forward cone; valid focus remains
stable until you change aim or cycle targets. The client
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
- Camera-relative walking projects one to three tiles ahead from the physical player tile and checks the exact
  revision-634 collision masks, including both side tiles for diagonals. Native
  continued walking requests are limited to one per 150ms, with immediate direction
  changes. Duplicate destinations are suppressed. Existing mouse destinations can override controller destinations.
- Nearby NPC/object actions use `Class325.method2599`, the normal menu dispatcher.
  Action IDs come from the actual 634 builders, not RuneLite's generic enum.
  No click emulation or invented server packets are used.
- Thirty-eight client tests pass without skips: math/state, actual camera bridge,
  projection/collision/focus scoring, lifecycle/action-edge tests, three native
  pathfinder/gate tests, eleven UI navigation/native-widget tests and real SDL
  virtual-controller polling. SDL checks both
  sticks, A edges, hotplug and unplug reset.
- Three patch-stack tests cover fresh application, upgrade/idempotence and
  preserving conflicting local edits.
- Client Shadow jar builds with the plugin, JNA dispatch resources and notices.
- Patch reproduces modified files exactly on the pinned base and is reversible.

The user confirmed camera panning. Movement/interaction feel, Gaming Mode focus
and Deck acceptance still require manual testing. Native tests do not establish
those. The current UI build handles visible inventory slots and exposed dialogue
buttons. Number/text entry, bank/shop grids and item/spell targeting in the world
remain subsequent work. Inventory Use can select an item for another inventory
slot; B cancels selection when leaving inventory focus.

## Reproduce the source change

The checkout remains at upstream base `297bc8a4861755b676855664d32859054779c067`.
SoloScape owns `patches/client/0001-controller-camera.patch` and
`patches/client/0002-controller-world.patch` and
`patches/client/0003-controller-movement-tiles.patch` and
`patches/client/0004-controller-inventory-dialogue.patch` and
`patches/client/0005-controller-world-usability.patch`. Source builds apply the patch stack
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

## Movement tile overlay (2026-10-08)

The overlay uses the collision-checked destination recorded by the native walk
adapter. It projects ground tile polygons through the existing perspective code
and renders under UI widgets. It clears on arrival, a different mouse destination,
A interaction, loss of focus/controller, plugin shutdown and invalid world state.
Neutralizing the stick keeps the destination visible while the queued walk finishes.

The client jar rebuilt and all 20 existing client tests passed without skips.
Patch 0003 reproduces the source exactly as an upgrade or fresh patch stack.
Visual placement, colours and camera tracking still need an in-game check.

## Inventory and dialogue build (2026-10-08)

Patch 0004 records real, clipped native widget bounds while rendering, gated by
plugin enablement. Inventory interface 149 and fixed/resized inventory-tab buttons
are verified against the pinned server interface definitions. Native permission
flags expose the same actions as mouse menus. The dispatcher's actual 634 widget
IDs are 18/1011 for normal operations, 13 for selection, 6 for a selected item on
another widget, and 16 for dialogue continue/choice buttons.

Actions revalidate the current widget identity, item/quantity, option and open
interface before dispatch. Hidden ancestors invalidate cached slots immediately.
Old render records expire after 100ms; a visible inventory with delayed redraw
keeps controller focus and suppresses actions until fresh bounds arrive. X opens
a controller action list backed by these normal actions. It does not guess from
screen coordinates or depend on the disabled inventory-grid plugin's fallback.

Dialogue pages require released face buttons before another action. B uses the
existing same-tile Walk dispatcher: the server's Movement handler closes normal
interfaces and dialogue suspensions. Server delays can still prevent cancellation,
as they do for ordinary walking. No responses are selected automatically.

All 31 client tests pass with zero skips/errors. Patch reproduction matches all
30 patched files as an upgrade and fresh stack. In-game item actions, conversation
controls, focus placement, tab opening and resized layout acceptance remain pending.

## Walking and aiming usability (2026-10-08)

Patch 0005 shortens walking projection, anchors it to the physical player tile,
adds LT aim-only input and LB/RB cycling, and displays the actual selected entity's
footprint and action in the scene. Resting aim stays in world space during camera
panning. Focus identity follows moving NPCs; A revalidates their current position,
option, name, region and reachability. It never substitutes another entity.

All 38 client tests pass without skips, including seven added checks for gentle
walking, footprint scoring, LT, camera panning, bumper edges, interaction recovery
and entity identity. Existing native pathfinder, widget and real SDL tests pass.
The Shadow jar rebuilt successfully. Physical ease of use and scene label placement
still need an in-game check; LT does not cancel a path already queued.
