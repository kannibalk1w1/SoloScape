# Controller prototype design

Status: SDL2 input, right-stick camera, left-stick walking and A world interaction
plus inventory and dialogue controls are built and tested. The user confirmed
camera panning and the movement tile overlay. See
`CONTROLLER_TESTING.md` for controls and validation. Movement/interaction gameplay
UI gameplay and Steam Deck acceptance remain pending.

The plugin owns one reusable state buffer containing axes/triggers and
pressed/held/released button masks. Poll once per input update, clear state on
disconnect/focus loss, release native resources on plugin shutdown, and dispatch
game actions only on the client thread. Keep existing keyboard/mouse listeners.

First experiment is right-stick camera via existing yaw/pitch input integration,
with radial deadzone and frame-time scaling. Avoid changing final render camera
coordinates or scripted camera states. Deadzone, inversion and speed become
named settings only when the implementation uses them.

Left stick projects a short camera-relative tile destination through the normal
walking/pathfinding adapter. The current build uses deadzone 0.18, projection
2–4 tiles and updates 150ms apart. Deduplicate destinations; validate
collision and diagonal movement. Returning to deadzone stops issuing requests;
the already queued path may finish. Immediate movement cancellation needs a
verified existing action, not an invented controller protocol packet.

World mode: A invokes the focused nearby NPC/object's normal default action.
The build uses a 3.5-tile forward cone, a retention bias, bounded native
pathfinding and a target/action overlay. A revalidates the displayed target and
dispatches once per press. Returning to neutral after interaction prevents
walking requests from canceling it. X/B context/back
are incremental additions. Verify action IDs against the actual 634 dispatcher.

Inventory mode: Y opens/focuses the native inventory tab. D-pad moves a yellow
focus through the four-column grid. The renderer records actual visible slot bounds;
there is no guessed fixed screen layout. A dispatches the normal default action,
X opens its normal action list and B backs out. UI modes suppress left-stick walks
and require neutral inputs before returning to world movement.

Dialogue mode takes priority while a known dialogue interface is open. D-pad
selects an exposed response, A invokes its native continue/choice action once per
press, and B uses the existing same-tile Walk action to cancel normal conversations.
Widget identity, item/quantity, permissions and visibility are revalidated just
before dispatch. Numeric/text entry and other grids remain subsequent work.

Deadzone, camera intent and input-state calculations have automated tests. Test
projection/grid calculations when implemented. Hardware tests
must cover Steam Deck, a standard Xbox-style pad if available, hotplug, unplug
while moving and keyboard/mouse coexistence. Avoid per-frame log/allocation
spam. SDL2/JNA was selected; see `CONTROLLER_DEPENDENCIES.md` for the decision.
