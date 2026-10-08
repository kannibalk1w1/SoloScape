# Console alpha save/isolation foundation evidence

8 October 2026, development branch `overnight/controller-sprint`.

- Disposable Python profile fixtures: 10 recovery/isolation tests passing; existing
  tooling/lifecycle tests also pass (24 total). Original saves/cache not inspected.
- Patched server: config 74, network 249, selected engine 35 tests passing, no skips,
  failures or errors; `:game:shadowJar` succeeds. New coverage exercises failed
  serialization preservation, complete UTF-8 replacement, missing save parents,
  actual IPv4 loopback bind, failed-bind cleanup and environment precedence on reload.
- Server patch 0004 reproduces all 23 changed/patched source files from the pinned
  baseline; fresh apply, previous-stack upgrade, reverse and idempotence verified.
- Native character saves now use synced sibling temporary files and required atomic
  replacement. Exchange files retain upstream writes; complete world backups are
  taken only while the owned server is stopped, including exchange and failed saves.
- Profile restore validates archive paths, entry identity, hashes and native character
  structure, writes a new generation and atomically switches its manifest pointer.
  Old generations remain available. This does not yet prove gameplay save/reload.

Launcher integration and an independent Claude implementation review are in progress.
`import_character` currently copies one character only: world/exchange migration must
be strengthened before exposing migration in the launcher. Profile manifest corruption
requires additional recovery handling; damaged character TOML recovery is tested.
