# Second sprint: follow-up on review findings

Scope: the fixes for the findings in `CLAUDE_SECOND_SPRINT_REVIEW.md`. This was a read-only
check: no builds, game, cache, edits or commits, and no gameplay acceptance.

## Dispositions

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Default slots acted on the first Eat/Drink item | **Fixed** | `food()`/`drink()` are removed. `quickBinding` returns `null` for an empty or `"default"` slot (`SoloScapeControllerPlugin`). `decode` now requires `item >= 0` for group 149. |
| 2 | Dose fallback took the first slot | **Fixed** | The pending flow picks the lowest `priority(w)` (`QuickRadialControls:52`), and `priority` returns the dose `(n)` for Drink (`QuickBinding:46-51`). The family match is still limited to the assigned potion's name family. Ties go to the first slot (strict `<`). |
| 3 | Partial food breaks an Eat binding | **Accepted, fails closed** | Eat still requires the exact item ID (`QuickBinding:34`), so "2/3 cake" reports "Unavailable". The documentation is still to be written. |
| 4 | Amount cursor not synced | **Fixed** | When 905 opens, `amountIndex` is mapped from `state.amount` (1/5/10, and >10 → All) (`UiControls:105-108`). Amounts that are none of these (for example 3 or 7) start at index 0. That's harmless, because the prompt shows the real amount. |
| 5 | Action 30 always marked server approach | **Fixed** | `action == 30 && selectedSpell()`, where `selectedSpell()` checks that `Class149.anInt2046` is in group 192, 193 or 430 (`ControllerWorld.target`). Item-on-NPC now uses the normal 5-tile reachable path. |
| 6 | Spell match ignored action type | **Fixed** | Version 2 bindings store `type` and `operation`. `match` requires `a.type == type`, and also `a.operation == operation` for every action except Toggle. `decode` rejects other types and operations outside 0–10. |
| — | Pending timeout ordering | **Confirmed** | `now >= deadline` is checked before the snapshot, match and invoke (`QuickRadialControls:45`). |
| — | Widened scoring radius | **Confirmed** | `areaScore(..., radius)` is passed `10` for server-approach targets in the filter, the first sort and the cycle sort (`ControllerWorld:94,95,117`). The old 9-argument overload still defaults to 5 for everything else. |

## Remaining limits (non-blocking)
- **Old settings are lost.** Bindings saved in the old format (no `"2:"` prefix) decode to
  empty slots, so users must assign them again. Mention this in the release notes.
- **Prayer toggles ignore the operation index.** Toggle bindings match by type and an
  Activate/Deactivate label, on purpose, since the label flips. The widget ID and name are
  still checked.
- **The amount cursor can start at index 0 for one frame.** If 916 hasn't been recorded in the
  first frame that 905 opens, `amountIndex` starts at 0. It isn't re-synced later, because the
  sync runs only when the dialogue ID changes. This is cosmetic.
- **Not confirmed here:** varbit 8095 availability in the cache, whether the production
  interface ops are unlocked, the client-opened modal close behaviour, and in-game behaviour.

## Verdict
**No remaining blockers.** All six findings are fixed or deliberately accepted as fail-closed.
