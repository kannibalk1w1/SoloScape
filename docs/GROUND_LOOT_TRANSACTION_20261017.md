# Rejected ground pickup preserves loot — 17 October 2026

Ground pickup removed the floor entry before its inventory transaction. Slot exhaustion after a partial nonstackable addition, or a stack overflow, reverted the inventory while permanently deleting the floor pile. The early full-inventory check does not cover these cases.

Server patch0040 attempts the complete inventory addition first, then removes the floor entry only while that transaction is still valid. If the floor reference is stale, the transaction fails and rolls back its tentative addition. There is no suspension between these operations. Existing capacity rules, whole-pile refusal and charges handling remain in the native transaction.

## Evidence

Two independently run native tests fail before the fix at the floor-preservation assertion: a two-coin pile with an inventory stack of `Int.MAX_VALUE - 1`, and two nonstackable swords with one free slot. After the fix, each refuses without losing loot, then succeeds after supplied capacity is freed. A direct stale-reference case verifies rollback with an otherwise valid empty inventory.

All five native Take cases and the existing death-loot recovery case pass. Four existing Telekinetic Grab cases pass. The expanded official death group passes15 cases with no failures or skips, including the nine existing gravestone cases. All83 modified/patched server sources match the exported stack at coordinator verification. [Sanitized evidence](evidence/ground-loot-transaction-20261017.json) includes red messages, fresh counts and patch hashes.

Private evidence is `.runtime/ground-loot-transaction-20261017/`; official group summary is `.runtime/content-coverage/1792258273844932335/summary.json`. Fixtures supply inventory/piles and free capacity directly; this is a native pickup transaction proof, not an earned loot journey or hardware acceptance. Grave restart persistence remains a separate open P1 issue under the owner's pause-while-closed policy.
