"""PRIVATE ACCEPTANCE ONLY: real source folders built by the project's own scripts/prepare-build.sh.

A "player folder" and a "maintainer folder" are disposable copies of this checkout's sources (no build outputs, no
runs, no cache); each is built by the real prepare flow, so every build record, jar and data file the managed
updater consumes in the real-checkout acceptance is genuine rather than synthesized. Gradle's user cache is shared
through a symlink to this worktree's own. Nothing outside the copies is edited.
"""
import difflib
import os
import shutil
import subprocess
from pathlib import Path

COPIED = ('scripts', 'patches', 'config', 'experiments/native-prebuilt-server')
UPSTREAM = ('game-server', 'runelite-client', '634-client')
SKIP = shutil.ignore_patterns('build', '.gradle', '__pycache__', '.runtime', '*.pyc')
INERT_FILE = 'game/src/main/kotlin/ContentLoader.kt'  # no server patch touches this file
INERT_PATCH = 'patches/server/0999-acceptance-inert-rebuild.patch'


def copy_source(source, destination):
    """Copy the sources of a checkout into a new folder (never build outputs) and share its Gradle cache."""
    source, destination = Path(source), Path(destination)
    for name in COPIED:
        shutil.copytree(source / name, destination / name, ignore=SKIP, symlinks=False)
    for name in UPSTREAM:
        shutil.copytree(source / 'upstream' / name, destination / 'upstream' / name, ignore=SKIP, symlinks=True)
    (destination / '.gradle').symlink_to(source / '.gradle')
    return destination


def prepare(folder, cache, log, env=None):
    """Run the folder's own scripts/prepare-build.sh. Returns the exit status; output goes to `log`."""
    environment = dict(os.environ if env is None else env, SOLOSCAPE_CACHE_HOME=str(cache))
    for key in ('SOLOSCAPE_MANAGED_ROOT', 'SOLOSCAPE_PROFILE_HOME', 'SOLOSCAPE_LAUNCHER_HOME'):
        environment.pop(key, None)
    with open(log, 'w') as output:
        return subprocess.run(['bash', str(Path(folder) / 'scripts/prepare-build.sh')], cwd=folder, env=environment,
                              stdout=output, stderr=subprocess.STDOUT).returncode


def inert_patch_text(folder):
    """A server patch that only adds a comment line: it changes the built jar and the patch hashes, not behaviour."""
    repo = Path(folder) / 'upstream/game-server'
    before = subprocess.run(['git', '-C', str(repo), 'show', 'HEAD:' + INERT_FILE], capture_output=True, text=True, check=True).stdout
    lines = before.splitlines(keepends=True)
    after = lines[:1] + ['// SoloScape managed-updater acceptance: inert marker that forces a local rebuild.\n'] + lines[1:]
    diff = difflib.unified_diff(lines, after, 'a/' + INERT_FILE, 'b/' + INERT_FILE, n=3)
    return 'diff --git a/%s b/%s\n' % (INERT_FILE, INERT_FILE) + ''.join(diff)


def add_inert_patch(folder):
    target = Path(folder) / INERT_PATCH
    target.write_text(inert_patch_text(folder))
    return target


def add_inert_patch_to(destination, source_root):
    """Write the inert patch into another tree's patches folder, derived from `source_root`'s pinned game-server checkout."""
    target = Path(destination) / INERT_PATCH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(inert_patch_text(source_root))
    return target
