#!/usr/bin/env python3
"""Build two PRIVATE test packages (releases private-test-a / private-test-b) from a deck-export snapshot.

Both are code-only: they carry this checkout's runtime scripts and the pins and patch hashes, nothing else. The
snapshot's server jar and tracked data and this checkout's built client jar are written to a separate private
"build" folder with the build record `local_dev.prepare` would have written, and the installer copies them from
there. Only the manifest's release label differs between the packages, which gives the managed installer two
distinct, real-sized version identities for update, Continue and rollback acceptance. The build folder includes
the owner's authorized game data and MUST NOT be uploaded or published. No cache is included; it stays external.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/native-prebuilt-server'))
import package_builder  # noqa: E402
import runtime_manifest  # noqa: E402
import local_dev  # noqa: E402
from runtime_inputs import collect_data  # noqa: E402


def collect(snapshot, client_jar):
    server_repo = snapshot / 'upstream/game-server'
    server_jar = server_repo / 'game/build/libs/void-server-dev.jar'
    files = {package_builder.SERVER_ROLE: server_jar.read_bytes(), package_builder.CLIENT_ROLE: Path(client_jar).read_bytes()}
    patches = sorted((ROOT / 'patches/server').glob('*.patch'))
    for item in collect_data(server_repo, patches):
        files['upstream/game-server/' + item['path']] = (server_repo / item['path']).read_bytes()
    for name in runtime_manifest.RUNTIME_SCRIPTS:
        files['scripts/' + name] = (ROOT / 'scripts' / name).read_bytes()
    files[package_builder.LAUNCHER] = (ROOT / 'scripts/launcher.sh').read_bytes()
    return files


def split(files):
    """Released files (scripts) versus the paths a player's own build supplies (jars and server data)."""
    local = sorted(path for path in files if runtime_manifest.SERVER_JAR.fullmatch(path) or runtime_manifest.CLIENT_JAR.fullmatch(path)
                   or path.startswith(runtime_manifest.DATA_PREFIX))
    return {path: data for path, data in files.items() if path not in local}, local


def write_build_folder(files, local, destination):
    """A private stand-in for a built source folder: the local files plus the matching build record."""
    destination = Path(destination)
    for path in local:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[path])
    patches = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((ROOT / 'patches').glob('*/*.patch'))}
    (destination / '.runtime').mkdir(exist_ok=True)
    (destination / '.runtime/build-stamp.json').write_text(json.dumps({
        'format': 1, 'pins': dict(local_dev.PINNED), 'patches': patches,
        'jars': {'server': hashlib.sha256(files[package_builder.SERVER_ROLE]).hexdigest(),
                 'client': hashlib.sha256(files[package_builder.CLIENT_ROLE]).hexdigest()}}, indent=2) + '\n')
    return patches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--client-jar', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    files = collect(args.snapshot, args.client_jar)
    released, local = split(files)
    patches = write_build_folder(files, local, args.out / 'build')
    result = {}
    for label in ('a', 'b'):
        release = 'private-test-' + label
        manifest = package_builder.build_manifest(released, release, (0, 1), '0' * 40, dict(local_dev.PINNED), patches, local=local)
        archive = args.out / ('soloscape-package-' + release + '.zip')
        result[release] = {'path': str(archive), 'sha256': package_builder.write_zip(released, manifest, archive),
                           'size': archive.stat().st_size, 'released_files': len(released) + 1, 'local_files': len(local)}
        (args.out / (archive.name + package_builder.SIDECAR)).write_text('Private test package (scripts only). Do not publish; the build folder beside it holds owner-authorized data.\n')
    (args.out / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
