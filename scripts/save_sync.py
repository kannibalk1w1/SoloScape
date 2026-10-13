#!/usr/bin/env python3
"""Publish/receive verified stopped-world saves through a provider-managed folder.

Track this folder with OpenSave (or another file sync provider), never live profiles.
Receiving creates a separate local profile; competing progress remains reviewable.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import zipfile
import profiles


def validate_bundle(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > profiles.MAX_BACKUP:
        raise ValueError('Choose a regular, bounded SoloScape save bundle.')
    # Freeze bytes locally so a sync provider cannot replace the archive between reads.
    with tempfile.TemporaryDirectory(prefix='soloscape-sync-') as scratch:
        frozen = Path(scratch) / 'save.zip'
        shutil.copyfile(path, frozen)
        with zipfile.ZipFile(frozen) as archive:
            info = archive.getinfo('backup.json')
            if info.file_size > profiles.MAX_FILE:
                raise ValueError('Save bundle metadata is oversized.')
            manifest = json.loads(archive.read('backup.json'))
        validator = object.__new__(profiles.Profile)
        validator.manifest = {'id': profiles.identifier(manifest['profile']), 'account': manifest['account']}
        manifest, contents = validator.validate_backup(frozen)
        primary = 'saves/' + manifest['account'].lower() + '.toml'
        if primary not in contents:
            raise ValueError('Save the character at least once before publishing it.')
        profiles.validate_save(contents[primary], manifest['account'])
        return manifest, contents


def publish(uid, folder):
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError('Sync folder cannot be a symbolic link.')
    folder.mkdir(parents=True, exist_ok=True)
    if folder.resolve().is_relative_to(profiles.PROFILES.resolve()):
        raise ValueError('Use a separate sync folder outside live profile storage.')
    profile = profiles.load(uid)
    with profile.lock():
        if (profile.directory / 'session.json').exists():
            raise RuntimeError('Save & Quit or recover the earlier session before publishing.')
        bundle = profile._backup('manual-sync-export')
        validate_bundle(bundle)
        # Immutable names retain independent progress on both devices. Providers
        # must not merge archives or select a winner by wall-clock timestamps.
        destination = folder / (profile.manifest['id'] + '-' + uuid.uuid4().hex + '.zip')
        temporary = destination.with_suffix('.partial')
        try:
            with temporary.open('xb') as out, bundle.open('rb') as source:
                os.fchmod(out.fileno(), 0o600)
                shutil.copyfileobj(source, out)
                out.flush()
                os.fsync(out.fileno())
            temporary.replace(destination)
            profiles.fsync_directory(folder)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def receive(bundle, label):
    manifest, contents = validate_bundle(bundle)
    # Existing characters are never replaced. A receive is a verified new local
    # branch with all world/exchange files, ready to Continue after selection.
    with tempfile.TemporaryDirectory(prefix='soloscape-sync-world-') as scratch:
        saves = Path(scratch) / 'saves'
        saves.mkdir()
        for name, data in contents.items():
            if not name.startswith('saves/'):
                continue
            target = saves / name[6:]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o600)
        return profiles.import_world_copy(saves, label, manifest['account'], world=profiles.world_settings(manifest.get('world')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    commands.add_parser('list', help='List local profile IDs and labels.')
    export = commands.add_parser('publish')
    export.add_argument('profile')
    export.add_argument('folder', type=Path)
    fetch = commands.add_parser('receive')
    fetch.add_argument('bundle', type=Path)
    fetch.add_argument('--label', required=True)
    args = parser.parse_args()
    try:
        if args.operation == 'list':
            for row in profiles.list_profiles():
                print(row['id'] + ' ' + row['label'])
            return
        result = publish(args.profile, args.folder) if args.operation == 'publish' else receive(args.bundle, args.label).manifest['id']
        print(result)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
