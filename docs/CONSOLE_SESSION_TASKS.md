# Cohesive console session — approved 9 October 2026

- [x] N1 Shared menu parent/back navigation, focus restoration and neutral input handoff.
- [x] N2 Right-stick scrolling in active panes, gradual repeat speed, native edge scrolling and mouse coexistence.
- [x] N3 Everyday interface readability, artwork where supported, tooltips, confirmations and remapped hints.
- [x] N4 Existing early-game route: gathering, production, shops, banking, combat, travel and a short quest; repair concrete blockers and verify persistence.
- [x] N5 Interrupted startup, client closure, reconnect and save recovery; explicit manageable backup retention.
- [x] N6 Repeatable installation/update guidance, performance diagnostics and a focused physical controller/Deck acceptance checklist.

Commit verified batches to overnight/controller-sprint. Preserve current game, original saves/cache and public main. Automated evidence does not replace hardware acceptance.

Implementation/preparation complete: 320f963, 017f2ad, ef55e2a, followed by the documentation checkpoint. Evidence: 151 client (one optional SDL skip), 44 root and 11 selected game cases; full 87/31-file exports; matched builds; native New/Continue and observed early cancellation; Claude follow-up with no blockers. See MORNING_REPORT.md.

The checks above record delivered code and preparation, not human acceptance. Separate remaining gates:

- [ ] Physical B ancestry and scroll speed/neutral checks in both layouts.
- [ ] Full actual-map Cook's Assistant route, including doors and mill floors, on a controller.
- [ ] Steam Deck Gaming Mode, frame-time/battery and suspend/reconnect acceptance.
- [ ] Artwork relog/native-cache variants and minimum-scale readability polish from observed issues.
