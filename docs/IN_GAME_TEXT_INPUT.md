# In-game keyboard ownership

The controller plugin now gives text entry a single controller-input owner. **Text keyboard** is reversible: Automatic chooses Steam on a detected Deck; Steam / physical keyboard uses native typed keys; SoloScape controller keyboard uses the existing key grid for recognized prompts. Home → Settings → Basics exposes this preference beside **Classic controller UI**. RuneLite's plugin configuration exposes the same options.

## Recognized native prompts

| Native type | Route | Ownership and validation |
| --- | --- | --- |
| 7 | Amount/quantity, including native X amounts | Numeric Steam keyboard request or local numeric grid; native amount validation and submit remain authoritative |
| 8 | Native name/account-related prompts | Native name limit and ordinary native callback; no new naming packet |
| 9 | Native string/text prompts | Native text callback and existing ASCII/length validation |
| 11 | Bank-search entry | Existing explicit Search callback prepares native entry; typing/filtering remains native |

These correspond to the pinned server's `int_entry`/`name_entry`/`string_entry` scripts 108/109/110 and bank search arm 1472. The existing adapter observes prompt identity/revision and fresh native widget visibility. Unsupported widget-specific scripts are not guessed or reclassified as these types.

While Steam mode owns a prompt, controller walking, camera, targets, radials and local key-grid editing pause. Native typed keys go through the game's ordinary key pipeline. Prompt replacement creates a new ownership token; changed text alone does not reopen the keyboard. Native prompt disappearance releases ownership, then the controller must become neutral before game actions resume. Losing canvas focus to Steam's keyboard does not release ownership. Logout, plugin shutdown and switching to controller mode clean up the session.

Enter/Escape on the system keyboard retain native semantics. A small top-left panel provides **Reopen**, **Done** and **Cancel** if the Steam keyboard was dismissed. Done validates the current native entry; Cancel invokes the pinned native `close_entry` script 101 after the same freshness/session checks. The cache's script 112 Escape branch does not close ordinary types 7/8/9; physical Escape retains that native behavior. These pointer/touch actions carry an ownership token and cannot act on a replacement prompt. Mouse/touch outside this panel remain native.

The local fallback keeps D-pad/A/X/Y/B behavior. Only while a connected controller, focused canvas and active grid actually own entry are mapped navigation/edit keys consumed. Ordinary physical letters/digits and all key releases still reach the client. In this mode physical Enter/Escape/Backspace belong to the local grid; select Steam / physical mode for full native keyboard editing. Close Steam's keyboard before choosing the local fallback.

## Chat and other native text paths

**Right-stick click** opens a deliberate native text keyboard session when that button is not used by another remapped action. Home → Settings → Finish → **Open text keyboard** provides an alternative. Choose Steam / physical mode first if using the local fallback off Deck. The session accepts native chat or other currently active native input; it does not fabricate a chat packet, infer a recipient or edit hidden fields.

Enter/Escape or the panel's Done/Cancel finish the manual session through the native key pipeline. Cancel preserves whatever the original client preserves; it does not promise to clear unsent chat text. SDL stays paused until ownership ends and controls become neutral.

Ordinary printable native typing can adopt ownership **without opening or closing Steam's keyboard**. Space/control characters and recent/held controller button activity do not trigger that latch, reducing conflicts with Steam desktop mappings. An arbitrary custom Steam layout mapping a controller button to a printable letter can arrive before SDL polling; that is not a reliable overlay-visibility detector. For Steam + X in chat or an unsupported entry, start the explicit right-stick/Settings session first.

This provides one ownership policy for the recognized prompt families and a deliberate path for other native text. It does not claim automatic detection of every upstream text widget, login/password screen, custom recipient UI or third-party plugin textbox. Native credentials are still supplied by the profile launcher; keyboard input is not recorded by this feature.

## Steam integration and limits

Deck detection uses Steam's `SteamDeck=1` environment or DMI Jupiter/Galileo, with a test override property. Steam URI requests follow [SDL's X11 implementation](https://discourse.libsdl.org/t/sdl-x11-add-support-for-the-steam-deck-on-screen-keyboard/39748); amount prompts request its numeric mode, others single-line mode. Requests run on an ordered daemon worker with a bounded wait and visible error hint. URI success is not proof of keyboard visibility and supplies no dismissal callback. [Valve's SteamUtils API](https://partner.steamgames.com/doc/api/isteamutils#ShowFloatingGamepadTextInput) describes the keyboard modes; a future Steamworks integration can improve dismissal observation.

Unit, real-native fixture and physical acceptance evidence are separate in the sprint report. Steam + X visibility, physical simultaneous button/key delivery and Gaming Mode still require owner acceptance. Existing native submission and save guards remain authoritative.

Native Cancel closes the client prompt. The protocol has no entry-cancel packet: an awaiting server action is released by ordinary native interaction/dialogue-close lifecycle. Logout while that server action is pending is not established by these client-only fixtures. A real server Withdraw-X → Cancel → logout route remains an acceptance item; synthetic client fixtures do not prove that suspension path. Bank search type 11 retains the existing adapter and lacks a new real-bank cancellation fixture in this batch.
