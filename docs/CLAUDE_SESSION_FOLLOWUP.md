# Session follow-up review: patch 0021, retention, prepare, shared general-store stock

This was a static review, inside this repo only. I did not run any game, build or test, did not
open saves, cache, login data or config credentials, and made no network calls, source edits
or commits. Scope:
- `patches/client/0021-native-item-artwork-mapped-hints-and-session-polish.patch`
- in `scripts/profiles.py`: `retention_plan`, `preview_retention` and `apply_retention`
- the launcher retention backend and UI
- `scripts/local_dev.py` `prepare`
- on the server: `Inventories.bindExternal` / `getOrNull`, `GeneralStores.bind` / `unbind`
  and `SessionAdventureTest`

## Verdict
**No correctness or preservation blockers in the client, retention or server changes.**
- One **medium** process-safety gap: `prepare` can rebuild the jars while a world started from
  the launcher is running.
- The other findings are polish.
- Modal→modal generic reopen is accepted as the documented limit.

## Verified
**Navigation fixes**
- **Stale-child ownership.**
  - `Parent` now stores `child`.
  - `pop(child)` and `hasParent(child)` only match the top entry for that child
    (`MenuNavigation`).
  - When a modal goes away without a B press (`closingChild < 0`), its entries are discarded
    (`UiControls`, the `discard` line).
  - The new test `serverClosedBankCannotLeaveInventoryParentForLaterShop` covers the case from
    my earlier review: a bank the server closed no longer leaves an inventory parent behind for
    a later shop.
- **Close timeout.** `closingChild` is cleared when `panel.closing()` turns false while the same
  panel is still open. If the server later closes it, the discard path above runs.
- **Stick and button on the same frame.** A stick scroll step is skipped when A, X, LB or RB is
  pressed on that frame (B is handled earlier). The press goes through, and at most one scroll
  repeat slot is spent.
- **Deadzone.** `StickScroll` uses `clamp(config.deadzone, .25, .9)` as neutral, and its active
  threshold is at least 0.3. That is consistent with the camera's `<= deadzone` re-arming, so
  neither one stays disarmed when the stick drifts.
- **Logout history.** `ui.clearHistory()` (saved panel positions and the parent stack) runs on
  every tick without a local player, and on `shutDown`.

**Sidebar hit mapping**
- `paint` returns a `Rectangle[]` with one entry per action index. Actions scrolled out of the
  window are `null`, and `mousePressed` skips null entries.
- So a click always maps to `current.focus.actions[i]` for the row that was drawn.
- The window keeps `selectedAction` visible, and starts at 0 when nothing is selected.
- `PanelOverlayTest` checks that the 24th action is visible, mapped, inside the panel, and not
  overlapping any other entry.

**Native artwork**
- It copies pixels the native renderer has already produced, on the client thread. It doesn't
  render or load anything itself.
- It only accepts images of exactly 36×32, makes a defensive copy, and keeps at most 128 in an
  access-order LRU.
- The cache is synchronized, cleared on login, and used for display only. When no image is
  available, the cell falls back to text.

**Mapped hints**
- The substitution is a single pass (`appendReplacement`), so a swapped binding such as A↔B
  can't remap itself back.
- The order of `hint()`'s arguments matches the `logical` table (A, B, X, LB, RB, Y, View,
  Start).
- Both tests cover Xbox and PlayStation labels with swapped bindings.

**Retention (`profiles.py:545-583`, backend `:67-70`, launcher `retention()`)**
- Only *verified* backups whose reason is `before-launch` or `after-clean-shutdown` are
  candidates. These match the `profile_session.py:36,103` strings exactly.
- Kept regardless: manual, imported and damaged or unverifiable archives, and every save
  generation.
- `keep` must be an `int` from 2 to 100. Booleans are rejected, and the UI spinner has the same
  limits.
- Both preview and apply run under the exclusive profile lock, so they're refused while the
  world is running, and the UI disables the button then too.
- Apply recomputes the plan under the lock and requires the token. The token binds the
  profile, generation, `keep`, and the name, sha256 and size of every automatic backup. Any
  change in the meantime is refused.
- Unlinks are followed by a directory fsync.
- Backup names begin with a `%Y%m%dT%H%M%S` timestamp, so sorting by name in reverse puts the
  newest first.
- The UI shows the count, the size and every file name before asking for a second
  confirmation.

**Server: shared general-store stock**
- `bindExternal` keeps the shared store `Inventory` in a separate `external` map. `getOrNull`
  checks it first (`Inventories.kt:26-47`), and it is used only by
  `InterfaceHandler.getInventoryItem` validation.
- Because it is never added to `instances`, `PlayerSave` never writes shared stock into a
  character file. Before this change, validating general-store items would have failed with
  "invalid interface inventory".
- `unbindExternal` only removes the entry if it is the same object, and it runs from the
  `interfaceClosed("shop")` handler (`ShopOpen.kt:28-36`). The repeated
  `GeneralStores.bind` calls from `shopInventory()` just put the same entry back.
- `SessionAdventureTest`:
  - It asserts that the stock is shared between two players, not saved in `instances`, and
    unbound per player.
  - It does a full save and load into a **temporary directory**, comparing tile, quest state,
    experience and every saved inventory, then deletes the directory.
  - It never touches real saves.

## Findings
### 1. Medium (process safety): `prepare` can rebuild jars under a running world
- `local_dev.prepare` (`local_dev.py:174-194`) only takes `.runtime/launcher.lock`.
- The persistent GUI backend and `profile_session.run` never take that lock (only `local_dev`
  does). They start `java -jar` straight from the shadow jars (`profile_session.py:28-30, 61,
  80`).
- So running `prepare` while a GUI-launched world is live re-applies the patches and rebuilds
  `void-server-*.jar` and `void-client-*.jar` in place.
- I did not check whether Gradle replaces the archive file or truncates it and writes it in
  place. If it truncates, the running JVM's lazy class loading could fail. That includes
  classes first needed by the shutdown hook's `SaveQueue` / `worldDespawn` path, which would
  turn a clean Save & Quit into a crash. The autosave within the last 5 minutes and the
  pre-launch backup would remain, but this matters for preservation.

**Smallest fix:** have the backend hold a shared lock on `launcher.lock` (or a dedicated
`build.lock`) for the whole time a world session is running, and make `prepare` take it
exclusively. Alternatively, have `prepare` refuse while any `profiles/*/profile.lock` is held.

### 2. Low (display): hint mapping also rewrites the X in native labels such as "Withdraw-X"
`TOKENS` matches `\bX\b` followed by a space, a colon or a slash. A hyphen counts as a word
boundary, so prompts that embed native labels get rewritten:
- "A: Withdraw-X Coins ×5 · …" becomes "Withdraw-[X] Coins" (or "Withdraw-Square", or
  "Withdraw-RS click" when X is remapped).
- "Make X ·" and article "A " in names are affected the same way.

This is display-only and doesn't change what is dispatched. **Fix:** only map tokens that start
a hint segment, for example at the start of the text or after "· " and followed by ":" or
"/". Alternatively, mark controller tokens in the authored strings (such as `{A}`), and never
pass `action.label` through `hint()` (`SoloScapeUiOverlay` menu rows).

### 3. Low (cosmetic): artwork is missing or varies after relog
- `ControllerItemImages.capture` only runs on a **native sprite-cache miss**
  (`ObjTypeList.method1932`: `method1941` returns cached sprites first).
- After `clear()` on login, or after LRU eviction, items the native cache still holds are never
  captured again until it evicts them. Their cells show text only.
- The key ignores the outline, shadow and stack-text arguments (`i`, `i_1_`, `i_6_`). A
  selected or outlined variant can therefore replace the plain icon.

**Fix (optional):** include those arguments in the key and capture only the plain variant, or
accept text fallback and document it.

### 4. Low: retention may delete the backup a restore came from, and is slow
- A profile restored from an older automatic backup keeps the newest N automatic archives. The
  `restored_from` archive can fall outside them and be deleted. Generations are kept, so this
  is recoverable. **Optional:** protect `manifest['restored_from']`.
- `retention_plan` fully validates *and* re-reads every archive while holding the lock. That is
  up to 100 × 512 MB, so the launcher shows "running" for a while on large histories. The
  result is correct, just slow.

## Addendum: startup ordering in `Main.kt` (server working tree)

Read from `git diff -- game/src/main/kotlin/Main.kt`, together with `World.start` and
`World.shutdown`. **Verdict: correct, no blockers.** The shutdown of a running world that has
finished loading is unchanged: the hook body (`World.shutdown()` then `AuditLog.save()`) and the
`runBlocking { job.join() } finally { … }` path are the same as before.

**What I checked**
- **Preload failure now returns** (`Main.kt`, the `catch` around `preload`). Before, it fell
  through after `server.stop()` and went on into `LoginServer.load` and `World.start` with half
  of Koin initialised. Now nothing after a failed preload runs. Because the hook used to be
  registered at the very end of `preload`, a failed preload never registered it, so nothing
  can save afterwards.
- **The hook is registered right after `World.start(configFiles)` returns, and before
  `GameLoop.start` and `server.loginServer = loginServer`.**
  - **SIGTERM during preload or `World.start`:** no hook exists, so the JVM exits without
    calling `exchange.save()` or `saveQueue.direct()`. No player can be logged in before the
    login server is attached, so there is no player state to lose. The exchange files on disk
    stay exactly as they were loaded. This removes the risk I noted as item 9 in
    `CLAUDE_ALPHA_SAVE_REVIEW.md` (shutdown during startup writing shared state that was only
    partly initialised).
  - **SIGTERM after the hook, but before login is attached:** `World.shutdown()` runs with no
    players. `Despawn.world()` → `worldDespawn` then saves an exchange that is fully loaded,
    because `GrandExchange` is created at Koin start inside `preload`, which has already
    finished. That saves unchanged data.
  - **SIGTERM once the world is ready:** same behaviour as before.

**Residual notes (low)**
1. **The hook might wait on a stopped game loop.** In the short window between registering the
   hook and `GameLoop(stages).start(scope)`, the hook runs without a game loop. I still haven't
   traced whether `worldDespawn` waits on anything driven by ticks. If it did, a SIGTERM in
   that window could hang the shutdown rather than lose data. `profile_session` only ever sends
   SIGTERM, so the launcher would show "saving" until the process exits.
2. **An exception in `World.start` isn't caught.** If a spawn loader throws, `main` exits by
   that exception without calling `server.stop()`, and the game-server threads that are already
   bound may keep the JVM alive with no world and no hook. Nothing is saved, which is safe, but
   the session never reaches ready and waits on its own cancel. This behaviour already existed.
   **Optional:** wrap `World.start` like `preload` (log, `server.stop()`, `site?.cancel()`,
   `return`).
3. **Startup audit entries can be lost.** With no hook during startup, `AuditLog.save()`
   doesn't run, so in-memory entries such as "startup" and "login online" are lost when
   startup is cancelled. This is cosmetic.
4. **Derived files can be half-written.** A cancel during `preload` can interrupt writes to
   derived files (`configFiles.update()`, `Wildcards.update`). These live under the per-profile
   `storage.data.modified` and `storage.wildcards` paths and can be regenerated. I did not
   confirm that a truncated derived file is detected and rebuilt on the next start.

**Limitation on coverage:** tests and smoke runs that cancel startup can only hit particular
moments. They can't cover every startup phase, such as the cache load, each Koin singleton
inside `preload`, each spawn loader inside `World.start`, or the gap between the hook and
attaching the login server. The safety argument above rests on reading the code: no hook
exists before `World.start` returns, and nobody can log in before the hook exists. It has not
been checked exhaustively at runtime.

## Remaining limits
- No runtime verification of any of this: tests, builds and in-game behaviour weren't checked
  here. Your report that the client tests and 41 root tests pass is the only evidence of test
  status, and the expanded server tests are still pending.
- I did not trace whether `interfaceClosed("shop")` fires on logout or when another interface
  replaces the shop. If it doesn't, the stale binding lives only on that player object, so the
  risk is low.
- I did not check Gradle's archive write semantics (finding 1).
- Modal→modal generic reopen remains the documented limit.
- Tests that cancel startup natively can't cover every startup phase (see the addendum). The
  safety of the startup ordering rests on reading the code, not on exhaustive runtime checks.

## Follow-up verdict on the fixes (static re-check)

**All five fixes are correct. No blockers remain.**

| Finding | Status | Evidence |
|---|---|---|
| 1. `prepare` could rebuild jars while a world runs | **Fixed** | `local_dev.build_lock` (`local_dev.py:28-39`) takes a non-blocking `flock` on `.runtime/build.lock`. `profile_session.run` holds it **shared** for the whole `_run`, including the post-stop backup (`profile_session.py:23-25`). `prepare` holds it **exclusive** (`:188`). A dev launch takes it exclusive while building, or shared with `skip_build`, and after building downgrades to shared (`:216, :243-244`). Holding a shared lock refuses an exclusive one and the reverse, so a rebuild can't overlap an owned JVM. The tests check the lock is refused while playing and succeeds after save and cleanup (`test_launcher_backend.py:70, :84`). |
| 2. Hints rewrote native labels | **Fixed** | The pattern is now `(?<![\w-])(A\|B\|X\|Y\|LB\|RB\|View\|Start)\b(?=\s*[:/])`. A token preceded by a hyphen or a word character is rejected, and a colon or slash must follow it. Menu rows in `SoloScapeUiOverlay` (`:88, :99`) draw `action.label` without mapping it, and the panel action list never mapped it. The test keeps "Withdraw-X", "Make X" and "A new item" unchanged while still mapping "X / right click". |
| 4. Retention could delete the restore source | **Fixed** | `retention_plan` skips `path.name == manifest['restored_from']` (`profiles.py:558`). The token is computed from the filtered records, so apply follows the same rule. |
| Addendum 2. Uncaught `World.start` failure | **Fixed** | `World.start` is wrapped in `try/catch`: it logs, calls `server.stop()` and `site?.cancel()`, then `return`. This happens before the hook is registered, so a failed world start never saves anything. |
| Startup hook ordering | **Unchanged and correct** | As in the addendum above. |

**Remaining low notes (not blocking)**
- **The lock downgrade isn't atomic.** On Linux, `flock` turns exclusive into shared by
  dropping the old lock and then taking the new one. The downgrade at `local_dev.py:244`
  blocks with no `LOCK_NB`. If a `prepare` grabs the lock in that microsecond gap, the launch
  waits until it finishes and then runs a pair that `prepare` built and stamped as matching.
  That is safe; it can't produce a mismatched pair.
- **The build lock belongs to the Python process, not the JVMs.** Python file descriptors
  aren't inherited by child processes (PEP 446). If the launcher backend process itself died
  while the JVMs kept running, the lock would be released and `prepare` could rebuild under
  them. That needs an abnormal backend death. Optional fix: refuse to `prepare` while any
  `profiles/*/profile.lock` is held, or pass the lock fd to the server child.
- **`World.start` only catches `Exception`.** A JVM `Error` such as `NoClassDefFoundError`
  still escapes. Nothing is saved in that case, which is safe.
- The limits listed above still apply. This was static only, with no runtime confirmation, and
  tests that cancel startup can't cover every startup phase.
