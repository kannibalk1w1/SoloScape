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

## Launcher keyboard ownership acceptance

- [ ] New Character automatically opens Steam keyboard in Deck launcher; one selected key inserts exactly one character.
- [ ] Enter moves label → account → Create; the same held A cannot create a character.
- [ ] From Create, controller traversal can return to either field; A opens typing, without a trapped auto-open loop.
- [ ] Steam + X reopen/dismiss and tapping controls preserve entered values.
- [ ] Selecting local fallback after closing Steam keyboard makes D-pad change selected key without moving the caret.
- [ ] Main character list D-pad changes one row per press; confirm acts once.
- [ ] Desktop keyboard navigation disables competing launcher SDL; USB/Bluetooth keys work.
- [ ] Repeat in Gaming Mode; record Steam Input layout and focus behavior.
- [ ] Later: apply/accept the same exclusive ownership for every in-game entry (parked roadmap task).
