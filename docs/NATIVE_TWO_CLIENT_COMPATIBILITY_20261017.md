# Two native clients in one local world — 17 October 2026

Two actual native clients connect to one disposable loopback server, observe each other's ordinary movement, keep inventory changes separate and retain their states through a full world restart. This is a compatibility probe for M5, not a hosting UI or release of private multiplayer.

## Observed contract

Both fresh accounts start at Lumbridge with their native starter kits. CoopAlpha walks east to `(3222,3219,0)`; CoopBeta walks north to `(3221,3220,0)`. Each client independently observes the other at the correct destination. Alpha uses the native inventory Drop action on its bronze dagger; Beta keeps its dagger. Both native save files match their respective client observations.

Both clients and the server close, with the current-session native save receipt and verified backup. A new server and two new clients then load the same world. Inventory, XP and tile match exactly across the process restart. Alpha still has no dagger; Beta still has one. Native player indices change with login order, so the probe compares account identities rather than assuming an index survives a restart.

The final reviewed harness also waits for a known retained sword before using inventory counts. A widget can render before its container data arrives; an initially empty display must not count as evidence that an item was lost or that Alpha's zero count is correct. The first false-negative attempt and subsequent successful runs are retained privately.

## Running it

After the normal matched native build:

```sh
bash scripts/smoke-coop.sh
```

The script creates its own `.runtime/alpha-tests/coop-*` world, credentials, client homes, logs and private Xvfb. It uses ordinary native destination-walk and widget actions. It starts no public listener, changes no hosting settings and touches no owner profile or Deck installation. The fixture guest uses the same world but a separate auth file and client cache/home. It inherits the same owned world/build locks; all child process objects are retained for cleanup.

File barriers keep both clients alive until their independent observations can be compared. Exceptions retain the disposable evidence, finish or terminate only owned clients and always request normal world closure. The server is never forcibly killed. A deliberate post-observation validator failure separately verifies this cleanup path.

## Evidence and performance limits

- Final success: `.runtime/alpha-tests/coop-1792253536839131147/summary.json`; log `.runtime/native-coop-final-20261017.log`. Two complete sessions took **63.104s and 19.198s**, including loading, both client handshakes and saves. These are uncontrolled host session times, not frame-time/FPS/Deck measurements.
- Earlier successful run: `.runtime/alpha-tests/coop-1792252490027824772/summary.json`, 85.872s and 19.787s. The positive inventory-ready witness was added afterward.
- Three root fixture tests reject incorrect account/index/position/inventory/dispatch evidence and observer movement. All 151 root tooling cases pass, with one existing optional skip.
- Both successful sessions preserve legacy mutable-path byte hashes. [Sanitized evidence](evidence/native-two-client-20261017.json) includes matched build identities and the cleanup control.

## Open gates

This covers movement, one inventory change, mutual visibility, normal native saves and reload only. It does not establish trade, combat/loot sharing, private-network security, mixed builds, disconnect/reconnect campaigns, direct-stick co-op, physical controllers, Gaming Mode, suspend or performance acceptance. The launcher session record still models one primary client; a guest-session ownership/recovery design remains required before offering a product hosting flow. Unrecovered grave/ground persistence remains the separate [open save boundary](WORLD_TRANSIENT_SAVE_AUDIT_20261017.md).
