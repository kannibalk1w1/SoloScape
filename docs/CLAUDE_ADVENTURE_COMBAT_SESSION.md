# Adventure batch: combat, prayer and spells, plus session lock inheritance

This was static only, with no source edits. I ran no game, build or tests, used no network, and
opened no saves, cache, login data or config secrets. The only thing I executed was a read-only
Python cross-check of the patch's spell table against the pinned
`spellbook.ifaces.toml`. Scope:
- `patches/client/0024-adventure-combat-prayer-spells.patch`
- `scripts/profile_session.py`, `profiles.py`, `local_dev.py` and `test_launcher_backend.py`

## Verdict
**No correctness blockers.** I checked every table against pinned server data and found no
mismatch. All new metadata is display-only, and the one new quick binding goes through the
existing fresh native validation. Two low notes follow, both about recovery when something is
abnormal.

## Verified
**Prayer order and masks** (`ControllerAdventureDetails`)
- `PRAYER_NAMES` and `PRAYER_LEVELS` match `index` and `level` for all 30
  `*_prayer` entries in `data/skill/prayer/prayers.toml`. The server maps the clicked slot to
  that `index` (`QuickPrayers.togglePrayer` → `definitions.getPrayer(index)`, unlocked for 0–29
  on `prayer_list:regular_prayers` / `quick_prayers`), so the child index equals the prayer
  index.
- `PRAYER_BITS[i]` equals the position of that prayer in the bitwise `values` of
  `activated_prayers` (1395) and `quick_prayers` (1397) in `prayer.varps.toml`. I checked all
  30, including the out-of-order ones: sharp eye 18, mystic will 19, hawk eye 20, mystic lore 21,
  eagle eye 22, mystic might 23, protect from summoning 24, piety 26, rapid renewal 27, augury 28
  and rigour 29.
- **Curses.** The names, levels and bits 0–19 match all 20 `*_curse` entries and the
  `activated_curses` (1582) / `quick_curses` (1587) value order.
- **Curses vs normal.** This is decided only by varp 1584 (`prayers`: 0 = normal, 1 = curses).
  Any other value, or a missing value, returns `null`, so the native name stays. Component 8 is
  "Active"/"Inactive" from 1395/1582, and component 42 is "Selected"/"Unselected" from
  1397/1587.
- **Varp source.** `aClass170_10209.anIntArray5063` is the varp store; `Class170:65` derives
  varbits from it.
- **Unknown varps.** `value()` returns `null` for a missing array or an id out of range. That
  gives an empty status (prayers), "Energy is loading" (special attack), or an empty status
  (style and retaliate). Nothing is guessed.

**Combat (884)** (`combat_style.ifaces.toml`, `combat_style.varps.toml`)
- Styles are components 11–14, compared against `attack_style_index` (varp 43) as
  `component - 11`.
- Retaliate is component 15. Varp 172 maps `true = 0`, so 0 means "On".
- The special bar is component 4. Varp 301 is a boolean (1 = "Selected"), and varp 300 is
  energy out of 1000, shown divided by 10 as a percentage.

**Spells.** The 69 modern, 29 ancient and 39 lunar component→name entries match
`spellbook.ifaces.toml` exactly. I compared names ignoring case and punctuation, and found
0 mismatches. Because these names become the widget name used in binding identity, an error
here would have mislabelled which spell a slot casts. None exists.

**Special-attack quick binding (`884:4` "Use")**
- `QuickBinding.of` only accepts `w.id == 884<<16|4` with a type 18 or 1011 "Use" action.
- `decode` requires `group 884`, the Combat tab, `item == 884<<16|4`, type 18 or 1011 and
  "Use". Anything else decodes to an empty slot.
- `match` needs the exact widget id and the name "Special attack", plus the same type,
  operation and label, with `selection == 0`.
- Running it goes through the existing pending flow: the Combat tab opens, then a fresh
  snapshot is matched, then `ControllerUi.invoke` checks freshness, the open group, `same()`
  and the permission-gated op. The server handles this through `interfaceOption("Use",
  "combat_styles:special_attack_bar")`. A weapon with no special hides the bar, so `isVisible`
  fails and the slot reports "Unavailable", failing closed.
- Prayer bindings now use the table name. That name is fixed per child and per book, and the
  Active/Inactive state is kept in `status`, which `same()` ignores. Identity therefore doesn't
  flip when a prayer is toggled.

**Lock inheritance**
- Neither `fcntl.flock` file description is unlocked explicitly. I found no `LOCK_UN` anywhere
  in `scripts/`.
- `profile_session._run` takes the profile lock with `descriptor=True` and passes both the
  profile and the shared build lock to the server and client through `pass_fds`
  (`profile_session.py:40, 72, 93`).
- `local_dev._launch` passes `launcher.lock` plus the build guard, after the shared downgrade
  (`local_dev.py:244-245, 262, 275`).
- These descriptors are non-inheritable by default (PEP 446) and `close_fds` defaults to true,
  so **only** these guards reach the children. Each child holds the same open file
  description, so the lock survives the parent's `with` exit or its death, and is released only
  when the last owned JVM exits.
- `start_new_session=True` keeps a terminal hangup from reaching the children.
- On the normal path, `local_dev.stop` waits for both children before the profile lock's `with`
  exits, and the after-shutdown backup still runs under the lock.
- `test_killed_launcher_leaves_world_and_build_locked_until_owned_children_exit` uses SIGKILL
  on a separate launcher process, so its cleanup can't run, and checks both locks.

## Findings (low, actionable)
1. **An orphaned world can't be recovered from the launcher.** After the launcher dies, the
   orphaned server keeps the profile and build locks, as intended. But a new launcher only
   reports "running or another save operation is active" (`profiles.py:149-151`). It doesn't
   know the PID, so it can't offer Save & Quit (SIGTERM), and the user has to find the JVM by
   hand.
   **Fix:** write the owned server's PID and start time into the profile directory while the
   lock is held. When a lock attempt is refused, show "World still running (PID n) — Save & Quit
   sends SIGTERM". Keep it SIGTERM-only.
2. **Saved prayer and spell slots may need reassigning after this update.** The names in
   `describePanel` now come from the pinned tables, not the native widget text. Slots saved
   before this patch store the old `name`, and `match` requires `w.name.equals(name)` for groups
   271, 192, 193 and 430. Wherever the old native name differs, even only in case (the tables use
   "Burst Of Strength" and "Npc Contact"), those slots now report "Unavailable". This is safe and
   fails closed.
   **Fix:** a release note, or on decode a one-time migration that compares names ignoring case
   and punctuation, for those groups only.

## Limits
- I didn't check in game or against the cache that the 634 client renders 271:8 and 271:42
  children in `index` order. This rests on the server's slot→index mapping.
- I didn't check the special bar's native op label ("Use") in the cache. It comes from the
  server handler.
- I didn't see the test, `shadowJar` or Java 8/21 probe results; they come from your report.
  No gameplay acceptance is claimed.
