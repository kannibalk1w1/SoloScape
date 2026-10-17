# Original Lab token through a live native world

Fixture-only follow-up to the [deterministic cache-copy lab](../../docs/BACKPORT_LAB_TOKEN_20261017.md).
It adds no production patch, gameplay content, permanent ID reservation or runtime dependency.

Run the cache lab first, then create a **new private snapshot** with `python3 scripts/deck_export.py`.
With the snapshot path and the generated `run-a/cache-copy` path:

```sh
python3 experiments/native-lab-token/run.py \
  --snapshot /absolute/path/to/SoloScape/.runtime/deck-exports/NEW_SNAPSHOT \
  --candidate /absolute/path/to/SoloScape/.runtime/backport-lab/lab-token-RUN/run-a/cache-copy
```

Requires the matched native server/client jars, JDK21/JDK8 in that snapshot and Xvfb.
The runner only accepts the documented baseline and original Lab token cache fingerprints.
It verifies the snapshot's listed input files, overlays the generated cache and one original
`[lab_token] id=20179` mapping in the copy, and records that overlay separately. The original
`deck-manifest.json` describes the pre-overlay snapshot, so this experimental copy must never
be mistaken for a verified release or sent to the owner Deck.

The normal profile session machinery creates an original AlphaTest account under the lab's
new private directory. An external client harness logs in, uses ordinary Continue and opens
the native inventory. It checks the live client's definition loaded through JS5, the label,
stack count, quantity and starter slots. After the first normal shutdown, the external Java
helper loads that fresh native save, initializes real cache definitions and the semantic mapping,
uses native item-dependent inventory transactions to add three/remove one/refuse removal of
three, and saves the resulting two-token stack through PlayerSave/FileStorage. Two fresh
server/client sessions must retain that stack and the starter items. A separate JVM performs
a final native cold read. Profile backups are verified through the existing backup reader.

The baseline-cache negative check must refuse before modifying the same saved fixture.
This is a **lab helper guard**, not a production cache-identity or content-uninstall facility.
The generated cache, private account credentials, saves, jars, logs and snapshots stay ignored
under `.runtime/`. Only original source and sanitized evidence belong in Git.

No appearance claim: the definition has no authored model or sprite. This proves a definition,
container/protocol and save boundary, not a finished item, imported OSRS feature, general ID
allocator, clean uninstall with affected saves, physical controller acceptance or Deck performance.
