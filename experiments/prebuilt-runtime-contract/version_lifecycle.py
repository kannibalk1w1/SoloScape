#!/usr/bin/env python3
"""Private native A/B lifecycle driver over the stdio launcher backend.

Each version runs from its own copied payload, with one shared profile, cache and
launcher home. Original inputs are read only. Run only from a fresh directory under
.runtime/prebuilt-version-lifecycle; nothing here touches owner profiles or Deck state.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import selectors
import shutil
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/native-prebuilt-server'))
import local_dev  # noqa: E402
import profiles  # noqa: E402
import session_recovery  # noqa: E402

_spec = importlib.util.spec_from_file_location('lifecycle_payload_helpers', ROOT / 'experiments/native-prebuilt-server/run.py')
support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(support)

ACCOUNT = 'BundleProbe'
PRIOR_RUNS = (ROOT / '.runtime/prebuilt-runtime').resolve()
LIFECYCLE_ROOT = ROOT / '.runtime/prebuilt-version-lifecycle'
PLAY_TIMEOUT = 120
LOGIN_TIMEOUT = 120
ACK_TIMEOUT = 180
SAVE_TIMEOUT = 300
CLEANUP_TIMEOUT = 120
LOGIN = re.compile(r'Player logged in\s+' + ACCOUNT, re.IGNORECASE)
FIELDS = ('accountName', 'experience', 'inventories', 'tile')
ROLES = ('server', 'client')


def log(message):
    print(time.strftime('%H:%M:%S'), message, flush=True)


def sha(path):
    return support.digest(Path(path))


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def port_free(port):
    try:
        local_dev.probe_port(port)
        return True
    except OSError:
        return False


def context_key(root):
    """Same derivation as prebuilt_bootstrap.configure: code root plus manifest hash."""
    manifest = sha(root / 'soloscape-runtime.json')
    return hashlib.sha256((str(root.resolve()) + '\0' + manifest).encode()).hexdigest()


def wait_until(check, timeout, what):
    deadline = time.monotonic() + timeout
    while True:
        result = check()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise TimeoutError(f'Timed out waiting for {what}.')
        time.sleep(0.5)


def playing(record):
    return record['phase'] == 'playing' and set(ROLES) <= set(record['children'])


def validate_run(path, label):
    run = Path(path).resolve(strict=True)
    if run.parent != PRIOR_RUNS or not run.name.isdecimal():
        raise SystemExit(f'{label} run must be a numeric direct child of .runtime/prebuilt-runtime.')
    preparation = json.loads((run / 'preparation.json').read_text())
    if preparation.get('passed') is not True:
        raise SystemExit(f'{label} preparation did not pass.')
    payload_tree = support.tree(run / 'payload')
    if support.tree_digest(payload_tree) != preparation['payload_tree_sha256']:
        raise SystemExit(f'{label} payload differs from its preparation.')
    cache_tree = support.tree(run / 'cache')
    if support.tree_digest(cache_tree) != preparation['cache_tree_sha256']:
        raise SystemExit(f'{label} cache differs from its preparation.')
    jars = {role: sha(run / 'payload' / preparation['roles'][role]) for role in ROLES}
    if jars != preparation['jars']:
        raise SystemExit(f'{label} jars differ from their preparation.')
    return dict(run=run, preparation=preparation, payload=run / 'payload', cache=run / 'cache',
                state=run / 'state', payload_tree=payload_tree, cache_tree=cache_tree, jars=jars,
                manifest_sha=sha(run / 'payload/soloscape-runtime.json'))


def check_pair(old, new):
    if old['payload_tree'] == new['payload_tree'] or old['manifest_sha'] == new['manifest_sha']:
        raise SystemExit('Old and new payloads are identical; choose two different prepared versions.')
    if old['jars']['client'] != new['jars']['client']:
        raise SystemExit('Client jars must match between the two versions.')
    if old['jars']['server'] == new['jars']['server']:
        raise SystemExit('Server jars must differ between the two versions.')
    if old['cache_tree'] != new['cache_tree']:
        raise SystemExit('Both versions must use the same cache inventory.')


def copy_exact(source, destination):
    """Copy with modes preserved, then require identical inventories before use."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    if support.tree(source) != support.tree(destination):
        raise RuntimeError(f'Copy inventory differs: {destination}')
    return support.tree_digest(support.tree(destination))


def write_wrapper(path, java, temp):
    """Forwarding wrapper: execs the real JRE with only -Djava.io.tmpdir prefixed."""
    code = ('#!{py}\nimport os, sys\njava = {java!r}\n'
            'os.execv(java, [java, {opt!r}] + sys.argv[1:])\n')
    path.write_text(code.format(py=sys.executable, java=str(java), opt='-Djava.io.tmpdir=' + str(temp)))
    path.chmod(0o700)
    return path


class Evidence:
    def __init__(self, path, header):
        self.path = path
        self.data = dict(header, passed=False, phases=[])

    def phase(self, name, **facts):
        self.data['phases'].append(dict(phase=name, at=time.strftime('%Y-%m-%dT%H:%M:%S'), **facts))
        log(f'{name}: recorded')
        self.save()

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, indent=2, sort_keys=True, default=str) + '\n')
        temporary.replace(self.path)


class Backend:
    """One launcher_backend.py process speaking one JSON line per request."""

    def __init__(self, name, root, env, logs):
        self.name = name
        self.next_id = 0
        self.buffer = b''
        self.stderr = (logs / (name + '.stderr')).open('wb')
        self.process = subprocess.Popen([sys.executable, '-B', str(root / 'scripts/launcher_backend.py')],
                                        cwd=root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr)

    def request(self, action, timeout=60, **fields):
        self.next_id += 1
        self.process.stdin.write((json.dumps(dict(id=self.next_id, action=action, **fields)) + '\n').encode())
        self.process.stdin.flush()
        return self.read(self.next_id, timeout)

    def read(self, expected, timeout):
        descriptor = self.process.stdout.fileno()
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(descriptor, selectors.EVENT_READ)
            while b'\n' not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError(f'{self.name} did not answer request {expected}.')
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    raise RuntimeError(f'{self.name} closed its reply stream.')
                self.buffer += chunk
                if len(self.buffer) > 4 * 1024 * 1024:
                    raise RuntimeError("Backend reply exceeds private probe bound.")
        line, _, self.buffer = self.buffer.partition(b'\n')
        reply = json.loads(line)
        if reply.get('id') != expected:
            raise RuntimeError(f'{self.name} answered out of order.')
        return reply

    def ok(self, action, **fields):
        reply = self.request(action, **fields)
        if not reply.get('ok'):
            raise RuntimeError(f'{self.name} {action} refused: {reply.get("error")}')
        return reply['result']

    def status(self):
        return self.ok('status')

    def close(self, timeout=CLEANUP_TIMEOUT):
        """Closing stdin is the backend's normal Save & Quit path. Never kills game JVMs."""
        try:
            try:
                self.process.stdin.close()
            except OSError:
                pass
            self.process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False
        finally:
            self.stderr.close()

    def kill(self):
        """Only the Python backend; its JVM children are separate session leaders."""
        self.process.kill()
        self.process.wait(timeout=CLEANUP_TIMEOUT)
        self.stderr.close()


class Probe:
    def __init__(self, args, run, old, new):
        self.args = args
        self.run = run
        self.old = old
        self.new = new
        self.state = run / 'state'
        self.logs = run / 'logs'
        self.cache = run / 'cache'
        self.launcher = self.state / 'launcher'
        self.root_a = run / 'versions/A'
        self.root_b = run / 'versions/B'
        self.evidence = Evidence(run / 'probe.json', dict(
            scope='Private native A/B lifecycle over the stdio backend. No release, update, Deck, owner or physical-input acceptance.',
            audio_excluded=True, physical_input=False, full_update=False,
            runner_sha256=sha(Path(__file__)),
            screen_helper_sha256=sha(Path(__file__).with_name('ScreenInput.java')),
            source_commits=dict(A=old['preparation']['source_commit'], B=new['preparation']['source_commit']),
            jar_sha256=dict(A=old['jars'], B=new['jars']),
            manifest_sha256=dict(A=old['manifest_sha'], B=new['manifest_sha']),
            old_run=str(old['run']), new_run=str(new['run'])))
        self.backends = []
        self.display = None
        self.xvfb = None
        self.wrappers = {}
        self.snapshot = {}
        self.children = {}
        self.session = None
        self.known_children = []

    # -- setup -------------------------------------------------------------
    def setup(self):
        for directory in (self.state, self.logs, self.state / 'bin', self.state / 'temp', self.state / 'home'):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.launcher.mkdir(mode=0o700)
        (self.state / 'alsa.conf').write_text('')
        self.start_display()
        javac = Path(self.args.client_java).with_name('javac')
        if not javac.exists():
            raise RuntimeError('A JDK8 javac next to the client java is required to compile ScreenInput.')
        (self.run / 'input').mkdir(mode=0o700)
        subprocess.run([str(javac), '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-d', str(self.run / 'input'),
                        str(Path(__file__).with_name('ScreenInput.java'))], check=True)
        self.snapshot = dict(A=copy_exact(self.old['payload'], self.root_a),
                             B=copy_exact(self.new['payload'], self.root_b),
                             cache=copy_exact(self.old['cache'], self.cache),
                             old_profiles=support.tree_digest(support.tree(self.old['state'] / 'profiles')))
        source_profiles = self.old['state'] / 'profiles'
        copy_exact(source_profiles, self.state / 'profiles')
        self.setup_fixture()
        self.wrappers = dict(
            server=str(write_wrapper(self.state / 'bin/server-java', self.args.server_java.resolve(strict=True), self.state / 'temp')),
            client=str(write_wrapper(self.state / 'bin/client-java', self.args.client_java.resolve(strict=True), self.state / 'temp')))
        self.baseline = self.save_fields()
        log(f'setup: fixture profile {self.uid} copied; baseline tile recorded')

    def setup_fixture(self):
        profile_home = self.state / 'profiles'
        if any((path / 'session.json').exists() for path in (self.old['state'] / 'profiles').iterdir()):
            raise RuntimeError('Old fixture has an unfinished session record; refusing to copy it.')
        entries = list(profile_home.iterdir())
        if len(entries) != 1 or not entries[0].is_dir() or entries[0].is_symlink():
            raise RuntimeError('Fixture must hold exactly one profile directory.')
        self.profile_dir = entries[0]
        self.uid = self.profile_dir.name
        self.profile = profiles.Profile(self.profile_dir)
        if self.profile.manifest['account'].lower() != ACCOUNT.lower():
            raise RuntimeError('Fixture profile is not the BundleProbe account.')
        if (self.profile_dir / 'session.json').exists():
            raise RuntimeError('Fixture profile has a session record; refusing to start.')
        self.generation = self.profile.manifest['generation']
        rows = self.backups()
        if len(rows) != 4 or not all(row['valid'] for row in rows):
            raise RuntimeError('Fixture must retain exactly four valid backups.')

    def start_display(self):
        read_fd, write_fd = os.pipe()
        environment = {'PATH': os.defpath, 'HOME': str(self.state / 'home'), 'TMPDIR': str(self.state / 'temp'), 'LANG': 'C.UTF-8'}
        with (self.logs / 'xvfb.stderr').open('wb') as errors:
            self.xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                                         env=environment, pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=errors)
        os.close(write_fd)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(read_fd, selectors.EVENT_READ)
                if not selector.select(10):
                    raise RuntimeError('Private Xvfb handshake timed out.')
                number = os.read(read_fd, 64).decode().strip()
        finally:
            os.close(read_fd)
        if not number.isdecimal() or self.xvfb.poll() is not None:
            raise RuntimeError('Private display failed.')
        self.display = ':' + number

    def environment(self):
        return {'PATH': os.defpath, 'HOME': str(self.state / 'home'), 'TMPDIR': str(self.state / 'temp'), 'LANG': 'C.UTF-8',
                'PYTHONDONTWRITEBYTECODE': '1', 'ALSA_CONFIG_PATH': str(self.state / 'alsa.conf'),
                'SOLOSCAPE_PROFILE_HOME': str(self.state / 'profiles'), 'SOLOSCAPE_CACHE_HOME': str(self.cache),
                'SOLOSCAPE_LAUNCHER_HOME': str(self.launcher), 'SERVER_JAVA': self.wrappers['server'],
                'CLIENT_JAVA': self.wrappers['client'], 'LIBGL_ALWAYS_SOFTWARE': '1', 'DISPLAY': self.display}

    def backend(self, name, root):
        backend = Backend(name, root, self.environment(), self.logs)
        self.backends.append(backend)
        return backend

    # -- observation -------------------------------------------------------
    def read_record(self):
        path = self.profile_dir / 'session.json'
        record = json.loads(path.read_text()) if path.exists() else None
        if record:
            for process in record['children'].values():
                if process not in self.known_children:
                    self.known_children.append(process)
        return record

    def wait_record(self, ready, timeout, what):
        def check():
            record = self.read_record()
            return record if record and ready(record) else None
        return wait_until(check, timeout, what)

    def wait_stage(self, backend, stage, timeout):
        def check():
            status = backend.status()
            if status['stage'] == 'error':
                raise RuntimeError(f"{backend.name} error: {status['error']}")
            return status if status['stage'] == stage and status['running'] else None
        return wait_until(check, timeout, f'{backend.name} stage {stage}')

    def wait_idle(self, backend, timeout):
        def check():
            status = backend.status()
            return None if status['running'] else status
        return wait_until(check, timeout, f'{backend.name} to finish')

    def wait_login(self):
        """Matches the server log line only; log contents are never printed."""
        log_file = self.profile_dir / 'session-logs/server.log'
        wait_until(lambda: log_file.exists() and bool(LOGIN.search(log_file.read_text(errors='replace'))),
                   LOGIN_TIMEOUT, 'native login')

    def profile_row(self, backend):
        return next(row for row in backend.ok('list')['profiles'] if row['id'] == self.uid)

    def children_alive(self):
        return {role: session_recovery.same_process(self.children[role]) for role in ROLES}

    def backups(self):
        profile = profiles.Profile(self.profile_dir)
        rows = []
        for path in sorted((self.profile_dir / 'backups').glob('*.zip')):
            try:
                manifest, _ = profile.validate_backup(path)
                rows.append(dict(name=path.name, reason=manifest.get('reason', ''),
                                 recovered_from_session=manifest.get('recovered_from_session'), valid=True))
            except (ValueError, OSError, KeyError) as exc:
                rows.append(dict(name=path.name, valid=False, error=str(exc)))
        return rows

    def journal_state(self):
        path = self.profile_dir / 'session.json'
        return dict(journal=sha(path) if path.exists() else None, backups=self.backups(), children=self.children_alive())

    def save_fields(self):
        save = self.profile.state / 'saves' / 'bundleprobe.toml'
        account = profiles.validate_save(save.read_bytes(), ACCOUNT)
        return {key: account[key] for key in FIELDS}

    def screenshot(self, name):
        target = self.run / 'screens' / (name + '.png')
        target.parent.mkdir(exist_ok=True)
        subprocess.run([self.args.client_java.as_posix(), '-cp', str(self.run / 'input'), 'ScreenInput', 'screenshot', str(target)],
                       env={'PATH': os.defpath, 'HOME': str(self.state / 'home'), 'TMPDIR': str(self.state / 'temp'),
                            'LANG': 'C.UTF-8', 'DISPLAY': self.display}, check=True, timeout=60)
        return dict(path=str(target), sha256=sha(target))

    def child_proof(self, root, preparation, record):
        """Raw argv: the real JRE, then -jar and the exact jar path; guards via same_process."""
        proof = {}
        for role in ROLES:
            process = self.children[role]
            argv = Path(f"/proc/{process['pid']}/cmdline").read_bytes().split(b'\0')[:-1]
            jar = str(root / preparation['roles'][role])
            exact = argv[argv.index(b'-jar') + 1] == jar.encode() and record['jars'][role] == jar
            expected_java = self.args.server_java if role == 'server' else self.args.client_java
            real_java = argv[0].decode() == str(expected_java.resolve(strict=True))
            same = session_recovery.same_process(process)
            proof[role] = dict(pid=process['pid'], same_process=same, argv0=argv[0].decode(), raw_jar=jar,
                               raw_jar_exact=exact, real_java=real_java, jar_sha256=sha(jar))
            if not (exact and real_java and same):
                raise RuntimeError(f'Raw jar or guard proof failed for {role}.')
        return proof

    def context_proof(self, record):
        contexts = self.launcher / 'version-contexts'
        keys = dict(A=context_key(self.root_a), B=context_key(self.root_b))
        if sorted(keys.values()) != sorted(path.name for path in contexts.iterdir()):
            raise RuntimeError('Exactly two version contexts must exist.')
        build = {}
        for name, key in keys.items():
            info = (contexts / key / 'build.lock').stat()
            build[name] = [info.st_dev, info.st_ino]
        if record['locks']['build'] != build['A'] or build['A'] == build['B']:
            raise RuntimeError('Recorded build lock is not the original context lock.')
        return dict(context_ids=keys, build_lock_inode=build)

    # -- phases ------------------------------------------------------------
    def phase1_start_a(self):
        log('phase 1: A starts a native world and logs in')
        self.port_a = free_port()
        self.a1 = self.backend('A1', self.root_a)
        self.a1.ok('start', profile=self.uid, port=self.port_a)
        self.wait_stage(self.a1, 'playing', PLAY_TIMEOUT)
        record = self.wait_record(playing, PLAY_TIMEOUT, 'playing record with both children')
        self.session = record['session']
        self.children = record['children']
        self.wait_login()
        proof = self.child_proof(self.root_a, self.old['preparation'], record)
        shot = self.screenshot('phase1-A-playing')
        self.evidence.phase('A-playing', session=self.session, port=self.port_a,
                            recovery_row_while_owner_live=self.profile_row(self.a1)['recovery'],
                            children=proof, screenshot=shot)

    def phase2_refuse_second_world(self):
        log('phase 2: B on the same profile, different free port')
        before = self.journal_state()
        port = free_port()
        if port == self.port_a or not port_free(port):
            raise RuntimeError('No distinct free port for B.')
        self.b1 = self.backend('B1', self.root_b)
        self.b1.ok('start', profile=self.uid, port=port)
        status = self.wait_idle(self.b1, PLAY_TIMEOUT)
        message = status['error'] or ''
        # The profile-lock error is raised after doctor and build-stamp checks, so
        # a port or preflight failure would carry different text.
        if status['stage'] != 'error' or 'character/world is running' not in message.lower() or 'port' in message.lower():
            raise RuntimeError('B was not refused by the profile lock: ' + message)
        if self.journal_state() != before:
            raise RuntimeError('B refusal changed the journal, backups or children.')
        if not port_free(port):
            raise RuntimeError('B left its refused port occupied.')
        self.b1.close()
        self.evidence.phase('B-refused-same-profile', port=port, error=message, refused_after_preflight=True)

    def phase3_kill_a_and_refuse_b(self):
        log('phase 3: SIGKILL only the A backend process; B must refuse recovery')
        record = self.read_record()
        before = self.journal_state()
        identity = session_recovery.identity(self.a1.process.pid)
        if record['owner']['pid'] != self.a1.process.pid or record['owner']['start'] != identity['start']:
            raise RuntimeError('The A backend is not the recorded owner.')
        self.a1.kill()
        if not all(self.children_alive().values()) or self.journal_state() != before:
            raise RuntimeError('Killing the backend changed the JVMs or the journal.')
        self.b2 = self.backend('B2', self.root_b)
        recovery = self.profile_row(self.b2)['recovery']
        if not recovery or recovery['recoverable'] or 'could not be verified' not in recovery['message']:
            raise RuntimeError('B list did not refuse the orphan: ' + str(recovery))
        self.b2.ok('recover', profile=self.uid, port=free_port())
        status = self.wait_idle(self.b2, PLAY_TIMEOUT)
        if status['stage'] != 'error' or 'identity changed' not in (status['error'] or ''):
            raise RuntimeError('B recover did not fail on identity change: ' + str(status))
        archive = self.b2.request('archive_session', profile=self.uid)
        self.evidence.phase('B-archive-response', response=archive)
        if archive.get('ok') or archive.get('error') != 'This character/world is running or another save operation is active.':
            raise RuntimeError('B archive was not refused by the live profile lock: ' + str(archive))
        if self.journal_state() != before:
            raise RuntimeError('B refusals changed the journal, backups or children.')
        self.evidence.phase('orphan-refusals-from-B', recovery_row=recovery, recover_error=status['error'],
                            archive_error=archive.get('error'), journal_unchanged=True,
                            children_alive=self.children_alive(), contexts=self.context_proof(record))

    def phase4_recover_original(self):
        log('phase 4: original A context recovers the orphaned world')
        self.a2 = self.backend('A2', self.root_a)
        recovery = self.profile_row(self.a2)['recovery']
        if not recovery or not recovery['recoverable'] or sorted(recovery['active']) != sorted(ROLES):
            raise RuntimeError('A list did not prove both recorded guards: ' + str(recovery))
        before = self.save_fields()
        self.a2.ok('recover', profile=self.uid, port=free_port())
        status = self.wait_idle(self.a2, SAVE_TIMEOUT)
        if status['stage'] != 'stopped' or status['error'] or 'Clean shutdown is unconfirmed' not in status['message']:
            raise RuntimeError('A recovery did not report unconfirmed closure: ' + str(status))
        if self.read_record() is not None or any(self.children_alive().values()):
            raise RuntimeError('Recovered journal or JVMs remain.')
        recovered = [row for row in self.backups()
                     if row.get('reason') == 'after-recovered-shutdown' and row.get('recovered_from_session') == self.session]
        if len(recovered) != 1 or not recovered[0]['valid']:
            raise RuntimeError('Expected one valid after-recovered-shutdown backup for this session.')
        after = self.save_fields()
        if before != self.baseline or after != self.baseline:
            raise RuntimeError('Original-context recovery changed the compared fixture account fields.')
        self.evidence.phase('A-recovered-original-context', recovery_row=recovery, status_message=status['message'],
                            backup=recovered[0], save_before=before, save_after=after)
        self.a2.close()

    def phase5_continue_b(self):
        log('phase 5: B continues, waits for the coordinator ack, then stops')
        self.b2.ok('start', profile=self.uid, port=free_port())
        self.wait_stage(self.b2, 'playing', PLAY_TIMEOUT)
        record = self.wait_record(playing, PLAY_TIMEOUT, 'B playing record')
        if record['session'] == self.session:
            raise RuntimeError('B reused the recovered session id.')
        self.children = record['children']
        self.wait_login()
        loaded = self.save_fields()
        if loaded != self.baseline:
            raise RuntimeError('Candidate did not continue the original compared fixture state.')
        shot = self.screenshot('phase5-B-login')
        request = dict(format=1, display=self.display, screenshot=shot['path'], screenshot_sha256=shot['sha256'],
                       native_session=record['session'], profile_directory=str(self.profile_dir),
                       generation=self.generation, save_path=str(self.profile.state / 'saves/bundleprobe.toml'),
                       saved_tile=loaded['tile'], baseline_tile=self.baseline['tile'],
                       ack_file=str(self.run / 'progress.ack'))
        (self.run / 'progress-request.json').write_text(json.dumps(request, indent=2, default=str) + '\n')
        log('waiting up to 180s for run/progress.ack from the coordinator')
        ack = self.wait_ack(shot['sha256'])
        time.sleep(5)
        self.b2.ok('stop')
        status = self.wait_idle(self.b2, SAVE_TIMEOUT)
        if status['stage'] != 'stopped' or status['error'] or 'World saved and verified' not in status['message']:
            raise RuntimeError('B stop was not a verified normal save: ' + str(status))
        if self.read_record() is not None:
            raise RuntimeError('B stop left its journal behind.')
        after = self.save_fields()
        if any(after[key] != loaded[key] for key in ('accountName', 'experience', 'inventories')):
            raise RuntimeError('Account, XP or inventory changed during movement.')
        if after['tile'] == self.baseline['tile']:
            raise RuntimeError('No movement witness: saved tile equals the baseline tile.')
        self.post_b = after
        self.evidence.phase('B-continue-movement', native_session=record['session'], ack=ack,
                            status_message=status['message'], save_loaded=loaded, save_after=after,
                            backups_clean=[row for row in self.backups() if row.get('reason') == 'after-clean-shutdown'])
        self.b2.close()

    def wait_ack(self, screenshot_sha):
        ack_path = self.run / 'progress.ack'

        def check():
            if not ack_path.exists():
                return None
            try:
                ack = json.loads(ack_path.read_text())
            except ValueError:
                return None
            if ack.get('screenshot_sha256') != screenshot_sha:
                raise RuntimeError('Ack names a different screenshot.')
            if type(ack.get('x')) is not int or type(ack.get('y')) is not int:
                raise RuntimeError('Ack lacks integer coordinates.')
            return ack
        return wait_until(check, ACK_TIMEOUT, 'coordinator ack')

    def phase6_rollback_a(self):
        log('phase 6: A rollback continues the same generation without restore')
        self.a3 = self.backend('A3', self.root_a)
        self.a3.ok('start', profile=self.uid, port=free_port())
        self.wait_stage(self.a3, 'playing', PLAY_TIMEOUT)
        record = self.wait_record(playing, PLAY_TIMEOUT, 'A rollback playing record')
        self.children = record['children']
        self.wait_login()
        self.a3.ok('stop')
        status = self.wait_idle(self.a3, SAVE_TIMEOUT)
        if status['stage'] != 'stopped' or status['error'] or 'World saved and verified' not in status['message']:
            raise RuntimeError('A rollback stop was not a verified normal save: ' + str(status))
        final = self.save_fields()
        if any(final[key] != self.post_b[key] for key in FIELDS):
            raise RuntimeError('A rollback did not keep the B progress.')
        if profiles.Profile(self.profile_dir).manifest['generation'] != self.generation:
            raise RuntimeError('Generation changed; a restore may have happened.')
        rows = self.backups()
        if not all(row['valid'] for row in rows):
            raise RuntimeError('A backup is invalid after rollback.')
        self.evidence.phase('A-rollback', status_message=status['message'], save_final=final,
                            generation_unchanged=True, backup_reasons=dict(Counter(row['reason'] for row in rows)),
                            backup_total=len(rows))
        self.a3.close()

    def verify_inputs(self):
        checks = dict(
            A=support.tree_digest(support.tree(self.root_a)) == self.snapshot['A'],
            B=support.tree_digest(support.tree(self.root_b)) == self.snapshot['B'],
            cache=support.tree_digest(support.tree(self.cache)) == self.snapshot['cache'],
            old_profiles_source=support.tree_digest(support.tree(self.old['state'] / 'profiles')) == self.snapshot['old_profiles'],
            old_payload=support.tree_digest(support.tree(self.old['payload'])) == self.old['preparation']['payload_tree_sha256'],
            new_payload=support.tree_digest(support.tree(self.new['payload'])) == self.new['preparation']['payload_tree_sha256'],
            old_cache_source=support.tree_digest(support.tree(self.old['cache'])) == self.old['preparation']['cache_tree_sha256'])
        self.evidence.phase('inputs-unchanged', checks=checks)
        if not all(checks.values()):
            raise RuntimeError('Payload, cache or fixture inputs changed: ' + str(checks))

    def cleanup(self):
        """Preserve evidence and display if any owned process cannot close normally."""
        clean = True
        for backend in list(self.backends):
            if backend.process.poll() is None and not backend.close():
                clean = False
                log(f'{backend.name} did not exit within 120s; retained')
        record = self.read_record() if hasattr(self, 'profile_dir') else None
        if record and any(session_recovery.same_process(child) for child in record['children'].values()):
            owner = None
            for name, root, preparation in (('A', self.root_a, self.old['preparation']), ('B', self.root_b, self.new['preparation'])):
                if all(record['jars'][role] == str(root / preparation['roles'][role]) for role in ROLES):
                    owner = (name, root)
            if owner is None or not self.wrappers:
                clean = False
                log('Orphan cannot be matched to a prepared context; not signalling.')
            else:
                backend = self.backend('cleanup-' + owner[0], owner[1])
                try:
                    backend.ok('recover', profile=self.uid, port=free_port())
                    status = self.wait_idle(backend, CLEANUP_TIMEOUT)
                    if status['error']:
                        clean = False
                except (RuntimeError, TimeoutError, OSError) as exc:
                    clean = False
                    log(f'Cleanup recovery did not finish: {exc}')
                if not backend.close():
                    clean = False
        retained = [child for child in self.known_children if session_recovery.same_process(child)]
        retained_backends = [backend.process.pid for backend in self.backends if backend.process.poll() is None]
        if retained or retained_backends:
            clean = False
        self.evidence.data['retained_children'] = retained
        self.evidence.data['retained_backend_pids'] = retained_backends
        self.evidence.data['retained_display'] = self.display if not clean else None
        if clean and self.xvfb is not None and self.xvfb.poll() is None:
            self.xvfb.terminate()
            self.xvfb.wait(timeout=10)
        return clean

    def execute(self):
        try:
            self.setup()
            self.phase1_start_a()
            self.phase2_refuse_second_world()
            self.phase3_kill_a_and_refuse_b()
            self.phase4_recover_original()
            self.phase5_continue_b()
            self.phase6_rollback_a()
            self.verify_inputs()
            self.evidence.data['passed'] = True
        except BaseException as exc:
            self.evidence.data['failure'] = f'{type(exc).__name__}: {exc}'
            log('probe failed; evidence preserved: ' + str(self.evidence.path))
            raise
        finally:
            try:
                clean = self.cleanup()
            except BaseException as cleanup_error:
                clean = False
                self.evidence.data['cleanup_failure'] = str(cleanup_error)
                self.evidence.data['retained_display'] = self.display
            self.evidence.data['cleanup_clean'] = clean
            if not clean:
                self.evidence.data['passed'] = False
            self.evidence.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-run', type=Path, required=True)
    parser.add_argument('--new-run', type=Path, required=True)
    parser.add_argument('--server-java', type=Path, required=True)
    parser.add_argument('--client-java', type=Path, required=True)
    args = parser.parse_args()
    with local_dev.build_lock():
        old = validate_run(args.old_run, 'old')
        new = validate_run(args.new_run, 'new')
        check_pair(old, new)
        LIFECYCLE_ROOT.mkdir(parents=True, exist_ok=True)
        run = LIFECYCLE_ROOT / str(time.time_ns())
        run.mkdir(mode=0o700)
        log(f'run directory {run}')
        with patch.object(profiles, 'PROFILES', run / 'state/profiles'):
            Probe(args, run, old, new).execute()


if __name__ == '__main__':
    main()
