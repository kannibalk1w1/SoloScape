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

This setting is an interim compatibility gate, not a negotiated guarantee. A user
who enables it against an unpatched server can still break that session. Before
private co-op, add server-advertised version/capabilities and reject unsupported
extensions automatically. Avoid casually reserving a varc: native scripts also
use that namespace, so its cache/script usage needs auditing first.

The local launcher separately checks a build stamp containing base pins, patch
hashes and both jar hashes. It refuses stale `--no-build` launches. Source builds
write a new stamp only after both jars exist and builds succeeded. The stamp is
local, ignored state, not proof that an arbitrary remote server is compatible.
