# Identical items kept on death — 17 October 2026

Normal native death protected only **one** of four identical nonstackable swords instead of three. With two identical swords in inventory and one equipped, two swords dropped although all three should have been protected. The combined selection list now retains every physical copy before applying the existing value ordering and protection rules.

`ItemsKeptOnDeath.getAllOrdered` previously used set union to combine inventory and equipment. Item equality compares ID and stored value, so separate identical copies collapsed. Concatenating the slot arrays preserves their multiplicity. Keep counts, skull/prayer rules, stack-unit splitting, charge handling and item values are unchanged. The same helper also supplies the native items-kept screen; no graphical screen acceptance is claimed here.

## Evidence

Claude Haiku wrote two focused native tests. Both use ordinary player damage and finish the death queue at the configured respawn tile with `dead` cleared. Before the fix, the four-sword case conserves all four but fails with expected three kept, actual one. The inventory/equipment case conserves all three but fails with expected zero floor swords, actual two. Later equipment/inventory assertions in that second baseline were not reached. Coordinator review independently reproduced the first post-death failure on unchanged production source. An initial test-precondition mistake involving empty slots and a runner method-name mismatch are excluded from the qualified results.

After the narrow fix, both complete cases pass: three protected plus one dropped; and three returned to inventory with no floor/equipment copy. Server patch **0049** contains the correction and both regressions; the standard death group now includes them.

- Death/loot group: **28 cases**, no failures/errors/skips.
- Selected identical-item, protected-charge, degradation and dragonfire-shield suites: **39 cases**, no failures/errors/skips.
- Four cases overlap those runs: **63 distinct native cases** in total.
- Root tooling: **276 cases**, one existing optional skip.
- Complete source exports: **98 server / 140 client files** match their patch stacks.
- Matched native **49/56** preparation passes; all 4 compiled items-kept helper/screen class files match the packaged server jar byte for byte. Client jar bytes remain unchanged.

[Sanitized assertions, suite counts and source hashes](evidence/identical-kept-items-20261017.json). Fresh private XML is under `.runtime/identical-kept-items-20261017/`, `.runtime/identical-kept-review-20261017/` and `.runtime/content-coverage/1792274721757250630/`.

```sh
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group death
```

## Remaining acceptance

Swords, equipment, clock and lethal damage are explicit fixtures, not earned progression. A disposable physical playtest should confirm ordinary duplicate-item protection and floor recovery. These checks do not persist unrecovered loot across restart; the [grave pause/persistence P1](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains open. No owner save, installed Deck build or public release was changed. The current separately validated private build remains identified by [the current status ledger](CURRENT_STATUS.md).
