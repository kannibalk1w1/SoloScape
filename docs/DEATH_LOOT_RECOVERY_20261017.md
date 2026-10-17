# Death loot recovery — 2026-10-17

## Scope

One native contract: a lethal death at a valid Lumbridge tile, respawn, recovery of the death drops through the normal floor-item Take and native Drop, then a native file save and fresh-player restore. This is a test-only change. No production code was edited.

## Result

`DeathLootRecoveryTest` has one case and it passes. The test:

- kills the player with `damage(101)` at `Tile(3235, 3220)`, the same API `GravestonesTest` uses, and checks the player respawns at `Tile(3221, 3219)`;
- derives the lost item from the real definitions: the cheapest supplied item by cache cost, which is `tinderbox`. Logs, bronze dagger and bronze sword are kept;
- fills the inventory with `raw_shrimps` (non-stackable, as `ProductionCapacityRecoveryTest` shows), and asserts a full inventory;
- walks to `Tile(3234, 3220)` and asserts arrival at that adjacent non-grave tile, then attempts Take. It is refused with the inventory-space message, and the ground item is unchanged (same object, same amount);
- walks back to `Tile(3234, 3220)`, asserts arrival again, and performs a native Drop of one filler item, freeing one slot;
- retries Take, which succeeds once. Further ticks do not duplicate the item on the ground or in the inventory;
- saves the post-recovery player with `SaveQueue(FileStorage(dir)).direct().join()` into an isolated temp directory owned by the test, then loads it with `PlayerSave.load`, despawns and removes the original, rebuilds with `save.toPlayer()`, and runs `AccountManager` setup, index and spawn. It asserts the restored tile, the XP array, every inventory array, exactly one recovered item, the kept originals, and the creation marker. The directory is deleted in `finally`.

## Correction

An earlier version of this document and its evidence said no test-visible helper applies a `PlayerSave` to a fresh `Player`, and so left the save-restore case out. That was wrong. `FullAdventureJourneyTest.verifyFreshPlayerRestore` (lines 272–298) already does this with the same APIs, and the save-restore step now follows that pattern.

## Two runs, kept separate

- **Earlier, in-memory only:** the death, full-inventory refusal, native Drop and retry steps, before the save-restore extension. No file save and no fresh player.
- **Current, with save-restore:** the same case with the file save and fresh-player restore. This is the only run that covers the restore.

## Finding during development

The refused Take's ordinary approach stepped the player onto the grave tile `(3235, 3220)`. A native Drop is refused there, which is the intended grave rule (see `GravestonesTest`, "Can't drop items onto a grave"). The test walks back off the grave before the Drop. No production rule was changed.

## Limits

- Death uses the damage API, not a real combat encounter.
- The supplied inventory is an explicit fixture, not earned progression.
- Walks use the Walk instruction helper. No teleport is used.
- The restore runs in-process against a temp save directory. It is not a login through a live session, an owner save, or a server process.

## Evidence

- Current run, new class plus `GravestonesTest`: 10 tests, 0 failures, 0 skipped (`DeathLootRecoveryTest` 1, `GravestonesTest` 9). Log: `.runtime/earned-lumbridge-20261017/death-loot-save-combined-20261017.log`.
- Earlier in-memory run: the same 10 tests, 0 failures, 0 skipped. Logs and XML are under `death-loot-recovery-*`, unchanged.
- Patch: `patches/server/0036-death-loot-recovery.patch` (new test file only, overwritten for this extension). Reverse check passes with the absolute patch path. `scripts/verify_patches.py server` reports all 76 files matching. Patches 0001–0034 are unchanged.
- Machine-readable record: `docs/evidence/death-loot-recovery-20261017.json`.

## Coordinator verification

The checked-in runner independently passes `--group death` (10 cases) and `--group capacity` (9 cases, including the cooking lifetime regression). Fresh XML is archived under `.runtime/content-coverage/1792251993265579538/` and `1792252017915872536/`; the machine-readable evidence records both patch-identified summaries. All 76 native files match the exported stack. This tests already-recovered inventory persistence; unrecovered grave/floor loot across a server restart is a separate boundary.

## Not done

- No `FullAdventureJourneyTest` run; it was not needed.
- No physical acceptance.
- No owner saves, profiles, Deck, or server sessions.
- No commit, stage, push, or branch switch.
