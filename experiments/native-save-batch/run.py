#!/usr/bin/env python3
"""Diagnose native account-batch writes with original disposable fixtures only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('StorageBatchProbe.java')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-jar', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--java', required=True, type=Path)
    parser.add_argument('--javac', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256):
        parser.error('Expected a lowercase SHA-256 for the trusted locally built server jar.')
    jar = args.server_jar.resolve(strict=True)
    if not jar.is_file() or sha(jar) != args.sha256:
        parser.error('Server jar does not match its expected digest.')
    runtime = ROOT / '.runtime'
    lab = runtime / 'native-save-batch'
    if runtime.is_symlink() or lab.is_symlink():
        parser.error('Refuse a symlinked experiment lab.')
    lab.mkdir(parents=True, exist_ok=True)
    out = lab / str(time.time_ns())
    out.mkdir()
    classes = out / 'classes'
    classes.mkdir()
    with (out / 'compile.log').open('w') as log:
        subprocess.run([str(args.javac.resolve(strict=True)), '-cp', str(jar), '-d', str(classes), str(SOURCE)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    started = time.monotonic()
    with (out / 'native.log').open('w') as log:
        subprocess.run([str(args.java.resolve(strict=True)), '-cp', str(classes) + ':' + str(jar),
                        'StorageBatchProbe', str(out / 'state')], stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=60)
    if sha(jar) != args.sha256:
        raise RuntimeError('Server jar changed during the probe; evidence is invalid.')
    result = json.loads((out / 'state/result.json').read_text())
    result.update(server_jar_sha256=args.sha256, source_sha256=sha(SOURCE), runner_sha256=sha(Path(__file__)),
                  native_process_elapsed_seconds=round(time.monotonic() - started, 3))
    (out / 'summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'evidence': str(out.relative_to(ROOT) / 'summary.json'),
                      'observed_partial_commit': result['observed_partial_commit']}, indent=2))


if __name__ == '__main__':
    main()
