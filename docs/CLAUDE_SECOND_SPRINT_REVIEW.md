# Second controller sprint: implementation review

Scope: the new unexported code in `upstream/runelite-client/client/src`:
- `QuickBinding` and `QuickRadialControls`
- `ControllerUi` production, amount and smithing sibling-action code
- `ControllerWorld` server-approach targets
- the plugin's quick-wheel wiring, config and button-conflict check
- overlay labels

This was a read-only review. I made no edits, builds, game launch or cache reads. I make no
claims about whether these widgets exist in the cache, and no gameplay acceptance.

## Verdict

**No severe integration defects or native-safety blockers.** Every new path still goes through
`ControllerUi.invoke`, which checks freshness, the open group, `same()` identity and the
permission-gated op list. Each press dispatches at most one native action. The most
important item is a gameplay-safety hazard in the **default** quick slots (finding 1).

## What I checked and found correct

- **One action per press (quick wheel).** A sets `pending` and disarms. Each later tick does at
  most one `invoke`, then clears `pending` whether the invoke succeeds or fails, so a failure
  is never retried. A 1 s deadline ends it. B or the trigger cancels even while pending
  (`QuickRadialControls.java:110`). `gateway.allowed()` is re-checked every tick, and it is
  false in dialogue, modal panels and entry, because `availableTabs()` returns 0 there. The
  wheel therefore resets on any modal transition.
- **Stale identity and permissions.** The match always runs against a fresh
  `snapshot(true)`. Prayer and spell bindings require the exact widget id and name. Actions
  that carry a selection token are never captured or matched. `decode` rejects unknown groups
  and tabs, and caps name and action length at 120 characters.
- **Button conflicts.** Defaults are Quick = Start, Home = View, Inventory = Y. Any pair of
  equal buttons disables both wheels and shows a warning (`SoloScapeControllerPlugin.java:229-231`).
  The wheel's own A, B, X, Y, bumpers and D-pad are only read while it is active, and the plugin
  returns before radial, UI and world processing while the wheel is in use.
- **Changing potion doses.** A captured Drink binding falls back to items of the same family
  (the name without its `(n)` suffix) when the exact item ID is gone, so the binding survives
  (4) → (3) → … → (1).
- **Smithing sibling actions.** The `SMITHING` rows `{item, name, _1, _5, _x, _all}` match the
  server TOML (for example dagger 18/19/24/23/22/21). When invoked, the sibling is re-checked
  (fresh, rendered this frame, group open), and the op is re-derived from the sibling's own
  permission-gated `actions()`. Sibling buttons are left out of the pane so they aren't listed
  twice. `primary()` prefers `Make|Tan|Smith 1` as a full-string match, so it never picks
  "Make 10", "All" or "X".
- **Amount row (905/916).** Only components 5–8 (1, 5, 10, All) are exposed, with no decrement.
  It is gated on `dialogueId == 905` and `916` being open. 916 is kept out of `DIALOGUES`, so
  the Continue choices stay primary. Each LB/RB press invokes exactly once.
- **Server-approach targets.** These are only Attack-labelled NPC options and action 30.
  `reachable(t, paths)` returns early for them, so they don't use up the 8-path reachability
  budget that objects and ground items rely on. They are capped at 6. The 10-tile radius
  applies only to them, because `nearby()` filters everything else at 5 before sorting.
  `interact` still re-enumerates targets and needs a token, `sameEntity`, option and name match.
  The overlay shows a dashed footprint with the label "server approach".

## Findings (ranked)

### 1. Medium (gameplay safety): default quick slots act on the first matching inventory item
`QuickBinding.food()` / `drink()` use `item = -1` (`QuickBinding.java:13-14`). `match`
(`:33-37`) then accepts the **first** slot whose op is Eat or Drink. Depending on inventory
order, the default slot could:
- eat a damaging or quest "Eat" item (for example a rock cake or a quest consumable),
- drink a stat-lowering or HP-costing brew, or drink wine,
- spend a valuable potion when the player wanted a different one.

A player pressing a "food" or "potion" wheel slot in combat can't see which slot will be
chosen.

**Smallest fix:** ship slots 0/1 empty, labelled "Assign: focus food/potion, press X". If you
want defaults, show the item that *would* be chosen as the wheel label (resolve
`match` against the current snapshot while the wheel is open). Make A require that label to be
non-empty.

### 2. Low: a dose fallback picks the first slot, not the lowest dose
For a captured potion, `match` takes the first family member in slot order (`:36`), so a (4)
can be used while a (1) is still in the inventory. That's wasteful and leaves the inventory
cluttered, though it doesn't break anything. **Fix:** in `QuickRadialControls` pending
resolution, gather all matches and prefer the exact item ID, then the lowest `(n)`.

### 3. Low: partial food (cakes, pies) breaks a captured Eat binding
Eat has no family fallback. A bound "Cake" becomes "2/3 cake" (a different ID and name), and
the slot reports "Unavailable". This fails safely. **Optional fix:** document it, or add a small
family rule for the `2/3`, `Slice of` and `Half a` prefixes.

### 4. Low (UX): the amount cursor isn't synced to the current amount
`amountIndex` resets to 0 when a dialogue opens (`UiControls.java:104`) without considering
`state.amount` (varbit 8095, persisted). The first RB always sends "5" and the first LB sends
"All", whatever the current amount. The prompt still shows the real amount, so nothing unsafe
happens. **Fix:** when the dialogue opens, set `amountIndex` from `state.amount` (1→0, 5→1,
10→2, ≥ max → index of All, if present).

### 5. Low: action 30 (any "use on NPC") is always marked "server approach"
`target(...)` sets `serverApproach` for `action == 30` whether the selection is a combat spell
or a used item (`ControllerWorld.java:272`). For "Use item on NPC", the server walks in to
interaction range, which matches native behaviour. The 10-tile reach and the "server approach"
label overstate the case, though. This is cosmetic and safe. **Optional fix:** set it only when
the selection source is a spellbook group (192/193/430).

### 6. Low: spell matching ignores the action type
`match` accepts any type 13/18/1011 action whose label equals the stored label (`:43`). If a
spell widget ever exposes the same label as both Select and an op, the first one wins, which
could swap select-then-target for a direct cast. **Fix:** store `a.type` in the binding (encode
version 2) and require it to match.

## Notes and limits
- `productionAmount` reads varbit 8095 via `aClass170_10209.method62`. I did not confirm that
  the call is safe if the varbit definition is missing from the pinned cache. The adapter
  `RuntimeException` catch would contain it, but the prompt would then show nothing. Check
  in game.
- I did not verify whether ops on 300/324/438/446/675/916 are unlocked or have CS2 handlers
  in this revision. That still needs in-game confirmation, as noted in the planning audit.
- `extraModal` now includes 742/743/178/275/134 (settings, quests, skill guide). While one is
  open, B closes it with a Walk, which closes every server-opened interface. I did not check
  whether any of these are opened client-side, in which case the Walk would not close them.
  The 1 s close timeout then returns control.
- Not reviewed: tests (being added at the same time as this review), overlay layout details,
  and earlier batches.
