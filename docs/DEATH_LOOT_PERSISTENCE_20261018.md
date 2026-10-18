# Integrated native death-loot persistence — 18 October 2026

Qualification report for server patches 0053–0054 over merged baseline `99f044a`, client stack 0056. This replaces the open integration state described by the earlier [pause/persistence plan](GRAVE_PAUSE_PERSISTENCE_PLAN.md) and [account-batch prerequisite](NATIVE_ACCOUNT_BATCH_20261018.md). Those dated reports remain historical evidence. Physical Deck acceptance and owner deployment are separate gates.

## What changed

The running native game now captures account snapshots and actual world-owned death loot together on the game thread. An IO worker publishes one replayable account-and-world checkpoint. Startup recovers a published checkpoint before account/name/clan readers and before restoring world entities. Clean shutdown uses the same path and only confirms a primary save after it succeeds.

The private `saves/.soloscape-death-loot.v1` file contains a checksummed, versioned envelope of separate grave and floor-pile records. Stable UUIDs avoid dependence on recycled NPC indexes. Graves retain canonical account, displayed identity, kind, tile, facing, remaining lifetime, blessing and latest-grave selection. Piles retain item, amount, charges, owner/public phase, both native counters and contributing accounts. Merged piles remain one record, even when two graves share a tile. BoB items spilled by player death enter the same ledger; manual familiar dismissal keeps its existing rules.

Remaining grave seconds and floor counters pause while the world is closed. Startup rebases seconds to its current clock and restores the native degradation phase. Running time continues to reduce them. Restore queues exact piles without merging them a second time; login attaches markers/latest-grave UI without respawning world loot.

Accepted deaths complete once before logout/shutdown snapshots, even if the animation queue is interrupted. Periodic saving defers while a player is mid-death. This prevents an account saved at zero health or without its corresponding drops. Instance deaths resolve their existing native origin before emitting durable loot.

## Commit and recovery contract

A checkpoint stages native account files and the world envelope, verifies their sizes/hashes/schema, forces the files and directories, then atomically renames the pending directory to `saves/.soloscape-account-save`. That publication is the commit decision. Recovery validates every member before installing any, replays the entire decision, forces installed state and atomically retires the journal. Abandoned unpublished stage directories are inert evidence. Python backup tooling never replays a journal.

Before publication, a process exit leaves the previous complete checkpoint authoritative. After publication, native readers replay the new complete checkpoint, including when an individual canonical file has already advanced. Online account state and queued offline saves enter the same capture as public loot. This covers guest pickup after the owner logs out and after the guest banks the item, without attempting to find a claim token in the guest's inventory.

SaveQueue acknowledges the captured pending entries by identity, retaining any newer queued save that arrived during IO. Captured world bytes are copied before IO. Capture errors retain the previous checkpoint and do not terminate the world loop; direct save reports failure and keeps recovery evidence. Fallback account files are diagnostic evidence, not a successful account-and-world commit or an automatic independent restore.

## Backup and compatibility

Profile backup, restore and stopped-world import now validate the native envelope plus the logical post-replay checkpoint. They preserve canonical files and valid pending journals byte for byte, including pending members overriding older or damaged canonical files. Launcher metadata previews the same validated logical checkpoint, so a committed first save or a covered damaged primary does not block native recovery before it can start. Invalid schema, checksums, members, nested/special/link journal entries or a missing required world file refuse validation before publication. Existing verified backups remain available.

Checkpointed accounts carry top-level `storage_version = 1`. Native version-one journal members require a world file in the same journal. Missing/corrupt world state blocks loading instead of silently starting an empty ledger. The frozen previous server52 jar rejects this unknown account key, preventing an apparently successful downgrade from dropping the world state. Older whole-world backups can still be explicitly restored through the existing generation mechanism; mixing individual old/new files is not supported.

A malformed legacy account encountered while checking for a missing guarded world also blocks startup. This is deliberately conservative: the validator cannot prove that the absent world was optional. It preserves evidence for a complete verified restore. Existing account discovery can still skip malformed unrelated accounts after a valid world is established; this change is not automatic file repair.

## Validation

Exact source, logs and suite identities are recorded in [sanitized evidence](evidence/death-loot-persistence-20261018.json). Only original/disposable characters and copied compatible inputs were used. No owner profile or Deck installation was changed.

Qualification includes 42 native storage/save cases, 40 native death/loot cases (nine cold-process scenarios with 49 child JVM launches), and 294 root tooling cases with one optional skip. All selected native cases pass without skips. The storage run precedes the final game-only instance/lifecycle changes; its engine files are unchanged.

Qualification includes:

- Native storage/save regressions, including actual FileStorage interruption/replay, strict world decoding, missing/corrupt world refusal, immutable byte capture, pending acknowledgement and capture-failure receipt handling.
- Native cold-process world tests: actual damage/death, full-inventory Take refusal then one charged recovery, stopped/running clock distinction, repeated deaths with merged loot, blessed graves, familiar inventory, death-animation Save & Quit and disconnect.
- Instance-origin cold restore and same-JVM logout/relogin, native repair and demolition retain identities without duplicate loot. The instance test reproduced a further defect: death left an instance offset attached to a normal-world respawn, and logout applied it again. Death now clears an exited instance before teleporting; same-instance custom respawns retain it.
- Actual offline-owner public pickup, bank deposit and forced exit at six production checkpoint boundaries: prepared, published, installed world, installed guest account, materialized and retired. Two later JVMs verify each outcome and exact conservation.
- Real native output imported into a disposable managed profile, verified/archive-restored, then read by a fresh native JVM. A separately published-but-interrupted checkpoint follows the same path, retaining its journal until native recovery. Both prove byte-preserving archive roundtrips; Python does not repair/rewrite records.
- Frozen server52 account-load rejection and root tooling regressions.

The native cold-process harness boots WorldTest definitions/scripts and invokes the same production world-start persistence handler, damage, Take/bank, account spawn/logout and World.shutdown paths. It uses independent JVMs and deliberate test clocks; it is not a network client session or a physical power-cut test. Process exits test the production commit implementation, not storage hardware's power-loss behaviour. Directory forcing is qualified on Linux; other filesystems/platforms need their own acceptance.

## Matched private build

Private snapshot `.runtime/deck-exports/1792316178568187369` contains the matched server54/client56 pair from implementation commit `84cc428`. Its 10,928 listed entries verify before and after use. It is a private, cache-containing test package, never a public GitHub release. The previously ready52 snapshot is retained.

The packaged graphical native New/Continue sessions pass with exact compared account/inventory/XP/tile fields, in-game Save & Quit, verified backups, cancelled startup preservation and a deliberate primary/fallback write failure that refuses clean closure and restores a verified backup. A further two headless packaged `Main` sessions restore a live grave and a real published checkpoint with a covered damaged primary, retain all UUIDs/quantities/charges, obtain normal save receipts and validate three backups per profile. These run the real application startup handler beyond the WorldTest harness.

Desktop software/Xvfb observations: native world-ready notification at 4.20s for New and 3.10s for Continue. Complete probe sessions, including readiness and saving, take 23.04s and 23.13s. Process RSS peaks are recorded in the evidence JSON. They are short host observations, not Steam Deck frame-rate, startup, battery, audio or suspend acceptance. ALSA is deliberately empty for this private graphical fixture.

## Physical follow-up

On a disposable Deck profile, die carrying charged and stackable items, search/Take some loot with the controller, Save & Quit, wait, then Continue. Confirm remaining loot, charges, marker/timer, recover once, and repeat Continue. Repeat an interrupted death and a shared-world guest pickup if co-op is being tested. Suspend/resume, audible audio, frame pacing and actual controller feel remain physical acceptance work. Owner-save migration and Deck deployment remain held.
