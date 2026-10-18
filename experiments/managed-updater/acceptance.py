#!/usr/bin/env python3
"""PRIVATE native acceptance of the managed updater on disposable state. Never run against an owner install.

Builds two real-sized private packages from a deck-export snapshot (read only), installs the first into a fresh
install root, then drives the real graphical launcher with mapped controller input on an owned Xvfb display:
play a world, check, cancel a download, download, Install and Restart, Continue in the new version, refuse a
save-incompatible candidate, roll back and Continue again. GitHub is replaced only at the backend's two network
seams by fake_github.py; production code has no override. Evidence goes to <run>/acceptance.json.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))
import death_loot_state  # noqa: E402
import managed_install as mi  # noqa: E402
import package_builder  # noqa: E402
import profiles  # noqa: E402
import update_package  # noqa: E402
import build_packages  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def logical_account(profile_dir, account='bundleprobe'):
    """The logical post-replay account, validated the way the launcher validates it (journal overrides canonical)."""
    profile = profiles.Profile(profile_dir)
    contents = {p.relative_to(profile.state).as_posix(): p.read_bytes() for p in profile._files()}
    logical = death_loot_state.validate_state(contents, profiles.validate_save, 'BundleProbe')
    return logical['accounts'][account]


def fields(account):
    return {key: account[key] for key in ('accountName', 'experience', 'inventories', 'tile')} | {
        'storage_version': account.get('storage_version', 0)}


def wait_for(path, seconds, process=None, label=''):
    end = time.monotonic() + seconds
    while not path.exists():
        if process is not None and process.poll() is not None and not path.exists():
            raise RuntimeError('process ended before ' + (label or path.name))
        if time.monotonic() > end:
            raise RuntimeError('timed out waiting for ' + (label or path.name))
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True, help='authorized cache to copy (read only)')
    parser.add_argument('--client-jar', type=Path, default=ROOT / 'upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar')
    parser.add_argument('--server-java', type=Path, required=True)
    parser.add_argument('--client-java', type=Path, required=True)
    options = parser.parse_args()
    snapshot, cache_source = options.snapshot.resolve(strict=True), options.cache.resolve(strict=True)
    run = ROOT / '.runtime/managed-acceptance' / str(time.time_ns())
    for name in ('packages', 'profiles', 'launcher', 'probe', 'temp', 'home', 'shim', 'classes'):
        (run / name).mkdir(parents=True, mode=0o700)
    (run / 'alsa.conf').write_text('')
    result = {'passed': False, 'checks': {}, 'scope': 'Private disposable native acceptance with mapped AWT Robot input on '
              'owned Xvfb; fake GitHub at the backend network seams; no SDL, hardware, audio or owner install.'}
    checks = result['checks']
    support = load(ROOT / 'experiments/native-prebuilt-server/run.py', 'acceptance_support')
    display = bootstrap = None
    try:
        # ---- packages and install root ----------------------------------------------------------------------
        files = build_packages.collect(snapshot, options.client_jar)
        patches = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'patches').glob('*/*.patch'))}
        import local_dev
        packages = {}
        for label in ('a', 'b'):
            release = 'private-test-' + label
            manifest = package_builder.build_manifest(files, release, (0, 1), '0' * 40, dict(local_dev.PINNED), patches)
            path = run / 'packages' / ('soloscape-package-' + release + '.zip')
            packages[release] = {'path': path, 'sha256': package_builder.write_zip(files, manifest, path), 'size': path.stat().st_size}
        shutil.copytree(cache_source, run / 'cache')
        cache_before = support.tree(run / 'cache')
        root = run / 'install'
        a = mi.install_first(root, packages['private-test-a']['path'], packages['private-test-a']['sha256'], run / 'profiles',
                             run / 'cache', run / 'launcher', release='private-test-a')
        result['package_bytes'] = {k: v['size'] for k, v in packages.items()}
        result['version_a'] = a
        checks['install_a_sealed'] = mi.read_pointer(root) == {'current': a, 'previous': None}
        fake = run / 'fake.json'
        b_package = packages['private-test-b']
        fake.write_text(json.dumps({'mode': 'serve', 'tag': 'private-test-b', 'name': 'soloscape-package-private-test-b.zip',
                                    'size': b_package['size'], 'sha256': b_package['sha256'], 'path': str(b_package['path']),
                                    'rate': 6 << 20}))
        # ---- wrappers ------------------------------------------------------------------------------------------------
        sessions = load(ROOT / 'experiments/native-prebuilt-session/run.py', 'acceptance_sessions')
        harness = run / 'harness'
        harness.mkdir()
        client_jar = root / 'versions' / a / 'upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar'
        javac = options.client_java.with_name('javac')
        subprocess.run([str(javac), '-encoding', 'UTF-8', '-cp', str(client_jar), '-d', str(harness),
                        str(ROOT / 'scripts/harness/NativeManagedUpdateProbe.java')] +
                       [str(ROOT / 'scripts/harness' / (name + '.java')) for name in sessions.HARNESS], check=True)
        shim = run / 'shim/python3'
        shim.write_text('#!/bin/sh\ncase "$1" in\n  */launcher_backend.py) exec %s -B %s "$@";;\n  *) exec %s "$@";;\nesac\n'
                        % (sys.executable, HERE / 'fake_github.py', sys.executable))
        shim.chmod(0o700)
        wrappers = {}
        for role, java in (('server', options.server_java), ('client', options.client_java)):
            wrapper = run / (role + '-java')
            code = '''import os,sys
from pathlib import Path
java=JAVA
args=['-Djava.io.tmpdir='+TEMP]+sys.argv[1:]
LAUNCHER='net.runelite.client.soloscape.launcher.SoloScapeLauncher'
if ROLE=='client' and '-jar' in args:
 i=args.index('-jar'); jar=args[i+1]
 count_file=Path(COUNTER)
 count=int(count_file.read_text())+1 if count_file.exists() else 1
 count_file.write_text(str(count))
 port=args[args.index('--port')+1]
 args=args[:i]+['-cp',jar+os.pathsep+HARNESS,'NativeSessionSmoke',MARKER+str(count),port]
elif ROLE=='client' and LAUNCHER in args:
 i=args.index(LAUNCHER); cp=args[args.index('-cp')+1]
 args=['-Dsoloscape.launcher.steamKeyboard=true','-cp',cp+os.pathsep+HARNESS,'net.runelite.client.soloscape.launcher.NativeManagedUpdateProbe',args[i+1],PROBE]
os.execv(java,[java]+args)
'''
            for name, value in {'JAVA': str(java), 'TEMP': str(run / 'temp'), 'ROLE': role, 'COUNTER': str(run / 'client-launches'),
                                'HARNESS': str(harness), 'MARKER': str(run / 'native-'), 'PROBE': str(run / 'probe')}.items():
                code = code.replace(name, repr(value))
            wrapper.write_text('#!' + sys.executable + '\n' + code)
            wrapper.chmod(0o700)
            wrappers[role] = wrapper
        env = {'PATH': str(run / 'shim') + ':/usr/bin:/bin', 'HOME': str(run / 'home'), 'TMPDIR': str(run / 'temp'), 'LANG': 'C.UTF-8',
               'PYTHONDONTWRITEBYTECODE': '1', 'ALSA_CONFIG_PATH': str(run / 'alsa.conf'), 'SERVER_JAVA': str(wrappers['server']),
               'CLIENT_JAVA': str(wrappers['client']), 'SOLOSCAPE_FAKE_GITHUB': str(fake)}
        read_fd, write_fd = os.pipe()
        display = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'], env=env,
                                   pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.close(write_fd)
        with selectors.DefaultSelector() as selector:
            selector.register(read_fd, selectors.EVENT_READ)
            if not selector.select(10):
                raise RuntimeError('Private Xvfb handshake timed out.')
            env['DISPLAY'] = ':' + os.read(read_fd, 64).decode().strip()
        os.close(read_fd)
        # ---- fixture character via the real backend --------------------------------------------------------------
        import socket
        with socket.socket() as probe_port:
            probe_port.bind(('127.0.0.1', 0))
            port = probe_port.getsockname()[1]
        backend_env = mi.child_environment(root, mi.load_config(root), env)
        requests = [dict(id=1, action='settings', save=True, port=port), dict(id=2, action='create', label='Managed updater fixture', account='BundleProbe')]
        setup = subprocess.run([sys.executable, '-B', str(root / 'versions' / a / 'scripts/launcher_backend.py')],
                               input=''.join(json.dumps(r) + '\n' for r in requests), env=backend_env, cwd=root / 'versions' / a,
                               text=True, capture_output=True, timeout=120)
        replies = [json.loads(line) for line in setup.stdout.splitlines()]
        if setup.returncode or len(replies) != 2 or not all(r.get('ok') for r in replies):
            raise RuntimeError('Fixture setup failed: ' + setup.stdout[:600] + setup.stderr[-600:])
        profile_dir = run / 'profiles' / replies[1]['result']['id']
        # ---- launch 1 and 2 via the real bootstrap ---------------------------------------------------------------------
        probe = run / 'probe'
        log = (run / 'bootstrap.log').open('w')
        bootstrap = subprocess.Popen([sys.executable, '-B', str(root / 'bootstrap/managed_install.py'), 'run', str(root)], env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        wait_for(probe / 'round0.json', 400, bootstrap, 'round 0')
        sessions_seen = {'round0': json.loads((probe / 'round0.json').read_text())}
        before_update = fields(logical_account(profile_dir))
        checks['round0_account_valid_storage_version'] = before_update['storage_version']
        marker = run / 'native-1'
        checks['round0_native_capabilities_verified'] = marker.is_file() and 'serverCapabilities=verified' in marker.read_text()
        (probe / 'round0.ack').write_text('verified\n')
        wait_for(probe / 'cancelled.flag', 300, bootstrap, 'cancel step')
        leftover = [n for n in os.listdir(root / 'staging') if n not in (update_package.LOCK,)]
        checks['cancel_left_no_partial_or_version'] = not leftover and os.listdir(root / 'versions') == [a]
        # While the launcher holds its lease, activation must be refused.
        wait_for(root / mi.CANDIDATE, 240, bootstrap, 'staged candidate')
        candidate = mi.read_candidate(root)
        try:
            mi.activate(root, candidate['id'])
            checks['activation_refused_while_launcher_runs'] = False
        except mi.Busy:
            checks['activation_refused_while_launcher_runs'] = True
            result['launcher_alive_at_refusal'] = bootstrap.poll() is None
        result['candidate'] = candidate
        wait_for(probe / 'round1.json', 600, bootstrap, 'round 1 (Continue after update)')
        pointer = mi.read_pointer(root)
        checks['pointer_after_update'] = pointer == {'current': candidate['id'], 'previous': a}
        after_update = fields(logical_account(profile_dir))
        checks['continue_after_update_fields_equal'] = after_update == before_update
        checks['native_second_session_capabilities_verified'] = 'serverCapabilities=verified' in (run / 'native-2').read_text()
        (probe / 'round1.ack').write_text('verified\n')
        code = bootstrap.wait(timeout=240)
        checks['bootstrap_exit_clean'] = code == 0 and (probe / 'passed2').exists()
        # The launcher showed the apply result to the player once (the probe asserted its text) and then cleared it.
        checks['result_shown_once_then_cleared'] = mi.read_result(root) is None
        # ---- save-format refusal and rollback ---------------------------------------------------------------------------
        old_only = dict(files)
        manifest_c = package_builder.build_manifest(old_only, 'private-test-c', (0,), '0' * 40, dict(local_dev.PINNED), patches)
        c_zip = run / 'packages/soloscape-package-private-test-c.zip'
        c_digest = package_builder.write_zip(old_only, manifest_c, c_zip)
        c_id = update_package.install_zip(root, c_zip, c_digest, expected_release='private-test-c')['id']
        try:
            mi.activate(root, c_id)
            checks['incompatible_save_format_refused'] = False
        except mi.InstallError as exc:
            checks['incompatible_save_format_refused'] = 'cannot read' in str(exc) and mi.read_pointer(root)['current'] == candidate['id']
            result['incompatible_message'] = str(exc)
        checks['saves_untouched_by_refusal'] = fields(logical_account(profile_dir)) == before_update
        rolled = mi.rollback(root)
        checks['rollback_pointer_only'] = rolled == a and mi.read_pointer(root) == {'current': a, 'previous': candidate['id']}
        checks['rollback_kept_saves'] = fields(logical_account(profile_dir)) == before_update
        bootstrap = subprocess.Popen([sys.executable, '-B', str(root / 'bootstrap/managed_install.py'), 'run', str(root)], env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        wait_for(probe / 'round2.json', 400, bootstrap, 'round 2 (Continue after rollback)')
        checks['continue_after_rollback_fields_equal'] = fields(logical_account(profile_dir)) == before_update
        (probe / 'round2.ack').write_text('verified\n')
        checks['rollback_launch_clean'] = bootstrap.wait(timeout=240) == 0 and (probe / 'passed3').exists()
        # ---- inventories -----------------------------------------------------------------------------------------------------
        with profiles_home(run / 'profiles'):
            backups = profiles.list_backups(profile_dir.name)
        checks['backups_all_valid'] = bool(backups) and all(row['valid'] for row in backups)
        result['backup_count'] = len(backups)
        checks['cache_unchanged'] = support.tree(run / 'cache') == cache_before
        for version in (a, candidate['id']):
            mi.verify_version(root, version)
        checks['both_versions_verify'] = True
        checks['two_version_contexts'] = len(list((run / 'launcher/version-contexts').iterdir())) == 2
        checks['no_staging_leftovers'] = [n for n in os.listdir(root / 'staging') if n != update_package.LOCK] == []
        result['probe_log'] = (probe / 'probe.log').read_text().splitlines()
        result['passed'] = all(v is True or (isinstance(v, int) and not isinstance(v, bool)) for v in checks.values())
        result['failed_checks'] = [k for k, v in checks.items() if v is False]
        result['passed'] = not result['failed_checks']
    except BaseException as exc:
        result['failure'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        if bootstrap is not None and bootstrap.poll() is None:
            os.killpg(bootstrap.pid, signal.SIGTERM)  # graceful: backend EOF/SIGTERM runs normal save hooks
            try:
                bootstrap.wait(timeout=180)
            except subprocess.TimeoutExpired:
                result['shutdown_unverified'] = True
        if display is not None and not result.get('shutdown_unverified'):
            display.terminate()
            try:
                display.wait(timeout=5)
            except subprocess.TimeoutExpired:
                display.kill()
                display.wait(timeout=5)
        (run / 'acceptance.json').write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
        print('Evidence:', (run / 'acceptance.json').relative_to(ROOT), 'passed=' + str(result['passed']), flush=True)


class profiles_home:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.old = profiles.PROFILES
        profiles.PROFILES = self.path

    def __exit__(self, *exc):
        profiles.PROFILES = self.old


if __name__ == '__main__':
    main()
