# Custom controller-panel foundation (in progress)

The reusable presentation model changes only copied widget bounds. It keeps native
component IDs, item IDs, quantities, action permissions and selection tokens unchanged;
the native invocation gateway still revalidates these immediately before dispatch.

Its readable four-column grid is constrained to the game canvas, including 765×503 and
1280×800 at 175% requested scale. Large native-visible panes page around focus while
retaining their off-page rows in the spatial navigation model. This never invents
hidden native bank contents: native scrolling remains necessary to load further rows.
Independent inventory/equipment/bank/shop screen toggles and rendering/input integration
are the next batch. This foundation is not yet exposed as a custom screen.

Destructive Drop/Destroy confirmation requires a second separate action for the same
native item/quantity/action token within three seconds. Changing the item/quantity or
expiring/cancelling cannot confirm an older intent. Native confirmation and permission
checks still apply after this presentation guard.

Tests cover canvas fit, preservation of native tokens, focus paging/fallback, stale and
expired destructive intents, and the native cache's reserved sector-zero sentinel.
The owned cache now reproduces the original native file access probe; isolated launches
never fall back to shared writable cache paths. Link/path escape cases fail closed.

Client regression suite: 127 tests, zero failures/errors, one existing SDL virtual-pad
skip. Client shadow jar builds. Patch 0016 reproduces the complete source stack.
