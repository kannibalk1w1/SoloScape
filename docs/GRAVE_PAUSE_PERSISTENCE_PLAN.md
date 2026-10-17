# Grave persistence: pause while the world is closed

The owner selected **pause while closed** on17 October2026. A stopped local world must retain its unrecovered death loot and remaining grave lifetime. Closing it for an hour must not consume that lifetime. This is the agreed behaviour, **not an implemented feature**. The [cold-JVM probe](GRAVE_COLD_JVM_PROBE_20261017.md) still reproduces lost unexpired graves and loot.

The timer continues while the world runs, including when its owner logs out. Preserve native private/public loot rules, repair/bless/demolish behaviour and pre-EoC mechanics. Suspend/resume clock handling is a separate acceptance question; this policy does not establish it. No modern reclaim service is proposed.

## Verified prerequisites and remaining boundary

[Pickup transactions](GROUND_LOOT_TRANSACTION_20261017.md) now retain refused loot and roll back stale references. [Live grave cleanup](GRAVE_LIFECYCLE_IDENTITY_20261017.md) now identifies the current grave, searches past unrelated markers and removes a demolished NPC once. These fix reproduced defects before persistence; neither recreates a grave on login/restart.

Claude Haiku audited the relevant native source. Coordinator review read the previously unreached save/copy/shutdown paths and checked the proposed claim scheme. Important source facts:

- `PlayerSave.save` uses an atomic writer for one account. `Player.copy` copies the variable map shallowly; nested mutable records would still alias a queued snapshot. Use immutable replacement snapshots if this representation is chosen.
- The native config writer/reader support lists/maps/scalars in variables. Arbitrary objects such as `Tile` are not a typed grave codec. Explicit persistent definitions and a bounded versioned record codec still need a native round-trip proof. A new top-level account section is not automatically required.
- `SaveQueue.direct` snapshots online players plus pending saves. Shutdown waits for the current save before requesting that final batch and checks primary success. It does not capture arbitrary offline-owner world objects.
- `AccountManager.logout` despawns and queues the player's save, then removes that player from the live collection. The grave/floor state remains world-owned. A stale offline `Player` object must never overwrite a newer session's account state.
- `FileStorage.save(accounts)` loops over individually replaced files. The [actual native batch diagnostic](NATIVE_SAVE_BATCH_BOUNDARY_20261017.md) confirms that the first account can advance when the second write fails. Individual atomic files do not provide an atomic world checkpoint.
- Profile backups include the existing `saves`/`errors` state closure. A new world file outside it would not automatically be retained, validated or restored. Any new persistence layout must update that contract and its corruption recovery.

## Record requirements, before choosing a layout

Use durable record identities independent of recyclable NPC indexes and display names. Record the original account identity, grave kind/location/remaining lifetime/blessing state, and the latest grave selected for its UI. Treat grave NPCs and actual floor piles as related but distinct records: multiple deaths can share a tile, and existing same-owner stackable floor items can merge. Recreating one pile independently for each grave would duplicate merged loot.

Retain each live pile's item identity, amount, charges, private/public phase and both remaining counters. Native `FloorItemTracking` calls `reveal()` and otherwise `remove()`; disappearance counts down after reveal, not as an absolute total lifetime. Snapshot those exact semantics instead of changing durations. Once public, a pile's visible owner becomes null; provenance cannot rely on that field alone.

Save a normalized, valid destination for instance deaths using the existing death/instance rules, with explicit tests for ephemeral region identities. Do not blindly persist an allocated instance coordinate or always substitute an old logout tile.

Restoration must recreate each record once per world and reattach UI on login. Same-JVM relogin must not spawn a second NPC/pile. Multiple graves, offline owners, empty/partly recovered graves, public loot, repair/bless/demolish and a second death must all update the same authoritative records.

## Smallest next experiment

Prove a crash-consistent transaction with **two original account snapshots and one original grave/pile ledger**, outside live saves. Inject failure before and after each publication step. Recovery must select one coherent state: exact item quantities across both inventories and remaining floor loot, with no loss/duplication. Include an already completed guest pickup even when the item was later banked, merged or consumed.

A per-account record is attractive for owner-only pickups, because inventory and record can share one atomic file. It is insufficient on its own for a guest taking public loot. Do not implement the initial audit's proposed inventory scan for a `claimId`: native items lack that durable provenance, and a collected item can move or disappear legitimately. A replayable transaction journal or coherent world-generation commit needs its own bounded proof. Compare them against existing generation/backups before selecting one; neither is implemented here.

Only after that experiment, connect a versioned native codec, live death/pickup/timer hooks, offline-owner updates, save failure signalling and restoration. Final primary-save confirmation must cover the new state. Validate and back up that state through the launcher without silently resetting it on corruption or an older build.

## Required acceptance

1. Actual native death, partial pickup, clean Save & Quit, then a different JVM/advanced clock: exact remaining loot and lifetime survive. Also prove that elapsed running-world time reduces them.
2. Full inventory and stack overflow refuse without changing the persisted floor record; retry succeeds once. Repeated restart/relogin never duplicates.
3. Guest/public pickup and offline-owner shutdown recover coherently after each injected failure. No stale account overwrite or dependency on finding the original item in the taker's inventory.
4. Multiple graves on same/different tiles, repair/bless, demolition, natural expiry and ephemeral-instance death preserve native rules and marker ancestry.
5. Verified backup/export/import/corruption recovery include the new records. Missing or incompatible data preserves evidence and gives an actionable recovery result.
6. Disposable Deck acceptance covers controller loot search/Take, Save & Quit, Continue and later suspend/resume decisions. Owner saves remain untouched until a reviewed deployment is authorized.

Stop an implementation spike if it needs a broad storage rewrite, silently changes multiplayer/loot semantics, cannot prove quantity conservation across a failed multi-file write, or introduces a save format without recovery/backup support. Keep this P1 open until the real cold-JVM acceptance passes; agreeing the timer policy does not close it.
