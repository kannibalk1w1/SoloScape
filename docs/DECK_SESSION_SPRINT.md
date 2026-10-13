# Dependable Deck sessions: sprint progress

Started 13 October 2026 from the [proposal](NEXT_DECK_SESSION_SPRINT.md). This log records completed batches and what each one does and does not establish. Physical controller, suspend/resume and Gaming Mode acceptance still come from owner playtests.

## Batch 1: save string serialization (server patch 0022)

**Problem.** `ConfigWriter.writeValue` wrapped strings in quotes without escaping them. A clan name, friend, ignore or recent-event text containing `"` ended the string early. A trailing `\` turned the closing quote into an escaped quote, so the rest of the save was read as one string. The profile tools validate saves with Python's strict `tomllib` before backup, import and Continue. Raw backslashes such as `C:\Clan` or raw control characters made the whole save fail validation there.

**Fix.**
- The writer emits TOML basic strings. It escapes `\\`, `\"`, `\b \t \n \f \r` and other control characters (`\uXXXX`). Plain strings and keys keep exactly the same bytes as before.
- Keys outside TOML's bare-key alphabet are quoted automatically: empty keys, spaces, quotes, dots, `quest:` prefixes and similar. Previously spaces were quoted only when a caller asked.
- The native reader decodes the same TOML escapes, including `\UXXXXXXXX`, and decodes text explicitly as UTF-8. Unknown legacy sequences such as `\p` and `\users` keep their old literal meaning. A string without a closing quote is now rejected instead of silently swallowing the rest of the save; failed loads keep the existing backups intact.
- Atomic replacement is unchanged: a failed write leaves the previous save.

**Compatibility boundary.** Older saves containing a raw `\` followed by `b t n f r u U \` or `"` now decode those as TOML escapes, matching what `tomllib` already did. Shipped game data contains none of these sequences; its only escape is `\"`, which still decodes the same. Upstream's four reader expectations that deliberately kept `\n`, `\t` and `\u00E9` undecoded were updated to the TOML meaning.

**Evidence (host, isolated worktree).**

| Check | Result |
| --- | --- |
| Server `:config:test` | 104 pass, 0 fail |
| Server `:engine:test` (includes new `PlayerSaveEscapeTest`) | 1261 pass, 0 fail, 3 skipped |
| Server `:game:test` | 3855 pass, 0 fail, 9 skipped |
| `scripts/test_profiles.py` (new strict-`tomllib` cross-check) | 20 pass |
| `verify_patches.py server` | all 60 modified/patched files reproduce |
| Fresh, repeated and upgrade application of the full stack on the pinned base | byte-identical to the working tree |

New regressions cover:
- quotes, backslashes, trailing backslashes, control characters, Unicode/emoji and 99/100-byte buffer boundaries;
- escaped values inside lists and maps followed by further fields;
- quoted friend keys;
- legacy raw backslashes and invalid `\u` escapes;
- unterminated strings;
- full `PlayerSave` save/reload, three repeated Save & Quit cycles, and reload from a copied backup;
- the exact writer bytes decoded by `tomllib`.

**Not established.** This batch has no Deck deployment yet and no physical session. Saves are not byte-identical across Save & Quit even without this change, because variable order follows a hash map. The tests therefore compare decoded content.
