# Familiar dismissal identity — 17 October 2026

Native spirit-wolf dismissal exposed two faults from one setter: assigning `player.follower = null` did nothing. Stopping the familiar timer then re-entered dismissal with the old binding, queuing removal twice. The NPC counter became−1 with zero live NPCs. Later, an unrelated rat allocated into the freed index became the player's apparent follower.

Server patch0039 clears `follower_index` and `follower_id` when assigning null. It leaves the familiar's original owner-session reference intact, preserving credit for an already landed hit as established by patch0038. No generic allocator/removal rewrite is required.

## Reproduction and verification

Claude Haiku wrote two independent reproductions using native pouch infusion with supplied materials, Summon and the familiar-details dismissal confirmation. Both failed before the fix. The slot-reuse test forces the allocator's late-uptime scan state temporarily, restoring it in `finally`; an actual rat then takes the freed slot through normal NPC insertion. After the fix, the rat remains unrelated and a newly infused pouch summons another wolf.

Coordinator verification passes both cases plus four owner-session, two lifecycle and44 utility-special-effect cases:52 targeted tests, with no failures or skips. The official selected Summoning group independently passes20 tests with no failures or skips. All81 modified/patched server source files match the exported stack. [Sanitized evidence](evidence/familiar-dismissal-20261017.json) includes the source-stack hashes and selected suite counts.

Private red XML and coordinator logs are under `.runtime/familiar-dismissal-20261017/`; official evidence is `.runtime/content-coverage/1792257901870374858/summary.json`. These are controlled native server tests, not an earned Summoning journey, actual long-uptime session or physical controller acceptance. Test dismiss, resummon and logout behaviour with a familiar during later Deck acceptance.
