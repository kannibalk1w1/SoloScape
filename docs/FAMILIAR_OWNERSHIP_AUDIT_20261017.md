# Familiar owner identity — 17 October 2026

Claude Haiku traced owner lookups and reproduced wrong-account Slayer credit in a controlled late-uptime fixture. Coordinator review added an original-player identity check and two controls. This is a narrow native server fix, not a claim about ordinary logout timing or a change to contested-kill policy.

## Finding and change

`NPCDeath` delays its death body by one tick. Its familiar kill-credit branch previously resolved `owner_index` through `Players.indexed`, which returns whichever account currently occupies that slot. `Players.index()` starts scanning free slots after its monotonic allocator reaches2048. A stale familiar in a victim's damage-dealer map could therefore credit another player after reuse.

A summoned familiar now retains its original `Player` object in a temporary server-only `familiar_owner_session` attribute. `familiarOwner()` returns that object only while the exact object remains indexed. `NPCDeath` uses this helper. A matching account name alone would not distinguish a new login session; current-follower equality alone would wrongly reject an already-landed hit when the still-online owner dismisses the familiar.

No extra state enters player saves. Native login restores a familiar by summoning it again, which binds the new player object. `owner_index` remains available for existing movement/display consumers. A detached familiar can no longer resolve kill credit to a replacement login. This does not choose a new policy for a departed owner still temporarily present in the player index.

## Evidence

The first native run contains one positive pass and one negative failure: replacement task remaining expected2, actual1. Before failure it verifies a native chicken death, familiar as the maximum damage dealer, original index removal and replacement ownership of the same slot. The coordinator archives that XML before subsequent runs.

The final four native cases pass, and the fresh official Summoning group passes all18 cases with no skips. The final targeted run also includes the existing spirit-wolf lifecycle and Slayer ownership cases. The four new cases cover:

- Original online owner receives native Slayer credit/XP exactly once.
- A different account reusing the index receives no credit or Slayer XP.
- A new session of the same account reusing the index also receives none.
- Dismissal after the killing hit preserves credit for the original online owner.

A spirit wolf is summoned through the pouch option. Pouch, levels and birds task are supplied fixtures. The killing damage uses `directHit(source = familiar)` against an actual chicken; this is not an earned combat/supply journey. The allocator is reflectively set to its late-uptime state and restored in `finally`. Replacement setup/index/spawn occurs without a tick, deliberately placing it before queued death resolution. Logout uses native despawn/removal calls; the network `AccountManager.logout` callback ordering is not reproduced.

Private evidence: `.runtime/familiar-owner-20261017/red-before.xml`, `green-reviewed-v2.log` and the fresh official Summoning summary referenced in [sanitized evidence](evidence/familiar-owner-20261017.json). No Deck, graphical client, real reconnect campaign, loot-table roll or physical controller acceptance is claimed.

## Source audit and remaining boundaries

All paths are relative to `upstream/game-server/`:

| Source | Confirmed boundary |
| --- | --- |
| `engine/.../entity/character/player/Players.kt` | Numeric lookup has no account/session identity; allocator eventually reuses free slots. |
| `engine/.../data/AccountManager.kt`, `entity/Despawn.kt` | Disconnect despawns and queues a player save; player-index removal is scheduled separately. Exact callback/tick ordering needs its own integration probe. |
| `game/.../skill/summoning/Summoning.kt`, `SummoningTimers.kt` | Logout queues familiar NPC removal; NPC removal itself is deferred. Original identity is now bound at summon completion. |
| `game/.../entity/death/NPCDeath.kt` | Victim retains its maximum damage dealer and resolves familiar ownership in a queued death body. This is the reproduced and repaired consumer. |
| `game/.../entity/player/combat/CombatExperience.kt` | Familiar damage XP still resolves a numeric player index. It needs a targeted event/timing test before a separate change. |
| `game/.../skill/summoning/FamiliarCombatSpecials.kt`, familiar death handler in `Summoning.kt` | Numeric owner lookup plus follower NPC-index equality is stronger than raw player lookup, but is **not identity proof** when indices recycle. No runtime failure is claimed for these consumers. |

The initial audit overstated the latter guards as complete ownership protection; coordinator review corrected that conclusion. Broad combat final-hit rules, post-logout reward persistence, NPC-index aliasing and familiar-special ownership remain separate follow-ups. No general entity or transport rewrite is needed for this fix.
