"""Linux recovery of recorded owned JVMs. Never infer clean shutdown from exit alone."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import select
import signal
import time
import uuid
import local_dev
import profiles

RECORD = 'session.json'


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def identity(pid):
    if type(pid) is not int or pid < 1:
        raise ValueError('Invalid recorded process identity.')
    path = Path('/proc')/str(pid)
    if path.stat().st_uid != os.getuid():
        raise ValueError('Recorded process belongs to another user.')
    tail = (path/'stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'start': int(tail[19]), 'state': tail[0]}


def same_process(process):
    try:
        current = identity(process['pid'])
        return current['start'] == process['start'] and current['state'] not in ('Z', 'X')
    except (OSError, ValueError, KeyError):
        return False


def lock_identity(path):
    stat = path.stat()
    return [stat.st_dev, stat.st_ino]


def read(profile):
    path = profile.directory/RECORD
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or path.stat().st_size > 16384:
        raise ValueError('Session record is unsafe or damaged; preserve it for manual recovery.')
    record = json.loads(path.read_text())
    if (not isinstance(record, dict) or record.get('format') != 1
            or record.get('profile') != profile.manifest['id']
            or record.get('generation') != profile.manifest['generation']
            or not re.fullmatch('[0-9a-f]{32}', str(record.get('session', '')))):
        raise ValueError('Session record does not match this world; preserve it for manual recovery.')
    return record


def begin(profile, port, server_jar, client_jar):
    if read(profile) is not None:
        raise RuntimeError('An earlier session has unverified closure. Use Recover Session before starting again.')
    record = {'format': 1, 'session': uuid.uuid4().hex, 'profile': profile.manifest['id'],
              'generation': profile.manifest['generation'], 'boot': boot_id(),
              'owner': identity(os.getpid()), 'port': port, 'started': profiles.now(),
              'phase': 'starting', 'children': {},
              'jars': {'server': str(server_jar), 'client': str(client_jar)},
              'locks': {'profile': lock_identity(profile.directory/'profile.lock'),
                        'build': lock_identity(local_dev.RUNTIME/'build.lock')}}
    write(profile, record)
    return record


def write(profile, record):
    profiles.atomic_json(profile.directory/RECORD, record)


def registered(profile, record, role, process):
    record['children'][role] = identity(process.pid)
    write(profile, record)


def verified(profile, record, process, role):
    """Caller opens pidfd first. Verify start, boot, owner, environment, argv and both guards."""
    if record['boot'] != boot_id() or not same_process(process):
        return False
    path = Path('/proc')/str(process['pid'])
    environment = dict(part.split(b'=', 1) for part in (path/'environ').read_bytes().split(b'\0') if b'=' in part)
    expected = {b'SOLOSCAPE_SESSION_ID': record['session'].encode(),
                b'SOLOSCAPE_SESSION_ROLE': role.encode(),
                b'storage.players.path': (str(profile.state.resolve()/'saves')+'/').encode()}
    if any(environment.get(key) != value for key, value in expected.items()):
        return False
    argv = (path/'cmdline').read_bytes().split(b'\0')
    if record['jars'][role].encode() not in argv:
        return False
    wanted = {tuple(value) for value in record['locks'].values()}
    # Reject replaced lock files even if a PID still holds an older description.
    if wanted != {tuple(lock_identity(profile.directory/'profile.lock')),
                  tuple(lock_identity(local_dev.RUNTIME/'build.lock'))}:
        return False
    held = set()
    for fd in (path/'fd').iterdir():
        try:
            stat = fd.stat()
            key = (stat.st_dev, stat.st_ino)
            if key in wanted and 'FLOCK' in (path/'fdinfo'/fd.name).read_text():
                held.add(key)
        except (OSError, ValueError):
            continue
    return held == wanted


def candidates(profile, record):
    found = dict(record['children'])
    if record['boot'] != boot_id():
        return {}  # old boot cannot own a current process
    # Close the Popen -> record write crash gap using the unique session/role + guards.
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            process = identity(int(path.name))
            for role in ('server', 'client'):
                if role not in found and verified(profile, record, process, role):
                    found[role] = process
        except (OSError, ValueError, KeyError):
            continue
    return found


def inspect(profile, owner_active=None):
    try:
        record = read(profile)
        if record is None:
            return None
        owner_alive = record['phase'] != 'unverified' and record['boot'] == boot_id() and same_process(record['owner'])
        if owner_active is not None and record['owner']['pid'] == os.getpid():
            owner_alive = owner_alive and owner_active()
        processes = record['children']  # Crash-gap discovery is reserved for explicit recovery.
        active = []
        for role, process in processes.items():
            if same_process(process) and record['boot'] == boot_id():
                if not verified(profile, record, process, role):
                    return {'recoverable': False, 'message': 'Session process identity could not be verified. No automatic stop is available.'}
                active.append(role)
        return {'recoverable': not owner_alive, 'archiveable': not owner_alive and not active,
                'session': record['session'], 'active': active,
                'message': 'World is owned by another active launcher.' if owner_alive else
                    'Earlier launcher session needs recovery. Save & Quit will stop only verified owned processes; clean closure is unconfirmed.'}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'recoverable': False, 'message': 'Session recovery unavailable: '+str(exc)}


@contextmanager
def recovery_lock(profile):
    fd = os.open(profile.directory/'recovery.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another launcher is recovering this session.') from exc
        yield


def archive_ended(profile, owner_active=None):
    """Explicitly retain unverified closure evidence so a damaged stopped world can restore."""
    with recovery_lock(profile), local_dev.build_lock(shared=True), profile.lock():
        record = read(profile)
        if record is None:
            raise RuntimeError('No earlier session record remains.')
        status = inspect(profile, owner_active)
        if not status.get('archiveable') or any(same_process(child) for child in candidates(profile, record).values()):
            raise RuntimeError('Earlier session is active or cannot be verified as ended. No record was archived.')
        target = profile.directory/('session.'+record['session']+'.unverified.json')
        if target.exists() or target.is_symlink():
            raise RuntimeError('An archived record with this identity already exists; preserve both for inspection.')
        (profile.directory/RECORD).rename(target)
        profiles.fsync_directory(profile.directory)
        return {'message': 'Ended session record archived. Current world closure remains unverified; restore a verified backup before trusting a damaged save.'}


def recover(profile, cancelled, notify, owner_active=None):
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Safe session recovery needs Linux pidfd support; no process was signalled.')
    with recovery_lock(profile), local_dev.build_lock(shared=True):
        record = read(profile)
        if record is None:
            raise RuntimeError('No recorded session needs recovery.')
        owner_alive = record['phase'] != 'unverified' and record['boot'] == boot_id() and same_process(record['owner'])
        if owner_active is not None and record['owner']['pid'] == os.getpid():
            owner_alive = owner_alive and owner_active()
        if owner_alive:
            raise RuntimeError('The original launcher is still active; use its Save & Quit.')
        handles = {}
        try:
            for role, process in candidates(profile, record).items():
                if record['boot'] != boot_id() or not same_process(process):
                    continue
                fd = os.pidfd_open(process['pid'])
                handles[role] = fd
                if not verified(profile, record, process, role):
                    raise RuntimeError('Owned process identity changed; no process was signalled.')
                if identity(process['pid'])['state'] in ('T', 't'):
                    raise RuntimeError('An owned process is suspended. Resume it before recovery; no process was signalled.')
            if cancelled.is_set():
                notify('stopped', 'Recovery cancelled before signalling. Earlier session retained.')
                return 0
            # Recheck after all pidfds are opened: an unrelated replacement cannot receive signals.
            for role in ('client', 'server'):
                if role not in handles:
                    continue
                notify('saving', 'Stopping earlier owned '+role+'; waiting for normal save hooks…')
                try:
                    signal.pidfd_send_signal(handles[role], signal.SIGTERM)
                except ProcessLookupError:
                    pass
                waited = time.monotonic()
                while not select.select([handles[role]], [], [], 1)[0]:
                    if time.monotonic()-waited >= 60:
                        notify('saving', 'Still waiting for earlier owned '+role+' to close. No forced kill will interrupt saves.')
                        waited = time.monotonic()
            # Inherited guards must really be released; do not infer it from pidfd exit alone.
            with profile.lock():
                if read(profile)['session'] != record['session']:
                    raise RuntimeError('Session record changed during recovery.')
                dirty = any((profile.state/'errors').rglob('*')) or any(profile.state.rglob('.save-*.tmp'))
                if dirty:
                    raise RuntimeError('Recovered processes closed, but save errors/temporary files need inspection. Previous backups and session record retained.')
                profile._backup('after-recovered-shutdown', recovered_from_session=record['session'])
                (profile.directory/RECORD).unlink()
                profiles.fsync_directory(profile.directory)
            notify('stopped', 'Recovered world closed; snapshot verified. Clean shutdown is unconfirmed. Previous backups retained.')
            return 0
        finally:
            for fd in handles.values():
                os.close(fd)
