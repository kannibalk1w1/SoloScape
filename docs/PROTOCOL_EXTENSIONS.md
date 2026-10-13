# SoloScape protocol extensions

Revision-634 client/server bases remain pinned. These deliberate extensions support
held directional movement and position-free cancellation:

| Client → server opcode | Size | Meaning |
| --- | --- | --- |
| 85 | 3 bytes | Signed dx, dy (-1..1) and run request (0/1); zero vector stops direct mode |
| 86 | 0 bytes | Cancel an ordinary world action and run pending content cleanup |

The directional heartbeat is 200ms and server expiry 750ms. The server accepts
intent, not absolute position, and applies existing collision/energy/forced-action
rules. A late stop only clears DirectMovementMode. Stop precedes interaction/cancel.

These are recorded exceptions to the original kickoff rule about controller-only
packets. Use them only on matched SoloScape server builds. The client now requires
explicit **SoloScape server features** opt-in (off by default). Ordinary destination
walking, UI operations and fallback B use existing native packets. A disabled
extension never sends 85/86; B falls back to ordinary Walk at the path head.

A fresh session now negotiates capabilities through an ordinary native command:
`soloscape_capabilities <nonce>`. The server replies through one unsplit native game
message, `SOLOSCAPE|1|<nonce>|direct,cancel,entry-cancel,fire-use`. The client requires
an exact nonce/version match within ten seconds; logout/reset clears permissions.
The reply bypasses chat font line wrapping because it is a protocol token, not a
player-facing line. Earlier `direct,cancel` and `direct,cancel,entry-cancel` replies
remain supported by the current client.

`entry-cancel` supports the existing typed entry cancellation extension.
`fire-use` permits the controller to expose ordinary object option 1 (**Use**) for
the six player-lit fire definitions. The matched server supplies that validated
option and uses the existing cooking recipe flow. This adds no new packet opcode.
A server without `fire-use` does not receive a fabricated direct fire option;
native item-on-object cooking remains available. Use matched client/server builds
when upgrading the extended capability set.

The local launcher separately checks a build stamp containing base pins, patch
hashes and both jar hashes. It refuses stale `--no-build` launches. Source builds
write a new stamp only after both jars exist and builds succeeded. The stamp is
local, ignored state, not proof that an arbitrary remote server is compatible.
