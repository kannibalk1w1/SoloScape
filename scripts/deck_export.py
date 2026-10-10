#!/usr/bin/env python3
"""Private owner-to-device test snapshot. Never a public redistributable package."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import local_dev

MUTABLE = ('data/saves', 'data/errors', 'data/.temp', 'data/cache', 'data/exchange')


def safe_source(name):
    path = Path(name)
    return not path.is_absolute() and '..' not in path.parts and not any(
        name == prefix or name.startswith(prefix + '/') for prefix in MUTABLE)


def source_files(repo, patches):
    names = set(subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z']).decode().split('\0'))
    for patch in patches:
        for name in re.findall(r'^\+\+\+ b/(.+)$', patch.read_text(), re.MULTILINE):
            names.add(name)
    return sorted(name for name in names if name and safe_source(name) and (repo / name).is_file())


def copy_file(source, target, allowed_root=None):
    if source.is_symlink():
        raise ValueError('Source snapshot cannot contain symlinks: ' + str(source))
    if not source.resolve().is_relative_to(Path(allowed_root or local_dev.ROOT).resolve()):
        raise ValueError('Source path leaves the source tree: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_pin_metadata(repo, target, pin):
    """Only reachable pinned objects; never a stash or dangling locally staged blob."""
    metadata = target / '.git'
    (metadata / 'objects/pack').mkdir(parents=True)
    (metadata / 'refs').mkdir()
    (metadata / 'HEAD').write_text(pin + '\n')
    (metadata / 'config').write_text('[core]\n\trepositoryformatversion = 0\n\tbare = false\n')
    subprocess.run(['git', '-C', str(repo), 'pack-objects', '--revs', str(metadata / 'objects/pack/pack')],
                   input=pin+'\n', text=True, check=True, stdout=subprocess.DEVNULL)
    if (repo / '.git/shallow').is_file():
        shutil.copyfile(repo / '.git/shallow', metadata / 'shallow')
    subprocess.run(['git', '-C', str(target), 'read-tree', pin], check=True)


def export():
    completed = local_dev.RUNTIME / 'deck-exports' / str(time.time_ns())
    destination = completed.with_name(completed.name + '.partial')
    destination.mkdir(parents=True, mode=0o700)
    with local_dev.build_lock(shared=True):
        server = local_dev.jar(local_dev.SERVER / 'game', 'void-server-*.jar')
        client = local_dev.jar(local_dev.CLIENT / 'client', 'void-client-*.jar')
        local_dev.verify_build_stamp(server, client)
        root_names = subprocess.check_output(['git', '-C', str(local_dev.ROOT), 'ls-files', '-z']).decode().split('\0')
        # Include this sprint's new tooling before its first commit, never arbitrary ignored files.
        root_names += ['scripts/deck_export.py', 'scripts/deck_runtime.py', 'scripts/deck-launch.sh',
                       'scripts/test_deck_runtime.py', 'scripts/native_metrics.py',
                       'scripts/summarise_native_metrics.py', 'scripts/test_native_metrics.py',
                       'scripts/harness/NativeControllerProbe.java', 'docs/DECK_SPRINT_TASKS.md']
        root_names += ['scripts/harness/NativeSidebarProbe.java',
                       'patches/client/0036-sidebar-resize-thread-and-controller-default.patch',
                       'patches/server/0015-stop-game-loop-before-saving.patch']
        for name in sorted(set(root_names)):
            if name and name != 'config/local.env' and not name.startswith(('upstream/', '.runtime/')):
                source = local_dev.ROOT / name
                if source.is_file():
                    copy_file(source, destination / name)
        for name, pin in local_dev.PINNED.items():
            repo = local_dev.ROOT / 'upstream' / name
            actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
            if actual != pin:
                raise ValueError('Upstream pin mismatch: ' + name)
            patches = sorted((local_dev.ROOT / 'patches' / ('server' if name == 'game-server' else 'client')).glob('*.patch')) if name != '634-client' else []
            for relative in source_files(repo, patches):
                copy_file(repo / relative, destination / 'upstream' / name / relative, repo)
            copy_pin_metadata(repo, destination / 'upstream' / name, pin)
        for source in (server, client, local_dev.RUNTIME / 'build-stamp.json'):
            copy_file(source, destination / source.relative_to(local_dev.ROOT))
        cache = local_dev.SERVER / 'data/cache'
        if any(path.is_symlink() for path in cache.rglob('*')) or cache.is_symlink():
            raise ValueError('Cache symlinks are refused; supply ordinary compatible cache files.')
        shutil.copytree(cache, destination / 'upstream/game-server/data/cache')
        for version in ('jdk8', 'jdk21'):
            source = local_dev.RUNTIME / 'jdks' / version
            for link in source.rglob('*'):
                if link.is_symlink() and not link.resolve().is_relative_to(source.resolve()):
                    raise ValueError('JDK symlink leaves the private runtime: ' + str(link))
            shutil.copytree(source, destination / '.runtime/jdks' / version, symlinks=True)
        entries = {}
        for path in sorted(destination.rglob('*')):
            relative = path.relative_to(destination).as_posix()
            if relative.endswith('/.git/index'):
                continue  # Git legitimately refreshes index stat data; source/pack hashes remain checked.
            if path.is_symlink():
                entries[relative] = {'link': os.readlink(path)}
            elif path.is_file():
                entries[relative] = {'sha256': local_dev.file_hash(path), 'size': path.stat().st_size}
        manifest = {'format': 1, 'purpose': 'private Steam Deck test; not a redistribution release',
                    'source_commit': subprocess.check_output(['git', '-C', str(local_dev.ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                    'pins': local_dev.PINNED, 'files': entries}
        (destination / 'deck-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    destination.rename(completed)
    print(completed)


if __name__ == '__main__':
    export()
