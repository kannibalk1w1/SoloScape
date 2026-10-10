# In-game text ownership and classic controller UI sprint — 10 October 2026

Owner-authorized continuation, with actual Claude implementing the visual pass in parallel. Preserve native actions/game rules, saves/cache, public main and Steam configuration. Keep presentation and keyboard choices reversible. Synthetic native tests are separate from physical acceptance.

- [x] K1 Inventory native entry routes and add a shared Steam keyboard transport/device policy.
- [x] K2 Add automatic exclusive ownership for native amount/name/search/text prompts, with local fallback and neutral rearming.
- [x] K3 Add a deliberate system-keyboard path for chat/other native text; preserve the native key pipeline and avoid invented chat packets.
- [x] K4 Expose discoverable keyboard/style preferences and finish/cancel/reopen controls.
- [x] K5 Claude: classic stone/brown/parchment/gold panels and radials, with modern-style rollback and unchanged hitboxes/actions.
- [x] K6 Meaningful regression tests, visual previews and matched source/jar verification.
- [ ] K7 Native New/Continue/settings/save checks on host/Deck, private update with profile preservation when the owner has closed the app.
- [ ] K8 Bounded actual Claude review of keyboard integration, commits/pushes, updated combined report and handoff.

No physical Steam keyboard visibility, Gaming Mode, long-duration battery or suspend acceptance is inferred from SSH or synthetic events. Unsupported native entry scripts must be documented rather than guessed.

Integration checkpoint: 192 client cases (zero failures/errors, one optional SDL skip), 78 root cases, shadow jar/matched stamp and exact 106/33 source reproduction pass. Twenty synthetic classic/modern previews render; small and Deck-sized layouts were visually checked. Real native cancellation exposed the old Escape-script mismatch; guarded Cancel now uses pinned `close_entry` 101. Native host/Deck acceptance is still being completed.
