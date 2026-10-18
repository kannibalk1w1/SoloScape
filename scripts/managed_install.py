"""Trusted outer installer for managed SoloScape versions.

An install root holds, outside every replaceable version directory:

  install.json            fixed configuration: external profile/cache/launcher homes (strict, private)
  install.guard           the one lock file; a launched version holds a shared lease, apply needs exclusive
  active.json             {current, previous} version ids, replaced atomically
  versions/<id>/          sealed read-only payloads; <id> is the SHA-256 of the payload's manifest bytes
  staging/                downloads and extraction scratch (see update_package)
  bootstrap/              this file and its two siblings, copied at install time and never version-owned
  update-request.json     a stopped launcher's request to switch to one staged candidate (advisory)
  trial.json              the first launch of a freshly activated version; rolls back if it fails at once
  last-update.json        the plain result of the most recent apply, shown by the next launcher

Profiles, backups, settings and the cache live in the external homes named by install.json and are
never read for restore, copied, moved or rewritten here. Rollback moves the pointer only. The bootstrap
decides after taking the lease; a version's own preflight is advisory.

This is a cooperative single-user protocol, not a security boundary against a hostile local user.
"""
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_manifest  # noqa: E402

FORMAT_CONFIG = 'soloscape-install-config-1'
FORMAT_POINTER = 'soloscape-install-pointer-1'
FORMAT_REQUEST = 'soloscape-update-request-1'
FORMAT_TRIAL = 'soloscape-update-trial-1'
FORMAT_RESULT = 'soloscape-update-result-1'
GUARD = 'install.guard'
CONFIG = 'install.json'
POINTER = 'active.json'
REQUEST = 'update-request.json'
TRIAL = 'trial.json'
RESULT = 'last-update.json'
CANDIDATE = 'candidate.json'
FORMAT_CANDIDATE = 'soloscape-staged-candidate-1'
VERSIONS = 'versions'
BOOTSTRAP = 'bootstrap'
BOOTSTRAP_FILES = ('managed_install.py', 'runtime_manifest.py', 'update_package.py')
RESTART_CODE = 75  # a stopped launcher asks the bootstrap to apply its recorded request
TRIAL_SECONDS = 60
MAX_RECORD = 16 * 1024
MAX_SAVE = 32 * 1024 * 1024
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
SAFE_ID = re.compile(r'[a-f0-9]{32}\Z')
CUTPOINTS = ('after-temp-fsync', 'after-replace')
CUT_EXIT = 75
WORLD_FILE = '.soloscape-death-loot.v1'
JOURNAL = '.soloscape-account-save'


class InstallError(Exception):
    """A refusal whose message is safe to show to the player as-is."""


class Busy(InstallError):
    """A launcher or world still holds the install guard."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _read_limited(path, limit):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise InstallError('Cannot read ' + Path(path).name + '.') from exc
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise InstallError(Path(path).name + ' is not an ordinary file.')
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise InstallError(Path(path).name + ' is too large.')
    return data


def _strict_json(data, what):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise InstallError(what + ' has a duplicate key.')
            out[key] = value
        return out

    def refuse(_):
        raise InstallError(what + ' has a non-finite number.')
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=refuse)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallError(what + ' is not valid JSON.') from exc


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ordinary_dir(path, what):
    try:
        if not stat.S_ISDIR(os.lstat(path).st_mode):
            raise InstallError(what + ' must be an ordinary folder, not a link or file.')
    except OSError as exc:
        raise InstallError(what + ' is missing.') from exc
    return Path(path)


def _publish(root, name, record, cutpoint=None):
    """Temp file, fsync, atomic replace, directory fsync: readers see the old or the new file."""
    if cutpoint is not None and cutpoint not in CUTPOINTS:
        raise ValueError('unknown cutpoint')
    fd, temp = tempfile.mkstemp(dir=root, prefix='.' + name + '.')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(_canonical(record))
            handle.flush()
            os.fsync(handle.fileno())
        if cutpoint == 'after-temp-fsync':
            os._exit(CUT_EXIT)  # test-only process-kill cut; not a power-loss claim
        os.replace(temp, Path(root) / name)
    except BaseException:
        if os.path.lexists(temp):
            os.unlink(temp)
        raise
    if cutpoint == 'after-replace':
        os._exit(CUT_EXIT)
    _fsync_dir(root)


# ---- configuration and pointer ---------------------------------------------------------------

def load_config(root):
    root = _ordinary_dir(root, 'The install folder')
    value = _strict_json(_read_limited(root / CONFIG, MAX_RECORD), 'install.json')
    allowed = {'format', 'profile_home', 'cache_home', 'launcher_home', 'server_java', 'client_java'}
    if (not isinstance(value, dict) or value.get('format') != FORMAT_CONFIG
            or not {'format', 'profile_home', 'cache_home', 'launcher_home'} <= set(value) <= allowed):
        raise InstallError('install.json is not a supported configuration.')
    for key in set(value) - {'format'}:
        if not isinstance(value[key], str) or not value[key].startswith('/') or '\0' in value[key]:
            raise InstallError('install.json ' + key + ' must be an absolute path.')
    return value


def read_pointer(root):
    value = _strict_json(_read_limited(Path(root) / POINTER, MAX_RECORD), 'active.json')
    if not isinstance(value, dict) or set(value) != {'format', 'current', 'previous'} or value['format'] != FORMAT_POINTER:
        raise InstallError('active.json is not a supported pointer.')
    current, previous = value['current'], value['previous']
    if (not isinstance(current, str) or not HEX64.match(current)
            or (previous is not None and (not isinstance(previous, str) or not HEX64.match(previous)))
            or previous == current):
        raise InstallError('active.json names an invalid version.')
    return {'current': current, 'previous': previous}


def verify_version(root, version):
    """Full check of one sealed version against its own manifest; returns its manifest."""
    if not isinstance(version, str) or not HEX64.match(version):
        raise InstallError('Invalid version identifier.')
    versions = _ordinary_dir(Path(root) / VERSIONS, 'The versions folder')
    directory = _ordinary_dir(versions / version, 'Version ' + version[:12])
    try:
        manifest, found = runtime_manifest.validate_with_id(directory)
    except (ValueError, OSError) as exc:
        raise InstallError('Version ' + version[:12] + ' failed verification: ' + str(exc)) from None
    if found != version:
        raise InstallError('Version ' + version[:12] + ' does not match its identifier.')
    return manifest


# ---- lease ------------------------------------------------------------------------------------

class Lease:
    """One flock description on install.guard. Closing drops only this descriptor; children keep theirs."""

    def __init__(self, root, mode, fd):
        self.root, self.mode, self.fd, self.open = Path(root), mode, fd, True

    def current(self):
        return read_pointer(self.root)['current']

    def close(self):
        if self.open:
            self.open = False
            os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def acquire(root, mode, blocking=False):
    if mode not in ('shared', 'exclusive'):
        raise ValueError('mode must be shared or exclusive')
    root = _ordinary_dir(root, 'The install folder')
    try:
        fd = os.open(root / GUARD, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise InstallError('The install guard is unreadable.') from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise InstallError('The install guard is not an ordinary file.')
    op = fcntl.LOCK_SH if mode == 'shared' else fcntl.LOCK_EX
    if not blocking:
        op |= fcntl.LOCK_NB
    try:
        fcntl.flock(fd, op)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            raise Busy('A SoloScape launcher or world is still running from this install.') from exc
        raise
    return Lease(root, mode, fd)


# ---- profiles: sessions and logical save versions ----------------------------------------------

def _logical_storage_version(state):
    """Highest logical storage_version among the state's accounts; journal members override canonical files.

    Returns (version or None for an empty/unsaved state). Raises InstallError for unreadable or inconsistent
    saves: an installer must fail closed, not guess. The version itself fully validates content at launch.
    """
    saves = state / 'saves'
    if not saves.exists() and not saves.is_symlink():
        return None
    if saves.is_symlink() or not saves.is_dir():
        raise InstallError('the saves folder is not an ordinary folder')
    accounts, world = {}, os.path.lexists(saves / WORLD_FILE)
    for entry in sorted(os.scandir(saves), key=lambda e: e.name):
        if entry.name == JOURNAL:
            continue
        if entry.name.endswith('.toml'):
            accounts[entry.name] = Path(entry.path)
        elif entry.is_symlink():
            raise InstallError('the saves folder contains a link')
    journal = saves / JOURNAL
    if journal.is_symlink():
        raise InstallError('the pending save batch is a link')
    if os.path.lexists(journal):
        if not journal.is_dir():
            raise InstallError('the pending save batch is not a folder')
        for entry in os.scandir(journal):
            if entry.is_symlink() or not entry.is_file():
                raise InstallError('the pending save batch holds an unsupported member')
            if entry.name.endswith('.toml'):
                accounts[entry.name] = Path(entry.path)
            elif entry.name == WORLD_FILE:
                world = True
    version = None
    for name, path in accounts.items():
        data = _read_limited(path, MAX_SAVE)
        try:
            save = tomllib.loads(data.decode('utf-8'))
        except (UnicodeError, tomllib.TOMLDecodeError):
            raise InstallError('a character save is damaged') from None
        stored = save.get('storage_version', 0)
        if type(stored) is not int or stored < 0:
            raise InstallError('a character save has an invalid storage version')
        version = stored if version is None else max(version, stored)
    if version is not None and version >= 1 and not world:
        raise InstallError('a storage version 1 world has no death-loot world file')
    return version


def scan_profiles(profile_home):
    """One row per profile: {id, label, problem, storage_version}. Read-only; never opens a save for writing."""
    home = Path(profile_home)
    if not home.exists():
        return []
    if home.is_symlink() or not home.is_dir():
        raise InstallError('The profile folder is not an ordinary folder.')
    rows = []
    for entry in sorted(os.scandir(home), key=lambda e: e.name):
        if not SAFE_ID.match(entry.name):
            continue
        row = {'id': entry.name, 'label': entry.name[:8], 'problem': None, 'storage_version': None}
        rows.append(row)
        directory = Path(entry.path)
        try:
            if entry.is_symlink() or not entry.is_dir():
                raise InstallError('the profile folder is a link')
            manifest = _strict_json(_read_limited(directory / 'profile.json', 64 * 1024), 'profile.json')
            if isinstance(manifest.get('label'), str):
                row['label'] = manifest['label'][:40]
            generation = manifest.get('generation')
            if not isinstance(generation, str) or not SAFE_ID.match(generation):
                raise InstallError('the profile has no valid save generation')
            if os.path.lexists(directory / 'session.json'):
                row['problem'] = 'has an earlier session that still needs Recover Session in its original version'
                continue
            lock = directory / 'profile.lock'
            if os.path.lexists(lock):
                try:
                    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
                except OSError:
                    raise InstallError('the profile lock is unreadable') from None
                try:
                    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                except OSError:
                    row['problem'] = 'is running or being saved right now'
                    continue
                finally:
                    os.close(fd)
            state = directory / 'states' / generation
            if state.is_symlink() or not state.is_dir():
                raise InstallError('its save generation folder is missing')
            row['storage_version'] = _logical_storage_version(state)
        except (InstallError, ValueError, OSError) as exc:
            row['problem'] = 'cannot be checked safely: ' + str(exc)
    return rows


def blockers(cfg, manifest):
    """Plain reasons activating (or rolling back to) this manifest would be unsafe; empty means allowed."""
    reasons = []
    supported = manifest['storage_versions']
    for row in scan_profiles(cfg['profile_home']):
        if row['problem']:
            reasons.append('Character ' + row['label'] + ' ' + row['problem'] + '.')
        elif row['storage_version'] is not None and row['storage_version'] not in supported:
            reasons.append('Character ' + row['label'] + ' uses save storage version ' + str(row['storage_version'])
                           + ', which release ' + manifest['release'] + ' cannot read. Saves were left unchanged.')
    return reasons


def preflight(root, candidate):
    """Advisory, lock-free pre-check used by a running version's UI. The bootstrap repeats it under the lease."""
    cfg = load_config(root)
    pointer = read_pointer(root)
    if candidate == pointer['current']:
        return ['That version is already installed.']
    manifest = verify_version(root, candidate)
    return blockers(cfg, manifest)


def identity(root):
    pointer = read_pointer(root)
    manifest = verify_version(root, pointer['current'])
    return {'release': manifest['release'], 'id': pointer['current'], 'storage_versions': manifest['storage_versions'],
            'previous': pointer['previous']}


# ---- requests, results, activation -----------------------------------------------------------------

def request_activation(root, candidate):
    if not isinstance(candidate, str) or not HEX64.match(candidate):
        raise InstallError('Invalid version identifier.')
    _publish(root, REQUEST, {'format': FORMAT_REQUEST, 'candidate': candidate})


def _take_request(root):
    path = Path(root) / REQUEST
    if not os.path.lexists(path):
        return None
    try:
        value = _strict_json(_read_limited(path, MAX_RECORD), 'the update request')
        if (isinstance(value, dict) and set(value) == {'format', 'candidate'} and value['format'] == FORMAT_REQUEST
                and isinstance(value['candidate'], str) and HEX64.match(value['candidate'])):
            return value['candidate']
        return None
    except InstallError:
        return None
    finally:
        path.unlink(missing_ok=True)  # a request is single-use consent for one stopped-launcher restart


def record_result(root, ok, message, candidate=None):
    _publish(root, RESULT, {'format': FORMAT_RESULT, 'ok': ok, 'message': message[:600],
                            'candidate': candidate, 'at': int(time.time())})


def read_result(root):
    try:
        value = _strict_json(_read_limited(Path(root) / RESULT, MAX_RECORD), 'last-update.json')
    except InstallError:
        return None
    if isinstance(value, dict) and value.get('format') == FORMAT_RESULT and isinstance(value.get('message'), str):
        return {'ok': value.get('ok') is True, 'message': value['message'], 'at': value.get('at')}
    return None


def _discard(path):
    for base, dirs, _ in os.walk(path):
        for name in dirs:
            os.chmod(Path(base) / name, 0o755)
    os.chmod(path, 0o755)
    shutil.rmtree(path)


def read_candidate(root):
    """The staged-but-not-yet-installed candidate recorded by the launcher, or None."""
    try:
        record = _strict_json(_read_limited(Path(root) / CANDIDATE, MAX_RECORD), CANDIDATE)
    except InstallError:
        return None
    if (not isinstance(record, dict) or record.get('format') != FORMAT_CANDIDATE or not isinstance(record.get('id'), str)
            or not HEX64.match(record['id']) or not isinstance(record.get('release'), str)
            or not isinstance(record.get('zip_sha256'), str)):
        return None
    return {'id': record['id'], 'release': record['release'], 'zip_sha256': record['zip_sha256']}


def write_candidate(root, version, release, zip_sha256):
    _publish(root, CANDIDATE, {'format': FORMAT_CANDIDATE, 'id': version, 'release': release, 'zip_sha256': zip_sha256})


def _prune(root, keep):
    """Remove versions that are neither current, previous nor the recorded staged candidate."""
    staged = read_candidate(root)
    keep = set(keep) | ({staged['id']} if staged else set())
    versions = Path(root) / VERSIONS
    for entry in os.scandir(versions):
        if entry.name not in keep and not entry.is_symlink() and entry.is_dir():
            _discard(entry.path)


def _switch(root, lease, target, expected_current, cutpoint, what):
    """Shared by activate and rollback; the caller holds an exclusive lease and has verified the manifest."""
    state = read_pointer(root)
    if state['current'] != expected_current:
        raise InstallError('The installed version changed while updating; nothing was switched.')
    _publish(root, POINTER, {'format': FORMAT_POINTER, 'current': target, 'previous': state['current']}, cutpoint)
    return state


def activate(root, candidate, cutpoint=None):
    """Point current at a verified staged candidate. The old current becomes previous. Pointer-only."""
    with acquire(root, 'exclusive') as lease:
        cfg = load_config(root)
        state = read_pointer(root)
        if candidate == state['current']:
            raise InstallError('That version is already installed.')
        manifest = verify_version(root, candidate)
        reasons = blockers(cfg, manifest)
        if reasons:
            raise InstallError(' '.join(reasons))
        _publish(root, TRIAL, {'format': FORMAT_TRIAL, 'candidate': candidate, 'previous': state['current']})
        _switch(root, lease, candidate, state['current'], cutpoint, 'activate')
        _prune(root, {candidate, state['current']})
    return candidate


def rollback(root, cutpoint=None):
    """Return current to previous after the same checks. No saves are restored, copied or rewritten."""
    with acquire(root, 'exclusive') as lease:
        cfg = load_config(root)
        state = read_pointer(root)
        if state['previous'] is None:
            raise InstallError('There is no earlier version to return to.')
        manifest = verify_version(root, state['previous'])
        reasons = blockers(cfg, manifest)
        if reasons:
            raise InstallError(' '.join(reasons))
        _switch(root, lease, state['previous'], state['current'], cutpoint, 'rollback')
        Path(root, TRIAL).unlink(missing_ok=True)
        _prune(root, {state['previous'], state['current']})
    return state['previous']


def recover(root):
    """Clear leftovers of an interrupted publish or activation. Takes the exclusive lease if free, else does nothing."""
    try:
        lease = acquire(root, 'exclusive')
    except Busy:
        return
    with lease:
        for entry in os.scandir(root):
            if entry.name.startswith('.') and any(entry.name.startswith('.' + n + '.') for n in (POINTER, REQUEST, TRIAL, RESULT)):
                try:
                    os.unlink(entry.path)
                except OSError:
                    pass
        state = read_pointer(root)
        trial = Path(root) / TRIAL
        if os.path.lexists(trial):
            try:
                value = _strict_json(_read_limited(trial, MAX_RECORD), 'trial.json')
                valid = (isinstance(value, dict) and value.get('format') == FORMAT_TRIAL
                         and value.get('candidate') == state['current'] and value.get('previous') == state['previous'])
            except InstallError:
                valid = False
            if not valid:
                trial.unlink()  # activation never completed, or the trial record is damaged


# ---- run loop ---------------------------------------------------------------------------------------

def child_environment(root, cfg, base=None):
    env = dict(os.environ if base is None else base)
    env.update(SOLOSCAPE_MANAGED_ROOT=str(root), SOLOSCAPE_PROFILE_HOME=cfg['profile_home'],
               SOLOSCAPE_CACHE_HOME=cfg['cache_home'], SOLOSCAPE_LAUNCHER_HOME=cfg['launcher_home'],
               PYTHONDONTWRITEBYTECODE='1')
    for key, name in (('server_java', 'SERVER_JAVA'), ('client_java', 'CLIENT_JAVA')):
        if key in cfg and name not in env:
            env[name] = cfg[key]
    return env


def _launch(root, cfg, lease, version, base_env=None, launcher=None):
    script = Path(root) / VERSIONS / version / 'scripts' / 'launcher.sh'
    argv = launcher or ['bash', str(script)]
    process = subprocess.Popen(argv, env=child_environment(root, cfg, base_env), pass_fds=(lease.fd,))
    return process.wait()


def _trial_pending(root, pointer):
    path = Path(root) / TRIAL
    if not os.path.lexists(path):
        return False
    try:
        value = _strict_json(_read_limited(path, MAX_RECORD), 'trial.json')
    except InstallError:
        return False
    return value.get('candidate') == pointer['current'] and value.get('previous') == pointer['previous']


def run(root, trial_seconds=TRIAL_SECONDS, base_env=None, launcher=None, output=print):
    """Launch the current version until the player quits; apply a recorded restart request between runs."""
    root = Path(root)
    while True:
        recover(root)
        cfg = load_config(root)
        with acquire(root, 'shared') as lease:
            pointer = read_pointer(root)  # resolved only after the lease is held
            trial = _trial_pending(root, pointer)
            try:
                verify_version(root, pointer['current'])
            except InstallError as exc:
                if not trial:
                    raise
                output('The new version failed verification: ' + str(exc))
                code = 1
                started = time.monotonic()
            else:
                started = time.monotonic()
                code = _launch(root, cfg, lease, pointer['current'], base_env, launcher)
        failed = code not in (0, RESTART_CODE)
        quick = time.monotonic() - started < trial_seconds
        if trial:
            if failed and quick:
                try:
                    rollback(root)
                    record_result(root, False, 'The updated version failed to start, so the previous version was restored. '
                                               'Your characters and backups were not changed.')
                    output('Updated version failed to start; previous version restored.')
                    continue
                except (InstallError, OSError) as exc:
                    output('Could not restore the previous version: ' + str(exc))
                    return code
            Path(root, TRIAL).unlink(missing_ok=True)
        request = _take_request(root)
        if code == RESTART_CODE and request is not None:
            try:
                activate(root, request)
                record_result(root, True, 'Updated. Your characters, backups and settings were kept.', request)
            except (InstallError, OSError) as exc:
                record_result(root, False, 'Update not applied: ' + str(exc), request)
                output('Update not applied: ' + str(exc))
            continue
        if code == RESTART_CODE:
            continue
        return code


# ---- first install and CLI ---------------------------------------------------------------------------

def _absolute(value, what):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise InstallError(what + ' must be an absolute path.')
    return str(path)


def install_first(root, package, sha256, profile_home, cache_home, launcher_home, release=None, **options):
    """Create a new install root from one local package zip whose SHA-256 the caller supplies."""
    import update_package
    root = Path(root)
    if root.exists() and (root.is_symlink() or not root.is_dir() or any(root.iterdir())):
        raise InstallError('The install folder must be new or empty.')
    homes = [Path(_absolute(h, n)) for h, n in ((profile_home, 'profile home'), (cache_home, 'cache home'), (launcher_home, 'launcher home'))]
    for index, a in enumerate(homes + [root.absolute()]):
        for b in (homes + [root.absolute()])[index + 1:]:
            if a == b or a.is_relative_to(b) or b.is_relative_to(a):
                raise InstallError('Install, profile, cache and launcher folders must be distinct and not nested.')
    root.mkdir(parents=True, exist_ok=True)
    for name in (VERSIONS, 'staging', BOOTSTRAP):
        (root / name).mkdir(mode=0o700)
    version = update_package.install_zip(root, package, sha256, expected_release=release)['id']
    here = Path(__file__).resolve().parent
    for name in BOOTSTRAP_FILES:
        shutil.copyfile(here / name, root / BOOTSTRAP / name)
        os.chmod(root / BOOTSTRAP / name, 0o444)
    config = {'format': FORMAT_CONFIG, 'profile_home': str(homes[0]), 'cache_home': str(homes[1]), 'launcher_home': str(homes[2])}
    config.update({k: _absolute(v, k) for k, v in options.items() if v})
    _publish(root, CONFIG, config)
    fd = os.open(root / GUARD, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    _publish(root, POINTER, {'format': FORMAT_POINTER, 'current': version, 'previous': None})
    return version


def status(root):
    pointer = read_pointer(root)
    rows = scan_profiles(load_config(root)['profile_home'])
    return {'pointer': pointer, 'identity': identity(root), 'versions': sorted(os.listdir(Path(root) / VERSIONS)),
            'profiles': rows, 'last_result': read_result(root)}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='SoloScape managed install: init, run, status, activate, rollback.')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='create an install root from a local package zip')
    init.add_argument('root')
    init.add_argument('--package', required=True)
    init.add_argument('--sha256', required=True)
    init.add_argument('--profile-home', required=True)
    init.add_argument('--cache-home', required=True)
    init.add_argument('--launcher-home', required=True)
    init.add_argument('--server-java')
    init.add_argument('--client-java')
    for name in ('run', 'status', 'rollback'):
        sub.add_parser(name).add_argument('root')
    act = sub.add_parser('activate', help='switch to an already staged candidate (headless apply)')
    act.add_argument('root')
    act.add_argument('candidate')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            print(install_first(args.root, args.package, args.sha256, args.profile_home, args.cache_home,
                                args.launcher_home, server_java=args.server_java, client_java=args.client_java))
        elif args.command == 'run':
            return run(args.root)
        elif args.command == 'status':
            print(json.dumps(status(args.root), indent=2, sort_keys=True))
        elif args.command == 'rollback':
            print(rollback(args.root))
        else:
            print(activate(args.root, args.candidate))
    except (InstallError, OSError, ValueError) as exc:
        print('SoloScape install: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
