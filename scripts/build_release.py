#!/usr/bin/env python3
"""Prepare an installer AND a code-only managed update for one clean, committed source tree.

Local artifact generation only. No publication, game jars, server data, cache or art.
Run prepare-build.sh first, then build_release.py --release v0.52 --out <new directory>.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import build_installer
import local_dev
import package_builder
import runtime_manifest
import source_build
import update_package

ROOT = Path(__file__).resolve().parents[1]


def audit_package(package, release, commit, source=ROOT):
    """Use the existing updater's format, then independently restrict every shipped member to own scripts."""
    manifest = update_package.read_manifest(package)
    if manifest['release'] != release or manifest['source_commit'] != commit:
        raise ValueError('The update package does not name the release source.')
    expected = runtime_manifest.RUNTIME_SCRIPT_PATHS | {runtime_manifest.LAUNCHER}
    released = {p for p, entry in manifest['files'].items() if entry != runtime_manifest.LOCAL}
    if released != expected:
        raise ValueError('Public update packages must ship only SoloScape runtime scripts; game files must stay local.')
    with zipfile.ZipFile(package) as archive:
        if set(archive.namelist()) != expected | {runtime_manifest.MANIFEST_NAME}:
            raise ValueError('The update ZIP contains unexpected or missing members.')
        for path in expected:
            data = archive.read(path)
            entry = manifest['files'][path]
            if (len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']
                    or data != (Path(source) / path).read_bytes()):
                raise ValueError('The update ZIP differs from source: ' + path)
    source_build.verify_tree(source, manifest)
    return manifest


def build(release, destination, checkout=ROOT):
    if not runtime_manifest.RELEASE.fullmatch(release):
        raise ValueError('Invalid release label.')
    if subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=normal']).strip():
        raise ValueError('Commit the reviewed source before building release artifacts.')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    destination = Path(destination).absolute()
    if destination.exists():
        raise ValueError('Choose a new release output directory; existing artifacts are never replaced.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='.release-', dir=destination.parent))
    try:
        package = scratch / ('soloscape-package-' + release + '.zip')
        with local_dev.build_lock(shared=True):
            package_builder.checkout_package(checkout, release, (0, 1), package)
        notice = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(package, 'a') as archive:
            archive.comment = notice  # accepted by the original v0.5 updater; no extra payload path
        audit_package(package, release, commit, ROOT)
        installer = build_installer.build(release, commit, scratch / 'soloscape-installer.sh')
        with zipfile.ZipFile(installer) as archive:
            if json.loads(archive.read('release.json')) != {'release': release, 'commit': commit}:
                raise ValueError('The installer does not name the release source.')
        (scratch / 'LICENSE.txt').write_bytes(notice)
        assets = {}
        for asset in (installer, package):
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            asset.with_name(asset.name + '.sha256').write_text(digest + '  ' + asset.name + '\n')
            assets[asset.name] = {'size': asset.stat().st_size, 'sha256': digest}
        (scratch / 'release-assets.json').write_text(json.dumps({'release': release, 'source_commit': commit, 'assets': assets}, indent=2) + '\n')
        os.rename(scratch, destination)
        return destination
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--checkout', type=Path, default=ROOT, help='matching prepared build; defaults to this source folder')
    args = parser.parse_args()
    print(build(args.release, args.out, args.checkout))


if __name__ == '__main__':
    main()
