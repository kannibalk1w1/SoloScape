# Grave lifecycle identity — 17 October 2026

An older grave could clear the newer grave's timer/location variables, including when both occupied the same tile. Cleanup looked up the owner's latest tile instead of identifying the grave being stopped. Two additional defects were reproduced: marker removal stopped at the first occupied slot even when unrelated, and native Demolish queued the grave removal twice, making the NPC counter−1 with zero live NPCs.

Server patch0041 binds the latest grave's UI state to that NPC object at runtime. Only that grave clears the latest timer/location; each stopped grave removes its own tile marker. Marker removal searches until the first matching tile/type. Demolish lets its timer-stop handler own NPC removal once. The new NPC reference is temporary server state, not a persisted save value or network ID.

## Evidence

Claude Haiku wrote independent distinct-tile and same-tile reproductions. Coordinator review added independent native controls for an earlier unrelated marker and the Demolish NPC count. All four failed before their fixes. The timer assertions now use the native integer seconds type consistently; an initial green attempt exposed a boxed numeric assertion mismatch and was corrected without changing the expected behaviour.

All14 targeted native grave/death-recovery tests pass. The expanded official death group passes19 cases, including the five Take regressions, with no failures or skips. All87 modified/patched server sources match the exported stack. [Sanitized evidence](evidence/grave-lifecycle-identity-20261017.json) records independent red messages, fresh suite counts and patch hashes. Private artifacts: `.runtime/repeated-grave-20261017/`; official summary: `.runtime/content-coverage/1792258636925307879/summary.json`.

Fixtures call native grave spawning/timer stop with supplied state; the Demolish case uses its native action. They do not complete two earned deaths or establish physical controller acceptance. This fixes live-world lifecycle prerequisites only. The owner's pause-while-closed expiry policy is agreed; cold-JVM loot persistence and same-world logout restoration remain open. No new save writer or modern reclaim mechanic is introduced.
