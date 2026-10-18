#!/usr/bin/env python3
"""Build two PRIVATE test packages (releases private-test-a / private-test-b) from a deck-export snapshot.

Both carry the same game bytes (the snapshot's server jar and tracked data, this checkout's built client jar and
runtime scripts); only the manifest's release label differs, which gives the managed installer two distinct,
real-sized version identities for update, Continue and rollback acceptance. Output includes the owner's
authorized game data and MUST NOT be uploaded or published. No cache is included; it stays external.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--client-jar', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    files = collect(args.snapshot, args.client_jar)
    patches = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((ROOT / 'patches').glob('*/*.patch'))}
    result = {}
    for label in ('a', 'b'):
        release = 'private-test-' + label
        manifest = package_builder.build_manifest(files, release, (0, 1), '0' * 40, dict(local_dev.PINNED), patches)
        archive = args.out / ('soloscape-package-' + release + '.zip')
        result[release] = {'path': str(archive), 'sha256': package_builder.write_zip(files, manifest, archive),
                           'size': archive.stat().st_size, 'files': len(files) + 1}
        (args.out / (archive.name + package_builder.SIDECAR)).write_text('Private test package. Contains owner-authorized game data. Do not upload.\n')
    (args.out / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
