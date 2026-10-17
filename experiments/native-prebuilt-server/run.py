#!/usr/bin/env python3
"""Boot an owned empty world from a private prebuilt payload; never publish it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import local_dev
from runtime_inputs import collect_data


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            result.update(chunk)
    return result.hexdigest()


def tree(root):
    """Inventory only this explicitly selected input/payload tree, never legacy saves."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Expected a real input directory.')
    result = {}
    for path in sorted(root.rglob('*')):
        mode = path.lstat().st_mode
        name = path.relative_to(root).as_posix()
        if stat.S_ISDIR(mode):
            result[name] = {'directory': True, 'mode': stat.S_IMODE(mode)}
        elif stat.S_ISREG(mode):
            result[name] = {'size': path.stat().st_size, 'sha256': digest(path),
                            'mode': stat.S_IMODE(mode)}
        else:
            raise ValueError('Links/special files are not supported in experiment inputs: ' + name)
    return result


def tree_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def resident_kib(process):
    try:
        text = Path(f'/proc/{process.pid}/status').read_text()
        found = re.search(r'^VmHWM:\s+(\d+) kB$', text, re.MULTILINE)
        return int(found.group(1)) if found else None
    except OSError:
        return None


def interrupt(signum, frame):
    raise InterruptedError('Experiment interrupted; closing only its owned fixture process.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True,
                        help='Authorized compatible input cache; a private copy is used by the JVM.')
    parser.add_argument('--java', type=Path, required=True)
    options = parser.parse_args()
    java = options.java.resolve(strict=True)
    if local_dev.java_version(str(java)) < 21:
        parser.error('The prebuilt server requires Java21 or newer.')
    source_cache = options.cache.absolute()
    if source_cache.is_symlink() or not source_cache.is_dir():
        parser.error('Supply a real compatible cache directory.')
    for name in ('main_file_cache.dat2', 'main_file_cache.idx255'):
        if not (source_cache / name).is_file() or (source_cache / name).stat().st_size == 0:
            parser.error('Missing/empty compatible cache input: ' + name)
    for directory in (ROOT / '.runtime', ROOT / '.runtime/prebuilt-server'):
        if directory.is_symlink():
            parser.error('The experiment lab must not be a link.')
        directory.mkdir(exist_ok=True)
    output = ROOT / '.runtime/prebuilt-server' / str(time.time_ns())
    output.mkdir(mode=0o700)
    signal.signal(signal.SIGTERM, interrupt)
    result = {'scope': 'Private empty-world server boot only. No public package, launcher, client, character or Deck acceptance.',
              'run': str(output.relative_to(ROOT)), 'passed': False}
    process = None
    try:
        with local_dev.build_lock(shared=True):
            server = local_dev.jar(local_dev.SERVER / 'game', 'void-server-*.jar')
            client = local_dev.jar(local_dev.CLIENT / 'client', 'void-client-*.jar')
            local_dev.verify_build_stamp(server, client)
            subprocess.run([sys.executable, str(ROOT / 'scripts/verify_patches.py'), 'server'], check=True)
            stamp = json.loads((local_dev.RUNTIME / 'build-stamp.json').read_text())
            sources = collect_data(local_dev.SERVER, sorted((ROOT / 'patches/server').glob('*.patch')))
            payload = output / 'payload'
            payload.mkdir()
            shutil.copyfile(server, payload / 'server.jar')
            if digest(payload / 'server.jar') != stamp['jars']['server']:
                raise RuntimeError('Copied server jar does not match the verified build.')
            for item in sources:
                target = payload / item['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local_dev.SERVER / item['path'], target)
                if target.stat().st_size != item['size'] or digest(target) != item['sha256']:
                    raise RuntimeError('Runtime data changed while copying: ' + item['path'])
            (output / 'source-data.json').write_text(json.dumps(sources, indent=2) + '\n')
            source_cache_before = tree(source_cache)
            cache = output / 'external-cache'
            shutil.copytree(source_cache, cache)
            if tree(cache) != source_cache_before:
                raise RuntimeError('The private cache copy does not match its input.')
            for path in payload.rglob('*'):
                path.chmod(0o555 if path.is_dir() else 0o444)
            payload.chmod(0o555)
            payload_before = tree(payload)
            if any('.git' in Path(name).parts or '.gradle' in Path(name).parts
                   or Path(name).suffix in ('.kt', '.kts', '.java')
                   or Path(name).name in ('gradlew', 'gradlew.bat') for name in payload_before):
                raise RuntimeError('The payload unexpectedly contains source/build metadata.')
            with zipfile.ZipFile(payload / 'server.jar') as archive:
                manifest = archive.read('META-INF/MANIFEST.MF').decode('utf-8')
                if re.search(r'^Class-Path:', manifest, re.MULTILINE | re.IGNORECASE):
                    raise RuntimeError('External jar classpath needs a separate verified payload contract.')
            result.update(source_data_files=len(sources), source_data_bytes=sum(x['size'] for x in sources),
                          source_data_manifest_sha256=digest(output / 'source-data.json'),
                          server_jar_sha256=stamp['jars']['server'], pins=stamp['pins'],
                          selector_sha256=digest(Path(__file__).with_name('runtime_inputs.py')),
                          cache_tree_sha256=tree_digest(source_cache_before))
            state = output / 'state'
            for name in ('saves', 'errors', 'logs', 'temp', 'home', 'jvm-temp'):
                (state / name).mkdir(parents=True)
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            session = uuid.uuid4().hex
            env = {'PATH': os.defpath, 'HOME': str(state / 'home'),
                   'JAVA_HOME': str(java.parent.parent), 'TMPDIR': str(state / 'jvm-temp'),
                   'LANG': 'C.UTF-8', 'network.bind': '127.0.0.1', 'network.port': str(port),
                   'server.name': 'SoloScapeClosure', 'storage.type': 'files',
                   'storage.data': str(payload / 'data') + '/',
                   'storage.cache.path': str(cache) + '/',
                   'storage.players.path': str(state / 'saves') + '/',
                   'storage.players.errors': str(state / 'errors') + '/',
                   'storage.players.logs': str(state / 'logs') + '/',
                   'storage.data.modified': str(state / 'temp/modified.dat'),
                   'storage.wildcards': str(state / 'temp/wildcards.txt'),
                   'storage.caching.path': str(state / 'temp') + '/',
                   'web.server.enabled': 'false', 'bots.count': '0',
                   'development.accountCreation': 'false', 'development.admin.name': '',
                   'SOLOSCAPE_SESSION_ID': session}
            log = output / 'server.log'
            started = time.monotonic()
            with log.open('w') as stream:
                process = subprocess.Popen([str(java), '-Djava.awt.headless=true',
                                            '-Djava.io.tmpdir=' + str(state / 'jvm-temp'),
                                            '-jar', str(payload / 'server.jar')], cwd=payload,
                                           env=env, stdin=subprocess.DEVNULL, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                result.update(pid=process.pid, port=port)
                deadline = time.monotonic() + 180
                while True:
                    text = log.read_text(errors='replace')
                    if process.poll() is not None:
                        raise RuntimeError('Prebuilt world exited before readiness; inspect its private log.')
                    if re.search(r'SoloScapeClosure loaded in \d+ms', text):
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError('Prebuilt world startup timed out; evidence retained.')
                    time.sleep(0.1)
                result.update(startup_seconds=round(time.monotonic() - started, 3),
                              host_peak_resident_kib=resident_kib(process), ready=True)
                stopping = time.monotonic()
                process.terminate()
                process.wait(timeout=90)
                result.update(shutdown_seconds=round(time.monotonic() - stopping, 3),
                              exit_code=process.returncode)
            text = log.read_text(errors='replace')
            plain = re.sub(r'\x1b\[[0-9;]*m', '', text)
            confirmed = f'SOLOSCAPE_WORLD_SAVED_V1 {session}' in plain.splitlines()
            if process.returncode not in (0, 143, -signal.SIGTERM) or not confirmed:
                raise RuntimeError('Prebuilt world did not confirm normal primary-save closure.')
            if any(marker in text for marker in ('Primary world save was not confirmed',
                                                  'Fallback save failed!', 'Error saving ')):
                raise RuntimeError('The native world logged an unconfirmed account write.')
            if tree(payload) != payload_before:
                raise RuntimeError('The immutable payload changed during the native run.')
            if tree(source_cache) != source_cache_before:
                raise RuntimeError('The source cache changed; experiment evidence is invalid.')
            # Native FileStorage accounts are top-level TOML; exchange files are nested.
            if any((state / 'saves').glob('*.toml')):
                raise RuntimeError('The empty-world probe unexpectedly created an account.')
            result.update(passed=True, primary_closure_confirmed=True,
                          immutable_payload_unchanged=True, source_cache_unchanged=True,
                          private_cache_unchanged=tree(cache) == source_cache_before,
                          payload_contains_source_or_git=False,
                          source_data_files=len(sources), source_data_bytes=sum(x['size'] for x in sources),
                          source_data_manifest_sha256=digest(output / 'source-data.json'),
                          cache_file_count=sum('sha256' in x for x in source_cache_before.values()),
                          cache_bytes=sum(x.get('size', 0) for x in source_cache_before.values()),
                          cache_tree_sha256=tree_digest(source_cache_before),
                          cache_revision_declared=634, cache_revision_detected=False,
                          pins=stamp['pins'], server_jar_sha256=stamp['jars']['server'],
                          server_patches_sha256={p: v for p, v in stamp['patches'].items() if p.startswith('patches/server/')})
    except BaseException as failure:
        result['failure'] = type(failure).__name__ + ': ' + str(failure)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                result['forced_fixture_stop'] = True
                process.kill()
                process.wait(timeout=10)
        result['runner_sha256'] = digest(Path(__file__))
        (output / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print('Evidence:', output.relative_to(ROOT) / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
