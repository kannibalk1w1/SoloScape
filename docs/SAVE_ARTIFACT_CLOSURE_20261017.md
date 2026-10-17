# Save-error artifacts prevent a clean-shutdown claim — 17 October 2026

Baseline: merged `efc5ea0`. Normal profile shutdown stopped the owned processes
and accepted expected server exit codes plus a readable backup. Unlike orphan
recovery, it did not check the world's error directory or unfinished atomic-save
files. A readable earlier save could therefore be backed up and reported as
"saved and verified" despite evidence of a failed newer write.

The normal path now shares orphan recovery's artifact check. After both owned
processes finish, any save-error or `.save-*.tmp` artifact keeps the session
record marked unverified, reports an error and retains the pre-launch backup.
It does not publish an `after-clean-shutdown` backup or remove the evidence.
Existing conservative handling also applies to artifacts retained from earlier
failures; they require inspection rather than an automatic clean claim.

Two disposable lifecycle regressions retain a valid earlier TOML save and inject
either a failed-save artifact or unfinished atomic-save file while the simulated
JVMs are running. Before the fix both cases incorrectly reported clean closure.
Afterward both processes stop gracefully, no success is reported, the record and
artifacts survive, and the previous backup remains unchanged. The existing explicit
ended-session archive and verified restore path restores a clean generation while
preserving the damaged generation.

Native source explains the risk: `engine/.../data/SaveQueue.kt` catches primary
storage errors and may write fallback saves instead of throwing out of the
shutdown job. `config/.../Config.kt:39` creates `.save-*.tmp` atomic-save files.
The tests simulate those artifacts, not a real disk-full event or native failure.

All 12 launcher lifecycle tests and all 136 tooling tests pass, with one optional
test skipped. No owner save, cache or Deck installation was accessed.

Reproduce:

```bash
python3 -m unittest discover -s scripts -p test_launcher_backend.py
```

Remaining limitation: absence of an artifact is not affirmative proof that the
latest primary world save succeeded, especially if fallback storage also fails.
An explicit native save-completion result/receipt is a justified follow-up;
these checks alone do not establish that stronger guarantee. Whole-process native
shutdown, suspend and physical acceptance remain separate.
