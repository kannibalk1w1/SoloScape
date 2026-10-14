# Controller panel lessons, 14 October 2026

Worker: Claude Sonnet 5.5 (`claude-sonnet-5-5`) for everything; no Opus, no Haiku, no sub-agents. Baseline: PR #21 at `7ab5801` (client 0052 / server 0022). New tracked patch: `patches/client/0053-shop-stock-boxes-in-controller-panel.patch`. All evidence is host evidence (private Xvfb 892×529, software renderer, synthetic pad through the plugin's own input tick, disposable AlphaTest profiles); none of it is physical Deck evidence.

## Findings

| Overnight finding | Real cause | Where fixed |
| --- | --- | --- |
| Shop panel exposed zero stock | **Real adapter fault.** Stock entries are an item-less click box (ops Info/Buy 1/5/10/50/500/Examine, or Take for free samples) with the item graphic drawn *inside* it. `ControllerUi.panel()` treats any child widget without an item as an empty slot and dropped every box. The sell side worked because inventory slots own their items. Not a pane-name issue. | Client 0053 |
| Pad B did not close cooking dialogue 905 | **Probe bug, not a product fault.** `NativeBloodPactProbe` called `neutral()` right after `production()` set the B hold, so the press never reached `input()`. A trace of raw/mapped pad state showed only A/X/trigger edges and no B. With a one-tick B pulse, the first pad B closes the menu (raw chicken 4 → 4, nothing cooked). No product change needed. | Probe only |
| "Settings disappeared on second tick" (`--adventure`) | **Harness artifact, not fixed.** The probe calls `ui.update` itself; the plugin's own tick runs between probe ticks with no pad connected (`padConnected=false`) and, by design, resets UI ownership every tick. Native panel 261 is present and the canvas has focus. It is *not* the B cause. Pad-driving probes avoid it by scripting `rawState` and calling the plugin's process step. | Diagnostics only (failure message now reports settingsOpen/focus/native panel/pad) |

## Shared contracts (corrected)

1. **Panel items are found by actions and geometry, not by names.** A panel widget with operations but no item is valid when an item-bearing sibling of the same component is drawn inside its bounds (`ControllerUi.stockItem`). The model shows the stocked item (id, name, quantity) with the box's own native actions. Dispatch is unchanged: the packet is the same one a native click sends (widget `620:25`, item `ffff` because the box owns none, slot = box child; the server derives the item from `slot / 6`). Free samples (`620:26`) use the same shape with Take actions.
2. **Probes must never assert on a cosmetic pane name.** The strict probe now looks for `Buy 1` in any pane that is not `Inventory`.
3. **A scripted pad press is a pulse.** Anything that sets `held` for one action must let `input()` run once with it and release on the next tick; a wrapper that calls `neutral()` after a helper silently cancels the press. Each UI re-arm still needs a neutral beat first.
4. **While a shop is open, the inventory tab is not drawn.** Count what the player holds from the shop's side-inventory pane (`heldSide`), never the hidden tab (`heldIn`); counting the tab made a successful purchase look like a failure.
5. **No masking.** `b_cancel_gateway_fallback` and `buy_blocked` no longer exist: B failing or no purchase now fails the probe. `verify_shop_save` now takes the bought item and the run fails unless the saved inventory contains it; the probe buys an item the starter kit lacks (Jug, then Shears/Bowl/Cake tin/Chisel) so the save proves it.
6. Sell invoke results are honoured and retried within the stage limit (`sell_rejected` is counted) instead of being assumed.

## Repeatable acceptance

Preserved by construction: neutral-stick release-and-push, fresh A/B gates (`ControllerUi.invoke` still re-reads and compares the fresh widget, including quantity), native item identities, world rates, owner saves (disposable profiles only).

```sh
export $(grep -v '^#' config/local.env | xargs)
python3 scripts/verify_patches.py client   # 138 files match (0053 included)
python3 scripts/verify_patches.py server   # 60 files match
scripts/smoke-profile.sh --shop-trade      # sell a dagger, buy a Jug, both saved and reloaded (~3 min)
scripts/smoke-profile.sh --gather-cook     # earned fire; B closes menu 905 with 4 raw chicken kept; cook/burn (~8 min)
scripts/smoke-profile.sh --adventure       # still stops at the documented Settings harness artifact
cd scripts && python3 -m unittest discover -p 'test_*.py'
```

Client suite via gradle `:client:test` (under `.runtime/build.lock`): 252 tests, 0 failures, 1 optional SDL skip. New regressions in `ControllerUiTest`: stock boxes become stocked items with native Buy actions; boxes with the graphic outside them or with no item stay inert; the purchase packet matches a native click. Tooling: `test_strict_shop_save_needs_the_purchased_item`.

## Evidence (reviewed)

- `docs/evidence/panel-lessons/shop-stock.png`: the real Lumbridge general store after the sale. The hint bar now names the focused stock entry ("Shop / Stock · [A]: Take 1 Tinderbox ×1"); 3 free samples and 13 stock entries are visible and exposed.
- `docs/evidence/panel-lessons/shop-trade-native.json`: coins 0 → 4 (dagger sold) → 3 (Jug bought); saved world contains Jug and coins after Continue.
- `docs/evidence/panel-lessons/gather-cook-pad-b-native.json` and `cooked.png`: pad B pressed once in the cooking menu with 4 raw chicken, 4 after; no `b_cancel_gateway_fallback`, no second press; cooked and burnt chicken saved with XP.

## Remaining risks

- Physical gamepad, Steam Input and Deck hardware were not exercised. Synthetic pad input proves the plugin path only.
- The custom (overlay) shop presentation (`PanelPresentation`, `customShop`) was not driven with stock; the native stock model is now correct for it to consume.
- `--adventure` still fails at the Settings step for the harness reason above; a proper fix is to drive that step through the plugin's process step with a scripted pad.
- Buying uses `Buy 1` only; multi-quantity buys and the Info side panel were not covered.
