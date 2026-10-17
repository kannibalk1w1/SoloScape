# Corner movement and precision walking — 17 October 2026

Status: first implementation, automated validation; physical acceptance required. Client patch 0054 and server patch 0024. No Deck deployment in this pass while the owner is playing.

The previous direct running mode resolved a direction once and repeated it for both steps. With a diagonal stick against a corner, the first step could slide legally along a wall but the second repeated that slide even where a turn had become possible.

The server now queues one local step, then re-evaluates the same held direction from the resulting tile before the second running step. Native collision checks still validate both steps. A blocked diagonal cannot cut through a corner; legal horizontal/vertical fallback can produce an L-shaped turn. This retains the existing three-byte directional-intent packet and maximum two steps per tick. It does not add waypoints, client position authority or a future movement queue.

Movement events run between steps. If an event replaces the mode, its new route is preserved and direct running stops. Delay, run energy/hysteresis, forced walking, heartbeat expiry, input ownership and stop semantics remain in the existing movement path. The optional server property/environment key `world.players.controllerCornerRunning=false` restores repeated-direction running. It defaults to true.

**Hold RT for precision walking** at any stick tilt while using verified-server direct movement. Release RT to restore the configured run threshold. This is continuous walking at one tile per tick, not a single-step-per-press action. Home → Settings → Basics → RT precision walking disables the modifier; RuneLite plugin settings expose the same toggle. LT retains aim ownership, and face-button actions still stop movement. Destination-walking fallback is unchanged.

## Validation and limits

- Direct-mode regressions cover all four L-turn quadrants using synthetic collision flags passed through the real RSMod step validator, a blocked second step, continuous wall sliding, run energy, stale/released input, delay, replacement-mode route preservation and disabling corner running. Other isolated cases mock the validator; this does not establish every native map edge.
- The client suite covers RT full-tilt walking, release restoring run, disabling the modifier, LT priority and A interaction. The full native client test selection and server movement package were run; results are recorded in [evidence](evidence/controller-corners-20261017.json).
- Production collision/pathfinder, combat range/line of sight and NPC pursuit algorithms are unchanged. This is a movement foundation, not acceptance of every safe spot or a new stationary-attack mode. A native Attack can still approach when its range/line-of-sight rules require it.
- Existing movement outlines indicate intent; no authoritative two-step preview has been added.

## Physical acceptance

On a disposable Deck profile, test walking/running around a fence, wall end and doorway in each direction; hold RT at full tilt, release it, then stop beside a corner. Check a large NPC footprint and ranged/magic safe spots: acquire target, fire, cancel, move one tile, re-attack and verify no unexpected approach. Check run depletion and an instance/region boundary. Menu close, focus loss and controller reconnect must still require neutral input.

## Next options

1. Add a true server-validated two-step preview only if the current marker causes confusion.
2. Audit native Attack auto-approach before designing an explicit “attack from here” modifier. Never silently weaken line of sight or NPC collision.
3. Consider an optional tile cursor/corner waypoint for exact click-style positioning. Keep the current D-pad tab bar and existing aim/target controls available; decide bindings after physical feedback.

Native 2011 tile/combat rules remain authoritative. [M6 audit and progression queue](SOLO_CONTENT_AUDIT.md).
