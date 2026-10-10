# Controller-first adventure sprint — approved 9 October 2026

Implementation and test preparation are delivered on `overnight/controller-sprint`. These checks record that scope; physical controller and Steam Deck acceptance is a separate gate below.

- [x] P1 Shared readable UI styling, focus/detail/scroll patterns, mouse coexistence and bounded native artwork reuse.
- [x] P2 Independently reversible quest journal and skills screens, loaded native progress/details, existing Home/B ancestry and fresh actions.
- [x] P3 Reversible combat/prayer/spellbook screens; native state, pinned levels/cache rune requirements and validated supported special quick binding.
- [x] P4 Controller settings and first-run preset/remapping/deadzone/run/scale setup; Game Settings child and B return.
- [x] P5 Item/spell source/target feedback, cancellation and fresh return-to-origin behavior; quick casts remain in world.
- [x] P6 Feasible actual-map audit: full Restless Ghost; Cook/Rune starts, castle doors/north stairs/upstairs banking; native progression and save/reload. Existing quest logic and earned-progression fixtures also pass.
- [x] P7 Durable owned-session/profile/archive guards, restart port regression and private native New/Continue/settings/logout/relogin/cancellation evidence; desktop render/memory observations with explicit limits.
- [x] P8 Bounded actual Claude reviews and fixes, verified commits/pushes and combined report/roadmap/handoff.

## Acceptance and continuation tasks

- [ ] Physically accept every new custom screen at desktop and Deck resolutions; compare independent native fallbacks and mouse/trackpad coexistence.
- [ ] Verify live journal progress/completion, skill guides, curses/alternate spellbooks, rune displays and every supported combat/prayer/special state.
- [ ] Verify first-run discovery, preset/binding swaps, persisted preferences, neutral rearming, reconnect and Settings → Game Settings → submenu → B ancestry using a real controller.
- [ ] Exercise item-on-item/object and spell targets: use, cancel, invalid targets, quantity/item change, focus loss and modal interruptions. Confirm one fresh source return and world quick casts.
- [ ] Complete Cook’s Assistant and Rune Mysteries travel entirely on the actual map, including ingredient travel, gates, mill/wizard-tower floors and restart.
- [ ] Measure repeatable Deck frame times, sustained memory, loading, battery/thermal budget, suspend/resume and Gaming Mode input before performance claims.
- [ ] Add orphan-owned-session recovery/Save & Quit and controller-only launcher text entry.

New custom screens remain independently reversible; adventure screens default off. Native server rules/actions remain authoritative. Private fixtures preserve existing saves/cache and public main. See MORNING_REPORT.md, ADVENTURE_ROUTE_AUDIT.md and ADVENTURE_NATIVE_VALIDATION.md for evidence and remaining limits.
