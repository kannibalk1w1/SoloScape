#!/usr/bin/env python3
"""Record exact local tooling and source identities after a successful decode proof."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(command):
    return subprocess.check_output(command, stderr=subprocess.STDOUT, text=True).strip()


def main():
    build = HERE / 'build'
    evidence = json.loads((build / 'evidence.json').read_text())
    if evidence['failures'] or evidence['mutation']:
        raise RuntimeError('Only a successful unmodified proof can record provenance.')
    fingerprints = {}
    for path in sorted(HERE.rglob('*')):
        relative = path.relative_to(HERE)
        if any(part in ('build', '.gradle', '__pycache__') for part in relative.parts):
            continue
        if path.is_file() and (path.suffix in ('.java', '.py', '.sh', '.gradle', '.html', '.md') or path.name == '.gitignore'):
            fingerprints[relative.as_posix()] = sha(path)
    artifacts = {}
    for name in ('decode.wasm', 'decode.wasm-runtime.js'):
        data = (build / 'teavm-out' / name).read_bytes()
        compressed = gzip.compress(data, compresslevel=9, mtime=0)
        artifacts[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                               gzip_bytes=len(compressed), gzip_sha256=hashlib.sha256(compressed).hexdigest())
    reused = HERE.parent / 'wasm-face/tools'
    report = dict(
        inputs=json.loads((build / 'inputs.json').read_text()),
        closure=json.loads((build / 'closure.json').read_text()),
        experimentSourceSha256=fingerprints,
        reusedToolsSha256={name: sha(reused / name) for name in ('browser_probe.mjs', 'serve_loopback.py')},
        toolchain=dict(java=version([str(Path(os.environ['JAVA_HOME']) / 'bin/java'), '-version']),
                       node=version([os.environ.get('NODE', 'node'), '--version']),
                       chromium=version([os.environ.get('CHROMIUM', '/usr/bin/chromium'), '--version']),
                       teavm='0.16.0 (offline pinned Gradle plugin/dependency)'),
        artifacts=artifacts,
        gzip_format='gzip level9, mtime0, no filename header; size is not a full client estimate',
        fixture_bytes={row['name']: row['bytes'] for row in json.loads((build / 'fixtures.json').read_text())},
        evidence_sha256=sha(build / 'evidence.json'))
    (build / 'provenance.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
