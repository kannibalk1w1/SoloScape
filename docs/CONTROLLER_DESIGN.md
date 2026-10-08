# Controller prototype design

Status: the input buffer, SDL2 provider and right-stick camera prototype are built
and tested. See `CONTROLLER_TESTING.md` for enablement and current validation.
Physical controller/Steam Deck validation remains pending. The movement, world
interaction and inventory sections below describe subsequent work.

The plugin owns one reusable state buffer containing axes/triggers and
pressed/held/released button masks. Poll once per input update, clear state on
disconnect/focus loss, release native resources on plugin shutdown, and dispatch
game actions only on the client thread. Keep existing keyboard/mouse listeners.

First experiment is right-stick camera via existing yaw/pitch input integration,
with radial deadzone and frame-time scaling. Avoid changing final render camera
coordinates or scripted camera states. Deadzone, inversion and speed become
named settings only when the implementation uses them.

Left stick projects a short camera-relative tile destination through the normal
walking/pathfinding adapter. Start experiments near deadzone 0.18, projection
2–5 tiles and updates 100–200ms apart. Deduplicate destinations; validate
collision and diagonal movement. Returning to deadzone stops issuing requests;
the already queued path may finish. Immediate movement cancellation needs a
verified existing action, not an invented controller protocol packet.

World mode: A invokes the focused nearby NPC/object's normal default action.
Start with a small distance/cone, exclude unreachable/invalid targets, retain
stable focus and show the target/action via existing overlays. X/B context/back
are incremental additions. Verify action IDs against the actual 634 dispatcher.

Inventory mode: reuse existing slot bounds and overlays for a visible focus.
D-pad moves focus in the normal inventory grid; A dispatches its default action;
X opens existing context actions if practical; B returns to world mode. Mouse
remains usable. Existing drag-grid code is a rendering reference, not evidence
of complete widget/action APIs.

Deadzone, camera intent and input-state calculations have automated tests. Test
projection/grid calculations when implemented. Hardware tests
must cover Steam Deck, a standard Xbox-style pad if available, hotplug, unplug
while moving and keyboard/mouse coexistence. Avoid per-frame log/allocation
spam. SDL2/JNA was selected; see `CONTROLLER_DEPENDENCIES.md` for the decision.
