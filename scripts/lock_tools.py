#!/usr/bin/env python3
"""Pin the Python + git + 7-Zip environment the installer brings to a computer that lacks them (stock SteamOS).

    python3 scripts/lock_tools.py /path/to/micromamba

Solves the environment on conda-forge once, records every package's URL, SHA-256 and size, and the micromamba program's
own hash in scripts/installer_inputs.json. The installer then downloads exactly those files and verifies each hash
before anything is installed; nothing is solved or resolved on the player's computer.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECS = ['python=3.12', 'git', '7zip']
MICROMAMBA_URL = 'https://github.com/mamba-org/micromamba-releases/releases/download/2.9.0-0/micromamba-linux-64'


def main(argv=None):
    binary = (argv or sys.argv)[1]
    root = tempfile.mkdtemp(prefix='lock-')
    env = dict(os.environ, MAMBA_ROOT_PREFIX=root)
    out = subprocess.run([binary, 'create', '-p', root + '/env', '-c', 'conda-forge', '--override-channels', '--dry-run', '--json',
                          '--no-rc'] + SPECS, capture_output=True, text=True, env=env, check=True).stdout
    actions = json.loads(out[out.index('{'):])['actions']['FETCH']
    packages = [{'name': a['name'], 'version': a['version'], 'url': a['url'], 'sha256': a['sha256'], 'size': a['size']}
                for a in sorted(actions, key=lambda a: a['name'])]
    with urllib.request.urlopen(MICROMAMBA_URL, timeout=120) as response:
        program = response.read()
    path = HERE / 'installer_inputs.json'
    inputs = json.loads(path.read_text())
    inputs['tools'] = {'micromamba': {'url': MICROMAMBA_URL, 'sha256': hashlib.sha256(program).hexdigest(), 'size': len(program),
                                      'publisher': 'mamba-org micromamba 2.9.0 (static Linux x64)'},
                       'specs': SPECS, 'packages': packages,
                       'publisher': 'conda-forge (python, git, 7zip and their dependencies)'}
    path.write_text(json.dumps(inputs, indent=1, sort_keys=True) + '\n')
    print('%d packages, %.1f MB' % (len(packages), sum(p['size'] for p in packages) / 1e6))
    return 0


if __name__ == '__main__':
    sys.exit(main())
