# Shared controller acceptance

Use this contract when changing or testing controller interfaces. The owner wants the lessons applied across future work, rather than an automated playthrough of every quest.

## Choose representative coverage

Select a small set of flows covering the changed interface families: inventory/item-use, dialogue/production, bank quantities/search, shop buy/sell, tab/settings transitions and save/lifecycle. Run another quest only when it exercises a different interaction contract, renderer/instance transition or demonstrated failure. Avoid long training or quest completion when the missing evidence is one widget action or a panel transition.

## Dispatch and observation

- Read the currently presented native model. Preserve real widget/component, item, slot and option identities; do not infer them from display names or pane captions alone.
- Treat an action's boolean dispatch result as evidence of acceptance only. A rejected stale-widget dispatch needs a fresh snapshot and a bounded retry; it must not advance the probe.
- Observe the result in the inventory/container actually belonging to the active panel. A shop's side inventory may differ from the normal inventory tab.
- Require the expected material, item, coin, XP or quest-state change and its persistence after Save & Quit/Continue. A shop sale is separate from a successful purchase; a full buy/sell test must verify both.
- Keep development teleports/items and direct gateway actions explicitly labelled. They can isolate a transition, but cannot establish an earned route or a successful physical controller action.

## Input ownership

- Preserve fresh A/B edges, modal ownership and release-and-push world input after readiness changes. Returning from an interface must not move or activate an action on stale held input.
- Check opening, selecting/scrolling, activating, cancelling and returning to world input. Cancellation must close the intended surface and preserve item/coin quantities when appropriate.
- A controller cancellation test fails if B fails. A direct native close fallback may collect diagnostic evidence, but must not convert that failure into a passing controller result.
- Reproduce a failure with the real plugin input tick and current native state before changing production code. Separate a broken probe from a broken gateway.

## Build and runtime portability

Compile Java 8 harnesses with explicit `-encoding UTF-8`. Steam can launch with a C locale, so host compilation does not establish Steam-launch compatibility. Keep matching source/patch/jar stamps and existing build/profile locks; never rebuild jars that a running world may still load.

The reusable `scripts/deck-controller-validation.sh` supports `quick`, `cook`, `shop`, `settings`, `route` and `launcher`. Gameplay modes create isolated disposable worlds through the existing smoke runner; the launcher mode uses its isolated launcher fixture. Use it as a separate Steam shortcut; preserve the normal player shortcut and owner profile. `SOLOSCAPE_VALIDATION_ROOT` selects the private installed build, and the route defaults to 1,800 seconds.

## Evidence and completion

Record the exact source/build, renderer, canvas, focus, controller connection, input method and power state. Separate private host/Xvfb/software results from actual Gaming Mode hardware measurements and human button acceptance. Retain loading stalls and frame-time tails; an average FPS figure alone does not establish sustained performance. Independent XWayland presentation samples measure their observed window lifetimes, not physical panel scanout or unobserved map intervals.

Use disposable-world screenshots, review them before committing, and keep saves/authentication/raw private logs out of Git. Report passed, partial, failed and blocked outcomes honestly. A save-preserving deployment requires a fresh verified backup, hash-checked profile copy, idle ownership guards and a reversible launcher switch.

## Lessons observed on 14 October 2026

The first Gaming Mode validation failed at Java compilation because Steam's locale selected ASCII. Explicit UTF-8 fixes the shared harness path; all 18 native harness sources compiled under `LC_ALL=C` afterward. The short r29 Deck check then passed tab navigation, New/Continue and whole-world startup cancellation, with hardware OpenGL near 60 FPS. These short samples remain distinct from the sustained route.

The overnight shop and cooking results also exposed probe weaknesses: ignored dispatch results, observing the wrong inventory pane, sale-only save validation and a cancellation fallback. The bounded follow-up confirmed and fixed the generic shop stock-box adapter in client patch 0053. Cooking B and Settings second-tick failures were harness defects: preserve input until dispatch, and own simulated input across real plugin ticks while restoring prior polling state. These lessons apply to future panel tasks; see the representative Deck and Settings reports.
