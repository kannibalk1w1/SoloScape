# Playtest follow-up — 12 October 2026

The controller fixes are represented by client patch 0037 and server patch 0016; client patch 0039 adds the fullscreen toggle. The installed Deck shortcut is still r10; candidate changes require a new matched build and acceptance.

| Feedback | Candidate change / evidence |
| --- | --- |
| Left stick in chat | Left stick navigates NPC/dialogue choices, inventory/panels and world action menus such as stairs. D-pad remains available. Opening a world menu requires a neutral stick before stick navigation, preventing held walking from choosing an option. |
| No logout | Home now includes Log out and recognises native interface 182; Exit to Login uses the native operation. Launcher Save & Quit still owns world shutdown. |
| Wheat / item use | Choosing Use releases inventory focus for world targets. LT aims, LB/RB cycle, A uses the item; Y reopens inventory for an item destination without cancelling selection. |
| Corners / gates | Direct diagonal running resolves its slide before queuing the second step, avoiding a second destination that turns back into the wall. Closed doors/gates still require Open. Optional developer tile exclusions are available below. |
| Setup every launch | First successful automatic prompt records `setupPrompted` persistently, including when dismissed with B. Finish setup still records `setupComplete`; Home > Settings remains available. |
| Backup sizes | Launcher reports save, backup and cache bytes separately. Deck r10 read-only inspection: about 240 MiB total profile, 187 MiB native cache, 53 MiB server cache, 52 KiB backups. Existing Manage Backups provides explicit automatic-backup retention; this change deletes nothing. |
| 20–30 FPS | Added `smoke-profile.sh --desktop --performance`. Initial Deck Desktop comparison (892×529 canvas, renderer `oa`): controller on ~37.3 FPS, off ~43.9 FPS, reduced scene ~44 FPS. Short stationary observations differ from the reported gameplay/full-screen workload. Automatic target acquisition now stops at the first reachable candidate; candidate measurements were ~34.9–37.3 FPS enabled and ~41.7–43.1 FPS disabled. This change has not demonstrated a sustained FPS improvement; the reported full-screen 20–30 FPS issue remains open. The approved [60 FPS sprint](DECK_60FPS_REPORT.md) now has a separate measured OpenGL candidate; hardware acceptance is pending. |
| Fullscreen in game | F11 toggles borderless fullscreen on the current monitor and restores the previous window size, chrome and size lock. Rebind it under RuneLite > Window settings > Fullscreen Toggle Key, or map a Deck button to F11 in Steam Input. Works independently of the controller plugin and Deck graphics preset. |
| No map | Home includes native Map. Full-screen interface 755 owns controller focus, and B invokes its native Close operation. Controller map dragging/panning is not added here; existing map controls remain native. |
| Exhausted run stutters | Held run stays walking after exhaustion until energy reaches 5%; gentle/released input resets the latch. Native run preference is retained. |
| Bury leaves empty inventory focus | Successful controller Eat/Drink/Bury returns to the world. Mouse inventory behaviour stays native. |
| Quest completion needs mouse | Both completion interfaces 277/380 are recognised as modal controller panels; B closes through the normal native world-cancel operation. |
| Remote save systems | See [Save sync](SAVE_SYNC.md): researched OpenSave and added verified, provider-independent publish/receive bundles. Manual branch-preserving transfer is available; automatic integration remains future work. |

## Developer tile painting

Run `python3 scripts/paint_controller_tiles.py`, open the printed HTML locally, set west/south coordinates and plane, and drag to paint exclusions. Start on a red tile to erase. Import/export supports up to 4096 coordinates. The grid does not include game geometry; use the in-game debug position and observation to identify problem tiles.

Export `controller-avoid-tiles.txt` to `upstream/game-server/data/controller-avoid-tiles.txt`, or set `SOLOSCAPE_CONTROLLER_AVOID_TILES` to its path before starting the world. For an alternate path, use `export SOLOSCAPE_CONTROLLER_AVOID_TILES=/path/to/controller-avoid-tiles.txt` before launching. Restart to reload. Entries are `x,y,plane`, one per line. The optional file is developer configuration, not a world save. It affects direct controller movement only; native collision, ordinary pathfinding and mouse movement are unchanged. An invalid file emits a warning and leaves native collision active.

## Validation

216 client cases (one optional SDL skip), nine direct-movement server cases, and the matched jar build pass, including item selection, consumption, dialogue stick navigation, both completion panels, full-screen map recognition, diagonal sliding and exhausted-run recovery. Root tooling suite: 82 tests pass, including portable world/exchange round trips and publication locks. Host native New/Continue verifies map gateway open/close, controller logout/relogin with fresh capabilities, text handling, saved fields, four backups and whole-world startup cancellation. The first candidate Deck Desktop native map/performance/save run also passed; its client/server bytes precede only the final stick-hint/debug-coordinate wording change. Physical controller behaviour and sustained full-screen gameplay remain acceptance work.

Fullscreen validation (patch 0039): matched build/client regressions and host software New/Continue pass. The r21 Gaming Mode OpenGL native check passes repeated F11 events through the registered key adapter, autorepeat, locked bounds, saved bounds, game focus, restored sidebar/title controls, map close and verified save/reload/startup cancellation. The original player launcher remains r10; fullscreen is in the candidate, awaiting promotion. The owner requested no further tests before powering off.
