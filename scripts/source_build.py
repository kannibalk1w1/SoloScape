"""Fetch, verify and build the exact source of a release in an isolated workspace inside the install.

Version-side code run by the launcher's update manager on its own worker thread (never inside Save & Quit). It
never touches the player's registered source folder except to read git objects out of its `upstream/*` clones and
to copy its Gradle dependency cache once: no checkout, reset, stash, clean or write happens there, so local edits
survive. Every step is bounded and cancellable, and cancellation or backend shutdown ends only the process groups
this module started.

What is trusted, and where it comes from:

  * The release package (SHA-256 verified against GitHub's own asset listing) declares `source_commit`, the
    server/client/reference `pins`, the hashes of every patch file and the hash of every released script. Nothing is
    derived from a tag or from release notes, and no metadata text is ever executed or used as a command or URL.
  * The commit is fetched only from the fixed SoloScape repository (and upstream pins only from their fixed
    2011Scape repositories, and only when no registered folder already holds that exact commit). The fetched commit id
    must equal the declared one, and the fetched tree must reproduce the declared pins, patch hashes and script hashes
    before anything is built. Mismatched or incomplete source is refused and deleted unbuilt.
  * The build is the project's own scripts/prepare-build.sh with the player's local JDKs and cache.

A digest or a commit id is not a publisher signature; GitHub HTTPS for the fixed project is the explicit trust source.
"""
import ast
import hashlib
import hmac
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_manifest  # noqa: E402
import update_package  # noqa: E402
from update_package import Cancelled, Job, PackageError  # noqa: E402

BUILDS = 'builds'
GRADLE_HOME = 'gradle-home'
LOG = 'last-build.log'
LOCK = '.lock'
BUILD_DEADLINE = 90 * 60
FETCH_DEADLINE = 15 * 60
KEEP_WORKSPACES = 1
STOP_GRACE = 10
HEX40 = re.compile(r'[0-9a-f]{40}\Z')

# Fixed origins. Production code has no override; tests replace this mapping (and ALLOWED_PROTOCOLS) in-process.
ORIGINS = {
    'SoloScape': 'https://github.com/kannibalk1w1/SoloScape.git',
    'game-server': 'https://github.com/2011Scape/game-server.git',
    'runelite-client': 'https://github.com/2011Scape/runelite-client.git',
    '634-client': 'https://github.com/2011Scape/634-client.git',
}
ALLOWED_PROTOCOLS = 'https'


class BuildError(PackageError):
    """A refusal with a plain message. `code` is 'no-source', 'source-mismatch', 'no-tools' or 'build-failed'."""


def _git_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ALLOW_PROTOCOL=ALLOWED_PROTOCOLS,
               GIT_OPTIONAL_LOCKS='0', LC_ALL='C')
    return env


class Runner:
    """Run owned subprocesses in their own process group so cancellation ends exactly those and nothing else."""

    def __init__(self, job, on_line=None):
        self.job, self.on_line = job, on_line
        self.tail = deque(maxlen=40)

    def run(self, argv, cwd=None, env=None, log=None):
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True)

        def read():
            for raw in process.stdout:
                line = raw.decode('utf-8', 'replace').rstrip('\n')
                self.tail.append(line)
                if log is not None:
                    log.write(line + '\n')
                    log.flush()
                if self.on_line is not None:
                    self.on_line(line)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            while process.poll() is None:
                self.job.check()
                time.sleep(0.1)
        except BaseException:
            _stop_group(process)
            reader.join(5)
            process.stdout.close()
            raise
        reader.join(5)
        process.stdout.close()
        return process.returncode


def _stop_group(process):
    """Terminate the process group this module started; never any other process."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(STOP_GRACE)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        process.wait()


# ---- identity ---------------------------------------------------------------------------------------------------

def rebuildable(manifest):
    """The release's declared source commit, or a BuildError explaining that none is declared."""
    commit = manifest.get('source_commit')
    if not isinstance(commit, str) or not HEX40.match(commit) or set(commit) == {'0'}:
        raise BuildError('This release does not name the exact source it was built from, so it cannot be rebuilt here. '
                         'Nothing was changed.', 'no-source')
    return commit


def pinned_from_text(text):
    """The PINNED mapping of a fetched local_dev.py, read as data (the file is never imported or run)."""
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PINNED' for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('no PINNED mapping')


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def verify_tree(tree, manifest):
    """The fetched source must reproduce the release's declared pins, patch hashes and released-script hashes."""
    tree = Path(tree)
    problems = []
    try:
        if pinned_from_text((tree / 'scripts/local_dev.py').read_text()) != manifest['pins']:
            problems.append('the pinned upstream commits differ')
    except (OSError, ValueError, SyntaxError, UnicodeError):
        problems.append('scripts/local_dev.py has no readable pin list')
    found = {}
    for patch in sorted((tree / 'patches').glob('*/*.patch')):
        if patch.is_symlink() or not patch.is_file():
            problems.append('a patch is not an ordinary file: ' + patch.name)
        else:
            found[patch.relative_to(tree).as_posix()] = _sha256(patch)
    if found != manifest['patches']:
        changed = sorted(k for k in set(found) | set(manifest['patches']) if found.get(k) != manifest['patches'].get(k))
        problems.append('the patches differ (' + ', '.join(changed[:3]) + (' and more' if len(changed) > 3 else '') + ')')
    for name, meta in sorted(manifest['files'].items()):
        if 'sha256' not in meta:
            continue
        path = tree / name
        if path.is_symlink() or not path.is_file() or not hmac.compare_digest(_sha256(path), meta['sha256']):
            problems.append('the released file ' + name + ' differs')
            break
    if problems:
        raise BuildError('The source fetched for commit ' + manifest['source_commit'][:12] + ' does not match release '
                         + manifest['release'] + ': ' + '; '.join(problems) + '. Nothing was built or changed.', 'source-mismatch')


# ---- fetch --------------------------------------------------------------------------------------------------------

def _git(runner, args, cwd, protocols=None):
    env = _git_env()
    if protocols:
        env['GIT_ALLOW_PROTOCOL'] = protocols
    return runner.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'advice.detachedHead=false', '-c', 'protocol.version=2', *args],
                      cwd=cwd, env=env)


def _fail_git(runner, what):
    last = next((line for line in reversed(runner.tail) if line.strip()), '')
    raise BuildError('Could not ' + what + ' (' + last[:160] + '). Your installed version keeps working.', 'source-unavailable')


def fetch_source(workspace, commit, runner):
    """Fetch exactly `commit` from the fixed SoloScape repository into `workspace` and check it out detached."""
    workspace = Path(workspace)
    workspace.mkdir(mode=0o700, parents=True)
    if _git(runner, ['init', '-q'], workspace):
        _fail_git(runner, 'prepare the source folder')
    if _git(runner, ['fetch', '--quiet', '--depth=1', '--no-tags', '--no-recurse-submodules', ORIGINS['SoloScape'], commit], workspace):
        _fail_git(runner, 'fetch release source ' + commit[:12])
    head = subprocess.run(['git', 'rev-parse', 'FETCH_HEAD^{commit}'], cwd=workspace, env=_git_env(), capture_output=True, text=True)
    if head.returncode or head.stdout.strip() != commit:
        raise BuildError('The fixed project returned a different commit than the release declares (' + commit[:12]
                         + '). Nothing was built or changed.', 'source-mismatch')
    listing = subprocess.run(['git', 'ls-tree', '-r', '-z', 'FETCH_HEAD'], cwd=workspace, env=_git_env(), capture_output=True)
    if listing.returncode or len(listing.stdout) > 64 << 20:
        _fail_git(runner, 'read the fetched source')
    for entry in listing.stdout.split(b'\0'):
        if entry and entry.split(b' ', 1)[0] not in (b'100644', b'100755'):
            raise BuildError('The fetched source contains a link or submodule, which is never built. Nothing was built or changed.',
                             'source-mismatch')
    if _git(runner, ['checkout', '--quiet', '--detach', 'FETCH_HEAD'], workspace):
        _fail_git(runner, 'check out the fetched source')


def provision_upstream(workspace, manifest, local_folders, runner):
    """Give the workspace its pinned upstream clones: from a registered folder that already holds the exact commit
    (read-only copy of its git objects), otherwise from the fixed upstream repository."""
    for name, pin in sorted(manifest['pins'].items()):
        target = Path(workspace) / 'upstream' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        for folder in local_folders:
            source = Path(folder) / 'upstream' / name
            if source.is_symlink() or not (source / '.git').is_dir():
                continue
            has = subprocess.run(['git', '-C', str(source), 'cat-file', '-e', pin + '^{commit}'], env=_git_env(), capture_output=True)
            if has.returncode == 0 and _git(runner, ['clone', '--quiet', '--no-checkout', '--no-hardlinks', str(source), str(target)],
                                            workspace, protocols='file') == 0:
                break
            shutil.rmtree(target, ignore_errors=True)
        else:
            if _git(runner, ['init', '-q', str(target)], workspace) or _git(
                    runner, ['fetch', '--quiet', '--depth=1', '--no-tags', '--no-recurse-submodules', ORIGINS[name], pin], target):
                if name in runtime_manifest.REFERENCE_PINS:  # provenance-only pin the build never reads; the host may no longer serve it
                    shutil.rmtree(target, ignore_errors=True)
                    continue
                _fail_git(runner, 'fetch upstream ' + name)
            if _git(runner, ['checkout', '--quiet', '--detach', 'FETCH_HEAD'], target):
                _fail_git(runner, 'check out upstream ' + name)
            continue
        if _git(runner, ['checkout', '--quiet', '--detach', pin], target):
            _fail_git(runner, 'check out upstream ' + name + ' at its pin')
        head = subprocess.run(['git', '-C', str(target), 'rev-parse', 'HEAD'], env=_git_env(), capture_output=True, text=True).stdout.strip()
        if head != pin:
            raise BuildError('Upstream ' + name + ' is not at the commit the release pins. Nothing was built.', 'source-mismatch')


# ---- build --------------------------------------------------------------------------------------------------------

def builds_dir(root):
    path = Path(root) / BUILDS
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise BuildError('The install build folder is unsafe.', 'no-tools')
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def _seed_gradle(private, local_folders, runner):
    """One-time copy of a registered folder's Gradle dependency cache into this install's private cache."""
    if private.exists():
        return
    for folder in local_folders:
        source = Path(folder) / '.gradle'
        if source.is_dir():
            partial = private.with_name(private.name + '.partial')
            shutil.rmtree(partial, ignore_errors=True)
            partial.mkdir(mode=0o700)
            if runner.run(['cp', '-a', '--reflink=auto', '-L', str(source) + '/.', str(partial)]) != 0:
                shutil.rmtree(partial, ignore_errors=True)
                continue
            (partial / 'gradle.properties').write_text('org.gradle.offline=true\n')
            os.rename(partial, private)
            return
    raise BuildError('No Gradle dependency cache is available for an offline build. Run scripts/prepare-build.sh once in your '
                     'source folder (it needs internet the first time), register that folder, and try again.', 'no-tools')


def built_workspaces(root):
    """Finished build workspaces (each holds a build record and the jars/data), newest first."""
    base = Path(root) / BUILDS
    if not base.is_dir() or base.is_symlink():
        return []
    found = [entry for entry in os.scandir(base) if entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.')
             and entry.name != GRADLE_HOME and os.path.isfile(os.path.join(entry.path, '.runtime/build-stamp.json'))]
    return [Path(e.path) for e in sorted(found, key=lambda e: e.stat().st_mtime, reverse=True)]


def build_workspace(root, manifest, config, local_folders, job, progress=None, environ=None):
    """Fetch, verify and build the release source. Returns the finished workspace path (a supply root)."""
    commit = rebuildable(manifest)
    environ = os.environ if environ is None else environ
    java = {name: config.get(key) or environ.get(name) for key, name in (('server_java', 'SERVER_JAVA'), ('client_java', 'CLIENT_JAVA'))}
    if not all(java.values()):
        raise BuildError('Set the server (Java 21) and client (Java 8) JDK locations in the install configuration before '
                         'rebuilding.', 'no-tools')
    base = builds_dir(root)
    final = base / commit[:12]
    with open(base / LOCK, 'a+') as lock:
        import fcntl
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BuildError('Another rebuild is already running for this install.', 'build-failed') from None
        say = progress or (lambda stage, detail='': None)
        log = open(base / LOG, 'w')
        work = base / ('.work-' + os.urandom(4).hex())
        try:
            runner = Runner(job, lambda line: say('building', _detail(line)) if line.startswith('> Task') else None)
            say('fetching source', commit[:12])
            fetch_source(work, commit, runner)
            say('verifying source', commit[:12])
            verify_tree(work, manifest)
            say('fetching source', 'upstream projects')
            provision_upstream(work, manifest, local_folders, runner)
            _seed_gradle(base / GRADLE_HOME, local_folders, runner)
            (work / '.gradle').symlink_to(base / GRADLE_HOME)
            env = {k: v for k, v in environ.items() if not k.startswith('SOLOSCAPE_')}
            env.update(SOLOSCAPE_CACHE_HOME=config['cache_home'], SERVER_JAVA=java['SERVER_JAVA'], CLIENT_JAVA=java['CLIENT_JAVA'])
            say('building', 'starting')
            code = runner.run(['bash', str(work / 'scripts/prepare-build.sh')], cwd=work, env=env, log=log)
            if code != 0:
                last = [line for line in runner.tail if line.strip()][-3:]
                raise BuildError('The build did not finish (exit ' + str(code) + '). ' + ' | '.join(l[:120] for l in last)
                                 + ' The log is ' + str(base / LOG) + '. Your installed version keeps working.', 'build-failed')
            _check_stamp(work, manifest)
            if final.exists():
                shutil.rmtree(final)
            os.rename(work, final)
            _prune(base, keep=final)
            return final
        except BaseException:
            shutil.rmtree(work, ignore_errors=True)
            raise
        finally:
            log.close()


def _detail(line):
    return re.sub(r'^> Task\s+:?', '', line)[:80]


def _check_stamp(workspace, manifest):
    import json
    try:
        stamp = json.loads((Path(workspace) / '.runtime/build-stamp.json').read_text())
    except (OSError, ValueError):
        stamp = None
    if not isinstance(stamp, dict) or stamp.get('pins') != manifest['pins'] or stamp.get('patches') != manifest['patches']:
        raise BuildError('The finished build does not match the release it was made for. Nothing was installed.', 'build-failed')


def _prune(base, keep):
    others = [p for p in built_workspaces(base.parent) if p != keep]
    for old in others[KEEP_WORKSPACES - 1:]:
        shutil.rmtree(old, ignore_errors=True)
    for entry in os.scandir(base):
        if entry.name.startswith('.work-') or entry.name.endswith('.partial'):
            shutil.rmtree(entry.path, ignore_errors=True)
