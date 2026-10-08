# Controller prototype design

Status: SDL2 input, right-stick camera, left-stick walking and A world interaction
plus inventory and dialogue controls are built and tested. The user confirmed
camera panning, the movement tile overlay and improved walking/aiming feel. See
`CONTROLLER_TESTING.md` for controls and validation. Direct movement, UI gameplay and Steam Deck acceptance remain pending.

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
1–3 tiles from the physical player tile and updates 150ms apart. Gentle tilt
requests one tile; medium tilt two; full tilt three. Direction changes respond
immediately. Holding LT aims without issuing new walks. Deduplicate destinations; validate
collision and diagonal movement. Returning to deadzone stops issuing requests;
the already queued path may finish. This is the default destination mode; its queued path can finish after release.
The separate opt-in direct mode uses the dedicated protocol below.

World mode: A invokes the focused nearby NPC/object's normal default action.
The build uses a five-tile forward cone measured from footprint edges, bounded
native pathfinding and a gold target footprint/action label. Valid focus persists
until deliberate aim changes, loss of reachability or LB/RB cycling. At rest,
right-stick camera panning leaves world-space aim unchanged. A revalidates the displayed target and
dispatches once per press. The held walking direction pauses after a successful interaction, preventing
movement requests from immediately cancelling it. Neutralizing or changing the
left-stick direction resumes walking after A is released. Moving NPCs retain
focus by identity; their current position is revalidated before dispatch. X/B context/back
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

## Optional direct movement

`Direct movement` defaults off in SoloScape Controller settings. It sends custom
opcode 85 with three bytes: signed dx, signed dy (-1..1), run request (0/1).
These are directions, never authoritative coordinates. The client quantizes
camera-relative input into eight sectors with seven degrees of angular hysteresis,
sends changes immediately and unchanged input every 200ms. Gentle tilt walks;
processed magnitude >= 0.9 requests running, subject to energy/equipment limits.
The ordinary run-toggle preference is preserved.

The server's DirectMovementMode queues only one/two local steps for the current
600ms tick and uses existing movement collision, delays, viewport checks, visual
updates and energy events. It does not find a route around an obstacle. Remaining
steps are cleared after each tick. Stop clears only this mode, so a delayed stop
cannot cancel a newer mouse destination or interaction. Movement events can replace
the mode; their new steps are preserved. Packet freshness expires after 750ms,
checked on each game tick; stale queued updates cannot restart movement.

LT aiming, A, UI modes, focus loss, disconnect, shutdown and toggling modes stop
directional input. Native menu dispatch stops direct input and blocks the held
stick until neutral, letting mouse actions take over. Switching settings requires
neutral input before movement resumes. Direct mode's green tile shows the next
collision-checked local step intent, rather than a server-confirmed destination.
Tile timing and eight-way movement remain; no client prediction or continuous
sub-tile server positioning is introduced.
