# Cooking target lifetime — 2026-10-17

## Finding

Cooking starts the `cooking` soft timer before the queued conversion runs. When the queued step found the fire gone, or the raw input was no longer replaceable, it returned without stopping that timer. The timer then stayed active until something else cleared it. Other code reads `softTimers.contains("cooking")`, including `LumbridgeBeginnerTasks` and `DungeonComplexity`, so a stale marker has visible effects.

Reproduced red before the fix in both cases (`CookingTargetLifetimeTest`, 2 of 2 failing on the timer assertion). The item and XP assertions preceding it passed, so nothing was consumed or granted.

## Fix

`upstream/game-server/game/src/main/kotlin/content/skill/cooking/Cooking.kt`, inside the queued `weakQueue` block only:

- `!GameObjects.contains(obj)` now calls `softTimers.stop("cooking")` before returning.
- `failedToReplace(...)` returning true now calls `softTimers.stop("cooking")` before returning.

Both match the existing completion and early-stop behaviour in `cook`. No balance, chance, XP, ActionQueue, or timer-framework change.

## Not changed

- The leftover-item `inventory.add` failure in the same block uses the same early-return pattern. It was not reproduced and is outside the two-case scope, so it is unchanged.
- Whether a weak queue cancelled by movement or a strong queue leaves the timer set is untested.

## Evidence

- Tests: `upstream/game-server/game/src/test/kotlin/content/skill/cooking/CookingTargetLifetimeTest.kt` (2 cases).
- Red before: 2 tests, 2 failures. Saved privately under `.runtime/earned-lumbridge-20261017/`.
- Green after: 8 tests, 0 failures across `CookingTargetLifetimeTest` (2), `CookingTest` (4), and `ProductionCapacityRecoveryTest` (2).
- Patch: `patches/server/0035-cooking-target-lifetime.patch`. Reverse check passes; `scripts/verify_patches.py server` reports all 75 files match; 0001–0034 unchanged.
- Machine-readable record: `docs/evidence/cooking-target-lifetime-20261017.json`.

## Limits

- Fire removal is an ordinary `GameObjects.remove` fixture, not fire expiry or player cancellation.
- Withdrawal is an explicit inventory fixture, not an ordinary player cancellation.
- No physical acceptance, no deck restamp or deploy, no commit or push.
