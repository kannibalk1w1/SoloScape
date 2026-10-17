# Charged death-drop recovery — 17 October 2026

A native nonPvP death dropped a partially charged chaotic rapier with **zero stored floor charges**, although the weapon had **12,345**. The death-drop call now supplies the existing per-item charge field, matching the native nontradeable Drop path. Native Take can then restore the original stored value. Quantity, ownership, grave lifetime, PvP conversion and deliberate dragonfire-shield discharge are unchanged.

## Native evidence

Claude Haiku added one integration regression with a supplied rapier, native SetCharge, an explicit skull, normal lethal damage and actual death/respawn. Fresh baseline XML runs one case, fails once and skips none: expected floor charges 12,345, actual 0. Before the failing assertion, native respawn/death completion, grave creation, absence from inventory, one floor weapon, quantity one and player ownership pass. A missing test import was corrected before that qualified run; it is not production evidence. Later recovery assertions were not reached in the baseline.

After the single-argument correction, the complete case passes. The player walks back with a supplied full inventory, native Take refuses and retains the same charged floor item, native Drop frees one slot, and native Take restores exactly one weapon with raw charge 12,345. Twenty more ticks preserve the charge and quantity with no floor duplicate. Server patch **0050** contains the correction and regression, now included in the standard death group.

- Death/loot group: **29 cases**, no failures/errors/skips.
- Selected recovery, identical-item, protected-charge, degradation and shield groups: **40 cases**, no failures/errors/skips.
- Five overlap: **64 distinct native cases** in total. Existing dropped dragonfire-shield discharge passes.
- Root tooling: **276 cases**, one existing optional skip.
- Complete source exports: **99 server / 140 client files** match their patch stacks.
- Matched native **50/56** preparation passes. All 2 tested PlayerDeath class files match the packaged server jar byte for byte; the client jar is unchanged.

[Sanitized assertions, suite counts and source hashes](evidence/death-drop-charges-20261017.json). Private native results remain under `.runtime/death-drop-charges-20261017/`, `.runtime/death-drop-review-20261017/` and `.runtime/content-coverage/1792275033353472322/`.

```sh
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group death
```

## Limits

The weapon, charge, skull, filler, clock and lethal damage are explicit fixtures. This is native damage/death and action-handler evidence, not earned combat or a physical controller session. The specific charged recovery has no disk round trip here, and the [unrecovered grave/floor persistence P1](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains open. This change adds no new death penalty or general item/save format. Owner saves, Deck installation and release publishing remain held.
