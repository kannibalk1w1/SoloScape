# Update activation gate (lab mechanism)

Experimental, supervised, asset-free. This is a mechanism lab, **not a production updater**.
It proves the lease, pointer and marker rules on original inert fixtures. It does not
download, install, launch, migrate owners, execute candidates, or run native code.

Run the proof from the repository root:

```sh
python3 -m unittest discover -s scripts -p 'test_update_activation.py'
```

The tests need Linux `fcntl.flock` and pidfd APIs. Elsewhere they skip, which is not a pass.

## Lab layout

Everything lives under one caller-supplied, disposable lab root:

- `install.guard` — the single lock file. It sits outside every version directory, so all
  versions share one inode.
- `versions/<sha256>/` — a sealed, immutable version. It holds `.manifest.json` plus flat
  payload files. The directory name is the SHA-256 of the canonical manifest bytes.
- `active.json` — the pointer, `{format, current, previous}`. `current` and `previous` are
  64-character lowercase hex ids (or `previous` is `null`).
- `marker.guard` — a separate stable mutex serializing marker creation/resolution while shared world leases are held.
- `session.marker` — an optional bounded marker, `{format, session}`, for unresolved
  session work.
- Any other file, such as a world-state fixture or a sentinel, is opaque to the mechanism.

## API (`gate.py`)

| Call | Lease | Effect |
| --- | --- | --- |
| `install_candidate(lab, {name: bytes})` | none | Writes a sealed version and returns its id. An existing identical version is verified, never rewritten. |
| `initialize(lab, version)` | exclusive (internal) | Creates the guard and the first pointer, `previous: null`. Refuses an existing pointer. |
| `acquire(lab, 'shared'\|'exclusive', blocking=False)` | — | Takes the flock. Non-blocking refusal raises `Busy`. Use as a context manager. |
| `Lease.current()` | any open lease | Reads `current` after the lease is held. |
| `Lease.pass_fds` | any open lease | `(fd,)` for `subprocess.Popen(pass_fds=...)`. |
| `activate(lease, candidate, expected_current, cutpoint=None)` | exclusive | Checks the marker, checks `expected_current`, verifies the candidate, then publishes `current=candidate`, `previous=old current`. |
| `rollback(lease, expected_current, cutpoint=None)` | exclusive | Checks the marker and `expected_current`, verifies `previous`, then swaps the two pointers. It takes no data argument. |
| `retain_session(lease, session)` | shared | Writes the marker. Refuses a second one. |
| `release_session(lease, session)` | shared | Removes the marker only when it names this session. |
| `verify_version(lab, version)` | none | Exact check: manifest hash, membership, sizes, digests. |

Rules:

- Lease close only closes its own descriptor. It never calls `flock(LOCK_UN)`. A child that
  inherited the descriptor keeps the lease alive after the parent exits.
- Publishing writes a temp file, fsyncs it, `os.replace`s it onto the pointer, then fsyncs
  the directory. There is no multistep `CURRENT`/`PREVIOUS` split.
- Manifests are strict: no duplicate keys, no non-finite numbers, canonical bytes only.
  Names are flat (no `/`, no `..`, no leading dot), and there are at most 64 files of at
  most 1 MiB each. Symlinks and non-regular files are refused.
- Errors are `Busy` (live-lease contention), `Stale` (expected current mismatch),
  `CandidateError`, `PointerError`, `MarkerError`. `MarkerError` is not a `Busy` subclass.

## Two separate refusals

1. **Live lease exclusion** (`Busy`): a running world holds a shared flock, or an inherited
   child holds the descriptor. An apply needs the exclusive lock and is refused while any
   holder lives.
2. **Pending-closure marker refusal** (`MarkerError`): the caller retained unresolved session
   state. `activate` and `rollback` refuse while the marker exists, even with no live lease.
   The marker does not record real-profile state and does not resolve compatibility.

## Tests (14 cases, original inert fixtures; lock/order/exit cases use real processes)

1. One guard inode, no guard inside versions; apply is refused while a world lease is held.
2. A shared start is refused while an exclusive apply holds the lock, then succeeds after.
3. A start queued behind an apply resolves the NEW pointer after it gets the lease. The
   handshake is a printed line, not a sleep.
4. An inherited child keeps the lease after its parent exits. Apply is refused until the
   owned inert child receives SIGTERM and stops.
5. Tampered payload, manifest, extra file, or symlink is refused. `CURRENT` and a sentinel
   file are unchanged.
6. Malformed manifests (duplicate key, traversal, nested name, boolean size, uppercase
   digest, extra field, non-canonical spacing) are refused before any pointer change.
7. Stale expected-current refusal for both `activate` and `rollback`, from child processes.
8. Forced `os._exit` at `after-temp-fsync` leaves the old pointer. A forced exit at
   `after-replace` leaves the new pointer. Both states are parseable and roll back cleanly.
9. Rollback keeps the NEW world-state fixture bytes and both version directories. Rollback
   refuses when the previous version is tampered.
10. An unresolved marker refuses apply and rollback after the lease is released, and clears
    only for its own session.

11. Concurrent shared holders retain exactly one marker; a loser cannot overwrite or clear it.
12. A manifest-listed FIFO is refused without blocking; a symlinked versions namespace is refused.
13. An injected directory-fsync failure after replacement reports failure with the NEW pointer already visible; the caller must reread it.
14. A malformed pointer naming the same current/previous version is refused.

The coordinator mutation check in a private source copy (exclusive acquire changed to shared) failed 4 tests, and the actual
module passed all 14. Test-run logs stay in `.runtime/update-activation-gate-20261017/`.
Child stderr is in `child-stderr.log` there.

Cleanup closes helper input, waits for normal exit and uses SIGTERM only if needed. An inherited
original sleeper is addressed through its captured pidfd after its exact program and unique nonce
are checked. The sleeper has a 60-second bound. No native game or unrelated process is signalled.

## What this does NOT prove

- Actual `fsync` calls and forced process exits do not prove power-loss durability. Those
  cuts model a crashed coordinator. They do not model a torn disk write, a lost directory
  entry, or a filesystem that ignores fsync.
- No package authentication, signing, permissions, or trust claim. Sealing is by hash and
  is not a security boundary.
- Cutpoints are limited to the two publish points. Cuts during candidate install, marker
  writes, and staging cleanup are not covered. Leftover `.active.json.*` temp files are
  harmless and never read.
- This cooperative filesystem protocol assumes its guard inodes are never replaced. It does not
  protect against adversarial same-user directory renames or provide a security sandbox.
- The lab supports one pending marker. A real installation needs an explicit policy/registry for
  multiple profiles; separate per-profile locks do not serialize installation-wide metadata.
- An I/O error after pointer replacement does not imply the old version is current. Callers
  must reread and verify state before deciding how to recover.

## Remaining native integration gates (not in this lab)

- **Data and asset distribution**: how candidate bytes are obtained, verified against an
  authority, and staged. Only the sealed-directory shape exists here.
- **Health checks**: whether an activated version actually starts. Activation is pointer-only
  and never runs candidates.
- **Grave persistence**: the native gravestone and save state must survive activate and
  rollback. The fixture only proves the bytes are untouched.
- **Session recovery**: a real trusted outer updater, start/apply handshake, and compatibility
  resolver for a pending marker. The marker here only fails closed.
- **Production wiring**: no launcher, downloader, owner migration or `healthautoacceptance`.
  The real profile lock, `build.lock` interaction and `profile_session.run` integration are
  untouched and unverified by this lab.
