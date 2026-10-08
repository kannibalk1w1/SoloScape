# SoloScape controller sprint — progress and morning report

Started 8 October 2026, approximately 17:40 UTC. Status: **in progress**.
Remote development branch: `overnight/controller-sprint`; public `main` remains
at the published radial prototype. The local Orca checkout remains on
`soloscape/bootstrap`, tracking that remote development branch.

## Authorized scope

Reliability review fixes → bank → shop → equipment/prayer → spellbook and safe
targeting → radial integration → tests/builds/patches/documentation. Continue
independent work when physical gameplay judgment is needed. Preserve real saves,
cache and current game processes. Push completed batches and leave review evidence.

Claude is available for targeted second checks. User reported 14% of the current
five-hour window used, resetting approximately 21:40 UTC; conserve requests and
avoid broad repeat audits. One targeted Claude reliability review completed in about two and a half minutes; no blocking findings. Three minor suggestions were implemented. See `CLAUDE_RELIABILITY_REVIEW.md`.

## Completed in this sprint

Reliability batch completed: custom server opcodes now require an explicit opt-in; game-adapter exceptions no longer permanently disconnect the pad; idle inventory snapshots skip item descriptions; dialogue cancellation uses the queued tile; optional diagnostics include SDL polling; the launcher checks matching jar/patch fingerprints and retains previous logs. Automatic server capability negotiation remains future work.

## Verification and limitations

Current reliability build: 76 client cases, zero failures/errors, one SDL virtual-device skip; 11 root tooling cases pass. Existing server evidence: 247 network and 61 selected engine cases. Both jar builds have passed; the client jar was rebuilt for this batch.
Physical controller and Deck acceptance remain separate from automated evidence.

## How to try the latest completed build

Quit the current session normally before starting another server/client pair.
The final report will identify the last verified jars and exact launch command.

## Next work

Bank/interface navigation is next. Update this file
at completed checkpoints and replace this in-progress summary with final results.
