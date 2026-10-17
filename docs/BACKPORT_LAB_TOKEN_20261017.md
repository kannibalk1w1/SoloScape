# One original Lab token in a copied cache — 17 October 2026

The Lab token now goes beyond an in-memory codec probe: one original item definition is encoded, added to two fresh disposable copies of the supplied 634 cache, and read back through native cache/definition readers. Both complete candidate caches are byte-identical across all 39 recognized cache files. The original cache remains unchanged. This is a cache-format proof, not a live item or later-content feature.

## Fixed scope

The [original manifest](../backport/manifests/lab-token.json) names semantic key `lab_token`, temporary candidate item 20179 (index 19 / archive 78 / file 211), label “SoloScape Lab token”, cost 37 and stackability. The native encoder emits 28 bytes, opcodes 2/11/12/0. All three raw readers consume the entire definition and agree on its name/cost/stackability. A fresh native FileCache reopen returns the new entry.

No note/lend/stack-variant, wearable or animation link is added. Model 0 remains a numeric default; no model is loaded and no appearance dependency graph or rendering is proved. The empty manifest dependency list applies to this definition-only scope. No production TOML, player inventory, save or installed cache receives the token. Candidate 20179 is not a permanent reservation or a general safe range.

The wrapper freshly checks the exact documented baseline fingerprint, absent cache slot, item TOML reservations and source literals. The source scan fingerprints 7,860 inspected source files (game/engine/network/cache/client and source data; mutable state excluded) and distinguishes a commented NPC wander-table occurrence from an item reservation. This is partial consumer inspection, not proof that every computed override, packet, wearable, sprite or cached delivery path accepts new items. Existing server/client source suggests growth at this small nonwearable ID; full runtime acceptance is still required.

## Integrity and repeatability

| Final coordinator observation, each fresh candidate | Result |
| --- | ---: |
| Preexisting decoded item entries retained exactly | 20,178 / 20,178 |
| Item entries after adding the original token | 20,179 |
| Preexisting raw archive containers compared | 101,205 |
| Unchanged raw archive containers | 101,204 |
| Changed raw archive | only 19/78 |
| Reference-container slots compared, including an absent index | 37 |
| Changed complete reference container | only index 19 |
| Archive CRC / revision-footer mismatches | 0 / 0 |
| Available archive Whirlpool digests compared / mismatches | 36 / 0 |
| Whole reference CRC agreement between native and pinned library | 36 / 36 |

The touched archive advances revision 28→29. Its stored CRC matches native CRC32 and `java.util.zip.CRC32` over the compressed container **excluding its two-byte revision trailer**; the footer matches the stored revision. The target archive has no stored Whirlpool, so that branch is not claimed for it. Reference containers use a different CRC scope.

The root wrapper's two fresh runs agree on the new definition and full decoded item namespace. A separate coordinator comparison also finds all 39 candidate cache files byte-identical: fingerprint `f6ed21f471bfda634e3bc87b6c93026711d0b1ead71def4557482eb4b35f56b3`. That is an observed result for this pinned input/toolchain, not a guarantee across arbitrary compression/library revisions.

A third private copy receives a one-byte flip inside the target's compressed payload, preserving its sector header and revision footer. The actual helper refuses at the CRC gate before item decoding, with exit 1 and a mismatched CRC. Rewriting an already occupied candidate also refuses and preserves all its cache bytes. Fifteen asset-free boundary cases test manifest binding/types, duplicates/nonfinite values, occupied/range refusal, linked ancestors, copy preservation, reservation/source drift incompatible baseline refusal, and exclusion of mutable state before traversal. The full root suite runs 276 cases with one existing optional skip.

[Sanitized evidence and hashes](evidence/backport-lab-token-20261017.json). Native sources, jars, cache bytes and generated cache copies remain outside Git. The original definition/helper/manifest are authored for this experiment. No asset licence or redistribution right is inferred from a fingerprint.

## Reproduce and remove

After normal native source setup/build, with the separately supplied matching cache and pinned Gradle dependencies available locally:

```sh
python3 scripts/backport_lab_token.py --java-home .runtime/jdks/jdk21
```

The wrapper holds the shared build guard, freezes native/dependency jar inputs, creates new lab directories and verifies input/tool/source fingerprints before publishing its report. It never replaces an existing output. The helper itself confines cache writes to ordinary `cache-copy` directories inside this checkout's ignored backport lab. This cooperative filesystem guard is not an adversarial same-user sandbox or safe arbitrary-cache parser.

Final private coordinator report: `.runtime/backport-lab/lab-token-1792271946390030551/summary.json`. Discarding the private candidate directories removes the token; the installed/native baseline needs no repair or downgrade. The original definition can be regenerated from the committed helper and manifest with the documented inputs.

## Review lessons and next gate

Claude Haiku implemented the first helper/wrapper and integrity follow-up. Coordinator review bound all manifest fields, froze inputs, added path/source checks, exact whole-archive set checks and executable corruption/occupied controls, then independently reran the complete proof. An early source walk could include mutable legacy TOMLs. The final audit prunes saves/errors/cache/exchange/temp directories before traversal; an original sentinel test verifies those files are neither traversed nor read. The earlier scan is excluded from final evidence. Early private metadata evidence incorrectly inferred stale metadata from unchanged idx255 pointer bytes and a misread sector entry. Complete multi-sector reads disproved that. A first archive CRC calculation included the trailer and wrongly refused the pristine copy; pinned Displee bytecode established the correct scope. Those failed attempts remain private and are not counted as successful evidence.

The useful result is a minimal original definition written deterministically with an allowlisted cache change and protected baseline. A general allocator/lock with tombstones, actual dependency/assets, cache identity negotiation, live native item loading/render/interaction/save/uninstall policy and later-content semantics remain open. Do not turn this temporary candidate into a shipped ID without those checks. Native Deck and save reliability remain primary.
