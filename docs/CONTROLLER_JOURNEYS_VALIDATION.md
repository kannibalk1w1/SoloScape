# Controller journeys validation — 10 October 2026

This checkpoint adds controller launcher entry, recorded owned-session recovery and menu ancestry fixes to the previous adventure baseline. Actual native tests use disposable profiles/storage and installed compatible cache data. No cache, credentials, saves or runtime archives are published.

## Client and launcher

- Complete client test/shadow build: **176 cases**, zero failures/errors, one existing optional SDL skip. Historical config/network/engine module counts have not been rerun this checkpoint.
- **62 root cases** pass. Real pidfds and inherited flocks verify orphan identity, normal termination, owner rejection, mismatched tokens/archives/guards, suspended/cancelled recovery, crash-gap discovery, retained dirty-save evidence, restore generation protection, ended-record archival and backend SIGTERM cleanup. Fake JVM cases are labelled as simulated processes.
- Two Home ancestor cases fail before the navigation fix and pass after it: spell selection → independent inventory → B, and timed-out Home opening → independent inventory → B. Existing parent/settings/source-return and scrolling coverage remains green.
- `scripts/smoke-launcher.py` runs the actual Swing launcher, entry adapter and backend against a disposable copy of the scripts and its own private Xvfb. It verifies opening held A cannot type; controller keys/Y advance; invalid account paste is rejected; B leaves the keyboard without closing the form or losing values; successful create makes exactly one private profile; rejected backend creation preserves values and re-enables the form. The screenshot is in the launcher guide.
- The launcher probe drives the real entry adapter and button handlers directly. It does **not** establish the complete SDL timer path, a physical controller or Steam Deck acceptance.

## Actual-map content

`FullAdventureJourneyTest` uses native NPC/cache/object/collision state, ordinary Walk instructions and native interactions. It does not create fixture scenery/NPCs, teleport between scenes, inject quest progress or inject reward items. Starting positions place a newly created test character in the quest giver's scene. Object ladders/stairs perform their normal native transitions. Border crossings retain their native three-tick delay; the harness waits for it before issuing another Walk, so the instruction is not silently ignored. This is server/content integration with a headless test player, not a graphical controller playthrough.

Cook's Assistant now passes pot pickup, courtyard/north bridge, cow gates/bucket/milk, chicken gate/egg, west-bank travel, Millie dialogue, native wheat, both mill ladders, hopper/controls, flour collection, return, completed quest, 500 coins, 20 noted sardines and 300 Cooking XP. The native save/load preserves quest state, location, all instantiated persistent inventories and XP.

Rune Mysteries passes the full Duke → tower/basement/Sedridor → Varrock/Aubury → tower/reward route, native air talisman reward and save/load. The combined 20-case game slice passes with zero failures/errors/skips; the server shadow build passes. Exact exported stacks reproduce 99 client and 33 server files, and the matched jar/patch stamp verifies. The route corrections include real door completion waits, a valid hopper approach, raw native ladder ID lookup and accessible outdoor waypoints. They are harness corrections; no production collision, content or movement rules have changed.

## Native lifecycle probes

The real Java 21 server probe passes: an intentionally killed disposable Python parent leaves the owned server and inherited guards intact; verified pidfd recovery requests normal shutdown, validates an `after-recovered-shutdown` snapshot and retains the before-launch backup. Clean shutdown remains explicitly unconfirmed. Evidence: `.runtime/recovery-tests/1791633046875158617/summary.json`. No player or native orphan-client claim is made.

Evidence: `.runtime/alpha-tests/session-1791633113487158745/native-smoke-summary.json`. The repeated graphical New/Continue adventure smoke passes native login, settings adoption/reversal, B-to-Home, ordinary logout and settled same-client relogin with fresh capabilities, native save/load fields and four verified backups. A cancellation observed before readiness preserves every saved-world file. Original legacy mutable-path size/mtime fingerprints remain unchanged. Complete New/Continue sessions took 67.879/65.188 seconds on private Xvfb/software rendering; these totals include readiness/shutdown and are not FPS or Deck measurements.

The final Swing launcher rerun also passes with owned-display cleanup; evidence is in `.runtime/launcher-tests/1791633113389201949`.

## Reproduce

After the pinned source/cache/runtime setup, a stopped-world matched build and exported patches:

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'
source config/local.env
export SERVER_JAVA CLIENT_JAVA
python3 scripts/smoke-launcher.py
python3 scripts/smoke-recovery.py
./scripts/smoke-profile.sh --adventure
```

The native probes require Linux pidfds, Java 21/8, Xvfb for graphical checks, a compatible local cache and their dedicated free loopback ports (43595/43596). Recovery covers the real server only; the separate native profile smoke covers player New/Continue and save/reload. Original legacy mutable paths must retain their size/mtime fingerprints. The test-created profiles and raw evidence stay in ignored `.runtime`.

Run the selected game suite with `SOLOSCAPE_TEST_ROOT` set to an absolute disposable directory, Java 21 and the root build guard held. Select `content.soloscape.*`, `ShopTest`, `CooksAssistantTest`, `RuneMysteriesTest` and `RestlessGhostQuest`. Without the isolated-root variable, the new actual-map tests skip deliberately.

## Limits

Physical controller/Steam Deck/Gaming Mode, real-game first-run discovery, mouse/controller takeover, completed live quest-journal rendering, sustained frame time/memory/battery/thermal/suspend behavior and fresh-machine installation remain separate acceptance. A successful recovered snapshot is not a clean-shutdown marker. Native server recovery does not prove native orphan-client recovery or every failure timing. The selected routes do not establish all upstream content as complete.
