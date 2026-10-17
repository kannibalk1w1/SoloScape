#!/usr/bin/env python3
"""Run an original definition through actual native codecs without opening a cache."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from backport_catalogue import ROOT, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-jar', type=Path, required=True)
    parser.add_argument('--cache-jar', type=Path, required=True)
    parser.add_argument('--client-jar', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    args = parser.parse_args()
    jars = {'cache': args.cache_jar, 'server': args.server_jar, 'client': args.client_jar}
    if any(p.is_symlink() or not p.is_file() for p in jars.values()):
        raise ValueError('Supply regular locally built native jars.')
    lab = ROOT / '.runtime/backport-lab'
    lab.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'backport/tooling/OriginalItemCodec.java'
    before = {name: digest(path) for name, path in jars.items()}
    tool_hash = digest(source)
    wrapper_hash = digest(Path(__file__))
    with tempfile.TemporaryDirectory(prefix='item-codec-', dir=lab) as temporary:
        build = Path(temporary)
        frozen = []
        for name, path in jars.items():
            copy = build / (name + '.jar')
            shutil.copyfile(path, copy)
            if digest(copy) != before[name]:
                raise ValueError('An input jar changed while copying.')
            frozen.append(str(copy))
        classpath = os.pathsep.join(frozen)
        subprocess.run([str(args.java_home / 'bin/javac'), '-cp', classpath, '-d', str(build), str(source)], check=True)
        run = subprocess.run([str(args.java_home / 'bin/java'), '-Djava.awt.headless=true', '-cp',
                              str(build) + os.pathsep + classpath, 'OriginalItemCodec'], check=True, capture_output=True, text=True)
        result = json.loads(run.stdout)
    if ({name: digest(path) for name, path in jars.items()} != before or digest(source) != tool_hash
            or digest(Path(__file__)) != wrapper_hash):
        raise ValueError('An input/tool changed during the probe; report withheld.')
    result['inputs_sha256'] = before
    result['tools_sha256'] = {'OriginalItemCodec.java': tool_hash, 'backport_item_codec.py': wrapper_hash}
    result['limits'] = ['Original name/cost/stackability/scale subset and numeric note-reference boundaries only.',
                        'No cache opened or changed, target ID allocated, asset decoded or game item enabled.',
                        'Three high-reference mismatches are expected evidence, not successful conversions.',
                        'Raw opcode decode only; no cache definition-link normalization, model render or inventory packet test.']
    output = lab / ('item-codec-report-' + str(time.time_ns()) + '.json')
    with output.open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(output)


if __name__ == '__main__':
    main()
