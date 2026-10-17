# Protected item charge preservation — 17 October 2026

Native death handling reset a kept partially charged weapon to **1 charge**, even though the original weapon was selected for protection with **12,345 charges**. The return path now preserves the item's stored value while adding its ordinary quantity. It does not change keep counts, value ordering, death penalties or stack merging.

## Reproduction and correction

Claude Haiku wrote two focused native regressions. A supplied chaotic rapier has per-item charges, no shared charge variable, quantity 1 and raw value 12,345. The native keep selector returns that same item before death. Real player damage, death processing and respawn then return exactly one protected weapon. Both separate baseline runs fail at the literal assertion: expected 12,345, actual 1. Coordinator review adds explicit respawn/completion and quantity checks and independently reproduces the same failure on unchanged production code.

`PlayerDeath.dropItems` previously recreated every kept item with `inventory.add(item.id, item.amount)`. For an instance-charged item, `amount` is the item count 1; it is not the stored charge value. The quantity-aware add now runs in one transaction and restores the original Item when raw value differs from quantity. Ordinary stacks keep using the existing add/merge behavior. Replacing the quantity with the charge value would have created extra items and is deliberately not the implementation.

The first fixed case returns one weapon with all 12,345 charges and no floor copy. The mixed case also keeps exactly 2 coins, drops 998 and preserves the total 1,000. Those coin assertions were not reached in the red run because the earlier charge assertion failed; they pass after the correction.

## Validation

- Both new native cases pass.
- The selected death/loot group passes 26 cases with no failures/errors/skips.
- The selected charge/degradation/shield groups pass 37 cases with no failures/errors/skips. The two new cases appear in both runs; together these are 61 distinct native cases.
- Existing tests retain the deliberate discharge of a dropped dragonfire shield and native equipment degradation behaviour.
- Root tooling passes 276 cases with one existing optional skip.
- Source exports match 96 server / 140 client files. Matched native 48/56 preparation passes.
- Both tested `PlayerDeath` class files match the actual packaged server jar byte for byte. The server jar changes to `78cb090da0bc7fb3165c01423f9a0b137187ec9e85ebfe8b6443789578343c5c`; client bytes remain unchanged.

Server patch 0048 contains the narrow production correction and the new test. The standard death group now retains the regression. [Sanitized evidence, red assertions, suite counts and hashes](evidence/kept-item-charges-20261017.json).

```sh
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group death
```

Fresh selected death XML/patch identities are under `.runtime/content-coverage/1792273485635315456/`; red and charge-suite evidence stays under `.runtime/kept-item-charges-20261017/`. No binary or proprietary cache is committed.

## Limits

Equipment, charge value, currency, clock and lethal damage are explicit test fixtures. These are native damage/death contracts, not earned combat, Dungeoneering rewards or a physical controller campaign. This correction covers **kept-item state**; it does not qualify every unprotected charged-item drop/transfer or add a disk round trip for these cases. No new save format is introduced. [Unrecovered grave/floor persistence while closed](GRAVE_PAUSE_PERSISTENCE_PLAN.md) remains open. Owner saves, Deck deployment and release publishing remain held.
