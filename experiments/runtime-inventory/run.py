#!/usr/bin/env python3
"""Inventory local runtime artifacts and notices; grants no distribution clearance."""
import argparse
import collections
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import local_dev

MAX_ENTRIES = 100000
MAX_NOTICE = 1 << 20
MAX_ENTRY = 128 << 20
MAX_ARCHIVE = 512 << 20
MAX_HASHED = 256 << 20


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            result.update(block)
    return result.hexdigest()


def notice_candidate(name):
    """Filename heuristic only: never infer a licence from its presence or absence."""
    name = Path(name).name.lower()
    return not name.endswith('.class') and any(
        part in ('license', 'licenses', 'licence', 'licences', 'notice', 'notices', 'copying')
        for part in re.split(r'[^a-z]+', name))


def inspect_archive(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARCHIVE:
        raise ValueError('Expected a bounded ordinary local archive: ' + path.name)
    notices, natives, hashed = [], [], 0
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES:
            raise ValueError('Too many archive entries.')
        files = [entry for entry in entries if not entry.is_dir()]
        counts = collections.Counter(entry.filename for entry in files)
        if any(number != 1 for number in counts.values()):
            raise ValueError('Ambiguous duplicate archive entry names.')
        for entry in files:
            notice = notice_candidate(entry.filename)
            native = entry.filename.lower().endswith(('.so', '.dll', '.dylib', '.jnilib'))
            if not notice and not native:
                continue
            limit = MAX_NOTICE if notice else MAX_ENTRY
            if entry.file_size < 0 or entry.file_size > limit or hashed + entry.file_size > MAX_HASHED:
                raise ValueError('Bounded archive inventory exceeded.')
            checksum = hashlib.sha256()
            actual = 0
            with archive.open(entry) as source:
                for block in iter(lambda: source.read(1 << 20), b''):
                    actual += len(block)
                    if actual > limit or hashed + actual > MAX_HASHED:
                        raise ValueError('Expanded archive entry exceeds inventory limits.')
                    checksum.update(block)
            if actual != entry.file_size:
                raise ValueError('Archive entry size changed.')
            hashed += actual
            row = dict(path=entry.filename, size=actual, sha256=checksum.hexdigest())
            if notice:
                notices.append(row)
            if native:
                natives.append(row)
        return dict(entries=len(files), classes=sum(name.endswith('.class') for name in counts),
                    notice_candidates=notices, embedded_native_libraries=natives)


def artifact_rows(log):
    marker = 'SOLOSCAPE_RUNTIME_ARTIFACTS '
    lines = [line[len(marker):] for line in log.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        raise ValueError('Gradle did not emit one resolved runtime inventory.')
    rows = json.loads(lines[0])
    if not isinstance(rows, list) or not rows or len(rows) > 1000:
        raise ValueError('Invalid resolved runtime inventory.')
    output = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str):
            raise ValueError('Invalid artifact path.')
        path = Path(row['path'])
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError('Missing or unsafe resolved artifact.')
        if path in seen:
            raise ValueError('Duplicate resolved artifact path.')
        seen.add(path)
        if path.suffix.lower() != '.jar':
            raise ValueError('Non-jar runtime artifact needs explicit review.')
        metadata = inspect_archive(path)
        output.append(dict(coordinate=row.get('coordinate'), file=path.name,
                           origin=row.get('origin', 'resolved-module-or-project'),
                           size=path.stat().st_size, sha256=digest(path),
                           **metadata))
    return sorted(output, key=lambda row: (row['coordinate'] or '', row['file']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-java', type=Path, required=True)
    parser.add_argument('--client-java', type=Path, required=True)
    args = parser.parse_args()
    java21 = args.server_java.resolve(strict=True)
    java8 = args.client_java.resolve(strict=True)
    if local_dev.java_version(str(java21)) < 21 or local_dev.java_version(str(java8)) != 8:
        parser.error('Supply the existing Java21 server and Java8 client runtimes.')
    parent = ROOT / '.runtime/runtime-inventory'
    if parent.is_symlink():
        raise ValueError('Inventory output cannot be a link.')
    parent.mkdir(exist_ok=True)
    run = parent / str(time.time_ns())
    run.mkdir(mode=0o700)
    result = dict(passed=False, public_distribution_approved=False,
                  scope='Offline resolved-runtime and archive metadata inventory only; not legal clearance, vulnerability scanning or a complete SBOM.')
    tool = Path(__file__).with_name('artifacts.gradle')
    try:
        with local_dev.build_lock(shared=True):
            jars = dict(server=local_dev.jar(local_dev.SERVER / 'game', 'void-server-*.jar'),
                        client=local_dev.jar(local_dev.CLIENT / 'client', 'void-client-*.jar'))
            local_dev.verify_build_stamp(jars['server'], jars['client'])
            stamp = json.loads((local_dev.RUNTIME / 'build-stamp.json').read_text())
            result.update(pins=stamp['pins'], patches=stamp['patches'], jar_sha256=stamp['jars'],
                          observed_checkout_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                          artifacts={}, matched_jars={})
            for role, repo in (('server', local_dev.SERVER), ('client', local_dev.CLIENT)):
                env = dict(os.environ, JAVA_HOME=str(java21.parent.parent),
                           GRADLE_USER_HOME=str(ROOT / '.gradle'))
                command = ['bash', 'gradlew', '--offline', '--no-daemon', '--no-configuration-cache',
                           '-Dorg.gradle.java.installations.paths=' + str(java21.parent.parent) + ',' + str(java8.parent.parent),
                           '-I', str(tool), ':' + ('game' if role == 'server' else 'client') + ':soloScapeRuntimeInventory']
                completed = subprocess.run(command, cwd=repo, env=env, text=True,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
                (run / (role + '.log')).write_text(completed.stdout)
                if completed.returncode:
                    raise RuntimeError('Offline ' + role + ' dependency resolution failed; private log retained.')
                result['artifacts'][role] = artifact_rows(completed.stdout)
                result['matched_jars'][role] = dict(size=jars[role].stat().st_size, **inspect_archive(jars[role]))
            # Gradle inspection must not replace a matched game build.
            local_dev.verify_build_stamp(jars['server'], jars['client'])
            result['passed'] = True
    except BaseException as exc:
        result['failure'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        result.update(runner_sha256=digest(Path(__file__)), gradle_inventory_sha256=digest(tool))
        (run / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        print('Inventory evidence:', run.relative_to(ROOT) / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
