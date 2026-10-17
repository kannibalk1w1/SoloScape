# Production capacity and retry — 17 October 2026

Baseline: merged `60e6cb5`. Server patch 0030 adds two native contract tests in
`content.soloscape.ProductionCapacityRecoveryTest`; it changes no gameplay code.
[Machine-readable evidence](evidence/production-capacity-20261017.json) records
fresh selected XML counts and source/patch SHA-256 values.

The earned Lumbridge slice already establishes the connected happy path and
walking cancellation. These tests isolate two inventory-capacity boundaries with
supplied items and created NPC placement on the test's empty tile. They do not
claim another earned journey, actual-map travel or controller acceptance.

- **Fishing:** a net and 27 supplied raw shrimp fill all slots. The normal `Net`
  instruction reports a full inventory, leaves items and Fishing XP unchanged,
  and stops the fishing timer. Native `Drop` frees one slot. Selecting `Net`
  again catches exactly one shrimp for 10 XP and stops again when full. Further
  ticks leave both inventory and XP unchanged.
- **Bread dough:** flour, water and 26 supplied logs fill all slots. The native
  item-on-item action and bread creation choice attempt a recipe with three
  outputs (`bread_dough`, `bowl`, `empty_pot`) from two input slots. Rejection
  preserves every input and Cooking XP and stops the production timer. After
  dropping one log through its native action, retry consumes exactly the flour
  and water, returns all three outputs, preserves the other 25 logs and stops.

The first fishing case passed immediately. The initial dough fixture omitted the
native recipe selection and consequently remained in a dialogue. Adding the
same creation choice used by the existing Cooking test reached the transaction
boundary. No production defect was inferred from that fixture error.

Reproduce with a configured user-supplied compatible cache and JDK 21:

```bash
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group capacity
```

All **7 cases** across the two new tests and existing Fishing/Cooking suites
pass with zero failures, errors or skips. The runner deletes selected historical
XML, uses isolated mutable storage, archives fresh results and records stack
digests. All 66 patched server files match the exported stack. No owner profile,
Deck installation or proprietary asset was changed or published.

Remaining physical check: fill a disposable character's inventory, observe the
feedback and retry after freeing a slot using only the controller. This report
does not accept death recovery, whole-process restart, interruption during a
transaction, or save durability across a system failure.
