# Native grave degradation and expiry — 17 October 2026

Two reproduced defects in the native grave timer are corrected. A collapsed grave could return to its broken appearance on the next poll; an expired grave never cancelled its timer and remained in the world. The handler now selects the phase by remaining lifetime, retains collapse in the final minute and returns `Timer.CANCEL` when expired. The existing stop handler owns NPC removal and owner UI cleanup.

## Evidence

The first regression supplies a shortened lifetime of 119 seconds, then calls the native degradation handler with fixture clock samples 0/36/72/108 seconds. These match the existing poll interval of 60 game ticks (36 seconds). Broken stays broken, then changes to collapse. Before the fix, the final call changes it back to broken: expected `gravestone_memorial_plaque_collapse`, actual `gravestone_memorial_plaque_broken`. After the fix it stays collapsed on the same live NPC. These are explicit clock samples/handler calls, not a naturally elapsed rendered session.

The second regression spawns an ordinary five-minute plaque, advances the fixture clock past its lifetime and runs 121 native world ticks. It does not call the stop handler directly. Before the fix the expired NPC remains. After the fix the native scheduler observes cancellation, removes the NPC and clears `gravestone_npc`, `gravestone_time` and `gravestone_tile`. Those cleanup assertions were not reached in the baseline after the NPC assertion failed. Expiry remains subject to the existing poll interval; no exact-to-the-second expiry or suspend policy is claimed.

Both fresh baseline methods run once, fail once and skip none. Both fixed cases pass, and the standard native death/loot group passes **31 cases** with no failures/errors/skips. This retains existing repeated-grave identity, owner-marker cleanup, loot pickup and charge tests. Root tooling passes **276 cases**, with one existing optional skip. Complete source exports match **100 server /140 client files**. Server patch 0051 retains both regressions in the standard group.

Matched native **51/56** preparation passes; all 8 compiled Gravestones class files match the packaged server jar byte for byte. Client bytes remain unchanged.

[Sanitized assertions, counts and hashes](evidence/gravestone-timer-20261017.json). Private results: `.runtime/gravestone-phase-review-20261017/` and `.runtime/content-coverage/1792275779068042799/`.

```sh
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group death
```

This changes live NPC degradation/expiry, not loot ownership/lifetime rules or the save layout. No owner save, installed Deck build or public release is changed. The [pause-while-closed grave persistence P1](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains open. A disposable physical session should confirm final-minute appearance, eventual expiry and marker cleanup alongside loot recovery.
