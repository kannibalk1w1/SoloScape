"""Original disposable fixtures for source-fetch-and-build tests: tiny real git repositories and a fake prepare script.

Nothing here is game data. The "origin" repository stands in for the fixed project repository, three small repositories
stand in for the pinned upstream projects, and a fake scripts/prepare-build.sh copies pre-baked outputs instead of
running Gradle (the real script is exercised by the native acceptance).
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import managed_fixture as fx
import package_builder
import runtime_manifest

FAKE_PREPARE = '''#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
env | sort > "$root/.build-env.txt"
pwd > "$root/.build-cwd.txt"
echo "> Task :game:compileKotlin"
if [[ -n "${FAKE_SLEEP:-}" ]]; then
  sleep "$FAKE_SLEEP" &
  echo $! > "$FAKE_PID_FILE"
  wait
fi
if [[ -n "${FAKE_FAIL:-}" ]]; then echo "boom: $FAKE_FAIL" >&2; exit 3; fi
cp -a "$FAKE_BUILD_SRC/." "$root/"
echo "> Task :client:shadowJar"
'''


def git(cwd, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    return subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid', *args],
                          check=check, capture_output=True, text=True, env=env).stdout.strip()


def commit_all(repo, message='fixture'):
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '-m', message)
    return git(repo, 'rev-parse', 'HEAD')


class Source:
    """A fixed-origin repository at one commit, its pinned upstream repositories, a pre-baked build and a matching package."""

    def __init__(self, directory, release='r2', storage=(0, 1)):
        self.directory, self.release, self.storage = Path(directory), release, storage
        self.upstream, self.pins = {}, {}
        for name in ('game-server', 'runelite-client', '634-client'):
            repo = self.directory / 'upstream-origins' / name
            repo.mkdir(parents=True)
            git(repo, 'init', '-q')
            (repo / 'README').write_text('synthetic upstream ' + name + '\n')
            self.pins[name] = commit_all(repo)
            self.upstream[name] = repo
        self.origin = self.directory / 'origin'
        self.origin.mkdir()
        git(self.origin, 'init', '-q')
        self.files = fx.payload_files(release, storage=storage)
        self.files['scripts/prepare-build.sh'] = FAKE_PREPARE.encode()
        self.files['scripts/local_dev.py'] = ('# synthetic\nPINNED = ' + json.dumps(self.pins, indent=4) + '\n').encode()
        for side in ('client', 'server'):
            path = self.origin / 'patches' / side / '0001-fixture.patch'
            path.parent.mkdir(parents=True)
            path.write_text('--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b\n' + side + '\n')
        self.write_released()
        self.commit = commit_all(self.origin)
        self.build_output = self.directory / 'prebuilt'
        self.make_output()

    @property
    def released(self):
        return {p: d for p, d in self.files.items() if p not in fx.LOCAL_PATHS}

    def patches(self):
        return {p.relative_to(self.origin).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((self.origin / 'patches').glob('*/*.patch'))}

    def write_released(self):
        for path, data in self.released.items():
            target = self.origin / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def make_output(self):
        for path in fx.LOCAL_PATHS:
            target = self.build_output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.files[path])
        (self.build_output / '.runtime').mkdir()
        (self.build_output / '.runtime/build-stamp.json').write_text(json.dumps({
            'format': 1, 'pins': self.pins, 'patches': self.patches(),
            'jars': {'server': hashlib.sha256(self.files[fx.SERVER]).hexdigest(), 'client': hashlib.sha256(self.files[fx.CLIENT]).hexdigest()}}))

    def manifest(self, **override):
        values = dict(release=self.release, storage=self.storage, commit=self.commit, pins=self.pins, patches=self.patches(),
                      released=self.released)
        values.update(override)
        raw = package_builder.build_manifest(values['released'], values['release'], values['storage'], values['commit'], values['pins'],
                                             values['patches'], local=fx.LOCAL_PATHS)
        return runtime_manifest.parse(raw), raw

    def package(self, directory, **override):
        manifest, raw = self.manifest(**override)
        released = override.get('released', self.released)
        path = Path(directory) / ('source-' + self.release + '.zip')
        return path, package_builder.write_zip(released, raw, path)

    def player_folder(self, directory, name='player'):
        """A registered source folder: pinned upstream clones, a Gradle cache, local edits, and an older build."""
        folder = Path(directory) / name
        for upstream, repo in self.upstream.items():
            subprocess.run(['git', 'clone', '-q', '--no-hardlinks', str(repo), str(folder / 'upstream' / upstream)], check=True,
                           capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull))
            (folder / 'upstream' / upstream / 'LOCAL-EDIT.txt').write_text('uncommitted work of the player\n')
        (folder / 'scripts').mkdir(exist_ok=True)
        (folder / 'scripts/local_dev.py').write_text('# the player\'s own, possibly edited\n')
        (folder / '.gradle/caches').mkdir(parents=True)
        (folder / '.gradle/caches/modules.bin').write_bytes(b'synthetic dependency cache')
        (folder / 'notes.txt').write_text('personal notes\n')
        return folder
