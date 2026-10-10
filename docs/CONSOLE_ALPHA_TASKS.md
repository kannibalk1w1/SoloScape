# Playable console alpha — approved implementation task list

Approved 8 October 2026. Continues `overnight/controller-sprint`; public main and
original saves/cache/running processes remain untouched. Each verified batch is
committed and pushed. Actual Claude provides bounded independent reviews.

- [x] A1 Save ownership, isolated profiles/world generations, character metadata,
      versioned backups, validated atomic restore and recovery tests on copies.
- [x] A2 Graphical launcher: New Character, Continue, settings, startup progress,
      actionable errors, local connection and graceful Save & Quit.
- [x] A3 Reusable reversible controller panel foundation: focus/navigation,
      scrolling, tooltips, confirmation, labels, scaling and discoverable guide.
- [x] A4 Custom inventory/equipment: names/quantities/actions, worn slots/bonuses,
      native item/spell selection and mouse/trackpad coexistence.
- [x] A5 Custom bank/shop: readable grids/search/quantities/transaction feedback,
      native permissions, normal mouse fallback and independent toggles.
- [x] A6 Broader action remapping/presets, conflicts, run thresholds/defaults,
      improved quick assignment/clearing and native special-attack investigation.
- [x] A7 Loopback binding, capability negotiation/mismatch feedback, reconnect and
      long-interruption guards; contained solo-pause prototype/investigation with
      documented guest/networking/shutdown behavior.
- [x] A8 Isolated disposable-world gameplay harness; complete existing gathering →
      production → combat route, repair concrete blockers, verify save/reload.
- [x] A9 Final integration checks, Claude follow-ups, updated roadmap/handoff and
      one combined report incorporating both preceding sprints.

Physical controller/Deck performance and Gaming Mode/suspend acceptance are separate
human/hardware gates; automated or renderer checks will not be labelled physical play.

Implementation evidence and limits: [combined report](MORNING_REPORT.md). True pause was delivered as a contained investigation, not an exposed feature; graphical import and physical hardware acceptance remain deferred.
