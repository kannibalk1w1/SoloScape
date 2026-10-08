# SoloScape — morning report, 8 October 2026

The planned autonomous controller sprint is **implemented, verified and pushed**.
Work ran from approximately 17:40 to 18:55 UTC. Gameplay acceptance remains open.
Your running session, accounts, cache and local control preferences were left alone.

Development branch: [overnight/controller-sprint](https://github.com/kannibalk1w1/SoloScape/tree/overnight/controller-sprint).
Implementation head: [`bb1aca0`](https://github.com/kannibalk1w1/SoloScape/commit/bb1aca03496fe5dbb95b2224f37e59484758aa81).
Public `main` remains at the previously published radial prototype (`07e789b`);
these changes have not been merged into it. The local Orca checkout stays on
`soloscape/bootstrap`, tracking the overnight development branch.

## What was completed

| Planned task | Result |
| --- | --- |
| Reliability review follow-ups | Explicit matched-server opt-in; separate SDL/provider and game-adapter recovery; cheaper idle inventory snapshots; queued-tile cancellation; optional poll/tick diagnostics; jar/patch fingerprints and previous-session log retention |
| Bank | Automatic focus, native deposit/withdraw quantities, side inventory, tabs/control pane, note/swap/deposit-carried/worn actions, spatial navigation and native scrolling; controller quantity entry and search |
| Shops | Stock, player inventory and controls panes; A chooses Buy/Sell rather than Info/Value; X exposes native quantities/actions; existing server messages provide transaction feedback |
| Equipment and prayer | Radial focus handoff, D-pad navigation, native remove/toggle/actions; equipment bonuses and side inventory panes |
| Spellbook and targeting | Modern/ancient/lunar actionable widgets, immediate casts and native selected targeting; source/item/quantity/permission/re-selection checks; eligible nearby NPC/object/ground and inventory targets; explicit B cancellation |
| Radial and hints | Inventory/Equipment/Prayer/Spellbook handoff; consumed input prevents held A from firing in the new screen; world movement pauses for selected aiming; UI camera input pauses; wrapped hints and a controller keyboard |
| Verification and delivery | Four implementation commits pushed; reproducible patch stacks, whole-tree export verifier, tests/builds, original Claude reviews, roadmap/handoff updates and labelled renderer previews |

The additions remain a patch layer over pinned revision-634 sources. Banks, shops,
prayers, equipment and spells use the native widget/menu/CS2 pipeline; their
transactions and requirements remain server-authoritative. This does not change
600 ms tile movement or add a new combat simulation.

## Commits

- [`daf577c`](https://github.com/kannibalk1w1/SoloScape/commit/daf577cba8d133dc09a6688addfeb7534b3a8124): reliability and matched-server guard.
- [`40cc0a0`](https://github.com/kannibalk1w1/SoloScape/commit/40cc0a0f0929dfc254787525ffc92f3b28330f9e): bank/shop focus, actions, panes and scrolling.
- [`237e5be`](https://github.com/kannibalk1w1/SoloScape/commit/237e5be526942f75fa8d25e76c6e2810ecd91224): controller keyboard and panel recovery.
- [`bb1aca0`](https://github.com/kannibalk1w1/SoloScape/commit/bb1aca03496fe5dbb95b2224f37e59484758aa81): equipment/prayer/spells, safe targeting, native hooks and complete export checks.

Client patches 0010–0013 contain the sprint. There are now 13 client and three
server patches. A broader export check caught omitted native hooks from the
intermediate export; 0013 includes them. The final full trees match the exported
stacks exactly, so fresh setup has the tested hooks.

## Checks and Claude review

- **100 client test cases:** zero failures/errors; one SDL virtual-device case skipped. Client Shadow jar passes. Physical SDL/Deck testing was not rerun in this sprint.
- **14 root tooling cases:** patch application/conflicts, launcher lifecycle, build stamps, retained logs and complete patch export; all pass. Python compilation, ShellCheck and whitespace checks pass.
- **53 client / 14 server source files:** full modified-tree comparison matches reproduced patches. Fresh/upgrade/reverse/repeated application pass, including real checkout idempotence.
- Existing unchanged-server evidence remains **247 network + 61 selected engine cases**, with its verified Shadow jar. No server code changed in this client sprint.
- The actual native spell-on-NPC packet is tested against the pinned decoder field layout: source widget/child/item and NPC identity. UI tests exercise quantity changes, permissions, hidden/replaced widgets, native scrolling, ignored-close recovery, held-input handoff and selection replacement.
- All four implementation CI runs passed; [latest implementation run](https://github.com/kannibalk1w1/SoloScape/actions/runs/37827141774).

Claude performed **three bounded, targeted checks**, conserving the reported
five-hour allowance instead of repeating the whole audit. The bank review found
a medium close-recovery issue; it is fixed. Redraw focus, item replacement,
search handoff and missing-test suggestions were also addressed. The final entry/
selection review found no blockers. Original records are retained in
[reliability review](CLAUDE_RELIABILITY_REVIEW.md),
[bank/shop review](CLAUDE_BANK_SHOP_REVIEW.md) and
[entry/selection review](CLAUDE_ENTRY_SELECTION_REVIEW.md).
Actual remaining Claude allowance was not measured or inferred.

Bank and keyboard renderers were inspected on plain backgrounds at 765×503 and
1280×800. [Bank preview](images/controller-bank-preview.png) and
[keyboard preview](images/controller-keyboard-preview.png) are renderer artifacts,
not gameplay screenshots.

## Try the build

Quit the current game and launcher normally, allowing the usual save/shutdown.
Then, from this existing workspace:

```bash
./scripts/dev-run.sh --no-build
```

The verified jars are:

- `upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar`
- `upstream/game-server/game/build/libs/void-server-dev.jar`

Their hashes and current patch fingerprints are recorded in ignored
`.runtime/build-stamp.json`; verification passes. If either jar or a patch changes,
run `./scripts/dev-run.sh` without `--no-build` to rebuild the pair. A fresh clone
also needs normal setup and the [separate cache download](CACHE_SETUP.md).

Enable **SoloScape Controller**. **Native interface navigation** defaults on.
To retain direct movement, enable both **Direct movement** and **SoloScape server
features**; the latter is a new opt-in, default off, for this patched server only.
With it off, ordinary destination walking/cancellation is used.

| Context | Controls |
| --- | --- |
| Radial | View/Select opens; stick/D-pad/bumpers choose; A opens; B cancels |
| Bank/shop/deposit box | D-pad moves; up/down at grid edge scrolls; LB/RB switches panes; A uses native default; X lists quantities/actions; B list-back, then close |
| Equipment/prayer/spell tab | Choose it on the radial; D-pad navigates; A performs/selects; X alternatives; B returns to world |
| Selected world spell | Stick aims without walking; LB/RB cycles eligible targets; A invokes; B cancels |
| Amount/name/search keyboard | D-pad chooses key; A enters; X deletes; Y/Done submits; B uses native Escape |

Bank tabs and deposit/note/swap buttons are in **Controls / tabs**. Search starts
only after the controller invokes Search; normal mouse/keyboard search keeps its
native behavior. Inventory-target spells retain their selection during tab handoff.
A source stack change requires B and re-selection. Ineligible targets never turn
A into an Eat/Drop action.

## First gameplay checks

1. Bank: withdraw/deposit 1, 5, All and X; cancel X and request another amount; test note mode, tabs, search/no matches/clear, a large scrolling bank and mouse scrolling.
2. Shop: buy/sell quantities, insufficient money, depleted/full stock and side-inventory focus. Check native message feedback.
3. Equipment/prayer: remove with a full bag, empty slots, open/close bonuses, prayer toggles and quick-prayer selection/confirmation.
4. Spells: immediate/home teleport; eligible NPC cast with enough and insufficient runes; an inventory spell; re-selection, item count changes, despawns and B cancellation. Check all available books.
5. Input lifecycle: hold A/stick when opening screens; radial → tab → world; focus loss/reconnect; fixed/resized layouts; disable/re-enable the interface setting; confirm mouse controls.
6. Save: clean exit/restart and verify location, inventory, equipment, XP and quest state. Then the Steam Deck checklist.

Pay particular attention to the native bank scrollbar thumb and focus flicker at
low frame rates. Automated bounds and frame checks do not establish their actual
in-game appearance.

## Limits and next work

Bank PIN and many special interfaces still require native mouse/keyboard input.
Only Inventory, Equipment, Prayer and Spellbook have radial controller handoff;
other home tabs, quick slots and remapping remain future work. The controller
keyboard is bounded printable ASCII. Player/PvP/self and arbitrary ground-tile
spell targets are not added. Nearby world targeting retains conservative approach
reachability; full combat range/line-of-sight policy remains a separate task.
Automatic server capability negotiation is also pending; the new flag is an
interim compatibility guard.

No character-save roundtrip or physical gameplay acceptance was claimed, no game
was launched/stopped, and no assets or saves were published. Changes can be reviewed
on the development branch before merging. Turn **Native interface navigation** off
to return the added interfaces to mouse/keyboard controls; turn **Tab radial menu**
off to remove the wheel, or disable the plugin to return to normal client input.
The original inventory/dialogue controls remain when interface navigation is off.

The proposed full project backlog is updated in [ROADMAP.md](ROADMAP.md).
[PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) summarizes the current state for ChatGPT.
The next useful step is the gameplay pass above, followed by fixes from that pass,
remaining high-use interfaces, readable scaling/quick actions and Deck lifecycle.
