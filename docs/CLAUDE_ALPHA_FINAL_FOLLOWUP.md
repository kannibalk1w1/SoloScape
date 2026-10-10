# Alpha final follow-up

Scope:
- `patches/client/0019-claude-panel-fixes-and-persistent-launcher.patch`: the controller and
  panel changes and `UiControlsTest`. I did not review the launcher hunk.
- `patches/server/0008-exchange-counter-crash-recovery.patch`
- `scripts/profiles.py`: `recovery_profile`, `restore_profile` (and the `restore(recovery=True)`
  path) and `import_world_copy`.

This was static only, searching inside this repo. I ran no tests, opened no saves, cache or
credentials, made no edits, used no network and made no commits.

## Verdict
**No blocking findings.** Both earlier findings are fixed correctly, and the new recovery and
import paths keep the source copy, the damaged metadata and `login.json` intact. The notes below
are low severity.

## 1. Drop/Destroy confirmation (fixed)
- **Gamepad.** `UiControls` (context branch) and `PanelControls` (context branch) now clear the
  context only when `gateway.invoke` returns true. When an invoke is blocked, the context
  and `contextIndex` stay open, so the second A repeats the same Drop. It no longer falls
  through to `actions[0]` or `primary()`.
- **Mouse.** After a blocked invoke, `mouseInvoke` reopens the context with
  `mouseFocus(expected, true)`. It then points `contextIndex` at the blocked action, matching on
  type and operation. For panels this goes through the new `PanelControls.focusAction`. A stale
  or changed item fails `mouseFocus` and opens nothing, which fails closed.
- **B** with the context open now only closes the context. The plugin clears the confirmation
  on B, so the misleading "B: cancel leaves the inventory" case is gone.
- **Tests:**
  - `destructiveContextConfirmationRepeatsChosenDropRatherThanEating`: X → Drop → A (blocked,
    context kept) → A sends exactly one `Drop`, then closes the context.
  - `blockedMouseDropKeepsItsActionForControllerConfirmation`: a blocked mouse Drop followed
    by gamepad A sends exactly one `Drop`.

  Both tests route the fake gateway through the real `PanelConfirmation`.
  - Small caveat: the fake calls `System.nanoTime()` while the presses use synthetic times.
    That's fine, because the two calls are well within the 3 s window.
- **A side effect, and it's acceptable:** a non-destructive context action that fails as stale
  now also keeps the context open. It is checked again every frame (`context.same(focus)`), so
  a changed item still closes it.
- **The other review items are also fixed:**
  - focus after a native scroll is now based on the item's identity (`scrollSubject` with
    `find`, then `neighbor`, then the nearest child in the scroll direction);
  - the mouse wheel sets the same anchor;
  - the page label now reads "Visible page";
  - game messages are prefixed with "Game:";
  - `mouseMoved` is consumed inside the panel.

## 2. Exchange offer counter (fixed)
- The counter is now written atomically **before** the item files. Gaps in the numbering are
  allowed; reused IDs are not.
- When loading, `counter = max(counter, highest loaded offer id)` is applied **before**
  `removeInactive`, so expired offers still count. That covers both old snapshots and a
  missing counter file. The test covers a stale counter and a deleted one.
- **Low:** IDs that now exist only in `claimable_offers` (completed offers no longer in the
  buy or sell files) aren't included in that max. With the new write order a crash can no
  longer produce this case, but a snapshot taken *before* this patch could. Optional: include
  `claims.keys()` in the max.

## 3. Profile recovery, restore and world-copy import

**Checked and correct**
- **Ownership.**
  - `recovery_profile` only accepts a backup name that matches the pattern, from that
    profile's own `backups/` folder. It refuses symlinks on the directory, `states`, `backups`
    and the zip itself, and requires `backup.json.profile == uid`.
  - It then runs the full `validate_backup`: checksums, paths, sizes and save validation.
  - It never constructs a runnable profile.
- **Locking.**
  - `restore(recovery=True)` takes the exclusive lock without reloading. Under the lock it then
    tries `reload()` again and refuses if the profile has become healthy in the meantime, which
    closes the race with a concurrent repair.
  - A running session holds the same lock, so no restore can happen while the world is live.
- **Damaged metadata is kept.** Before the manifest switch, `profile.json` is copied to
  `damaged-manifest-<uuid>.json` (mode 0600, fsynced, directory fsynced). The old generation
  directories are never removed. `login.json` isn't touched.
- **Failure cleanup.** The new generation is deleted only if `profile.json` on disk doesn't
  point to it.
- **Source copy preservation.** `import_world_copy` only reads the source:
  - It refuses symlinks and anything under `upstream/game-server/data`.
  - It reads everything into memory with size and mtime fingerprints, checks again for changes,
    and only then creates the profile.
  - It writes with `open('xb')` and fsync, so nothing is ever overwritten.
  - `.save-*.tmp` files are skipped.
  - On any failure it deletes only the profile it just created.
  - Empty credentials leave the native login as it is; no password hash is rewritten.

**Low notes (not blocking)**
1. **Recovery records a generation that doesn't exist** (`restore`, `previous_generations`).
   `recovery_profile` invents `generation: uuid4()`, so the recovered manifest's
   `previous_generations` gets that fake ID instead of the damaged manifest's real generation
   and history. The data itself is safe: the old `states/*` directories are still on disk, and
   the damaged manifest copy records them. **Risk:** any future pruning that trusts
   `previous_generations` would treat the real old generations as unreferenced. **Fix:** in
   recovery, set the previous list to `[]` and record `recovered_from_manifest:
   damaged-manifest-<uuid>.json`, or list the `states/` directories that exist on disk.
2. **`created` comes from the wrong field.** `recovery_profile` sets `created` from
   `header['created']` (when the backup was made) rather than `metadata['created']` (when the
   profile was created). This is cosmetic.
3. **Import can read from another live profile.** `import_world_copy` only refuses
   `upstream/game-server/data`. A source inside `.runtime/profiles/*/states/*/saves` belonging
   to a running profile is accepted. Each file is atomic, but the files may not be consistent
   with each other. **Fix:** refuse paths under `PROFILES`, or take that profile's lock while
   reading.
4. **There's an unlocked moment during imports.** `import_world_copy` and `import_character`
   call `create()` and only then take the lock. If something starts that profile in the gap,
   the import fails to get the lock and then deletes the directory of a running profile. The
   current backend handles requests one at a time, so this can't happen today. **Fix:** stage
   the import under a temporary directory name and rename it into `PROFILES` after the
   backup.
5. **Account-name case must match.** The primary account is validated against the typed
   `account`, so a case mismatch with the save's `accountName` is refused. This only affects
   usability, and it fails closed.
6. **Import isn't connected yet.** `import_world_copy` has no handler in
   `launcher_backend.dispatch` at this snapshot, so it is functionality still to come.

## Codex follow-up

The low recovery-history and creation-time notes are fixed: recovery records actual retained state-directory IDs, the preserved damaged-manifest filename, and the original creation time from backup metadata. World-copy import now refuses active profile storage as well as upstream data. Both import paths stage under hidden `.import-*` directories and publish by rename only after copy and verified backup finish; failed staging cannot delete a discoverable/running profile. A new regression proves the import stays absent from character lists until publication. Native case matching already uses casefold in validate_save. Import is available through `scripts/import-profile.py`; a graphical import picker is deferred. Earlier claim-only IDs from historical exchange snapshots and general UI polish remain limitations.
