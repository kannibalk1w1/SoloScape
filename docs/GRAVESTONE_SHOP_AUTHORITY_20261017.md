# Gravestone shop authority — 17 October 2026

The server now rejects a gravestone selection unless its existing quest-derived availability mask permits it. The default memorial plaque remains free and available; selecting the current grave still costs nothing. Unknown enum slots are rejected before lookup or payment. This closes a native interface-instruction gap without changing prices, prerequisites or the 2011 paid-selection model.

## Reproduction and fix

A native `WorldTest` opens the real shop after supplying the Restless Ghost prerequisite. The authorized local cache identifies royal dwarven gravestone as slot 13 with a 500,000-coin price. Coins and quest state are explicit test inputs, not earned progression. The test submits the normal `InteractInterface` instruction through the existing validation helper, rather than calling the shop script directly.

Before the fix, a player without King of the Dwarves completion has no royal availability bit, yet confirming slot 13 removes all 500,000 coins and selects that grave. A separate positive control with the prerequisite completes the same purchase; repeating that selection charges nothing. The generic instruction validator checks the option index, not this content prerequisite. Client-side disabled entries are insufficient authority.

Server patch 0045 checks membership in the native names enum, then the existing availability mask before charging. The mask is temporary state reconstructed when the shop opens. It is **not purchased ownership** and should not gain a persistence flag. `gravestone_current` already persists. This change adds no ownership collection or save migration.

## Verification and limits

The final death group passes all 24 native cases with no failures or skips, including five new shop cases: locked rejection without charge, unlocked purchase, repeat selection, return to the default free plaque and malformed slots. Existing loot pickup, grave and repeated-identity cases remain selected. Root tooling passes 242 cases with one optional skip. Both exported source stacks match the local source trees; matched native build details are in the accompanying evidence.

Private red XML/logs remain under `.runtime/grave-unlock-persistence-20261017/repro`; final selected results are archived by the coverage runner. An added plaque assertion initially used the wrong fallback value: native variables set to their defined default are cleared. Correcting that assertion required no additional production change. An earlier compile failed on an incorrect message import and was corrected before final validation.

This is host automation, not controller or physical Deck acceptance. It does not validate every quest prerequisite, the visible shop's slot-13 click settings, or persistence of grave actors/floor loot across a stopped world. The latter remains open under the [pause-while-closed persistence plan](GRAVE_PAUSE_PERSISTENCE_PLAN.md). No owner saves or Deck installation were accessed.
