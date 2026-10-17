# Playtest direction and architecture review

Reviewed 17 October 2026 against merged `main` at `502df96` (PRs #20–#24 and their evidence). This is an inspection and prioritisation pass, not new human acceptance. Start at [CURRENT_STATUS](CURRENT_STATUS.md); [the dated session checklist](CONSOLE_SESSION_ACCEPTANCE.md) remains useful historical acceptance guidance.

SoloScape is a substantial native revision-634 controller RPG prototype. It is beyond a controller proof of concept, but not a physically accepted console release. Keep 2010–2011 presentation/rules, pre-EoC combat, server authority, optional native interfaces, independent worlds and reversible changes. More quest scripts do not resolve uncertainty about real buttons, Steam keyboard visibility or suspend.

## What the latest evidence actually establishes

- Ordered client 0001–0053/server 0001–0022 patches reproduce the pinned sources; root CI is asset-free tooling, not the native game suite. Consult the generated stack identities rather than copying old test counts.
- Native shop buy/sell persistence passed on Deck after patch 0053. Cooking B and Settings lifetime failures included probe defects; their corrections are not evidence of equivalent production defects.
- Two r31 Settings reruns passed exact save equality. The earlier r30 one-tile change remains unexplained; do not weaken the comparison or claim a fix.
- r29 completed 36.14 minutes on powered Deck OpenGL at 59.04 average callback FPS, but missed the strict frame-time tails. r32 was a mixed-power, approximately 30 FPS loading diagnostic, not an improved 60 FPS benchmark.
- Ended, unverified owner sessions were found more than once. Recovery preserved valid current saves and archives without proving earlier clean closure. A valid TOML save is not proof that every intended last action was durably saved.
- Representative early quests/production have native evidence; full M6, Summoning and solo Dungeoneering acceptance do not follow from directories or definitions existing.

Evidence: [Deck results](DECK_CONTROLLER_VALIDATION_20261014.md), [loading diagnosis](DECK_STALL_DIAGNOSIS_20261014.md), [shared contracts](CONTROLLER_INTERACTION_ACCEPTANCE.md), [content coverage](CONTENT_COVERAGE.md).

## Architecture findings, ranked by practical risk

Paths below are relative to `upstream/runelite-client/client/src/` unless stated otherwise. Inspect the applied stack, not just the initial upstream tree.

| Area | Current design / real risk | Priority and contained next action |
| --- | --- | --- |
| Input ownership | `.../plugins/soloscapecontroller/SoloScapeControllerPlugin.java:processInput` sequences text, reconnect, settings, selected source, tab bar, radials, panels and world through ordered guards. This is functional but precedence changes can expose two owners or clear remembered state. | P1 on reproduction. Add a transition regression for each real failure; consider a small opt-in owner/reason trace before any arbiter rewrite. |
| Neutral/handoff | `ActionMap`, `WorldControls`, `CameraIntent` and plugin resets distinguish camera, scrolling and world movement. Long input gaps (>750 ms), focus loss and disconnect clear intent. | Physically test held-stick menu entry/exit and reconnect. Preserve release-and-push; do not replace it with automatic resume. This is not a suspend/world-clock policy. |
| Back ancestry | `MenuNavigation` holds bounded parent identities; `SelectionReturn` holds source identity/token, not executable actions. Arbitrary server modal reopening is deliberately unsupported. | Keep identity-only restoration and fresh actions. Test B through entry → panel → known parent → Home → world, plus server-closed panels. Avoid a universal modal reopener. |
| Source targeting / quick slots | Selection tokens, quantity/name/child identity and one-shot return prevent stale invocation. Quick casts intentionally remain world actions. | Test depleted stacks, changed equipment, target death/despawn, interruption and cancelled casts. Quick-slot support is per validated native action, not a generic arbitrary packet macro. |
| Native/custom coexistence | `ControllerUi.java` extracts current rendered widgets, native IDs/actions and bounded artwork. Stock boxes needed graphic metadata joined to their click target (0053). | P1 risk for new interface families. Verify authoritative action target separately from display data; group-specific fixtures plus a live native flow. Never fix this per quest. |
| Revision coupling | `ControllerUi`, `ControllerEntry`, `ControllerWorld` and `com/GameClient` bridge obfuscated fields, widget groups, scene coordinates and native menu dispatch. Arrays/groups/opcodes are intentionally revision-specific. | High extension cost, not reason for wholesale deobfuscation. Put new native knowledge behind these bridges; use semantic adapters in pure controller code. New cache/interface backports require explicit adapter acceptance. |
| Bank/shop/text | Separate stock/carried panes, native amount validation, type-11 local search and matched-server entry cancellation exist. Cancellation identifies type, not an individual server prompt. | Same-type replacement race remains real documented risk. Reproduce before adding a negotiated prompt-generation protocol; retain legacy fallback and native validation. |
| Controller ↔ mouse | Native panels, overlay mouse listeners, focus guards and selection reset coexist. Dragging, trackpad pointer, mouse wheel and Steam overlay add paths automation does not model well. | P1/P2 physical matrix. Check a mouse transaction followed by controller A cannot repeat stale selection. Do not globally disable native mouse. |
| Plugin/sidebar | Native RuneLite config, Java EDT and game-thread canvas focus/resize interact. Keyboard sidebar/fullscreen toggles exist; a universally available remappable controller sidebar action remains incomplete. | P2 unless it blocks setup, then P1. Verify pre-plugin accessibility, resize and closing-press consumption on Deck. Avoid adding more sidebar-dependent core flows. |
| Direct movement | Current-session nonce/version capability negotiation gates optional 85/86/87-related behaviour; server applies existing collision, run/energy and busy rules. Ordinary destination walking remains. | Keep server authority and feature negotiation. Nonce capability matching is compatibility/session binding, not authentication of an arbitrary hostile server. Test reconnect and unsupported servers. |
| Launcher/lifecycle | Swing launcher starts a Python backend; `scripts/profile_session.py`, `profiles.py`, `session_recovery.py` use locks, generations, checksums and verified process identity. Existing native/world tests are strong. | P0 if progress is lost or saving is misreported. Reproduce Steam Stop/client window close/launcher death separately; record stop reason and save outcome. Never infer clean closure from process exit. |
| Suspend/resume | Focus/long-gap guards and keep-awake support are not true solo pause. Native server ticks, timers, connection expiry and saves still matter. | Acceptance blocker. First establish an explicit safe Save & Quit fallback; design pause only after clock/tick/network/guest policy. No catch-up simulation assumption. |
| Test ownership | Native probes sometimes reflect private plugin fields and simulate a connected pad. Several earlier failures were masked or observed the wrong pane. | Keep probe input scoped/restored, require dispatch success and saved effects, retain failures. Longer term, a narrow harness driver is justified only when repeated private-field breakage warrants it. Do not remove production disconnect guards to pass probes. |
| Performance | Synchronous region rebuild/toolkit creation and map rendering account for large gaps; GC is only part of them. | Instrument sub-steps, then make one measured reversible change. Keep logic/server cadence and fair power/renderer comparisons; average FPS alone is insufficient. |

There is no architectural blocker that justifies replacing the functioning controller system. The highest risks are ownership transitions at native boundaries, lifecycle truth and incomplete physical coverage. Pure `UiControls.Gateway`, input maths/navigation and server semantic definitions are useful existing seams.

## Physical acceptance priorities

Use a disposable **real** profile with earned state and record the exact private build/manifest, source commit, native/custom toggles, controller mapping, graphics and power. Do not repeatedly run every quest.

1. **Save boundary:** make a visible inventory/XP/position change, use in-game Save & Quit, wait for success, Continue and compare. Then test client close and Steam Stop separately on a disposable copy. Confirm the normal launcher explains an unverified session rather than reporting it clean.
2. **Ownership loop:** world → inventory Use → target/cancel → bank search/Withdraw-X Cancel → shop both panes → Settings child/B/Home → world. Hold both sticks during handoff; alternate controller and trackpad. Confirm no movement/transactions leak.
3. **Text and setup:** character naming, chat, search and quantities under Steam and local keyboard modes; Steam+X, cancel/reopen, focus loss and remaps. Only one keyboard owns a prompt; typing must not activate the game behind it.
4. **One enjoyable progression slice:** choose one already validated early route plus gathering/production/combat/loot/banking. Assess readability, discoverability, rewards and friction, rather than quest coverage count.
5. **Interruption/performance:** controlled reconnect, Steam overlay, focus changes, then suspend on a disposable profile. Record powered/battery conditions separately; retain loading stalls. Until suspend is accepted, save and quit before sleep.

Do not intentionally cut power to the only copy of a character. Any destructive failure experiment uses disposable storage and a verified external backup.

## GitHub playtest workflow

Use **New issue → Human playtest finding**, implemented in `.github/ISSUE_TEMPLATE/playtest.yml`. One reproducible issue per finding; link duplicates. Severity is an impact assessment, not evidence of root cause.

| Severity | Meaning | Response |
| --- | --- | --- |
| P0 | Save corruption/lost progress, security exposure or serious lifecycle failure | Stop dependent testing; preserve private logs, world/generation and external verified backup. Isolate on a copy; no progression expansion until understood. |
| P1 | Blocks controller-only play or progression | Reproduce on the named build, identify ownership/native contract, fix and replay that representative flow with saved effects. |
| P2 | Recurring usability/friction | Record frequency/impact; fix a bounded cluster after P0/P1, then assess physically. |
| P3 | Polish/nice-to-have | Backlog with a screenshot and desired result; do not block core acceptance unless accessibility impact raises severity. |

Required: build/commit (or explicitly unknown), device/OS, Desktop/Gaming Mode, controller/Steam layout/input method/remaps, location/activity, expected/actual behaviour, ordered steps and frequency. Optional: timestamp, last successful save, screenshots/video and redacted log excerpts. Private saves/authentication stay off public issues; arrange a private reproducer if needed.

Maintainer triage records `reproduced / needs information / probe-only / fixed-awaiting-physical / physically accepted / deferred` in the issue body or comments. Labels are optional; do not require a separate service/database. Close a user-facing fix only after its acceptance is explicit, or clearly state the remaining physical follow-up. Link the fix, automated check and human retest build in the issue.

## Immediate post-playtest decision tree

- P0 or uncertain save completion → preserve evidence, stop world, use verified recovery on a copy; diagnose before any content/port work.
- P1 controller/progression blocker → reproduce the native/shared contract, fix once, automated regression plus physical replay; then resume the slice.
- Only P2/P3 → batch a few coherent usability fixes; do not start another UI overhaul.
- Core session works but tails/suspend fail → keep M4 active alongside a bounded M6 audit; no release claim.
- One slice and lifecycle/performance gates accepted → Backport Lab, then one optional later-content proof. New dependencies/maps require a fresh scope decision.
- WASM interest remains → execute only the narrow [spike plan](WASM_SPIKE_PLAN.md), after the native acceptance gate; do not introduce a transport hierarchy or new renderer speculatively.

## Documentation ownership

`docs/current-status.json` is the curated evidence ledger; `scripts/current_status.py` derives stack identities and renders `CURRENT_STATUS.md`. CI checks regeneration. It does not inspect a currently connected Deck or infer human acceptance from tests. Review affected rows whenever source changes. Keep dated reports unchanged; README/roadmap should point to the index rather than repeat counts/build names.
