# Controller reliability batch: second review

Scope: `patches/client/0010-controller-reliability.patch` and the uncommitted
`scripts/local_dev.py` / `scripts/test_local_dev.py` diff. This was a static review only. I
built nothing, ran no tests and did no gameplay acceptance. Client line numbers refer to
`upstream/runelite-client/client/src/` with the patch applied.

## Verdict

**No blocking findings.** Every change below matches the stated intent. The non-blocking items
are small hardening fixes and cheap tests.

## What I checked and found correct

- **Opcodes 85/86 gated.** `ControllerDirectMovement.update` stops before it sends anything when
  `serverFeatures` is false (line 22). `stop()` sends the direct stop only when `serverFeatures`
  is true. `cancelAction` falls back to `ControllerUi.cancelWorld()` before it builds `CANCEL`
  (line 47). The config defaults to `false`. The plugin also ANDs `directMovement && serverFeatures`.
- **Opt-out sends exactly one stop.** `enableServerFeatures(false)` calls `stop()` while the flag
  is still true, then clears it. After that, `direction == -1`, so the per-tick re-assert and
  `world.update(..., false)` send nothing more. `disablingServerFeaturesStopsTheExistingIntentOnce`
  covers this. `reset()` runs on the client thread from both `startUp` and `shutDown`
  (`clientThread.invoke`), so the packet is not sent from another thread.
- **Walk fallback to the path head.** `ControllerUi.java:260` uses `anIntArray10320[0]` /
  `anIntArray10317[0]`, the server-authoritative tile. The old `p.x>>9` could lag by one tile
  mid-step. `cancelWorld` keeps the `ready()` guard. The new test checks for one walk packet and
  the head coordinates.
- **`hasDialogue` makes no allocation.** It uses the same native cursor iteration as
  `openGroups()` and `isVisible()`. None of those three runs nested inside another, so the
  shared cursor is not clobbered. Null-table guard is present.
- **Idle snapshot.** `inventoryVisible` is still computed from the open group plus root
  visibility, not from the slots, so `hasInventory()` stays correct when `describe` is skipped.
  `UiControls.update` (line 59) asks for inventory on a Y press or while inventory mode is on.
  The Y-press tick therefore gets a full snapshot, and `selected()` reads slots only when
  `inventory` is set. `invoke()` re-validates through `fresh()` + `describe()`, so idle snapshots
  add no stale-widget risk.
- **Reachability null guards** (`Class282.aClass356_3654`, `def`) fail closed.
- **Provider vs adapter failures.** Adapter `RuntimeException`s reset intent, keep the device and
  rate-limit the log to once every 5 s. Provider (SDL) failures still set `failed` and need a
  toggle.
- **Launcher.** The stamp is written after a successful build and verified with `--no-build`.
  JSON is written to a temporary file and then renamed into place. Logs are rotated under the
  launcher lock before the child processes start, and the `"w"` opens plus zero offsets stay
  consistent. Tests cover a jar change, a patch change or addition, a missing or broken stamp,
  and log rotation.

## Non-blocking findings (smallest fixes)

1. **Idle snapshot shares a public mutable array.** At `ControllerUi.java:84`, an idle snapshot
   returns `UiState.EMPTY.inventory`, a public, writable `Widget[28]`
   (`UiState.java:8`). Any future consumer that writes a slot would corrupt `EMPTY` for every
   caller. No current code writes to it.
   *Fix:* use a private `static final UiState.Widget[] NO_INVENTORY = new UiState.Widget[28]`
   in `ControllerUi`, or accept this and add a comment that `UiState` arrays are read-only.

2. **No test pins the inventory-request flag** at `UiControls.java:59`. The idle-skip
   optimisation relies on that flag being true on the Y-press tick and while inventory mode is
   active, including entry through the radial's `focusInventory`. A regression there would show
   up as an empty inventory or a cursor that does not move, not as an exception.
   *Fix:* add one `UiControlsTest` case with a gateway that records the boolean. Expect
   idle → `false`, Y press → `true`, held in inventory → `true`, after `leave()` → `false`, and
   `focusInventory()` then `update` → `true`.

3. **The diagnostics timer leaves out the SDL poll.** `started` is taken after `pollController()`
   (`SoloScapeControllerPlugin.java:167-168`), so "Controller work" omits the device poll,
   probably the most variable cost. This is fine if intended. Otherwise, take `started` before
   `pollController()` or log the poll time separately.

4. **`LinkageError` from the adapter path is no longer caught.** The tick catch at line 199
   handles only `RuntimeException`. All SDL/JNI calls now go through `pollController()`, which
   still catches `LinkageError`, so this is acceptable today. If a native call is ever added
   after the poll, an `Error` would escape to the event bus. *Fix (optional):* add a comment, or
   widen the catch to `RuntimeException | LinkageError` and route it to the provider-failure path.

5. **Scope of the build stamp.** `build_fingerprint` (`scripts/local_dev.py:140`) proves that
   the jars and patch files are unchanged since the last build. It does not prove that the
   upstream working tree matched those patches at build time; the separate patch-reproduction
   check covers that. Separately, users who run `--no-build` with no stamp now fail fast until
   one full build. That is intended and has a clear message. I suggest a one-line note in the
   dev docs; no code change.

## Not covered

I did not review server patches, the capability negotiation (a documented future item), or
in-game behaviour (packet acceptance by the pinned server, how the Walk fallback feels, whether
dialogue closes). These still need manual gameplay acceptance.
