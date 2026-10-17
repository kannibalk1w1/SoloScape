# Backup primary-account validation — 17 October 2026

Baseline: merged `898847c`. Backup checks verified file structure and checksums
but did not compare the profile's primary save with its account identity. A
self-consistent archive containing another account under `saves/tester.toml`
was listed as valid and could be restored into a Tester profile. The launcher
then rejected that character at launch. Manual backup could also publish that
mismatched primary save as a verified archive.

Backup creation and archive validation now pass the expected account when
validating the primary save. This uses the existing native save validator and
its case-insensitive account comparison. Other accounts in a stopped-world
copy remain allowed, and a fresh profile can still have a before-launch backup
before its first save exists. No save bytes or archive format are rewritten.

Two disposable regressions reproduce the earlier behaviour and verify:

- correct checksums do not make a wrong-account primary save valid;
- rejected restore leaves the current manifest, save, archive and generation
  count unchanged;
- backup creation refuses the mismatch without publishing an archive or
  changing the mismatched source file.

Both tests failed before the fix. All 23 profile tests now pass, including the
existing multi-account world-copy migration and verified restore checks. Owner
saves, cache and Deck installation were not accessed. This is semantic archive
validation, not authentication or a cryptographic signature for save bundles.

Reproduce:

```bash
python3 -m unittest discover -s scripts -p test_profiles.py
```
