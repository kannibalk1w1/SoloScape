"""Shared test helper: a byte-exact picture of a directory tree."""
import hashlib
import os
from pathlib import Path


def snapshot(path):
    """Relative path -> (mode, sha256 | link target) for everything under path."""
    result = {}
    for base, dirs, names in os.walk(path):
        for name in dirs + names:
            full = Path(base) / name
            rel = full.relative_to(path).as_posix()
            if full.is_symlink():
                result[rel] = ('link', os.readlink(full))
            elif full.is_dir():
                result[rel] = ('dir', oct(full.stat().st_mode & 0o7777))
            else:
                result[rel] = (oct(full.stat().st_mode & 0o7777), hashlib.sha256(full.read_bytes()).hexdigest())
    return result
