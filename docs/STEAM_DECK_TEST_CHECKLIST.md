# Linux / Steam Deck acceptance

Prerequisite and build checks pass. No gameplay/hardware acceptance has run.

- [x] Doctor passes with JDK 21 + JDK 8 and authorized upstream cache.
- [x] Unmodified server/client build successfully at recorded pins.
- [ ] `dev-run.sh` waits for loaded world, then opens the localhost client.
- [ ] New local account can be created; no official server connection occurs.
- [ ] Record inventory, bank, skill XP and position; logout/quit cleanly.
- [ ] Restart, log in to the same account and confirm recorded state.
- [ ] Repeat with Ctrl+C shutdown; check logs for save errors.
- [ ] Client failure/server failure cleans up the other owned process.
- [ ] Steam Gaming Mode opens the application at 1280×800.
- [ ] Software renderer works; test OpenGL separately.
- [ ] Controller identity/mapping detected; hotplug/unplug does not crash.
- [ ] Right stick rotates/pitches with configurable deadzone.
- [ ] Left stick walks through existing pathfinding without oscillation.
- [ ] Deadzone stops new walk destinations; evaluate queued-path stopping.
- [ ] Focus label is visible and A invokes normal NPC/object interaction.
- [ ] Inventory focus navigates slots and activates normal item actions.
- [ ] Keyboard/mouse/trackpad work alongside the controller.
- [ ] Disabling controller support restores baseline input behaviour.
- [ ] Later: dialogue, bank/shop, UI scaling and suspend/resume.
- [ ] Later: two independent persisted accounts on one LAN server.
