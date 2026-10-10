# Journeys sprint: recovery-fix verification and controller menu audit

This was a bounded static review. I made no source, test, process, git or network changes, ran
no Gradle build or game, and opened no saves, cache or credentials. I read:
- `scripts/session_recovery.py`, `launcher_backend.py`, `profiles.py` (`restore`)
- `UiControls.java`, `MenuNavigation.java`, `PanelControls` (the uses relevant here)
- `SoloScapeLogin.java`
- `scripts/harness/NativeLauncherProbe.java` and `scripts/smoke-launcher.py`

## Verdict
**No blockers.** All three medium recovery findings from
`CLAUDE_JOURNEYS_IMPLEMENTATION_REVIEW.md` are fixed. The menu audit found **one reproducible
navigation bug**: a stale Home ancestor survives into a later inventory session (finding M1).
There is one low issue in the recovery `list` path. I found no blocker in `LauncherKeyboard` or
`NativeLauncherProbe`.

## Recovery fixes (verified)
| Earlier finding | Status | Evidence |
|---|---|---|
| 1. A stale record owned by this backend blocked Start and Recover | **Fixed** | `inspect` and `recover` take `owner_active`. When `record.owner.pid == os.getpid()`, the owner counts as alive only if the callback agrees (`session_recovery.py:138-139, 191-192`). `recover` and `archive_session` pass `lambda: False`, and they are refused while this launcher has a running worker (`launcher_backend.py:85-88, 125`). |
| 2. Restoring while a record existed stranded the profile | **Fixed** | `Profile.restore` refuses under the profile lock when `session.json` exists, including as a symlink (`profiles.py:292-294`). This covers both normal and damaged-manifest recovery restores. `archive_ended` exists for a record whose session has ended. It runs under the recovery lock, the shared build lock and the profile lock; it requires `archiveable` **and** a full `candidates()` scan with no live process; and it **renames** the record to `session.<id>.unverified.json`, refusing to overwrite (`:166-180`). |
| 3. The argv jar check compared resolved and unresolved paths | **Fixed** | The record stores `str(server_jar)` / `str(client_jar)`, exactly what `Popen` receives (`:67`). The expected `storage.players.path` now uses `profile.state.resolve()`, the same as `Profile.environment` (`:91`). |

### R1 (low): `list` treats a stale self-owned record for *another* profile as live
`list` passes `owner_active=lambda: current['running']` for every row (`launcher_backend.py:61-62`).
Suppose this backend owns a stale record for profile A (an earlier session's backup or unlink
failed) and is now running profile B. Then profile A's row shows "owned by another active
launcher" and can't be recovered until B stops. Recover still works once B has stopped.
- **Trigger:** make the after-clean-shutdown backup fail for A (for example, put an invalid
  top-level account TOML in A's saves before Save & Quit), then Start B and look at A's row.
- **Fix:** `owner_active=lambda: current['running'] and current['profile'] == row['id']`.

## Menu, selection and lifecycle audit

### M1 (medium, reproducible): a stale Home ancestor sends a later inventory B back to the Home wheel
`MenuNavigation.home` is set by `focusHomeTab` and is cleared only by `reset()`
(`focusTab`/`focusInventory`/`reset`) or by `homeBack()` (root B exit, `leave()`). Several
ordinary ways of leaving a Home-opened tab clear neither:
- **A spell selection out of the panel.** `UiControls.java:191-195` (`selectionRequested`) sets
  `focusedTab=-1; panel.reset()` but keeps `home`.
- **The tab never renders within the opening window.** `UiControls.java:200-201` sets
  `focusedTab=-1` and keeps `home`.
- **The panel disappears without B** (the `wasPanel && !panel.active()` path). `home` is kept.

The inventory button then opens the inventory **without** resetting navigation
(`UiControls.java:233-236`: `inventory=true` only). B in that inventory calls `leave()` →
`homeBack()` (`:283-285`), which sets `returnedHome` to the old tab, and the plugin calls
`radial.returnTo(...)`. So pressing B to leave an inventory opened directly with Y lands on
the Home wheel instead of the world.

**Testable trigger** (`UiControlsTest`, with a fake gateway):
1. `focusHomeTab(SPELLBOOK)`.
2. Adopt a 192 panel, then A on a spell whose action type is 13, so `selectionRequested`
   becomes true.
3. Return a snapshot with no panel.
4. Press the inventory button with `hasInventory()`.
5. Press B.
6. Assert `takeHomeBack() == -1`. It currently returns `SPELLBOOK`.

A second variant: `focusHomeTab(QUESTS)` with no 190 panel for more than 1 s, then the
inventory button, then B.

Return-to-source is unaffected, because `SelectionReturn.begin` captures `home` in `invokeUi`
before the panel is reset. With `returnToSource` off, or when the restore is blocked by a
dialogue, entry or modal, the stale ancestor is the only effect.

**Fix:** call `navigation.reset()` in the `selectionRequested` branch and in the
tab-opening-timeout branch. Also call it when the inventory button opens the inventory from a
non-inventory state. Simplest: `if(!inventory) navigation.reset();` before `inventory = true`
at `:235`.

### Checked with no issue found
- **Parent push and pop.** Parents are keyed by child id. Pop happens only when B closes the
  top child (`hasParent(state.panel.id)`). A modal closed by the server, without `closingChild`,
  discards its entries (`:179`). `closingChild` is cleared when a close attempt times out with
  the panel still open (`:189`). The parent tab reopens only when no modal is showing (`:174`).
- **SoloScapeLogin.** It makes one explicit attempt per client run, only on the login screen
  state (3) with nothing else in progress. Empty passwords keep the normal login, failure
  isn't retried silently, and nothing is printed except a generic message.

## LauncherKeyboard and NativeLauncherProbe
- **No blockers.** The probe runs the real Swing launcher and backend against a **disposable
  copy**:
  - `smoke-launcher.py` copies `scripts/*.py` into `.runtime/launcher-tests/<ns>/scripts`, so
    the backend's `ROOT`, `PROFILES`, settings and locks all resolve under that root, and no
    real profile is touched.
  - It uses its own `Xvfb -displayfd ... -nolisten tcp` with no display fallback, so the
    full-screen screenshot only sees the private display.
- The probe asserts:
  - a held A at opening doesn't type;
  - controller typing works, and Y moves to the account field;
  - pasting an invalid account (`bad-name`) is rejected by the `DocumentFilter`;
  - B leaves the keyboard and keeps the form and its text;
  - a valid create makes exactly one profile;
  - a backend rejection (a label of only a no-break space) keeps the form open with its text
    and re-enables Create.
- Small notes, not blockers:
  - It drives `keyboard.update` and `doClick` directly, so the launcher timer's SDL path and
    the focus-gained auto-activation are only covered indirectly.
  - `display.wait(timeout=5)` in `finally` can raise `TimeoutExpired` and hide the original
    failure if Xvfb ignores SIGTERM.

## Limits
- Static only. I didn't run the tests or probes. Whether the M1 trigger reproduces should be
  confirmed with the unit test described above.
- I didn't re-audit the scroll anchoring, `SelectionReturn` token semantics or the settings
  lifecycle beyond the earlier reviews (`CLAUDE_SESSION_NAVIGATION_REVIEW.md`,
  `CLAUDE_ADVENTURE_SETTINGS_*`). I saw no regression in the parts read here.
- No physical controller, Steam Deck or gameplay acceptance is claimed.

## Codex verification after review

M1 was reproduced with two actual `UiControlsTest` cases: Home spell selection → direct inventory → B, and Home opening timeout → direct inventory → B. Both failed before the fix. Navigation now clears on selection handoff, failed tab opening and independent inventory opening. The complete client suite passes 176 cases (one optional SDL skip); existing parent/settings/source-return cases remain green.

R1 now scopes the owner-active callback to the matching profile. A disposable backend listing case proves an ended self-owned record is not confused with a different active world. The complete root suite passes 61 cases. The actual Swing launcher probe also passed; physical SDL/Deck acceptance remains pending.
