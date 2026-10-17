"""Metadata-only selector for upstream runtime data inputs.

collect_data() reports path, sha256 and size for each expected data source.
It never writes, copies or returns file contents, and it never opens or
inspects the private data/ prefixes listed in PRIVATE_DIRS.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from pathlib import Path

MAX_FILES = 10_000
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
ALLOWED_SUFFIXES = (".toml", ".txt")
PRIVATE_DIRS = frozenset({"cache", "saves", "errors", ".temp", "logs", "exchange"})
DATA_ROOT = "data"
_NULL_SIDE = "/dev/null"
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_CHUNK = 1 << 20


class RuntimeInputError(ValueError):
    """Raised when expected inputs are unsupported, unsafe, or missing."""


def collect_data(repo: Path, patches: list[Path]) -> list[dict]:
    repo = Path(repo)
    if not repo.is_dir():
        raise RuntimeInputError(f"repo is not a directory: {repo}")

    expected = {rel for rel in map(_scope, _tracked_data(repo)) if rel is not None}
    for patch in patches:
        for old, new in _header_pairs(_read_patch(patch)):
            old, new = _scope(old), _scope(new)
            if old is not None:
                expected.discard(old)
            if new is not None:
                expected.add(new)

    selected = sorted(expected)
    if len(selected) > MAX_FILES:
        raise RuntimeInputError(f"too many runtime sources: {len(selected)}")
    for rel in selected:
        if not rel.endswith(ALLOWED_SUFFIXES):
            raise RuntimeInputError(f"unsupported source extension: {rel}")

    stats = {rel: _source_stat(repo, rel) for rel in selected}
    if sum(st.st_size for st in stats.values()) > MAX_TOTAL_BYTES:
        raise RuntimeInputError("runtime sources exceed total byte cap")
    return [_describe(repo, rel, stats[rel]) for rel in selected]


def _tracked_data(repo: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--", DATA_ROOT],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeInputError(f"git ls-files failed in {repo}") from exc
    try:
        return [_check_rel(name.decode("utf-8")) for name in out.split(b"\0") if name]
    except UnicodeDecodeError as exc:
        raise RuntimeInputError("tracked data path is not UTF-8") from exc


def _read_patch(patch: Path) -> str:
    try:
        data = Path(patch).read_bytes()
    except OSError as exc:
        raise RuntimeInputError(f"cannot read patch: {patch}") from exc
    if len(data) > MAX_FILE_BYTES:
        raise RuntimeInputError(f"patch too large: {patch}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeInputError(f"patch is not UTF-8: {patch}") from exc


def _header_pairs(text: str) -> list[tuple[str | None, str | None]]:
    """Return (old, new) header paths in patch order, skipping hunk bodies."""
    pairs: list[tuple[str | None, str | None]] = []
    old: str | None = None
    have_old = False
    old_left = new_left = 0
    for line in text.split("\n"):
        if old_left or new_left:
            if line.startswith("\\"):
                continue
            tag = line[:1]
            if tag == "+":
                new_left -= 1
            elif tag == "-":
                old_left -= 1
            elif tag == " ":
                old_left -= 1
                new_left -= 1
            else:
                raise RuntimeInputError(f"malformed hunk line: {line[:40]!r}")
            if old_left < 0 or new_left < 0:
                raise RuntimeInputError("hunk line count mismatch")
            continue
        match = _HUNK.match(line)
        if match:
            old_left = int(match.group(2)) if match.group(2) is not None else 1
            new_left = int(match.group(4)) if match.group(4) is not None else 1
            continue
        if line.startswith("--- "):
            if have_old:
                raise RuntimeInputError("patch has two old-side headers in a row")
            old = _side(line[4:], "a/")
            have_old = True
        elif line.startswith("+++ "):
            if not have_old:
                raise RuntimeInputError("patch new-side header without old side")
            pairs.append((old, _side(line[4:], "b/")))
            have_old = False
        elif have_old:
            raise RuntimeInputError("patch old-side header without new side")
    if have_old or old_left or new_left:
        raise RuntimeInputError("patch ends inside a header or hunk")
    return pairs


def _side(text: str, prefix: str) -> str | None:
    if text == _NULL_SIDE:
        return None
    if not text.startswith(prefix):
        raise RuntimeInputError(f"malformed patch header: {text[:80]!r}")
    return _check_rel(text[len(prefix):])


def _check_rel(name: str) -> str:
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or '"' in name
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in name)
        or any(seg in ("", ".", "..") for seg in name.split("/"))
    ):
        raise RuntimeInputError(f"unsafe path: {name!r}")
    return name


def _scope(rel: str | None) -> str | None:
    """Return rel if it is a non-private data/ path, else None (ignored)."""
    if rel is None:
        return None
    parts = rel.split("/")
    if parts[0] != DATA_ROOT or len(parts) < 2 or parts[1] in PRIVATE_DIRS:
        return None
    return rel


def _source_stat(repo: Path, rel: str) -> os.stat_result:
    parts = rel.split("/")
    current = repo
    for part in parts[:-1]:
        current = current / part
        st = _lstat(current, rel)
        if not stat.S_ISDIR(st.st_mode):
            raise RuntimeInputError(f"ancestor is not a plain directory: {rel}")
    st = _lstat(current / parts[-1], rel)
    if not stat.S_ISREG(st.st_mode):
        raise RuntimeInputError(f"expected source is not a regular file: {rel}")
    return st


def _lstat(path: Path, rel: str) -> os.stat_result:
    try:
        return os.lstat(path)
    except OSError as exc:
        raise RuntimeInputError(f"missing expected source: {rel}") from exc


def _identity(st: os.stat_result) -> tuple[int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def _describe(repo: Path, rel: str, st: os.stat_result) -> dict:
    if st.st_size > MAX_FILE_BYTES:
        raise RuntimeInputError(f"source exceeds per-file cap: {rel}")
    try:
        fd = os.open(repo.joinpath(*rel.split("/")), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise RuntimeInputError(f"cannot open source: {rel}") from exc
    try:
        before = os.fstat(fd)
        if _identity(before) != _identity(st):
            raise RuntimeInputError(f"source changed before read: {rel}")
        digest = hashlib.sha256()
        read = 0
        while True:
            chunk = os.read(fd, _CHUNK)
            if not chunk:
                break
            read += len(chunk)
            if read > before.st_size:
                raise RuntimeInputError(f"source grew during read: {rel}")
            digest.update(chunk)
        after = os.fstat(fd)
        if read != before.st_size or _identity(after) != _identity(before):
            raise RuntimeInputError(f"source changed during read: {rel}")
    finally:
        os.close(fd)
    return {"path": rel, "sha256": digest.hexdigest(), "size": read}
