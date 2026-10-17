# Dungeoneering native entrance follow-up — 17 October 2026

The earlier [lifecycle pass](DUNGEONEERING_TARGETED_PASS_20261017.md) called the entrance handler directly because its ordinary instruction did not open dialogue. This follow-up resolves that gap without changing production code, collision or cache data.

## Cause and change

The eastern entrance at (3455,3723,0) has a 1×2 footprint, rotation 2 and blockFlag 13. Its legal approach is from the west, at (3454,3723,0). The previous fixture stood east, at (3456,3723,0), on a blocked side. Native ReachStrategy rejects that side and PathFinder returns an alternative route with no waypoints; normal interaction therefore cannot start there. This was a fixture-position error, not evidence of a broken packet dispatcher.

The mirrored western entrance at (3444,3723,0) admits an approach from the east, at (3445,3723,0). Both now run the original entry/supplies/bind/leave/save assertions through the ordinary `InteractObject` helper. The logout case also uses ordinary entry. A negative case keeps the original blocked-side position and checks no dialogue, party or dungeon is created and the ring remains in inventory.

The direct coroutine, registry lookup and fabricated interaction are removed. Directional access rules remain intact. This is a useful test-design lesson for other objects: inspect the actual shape, rotation, footprint, access mask and reachable side before replacing native interaction with a direct handler call.

## Scope and reproduction

Only the incremental test patch 0028, report and current evidence index change. Ring supply and initial placement remain declared fixtures. Full floor combat, doors, keys, boss, rewards, walking the route to Daemonheim, live client/controller input and whole-process save/restart remain unproven. Historical reports are retained.

With JDK 21, a local authorized cache and a non-empty isolated `SOLOSCAPE_TEST_ROOT`, run from `upstream/game-server`:

```sh
./gradlew :game:test --tests 'content.skill.dungeoneering.*' --tests 'content.area.wilderness.daemonheim.*'
```

## Validation

All 41 selected Dungeoneering/Daemonheim cases passed with zero failures/errors/skips, including four cases in the updated lifecycle class. [Evidence](evidence/dungeon-native-entry-20261017.json) records suite totals and source/patch digests. All 64 modified/patched server source files match the exported stack.
