# Steam Deck tooling: static follow-up

This was a bounded **static** follow-up to `CLAUDE_DECK_DESIGN_REVIEW.md`. I read only:
- `scripts/deck_export.py`, `deck_runtime.py`
- `scripts/native_metrics.py`, `summarise_native_metrics.py`
- `scripts/smoke-recovery.py` (`--client`)
- the `--desktop` and metrics changes in `scripts/smoke_profile.py`
- the click path in `scripts/harness/NativeAdventureProbe.java` (`clickNative`, logout and relogin
  steps)

I ran nothing and made no source changes. I didn't use SSH, the network or Git, and I opened no
saves, cache or credentials. The 78 passing root cases, the temporary-repo blob test and the Deck
results are as you reported them.

## Verdict
**No blockers and no remaining medium findings.** Both earlier mediums are addressed. Four
low-severity notes remain.

## Earlier findings: status
| Earlier finding | Status | Evidence |
|---|---|---|
| M1: the `.git` copy got around the filter and made verification fragile | **Fixed** | `copy_pin_metadata` (`deck_export.py:38-49`) builds a new `.git` with three things: a detached `HEAD` set to the pin, a minimal `config` and **empty `refs/`**. Its single pack comes from `pack-objects --revs` with only the pin on stdin, so stashes, other refs and dangling or staged blobs can't get in. The source's `shallow` file is copied, and `read-tree` creates a local index. `.git/index` is left out of the manifest (`:95-96`), so `git status` on the Deck no longer breaks `verify`. The pack, idx, `HEAD`, `config` and `shallow` are still hashed. |
| M2: `--desktop` evidence and input share the real screen and controller | **Mitigated (as far as tooling can go)** | The summary records a hands-off precondition and says screenshots must be reviewed before publishing (`smoke_profile.py:133-134`). The desktop clicks now go through AWT events with canvas coordinates, so they don't depend on the OS pointer position. Nothing yet *detects* real input during a run (see L3). |
| 3: `verify` accepted extra files | **Wording fixed** | The output now says "listed files match" (`deck_runtime.py:50`). Unlisted files are still not reported, which is now stated honestly. |
| 5: a partial export, cache links, parent links | **Fixed** | The export is written to a `.partial` directory and renamed only after the manifest is written (`:53-55, :105`). Any symlink in the cache, or the cache itself being one, is refused before `copytree` (`:82-84`). `copy_file` requires `resolve()` to stay inside the repo (or `ROOT`), which catches parent-directory links (`:32-33`). |
| configure into a symlinked parent | **Fixed** | `config` must not be a symlink, and the resolved target must stay inside the root (`deck_runtime.py:38-39`). The earlier `exists`/`is_symlink` and `open('x')` checks are kept. |
| 6: metrics truthfulness | **Fixed** | Samples are added under the lock. `finish()` returns copies and includes `sample_count`, `truncated` and `worker_alive`. The method text says the sensors are host-wide and that the Xvfb run is software-rendered. Each stage is recorded through `notify` → `metrics.stage`. `add()` can no longer raise out of the `Popen` wrapper. The summariser computes CPU only between samples with the same (role, pid, start) identity and only when the delta is ≥ 0. It reports battery *statuses* only, never a power or battery-life figure, and its scope string says the numbers cover the whole session. |

## Newly reviewed
- **`smoke-recovery.py --client`.**
  - The required roles become `{server, client}`.
  - It needs both roles registered and `playing`, plus a 10 s settle in which **both** recorded
    identities stay `same_process`.
  - `inspect` must report exactly those active roles before `recover`.
  - The evidence derives `native_client_recovered` from those checks, and it claims no player
    readiness or input.
  - The cleanup that checks the session record is unchanged.

  *Not covered:* the original-world fingerprint looks at server `data/` only. It doesn't cover
  state the client writes on the real `DISPLAY` or in the user's home folder. That's fine for a
  lifecycle probe, but it isn't stated.
- **AWT desktop click path** (`NativeAdventureProbe.java:152-160`).
  - Before any click, it still requires all of the following, then clicks the centre of the
    widget box clipped to the canvas:
    - the widget is visible;
    - the label matches `exit` or `exittologin`;
    - the box isn't empty;
    - the box overlaps the canvas;
    - the canvas has focus.
  - The `MOVED` and `PRESSED` events are dispatched in **one EDT runnable**, so a real OS move
    can't land between them. `RELEASED` follows 80 ms later.
  - The relogin still has to see a new capability nonce and a verified connection. No packet is
    made up for logout.
  - The evidence records `mouse_method`, and the environment label says there is no physical or
    OS pointer acceptance.

## Remaining low notes
### L1. The probe doesn't attribute an unintended walk to its own clicks
The probe records `tile_change_<ms>` entries, but only the later strict save comparison in
`smoke_profile.py` fails, and it fails without saying which step caused it. That is how the Robot
click-through needed per-stage tracing.

**Fix:** store the tile at step 11 and `require` it to be unchanged at step 13, before relogin.
Then a click that falls through to the world fails at the step that caused it, labelled as
`awt` or `robot`.

### L2. The click coordinates assume one game unit per canvas pixel
The widget `bounds` are in game interface coordinates, and they are passed as canvas event
coordinates without scaling. That holds for JDK 8 on Linux (no HiDPI scaling) and a canvas that
isn't stretched. A stretched or scaled canvas would move the click, and a click that lands in the
world means a walk.

**Fix:** `require` that the canvas size matches the client's interface size before clicking, or
record both sizes in the evidence.

### L3. On the desktop, "hands off" is stated but not checked
During `--desktop` runs the client's live SDL loop and the real pointer stay active. A real move
can still arrive between `PRESSED` and the delayed `RELEASED`, and a held controller button can
still reach `ui.update` between the probe's ticks. Those mostly cause false failures, not false
passes.

**Fix (optional):** record any non-neutral `GamepadState` the plugin polled, and any real
(non-synthetic) mouse event on the canvas during steps 11–13. If either is seen, mark the run
invalid.

### L4. The focus wait raises the window and can fail when focus is blocked
`clickNative` calls `toFront()` and `requestFocusInWindow()` on every tick until the canvas has
focus, then fails after 15 s. Synthetic `dispatchEvent` doesn't need OS focus. Under KWin's
focus-stealing prevention this can turn into a false "focus not settled" failure, and it keeps
raising the window over the user's desktop.

**Fix:** keep the focus requirement for the Robot path only, or record focus as an observation
on the AWT path instead of requiring it.

## Limits
- Static only. I didn't run the export, the pack or `read-tree`, `verify`, the summariser, the
  recovery probe or the adventure probe. I haven't independently confirmed that a pack built from
  a shallow source keeps the shallow boundary; that relies on your temporary-repo test.
- I reviewed the AWT click path for logic only. Whether those clicks stop the walk on the Deck
  depends on the verification rerun that is still in progress.
- Nothing here shows the physical sticks, buttons or touchpads, the OS pointer, Gaming Mode,
  GPU, suspend/resume or gameplay working.

## Codex follow-up and native evidence

The Desktop AWT rerun now passes both graphical sessions, settings adoption/reversal, logout/relogin/fresh capabilities, exact save fields, four backups and early cancellation preserving saved-world bytes. Per-stage traces keep the tile unchanged around both clicks. The retained failed Robot runs are not accepted save/UI checkpoints. New guards compare the pre-Exit tile before logout, refuse stretched native/canvas dimensions, and record non-probe mouse presses/releases during logout. AWT events do not require focus-stealing requests; Robot/private-Xvfb keeps its focus requirement. The whole session smoke now retains the shared archive guard during harness compilation and both runs. Physical controller/OS pointer/Gaming Mode remain separate. Native real client/server recovery passes through the ordinary jar path; only original server mutable-path fingerprints are covered by that comparison, while the client uses its private profile home/cache. Final guarded rerun evidence is recorded in the Deck validation guide.
