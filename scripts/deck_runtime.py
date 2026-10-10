#!/usr/bin/env python3
"""Validate an owner-transferred test snapshot and configure its local JDK paths."""
import argparse
import json
import os
from pathlib import Path
import shlex
import local_dev


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'deck-manifest.json').read_text())
    if manifest.get('format') != 1 or manifest.get('pins') != local_dev.PINNED:
        raise ValueError('Unknown snapshot format or source pins.')
    for name, expected in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid snapshot path.')
        path = root / relative
        if not path.resolve().is_relative_to(root):
            raise ValueError('Snapshot path leaves its installation.')
        if 'link' in expected:
            if not path.is_symlink() or os.readlink(path) != expected['link']:
                raise ValueError('Snapshot link mismatch: ' + name)
        elif path.is_symlink() or not path.is_file() or path.stat().st_size != expected['size'] or local_dev.file_hash(path) != expected['sha256']:
            raise ValueError('Snapshot file mismatch: ' + name)
    return len(manifest['files'])


def configure(root):
    root = Path(root).resolve()
    lines = [f'{variable}={shlex.quote(str(root / ".runtime/jdks" / version / "bin/java"))}'
             for variable, version in (('SERVER_JAVA', 'jdk21'), ('CLIENT_JAVA', 'jdk8'))]
    destination = root / 'config/local.env'
    if destination.exists() or destination.is_symlink():
        raise ValueError('Existing local configuration retained; refusing replacement.')
    if destination.parent.is_symlink() or not destination.resolve().is_relative_to(root):
        raise ValueError('Configuration path leaves its installation.')
    destination.parent.mkdir(exist_ok=True)
    with destination.open('x') as output:
        output.write('\n'.join(lines) + '\n')
    destination.chmod(0o600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure', action='store_true', help='Write local Java paths only when no config exists.')
    options = parser.parse_args()
    print('Private snapshot listed files match:', verify(local_dev.ROOT))
    if options.configure:
        configure(local_dev.ROOT)
