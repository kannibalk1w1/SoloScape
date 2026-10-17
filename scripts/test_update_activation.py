"""Private multiprocess proof for the lab-only update activation gate. Not production evidence.

Every fixture is original inert bytes under a disposable lab root inside the private
.runtime directory. Child processes run the real gate module with -I; nothing runs
candidate files, native games, JVMs or the network. Only fixture PIDs we spawned are
signalled, and only when their own command line still names the inert sleeper.
"""
import hashlib
import inspect
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = ROOT/'experiments'/'update-activation'
PRIVATE = ROOT/'.runtime'/'update-activation-gate-20261017'
TIMEOUT = 20
sys.path.insert(0, str(GATE_DIR))
try:
    import gate
except ImportError:  # no fcntl flock on this platform
    gate = None

PRELUDE = 'import os, sys\nsys.path.insert(0, sys.argv[1])\nimport gate\n'
SLEEPER = 'import signal, sys\nsignal.signal(signal.SIGTERM, lambda *a: sys.exit(0))\nsignal.alarm(60)\nsignal.pause()\n'
SESSION = 'c' * 64
OTHER = 'd' * 64

WORLD_HOLD = '''
with gate.acquire(sys.argv[2], "shared") as lease:
    print(lease.current(), os.stat(os.path.join(sys.argv[2], gate.GUARD)).st_ino, flush=True)
    sys.stdin.readline()
'''

TRY = '''
print("waiting", flush=True)
try:
    with gate.acquire(sys.argv[2], sys.argv[3], blocking=sys.argv[4] == "wait") as lease:
        print("acquired", lease.current(), flush=True)
        sys.stdin.readline()
except gate.Busy:
    print("busy", flush=True)
'''

LAUNCH = '''
import subprocess
with gate.acquire(sys.argv[2], "shared") as lease:
    grand = subprocess.Popen([sys.executable, "-I", "-c", sys.argv[3], sys.argv[4]], pass_fds=lease.pass_fds,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    print(grand.pid, flush=True)
'''

WAIT_START = '''
try:
    lease = gate.acquire(sys.argv[2], "shared")
except gate.Busy:
    print("blocked", flush=True)
    lease = gate.acquire(sys.argv[2], "shared", blocking=True)
else:
    print("unexpectedly-acquired", flush=True)
with lease:
    print("acquired", lease.current(), flush=True)
    sys.stdin.readline()
'''

RETAIN_RACE = '''
with gate.acquire(sys.argv[2], "shared") as lease:
    print("ready", flush=True)
    sys.stdin.readline()
    try:
        gate.retain_session(lease, sys.argv[3])
        print("retained", flush=True)
    except gate.MarkerError:
        print("MarkerError", flush=True)
'''

ACT = '''
lab, op, candidate, expected, cut = sys.argv[2:7]
point = None if cut == "-" else cut
try:
    with gate.acquire(lab, "exclusive") as lease:
        if op == "activate":
            print("ok", gate.activate(lease, candidate, expected, cutpoint=point), flush=True)
        else:
            print("ok", gate.rollback(lease, expected, cutpoint=point), flush=True)
except gate.ActivationError as exc:
    print(type(exc).__name__, flush=True)
'''

WORLD_WRITE = '''
lab = sys.argv[2]
with gate.acquire(lab, "shared") as lease:
    if lease.current() != sys.argv[3]:
        raise SystemExit(3)
    with open(os.path.join(lab, "world-state.bin"), "wb") as handle:
        handle.write(sys.argv[4].encode())
print("wrote", flush=True)
'''

WORLD_MARK = '''
with gate.acquire(sys.argv[2], "shared") as lease:
    gate.retain_session(lease, sys.argv[3])
print("retained", flush=True)
'''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _remove_tree(path):
    for root, _dirs, _files in os.walk(path):
        os.chmod(root, 0o755)
    shutil.rmtree(path, ignore_errors=True)


def _stop_owned_sleeper(record):
    """Use the captured pidfd, exact original program and unique nonce; SIGTERM only."""
    fd, pid, nonce = record
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as handle:
            argv = handle.read().rstrip(b'\0').split(b'\0')
        if argv[-4:] != [b'-I', b'-c', SLEEPER.encode(), nonce.encode()]:
            return False
        signal.pidfd_send_signal(fd, signal.SIGTERM)
        return True
    except OSError:
        return False


def _run(code, *args):
    with open(PRIVATE/'child-stderr.log', 'a') as log:
        return subprocess.run([sys.executable, '-I', '-c', PRELUDE+code, str(GATE_DIR), *map(str, args)],
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=log,
                              text=True, timeout=TIMEOUT, check=False)


def _line(proc):
    """Read one complete line with a deadline; no sleeps, no busy-wait."""
    deadline = time.monotonic() + TIMEOUT
    data = b''
    while not data.endswith(b'\n'):
        ready, _, _ = select.select([proc.stdout], [], [], max(deadline - time.monotonic(), 0))
        if not ready:
            raise TimeoutError('child produced no line in time')
        chunk = os.read(proc.stdout.fileno(), 1)
        if not chunk:
            raise EOFError('child closed stdout')
        data += chunk
    return data.decode().strip()


@unittest.skipUnless(gate is not None and sys.platform.startswith('linux')
                     and hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                     'update activation lab needs Linux flock and pidfd support')
class UpdateActivationTests(unittest.TestCase):
    def setUp(self):
        PRIVATE.mkdir(parents=True, exist_ok=True)
        self.lab = Path(tempfile.mkdtemp(prefix='lab-', dir=PRIVATE))
        self.addCleanup(_remove_tree, self.lab)
        self.procs = []
        self.owned_pids = []
        self.addCleanup(self._reap)
        self.a = gate.install_candidate(self.lab, {'run.txt': b'inert version A\n'})
        self.b = gate.install_candidate(self.lab, {'run.txt': b'inert version B\n', 'notes.txt': b'b\n'})
        gate.initialize(self.lab, self.a)
        (self.lab/'sentinel.txt').write_bytes(b'sentinel\n')
        (self.lab/'world-state.bin').write_bytes(b'generation=7\n')

    def _reap(self):
        for proc in self.procs:
            if proc.stdin and not proc.stdin.closed:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
            if proc.poll() is None:
                try:
                    proc.wait(2)
                except subprocess.TimeoutExpired:
                    proc.terminate()  # only this original inert helper, never a native game
                    proc.wait(TIMEOUT)
            for pipe in (proc.stdin, proc.stdout):
                if pipe:
                    pipe.close()
        for record in self.owned_pids:
            try:
                _stop_owned_sleeper(record)
                if not select.select([record[0]], [], [], TIMEOUT)[0]:
                    raise TimeoutError('owned inert child did not stop normally')
            finally:
                os.close(record[0])

    def _spawn(self, code, *args):
        with open(PRIVATE/'child-stderr.log', 'a') as log:
            proc = subprocess.Popen([sys.executable, '-I', '-c', PRELUDE+code, str(GATE_DIR), *map(str, args)],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
        self.procs.append(proc)
        return proc

    @staticmethod
    def _release(proc):
        proc.stdin.close()

    def _pointer(self):
        return json.loads((self.lab/gate.POINTER).read_bytes())

    def test_one_guard_inode_blocks_apply_while_world_lease_is_held(self):
        self.assertFalse((self.lab/gate.VERSIONS/self.a/gate.GUARD).exists())
        world = self._spawn(WORLD_HOLD, self.lab)
        current, inode = _line(world).split()
        self.assertEqual(current, self.a)
        self.assertEqual(int(inode), os.stat(self.lab/gate.GUARD).st_ino)
        updater = self._spawn(TRY, self.lab, 'exclusive', 'nowait')
        self.assertEqual(_line(updater), 'waiting')
        self.assertEqual(_line(updater), 'busy')
        self._release(world)
        self.assertEqual(world.wait(TIMEOUT), 0)
        with gate.acquire(self.lab, 'exclusive') as lease:
            gate.activate(lease, self.b, self.a)
        self.assertEqual(self._pointer()['current'], self.b)

    def test_shared_lease_blocks_start_while_apply_holds_exclusive(self):
        with gate.acquire(self.lab, 'exclusive') as apply_lease:
            start = self._spawn(TRY, self.lab, 'shared', 'nowait')
            self.assertEqual(_line(start), 'waiting')
            self.assertEqual(_line(start), 'busy')
            start.wait(TIMEOUT)
            gate.activate(apply_lease, self.b, self.a)
        start = self._spawn(TRY, self.lab, 'shared', 'nowait')
        self.assertEqual(_line(start), 'waiting')
        self.assertEqual(_line(start), f'acquired {self.b}')
        self._release(start)

    def test_start_resolves_new_pointer_only_after_it_gets_the_lease(self):
        with gate.acquire(self.lab, 'exclusive') as apply_lease:
            start = self._spawn(WAIT_START, self.lab)
            self.assertEqual(_line(start), 'blocked')  # actual nonblocking flock attempt was refused
            gate.activate(apply_lease, self.b, self.a)
        self.assertEqual(_line(start), f'acquired {self.b}')
        self._release(start)

    def test_inherited_child_keeps_lease_after_parent_exits_until_it_stops(self):
        nonce = uuid.uuid4().hex
        launcher = self._spawn(LAUNCH, self.lab, SLEEPER, nonce)
        grand = int(_line(launcher))
        record = (os.pidfd_open(grand), grand, nonce)
        self.owned_pids.append(record)
        self.assertEqual(launcher.wait(TIMEOUT), 0)  # parent closed its own descriptor and exited
        with self.assertRaises(gate.Busy):
            gate.acquire(self.lab, 'exclusive')
        self.assertTrue(_stop_owned_sleeper(record))
        waiter = self._spawn(TRY, self.lab, 'exclusive', 'wait')
        self.assertEqual(_line(waiter), 'waiting')
        self.assertEqual(_line(waiter), f'acquired {self.a}')
        self._release(waiter)

    def test_concurrent_marker_retention_preserves_one_identity_and_refuses_the_other(self):
        first = self._spawn(RETAIN_RACE, self.lab, SESSION)
        second = self._spawn(RETAIN_RACE, self.lab, OTHER)
        self.assertEqual(_line(first), 'ready')
        self.assertEqual(_line(second), 'ready')
        for proc in (first, second):
            proc.stdin.write(b'go\n')
            proc.stdin.flush()
        self.assertEqual(sorted([_line(first), _line(second)]), ['MarkerError', 'retained'])
        for proc in (first, second):
            self.assertEqual(proc.wait(TIMEOUT), 0)
        marker = (self.lab/gate.MARKER).read_bytes()
        survivor = json.loads(marker)['session']
        with gate.acquire(self.lab, 'shared') as lease:
            with self.assertRaises(gate.MarkerError):
                gate.release_session(lease, OTHER if survivor == SESSION else SESSION)
            self.assertEqual((self.lab/gate.MARKER).read_bytes(), marker)
        with gate.acquire(self.lab, 'exclusive') as lease:
            with self.assertRaises(gate.MarkerError):
                gate.activate(lease, self.b, self.a)

    def test_fifo_payload_and_symlinked_namespace_are_refused_without_blocking(self):
        before = (self.lab/gate.POINTER).read_bytes()
        candidate = gate.install_candidate(self.lab, {'run.txt': b'original special-file control'})
        directory = self.lab/gate.VERSIONS/candidate
        os.chmod(directory, 0o755)
        (directory/'run.txt').unlink()
        os.mkfifo(directory/'run.txt')  # same manifest-listed name, not an extra-entry shortcut
        result = _run(ACT, self.lab, 'activate', candidate, self.a, '-')
        self.assertEqual(result.stdout.strip(), 'CandidateError')
        versions = self.lab/gate.VERSIONS
        versions.rename(self.lab/'retained-versions')
        os.symlink(self.lab/'retained-versions', versions)
        with self.assertRaises(gate.CandidateError):
            gate.verify_version(self.lab, self.a)
        self.assertEqual((self.lab/gate.POINTER).read_bytes(), before)

    def test_directory_sync_failure_after_replace_requires_rereading_the_pointer(self):
        with gate.acquire(self.lab, 'exclusive') as lease:
            with mock.patch.object(gate, '_fsync_dir', side_effect=OSError('injected directory sync failure')):
                with self.assertRaisesRegex(OSError, 'injected'):
                    gate.activate(lease, self.b, self.a)
        self.assertEqual(self._pointer(), {'format': gate.FORMAT_POINTER, 'current': self.b, 'previous': self.a})
        self.assertEqual((self.lab/'world-state.bin').read_bytes(), b'generation=7\n')

    def test_pointer_cannot_name_the_same_current_and_previous(self):
        value = {'format': gate.FORMAT_POINTER, 'current': self.a, 'previous': self.a}
        (self.lab/gate.POINTER).write_bytes(_canonical(value))
        with gate.acquire(self.lab, 'shared') as lease:
            with self.assertRaises(gate.PointerError):
                lease.current()

    def test_tampered_candidate_is_refused_and_current_and_sentinel_stay_unchanged(self):
        before = (self.lab/gate.POINTER).read_bytes()
        sentinel = (self.lab/'sentinel.txt').read_bytes()
        for index, tamper in enumerate(('payload', 'manifest', 'extra', 'symlink')):
            with self.subTest(tamper=tamper):
                candidate = gate.install_candidate(self.lab, {'run.txt': f'candidate {index}\n'.encode()})
                directory = self.lab/gate.VERSIONS/candidate
                os.chmod(directory, 0o755)
                if tamper == 'payload':
                    target = directory/'run.txt'
                    os.chmod(target, 0o644)
                    target.write_bytes(target.read_bytes().upper())
                elif tamper == 'manifest':
                    target = directory/gate.MANIFEST
                    os.chmod(target, 0o644)
                    target.write_bytes(target.read_bytes().replace(b'run.txt', b'run.tx2'))
                elif tamper == 'extra':
                    (directory/'extra.txt').write_bytes(b'x\n')
                else:
                    os.symlink(self.lab/'sentinel.txt', directory/'link.txt')
                result = _run(ACT, self.lab, 'activate', candidate, self.a, '-')
                self.assertEqual(result.stdout.strip(), 'CandidateError')
                self.assertEqual((self.lab/gate.POINTER).read_bytes(), before)
                self.assertEqual((self.lab/'sentinel.txt').read_bytes(), sentinel)

    def test_malformed_manifests_are_refused_before_any_pointer_change(self):
        before = (self.lab/gate.POINTER).read_bytes()
        entry = {'sha256': '0' * 64, 'size': 1}
        cases = {
            'duplicate key': b'{"files":{},"files":{},"format":"update-activation-manifest-1"}',
            'traversal name': _canonical({'format': gate.FORMAT_MANIFEST, 'files': {'../escape.txt': entry}}),
            'nested name': _canonical({'format': gate.FORMAT_MANIFEST, 'files': {'sub/run.txt': entry}}),
            'boolean size': _canonical({'format': gate.FORMAT_MANIFEST,
                                        'files': {'run.txt': {'sha256': '0' * 64, 'size': True}}}),
            'uppercase digest': _canonical({'format': gate.FORMAT_MANIFEST,
                                            'files': {'run.txt': {'sha256': 'A' * 64, 'size': 1}}}),
            'extra field': _canonical({'format': gate.FORMAT_MANIFEST, 'files': {'run.txt': entry},
                                       'owner': 'x'}),
            'non-canonical spacing': json.dumps({'format': gate.FORMAT_MANIFEST,
                                                 'files': {'run.txt': entry}}, indent=1).encode(),
        }
        for label, data in cases.items():
            with self.subTest(case=label):
                version = hashlib.sha256(data).hexdigest()
                directory = self.lab/gate.VERSIONS/version
                directory.mkdir()
                (directory/gate.MANIFEST).write_bytes(data)
                result = _run(ACT, self.lab, 'activate', version, self.a, '-')
                self.assertEqual(result.stdout.strip(), 'CandidateError')
                self.assertEqual((self.lab/gate.POINTER).read_bytes(), before)

    def test_stale_expected_current_is_refused_for_activate_and_rollback(self):
        self.assertEqual(_run(ACT, self.lab, 'activate', self.b, self.b, '-').stdout.strip(), 'Stale')
        self.assertEqual(_run(ACT, self.lab, 'rollback', '-', self.b, '-').stdout.strip(), 'Stale')
        self.assertEqual(self._pointer(), {'format': gate.FORMAT_POINTER, 'current': self.a, 'previous': None})
        self.assertEqual(_run(ACT, self.lab, 'activate', self.b, self.a, '-').stdout.strip(), f'ok {self.b}')
        self.assertEqual(_run(ACT, self.lab, 'rollback', '-', self.a, '-').stdout.strip(), 'Stale')
        self.assertEqual(_run(ACT, self.lab, 'rollback', '-', self.b, '-').stdout.strip(), f'ok {self.a}')
        self.assertEqual(self._pointer()['current'], self.a)
        self.assertEqual(self._pointer()['previous'], self.b)

    def test_forced_exits_around_pointer_publish_leave_old_or_new_pointer(self):
        crashed = _run(ACT, self.lab, 'activate', self.b, self.a, 'after-temp-fsync')
        self.assertEqual(crashed.returncode, gate.CUT_EXIT)
        self.assertEqual(self._pointer()['current'], self.a)  # temp file written, pointer still old
        with gate.acquire(self.lab, 'exclusive'):  # the dead coordinator's lease is gone
            pass
        crashed = _run(ACT, self.lab, 'activate', self.b, self.a, 'after-replace')
        self.assertEqual(crashed.returncode, gate.CUT_EXIT)
        self.assertEqual(self._pointer(), {'format': gate.FORMAT_POINTER, 'current': self.b, 'previous': self.a})
        self.assertEqual(_run(ACT, self.lab, 'rollback', '-', self.b, '-').stdout.strip(), f'ok {self.a}')

    def test_rollback_keeps_new_world_state_fixture_and_both_version_directories(self):
        self.assertEqual(_run(ACT, self.lab, 'activate', self.b, self.a, '-').stdout.strip(), f'ok {self.b}')
        self.assertEqual(_run(WORLD_WRITE, self.lab, self.b, 'generation=8\n').stdout.strip(), 'wrote')
        world_state = (self.lab/'world-state.bin').read_bytes()
        self.assertEqual(world_state, b'generation=8\n')
        self.assertEqual(_run(ACT, self.lab, 'rollback', '-', self.b, '-').stdout.strip(), f'ok {self.a}')
        self.assertEqual((self.lab/'world-state.bin').read_bytes(), world_state)
        gate.verify_version(self.lab, self.a)
        gate.verify_version(self.lab, self.b)
        self.assertEqual(self._pointer(), {'format': gate.FORMAT_POINTER, 'current': self.a, 'previous': self.b})
        # Rollback takes no data argument, so it cannot accept or restore save bytes.
        self.assertEqual(set(inspect.signature(gate.rollback).parameters), {'lease', 'expected_current', 'cutpoint'})
        # Rollback verifies the previous version again; tampering it refuses the roll back.
        target = self.lab/gate.VERSIONS/self.b/'run.txt'
        os.chmod(target, 0o644)
        target.write_bytes(b'tampered\n')
        self.assertEqual(_run(ACT, self.lab, 'rollback', '-', self.a, '-').stdout.strip(), 'CandidateError')
        self.assertEqual(self._pointer()['current'], self.a)

    def test_unresolved_marker_refuses_after_the_lease_is_released(self):
        self.assertEqual(_run(WORLD_MARK, self.lab, SESSION).stdout.strip(), 'retained')
        self.assertFalse(issubclass(gate.MarkerError, gate.Busy))  # a marker is not lease contention
        with gate.acquire(self.lab, 'exclusive') as lease:  # no live lease remains
            with self.assertRaises(gate.MarkerError):
                gate.activate(lease, self.b, self.a)
            with self.assertRaises(gate.MarkerError):
                gate.rollback(lease, self.a)
        self.assertEqual(self._pointer()['current'], self.a)
        with gate.acquire(self.lab, 'shared') as lease:
            with self.assertRaises(gate.MarkerError):
                gate.release_session(lease, OTHER)
            gate.release_session(lease, SESSION)
        with gate.acquire(self.lab, 'exclusive') as lease:
            gate.activate(lease, self.b, self.a)
        self.assertEqual(self._pointer()['current'], self.b)


if __name__ == '__main__':
    unittest.main()
