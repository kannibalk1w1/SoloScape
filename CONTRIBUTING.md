# Contributing to SoloScape

SoloScape is public for transparency, feedback and carefully scoped contributions.
It is an early, maintainer-directed project. The owner, @kannibalk1w1, controls
scope and merges; public visibility does not mean the roadmap is open to wholesale
redesign or that contributors receive write access.

## What is welcome now

- Reproducible bug reports, especially controller input and interface problems.
- Steam Deck testing with device, display mode and reproduction steps.
- Small fixes to an agreed issue, documentation corrections and test improvements.

Before starting a feature, refactor, graphics overhaul, protocol change or substantial
content addition, open a proposal and wait for the maintainer to agree the scope.
The [roadmap](docs/ROADMAP.md) lists ideas and dependencies; an unchecked task is
not automatically available for implementation. Ask to claim work before starting.
There are no release dates or promised review times at this stage.

## Development and pull requests

1. Follow the [setup guide](README-SOLOSCAPE.md) and use the pinned upstream commits.
2. Keep a change focused and independently reversible. Preserve saves and existing
   mouse/keyboard behaviour. Experimental controls should have a toggle.
3. Submit changes as sequential patches under `patches/client/` or `patches/server/`.
   The upstream checkouts are ignored; editing them alone will not be included in a PR.
   Use the complete working tree (`git diff HEAD`), not only an unstaged diff.
   Generate incremental patches against the previous complete patch stack.
4. Verify fresh application, upgrade, reverse and repeated application; run the
   relevant tests and builds. Include reproduction steps and validation limits.
5. Update current-state/testing docs when behaviour changes. Distinguish automated
   checks from physical controller or Steam Deck acceptance.
6. Open a PR referencing the agreed issue. The maintainer reviews and merges it.

Do not upload game cache/assets, save files, account credentials, local configuration,
Java runtimes, downloaded archives or built jars. Redact personal data from logs.
The [upstream notices](THIRD_PARTY_NOTICES.md) explain the current licensing status;
preserve existing notices and only submit work you have permission to share.

## Current focus

Finish M0 controller acceptance and review follow-ups before expanding the feature
set. The new tab radial is a proof of concept, not a replacement for navigation
inside every game interface. Broad upstream content completeness and Deck
performance have not yet been verified.
