# Dungeon room-coordinate rotation fix — 17 October 2026

Baseline: merged `aa266a3`. Server patch 0032 fixes one line in
`content/skill/dungeoneering/DungeonMap.kt` and adds focused regressions.
[Evidence](evidence/dungeon-room-rotation-20261017.json) records the failing
baseline, fresh selected results and source/patch digests.

`DungeonMap.tile(room, x, y)` computed rotated X first and passed that transformed
value into the Y rotation. For quarter-turns 1 and 3, original X was lost: the
formulas mapped a 16×16 room onto only 16 distinct positions. Half- and zero-turn
rotations were unaffected. Y now uses the original `(x,y)`, as does the existing
zone-copy logic in `DungeonRoom.open`.

The helper serves boss spawn coordinates and `DungeonRoom.findObjects`, which
searches for the invisible key markers used by native key placement. The latter
previously revisited a diagonal instead of scanning the whole room for rotations
1 and 3. This is a shared geometry fix, with no cache changes, new floors or
changes to server-authoritative collision and movement.

Four parameterised geometry cases cover all 256 positions at each orientation,
compare them with independent repeated quarter-turn geometry and require 256
unique results. Before the fix, rotations 1 and 3 failed; rotations 0 and 2 passed.
Afterward all four pass. The cached boss-room test also compares the native
`findObjects` result with an independent base-relative sweep and requires the
existing trapdoor to be found exactly once. The trapdoor still unlocks through
the native death pipeline.

The checked-in `dungeon` group now includes these checks, the real-template
small-c1 floor/seed cases, generator contracts and ordinary entrance/lifecycle
checks:

```bash
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group dungeon
```

All **26 selected cases** pass with zero failures, errors or skips. All 69 patched
server source files match the exported stack. The earlier trapdoor report remains
historical evidence of the old placement; this follow-up supersedes its unresolved
rotation observation.

Limits: the map geometry is covered at every tile/orientation, but live cached
boss/death interaction still uses one deterministic dungeon. Native key pickup,
ordinary boss combat, a full floor, reward/countdown, physical controller use and
save/restart after completion remain open. Changes have not been deployed to Deck.
Owner profiles and cache data are untouched; no proprietary assets are published.
