# Everyday menu polish — 9 October 2026

The optional custom inventory, equipment, bank and shop screens now use native item artwork when the original client renderer has produced it. The 128-entry memory cache copies pixels, keys by exact item ID/quantity, clears at native login reset and falls back to readable names. It does not ship or generate game assets, nor request an extra native model render on an overlay thread. Newly visible/offscreen items can initially have no icon.

Live controller hints now use the current eight logical button bindings and Xbox/PlayStation labels in one pass. Swapping A/B or assigning a bumper/stick click no longer leaves the default prompts behind or recursively swaps labels. The quick guide uses the same mapping.

The details sidebar follows long action lists without changing native action indices. Only visible rows have mouse hit rectangles; hidden rows cannot be clicked. Item names, quantities, native action descriptions and existing destructive confirmations remain available.

Claude's navigation follow-up fixes are included: parents belong to the modal child that created them; a server-closed modal discards that ancestry; ignored close requests expire; simultaneous confirm/action/pane buttons take precedence over stick scrolling; scrolling respects configured neutral deadzone; logout/reset clears remembered focus. Native modal-to-modal screens cannot generically be reopened with fabricated server actions. Returning to the known home tab is the supported fallback.

Validation: 150 client cases, zero failures/errors, one pre-existing optional SDL skip. New coverage includes exact native sprite/quantity identity and cache bounds, swapped bindings, automatic modal closure followed by a different shop, and long action-list drawing/hit mapping. This remains automated evidence; physical controller acceptance is in CONSOLE_SESSION_ACCEPTANCE.md.
