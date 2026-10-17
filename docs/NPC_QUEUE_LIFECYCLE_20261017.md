# Native NPC deferred queue identity — 17 October 2026

The native NPC manager now reserves indices for pending spawns, retires only the queued object, cancels pre-spawn removals and clears pending work during a global reset. This repairs a shared boundary behind the previously fixed familiar/grave duplicate-removal callers, and prevents future queued content from inheriting those failures. Tick order stays deferred: a pending addition is not exposed as a live indexed NPC before the NPC stage.

Claude Haiku wrote five native engine regressions using an original fake NPC definition. Coordinator review added region-clear and spawn-lookup cases, then implemented the scoped manager fix. The original five controls passed while seven added cases failed against the original manager. After that fix, an additional independent case exposed a stale normal-retirement spawn lookup; it failed while the other 13 cases passed. The final manager passes all 14.

| Contract | Before | Final behavior |
| --- | --- | --- |
| Duplicate queued removal | size decremented twice | one retirement and one live-count change |
| Add/remove before first stage | cancelled NPC still spawned | pending spawn cancelled |
| Two queued additions after allocator saturation | same free index allocated twice | distinct reserved indices |
| Global clear with pending work | queued spawn could reappear | queues, reservations, old indices and lookup cleared |
| Old object after clear/index reuse | replacement removed by old index | stale identity refused |
| Region clear plus explicit removal | duplicate retirement | shared identity guard |
| Normal removal followed by index reuse | old spawn tile resolved unrelated replacement | mapping retired only if still owned by that index |

A separate overlapping-spawn control verifies that retiring one NPC preserves another NPC's current tile lookup. Identity assertions use `assertSame`/`===`: native `NPC.equals` compares only indices, so ordinary equality would miss the error. Test-only reflection forces allocator saturation and is restored in `finally`; this is an engine API proof, not a claim that a network login or physical route reproduced late uptime.

## Validation

- 38 related engine cases pass: NPC manager 14, character index map 10 and NPC update encoding 14.
- Fresh official native groups pass without skips: Summoning 20, death 19 and Dungeoneering 28. These include supplied-input/native-map fixtures; they are not an earned complete progression campaign.
- All 105 targeted native cases pass. Client 56/server 43 patch reproduction matches 140/89 files; matched jars/stamp rebuild passes.

[Sanitized evidence](evidence/npc-queue-lifecycle-20261017.json) pins code/build identities and exact private reports. Archived reds and final XML/logs are under `.runtime/npc-queue-lifecycle-20261017/`. No owner save, installation or Deck deployment is involved. Physical familiar, dungeon/cutscene lifecycle and long-session acceptance remain open. No FPS or complete-world/grave persistence claim is made.

A separate Haiku source review found no blocker in this scope. Global reset is
a load/teardown boundary; reentrant resets from NPC spawn/despawn callbacks and
callback-failure atomicity are not established here. Region clear continues to
index live region members; cancellation of same-tick pending regional additions
is outside this change. The existing call sites were inspected without claiming
physical Gudrun cutscene acceptance or capacity-exhaustion testing.
