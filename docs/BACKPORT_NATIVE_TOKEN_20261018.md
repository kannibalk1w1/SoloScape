# Original Lab token: live native container and save boundary

18 October 2026. **Bounded native proof passed**, using merged baseline `39fd65b`
(server 51/client 56) in a new disposable snapshot. No production patch or gameplay
feature was added. The owner installation, profiles and Deck were not used.
[Original tooling](../experiments/native-lab-token/README.md) ·
[Sanitized measured evidence](evidence/backport-native-token-20261018.json).

The [earlier cache-copy lab](BACKPORT_LAB_TOKEN_20261017.md) proved deterministic
encoding and three readers, but did not deliver an item through a running world.
This follow-up uses its exact original definition-only token at temporary ID 20179,
with the semantic save identity `lab_token`. No later-revision assets are imported.

## Observed native sequence

| Stage | Observed result |
| --- | --- |
| Fresh native New | Ordinary AlphaTest login/Continue; real client's JS5 definition reports SoloScape Lab token, cost 37, stackable 1, no note link; inventory contains no token |
| Stopped-world injection | Real full ItemDecoder loads an array of 20,180 entries (distinct from 20,179 occupied definitions). ItemDefinitions.init/load binds one original fixture TOML mapping. Native item-dependent Inventory transaction adds 3/removes 1; over-removing 3 fails and rolls back to 2 |
| Native save | PlayerSave/FileStorage writes one stack of 2 in slot 18 of the 28-slot inventory; independent TOML comparison preserves every other save field, all other inventories and every occupied starter slot |
| Fresh Continue 1 | New server and client JVMs; native visible inventory shows ID 20179, correct label and quantity 2 in one stack |
| Fresh Continue 2 | Another new server/client pair retains the same stack and starter slots |
| Native cold read | Separate helper JVM loads the resulting save and verifies one stack of 2; six profile backup archives validate |
| Baseline-cache control | Helper refuses with `cache lacks item 20179 at 19/78/211`, before loading the save; save bytes remain identical |

The client harness runs outside the production jar and uses the normal login,
Continue and inventory gateways. The quantity comes from actual native widgets,
not a fabricated client inventory. Existing profile-session ownership locks,
normal server shutdown, primary-save acknowledgement and verified backups remain
in use. The helper also takes the fixture profile lock while editing its stopped save.
Claude Haiku wrote the bounded helper; the coordinator reviewed it, implemented the
client/driver and ran the qualified sequence. The worker was released after settlement.

Whole session durations were 25.678/25.611/25.704 seconds, including loading,
readiness dwell, shutdown and backup verification. These are **not FPS, startup-only,
power or Deck measurements**. The environment was owned Xvfb, software rendering,
private HOME/client configuration and empty ALSA configuration; no physical controller.

## Input preservation and provenance

The authorized baseline and both generated candidate inputs retain their original
39-file hashes. The experimental snapshot's 39 cache files also remain equal to
the generated candidate after all three sessions. Every other original
snapshot-manifest entry remains unchanged. All three lab source files retain
identical before/after hashes, and Java 8/Java 21 compile the actual external probes.

The private overlay records the old snapshot manifest digest, generated-cache
summary digest, cache hashes and one added original mapping. The original private
Deck manifest describes the **pre-overlay** cache; the experimental copy is not a
verified release and must not be deployed as the ready owner build. The separate
ready native 51/56 test build remains unchanged.

| Cache input | Fingerprint SHA-256 |
| --- | --- |
| Original baseline | `a4293ba42198ed092f8db93f2b9c2dc8e755db1d6c16bdd91f4dcf0ad68c43fd` |
| Original Lab token candidate | `f6ed21f471bfda634e3bc87b6c93026711d0b1ead71def4557482eb4b35f56b3` |

The refreshed cache-generation audit again preserves 20,178 original definitions
and 101,204 unrelated archive containers. Its source reservation audit uses the
existing pruned source roots; mutable owner data is excluded before traversal.
Generated caches, runtime jars, accounts, credentials and saves remain ignored.
Only original code and sanitized evidence are committed.

An initial run completed New and the native transaction but stopped because ANSI
logging prefixes confused the coordinator's JSON parser. It is not counted as a
qualified complete sequence. The parser now strips ANSI sequences and requires
exactly one JSON record; missing/duplicate records refuse. The reported result
comes from a separate fresh snapshot and fresh profile after that correction.
Root tooling also passed 276 tests with one optional skip.

## Meaning and remaining gates

This supports the proposed compatibility layer: a semantic item identity survives
native saves while the numeric cache/container identity is explicit and isolated.
It does not establish a general generated registry or allocator. ID 20179 is still
a temporary audited fixture allocation, not a permanent range reservation.

The token has no authored model/sprite. Successful definition and inventory delivery
is **not appearance acceptance**, an earned gameplay mechanic or an OSRS import.
Removing the helper/fixture overlay leaves the original inputs untouched, but
removing content from a world containing it needs a versioned migration policy.
The baseline-cache refusal is a helper guard, not a production compatibility check
or proof of safe uninstall. Do not expose this item to owner saves.

Before a real later-content experiment, retain the same native roundtrip gate and
prove one bounded appearance dependency, deterministic allocation/collision checking,
and explicit save compatibility/removal behaviour. Do not replace the 634 cache or
begin a large gameplay backport from this result.
