# Earned Lumbridge progression slice — 17 October 2026

This connects the previously separate actual-map Cook’s Assistant journey and fixture-based food/combat coverage. It uses the normal 2011 rules and native instructions. It does not add gameplay content or change balance.

## Scope

A new player receives the real `starterKit` routine, walks the native Cook ingredient/mill route and completes the quest, then walks to Lumbridge swamp fishing. The player catches shrimp, follows native fishing-spot relocations, interrupts fishing by walking, cuts a real tree, lights gathered logs with the starter tinderbox and cooks using the player-lit fire’s native **Use** option. The player returns to the farm, wields the starter bronze sword, kills a native chicken, takes its bones and eats a shrimp. Castle stairs lead to the real bank, where food is deposited and one is withdrawn.

The native SaveQueue/FileStorage writes a TOML save. A fresh Player is constructed from that file and spawned through AccountManager. Tile, completed quest, XP, bank, inventory and equipment must survive without duplicate starter supplies. The persisted creation marker, rather than the transient `had_starter` flag, controls the real login introduction guard.

## Fixtures and limits

- Host `WorldTest`, real cache/collision, real configured NPC/item spawns, instruction helpers, no graphical client or physical controller.
- WorldTest skips character creation. The test calls the production starter-kit function explicitly and verifies its 25 bank coins and one starter shrimp. No extra allowance, spawned resource, quest-state/reward injection, teleport or skill boost.
- The test reissues bounded normal Walk/Attack inputs after an approach ends, selects an accessible native chicken, and follows fishing relocations. It does not assert that every distant click survives moving NPCs uninterrupted.
- Seeded ordinary Kotlin RNG (634), including normal fishing movement, gather success, cooking burns and combat rolls. No forced-success FakeRandom in the connected case. Existing standalone journeys retain their historical fixtures.
- The connected case reuses the native Cook route helper. Standalone Cook still begins without a starter kit and picks up containers. The connected case uses its kit containers.
- Cooking must produce more shrimp than the one supplied by the starter kit before food is consumed. Raw fish, logs and bones must all be acquired natively.
- Save/Continue is a disk round-trip into a fresh player **in the same JVM**. Launcher generations, whole-process restart, controller ownership, human pacing, death/recovery, full-inventory and suspend remain separate gates.

## Reproduction

From the repository root with the local JDK/cache setup completed:

```sh
SERVER_JAVA="$PWD/.runtime/jdks/jdk21/bin/java" bash scripts/test-content-coverage.sh --group journeys
```

This selects FullAdventureJourneyTest (the connected slice plus existing standalone Cook and Rune Mysteries journeys), creates isolated mutable storage, removes selected old XML, archives fresh XML and records patch identities. No owner profile is used. The final run passed all three journeys with zero failures, errors or skips. [Machine-readable evidence](evidence/earned-lumbridge-20261017.json) records case names, patch/source digests, timestamp and fixture limits. Root tooling passed 130 cases (one optional skip); all 64 modified/patched server source files match the exported stack. Incremental patch 0027 reproduces the test byte-for-byte from the prior stack.
