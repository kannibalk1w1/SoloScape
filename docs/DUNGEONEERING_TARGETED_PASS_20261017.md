# Targeted solo Dungeoneering pass — 17 October 2026

Scope: one normal-player solo small complexity-1 floor-1 lifecycle through native handlers, plus one logout boundary. No floors beyond 1, no combat, no admin entry, no production changes. Baseline e44af90 with server patches 0001–0024 applied; new incremental patch 0025.

## Proven (`SoloDungeonLifecycleTest`, 2 tests, passing)

- **Entry:** Climb-down on `daemonheim_dungeon_entrance` without a party opens `dialogue_multi2`; Yes makes the player party leader; a second Climb-down generates a Small c1 floor-1 dungeon (non-null, `playerCount` 1) and teleports to `dungeon.startTile()`.
- **Starting supplies:** ring of kinship worn and removed from inventory; `allocateGear` supplies air runes (86–165) and a rapier.
- **Bind:** `Option3` on the starting rapier moves it to `dungeoneering_bound`.
- **Leave:** `DungeoneeringParty.leave` clears `in_dungeoneering`, teleports to 3460,3721,1 and keeps the bound item.
- **Save:** the TOML written after leaving has tile 3460,3721,1 and `dungeoneering_bound` containing `<rapier>_bound`.
- **Logout inside the dungeon:** `Despawn.player` (the native `playerDespawn` leave), then `saveQueue.save` snapshot, then `Players.remove`, in the same order as `AccountManager.logout`. The saved tile is the castle, not an instance tile, and the bound item persists.

## Fixtures (all explicit in the test class doc)

- Ring of kinship added to inventory (the tutor purchase is not exercised).
- The player spawns beside the entrance; the walk is not exercised.
- The entrance click invokes the registered `Climb-down:daemonheim_dungeon_entrance` handler directly in an `Unconfined` coroutine. The packet `InteractObject` path does not reach it in `WorldTest` (see gap).
- `storage.disabled=false` for the logout test only, so `saveQueue.save` takes a snapshot.
- Saves are read from the TOML file, not a second live login.
- No quest progress, teleport, kill, spawn, or admin `start_dungeon`.

## Not proven

- Combat and the Icy Bones boss kill; keys, locks and door traversal inside the dungeon.
- Trapdoor `End-dungeon` completion, reward XP, tokens, prestige and `dungeon_reward_given`.
- Walking the real route to the entrance; a second live login from the save; multi-member parties; floors beyond 1.

## First remaining gap

Packet dispatch does not reach the entrance handler in `WorldTest`. After `objectOption` and 12 ticks the player mode is `EmptyMode` and no dialogue opens. Invoking the same registered handler directly opens `dialogue_multi2`. This is an unresolved harness dispatch gap; it does not establish a player-facing defect. The earlier staircase probe was not evidence: no handler is registered for `daemonheim_staircase_down`. Next action: trace `ObjectOptionHandler.validate` and `PlayerOnObjectInteract` scheduling under `WorldTest`, or label it harness-only and move to a boss fixture.

## Commands and results

- Baseline `ItemBindingTest`: 8 passed.
- Final lifecycle test: 2 passed, 0 skipped.
- Final selected packages (`content.skill.dungeoneering.*`, `content.area.wilderness.daemonheim.*`): 39 passed, 0 failed, 0 skipped; XML written 14:17:09.
- `python3 scripts/verify_patches.py server`: all 64 files match the stack.
- Patch 0025 applies to the untouched baseline and reproduces the test byte-for-byte.

Commands and fixtures are in `docs/evidence/targeted-dungeoneering-20261017.json`.

## Files

- `patches/server/0025-targeted-solo-dungeoneering.patch` (new): adds `game/src/test/kotlin/content/skill/dungeoneering/SoloDungeonLifecycleTest.kt`.
- `docs/DUNGEONEERING_TARGETED_PASS_20261017.md` and `docs/evidence/targeted-dungeoneering-20261017.json` (new).
- No production source changed. Temporary probe tests were removed. `docs/current-status.json`, `CURRENT_STATUS`, `ROADMAP` and historical reports are untouched.

## Review isolation

The save-writing lifecycle class requires `SOLOSCAPE_TEST_ROOT` so ordinary test runs cannot write into default player storage. The packet-entry boundary and full floor completion remain unproven.

Coordinator rerun with both targeted Summoning classes: 43 tests, zero failures/errors/skips. The full patch stack reproduces 64 modified/patched source files.

Reproduce from `upstream/game-server` with JDK 21 and a non-empty isolated `SOLOSCAPE_TEST_ROOT`:

```sh
./gradlew :game:test --tests 'content.skill.dungeoneering.*' --tests 'content.area.wilderness.daemonheim.*' --tests content.skill.summoning.SoloSpiritWolfLifecycleTest --tests content.skill.summoning.SummoningLevelGateTest
```
