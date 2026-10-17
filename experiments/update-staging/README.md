# Update staging prototype (experimental, asset-free)

**Status: STRICTLY EXPERIMENTAL.** This is a proof of verified candidate staging against original dummy
fixtures. It is not a release manager, a downloader, a migration tool, or a production package format.
Its schema and limits are provisional and are explicitly unsuitable for current real jars.

## What it does

`stage.stage(bundle_path, expected_archive_sha256, lab_root)` verifies a ZIP bundle and stages its exact
payload bytes into a **new** candidate directory `lab_root/<archive-sha256>/`. It never installs, activates,
switches an active version, writes a success or active pointer, downloads, extracts with a subprocess,
or runs anything from the archive. The CLI is `python3 experiments/update-staging/stage.py BUNDLE SHA256`. It has
**no `--root` option**: it always stages into `ROOT/.runtime/update-lab/`, where `ROOT` is the repository root
derived from the script's own path (ignored by git). It refuses symlinked `.runtime` or `update-lab`.
`stage()` takes an explicit existing lab root for programmatic tests; the CLI root is fixed.

Steps, in order:

1. Validate the expected digest (64 lowercase hex). Refuse a lab root that is a symlink or not a directory.
2. Freeze the bundle: `O_NOFOLLOW`, regular file, at most 8 MiB, read once with a bound, refused if its
   device/inode/size/mtime changed while being read. Verify the SHA-256 before any ZIP parsing.
3. Take a non-blocking `flock` on `lab_root/.update-staging.lock`. Refuse if another run holds it.
4. Refuse if `lab_root/<archive-sha256>` already exists.
5. Write everything into a `mkdtemp` partial directory `lab_root/.partial-*`. Any failure removes only that
   partial directory. Inputs and unrelated files are never touched.
6. Rename the partial directory to the candidate name only after every check has passed.

## Provisional bundle schema (format 1)

ZIP entries: exactly `manifest.json` plus the listed payload files. Only regular file entries, with
no directory entries, symlinks or special files. No encryption. Compression is STORED or DEFLATED only.
No duplicate entry names.

`manifest.json` is strict JSON with no duplicate keys and no NaN/Infinity:

```json
{
  "format": 1,
  "repository": "kannibalk1w1/SoloScape",
  "source_commit40": "<40 lowercase hex>",
  "platform": "linux-x86_64",
  "cache_revision": 634,
  "roles": {"launcher": "app/...", "client": "app/...", "server": "app/..."},
  "files": {"app/...": {"sha256": "<64 lowercase hex>", "size": 123, "mode": "0644"}}
}
```

- The identities (`repository`, `source_commit40`, `platform`, `cache_revision`) are **declared, not verified**.
  Nothing checks them against a runtime, a source tree or a cache. `cache_revision` is never detected from the
  payload; the report records `cache_revision_detected: false`.
- `mode` is the string `"0644"` or `"0755"`. The staged file gets exactly that mode. The archive's own mode
  bits, including setuid, are ignored.
- Each role must name a listed file. The three roles must name three distinct files.
- ZIP entry names must equal their normalized `ZipInfo.filename`. Names containing NUL or changed by `zipfile` normalization are refused before name mapping. The separate payload-path check rejects backslashes and drive prefixes.
- Paths must match `app(/[A-Za-z0-9_][A-Za-z0-9._-]*)+`. This rejects absolute paths, `.`/`..` segments,
  backslashes, colons, NUL, and any dot-prefixed segment. Paths containing `.runtime`, `.git`, `profiles`,
  `caches`, `cache`, `saves`, `backups`, `credentials`, or `config/local.env` are refused. A listed file may
  not be nested under another listed file.
- Bytes are validated before use: the manifest size and each file's ZIP metadata size must match the
  manifest, the streamed byte count must match, and the streamed SHA-256 must match.

## Prototype limits

| Limit | Value |
| --- | --- |
| archive | 8 MiB |
| manifest | 64 KiB |
| one file | 4 MiB |
| total declared output | 16 MiB |
| files | 100 |

## Output

On success the candidate contains `app/...` (the exact payload bytes and modes), `manifest.json` (the
verified bytes) and `report.json`. `report.json` records the archive SHA-256, the manifest SHA-256, the declared
identities, the roles, per-file digests, sizes and modes, and the limits. It holds no payload bytes.
The API returns the same dictionary, plus `candidate`.

## Scope and limits of the proof

Proven by `scripts/test_update_staging.py` (24 tests, original dummy fixtures only): exact bytes and modes on a
positive bundle, including setuid and executable archive bits that must not leak; refusal of a wrong or malformed
digest; a bundle changed while being read; mismatched file hash and size; unsafe and private paths; duplicate
ZIP names; duplicate JSON keys; symlink, FIFO and directory entries; unlisted and missing members; oversized
manifest, file, total output and archive; too many files; invalid schema values; an existing candidate; a symlinked
lab; a lab locked by another run; encrypted/unsupported-compression headers and a corrupt DEFLATE stream after earlier payload writes; a symlinked CLI `update-lab`; a byte-patched ZIP entry whose name contains NULs
and would otherwise truncate to a listed path (local and central headers both patched; the control was verified to
stage the entry when the guard is removed); and real subprocess CLI runs from a copied code root. Those runs show that
`--root` is rejected with nothing created anywhere in the tree, that a refused bundle exits 1 with no candidate, and that
a valid bundle stages only under the copied `ROOT/.runtime/update-lab`. Each refusal
also checks that the lab listing, the sentinel file, and the input bundle bytes are unchanged.

Fixtures are original dummy bytes only. No real game binaries, assets or jars were staged. The provisional
4 MiB file and 16 MiB total limits are unsuitable for current real jars.

Atomicity is namespace-level only: the candidate appears in one `rename` after all checks pass, under a flock.
Nothing is fsynced, so durability across a crash or power cut is unproven. Concurrency is exercised by one flock
contention test. Not proven: activation, active-version pointers, migration, cache-revision verification, or
identity verification against a runtime. Live GitHub release metadata is not used.

## Running

```sh
cd scripts && python3 -m unittest -v test_update_staging
```

The subprocess tests copy `stage.py` into a temporary code root and never touch the repository's `.runtime`.
