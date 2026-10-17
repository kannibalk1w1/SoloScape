#!/usr/bin/env python3
"""Two real native clients on one disposable loopback world; no hosting UI or Deck changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import selectors
import signal
import subprocess
import threading
import time
from unittest.mock import patch

import local_dev
import profile_session
import profiles


def tile(value):
    return (isinstance(value, list) and len(value) == 3
            and all(type(n) is int for n in value) and all(0 <= n <= 16383 for n in value[:2])
            and 0 <= value[2] <= 3)


def validate_pair(alpha, beta, observe=False):
    """Independent clients must agree on each other's actual server-updated state."""
    raw = (alpha, beta)
    try:
        alpha, beta = [dict(row, ownName=row['self']['account'], peerName=row['peer']['account'],
                            ownIndex=row['self']['index'], peerIndex=row['peer']['index'],
                            ownTile=row['self']['tile'], peerTile=row['peer']['tile'],
                            initialTile=row['initial_tile'], daggerCount=row['bronze_dagger']) for row in raw]
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing native observation fields.') from exc
    for role, row, peer in (('alpha', alpha, beta), ('beta', beta, alpha)):
        name, other = ('CoopAlpha', 'CoopBeta') if role == 'alpha' else ('CoopBeta', 'CoopAlpha')
        if row.get('ownName') != name or row.get('peerName') != other or row.get('observe') is not observe:
            raise ValueError('Wrong native account or phase.')
        if type(row.get('ownIndex')) is not int or type(row.get('peerIndex')) is not int or row['ownIndex'] == row['peerIndex']:
            raise ValueError('Distinct native player indices required.')
        if not all(0 <= row[key] < 2048 for key in ('ownIndex', 'peerIndex')):
            raise ValueError('Player index outside native client array.')
        if row['ownIndex'] != peer.get('peerIndex') or row['peerIndex'] != peer.get('ownIndex'):
            raise ValueError('Native clients disagree on player indices.')
        if not all(tile(row.get(key)) for key in ('ownTile', 'peerTile', 'initialTile')):
            raise ValueError('Invalid native coordinate evidence.')
        if row['ownTile'] != peer.get('peerTile') or row['ownTile'] == row['peerTile']:
            raise ValueError('Native clients disagree on distinct final positions.')
        expected = 0 if role == 'alpha' else 1
        if type(row.get('daggerCount')) is not int or row['daggerCount'] != expected:
            raise ValueError('Independent native inventory state did not match.')
        if not observe and row['ownTile'] == row['initialTile']:
            raise ValueError('Native movement was not observed.')
        if observe and row['ownTile'] != row['initialTile']:
            raise ValueError('Observer phase moved the character.')
        if row.get('walk_sent') is not (not observe) or row.get('drop_sent') is not (not observe and role == 'alpha'):
            raise ValueError('Native action dispatch evidence does not match the phase.')
    return True


def legacy_fingerprint():
    return {str(path.relative_to(local_dev.SERVER)): hashlib.sha256(path.read_bytes()).hexdigest()
            for name in ('data/saves', 'data/errors', 'data/.temp')
            for path in (local_dev.SERVER / name).rglob('*') if path.is_file()}


def wait_for(paths, thread, errors, guests, timeout=180):
    deadline = time.monotonic() + timeout
    while not all(path.is_file() for path in paths):
        if errors:
            raise RuntimeError('Owned world failed: ' + str(errors[0]))
        if not thread.is_alive() or any(p.poll() is not None for p in guests):
            raise RuntimeError('An owned native process exited before evidence was complete.')
        if time.monotonic() > deadline:
            raise RuntimeError('Two-client native evidence timed out; inspect the disposable logs.')
        time.sleep(0.05)


def phase(profile, directory, harness, guest_auth, port, observe):
    directory.mkdir(mode=0o700)
    guest_home = directory.parent / 'guest-home'
    guest_home.mkdir(exist_ok=True, mode=0o700)
    client_jar = local_dev.jar(local_dev.CLIENT / 'client', 'void-client-*.jar')
    original = subprocess.Popen
    guests, errors, codes, events = [], [], [], []
    cancelled = threading.Event()
    with (directory / 'guest.log').open('w') as guest_log:
        def start(argv, **kwargs):
            if '-jar' not in argv or str(client_jar) not in argv:
                return original(argv, **kwargs)
            i = argv.index('-jar')
            shared = ['-Dsoloscape.coop.observe=' + str(observe).lower(), '-cp',
                      os.pathsep.join((str(client_jar), str(harness))), 'NativeCoopSmoke', str(directory), str(port)]
            primary = original(argv[:i] + shared + ['alpha'], **kwargs)
            try:
                guest_kwargs = dict(kwargs, env=dict(kwargs['env'], SOLOSCAPE_AUTH_FILE=str(guest_auth)),
                                    stdout=guest_log)
                guest_args = [argv[0], '-Duser.home=' + str(guest_home),
                              '-Dsoloscape.cache.root=' + str(guest_home / 'native-cache')]
                guests.append(original(guest_args + shared + ['beta'], **guest_kwargs))
            except BaseException:
                local_dev.stop(primary)
                raise
            return primary

        def run():
            try:
                codes.append(profile_session.run(profile, cancelled, lambda stage, message: events.append(stage), port=port))
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=run, name='disposable-coop-world')
        started = time.monotonic()
        with patch.object(subprocess, 'Popen', side_effect=start):
            thread.start()
            try:
                wait_for([directory / (role + '.ready.json') for role in ('alpha', 'beta')], thread, errors, guests)
                (directory / 'go').touch(exist_ok=False)
                wait_for([directory / (role + '.moved.json') for role in ('alpha', 'beta')], thread, errors, guests)
                (directory / 'check').touch(exist_ok=False)
                paths = [directory / (role + '.result.json') for role in ('alpha', 'beta')]
                wait_for(paths, thread, errors, guests)
                results = [json.loads(path.read_text()) for path in paths]
                validate_pair(*results, observe=observe)
                (directory / 'finish').touch(exist_ok=False)
            finally:
                # Finish the guest and always request normal world closure, including interrupted cleanup.
                (directory / 'finish').touch(exist_ok=True)
                try:
                    for guest in guests:
                        try:
                            guest.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            local_dev.stop(guest)
                finally:
                    cancelled.set()
                    while thread.is_alive():
                        try:
                            thread.join(30)
                        except KeyboardInterrupt:
                            print('Waiting for owned world normal save/closure…', flush=True)
                        if thread.is_alive():
                            print('Waiting for owned world normal save/closure…', flush=True)
        if errors or codes != [0] or len(guests) != 1 or guests[0].returncode != 0:
            raise RuntimeError('Native two-client closure failed; disposable records retained.')
        if (profile.directory / 'session.json').exists() or events[-1:] != ['stopped']:
            raise RuntimeError('World closure was not confirmed.')
        saves = {name: profiles.validate_save((profile.state / 'saves' / (name.lower() + '.toml')).read_bytes(), name)
                 for name in ('CoopAlpha', 'CoopBeta')}
        for name, row in zip(('CoopAlpha', 'CoopBeta'), results):
            saved = saves[name]
            saved_tile = [saved['tile']['x'], saved['tile']['y'], saved['tile'].get('level', 0)]
            count = sum(item.get('amount', 1) for item in saved['inventories']['inventory'] if item.get('id') == 'bronze_dagger')
            if saved_tile != row['self']['tile'] or count != row['bronze_dagger']:
                raise RuntimeError('Native save did not match its own client observation.')
        return {'observe': observe, 'clients': results, 'elapsed_session_seconds': round(time.monotonic() - started, 3),
                'confirmed_clean_closure': True}, saves


def main():
    signal.signal(signal.SIGTERM, local_dev.interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=43596)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged loopback test port.')
    root = local_dev.ROOT
    testroot = root / '.runtime/alpha-tests' / ('coop-' + str(time.time_ns()))
    testroot.mkdir(parents=True, mode=0o700)
    profiles.PROFILES = testroot / 'profiles'
    profile = profiles.create('Disposable two-account world', 'CoopAlpha')
    guest_auth = testroot / 'guest-login.json'
    profiles.atomic_json(guest_auth, {'account': 'CoopBeta', 'password': secrets.token_hex(8)})
    before = legacy_fingerprint()
    client_jar = local_dev.jar(local_dev.CLIENT / 'client', 'void-client-*.jar')
    harness = testroot / 'harness'
    harness.mkdir(mode=0o700)
    read_display, write_display = os.pipe()
    display = subprocess.Popen(['Xvfb', '-displayfd', str(write_display), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                               pass_fds=(write_display,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(write_display)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(read_display, selectors.EVENT_READ)
            if not selector.select(10):
                raise RuntimeError('Owned Xvfb handshake timed out.')
        number = os.read(read_display, 128).decode('ascii').strip()
        if not number.isdigit() or display.poll() is not None:
            raise RuntimeError('Owned Xvfb failed to allocate its display.')
        with local_dev.build_lock(shared=True), patch.dict(os.environ, DISPLAY=':' + number):
            local_dev.verify_build_stamp(local_dev.jar(local_dev.SERVER / 'game', 'void-server-*.jar'), client_jar)
            subprocess.run([str(Path(os.environ['CLIENT_JAVA']).with_name('javac')), '-encoding', 'UTF-8',
                            '-cp', str(client_jar), '-d', str(harness), str(root / 'scripts/harness/NativeCoopSmoke.java')], check=True)
            first, saved = phase(profile, testroot / 'new', harness, guest_auth, args.port, False)
            second, reloaded = phase(profile, testroot / 'continue', harness, guest_auth, args.port, True)
            for name in saved:
                for key in ('tile', 'inventories', 'experience'):
                    if saved[name][key] != reloaded[name][key]:
                        raise RuntimeError('Native restart changed saved ' + key)
        unchanged = before == legacy_fingerprint()
        if not unchanged:
            raise RuntimeError('Legacy mutable storage changed during isolated probe.')
        summary = {'environment': 'Two real native clients, one owned loopback server, private Xvfb. Synthetic destination walking and widget Drop; no physical controller, Deck or hosting UI acceptance.',
                   'phases': [first, second], 'exact_inventory_xp_tile_across_world_restart': True,
                   'legacy_mutable_paths_unchanged': unchanged, 'build': local_dev.build_fingerprint(local_dev.jar(local_dev.SERVER / 'game', 'void-server-*.jar'), client_jar)}
        profiles.atomic_json(testroot / 'summary.json', summary)
        print('Native two-client evidence:', testroot / 'summary.json')
    finally:
        os.close(read_display)
        display.terminate()
        try:
            display.wait(timeout=10)
        except subprocess.TimeoutExpired:
            display.kill()  # Only this probe's Xvfb; all native worlds have already stopped normally.
            display.wait()


if __name__ == '__main__':
    main()
