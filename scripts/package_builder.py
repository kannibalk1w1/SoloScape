"""Build a managed package zip from a payload file map or a prepared payload directory.

PRIVATE TEST TOOL. A package built from a deck export or from `prepare.py` output contains the owner's
authorized game data and jars and is never to be uploaded as a public release. Public package contents and
their licence inventory are separate, unresolved work (see docs/MANAGED_UPDATER_20261018.md). The builder
checks only structure and writes a sidecar marking the output private.
"""
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

import runtime_manifest

SERVER_ROLE = 'upstream/game-server/game/build/libs/void-server-dev.jar'
CLIENT_ROLE = 'upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar'
LAUNCHER = 'scripts/launcher.sh'
SIDECAR = '.PRIVATE-NOT-FOR-PUBLIC-RELEASE.txt'


def build_manifest(files, release, storage_versions, source_commit, pins, patches, roles=None, local=()):
    """files maps payload path -> bytes (without the manifest); `local` lists paths left to be supplied from the
    installing player's own build (listed in the manifest without a digest, absent from the package)."""
    if roles is None:
        paths = list(files) + list(local)
        server = next(p for p in paths if runtime_manifest.SERVER_JAR.fullmatch(p))
        client = next(p for p in paths if runtime_manifest.CLIENT_JAR.fullmatch(p))
        roles = {'server': server, 'client': client, 'launcher': LAUNCHER}
    manifest = {'format': runtime_manifest.FORMAT, 'release': release, 'storage_versions': sorted(storage_versions),
                'source_commit': source_commit, 'platform': runtime_manifest.PLATFORM,
                'cache_revision': runtime_manifest.CACHE_REVISION, 'pins': pins, 'patches': patches, 'roles': roles,
                'files': {**{path: {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                             for path, data in sorted(files.items())},
                          **{path: dict(runtime_manifest.LOCAL) for path in sorted(local)}}}
    return (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()


def write_zip(files, manifest_bytes, destination):
    """Write exactly the manifest plus its listed files. Returns the archive's SHA-256."""
    destination = Path(destination)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in [(runtime_manifest.MANIFEST_NAME, manifest_bytes), *sorted(files.items())]:
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    digest = hashlib.sha256()
    with open(destination, 'rb') as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def checkout_package(checkout, release, storage_versions, destination, source=None):
    """Code-only package for a built source folder: this tool's runtime scripts are released; the server and
    client jars and the server data stay local and are copied from the player's own build at install time.

    `checkout` is the folder `prepare` built (its jars, server data and .runtime/build-stamp.json); `source` is the
    SoloScape source tree supplying the scripts, patches and pins, which is this tool's own tree unless a test says
    otherwise. The result carries no game data, jar, cache or art, so its contents are only this project's scripts
    plus the pins and patch hashes a local build must match. Whether it may be published is a separate decision.
    """
    import sys
    source = Path(source or Path(__file__).resolve().parents[1])
    checkout = Path(checkout).resolve()
    stamp = json.loads((checkout / '.runtime/build-stamp.json').read_text())
    patches = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((source / 'patches').glob('*/*.patch'))}
    sys.path.insert(0, str(source / 'experiments/native-prebuilt-server'))
    try:
        from runtime_inputs import collect_data
    finally:
        sys.path.pop(0)
    sys.path.insert(0, str(source / 'scripts'))
    try:
        import local_dev
        pins = dict(local_dev.PINNED)
    finally:
        sys.path.pop(0)
    if patches != stamp['patches'] or pins != stamp['pins']:
        raise ValueError('The local build in ' + str(checkout) + ' was not made from this source tree; rebuild before packaging.')
    server_repo = checkout / 'upstream/game-server'
    local = [SERVER_ROLE, CLIENT_ROLE] + ['upstream/game-server/' + item['path']
                                           for item in collect_data(server_repo, sorted((source / 'patches/server').glob('*.patch')))]
    scripts = source / 'scripts'
    files = {'scripts/' + name: (scripts / name).read_bytes() for name in runtime_manifest.RUNTIME_SCRIPTS}
    files[LAUNCHER] = (scripts / 'launcher.sh').read_bytes()
    manifest = build_manifest(files, release, storage_versions, '0' * 40, pins, patches, local=local)
    return write_zip(files, manifest, destination)


def convert_payload(payload, scripts_dir, release, storage_versions, destination):
    """Re-package a prepared (format 1) private payload with this checkout's runtime scripts as format 2."""
    payload = Path(payload)
    old = json.loads((payload / 'soloscape-runtime.json').read_text())
    files = {}
    for path in old['files']:
        files[path] = (payload / path).read_bytes()
    for name in runtime_manifest.RUNTIME_SCRIPTS:
        files['scripts/' + name] = (Path(scripts_dir) / name).read_bytes()
    files[LAUNCHER] = (Path(scripts_dir) / 'launcher.sh').read_bytes()
    for stale in ('scripts/owned_launcher_backend.py', 'scripts/prebuilt_bootstrap.py', 'scripts/prebuilt_manifest.py'):
        files.pop(stale, None)
    manifest = build_manifest(files, release, storage_versions, old['source_commit'], old['pins'], old['patches'], old['roles'])
    digest = write_zip(files, manifest, destination)
    Path(str(destination) + SIDECAR).write_text('Private test package built from owner-authorized local data. Do not upload or publish.\n')
    return digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--payload', type=Path, help='prepared private payload (format 1): a full private package')
    source.add_argument('--checkout', type=Path, help='built source folder: a code-only package; jars and data stay local')
    parser.add_argument('--release', required=True)
    parser.add_argument('--storage-versions', default='0,1')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    versions = [int(v) for v in args.storage_versions.split(',')]
    if args.checkout:
        print(checkout_package(args.checkout, args.release, versions, args.out))
    else:
        print(convert_payload(args.payload, Path(__file__).resolve().parent, args.release, versions, args.out))


if __name__ == '__main__':
    main()
