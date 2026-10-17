# Update staging special-file refusals

18 October 2026. A bounded follow-up to the
[original staging lab](UPDATE_STAGING_LAB_20261017.md) fixes a reproduced input hang
and an unchecked staging guard. This changes experimental tooling only; it does
not enable downloading or installing updates in the launcher.

Before the fix, supplying a named FIFO as the bundle blocks in `os.open` before
its regular-file check. A subprocess regression with no FIFO writer reaches its
three-second timeout. Separately, replacing the staging guard with a FIFO allows
the original dummy candidate to be published instead of refusing the guard.
A directory guard exposes a raw open error rather than the lab's normal refusal.

The bundle is now opened with `O_NONBLOCK` before `fstat` checks its type. The guard
is opened with no-follow/nonblocking flags and must also be a regular file before
locking or creating a candidate. Every path after guard acquisition closes that
descriptor, including contention and other failures. Ordinary cooperating lock
contention keeps its existing refusal behaviour.

Two new tests use real filesystem objects and a real isolated Python subprocess:

- A FIFO bundle is refused with the regular-file diagnostic, without waiting for
  a writer. The FIFO, lab membership and unrelated sentinel remain unchanged.
- FIFO, directory and symlink guards each refuse without creating a candidate.
  Input bundle bytes, the existing guard entry and sentinel are preserved.

The baseline run has one failed guard assertion and two errors, including the
FIFO timeout. After correction, **26 staging cases pass**. The full root suite
passes **278 cases with one optional skip**; generated-status checks also pass.
Claude Haiku independently reviewed the change and ran the staging cases, finding
no actionable issue. [Sanitized evidence](evidence/update-staging-special-files-20261018.json).

Fixtures contain original inert dummy bytes only. No game, candidate executable,
network request, native cache, owner profile or Deck installation is used. The
subprocess deadline is a local FIFO regression bound, not a general filesystem
latency guarantee. This does not establish power-loss durability, authenticated
release packages, updater activation or native launcher integration. The ready
native 52/56 playable build remains unchanged.
