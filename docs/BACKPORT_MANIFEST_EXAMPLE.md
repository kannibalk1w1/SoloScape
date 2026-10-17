# Example content manifest

The machine-readable [Superior Slayer-style proposal](../backport/manifests/superior-slayer.example.json) is deliberately `buildable: false`. It is a concrete compatibility contract, not a claim that an ID, asset format, mechanic or licence has been verified. Nulls are blockers or explicitly inapplicable source IDs, never ID zero. No converter should accept an unresolved build manifest.

The proposed first feature is a `SUPERIOR_CRAWLING_HAND` semantic identity, resolved to the existing server-style key `soloscape_superior_crawling_hand`. Gameplay references that key through a generated typed registry. The source revision/NPC ID stays null because the first proof imports **behaviour**, using baseline 634 assets, rather than copying a current OSRS NPC definition. Before implementation, pin the mechanics reference and record each deliberate solo/pre-EoC interpretation. If a later asset import is approved, it must supply exact revision, source definition ID, cache digest and transitive assets in a separate manifest version.

`target_definition_id` remains null until a real target catalogue and allocation lock exist. A build then replaces it with a frozen allocation and records the catalogue fingerprint, tool versions and namespace limits. The example does not assert that any high number is available in the maintainer-modified cache. Models, sequences/bases, textures, sounds and bas/combat definition references must be enumerated even when reused. An empty new-map dependency list is intentional.

`behaviour` is a proposed native rule, including bounded ownership/placement, one task credit and non-recursion. Its 1/200 roll is an example of SoloScape tuning, not imported canonical balance. The first proof uses existing drops; new items, unlock currencies and persistent unlock UI would enlarge the dependency surface and require another decision.

A resolved allocation output might expose **names**, without embedding source IDs in scripts:

```kotlin
// Proposed generated API, not implemented runtime code.
SoloContent.Npc.SUPERIOR_CRAWLING_HAND // resolves native registry key and allocated target ID
```

Prefer the server's existing semantic definition mechanism underneath this API. Do not introduce parallel item/NPC stores or replace every existing string ID. Numeric target IDs are confined to generated mappings/cache boundaries and reviewed protocol code.

A future build must reject unknown schema versions, duplicate semantic keys, wrong cache digests, duplicate target IDs, stale allocations, dependency cycles, missing referenced assets and unknown opcodes. Disabling content and removing its cache definitions are different operations: saved items/variables may require compatibility tombstones or an explicit migration. See [the lab acceptance sequence](BACKPORT_ARCHITECTURE.md#backport-lab-acceptance-sequence).
