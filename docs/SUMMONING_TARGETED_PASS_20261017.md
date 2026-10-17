# Targeted Summoning pass: one spirit wolf lifecycle, 17 October 2026

Baseline: `e44af90`, with server patches through 0024 applied. Patch: `patches/server/0026-targeted-solo-summoning.patch` (new test file only; no production change). Machine-readable results: `docs/evidence/targeted-summoning-20261017.json`.

## What is covered

- **Infuse** a spirit wolf pouch at the obelisk from supplied materials. The recipe is read at test time from the same cache parameters `SummoningCrafting` uses, so the test does not hard-code it and this doc does not name it (cache content stays out of Git). Asserted: every recipe ingredient is consumed, one pouch is made, and the pouch's `infuse_experience` is awarded.
- **Summon** from the pouch at real beginner level. Asserted: the pouch is consumed, summoning points drop by the pouch's `summon_points`, the special pool is 60, summon xp is awarded, the lifetime is 6 minutes, and exactly one owner-matching spirit wolf is live.
- **Dismiss** through the native `familiar_details` "Dismiss Familiar" → "Yes." confirmation. Asserted: no follower, no owner-matching NPC left in the world, pouch not returned, persisted lifetime cleared.
- **Recovery boundary (logout then relog from disk).** Summon, save through the native `SaveQueue`/`FileStorage` into the isolated test saves folder, read the TOML back with `PlayerSave.load`, log out, then load into a fresh `Player` via `PlayerSave.toPlayer()` and log it in through `AccountManager`. Asserted: exactly one owner-matching spirit wolf after relog, no pouch returned or duplicated, summoning points and xp unchanged, and the saved lifetime restored rather than reset.

**Persisted vs reconstructed.** The active familiar NPC is not persisted. What persists is the summoning level and xp, the pouch inventory, and the familiar_details timer variables. On login `playerSpawn` reconstructs the follower from those variables. The test checks the reconstructed follower, and it does not check any NPC state beyond the owner count.

## Fixtures (all explicit)

- Owner: new account at `Tile(2523, 3056)`, real Summoning level 1 with empty xp, full points pool of 1.
- Materials: the recipe ingredients are added straight into the inventory.
- Obelisk: `GameObjects.find(Tile(2521, 3055), "obelisk")`, then `Infuse-pouch` and the `Infuse` interface option.
- The disk save is taken explicitly, because test storage is disabled.

Nothing is granted. There is no quest progress, teleport, or NPC kill/spawn beyond the native summon and infuse calls.

## Commands and results

```
flock .runtime/build.lock ./gradlew --offline :game:test \
  --tests content.skill.summoning.SoloSpiritWolfLifecycleTest \
  --tests content.skill.summoning.SummoningLevelGateTest
```

Fresh XML from the final run (`2026-10-17T12:57:47Z`), `BUILD SUCCESSFUL`:

| Class | Test | Result |
| --- | --- | --- |
| SoloSpiritWolfLifecycleTest | Infuse, summon and dismiss | passed |
| SoloSpiritWolfLifecycleTest | Saved to disk, restored once after relog | passed |
| SummoningLevelGateTest | Real level still gates the pouch | passed (regression) |
| SummoningLevelGateTest | Drained points don't block summoning | passed (regression) |

`scripts/verify_patches.py server` reports all 63 patched or modified source files match the exported stack, including the new test file. `git apply -R --check` on 0026 passes.

Earlier iterations were test-side only: a compile error (imports), a relog assertion that ran before the queued NPC removal (fixed with one tick), and an in-memory relog that was replaced by the disk round trip. No product behaviour changed.

## Fixture limits

- One spirit wolf pouch. This is not a 154-recipe run or a familiar-wide pass.
- Materials are supplied by fixture. They are not earned through Pikkupstix, shops, drops, or travel.
- The relog is a same-process reload into a fresh `Player`, not a server restart and not a real profile.
- Not exercised: the howl scroll and special move, Wolf Whistle, expiry while online, owner death, and bank-full recovery.
- No production code changed, so no regression beyond the two test classes above was run.

## First remaining gap

Earned acquisition. The native sources for the charm, shard and tertiary are unverified, so the pass proves the supplied-material lifecycle only. The smallest next action is to trace one real acquisition route for the spirit wolf charm and tertiary, then write a separate earned-route test that does not use `inventory.add` for those items.
