# SoloScape — combined morning report, 8 October 2026

Both approved autonomous controller sprints are **implemented and verified** on
[overnight/controller-sprint](https://github.com/kannibalk1w1/SoloScape/tree/overnight/controller-sprint).
The first ran approximately 17:40–18:55 UTC; the second began at 19:02 UTC.
This report combines the earlier work with the new batch. The original report is
preserved in [MORNING_REPORT_SPRINT_1.md](MORNING_REPORT_SPRINT_1.md).

Your running game, cache, accounts, saves and local control preferences were left
alone. Public `main` remains at the earlier radial prototype, `07e789b`; these
changes are on the development branch for review and gameplay acceptance.
The local Orca checkout remains `soloscape/bootstrap`, tracking that branch.

## Current project state

SoloScape is an early playable, single-player-first revision-634 RuneScape project
built as patches over pinned 2011Scape/Void server and RuneLite-style client sources.
The intended direction is pre-EoC 2010–2011 gameplay with native controller input,
a console-friendly interface and Steam Deck support. The existing tile simulation,
600 ms server ticks, collision, combat, requirements and transactions remain authoritative.

You have confirmed local launch, camera panning, movement markers, improved aiming/
interaction and that optional direct movement feels good. The newer interface,
quick-action and production build has automated evidence but **has not been accepted
through physical gameplay**. There is no packaged release yet.

The public repository is maintainer-directed: feedback and agreed contributions
are welcome; scope and merges remain with the maintainer. Proprietary assets,
cache, saves, runtimes, credentials and jars stay outside the source repository.
The [cache guide](CACHE_SETUP.md) provides the upstream-maintainer source,
verified archive/checksum and installation steps. Launching does not fetch it.

## What both sprints delivered

| Area | First sprint | New sprint |
| --- | --- | --- |
| Reliability | Explicit matched-server opt-in; separate SDL/provider and native adapter recovery; cheaper idle snapshots; queued-tile cancellation; tick diagnostics; jar/patch fingerprints and retained logs | Regression coverage for pending/expired quick actions, stale items/permissions, production handoffs and obstacle targets; binding-overlap feedback |
| Banking and shops | Automatic focus, deposit/withdraw/buy/sell amounts, side inventory, control/tab panes, scrolling, note/swap/deposit actions, quantity-X and bank search | Preserved and included in the combined acceptance checklist |
| Equipment/prayer/spells | Native actions, equipment bonuses, all three spellbook groups, source/item/quantity/permission tokens, world/inventory target handoff and B cancel | Assignable prayer toggles and native immediate/targeted spells on a separate wheel |
| Quick actions | Proposed next step | Eight configurable slots on Start/Menu; explicit assignments; all slots start empty; native tab/render handoff; unavailable/cancel/timeout feedback; potion family/dose handling |
| Production | Number/text keyboard and native dialogue choices | Make-amount presets and displayed amount; smithing product/quantity rows; tanning, silver and jewellery options; Make-X keyboard handoff |
| Home tabs | Inventory/Equipment/Prayer/Spellbook controller handoff | Combat, Skills, Quests and supported Settings handoff, plus exposed actions on selected detail modals |
| Targeting | Safe selected spell/item dispatch, sticky selection, native revalidation | Attack/selected NPC spell selection across walking obstacles; dashed “server approach” footprint; bounded cycle set; failed/stale-action and cancel feedback |
| Readability/controls | Focus outlines, wrapped hints, controller keyboard and home wheel | 75–175% controller overlays, canvas-bounded keyboard/wheels/action menus, Xbox/PlayStation labels, three configurable auxiliary bindings, Reset/defaults and an optional guide |
| Delivery | Patches 0010–0013, three bounded Claude reviews, tests/builds, docs and previews | Patch 0014, Claude planning/review/follow-up, expanded tests, updated roadmap/handoff, new labelled previews and this combined report |

## How to use the new build

Quit the current game and launcher normally so their usual save/shutdown completes.
From this existing workspace, run:

```bash
./scripts/dev-run.sh --no-build
```

Both verified jars are ready:

- `upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar`
- `upstream/game-server/game/build/libs/void-server-dev.jar`

The ignored build stamp verifies the current jars and patch fingerprints. If a
jar/patch changes, run `./scripts/dev-run.sh` to rebuild. Fresh clones need the
[development setup](../README-SOLOSCAPE.md) and separate cache installation.
Use the **overnight/controller-sprint** branch to get these additions.

Enable **SoloScape Controller**; its interface controls and both wheels default on.
For direct movement, enable **Direct movement** and **SoloScape server features**.
The server-features setting defaults off and is intended only for this patched server.
With it off, ordinary destination walking/cancellation remains available.

| Context | Default controls |
| --- | --- |
| Home wheel | View/Select opens; stick/D-pad/LB/RB chooses; A opens; B backs out |
| Quick wheel | Start/Menu opens; stick/D-pad/LB/RB chooses; A uses; X assigns the action focused before opening; Y restores that slot to empty; B cancels |
| Bank/shop/production modal | D-pad focus/scroll; LB/RB pane; A native default; X quantities/actions; B action-list back, then close |
| Make-amount dialogue | D-pad recipe; LB/RB unlocked amount preset; prompt shows native amount; A makes the recipe; B closes |
| Focused home tab | D-pad moves; A selects/invokes; X alternatives; B returns to world |
| Selected world spell | Stick aims without walking; LB/RB target; A invokes; B cancels |
| Controller keyboard | D-pad key; A enters; X deletes; Y/Done submits; B native Escape |

**Quick assignment:** open Inventory with Y, or Prayer/Spellbook through Home.
Focus your food, potion, prayer or spell; use X's action list if you want a different
native action. Open Quick actions, highlight a slot and press X to assign it.
Then A can invoke that action once. Every slot starts empty; the first two labels
suggest food/potion but do not choose a consumable for you.

Potion bindings survive dose changes in the assigned name family and use the lowest
available dose. Whole-item food is easiest initially: partial cakes/pies that change
item ID require reassigning; the old binding safely reports unavailable. Prayers
toggle that same native prayer. Targeted spells select, then use the existing
world/inventory targeting controls. Missing items, wrong spellbooks, permissions,
changed widgets, cancellation and expired handoffs cannot fall back to another action.
No released quick-slot settings need migration; intermediate pre-review formats
are rejected by the first published version.

Plugin settings include **Quick-action wheel**, auxiliary Home/Quick/Inventory
buttons, **Controller overlay size**, **Button labels** and **Show controller guide**.
Choose three distinct menu buttons; overlap disables the wheels and shows feedback.
The plugin's Reset restores bindings and empty slots. Face actions within wheels
and keyboards stay A/B/X/Y (or their PlayStation equivalents).

## Combat and production decisions

The ten-tile Attack/selected-NPC-spell radius is a **selection radius**, not a
prediction of actual weapon/spell range or LOS. Up to six such targets enter
cycling. A dashed footprint says “server approach”: melee may walk around an
obstacle or receive the server's unreachable message. Native server combat retains
its actual approach/range/LOS rules. Talk-to, objects, ground items and selected
item-on-NPC keep the bounded five-tile walking check. No client combat simulation
or guessed collision flags were introduced.

Make-amount combines recipe dialogue 905 with native amount controls 916, keeping
recipe confirmation separate. Only unlocked 1/5/10/All controls are offered; no
zero-producing decrement shortcut. Smithing uses explicit pinned product/sibling
IDs, including irregular rows; A prefers one and X exposes five/X/all. Each actual
quantity button is revalidated separately before ordinary native dispatch.
Tanning/silver/jewellery preserve their native op permissions, product names and
server checks. Hidden/missing jewellery models suppress their quantity actions.
Cache/CS2 operation availability still needs in-game confirmation.

## Verification and Claude

- **121 client cases:** zero failures/errors; one SDL virtual-device case skipped.
  Client test and Shadow-jar build pass. This adds 21 cases to the first sprint's 100.
- **14 root tooling cases:** pass, covering patch/conflict handling, launcher
  lifecycle, stamps, retained logs and complete source export. Python compilation,
  ShellCheck, shell syntax, patch syntax and whitespace checks pass.
- **59 client / 14 server files:** the full modified source trees match reproduced
  patches. Fresh application, upgrade, reverse and repeated application pass.
  There are 14 client and three server patches.
- **Server evidence is unchanged:** its verified jar and earlier 247 network plus
  61 selected engine cases remain the evidence. Neither interface sprint changed
  server source or reran physical server acceptance.
- Actual native packets are checked: selected spell-on-NPC uses the pinned decoder
  layout; smithing uses the real sibling widget in the existing interface-op packet.
  Tests also cover permissions, hidden/replaced widgets, item changes, potion doses,
  no retry on rejection, timeout ordering, held-input handoff and obstacle targets.

Actual Claude performed **six bounded checks across both sprints**: three first-sprint
reviews, then a native planning audit, implementation review and follow-up. Its
medium first-sprint close-recovery finding and new unspecified-consumable finding
were fixed. The final follow-up reports no remaining blockers. Partial-food binding
changes are a documented fail-closed limitation. Reviews did not claim cache or
physical gameplay validation. The remaining five-hour allowance was not inferred.
Original records: [first reliability review](CLAUDE_RELIABILITY_REVIEW.md),
[bank/shop review](CLAUDE_BANK_SHOP_REVIEW.md),
[entry/selection review](CLAUDE_ENTRY_SELECTION_REVIEW.md),
[new planning audit](CLAUDE_SECOND_SPRINT_AUDIT.md),
[implementation review](CLAUDE_SECOND_SPRINT_REVIEW.md) and
[follow-up](CLAUDE_SECOND_SPRINT_FOLLOWUP.md).

Renderer previews were inspected at 765×503 and 1280×800, including 100/150% scaling.
[Quick wheel](images/controller-quick-wheel-preview.png) and
[scaled keyboard](images/controller-scaled-keyboard-preview.png), together with
[first bank](images/controller-bank-preview.png) and
[keyboard](images/controller-keyboard-preview.png), use plain backgrounds.
**These are renderer artifacts, not gameplay screenshots.** Native game UI text
itself is not rescaled.

## Morning acceptance list and remaining work

1. Banks/shops: 1/5/All/X, cancel/re-request, note/swap/tabs/search, large scrolling
   lists, mouse takeover and insufficient funds/stock feedback.
2. Quick slots: assign each kind; missing item/wrong book; two potion doses;
   pending cancellation; held A; one-slot/all Reset; partial-food fail-closed behavior.
3. Production: cooking/spinning/smelting/fletching amount presets; regular/irregular
   smithing rows and locked products; tanning/silver/jewellery; X entry and close/reopen.
4. Combat: melee/ranged/selected spell across obstacles, native approach/requirements,
   unreachable feedback, target cycling/despawns/re-selection and B cancellation.
5. Tabs and layouts: Combat/Skills/Quests/Settings; fixed/resized; mouse fallback;
   scaled overlays at 1280×800; remapped menu buttons, overlap warning, labels and guide.
6. Lifecycle: focus loss/reconnect; interface/plugin disable/re-enable; clean character
   save/restart verifying location, inventory, equipment, XP and quest variables;
   physical Steam Deck performance and suspend.

Bank PIN, niche/familiar/Dungeoneering interfaces, remaining home tabs, arbitrary
sliders/drag controls and text-only scrolling pages still need native input.
Quick special attacks, player/PvP/self/free-ground spell targeting, full remapping/
presets, first-run onboarding and automatic server capability negotiation remain
future work. The controller keyboard uses bounded printable ASCII. Client-opened
modal close behavior also needs a gameplay check; ignored close requests allow retry.

The next useful batch is **acceptance fixes, followed by save/launcher lifecycle
and Deck validation**. Bigger ambitions—solo content adaptations, original art/UI,
persistent AI adventurers, a local economy, selected backports and private co-op—
remain proposals requiring their own scope decisions. The full checkbox backlog
is [ROADMAP.md](ROADMAP.md); [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) is self-contained
for taking into ChatGPT alongside this report.

Turn off either wheel or Native interface navigation independently, or disable the
plugin to restore normal client input. Nothing was merged into public main, and
no game processes, cache, player files or saves were modified during these sprints.
