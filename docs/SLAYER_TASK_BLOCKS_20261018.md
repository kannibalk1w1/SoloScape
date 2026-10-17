# Permanent Slayer blocks, recovery and native saves

18 October 2026. Fixed existing Slayer assignment behaviour in server patch 0052;
client 56 and the global block-list model remain unchanged. This is an M6 native
contract repair, not later-content gameplay or completion of the Slayer campaign.

## Reproduced problems

- Buying a permanent block deducted 100 points and cleared the assignment, but the
  block lived in temporary player variables and disappeared after native save/load.
- Weighted assignment never inspected the five blocked-task slots, so a blocked
  task remained assignable during the same session.
- The existing five cancel buttons had no handler to remove a block.
- Exhausting the novice's eligible choices could fail assignment after the
  confirmation had already reset the existing streak.

Baseline native evidence reproduces banned banshees being selected in three block
slots before fail-fast stopped that run. A separately selected paid-purchase case
reaches native primary save/load and finds the stored block missing. Expanded
recovery cases reproduce failed unblock clicks and streak 9 becoming 0 on a failed
replacement. These are supplied boundary fixtures, not earned playthroughs.

## Change

The existing `blocked_task_0` through `blocked_task_4` keys are now persisted strings.
Assignment eligibility excludes those task categories for that account. The native
cancel buttons clear their corresponding slot without charging or refunding points;
block, unblock and paid skip refresh the existing interface.

An empty eligible set is detected before the random draw. The normal NPC paths
explain that no suitable assignment is available, while preserving the old task,
remaining count, streak, points and assignment count. A successful replacement
retains the existing streak-reset policy. Missing master tables remain configuration
errors; they are not presented as exhausted assignments. Other exceptions remain
visible to normal error handling.

The 100-point block cost, five slots, task weights and XP/combat rules are unchanged.
This does not introduce modern OSRS per-master block lists, reinterpret every
master's reassignment dialogue, or add a new save format. Blocks already lost by
older builds cannot be reconstructed from their saves. No automatic refunds or
owner-save edits are performed.

## Qualified validation

`bash scripts/test-content-coverage.sh --group slayer` passes **53 cases**, with
zero failures, errors or skips: 17 new block/recovery cases, 2 kill-ownership cases,
27 existing task cases and 7 master cases.
[Sanitized suite evidence](evidence/slayer-task-blocks-20261018.json).

The new cases exercise every persisted block slot, account isolation, an actual
validated native block purchase and insufficient-points refusal, all five native
unblock buttons with repeated-click and disk-restore checks, exhausted first-task
and replacement paths, a successful replacement, and the configuration-error boundary.

Save checks use SaveQueue primary acknowledgement, FileStorage and PlayerSave,
then native AccountManager setup/index/spawn of a fresh player. Combat eligibility
and the full XP array must match before the next task is rolled. An unblocked
banshees task must actually become assignable again, so a failed restoration of
combat requirements cannot masquerade as successful block filtering.

During test development, the initial bare `toPlayer` fixture retained a default
combat level. That could mask an eligibility failure. It was replaced with the
full native setup/spawn above. Dialogue fixtures also acknowledge the selected
Yes player-chat step before checking the callback, and exhausted paths require
actual NPC chat and clean dialogue closure. Earlier partial runs are not counted
as the qualified final 53-case result.

Two Claude Haiku source reviews informed the implementation. Final review identified
stale paid-skip UI and missing-table error masking; both were corrected before the
qualified run. The complete source export matches 105 patched/modified server files. Root tooling
also passes 276 tests with one optional skip; the generated-status checks pass.

Physical controller navigation of the rewards screen, an earned points/task journey,
whole-process Slayer progress acceptance and Deck performance remain human/testing
gates. The separate private build report records ordinary native New/Continue
acceptance; that does not turn these supplied Slayer cases into a graphical campaign.
