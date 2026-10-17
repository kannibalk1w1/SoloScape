#!/usr/bin/env python3
"""Private native New/Continue from immutable jar/data payloads; not a release builder."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/native-prebuilt-server'))
import local_dev
import profiles
import profile_session
from runtime_inputs import collect_data

_spec = importlib.util.spec_from_file_location('prebuilt_payload_support', ROOT / 'experiments/native-prebuilt-server/run.py')
_support = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_support)
digest, tree = _support.digest, _support.tree

HARNESS = ('NativeSessionSmoke', 'NativeAdventureProbe', 'NativeTextProbe',
           'NativePlayableLoopProbe', 'NativeSidebarProbe', 'NativePerformanceProbe',
           'NativeMapProbe', 'NativeTabBarProbe', 'NativeArtworkProbe', 'NativeQuitProbe',
           'NativeContentCoverageProbe', 'NativeBloodPactProbe', 'NativePlaytestTwoProbe',
           'NativeFullscreenProbe', 'NativeDeck60Probe', 'NativeDeckRouteProbe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--server-java', type=Path, required=True)
    parser.add_argument('--client-java', type=Path, required=True)
    options = parser.parse_args()
    signal.signal(signal.SIGTERM, local_dev.interrupted)
    server_java = options.server_java.resolve(strict=True)
    client_java = options.client_java.resolve(strict=True)
    if local_dev.java_version(str(server_java)) < 21 or local_dev.java_version(str(client_java)) != 8:
        parser.error('Supply server Java21+ and client Java8.')
    source_cache = options.cache.absolute()
    if source_cache.is_symlink() or not source_cache.is_dir():
        parser.error('Supply a real authorized compatible cache directory.')
    output_base = ROOT / '.runtime/prebuilt-session'
    for directory in (ROOT / '.runtime', output_base):
        if directory.is_symlink():
            parser.error('The private lab root must not be a link.')
        directory.mkdir(exist_ok=True)
    output = output_base / str(time.time_ns())
    output.mkdir(mode=0o700)
    result = {'passed': False, 'scope': 'Private Xvfb/software/no-audio New/Continue only; no graphical launcher, update activation, controller, audio or Deck acceptance.', 'audio_excluded': True}
    display = None
    try:
        with local_dev.build_lock(shared=True):
            server_jar = local_dev.jar(local_dev.SERVER/'game', 'void-server-*.jar')
            client_jar = local_dev.jar(local_dev.CLIENT/'client', 'void-client-*.jar')
            local_dev.verify_build_stamp(server_jar, client_jar)
            for role in ('server', 'client'):
                subprocess.run([sys.executable, str(ROOT/'scripts/verify_patches.py'), role], check=True)
            stamp = json.loads((local_dev.RUNTIME/'build-stamp.json').read_text())
            inputs = collect_data(local_dev.SERVER, sorted((ROOT/'patches/server').glob('*.patch')))
            payload = output/'payload'
            server_root, client_root = payload/'server', payload/'client'
            binaries = {}
            for role, source, folder in (('server', server_jar, server_root/'game/build/libs'),
                                         ('client', client_jar, client_root/'client/build/libs')):
                folder.mkdir(parents=True)
                target = folder/source.name
                shutil.copyfile(source, target)
                if digest(target) != stamp['jars'][role]:
                    raise RuntimeError('Copied jar differs from its matched build: '+role)
                binaries[role] = target
            for item in inputs:
                target = server_root/item['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local_dev.SERVER/item['path'], target)
                if digest(target) != item['sha256'] or target.stat().st_size != item['size']:
                    raise RuntimeError('Data changed during copy: '+item['path'])
            cache_before = tree(source_cache)
            cache = output/'external-cache'
            shutil.copytree(source_cache, cache)
            if tree(cache) != cache_before:
                raise RuntimeError('Private copied cache differs.')
            harness = payload/'instrumentation'
            harness.mkdir()
            subprocess.run([str(client_java.with_name('javac')), '-encoding', 'UTF-8',
                            '-cp', str(binaries['client']), '-d', str(harness)] +
                           [str(ROOT/'scripts/harness'/(name+'.java')) for name in HARNESS], check=True)
            for path in payload.rglob('*'):
                path.chmod(0o555 if path.is_dir() else 0o444)
            payload.chmod(0o555)
            payload_before = tree(payload)
            if any(Path(name).suffix in ('.java', '.kt', '.kts') or
                   Path(name).name in ('.git', 'gradlew', 'gradlew.bat') or
                   '.git' in Path(name).parts for name in payload_before):
                raise RuntimeError('Source/build metadata unexpectedly copied.')
            state = output/'state'
            for name in ('home', 'temp'):
                (state/name).mkdir(parents=True)
            # Audio-device enumeration can block without the host sound-service context.
            # This packaging probe explicitly excludes audio rather than inheriting owner settings.
            (state/'alsa.conf').write_text('')
            base_env = {'ALSA_CONFIG_PATH': str(state/'alsa.conf'), 'PATH': os.defpath, 'HOME': str(state/'home'), 'TMPDIR': str(state/'temp'),
                        'LANG': 'C.UTF-8', 'SERVER_JAVA': str(server_java), 'CLIENT_JAVA': str(client_java),
                        local_dev.CACHE_HOME_ENV: str(cache)}
            original_popen = subprocess.Popen
            read_fd, write_fd = os.pipe()
            try:
                display = original_popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0',
                                          '1280x800x24', '-nolisten', 'tcp'], env=base_env,
                                         pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                os.close(write_fd); write_fd = None
                with selectors.DefaultSelector() as selector:
                    selector.register(read_fd, selectors.EVENT_READ)
                    if not selector.select(10):
                        raise RuntimeError('Private display handshake timed out.')
                    number = os.read(read_fd, 64).decode().strip()
                if not number.isdigit() or display.poll() is not None:
                    raise RuntimeError('Private display failed to allocate.')
                base_env['DISPLAY'] = ':'+number
            finally:
                os.close(read_fd)
                if write_fd is not None:
                    os.close(write_fd)
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            with patch.object(profiles, 'PROFILES', state/'profiles'):
                profile = profiles.create('Prebuilt native fixture', 'BundleProbe')
            native_state = profile.state
            rounds = []
            prior = None
            for iteration in range(2):
                marker = output/('new.marker' if iteration == 0 else 'continue.marker')
                processes = []
                def spawn(argv, **kwargs):
                    if str(binaries['server']) in argv:
                        argv = argv[:1]+['-Djava.io.tmpdir='+str(state/'temp')]+argv[1:]
                    elif str(binaries['client']) in argv:
                        index = argv.index('-jar')
                        argv = argv[:index]+['-Djava.io.tmpdir='+str(state/'temp'),
                                 '-Dsoloscape.probe.environment=Private immutable prebuilt payload; Xvfb/software only',
                                 '-cp', str(binaries['client'])+os.pathsep+str(harness),
                                 'NativeSessionSmoke', str(marker), str(port)]
                    process = original_popen(argv, **kwargs)
                    processes.append({'pid': process.pid, 'cwd': str(Path(kwargs['cwd']).relative_to(payload)),
                                      'role': kwargs.get('env', {}).get('SOLOSCAPE_SESSION_ROLE')})
                    return process
                events = []
                started = time.monotonic()
                with patch.dict(os.environ, base_env, clear=True), \
                     patch.object(local_dev, 'SERVER', server_root), patch.object(local_dev, 'CLIENT', client_root), \
                     patch.object(subprocess, 'Popen', side_effect=spawn):
                    code = profile_session.run(profile, threading.Event(), lambda *args: events.append(args),
                                               port=port, checked=False)
                account = profiles.validate_save((native_state/'saves/bundleprobe.toml').read_bytes())
                fields = {key: account[key] for key in ('accountName', 'experience', 'inventories', 'tile')}
                if code or not marker.is_file() or not events or 'saved and verified' not in events[-1][1]:
                    raise RuntimeError('Native session was not verified; inspect retained logs.')
                if prior is not None and fields != prior:
                    raise RuntimeError('New/Continue changed compared native account fields.')
                prior = fields
                rounds.append({'round': 'new' if iteration == 0 else 'continue',
                               'elapsed_seconds': round(time.monotonic()-started, 3), 'client_exit': code,
                               'native_world_marker': marker.read_text(), 'verified_closure': True,
                               'processes': processes, 'events': events})
                result['rounds'] = rounds
            result.update(payload_unchanged=tree(payload) == payload_before,
                          source_cache_unchanged=tree(source_cache) == cache_before,
                          private_cache_unchanged=tree(cache) == cache_before,
                          compared_account_fields_equal=True, verified_backups=len(list((profile.directory/'backups').glob('*.zip'))),
                          source_data_files=len(inputs), source_data_bytes=sum(x['size'] for x in inputs),
                          cache_file_count=len(cache_before), jars=stamp['jars'], pins=stamp['pins'],
                          client_patch_count=sum('/client/' in key for key in stamp['patches']),
                          server_patch_count=sum('/server/' in key for key in stamp['patches']),
                          instrumentation_sources={name: digest(ROOT/'scripts/harness'/(name+'.java')) for name in HARNESS},
                          payload_tree_sha256=_support.tree_digest(payload_before))
            if not all(result[key] for key in ('payload_unchanged','source_cache_unchanged','private_cache_unchanged')):
                raise RuntimeError('An immutable payload/input inventory changed.')
            result['passed'] = True
    except BaseException as exc:
        result['failure'] = type(exc).__name__+': '+str(exc)
        raise
    finally:
        if display is not None and display.poll() is None:
            display.terminate()
            try:
                display.wait(timeout=5)
            except subprocess.TimeoutExpired:
                display.kill(); display.wait(timeout=5)  # Only the private display, never a game/save process.
        result['runner_sha256'] = digest(Path(__file__))
        (output/'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
        print('Evidence:', output.relative_to(ROOT)/'summary.json', flush=True)


if __name__ == '__main__':
    main()
