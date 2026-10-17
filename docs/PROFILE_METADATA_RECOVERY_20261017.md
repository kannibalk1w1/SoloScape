# Profile metadata recovery follow-up — 17 October 2026

A valid JSON profile manifest with an account value of `null`, a number, a list,
an object or a boolean raised `TypeError` during account validation. Listing
profiles consequently failed before the launcher could offer the existing recovery
flow, including when another character was healthy. Whitespace-only account names
also passed this validation despite being rejected when creating a character.

`Profile.reload()` now validates that the account is a nonblank string before
checking its allowed characters. Invalid metadata raises the existing recoverable
`ValueError`; profile listing shows the damaged character as needing recovery and
continues listing healthy characters. No save format, backup policy or generation
switching behaviour changes.

The disposable regression exercises six invalid values. For each value it checks:

- listing isolates the damaged profile without changing its metadata;
- a verified backup remains selectable and restores the account and native save;
- the damaged manifest survives byte for byte under its recovery filename;
- the previous save generation and a healthy profile's metadata remain unchanged.

Before the fix, the test reproduced five uncaught `TypeError` cases. After the
fix, all 21 profile tests pass. The full tooling suite runs 131 tests successfully
with one optional test skipped. These tests use temporary profiles and fixture
TOML saves; they do not access the owner's character, Deck installation or cache.

Physical launcher acceptance remains open: a disposable damaged profile should
show a recovery entry while a healthy character remains selectable. Never damage
the owner's profile to perform this check. This is metadata-corruption handling,
not evidence for suspend/resume or a whole-process native save/restart campaign.
