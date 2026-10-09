# Controller session acceptance and performance record

Use a disposable graphical-launcher profile and record the branch/build, renderer, canvas size, controller model, preset and remapped buttons. The earlier user reports confirm local launch, panning, improved aiming and direct movement; they do not replace acceptance for these new menus.

| Check | Expected result |
| --- | --- |
| Home → Settings → graphics options → B | Graphics closes normally; Settings regains remembered focus |
| B in Settings → B in Home | Home wheel, then world controls |
| Direct inventory → B; wheel inventory → B | Direct inventory returns to world; wheel inventory returns to Home |
| Native bank closes after movement, then shop opens | Shop B does not revive stale inventory ancestry |
| Long native/custom bank, both panes | Right stick moves/scrolls the active pane; slow and strong tilt differ; no transaction occurs |
| Open menu holding right stick, leave holding it | Scroll and camera wait for neutral before taking ownership |
| A/X/pane button on a scroll frame | Button action remains available; no accidental row transaction |
| Mouse wheel and controller alternation | Fresh focus and native validation; no stuck cursor/camera |
| Bank quantity, shop Buy-X, production amount | B closes entry/dialogue before its parent; cancel sends no transaction |
| 24-action sidebar fixture; long real action menu | Selected row stays visible and mouse target matches it |
| Swapped A/B, bumper/stick bindings, PS preset | Physical prompts follow mappings; native Withdraw-X/Make X labels stay intact |
| Native/custom inventory, bank/shop/equipment; relog | Readable labels/quantities; cached native artwork when available; text fallback remains usable |
| Populated bank and item-on-object quest actions | Selected native identity remains correct through scrolling and redraw |
| Controller unplug/focus loss/menu handoff | Intent clears; no stuck walking or camera |
| Save & Quit, close client, Continue | Owned server completes saves; recorded XP/items/quest/position persist |
| Cancel world loading; restart | Existing character/exchange state remains readable; derived files can reload |
| Manage Backups while stopped | Exact preview, manual/restored-from backups and generations retained |
| Build while GUI world is live | Refuses; Save & Quit releases build lock only after shutdown |

Follow CONSOLE_SESSION_ROUTE.md for the combined quest/gather/commerce/combat route. Use both fixed 765×503 and 1280×800 layouts, then Steam Deck Gaming Mode. Generic reopening of one server-owned modal from another remains a documented limitation; the known parent tab is restored where supported.

## Reproducible performance notes

The private `./scripts/smoke-profile.sh` uses a separate Xvfb/software display, loopback port and disposable profile. It writes `.runtime/alpha-tests/session-*/native-smoke-summary.json` containing New/Continue complete-session seconds, cancellation preservation and original-path preservation. These totals include server startup, native asset transfer, readiness dwell and save/shutdown. They are not FPS, input latency or Deck battery measurements. Rerun only after changes justify it, and compare equivalent hardware, renderer and cache warmth.

On physical hardware record:

- Server `Void loaded in ...ms` from the selected profile's `session-logs/server.log` for cold and warm launches.
- Frame-rate/frame-time overlay from the platform (for Deck, its performance overlay) during 60 seconds each of world walking, Home, populated custom bank scrolling and native graphics settings. Record median/low FPS, long stalls, renderer and overlay scale. Compare custom screens on/off and controller guide shown/hidden.
- CPU/RAM before login and after 10 minutes of the route; observe whether repeated bank/menu open/close grows memory. The artwork cache is bounded at 128 entries; stale menu ancestry is bounded at 16.
- Time from Save & Quit to launcher Continue becoming available; whether status reports ongoing saving truthfully. Do not force-kill a saving server to obtain a faster result.
- Controller feel: accidental interactions, stick neutral drift, scroll speed at gentle/full tilt and camera resumption. These require human assessment and are not inferred from unit tests.

No physical Deck, sustained frame-time, suspend/resume or power-loss acceptance is claimed by this milestone.
