# Item and spell targeting

Selecting a native item or spell shows the source and target prompt in custom inventory. The source item carries a **Source** marker; eligible targets retain the game's current selection-token actions. Native permission and quantity changes still invalidate stale selections before dispatch.

**Return to selection source** is enabled by default and can be disabled in the controller plugin settings. For a selection started from an inventory/spellbook screen, completing or cancelling it can reopen that source screen and restore focus using fresh matching widgets. It remembers identity and quantity only, never an action to replay. A changed token, another Home tab, focus loss, logout, a modal/entry interruption, or disabling the preference drops the remembered return. Focus restoration expires after one second. Changed or consumed sources fall back to ordinary fresh screen focus.

Selections started through the quick wheel retain the existing world/inventory targeting flow and do not reopen the spellbook after a world cast. This avoids pulling the player into menus after every quick action.

Quick prayer/spell bindings tolerate differences in capitalisation in older saved labels. Component identity, action type and fresh permission checks remain mandatory; other renamed labels may still need reassignment.

Claude's settings lifecycle review found and prompted fixes for accidental dismissal on panel adoption, ownership after native mouse/tab changes, quick-cast return, failed first-run opening and delayed focus restoration. Native panel adoption now cancels selection without closing local preferences; explicit root B uses a separate leave hook. The follow-up confirmed the five fixes. Its remaining non-panel ownership note is also addressed: after the opening grace, the native Settings panel must actually be present. The per-frame settings snapshot no longer calls a re-entrant UI reset.

Verification: 169 client tests, zero failures/errors, one existing optional SDL skip; client shadow jar built; complete patch export reproduces 96 files. Physical targeting usability and broader live item/spell combinations remain acceptance work.
