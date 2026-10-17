# Solo dungeon reward-notice countdown fix — 17 October 2026

Baseline: merged `96e64d2`. Server patch 0033 fixes the ordering of the supported
solo floor's reward and next-floor timer. [Claude Haiku's reproduction](DUNGEON_REWARD_NOTICE_INVESTIGATION_20261017.md)
records the original failure; [follow-up evidence](evidence/dungeon-reward-notice-fix-20261017.json)
records the green regression and tested source identities.

`End-dungeon` queued the reward using `strongQueue`, then immediately started
the next-floor countdown. The queue waits for the player's notice acknowledgment
before granting XP, tokens and floor credit. If the player read that notice for
more than 30 seconds, generation closed its suspended dialogue and discarded the
reward. The acknowledged control received 201 XP, 20 tokens and floor-1 credit;
the delayed case received none.

The solo handler now starts the existing countdown from a private completion
callback at the end of the reward queue. Reading the notice has no deadline.
After acknowledgment, the same reward calculation runs and the normal countdown
advances. No reward formula, floor gate or other party-completion policy changes.

Both native cases now run without an opt-in gate. The delayed case waits 80 ticks
(48 simulated seconds), requires the original dungeon/notice to remain, acknowledges
it, verifies delivery, then lets the countdown replace the dungeon and requires
exactly the same XP, tokens and floor credit afterward. The prompt-acknowledgment
control also passes.

The checked-in `dungeon` group reproduces all **28 selected cases**, with zero
failures, errors or skips:

```bash
SERVER_JAVA=/path/to/jdk21/bin/java bash scripts/test-content-coverage.sh --group dungeon
```

Fixtures are explicit: supplied ring, directly opened boss room, controlled lethal
hit and a teleported legal approach to the real end trapdoor. The test invokes the
ordinary object option and confirmation; it never writes reward state or invokes
a private handler. This is a reward/continuation contract, not an earned dungeon.

Remaining acceptance: ordinary combat and traversal, key pickup, reward persistence
across logout/process restart, cancellation/exit during notices, higher-level and
guide-mode notices, multi-member completion, and human controller readability.
The earlier source audit's group-vote issue remains outside this solo fix. No
owner profile, cache or Deck installation was changed.
