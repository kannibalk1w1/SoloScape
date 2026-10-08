# Independent review of SoloScape controller and server work

Reviewer: Claude (Opus 5.5), 8 October 2026. This is a review only. I changed no
production code, patches, existing docs, config, cache, saves or processes, and
made no commits. The only file written in the repository is this document.
Everything under "Recommendations" and "Next batch" is a proposal and has not
been implemented.

Reviewed state: root `6cb9cf7` on `soloscape/bootstrap`; client base `297bc8a`
plus `patches/client/0001..0007`; server base `9f91135` plus
`patches/server/0001..0002`.

## 1. Scope and checks performed

**Read in full (real source, not only the summaries):**

- Client: `ControllerWorld.java`, `ControllerDirectMovement.java`, `ControllerUi.java`
  and `ControllerCamera.java`. The diffs to `GameClient.java`, `Applet_Sub1.java`,
  `Canvas_Sub1.java`, `Class325.java` and `Class348_Sub40_Sub7.java`. All of
  `net/runelite/client/input/controller/*` and `plugins/soloscapecontroller/*`.
  The world, direct-movement and world-action tests.
- Native client code needed to check the controller's assumptions:
  - the ground-item menu builder (`Class239_Sub24.java:256-290`);
  - the menu-entry constructor (`Class50_Sub3.method466`, `Class348_Sub42_Sub12`);
  - the dispatcher prologue (`Class325.method2599`);
  - the walk packet builder (`Class348_Sub14.method2807`);
  - the object tile lookup (`Class177.method1353`) and object identifier packing
    (`Class348_Sub40_Sub21.method3107`).
- Server:
  - `DirectMovementHandler.kt`, `CancelWorldActionHandler.kt`, `DirectMovementMode.kt`,
    the `Movement.kt` diff and the full `Movement.tick`/`step`/`nextDirection`;
  - the decoders, `Decoders.kt`, the `InstructionHandlers.kt` diff,
    `InstructionTask.kt` and the `LoginServer.kt` opcode loop;
  - content `Movement.kt` (the `instruction<Walk>` handler), `Energy.kt`,
    `Morphing.kt`, `Cutscene.kt`, `WeepingWall.kt` and the random-event
    `onExitInterrupt` users;
  - `Interfaces.closeInterfaces`, the `Player.mode` setter, the shutdown hook in
    `Main.kt` and `AutoSave.kt`;
  - the server SoloScape tests.
- Root scripts: `apply_client_patches.py`, `apply-client-patches.sh`,
  `apply-server-patches.sh` and `local_dev.py`.
- Docs: `PROJECT_HANDOFF`, `ROADMAP`, `CONTROLLER_DESIGN` and `CONTROLLER_TESTING`.
  For `KICKOFF`, only §4 (controller target) and §6.7–6.8 (client-side controller rule).

**Executed:**

| Check | Result |
| --- | --- |
| `:client:test`, **without** `-PcontrollerNativeTest` | 58 run, 0 failures/errors, 1 skipped (the SDL virtual-device test, skipped on purpose; see Limits) |
| `:network:test --rerun` and `:engine:test --rerun` with `*Movement*`, `*DecoderTest`, `*CancelWorldAction*` | 247 + 59, 0 failures/errors/skips (forced re-execution, not cached results) |
| Patch reproduction, independent | Extracted clean bases with `git archive` into scratch, applied every patch with `git apply`, and compared byte-for-byte with the live upstream trees: **37/37 client and 14/14 server files identical** |
| Two scratch-only probe tests (outside the repo, compiled against the built test classes) | Confirmed findings M2 and M3 below |
| Opcode collision scan of all 87 client `Class351` declarations | 85 and 86 are used only by SoloScape |

Not done: no game/server launch, no SDL native test (a physical pad may be connected),
no Deck hardware, no save roundtrip, no root Python tests re-run.

## 2. Findings, sorted by severity

Each finding is labelled **Verified** (a defect visible in the code, plus a probe where
noted) or **Hypothesis** (needs gameplay or further inspection).

### H1. World B (opcode 86) discards pending walk triggers, which can soft-lock a morphed player — Verified in code, high confidence

- **Where:** `engine/.../handle/CancelWorldActionHandler.kt:18` calls `player.clearWalkTrigger()`.
  The test `CancelWorldActionHandlerTest.kt:35` asserts this behaviour.
- **Why it is wrong:** content uses `walkTrigger` as "clean up on the next attempted
  walk". The ordinary Walk handler (`game/.../content/entity/Movement.kt:51-80`)
  **fires** it. `DirectMovementHandler` also fires it, correctly. Cancel silently drops it.
- **Trigger:** wear a Ring of stone or Easter ring (`Morphing.kt:15-35`). This sets
  `movementDelay = Int.MAX_VALUE`, opens the `morph` overlay tab and arms
  `walkTrigger { unmorph() }`. Press world **B**.
  - The trigger is discarded.
  - `closeInterfaces()` does not close the `overlay_tab`.
  - Later walks no longer unmorph, and movement stays blocked.
  - Only a mouse click on the morph tab's "Ok" button recovers, and controller
    UI cannot reach that tab yet.
- **Same pattern elsewhere:** Tears of Guthix (`WeepingWall.kt:36`, stuck lean
  animation/face), `Cutscene.onEnd` and the random-event `onExitInterrupt` exits
  (`RandomEventKidnap.kt:~100`). For random events, B also nulls the suspension, so the
  documented safety net ("the trigger re-queues the exit so the player is still sent
  home") is removed. That path is only reachable if B is pressed while the exit
  trigger is armed and no recognised dialogue is open. This needs a gameplay check.
- **Smallest fix:** replace `player.clearWalkTrigger()` with `player.walkTrigger()`,
  placed after `player.suspension = null`, which matches Walk. Change the test to assert
  that the trigger **runs once**. Add a test with a morph-style trigger. Update the
  handoff and design text that says B "removes pending walk triggers".

### M1. Opcode 86 is sent unconditionally and breaks the session on a server without the patch — Verified

- **Where:**
  - client `WorldControls.java:75-80`, which leads to
    `ControllerDirectMovement.cancelAction()` (`ControllerDirectMovement.java:37-45`);
  - server `LoginServer.kt:154-158`: on an unknown opcode it logs
    "No decoder for message opcode" and **returns**, so it stops reading that client's
    packets.
- **Trigger:** any controller client pressing world B against a stock 2011Scape server,
  an older SoloScape server jar, or a `--no-build` launch with mismatched jars.
  Unlike opcode 85, this is **not** behind the Direct movement toggle.
- **Impact:** the session silently stops accepting input. This also conflicts with
  KICKOFF §6.7: "Never create special server packets purely because an action came
  from a controller". The direct-movement exception to that rule was a deliberate,
  user-accepted decision. Cancel widened it without a recorded decision.
- **Smallest fix (pick one, then record it):**
  - (a) short-term: send 86 only when the user has enabled a "SoloScape server
    features" setting, and otherwise make world B do nothing or show a hint;
  - (b) preferred before M5: the server advertises a protocol version at login
    (for example a varp/varc). The client sends 85/86 only when that version is
    present and logs a clear message otherwise. Move ROADMAP M5-06 (reject
    mismatched builds) earlier, into the M0/M1 window.

### M2. LB/RB cannot reach pile entries beyond the 8th; "cycles all visible pile entries" is overstated — Verified by probe

- **Where:** `ControllerWorld.java:105-107`. At most 8 candidates (7 plus the retained
  one) are reachability-checked on each call, and cycling only rotates through that set.
- **Probe:** 10 different items on one tile. RB and LB each reached exactly 8 distinct
  items (`100..107`); `108` and `109` were never reachable. The existing test
  (`ControllerWorldActionsTest.java:43-54`) uses only 5 items.
- **Impact:** drops with more than 8 distinct item types (common for bosses, or
  several kills stacked on one tile) cannot be selected by controller. X/A on visible
  entries still work.
- **Smallest fix:** budget pathfinding per **distinct (tile, shape)** rather than per
  candidate. Cache the result within one `findTarget` call, so a whole pile costs one
  pathfind. Add a 10–12-item pile test. Correct the doc claim until the fix lands.

### M3. Eight closer unreachable candidates hide a reachable target — Verified by probe

- **Where:** the same budget, `ControllerWorld.java:105-108`. If the first 8 candidates
  sorted by score are all unreachable, the method returns `null` without examining
  the rest.
- **Probe:** an 8-item pile in an enclosed tile with a reachable item behind it gave
  `null`. With 7 enclosed items the reachable item was found.
- **Trigger in play:** loot or scenery behind a fence, a counter or a river, in a
  dense area. The player sees no gold target even though a reachable one is in the cone.
- **Smallest fix:** the same per-tile cache as M2. Keep scanning until one reachable
  target is found (or N for cycling) or a distinct-tile pathfind budget runs out
  (for example 8–12 tiles). Add the probe scenario as a test.

### M4. Any `RuntimeException` in game-adapter code permanently disables the controller with an SDL message — Verified (trigger is a hypothesis)

- **Where:** `SoloScapeControllerPlugin.java:157-162`. One catch block covers SDL
  polling **and** all of `ControllerWorld`/`ControllerUi`.
- **Impact:** a transient NPE or AIOOBE in world enumeration sets `failed = true`.
  The controller stays off until the plugin is toggled, and the warning tells the
  user to install SDL2.
- **Possible triggers:**
  - `ControllerWorld.reachable` dereferences `def` without a null check (`:276-279`);
  - the NPC table is used unguarded at `:268`.

  I did not find a definite reproduction.
- **Smallest fix:** keep the SDL init/poll catch as it is. Wrap the world/UI update
  separately: on an exception, call `resetWorld()` and `ui.reset()`, log at most once
  per few seconds with the real cause, and keep polling.

### M5. A UI snapshot is built every client tick, with regex and allocation, even when no UI mode is active — Verified in code; performance impact is a hypothesis

- **Where:** `SoloScapeControllerPlugin.java:145` runs `ui.update` every tick, which
  calls `ControllerUi.snapshot()` (`ControllerUi.java:65-90`).
- **Cost per tick:** for each filled visible inventory slot, `describe()` runs up to
  10 native label lookups, several `String.replaceAll` regex compilations
  (`ControllerUi.java:126`) and new arrays and `Rectangle`s. `hasDialogue()` builds a
  `HashSet` on every call, and `ControllerWorld.ready()` calls it many times per tick.
- **Other periodic work:** `findTarget` runs every 75 ms with up to 8 native BFS
  pathfinds. M2/M3 make this worse, because each item in a pile pathfinds to the
  same tile.
- **Impact:** this contradicts the design rule "Avoid per-frame log/allocation spam"
  and is untested on the Deck.
- **Smallest fix:**
  - precompile the tag-stripping `Pattern`;
  - snapshot only when inventory focus is active, Y was pressed, or a cheap
    open-group check finds a dialogue;
  - cache `openGroups()` once per tick;
  - add timing counters behind the diagnostics setting before M4 measurements.

### L1. Dialogue B walks to the *rendered* tile, not the server-confirmed tile — Hypothesis

- **Where:** `ControllerUi.java:218-219` uses `p.x >> 9, p.y >> 9`.
  `ControllerWorld.reachable` uses `anIntArray10320[0]`/`anIntArray10317[0]`, the
  path head.
- **Trigger:** a dialogue opens while the player is still interpolating a step, for
  example an NPC-initiated or random-event dialogue.
- **Impact:** if the rendered tile lags, the Walk target is not the server tile. The
  server then walks one tile back instead of doing a pure cancel.
- **Fix:** use the path-head coordinates.

### L2. Destination-mode projection starts at the rendered tile, while reachability and the server use the path head — Hypothesis (user reports good feel)

- **Where:** `ControllerWorld.java:66-69`.
- **Effect:** with gentle tilt while moving, a 1-tile projection can equal the
  server's current tile. The Walk handler then sets `EmptyMode`, which could cause a
  micro-stutter.
- **Action:** investigate only if stutter is observed. The fix would be to project
  from the path head.

### L3. Direct movement bypasses the content Walk handler's `border` passages — Hypothesis

- **Where:** `game/.../content/entity/Movement.kt:43-74` forces a no-collision crossing
  of areas tagged `border`:
  - the border guards between Edgeville/Varrock, Al Kharid/Varrock, Draynor/Port Sarim
    and others;
  - the Isafdar tripwires and traps.

  `DirectMovementMode` never reaches that code. Destination mode clips with client
  collision first.
- **Check in play:** walk through `border_guard_edgeville_varrock` (3138–3139,
  3466–3468) with the stick in both modes. If blocked, either route direct intent
  into the border handler or document "use mouse/minimap here".

### L4. "Run preference preserved" is only true above zero energy; direct mode ignores the run toggle — Verified, documentation/UX

- `DirectMovementMode.shouldRun` (`:77`) uses stick magnitude only, so with the run
  orb on, a gentle tilt still walks.
- At 0 energy, `Energy.walkWhenOutOfEnergy` (`Energy.kt:78-80`) sets the preference to
  walk. That is normal RuneScape behaviour, but the docs imply the preference is never
  touched.
- **Action:** clarify the docs. Optionally, let full tilt mean "use the run
  preference" in a later UX pass.

### L5. Validation counts and hygiene — Verified

- **Duplicated tests in the count:** `ControllerWorldActionsTest extends ControllerWorldTest`
  (`ControllerWorldActionsTest.java:9`), so the 3 inherited tests run twice. The
  reported "58 client tests" are **55 distinct test methods**. Prefer composition, or
  report distinct methods.
- **Partly staged index:** the upstream client index is partly staged. `git diff --cached`
  shows 15 files and the unstaged diff 7. Reproduction is still exact, but anyone
  regenerating a patch with plain `git diff` would silently miss staged hunks.
  `git diff HEAD` is the safe form; ideally keep the index clean (an unstaged
  working tree only).
- **Launcher logs:** `.runtime/server.log` and `.runtime/client.log` are truncated on
  every launch (`local_dev.py:162`), which loses the previous session's crash evidence.
  Rotate one previous copy.
- **`--no-build`:** this path (`local_dev.py:141-148`) does not check that the jars
  match the current patch stack. That is the most likely route to the M1 mismatch.
  A small stamp file written at build time (patch hashes) and checked at launch
  would catch it.

### L6. Cosmetic — Hypothesis

`ControllerWorld.markDirectDestination` (`:57`) writes the native minimap-flag globals
(`Class248.anInt3203`/`Class97.anInt1548`). `ControllerDirectMovement.stop()` clears
only the overlay marker. The minimap flag may linger one tile ahead after release or
a blocked step. Separately, the server slides along an axis when a diagonal is
blocked (`Movement.nextDirection`), but the client marker clears on a strict diagonal
check, so the green tile can vanish while the character still moves.

### Design gaps worth knowing (not defects)

- **Combat targeting:** focus requires a target within 5 tiles **and** a native walk
  path of at most 8 steps to an adjacent tile (`ControllerWorld.java:263-299`). With
  ranged or magic, the player cannot target an NPC across an obstacle (safe-spotting)
  or further than 5 tiles away. M1-07 and the combat work need a separate attack
  targeting policy based on line of sight and attack range.
- **NPCs behind counters or booths** (shopkeepers, bankers) may fail the
  adjacent-path check and never become focusable. This is a hypothesis, cheap to
  check in M0 and important before M1-01/M1-03.
- **Other side effects of world B:** it closes any open bank or shop interface and
  stops combat (`CombatMovement` is a `Movement`). This matches ordinary walking and is
  fine, but the docs should state it.

## 3. Areas reviewed and found sound

- **Packet ordering and ownership.**
  - `stop()` is idempotent and sends `(0,0)` at most once.
  - Held A, B and X send the stop **before** the interaction or cancel packet in the
    same frame (`WorldControls.java:110-113` runs before the A branch).
  - The server's late stop clears only `DirectMovementMode`, so a newer mouse walk or
    interaction survives.
  - Neutral input calls only no-op paths: there is no packet spam.
- **Protocol compatibility on a matched build.**
  - Opcodes 85 and 86 are not used by any stock client packet.
  - Fixed sizes 3 and 0 match the decoders.
  - Signed bytes round-trip.
  - Malformed vectors decode to `null`, and the read loop then continues safely.
- **Direct movement timing.**
  - The 200 ms heartbeat sits well inside the 750 ms expiry.
  - The instruction channel (capacity 20, drained up to 20 per tick) handles about 3
    heartbeats per tick.
  - A delayed queue cannot restart movement.
- **Direct movement collision.** Collision, `movement_delay`/`delay`, the viewport
  gate and visual updates all reuse `Movement.tick`. Mode replacement clears steps
  safely, because the replacement computes its route lazily in `tick`. Energy drain
  keys on `visuals.runStep`, so full-tilt running does drain energy.
- **Native mappings.**
  - Ground-item ops `21/10/47/22/5` match `Class239_Sub24.java:276-283`.
  - The pile index the native builder stores (`aLong9600`) is not read by the
    dispatcher, so leaving it at 0 is harmless.
  - `Class177.method1353` returns interactive objects only at their origin tile, so
    large objects are not duplicated.
- **Input lifecycle.**
  - The neutral, face-button-released `armed` gates cover focus loss, disconnect,
    reconnect, mode toggles, UI hand-off and stale menus.
  - The `blocked` flag after a mouse menu action clears only on neutral input.
  - Plugin shutdown sends the stop on the client thread.
- **Camera.** It is additive, units are consistent (16384 per turn), and it is gated
  on login and scripted camera states.
- **Patch tooling and launcher.**
  - The patch script validates against a disposable copy, refuses conflicts and
    rejects unsafe paths.
  - Reproduction is exact (independently re-checked).
  - The launcher terminates only process groups it owns, never with SIGKILL.
  - The server shutdown hook calls `World.shutdown()`, which awaits in-flight saves.
    That makes the lifecycle *plausible*, but it is not yet proven by a roundtrip.

## 4. Test coverage gaps

1. **Walk-trigger semantics:** no test that cancel and direct movement fire, rather
   than drop, `walkTrigger` (H1). The existing test locks in the defect.
2. **Pile and target budget:** no pile larger than 8 and no starvation scenario.
   Add both, as in M2 and M3.
3. **Plugin arbitration:** no test of `SoloScapeControllerPlugin.onClientTick`
   ordering (UI before world, focus/disconnect reset, the failure path). M4 is
   untested.
4. **Server interface closing is mocked** in the cancel tests. Add one engine or
   game-level test with real `closeInterfaces` covering a dialogue and a `wide_screen`
   menu. Better still, a game-module test that sends `CancelWorldAction` through the
   real instruction pipeline.
5. **Protocol mismatch:** no test or documented behaviour for an unpatched server
   receiving 86 or 85.
6. **No content-level direct-movement test** for border passages, doors or agility
   shortcuts (`delay` gate), or run energy reaching 0 mid-run.
7. **Dialogue B while moving** (L1) and destination-mode stutter (L2) need either a
   pathing-state unit test or a gameplay check.
8. **The SDL native test** needs "no physical gamepad connected". That makes it
   environment-sensitive. Consider filtering to the virtual device's GUID.
9. **No performance measurement** of `snapshot()` or `findTarget` (M5).

## 5. Architecture and roadmap recommendations

1. **Record the protocol decision.** Write down a short "SoloScape server protocol
   extensions" note: opcode list, version, capability negotiation and fallback.
   KICKOFF §6.7 says otherwise, so the exception should be explicit. Move M5-06 ahead
   of M1.
2. **Add the H1 fix plus these checks to M0 acceptance:**
   - morph ring followed by B;
   - a pile of more than 8 items;
   - talking to a banker or shopkeeper across a counter;
   - crossing a border-guard area with the stick in both modes;
   - B in a dialogue that opened mid-walk.
3. **Before M1-07 (quick slots, combat):** define attack targeting separately from
   the walk-reachability rule: attack range, line of sight, and possibly a
   screen-space or reticle factor (KICKOFF §4.4).
4. **Before M4 (Deck):** add cheap timing counters for controller work behind the
   diagnostics flag, so Deck measurements can attribute cost.
5. **Patch hygiene:** keep the upstream index clean. Optionally add a
   `scripts/verify-patches` that runs the scratch reproduction check I did, and use it
   in place of the prose claim.
6. **Validation wording:** report distinct test methods, state which tests were
   skipped, and give the "cycles all pile entries" claim a stated bound until M2 is
   fixed.

## 6. Recommended next small batch (in order, each independently reversible)

1. **Server:** fire rather than clear `walkTrigger` in `CancelWorldActionHandler`, and
   update its test. This is about 3 lines plus a test.
2. **Client:** per-distinct-tile reachability cache and budget in
   `ControllerWorld.findTarget`, plus tests for the >8 pile and for starvation.
3. **Client:** split the plugin's exception handling (M4), and use path-head
   coordinates for dialogue B (L1).
4. **Client and server:** gate 85/86 on a server-advertised capability, or as an
   interim step a setting. Add a jar/patch stamp check to `--no-build`.
5. **Client:** cheap `snapshot()` gating and a precompiled regex (M5).
6. **Then run the M0 in-game acceptance**, including the extra checks in §5.2 and a
   real save roundtrip.

## 7. Limits

- **No gameplay:** I did not launch the game or server. Every gameplay impact above
  comes from code reading or a unit-level probe. The morph soft-lock follows directly
  from the code but was not reproduced in-game.
- **SDL test not run:** I skipped the SDL virtual-device test on purpose, because a
  physical pad might be connected and the previous agent's native result might not
  reproduce. I did not re-run the root Python patch and launcher tests.
- **Partial reading:** I did not audit the full UI navigation edge cases (resized
  layouts, every dialogue group) or every native action ID for objects and widgets
  beyond the ground-item builder and what the existing tests cover. I also did not
  read the full combat code or all of KICKOFF.
- **Steam Deck:** Deck performance, Steam Input device selection (SDL may see both
  Steam's virtual pad and the raw device) and suspend behaviour remain unverified.
