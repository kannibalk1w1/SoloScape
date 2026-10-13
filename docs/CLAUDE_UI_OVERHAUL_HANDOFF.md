# Claude ownership handoff — full OSRS / RS2 UI overhaul

User request: "I want you to pass to claude to do a full UI overhaul, make it OSRS/RS2 themed and as close to 'jagex style' UI as possible."

Take ownership of the implementation in this existing checkout. This is a full handoff, not a request for a proposal or supervised task. Codex stops work after delivering this brief. Work autonomously through the implementation, appropriate validation, visual review and a reviewable result. Do not wait for Codex to continue.

Workspace: `/home/kannibalkiwi/orca/projects/SoloScape`.
Orca worktree ID: `38a470ad-5408-43c7-a12e-0d33666ec14d::/home/kannibalkiwi/orca/projects/SoloScape` (main).

## Desired design

Overhaul the SoloScape launcher and the custom controller UI throughout the game: inventory, equipment, bank, shop, quests/journal, skills, combat, prayer, spellbook, settings/setup, Home and quick-action radials, text entry, confirmation/amount/production dialogs, world/loot action menus and controller HUD/hints. Audit every reachable SoloScape-owned surface and make it coherent.

The user wants recognizable OSRS / classic RS2 / Jagex-style presentation, as close as practicable to the original UI. Treat the original game as the visual reference, not a generic modern dark dashboard with gold accents. Study existing native panels, fonts, item artwork and established assets. Reuse or faithfully match stone frames, bevels, parchment/brown panels, classic borders/buttons, appropriate pixel/bitmap typography, iconography, spacing and selected/disabled states. Keep text legible at Deck sizes, respect scalable/fixed/resized/fullscreen layouts and maintain controller, keyboard and mouse usability. Add meaningful, consistent feedback without exposing implementation jargon. Use existing art where possible; keep proprietary cache/game resources out of tracked source.

The launcher already uses the original mirrored brazier half-scene, stored privately at `.runtime/launcher-art/brazier.jpg`. `scripts/setup_launcher_art.py` downloads and verifies that original RuneLite background for fresh owner workspaces, and the private exporter includes it. This is a starting point, not the completed overhaul. Preview of the present launcher: `.runtime/launcher-tests/1791882924034896483/launcher-scene.png`.

Preserve gameplay and save behavior while changing presentation. Preserve the reversible custom/native UI settings and native permission/action validation. Keep health bars and the world readable; do not restore floating action text above the target's head. Do not reintroduce "server approach", "move into range", or server approach/range jargon in HUD/action feedback: the user explicitly asked for its removal. Existing native game interfaces need integration/restyling only where it is appropriate and reversible; do not break their scripts or controller ownership.

## Baseline and important safeguards

This checkout deliberately contains substantial uncommitted earlier work plus the latest playtest fixes. Inspect `git status` and preserve ALL of it. Do not reset, clean, discard, overwrite patch stacks, or replace these changes with a checkout from main. The ignored `upstream/` repositories contain the actual modified client/server source; the tracked root patch stacks are the reproducible deliverable. A fresh worktree would omit this state, which is why Claude is being launched here.

Read `README-SOLOSCAPE.md`, `docs/PLAYTEST_2.md`, `docs/PLAYTEST_FOLLOWUP.md`, and the relevant architecture/controller presentation guides. Preserve prior FPS/fullscreen/save-sync work too. Current client patches run through `0041-remove-approach-wording.patch`, server through `0018-player-lit-fire-use.patch`. Add subsequent incremental patches; ensure ALL modified/untracked upstream source is reproduced by the stacks.

Latest playtest behavior to retain:

- Custom inventory skips empty slots through spatial occupied-item navigation; native inventory retains its grid behavior.
- Horizontal right-stick camera direction is reversed; vertical camera/menu scroll directions stay as before.
- Target action prompts live in the corner HUD. X on ground loot browses the whole pile, including items beyond the three visible models, with a selected-row window and live validation.
- Launcher World Settings configure per-world XP/drop multipliers and unlimited run energy. Rates are server settings supplied by the launcher at startup, default to 1x, and survive backup/restore/recovery/manual save transfer. Running or unrecovered sessions cannot be reconfigured. Drop rates affect weighted chances, not item stack quantities.
- Matched server advertises `fire-use` through a fresh nonce capability reply. Reply is sent as ONE UNSPLIT native game message, bypassing font line wrapping. Client exposes native Use for the six player-lit fire definitions only with that capability; server validates and runs its existing recipe/cooking flow.
- Blood Pact revealed a general renderer state bug: native widget models overwrite scene camera/viewport before overlays project world geometry. `ControllerProjection.java` captures the real scene matrix/viewport/clip in `OutputStream_Sub1.java`, uses that snapshot in `Applet_Sub1.projectLocalToCanvas`, and restores renderer state afterward. Renderer identity, region base and player plane are checked. Preserve this general fix, not a quest-coordinate workaround. Player tiles also render without a destination marker.

## Files to start with

Client source is under `upstream/runelite-client/client/src/`:

- `net/runelite/client/soloscape/launcher/SoloScapeLauncher.java`, `LauncherScene.java`, `LauncherKeyboard.java`.
- `net/runelite/client/plugins/soloscapecontroller/ControllerTheme.java`, all `SoloScape*Overlay.java`, `ControllerGlyphs.java`, `ControllerHints.java`, `SoloScapeControllerConfig.java`, `SoloScapeControllerPlugin.java`.
- `net/runelite/client/input/controller/PanelPresentation.java`, `UiControls.java`, `PanelControls.java`, `EntryControls.java`, Home/quick/tab-radial/settings classes.
- Native adapters `ControllerUi.java`, `ControllerPanelDetails.java`, `ControllerAdventureDetails.java`, `ControllerItemImages.java`, `ControllerWorld.java`, `ControllerProjection.java`.

Launcher backend/profile settings live in root `scripts/launcher_backend.py`, `profiles.py`, `profile_session.py`. Preserve their ownership locks, private profile isolation and validated save lifecycle.

## Validation and delivery

Current matched jars/build stamp are valid. Latest client regressions: 230 cases, zero failures/errors, one optional SDL skip. Root tooling: 99 passing tests. Selected server cooking regression: four passing cases. Final native fixture `.runtime/alpha-tests/session-1791883660474975411/` verifies actual tinderbox/log fire lighting, Use Fire cooking (raw food consumed; cooked shrimps increased 1 -> 2), Blood Pact instance plane-1 tile polygon, player tile rendering without a destination (2069 pixels), direct destination, New/Continue/save integrity, four verified backups and whole-world startup cancellation. Launcher native probe verifies world settings persistence and character keyboard ownership. These are controlled native/virtual-display checks, not physical Deck acceptance or a full quest playthrough.

Use the project's build locks and JDK setup (`config/local.env`, local JDK 21 build/server and JDK 8 client). Re-export new source patches and run:

- `python3 scripts/verify_patches.py client` and `python3 scripts/verify_patches.py server`.
- Appropriate client tests/build and matched build stamp refresh. Root tests when changing backend/tooling.
- `python3 scripts/smoke-launcher.py` for real launcher forms/layout/backend.
- `./scripts/smoke-profile.sh --playtest-two` when checking world projection/fire integration. This creates an isolated admin fixture only; do not enable admin rights in normal profiles.
- Appropriate existing visual preview/native UI probes for the overhauled panels, including Deck-sized layouts, long labels, dense grids, focus/navigation, empty states and modal ownership. Inspect rendered screenshots rather than treating successful compilation as visual acceptance.

Avoid unnecessary repetitive or prolonged tests for cosmetic-only changes. Do perform checks needed to validate changed behavior and inspect the final visuals. Keep user saves/cache untouched. The installed Deck shortcut is older; the new source candidate has not been promoted or deployed to Deck. Do not claim deployment or physical acceptance without actual evidence.

Deliver the complete UI overhaul with screenshots/previews, clear validation evidence and a concise explanation of changes/remaining limitations. Continue the work rather than stopping after a design plan.

## Additional owner requirement — D-pad tab-bar focus

The owner subsequently requested left/right D-pad navigation of the native
bottom-right UI slots (inventory, settings, skills, etc.). Implement this as part
of the overhaul:

- With world input active and no menu/modal/keyboard focus, a left/right D-pad press
  enters tab-bar focus and visibly highlights an available slot. Subsequent
  left/right presses cycle the slots in their native visual order.
- Cycling only moves the highlight; it does not open tabs automatically.
- While the bar owns focus, A cannot invoke a world action. A is exclusively the
  fresh confirm press that opens the highlighted tab. Ignore simultaneous/held A
  during a direction press, so entering/cycling cannot accidentally confirm.
- B deselects and returns to world input. B from a tab opened through this flow
  should also leave its controller UI focus and return to world input, without an
  extra tab-bar escape step. Preserve necessary nested/modal cancellation.
- Preserve existing D-pad behavior inside inventory, panels, dialogue, loot menus,
  radials and keyboards. Respect available/hidden tabs, button remaps, lifecycle
  gates and neutral rearming so returning to the world does not leak held input.

The phrasing "A is disabled whilst cycling" is interpreted as disabling its world
interaction role while the tab bar is focused, with A remaining the explicit tab
confirm control. This matches the owner's request that A opens the selected slot.
