# Unrecovered grave cold-JVM probe — 17 October 2026

The source-inferred [transient save boundary](WORLD_TRANSIENT_SAVE_AUDIT_20261017.md) is now reproduced in a bounded native experiment. A five-minute grave and its unrecovered item are absent after a cold native world-test boot, while all three kept items, account XP and position survive. This is an open local-world lifecycle gap; it is not a passing grave-persistence contract or an implemented recovery policy.

## Observations

The first native JVM supplies logs, bronze dagger, bronze sword and tinderbox to `grave_probe`, applies native lethal damage at Lumbridge and runs the normal death flow. Three items are kept; the tinderbox is on the ground beside one gravestone. Live grave variables exist and expire at native epoch300. The fixed native clock is0.

It invokes the real `World.shutdown`, including `AutoSave` and its primary-save check, then retains the actual native account file. A second independent JVM boots native game scripts/configuration, loads that same account and runs native setup/index/spawn. This bypasses network account authentication and connection guards. Both use the same private storage root and shutdown exchange paths. The first test JVM PID is2676997; the second is2678948. The game clock remains0, so the original expiry is still300 seconds away.

| State | Before shutdown | Cold JVM |
| --- | ---: | ---: |
| Unrecovered tinderbox on death tile | 1 | 0 |
| Grave NPC on death tile | 1 | 0 |
| Live grave time/tile variables | present | absent |
| Grave map markers | 1 | 0 |
| Grave time/tile in account save | absent | absent |
| Supplied kept items in inventory | 3 | 3 |
| Unrecovered item in inventory | 0 | 0 |

Both phases verify the actual primary save exists and decodes. Reloaded inventory arrays, XP and position equal the retained account. Both selected native diagnostic executions pass their observation/setup assertions with no skips; `observed_gap:true` records the defect separately. Claude Haiku reviewed the source and earlier evidence. Review fixes add inherited shared-disk fingerprints, measured counts and atomic source injection; the fixed clock is simulation evidence, not wall-clock or suspend acceptance. Input cache file hashes remain unchanged, and the injected test source is removed afterward.

## Reproduction and evidence limits

Run `python3 experiments/native-grave-boundary/run.py` after the normal source/cache/JDK setup. The [runner documentation](../experiments/native-grave-boundary/README.md) explains the build lock, private outputs, exact-source cleanup and the WorldTest save-directory cleanup workaround. Source/patch verification passes for all80 modified native files before injection. [Sanitized evidence](evidence/grave-cold-jvm-20261017.json) records both observations and input/tool digests. Private output is `.runtime/grave-boundary/1792255106285865920/summary.json`; logs/XML remain there.

This uses native world startup/shutdown and account storage in two real JVMs, without network server `Main`, a graphical client, physical inputs or owner saves. Supplied items and API death are explicit fixtures. WorldTest's teardown clears runtime entities; that cleanup is not presented as a restart. Distinct JVMs and a fresh native world boot provide the cold boundary. Its teardown also deletes the account-save directory, so the retained save is restored byte-for-byte into that same root before phase2. Other private disk state is retained.

Earlier attempts are preserved privately: v1 failed compilation; v2 completed both phases but report generation failed on a pin lookup; v3 completed with separate phase roots and therefore established only account-file portability. The reviewed v4 uses one shared root and exchange paths. Final v5 additionally measures marker counts and inherited disk hashes, computes counts from observed state, and injects complete source atomically. None of these claims physical acceptance or reproduces the native network-server shutdown receipt.

## Decision required before implementation

Reliable local-world recovery should explicitly address this gap before death-heavy progression acceptance. Recommended priority is a P1 lifecycle follow-up: a routine world stop can remove unrecovered loot. This is not evidence of account-file corruption, and it does not choose a new 2011 death-reclaim mechanic.

A persistence design must retain owner/item/charges/expiry identity, prevent duplicate recovery after partial writes, remove records when items are taken, and survive migration or rollback. A pre-quit notice alone would not preserve items. No policy, writer, migration or new death mechanic is implemented in this change. Network shutdown, crash timing, relogin marker behaviour and a physical recovery session remain separate acceptance tasks.
