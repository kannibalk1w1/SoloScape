# Proposed next large sprint: dependable Deck gameplay sessions

The UI and individual quest/production gateways now have fixture coverage. The next gap is a complete controller-only session with real movement and combat, reliable save/lifecycle handling and sustained Gaming Mode performance. Existing [60 FPS acceptance](DECK_60FPS_SPRINT.md) remains the performance target; short stationary results do not establish it.

## Proposed work

1. Complete Blood Pact through actual native combat and its instance transitions, checking target selection, movement tiles, health visibility, loot and cancellation. Extend Druidic Ritual coverage to ingredient gathering and real travel, alongside a bank/shop/crafting round trip. Keep supplied-material/teleport fixtures clearly distinct from real-route acceptance.
2. Run a repeatable 30-minute 1280×800 Gaming Mode route on battery and external power. Include movement, camera turns, region changes, inventory/dialogue, bank/shop, map and combat. Profile stalls and fix measured costs. Preserve the 60 FPS target, 50 Hz client logic and server timing; retain full traces and report loading stalls separately.
3. Verify Save & Quit, Continue, suspend/resume and controller reconnection across that session, with matching quest progress, XP, inventory and position after reload. Close the known native-writer quote/backslash serialization gap with round-trip regressions and verified backups.

## Completion criteria

A reproducible mouse-free Deck session completes a real quest and production/banking loop; it survives save/reload and suspend/resume with progress intact. Performance results report actual canvas/settings, frame-time tails, power conditions and any unresolved 60 FPS shortfall. Physical controller acceptance comes from the owner playtest, supported by independent native automation and trace evidence.

This document is a recommendation, not a claim that the new sprint has started or its acceptance has passed.
