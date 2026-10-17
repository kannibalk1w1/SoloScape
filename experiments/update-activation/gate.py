"""Lab-only update activation mechanism: one guard, sealed versions, one pointer.

Experimental and private. Not a downloader, installer, launcher, migration or recovery
resolver, and it never executes candidate files. A live lease (flock) proves a holder is
running now; a session marker records unresolved work that outlived its lease. These are
separate refusals.
"""
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

FORMAT_MANIFEST = 'update-activation-manifest-1'
FORMAT_POINTER = 'update-activation-pointer-1'
FORMAT_MARKER = 'update-activation-marker-1'
GUARD = 'install.guard'
POINTER = 'active.json'
MARKER = 'session.marker'
VERSIONS = 'versions'
MANIFEST = '.manifest.json'
CUTPOINTS = ('after-temp-fsync', 'after-replace')
CUT_EXIT = 75
MAX_RECORD = 16 * 1024
MAX_FILE = 1024 * 1024
MAX_FILES = 64
HEX64 = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}(?:\.[A-Za-z0-9_-]{1,16})?')


class ActivationError(Exception):
    """A lab refusal; publication I/O errors require rereading the pointer."""


class Busy(ActivationError):
    """A live lease conflicts with the requested mode."""


class Stale(ActivationError):
    """The expected current version does not match the pointer."""


class CandidateError(ActivationError):
    """A version is missing, malformed, tampered or not exactly its manifest."""


class PointerError(ActivationError):
    """The active pointer is missing or malformed."""


class MarkerError(ActivationError):
    """An unresolved session marker refuses mutation, even with no live lease."""


def _valid_id(value):
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def _ordinary_directory(path, error):
    path = Path(path)
    try:
        if not stat.S_ISDIR(os.lstat(path).st_mode):
            raise error('not an ordinary directory: '+path.name)
    except OSError as exc:
        raise error('missing directory: '+path.name) from exc
    return path


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _strict_json(data, error):
    if len(data) > MAX_RECORD:
        raise error('record exceeds its bound')

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise error('duplicate key '+key)
            out[key] = value
        return out

    def refuse(_):
        raise error('non-finite number')

    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=refuse)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise error('not strict JSON') from exc
    if _canonical(value) != data:
        raise error('record is not canonical')
    return value


def _read_limited(path, limit, error):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise error('unreadable '+Path(path).name) from exc
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise error('not a regular file: '+Path(path).name)
        data = handle.read(limit+1)
    if len(data) > limit:
        raise error('too large: '+Path(path).name)
    return data


def _read_manifest(data, error):
    value = _strict_json(data, error)
    if not isinstance(value, dict) or set(value) != {'format', 'files'}:
        raise error('manifest shape')
    if value['format'] != FORMAT_MANIFEST:
        raise error('manifest format')
    files = value['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise error('manifest file count')
    for name, entry in files.items():
        if not NAME.fullmatch(name):
            raise error('unsafe payload name')
        if not isinstance(entry, dict) or set(entry) != {'sha256', 'size'}:
            raise error('manifest entry shape')
        if type(entry['size']) is not int or not 0 <= entry['size'] <= MAX_FILE:
            raise error('manifest size bound')
        if not _valid_id(entry['sha256']):
            raise error('manifest digest')
    return files


def verify_version(lab, version):
    """Exact check of one sealed version: manifest hash, membership, sizes and digests."""
    if not _valid_id(version):
        raise CandidateError('version id is not a sha256 identifier')
    lab = _ordinary_directory(lab, CandidateError)
    versions = _ordinary_directory(lab/VERSIONS, CandidateError)
    directory = _ordinary_directory(versions/version, CandidateError)
    manifest = _read_limited(directory/MANIFEST, MAX_RECORD, CandidateError)
    if hashlib.sha256(manifest).hexdigest() != version:
        raise CandidateError('manifest does not match its identifier')
    files = _read_manifest(manifest, CandidateError)
    entries = set()
    with os.scandir(directory) as listing:
        for entry in listing:
            entries.add(entry.name)
            if len(entries) > MAX_FILES + 1:
                raise CandidateError('too many directory entries')
    if entries != set(files) | {MANIFEST}:
        raise CandidateError('version membership differs from its manifest')
    for name, entry in files.items():
        data = _read_limited(directory/name, MAX_FILE, CandidateError)
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise CandidateError('payload differs from its manifest: '+name)


class Lease:
    """One flock on the lab guard. Closing drops only this descriptor; inherited copies keep it."""

    def __init__(self, lab, mode, fd):
        self.lab = lab
        self.mode = mode
        self.fd = fd
        self.open = True

    @property
    def pass_fds(self):
        return (self.fd,)

    def current(self):
        if not self.open:
            raise ValueError('lease is closed')
        return _read_pointer(self.lab)['current']

    def close(self):
        if self.open:
            self.open = False
            os.close(self.fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def acquire(lab, mode, blocking=False):
    """Take the lab-wide guard: shared for world/start, exclusive for apply/rollback."""
    if mode not in ('shared', 'exclusive'):
        raise ValueError('mode must be shared or exclusive')
    lab = _ordinary_directory(lab, ActivationError)
    try:
        fd = os.open(lab/GUARD, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise ActivationError('guard is unreadable') from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ActivationError('guard is not an ordinary file')
    operation = fcntl.LOCK_SH if mode == 'shared' else fcntl.LOCK_EX
    if not blocking:
        operation |= fcntl.LOCK_NB
    try:
        fcntl.flock(fd, operation)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            raise Busy(mode+' lease refused: the guard is held') from exc
        raise
    return Lease(Path(lab), mode, fd)


def _read_pointer(lab):
    value = _strict_json(_read_limited(Path(lab)/POINTER, MAX_RECORD, PointerError), PointerError)
    if not isinstance(value, dict) or set(value) != {'format', 'current', 'previous'}:
        raise PointerError('pointer shape')
    if value['format'] != FORMAT_POINTER:
        raise PointerError('pointer format')
    current, previous = value['current'], value['previous']
    if not _valid_id(current) or (previous is not None and not _valid_id(previous)):
        raise PointerError('pointer identifiers')
    if previous == current:
        raise PointerError('current and previous must differ')
    return {'current': current, 'previous': previous}


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _cut(requested, point):
    """Forced coordinator exit at a named point: a process-kill cut, not a power-loss claim."""
    if requested == point:
        os._exit(CUT_EXIT)


def _publish(lab, name, record, cutpoint=None):
    """Temp file, fsync, atomic replace, directory fsync: readers see old or new, never a mix."""
    if cutpoint is not None and cutpoint not in CUTPOINTS:
        raise ValueError('unknown cutpoint')
    lab = Path(lab)
    fd, temp = tempfile.mkstemp(dir=lab, prefix='.'+name+'.')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(_canonical(record))
            handle.flush()
            os.fsync(handle.fileno())
        _cut(cutpoint, 'after-temp-fsync')
        os.replace(temp, lab/name)
    except BaseException:
        if os.path.lexists(temp):
            os.unlink(temp)
        raise
    _cut(cutpoint, 'after-replace')
    _fsync_dir(lab)


def _require(lease, mode):
    if not lease.open or lease.mode != mode:
        raise ValueError('operation needs an open '+mode+' lease')


def _refuse_marker(lab):
    if os.path.lexists(Path(lab)/MARKER):
        raise MarkerError('unresolved session marker refuses apply and rollback')


@contextmanager
def _marker_guard(lease):
    """Serialize marker create/resolve while the caller holds a shared world lease."""
    _require(lease, 'shared')
    try:
        fd = os.open(lease.lab/'marker.guard', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except OSError as exc:
        raise MarkerError('marker guard is unreadable') from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise MarkerError('marker guard is not an ordinary file')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _discard(path):
    os.chmod(path, 0o755)
    shutil.rmtree(path)


def install_candidate(lab, files):
    """Write an immutable sealed version addressed by its manifest hash. Existing ones are verified only."""
    lab = _ordinary_directory(lab, CandidateError)
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError('a candidate needs 1 to 64 files')
    for name, data in files.items():
        if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(data, bytes) or len(data) > MAX_FILE:
            raise ValueError('unsafe or oversized candidate file: '+name)
    manifest = _canonical({'format': FORMAT_MANIFEST, 'files': {
        name: {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}
        for name, data in files.items()}})
    version = hashlib.sha256(manifest).hexdigest()
    (lab/VERSIONS).mkdir(exist_ok=True)
    _ordinary_directory(lab/VERSIONS, CandidateError)
    target = lab/VERSIONS/version
    if not os.path.lexists(target):
        staging = Path(tempfile.mkdtemp(dir=lab/VERSIONS, prefix='.staging-'))
        try:
            for name, data in [*files.items(), (MANIFEST, manifest)]:
                fd = os.open(staging/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            _fsync_dir(staging)
            os.chmod(staging, 0o555)
            os.rename(staging, target)
        except OSError:
            _discard(staging)
            if not os.path.lexists(target):
                raise
        _fsync_dir(lab/VERSIONS)
    verify_version(lab, version)
    return version


def initialize(lab, version):
    """Create the guard and the first pointer. Touches no world state and refuses an existing pointer."""
    lab = _ordinary_directory(lab, ActivationError)
    (lab/VERSIONS).mkdir(exist_ok=True)
    _ordinary_directory(lab/VERSIONS, ActivationError)
    fd = os.open(lab/GUARD, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ActivationError('guard is not an ordinary file')
    finally:
        os.close(fd)
    with acquire(lab, 'exclusive'):
        if os.path.lexists(lab/POINTER):
            raise PointerError('pointer already exists')
        verify_version(lab, version)
        _publish(lab, POINTER, {'format': FORMAT_POINTER, 'current': version, 'previous': None})


def activate(lease, candidate, expected_current, cutpoint=None):
    """Point CURRENT at a verified candidate; the old current becomes PREVIOUS. Needs the exclusive lease."""
    _require(lease, 'exclusive')
    _refuse_marker(lease.lab)
    state = _read_pointer(lease.lab)
    if state['current'] != expected_current:
        raise Stale('expected current does not match the pointer')
    if candidate == state['current']:
        raise ActivationError('candidate is already current')
    verify_version(lease.lab, candidate)
    _publish(lease.lab, POINTER,
             {'format': FORMAT_POINTER, 'current': candidate, 'previous': state['current']}, cutpoint)
    return candidate


def rollback(lease, expected_current, cutpoint=None):
    """Return CURRENT to PREVIOUS, verified again. Only pointers move; no data is restored or copied."""
    _require(lease, 'exclusive')
    _refuse_marker(lease.lab)
    state = _read_pointer(lease.lab)
    if state['current'] != expected_current:
        raise Stale('expected current does not match the pointer')
    if state['previous'] is None:
        raise PointerError('no previous version to roll back to')
    verify_version(lease.lab, state['previous'])
    _publish(lease.lab, POINTER,
             {'format': FORMAT_POINTER, 'current': state['previous'], 'previous': state['current']}, cutpoint)
    return state['previous']


def retain_session(lease, session):
    """Record unresolved session work while the shared lease is held. Refuses a second marker."""
    _require(lease, 'shared')
    if not _valid_id(session):
        raise ValueError('session must be a sha256-style identifier')
    with _marker_guard(lease):
        if os.path.lexists(Path(lease.lab)/MARKER):
            raise MarkerError('a session marker already exists')
        _publish(lease.lab, MARKER, {'format': FORMAT_MARKER, 'session': session})


def release_session(lease, session):
    """Resolve this session's marker while the shared lease is still held."""
    _require(lease, 'shared')
    with _marker_guard(lease):
        value = _strict_json(_read_limited(Path(lease.lab)/MARKER, MAX_RECORD, MarkerError), MarkerError)
        if not isinstance(value, dict) or set(value) != {'format', 'session'}:
            raise MarkerError('marker shape')
        if value['format'] != FORMAT_MARKER or not _valid_id(value['session']):
            raise MarkerError('marker identity')
        if value['session'] != session:
            raise MarkerError('marker belongs to another session')
        os.unlink(Path(lease.lab)/MARKER)
        _fsync_dir(lease.lab)
