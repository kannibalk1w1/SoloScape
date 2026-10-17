# Slayer kill credit and saved task isolation — 17 October 2026

Two native contracts strengthen the existing Slayer foundation before any later-content experiment. Production rules are unchanged.

- Two players hold supplied birds tasks with two kills remaining. Only one attacks a chicken through ordinary native combat. After the verified death, that player has one remaining and exactly the native Slayer XP award; the passive player keeps two remaining and zero XP. Further ticks do not duplicate credit. Both accounts save through SaveQueue/FileStorage and spawn as fresh players with independent task counts, exact XP and inventories.
- An attacker with a wolves task kills a chicken while a passive nearby player has birds. Neither receives Slayer credit or XP. The test explicitly verifies the chicken died before checking the negative result.

Claude Haiku authored the cases. Coordinator review shortened fixture accounts to the native 12-character limit, added bounded-combat death assertions and narrowed the ownership claim. The independent checked-in runner `--group slayer` passes **36 cases**: the new ownership class (2), existing SlayerTaskTest (27, including dynamic cases) and SlayerMasterTest (7). Fresh XML and patch identities are archived under `.runtime/content-coverage/1792253047531443489/`; [sanitized evidence](evidence/slayer-kill-ownership-20261017.json).

The new class is exported in `0037-slayer-kill-ownership.patch` and gated on the isolated test root, which the standard runner sets. A skipped class is not a pass. Earlier worker logs remain private under `.runtime/slayer-kill-ownership-20261017/`; the independent run covers the final reviewed source.

Assignments, master, high combat stats/equipment, inventory markers, deterministic RNG and one NPC spawn are explicit fixtures. This is not earned Slayer progression, a full server restart, physical controller acceptance or a Superior Slayer feature. One attacker plus a passive bystander does not establish contested/shared-damage/final-hit policy. Loot and Slayer-point completion rules are outside this contract. No owner saves or Deck installation were touched.
