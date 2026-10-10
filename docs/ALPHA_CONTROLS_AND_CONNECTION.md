# Controls and connection lifecycle

The plugin now exposes eight separate bindings: confirm/interact, back/cancel, action menu/assign, previous and next target/pane, inventory, Home wheel, and Quick wheel. All must use different SDL mapped buttons. Guide and D-pad are reserved. A changed mapping clears current intent and requires both sticks, triggers and buttons to return to neutral. Overlap disables controller actions and displays a warning; mouse and keyboard remain available.

Xbox, PlayStation and Steam Deck presets apply the standard bindings, labels, deadzone and run threshold. Deck also selects 125% overlay scale. After applying once, the preset returns to Custom so later edits persist. Overlay hints name logical actions; consult the binding settings after remapping. Physical controller and Deck acceptance remain outstanding.

Direct movement's run threshold is adjustable from 50–100% post-deadzone stick tilt. Quick wheel Y now explicitly says Clear rather than Restore; X assigns the captured eligible native action as before. Special attack already exists on the native Combat tab (884), which controller tab navigation can focus. No universal quick special-attack shortcut has been added: supported weapon, energy and native component availability must still be validated.

The SoloScape server-features setting now requires session capability negotiation as well. A random per-session nonce is sent through the existing ordinary command transport; only a matching revision-1 acknowledgement enables directional/cancel extensions. Older servers, mismatched replies and ten-second timeouts retain compatible ordinary movement. Login/reconnect clears the nonce and extension state. A client input interruption over 750 ms discards intentions and requires neutral controller input before resuming.

The server's default bind is IPv4 loopback. LAN hosting requires an explicit network.bind override; the profile launcher always uses loopback. Capability negotiation is compatibility detection, not authentication or a remote access control mechanism.

Validation: 137 client tests, zero failures/errors, one existing optional SDL skip. The private native graphical harness reached fully rendered game state with **serverCapabilities=verified** for New and Continue, saved through normal shutdown, preserved account/XP/inventories/tile on reload, produced four verified backups and confirmed original mutable paths unchanged. The harness uses disposable profiles, display :197 and port 43595; it never drives the user's game.
