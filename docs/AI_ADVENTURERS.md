# AI adventurers — upstream audit, 17 October 2026

Status: framework exists upstream; a SoloScape adventurer population is not implemented or accepted by this batch.

Source under `upstream/game-server/game/src/main/kotlin/content/bot/` includes `Bot`, `BotManager`, `BotCommands`, behaviour frames/states, setup resolvers, navigation graph/shortcuts, activity slots, combat contexts and metrics. Bots wrap a native `Player`. Actions and resolvers are useful foundations, but they do not establish complete autonomous questing or an offline economy.

`BotCommands.spawn()` chooses an area/name, creates a player, connects a `DummyClient`, applies appearance, grants 10,000 coins and enables running. This is a simulation fixture, not an earned adventurer lifecycle. Inspect account storage/reconnection and every grant before adopting it for persistent companions. Behaviour frames live in memory; no durable task-resume guarantee was established here.

The upstream resource defaults `bots.count=30` with `bots.spawnSeconds=60`. **SoloScape's profile environment overrides `bots.count=0`** in `scripts/profiles.py`; `WorldTest` also disables bots. Existing combat arena counts default to zero. Keep those defaults: this audit measured no CPU/memory/tick budget for a populated world, and existing native route performance is not a bot benchmark.

Before adding one opt-in adventurer, validate deterministic navigation failures/recovery, dialogue ownership, required-item acquisition, death, logout/reload, account separation and constrained tick cost. Start with a single local activity and a disposable bot account; reject arbitrary item/coin spawning in any economy claim. Add population only after costs are measured. Companion-dependent puzzles and offline/global economy simulation remain separate milestones. [M6 overview](SOLO_CONTENT_AUDIT.md).
