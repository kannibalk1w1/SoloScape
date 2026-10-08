# Controller build: world, inventory and dialogue controls

The experimental **disabled-by-default** RuneLite plugin now supports right-stick
camera, left-stick walking, A-button world interaction, inventory navigation and
dialogue controls, world action menus/loot and an optional direct movement toggle. Direct mode uses a
small matching server protocol extension; destination mode remains the default. The user confirmed camera
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
| Show movement tiles | On | Green walking destination/next direct step and light blue player tile |
| Direct movement | Off | Hold a direction to move; release to stop on the next server movement update |

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
  Destination mode uses the ordinary dispatcher; opt-in direct movement uses
  the explicit SoloScape directional protocol documented below.
- Fifty-eight client tests pass without skips: math/state, actual camera bridge,
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
`patches/client/0005-controller-world-usability.patch` and
`patches/client/0006-controller-direct-movement.patch` and
`patches/client/0007-controller-world-actions-loot.patch`. Matching server changes
are `patches/server/0001-controller-direct-movement.patch` and
`patches/server/0002-controller-world-cancel.patch`. Source builds apply both stacks
automatically before compiling. To apply separately:

```bash
./scripts/apply-client-patches.sh
```

Application is idempotent and refuses conflicting edits rather than resetting
the checkout. The initial upstream checkout now intentionally has controller
changes. Direct mode also modifies the server with a tracked patch.
`--no-build` uses the existing jars.

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

## Try optional direct movement (2026-10-08)

Both client and server jars have been rebuilt. Quit the existing game/launcher
cleanly and relaunch `./scripts/dev-run.sh --no-build` so both processes load the
new code. Enable **SoloScape Controller → Direct movement**. Leave it unchecked
for the previous destination controls; switching does not require another restart.
Release the stick and A after switching or returning focus.

- Hold the left stick: movement continues in eight camera-relative directions.
  Gentle tilt walks; full tilt requests running when energy/equipment permit.
- Release it: directional input stops at the next server movement update. A step
  already transmitted/rendering can finish; the game still uses 600ms ticks.
- Hold LT to aim without walking; LB/RB cycles gold targets and A acts on one.
- Walk into walls and diagonal corners; movement must stay collision checked.
  Turn while held and test region edges, energy depletion, inventory/dialogue,
  camera panning, focus loss and unplugging. No path should continue after stop.
- While holding the stick, click a mouse destination or interaction. That action
  takes over; direct input resumes only after the stick returns to neutral.
- Uncheck **Direct movement** and verify the previous one-to-three-tile destination
  walking returns, including its short queued-path finish after release.

Tests pass with zero failures/errors/skips: 47 client tests, 246 network tests
and 56 selected engine movement/decoder tests. New checks cover real encrypted
opcode/payload encoding, directional sectors, mouse takeover, toggle/release/A/LT
behavior, native decoder validation, server collision gates, per-tick steps, run
preferences/energy, timeout and late-stop handling. Both Shadow jars contain the
new classes. Client/server patches reproduce 36/9 files exactly; fresh, upgrade,
reverse and repeated application pass. Physical gameplay feel remains unverified.

Apply the server patch separately with `./scripts/apply-server-patches.sh`.
To repeat server checks using the configured JDK 21:

```bash
source config/local.env
export JAVA_HOME="$(dirname "$(dirname "$SERVER_JAVA")")"
export GRADLE_USER_HOME="$PWD/.gradle"
cd upstream/game-server
bash gradlew --no-daemon :network:test :engine:test \
  --tests '*Movement*' --tests '*DecoderTest' :game:shadowJar
```

## World action menus, loot and cancel (2026-10-08)

Both jars are rebuilt. Quit the existing game/launcher cleanly and restart with
`./scripts/dev-run.sh --no-build` to load the new client and server.

- Aim at an NPC/object and press **X**. The list uses its current native options.
  **D-pad** selects, **A** confirms once and **B** backs out. Movement input is
  suppressed while the list is open. Existing destination paths may finish;
  direct movement stops issuing intent. Inventory/dialogue still take priority.
- Aim at dropped loot: the gold footprint and A prompt use its default **Take**
  action. **LB/RB** cycles nearby targets, including every visible pile entry
  beyond the three rendered models. Ties are sorted consistently. Stack quantity
  is shown in the target name; stale/despawned items invalidate menus/actions.
- Outside an action list, **B** sends position-free server cancellation. It stops
  a normal approach, movement or interaction without walking toward an old tile.
  In a list the first B only backs out; press again to cancel the world action.
  Normal forced/busy actions retain the same delay gate as ordinary walking.
- Test X on a multi-option NPC, a tree/door, moving NPCs, disappearing loot and
  several items on one tile. Confirm button holds never repeat actions, mouse
  actions still work, and direct/destination modes resume only on fresh walking
  intent after cancellation. Test Y/dialogue takeover while a world list is open.

Native action IDs come from the actual builders: NPC 25/20/44/46/60, object
3/4/9/59/1007 and ground item 21/10/47/22/5. Ground items come from the client's
visible pile table, so targets reflect items the client knows about. X includes
secondary native actions; A re-enumerates and revalidates before dispatch.
Server opcode 86 has no payload, clears ordinary movement/interaction and weak
queued actions, then runs pending walk cleanup once, matching ordinary walking.
This cleanup may unmorph the player or start a content exit; it does not advance a
dialogue. The forced-action delay gate leaves the callback untouched.

All 58 client tests, 247 network tests and 59 selected engine tests pass without
failures/errors/skips. Native tests cover all pile entries, deterministic cycling,
NPC secondary options and movement, despawn rejection and cancellation packet order.
Server cancel tests verify no positional movement and preserve forced/nonmovement
states. UI closing is mocked in these server unit tests; gameplay acceptance is
still required. Both jars rebuild and patch reproduction matches all 37/14 files.
Three patch-helper tests and four launcher tests also pass.

Add `--tests '*CancelWorldAction*'` to the server test command above to include
its handler tests. See `PROJECT_HANDOFF.md` for a portable status summary and
`ROADMAP.md` for the proposed task list.


## Claude review fixes (2026-10-08)

Client patch 0008 and server patch 0003 address H1, M2 and M3 from
`CLAUDE_REVIEW.md`. The review itself records the earlier build and remains unchanged.

- Cycle a pile of at least 12 distinct items in both directions and confirm wrap.
- Put a dense pile behind a wall with a reachable target nearby: the reachable
  target should remain selectable. Distinct geometry checks are still capped at
  eight per scan; this is not unlimited targeting across a dense scene.
- Test Ring of stone/Easter ring followed by world B: the pending unmorph cleanup
  must run. Also check a content exit that uses a walk trigger.
- Check banker/shopkeeper targeting across counters, border crossings in both
  movement modes, and dialogue B while a step is interpolating. These are review
  hypotheses requiring gameplay checks, not fixes implemented in this batch.

Automated results: 61 client test cases (58 distinct methods), zero failures/errors,
with the SDL virtual-device case deliberately skipped; it was not revalidated in
this batch. The new native pathfinder tests exercise 12-item bidirectional cycling,
blocked-pile starvation and cache expiry between scans. All 247 network and 61
selected engine cases pass without skips. Cancellation tests verify cleanup once,
morph-style movement-delay release, preservation of cleanup-created exit steps,
and forced-action callback preservation. UI closing remains mocked.

Both Shadow jars rebuild. Fresh/upgrade/reverse/idempotent patch reproduction
matches 37 client and 14 server files. All seven root tooling tests pass. Physical
controller and save-roundtrip acceptance still require restarting both processes.


## Home-tab radial proof of concept (2026-10-08)

Enable SoloScape Controller; **Tab radial menu** is on by default and can be turned
back off. On Xbox/Deck layouts use **View/Select** (the left small menu button).
SDL's mapped Back button is used; it is not the face-button B.

1. Tap View/Select to open the wheel. If the stick was already held to walk,
   release it once before aiming on the wheel.
2. Tilt the left stick to highlight one of 16 tab slots. Alternatively, press
   D-pad left/up or LB for previous, right/down or RB for next.
3. Press A to open the highlighted native tab. Inventory also enters existing
   D-pad inventory focus. Other tab contents retain mouse controls for now.
4. B or View/Select closes the wheel without choosing. Hidden/unavailable tabs
   are dimmed; failed opens retain the wheel with a message.
5. After closing, release held controls and neutral the stick before moving again.

Check fixed/resized layouts, all available slots, hidden/tutorial-locked tabs,
opening while walking, A/B held during opening, dialogue priority, focus loss,
disconnect and disable/re-enable. Test that wheel selection does not move the
player or invoke a world interaction. Direct input stops on opening; a queued
legacy destination can finish. Mouse tab switching remains available.

Patch 0009 includes seven wheel state tests and three native UI tests, including
actual ordinary tab operation packet dispatch. The full client run has 71 cases
(68 distinct methods), zero failures/errors and one deliberately skipped SDL
virtual-device case. The client Shadow jar rebuilds. Patch reproduction matches
41 client files on upgrade/fresh/reverse/idempotent runs. Renderer previews at
765×503 and 1280×800 were inspected; physical/in-game acceptance remains pending.


## Overnight reliability batch

**SoloScape server features** is now an explicit opt-in, off by default. Enable it
only when using the patched SoloScape server; enable **Direct movement** as well
for held directional movement. With server features off, direct mode falls back
to destination walking and world B uses an ordinary same-tile Walk at the native
path head. It does not send custom opcodes 85/86. This is an interim compatibility
setting; automatic server capability negotiation is still proposed.

An adapter RuntimeException resets input/focus and logs its real cause at most
once per five seconds while SDL polling continues. Provider init/poll failures
still disable the plugin with provider-specific advice. Diagnostics now report
controller tick average/maximum microseconds once per second; Deck timings remain
unmeasured. Idle snapshots skip inventory item descriptions and regex is precompiled.

The launcher records patch/base and jar hashes after a successful source build.
`--no-build` rejects missing/invalid stamps, changed patches and changed jars with
an instruction to rebuild. Logs rotate to `server.previous.log` and
`client.previous.log` before the next session instead of losing the previous logs.
The current session is not rotated or interrupted by development builds.

Test the explicit server-features toggle, direct opt-out stop, normal B fallback,
focus rearming after a transient error and clean rebuild/restart. Do not enable
custom packets against an unpatched server. Automated tests cover custom packet
suppression, one direct stop and the native fallback packet/path-head coordinates.


## Bank and shop focus (patch 0011)

Open a bank, deposit box or shop normally. Controller focus activates automatically after held buttons/stick are released. D-pad navigates the visible grid; up/down at its edge scrolls the native container. LB/RB switches Bank/Stock, Inventory, and Controls / tabs panes. A uses the first withdrawal/deposit action, Buy or Sell; X lists all native quantities/actions, including Info/Value. B backs out of that list, then closes the interface. Bank tabs, deposit-carried/worn, note/swap toggles and other actionable buttons are in Controls / tabs. Server messages provide transaction feedback.

Test full/empty banks and shops, mixed stack quantities, note mode, buying with insufficient funds, selling with full stock, tab switches, grid scrolling, mouse scroll takeover and fixed/resized layouts. This build has automated native-widget and state-machine checks, but gameplay is not yet accepted. Deposit/Withdraw-X and search still require native keyboard entry until the next controller-entry batch; bank PIN remains native.


## Controller amount/name/search entry (patch 0012)

The native amount, name, string and bank-search prompts now show a controller keyboard. D-pad chooses keys; A inserts; X deletes one character; Y or Done submits; B uses native Escape. Numeric entry rejects values above the signed 32-bit limit. Text entry uses printable ASCII and bounded lengths; physical keyboard entry remains available. Native scripts 1564 and 112 handle edits/submission/cancellation. Bank search uses the native armed key callback and search pipeline.

Validate Withdraw/Deposit-X (including Cancel and a second quantity request), search with several matches/no matches/clearing, mouse/keyboard edits while the controller keyboard is open, hidden/replaced prompts, and held A during opening. B on an amount prompt cancels the native entry; the server retains its ordinary cancellation behavior. No quantity is fabricated on cancellation. Bank PIN remains native.

Bank/shop B recovers after one second if a busy server ignores a close. Scrolling resolves focus after an actual widget render, and item replacement requires release before A can act. The controller pauses camera input while UI modes consume input.


## Equipment, prayer and spell handoff (patch 0013)

On the View/Select radial, choose Equipment, Prayer or Spellbook. D-pad navigates rendered actionable widgets, A performs the native action, X lists alternatives and B returns to world control. Ordinary mouse tab switching does not enter controller focus. Equipment bonuses (667) and its side inventory (670) also support panes.

Selecting a targeted spell stops controller walking and hands off to eligible nearby NPC/object/ground targets; stick aims, LB/RB cycles, A dispatches, B cancels. Inventory-target spells open/focus inventory through a native tab operation that preserves selection. Source identity/item/quantity/permissions and a re-selection token are revalidated. A source stack change requires cancellation and re-selection. Ineligible or invalid inventory targeting never falls back to eating/dropping. Immediate casts still use their native operations. Server/native messages handle unmet requirements.

Test removing/equipping with a full bag, empty worn slots, opening/closing bonuses, toggling prayers and quick-prayer selection/confirmation, modern/ancient/lunar books, immediate/home teleport, a targeted NPC cast with enough and insufficient runes, an inventory spell, replacing the selected item, despawns/region changes, and B cancellation. Player/PvP/self and arbitrary ground-tile targets are not added; nearby targets retain conservative approach reachability rather than a new ranged-combat policy.

**Native interface navigation** in SoloScape Controller defaults on. Turn it off to restore mouse/keyboard handling for the added interfaces; inventory/dialogue controls and tab switching remain. New renderer previews in `images/controller-bank-preview.png` and `images/controller-keyboard-preview.png` use plain backgrounds, not gameplay screenshots.
