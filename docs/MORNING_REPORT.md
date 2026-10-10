# Combined morning report — 10 October 2026

The controller journeys/recovery, Deck keyboard/classic UI and controller-first playable-loop sprints are merged into GitHub’s default branch `main` via [PR #1](https://github.com/kannibalk1w1/SoloScape/pull/1), merge commit `a07347d2475451e4d6e2d70053cd9cbbb84071a1`. Tag `controller-deck-r9` preserves the installed source and incremental sprint history. This report combines their outcomes; earlier detailed reports remain archived.

## Current project

SoloScape runs a pinned revision-634 client and local server in independent character worlds. Controller camera, targeting, movement feedback and reversible direct movement have owner acceptance. Home-tab and quick-action radials, contextual B, right-stick menu scrolling, remapping/presets and optional inventory/equipment/bank/shop/quest/skills/combat/prayer/spellbook screens are implemented. Native game validation/actions remain authoritative. Menus do not freeze simulation.

The launcher provides New/Continue, separate worlds, verified backups/restore/import/retention and owned-session recovery. Cook's Assistant, Rune Mysteries, Restless Ghost and gathering/commerce/combat/food routes have real-server earned progression and native save/reload evidence. Controller full-quest playthrough remains physical acceptance.

The Deck has project-local Java 8/21 and a private **SoloScape Test** Desktop shortcut. Earlier native New/Continue/settings/text/save and owned client/server recovery pass; recovery deliberately does not claim confirmed clean shutdown. Exclusive keyboard ownership fixes the reported launcher double typing and local D-pad/caret competition. Steam is preferred on a detected Deck, with explicit local/physical alternatives. Recognized in-game amount/name/string/search prompts and a deliberate chat/other-entry path pause competing controller actions. Automatic discovery of every widget-specific textbox remains future work.

Actual Claude implemented the reversible classic stone/brown/gold/parchment controller theme and this sprint's readability follow-up. Native cache artwork and private screenshots are excluded from published renderer fixtures.

## Latest playable-loop changes

- **Menu return and scrolling focus:** remember pane/slot identities across returns and text entry; revalidate fresh quantities/actions; discard stale contexts and require neutral input. Text interruptions preserve child/Settings/Home ancestry and allow native repaint. Logout/disconnect clears remembered history.
- **Real server cancellation:** fresh matched-server negotiation enables opcode 87 for unanswered amount/name/string entries. Cancel clears the continuation without inventing an answer, while bank/side panes remain open. A controller Basics preference reverses this. Logout drains cancelled-entry cleanup; coroutine cancellation is propagated without a false error log. Legacy servers retain local closing. Type-11 search stays native/local.
- **Native Inventory fix:** asking to open the visible resized inventory no longer re-clicks and collapses it.
- **Native object reach fix:** rectangular objects use the native rectangle check with dimensions, rotated access faces and collision checks. The actual castle stairs are usable from their reachable edge.
- **Real bank Search fix:** native Search runs synchronously. Registering and consuming the fallback in the right order prevents a second toggle from closing the newly opened prompt. Local text edits now invoke the native filter refresh. The server's re-armed Search button is distinguished from active search mode.
- **Readability:** real grid page counts, one-line short cells, reserved action rows/hit targets, whole footer lines, clearer selected action and labels fitted to radial wedges. Both style choices remain reversible.

## Verification

| Check | Latest evidence |
| --- | --- |
| Client tests | 211 cases; zero failures/errors; one existing optional SDL skip |
| Root launcher/profile/recovery/metrics tooling | 78 passing |
| Selected engine | 12 passing: ActionQueue cancellation/logout plus Script cancellation cleanup |
| Network cancellation decoder | One passing; one-byte native types 7–9 only |
| Selected game/content | 24 passing; bank cancellation and actual earned progression/quest/save routes |
| Source reproduction and matched archives | 106 client / 43 server files through 0035 / 0014; Java 8/21 jars/stamp verified |
| Native host and actual Deck New/Continue | Both pass; exact saves, four verified backups, full bank/castle routes and startup cancellation |
| Real Deck controller detection | 100/100 passive SDL samples connected; no buttons pressed; max stick 0.0431 |
| Readability previews | 20 synthetic classic/modern fixtures rendered; representative small/Deck layouts inspected |

The native journey uses ordinary controller adapters and fresh real scene/widget actions: item Use/cancel, sword Wield/Remove, courtyard door, both castle floors, banker, deposit, Withdraw-X edit/Cancel, server pending-entry replies, native search edit/cancel/toggle, normal withdrawal, stairs/return, logout/relogin, New/Continue and exact-save checks. Disposable servers alone opt into a nonce-bound read-only pending-entry diagnostic. Earlier failed probes exposed real Inventory, staircase and Search defects and incorrect probe assumptions; those failures are retained privately and are not counted as passes.

Actual Claude reviewed menu/action freshness, cancellation, native reach geometry, readability and Search dispatch ordering. Findings were integrated and tested. Its final static reviews found no blockers; they do not establish hardware acceptance. The cancellation protocol identifies entry type rather than server prompt id, leaving a same-type replacement race; busy/type-mismatch refusal retains the native server continuation until later interaction/logout. [Detailed evidence](PLAYABLE_LOOP_EVIDENCE.md), [Claude review](CLAUDE_PLAYABLE_LOOP_REVIEW.md) and [text scope](IN_GAME_TEXT_INPUT.md).

## Deck delivery and measurements

The installed **SoloScape Test** Desktop shortcut selects r9. **SoloScape** is also registered in Steam as a native non-Steam game using the stable launcher path. Its Steam launch opened the verified r9 launcher/backend and frame; an ordinary window-close request shut them down. No normal worlds were started for this check. Existing Steam shortcuts were backed up; the new entry is verified in Steam and on disk. Normal r8 profiles were absent, so none were removed or copied; every older build and disposable test world remains.

The tested code checkpoint is `fdbc2678f0b32b1196aa6b209562f223eb004635`. Full native session totals: host **270.231 / 265.419 s**, Deck **295.515 / 296.860 s** (New/Continue). Gameplay round trips: host **210.121 / 207.108 s**, Deck **204.103 / 207.097 s**, **78** native walk dispatches each. These totals include fixed probe waits and save/relogin work; they are not launch-time or responsiveness targets. The final manifest identity is recorded in [Deck validation](DECK_VALIDATION.md).

The [Steam Deck player guide](SOLOSCAPE_STEAM_DECK_PLAYER_GUIDE.md) is self-contained Markdown for Obsidian, with first-time plugin enablement, character creation, controls, text ownership, bank/search, saving/recovery and an overnight checklist. A copy is provided in the Deck’s Downloads folder.

Latest Deck software-renderer callbacks: baseline median **24.30 / 22.89 ms**, journal **29.18 / 28.02 ms**. Whole-session peak simultaneous JVM RSS sums **8840 / 8943 MiB**, client peaks **7298 / 7719 MiB**. These longer, roughly five-minute sessions use substantially more resident memory than the earlier short probes; sustained memory behavior is a priority for the next performance campaign. RSS sums can double-count shared pages.

Earlier r6 software-renderer callbacks remain a historical baseline: New/Continue median 23.92/23.27 ms, journal 31.91/30.53 ms. Whole-session RSS sums 3013/2600 MiB include shared-page double counting. They are short Desktop observations, not GPU presentation FPS, input latency, sustained Gaming Mode budgets or battery measurements. [Device evidence](DECK_VALIDATION.md) records the new observations and exact private test/deployment identities.

Steam visibility in text probes is injected; actual SDL detection is real but actions are native/synthetic. Wayland screenshots were black. Gaming Mode, physical Steam keyboard visibility, simultaneous physical input, arm's-length readability, touch accuracy, full reconnect/unplug, suspend/resume, OpenGL/GPU timing and sustained battery/thermal comfort remain unclaimed.

## Next task list

1. Physically accept launcher and in-game Steam/local text ownership, including amount Cancel, search, chat, field traversal and reopen.
2. Play the bank/shop/settings/quest loop on the Deck: B returns one level, right stick scrolls the intended pane, focus survives returns, Use/Wield/Remove/quick slots feel clear.
3. Physically complete the existing Cook/Rune routes from a fresh profile; record concrete UI/text/content gaps.
4. Run a controlled Gaming Mode/focus/reconnect/suspend and sustained performance campaign; optimize measured bottlenecks.
5. Extend native textbox recognition and special-interface coverage from those observations, then validate fresh-machine setup/update and redistribution licences before packaging.

[Project handoff](PROJECT_HANDOFF.md) is the self-contained ChatGPT context. [Roadmap](ROADMAP.md) is the wider proposed backlog; [this sprint's tasks](PLAYABLE_LOOP_SPRINT_TASKS.md) track delivered scope. [Physical checklist](PLAYABLE_LOOP_ACCEPTANCE.md) gives the next acceptance steps. Previous reports: [keyboard/classic UI](MORNING_REPORT_KEYBOARD_CLASSIC.md), [Deck](MORNING_REPORT_DECK.md), [journeys](MORNING_REPORT_JOURNEYS.md). The cache/setup instructions remain in [CACHE_SETUP.md](CACHE_SETUP.md): the compatible archive comes from the pinned upstream maintainer, not an official Jagex distribution.

## Final delivery

The Deck’s Steam library contains **SoloScape**, launching the verified r9 snapshot. The standalone player guide is also copied to `~/Downloads/SoloScape_Steam_Deck_Player_Guide.md` for Obsidian. All completed source and documentation are published on `main`; only the primary checkout remains, with completed sprint branches and the Claude helper terminal removed. Normal worlds, cache and older private build/test evidence are preserved. The game and launcher are closed, ready for the owner’s overnight play.
