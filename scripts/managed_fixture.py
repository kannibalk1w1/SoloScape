"""Original disposable fixtures for the managed updater tests. Not real game data; every byte is synthetic."""
import hashlib
import json
import os
import uuid
from pathlib import Path

import package_builder
import runtime_manifest

PINS = {'game-server': '1' * 40, '634-client': '2' * 40, 'runelite-client': '3' * 40}
PATCHES = {'patches/client/0001-test.patch': 'a' * 64, 'patches/server/0001-test.patch': 'b' * 64}
SERVER = package_builder.SERVER_ROLE
CLIENT = package_builder.CLIENT_ROLE


def payload_files(release, launcher='exit 0\n', server=b'TEST-ONLY synthetic server jar\n', storage=(0, 1)):
    files = {'scripts/' + name: ('# TEST-ONLY stub ' + name + ' ' + release + '\n').encode() for name in runtime_manifest.RUNTIME_SCRIPTS}
    files['scripts/launcher.sh'] = ('#!/usr/bin/env bash\n' + launcher).encode()
    files[SERVER] = server
    files[CLIENT] = b'TEST-ONLY synthetic client jar ' + release.encode() + b'\n'
    files['upstream/game-server/data/test/items.toml'] = b'name = "synthetic"\n'
    return files


def make_package(directory, release, storage=(0, 1), **options):
    """Write a package zip; returns (path, sha256, files)."""
    files = payload_files(release, storage=storage, **options)
    manifest = package_builder.build_manifest(files, release, storage, 'c' * 40, PINS, PATCHES)
    path = Path(directory) / ('package-' + release + '.zip')
    digest = package_builder.write_zip(files, manifest, path)
    return path, digest, files


def version_id(files, release, storage=(0, 1)):
    return hashlib.sha256(package_builder.build_manifest(files, release, storage, 'c' * 40, PINS, PATCHES)).hexdigest()


def make_profile(home, label='Tester', storage_version=1, world=True, session=False, account='tester'):
    uid = uuid.uuid4().hex
    generation = uuid.uuid4().hex
    directory = Path(home) / uid
    saves = directory / 'states' / generation / 'saves'
    saves.mkdir(parents=True)
    (directory / 'profile.json').write_text(json.dumps({'format': 1, 'id': uid, 'generation': generation, 'label': label,
                                                        'account': account}))
    prefix = '' if storage_version is None else 'storage_version = ' + str(storage_version) + '\n'
    (saves / (account + '.toml')).write_text(prefix + 'accountName = "Tester"\nprogress = "start"\n')
    if world and storage_version:
        (saves / '.soloscape-death-loot.v1').write_text('synthetic world file\n')
    if session:
        (directory / 'session.json').write_text('{}')
    return directory, saves / (account + '.toml')
