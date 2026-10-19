#!/usr/bin/env python3
"""Build the single-file installer (a Python zipapp) for one release.

    python3 scripts/build_installer.py --release r1 --commit <40 hex> --output soloscape-installer.sh

The file is a shell script followed by a Python zipapp. It holds the installer, its pinned inputs and the release identity, and no game data, jars, cache or art. It is
built locally; publishing it anywhere is a separate decision.
"""
import argparse
import json
import re
import stat
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def header(inputs):
    """The shell script that starts the installer, with the pinned tool downloads filled in from the inputs file."""
    tools = inputs['tools']
    lock = '\n'.join(p['sha256'] + ' ' + p['url'] for p in tools['packages'])
    total = (tools['micromamba']['size'] + sum(p['size'] for p in tools['packages'])) / 1e6
    text = (HERE / 'installer_header.sh').read_text()
    for key, value in (('@@MICROMAMBA_URL@@', tools['micromamba']['url']), ('@@MICROMAMBA_SHA@@', tools['micromamba']['sha256']),
                       ('@@TOTAL_MB@@', '%d' % round(total, -1)), ('@@LOCK@@', lock)):
        text = text.replace(key, value)
    return text.encode()


def build(release, commit, output):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('The commit must be 40 lowercase hex characters.')
    if not release or '/' in release:
        raise ValueError('The release name is invalid.')
    output = Path(output)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('__main__.py', 'import installer\nimport sys\nsys.exit(installer.main())\n')
        archive.write(HERE / 'installer.py', 'installer.py')
        archive.write(HERE / 'installer_inputs.json', 'installer_inputs.json')
        archive.writestr('release.json', json.dumps({'release': release, 'commit': commit}, sort_keys=True) + '\n')
    inputs = json.loads((HERE / 'installer_inputs.json').read_text())
    output.write_bytes(header(inputs) + output.read_bytes())
    output.chmod(output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--release', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', default='soloscape-installer.sh')
    args = parser.parse_args(argv)
    print(build(args.release, args.commit, args.output))
    return 0


if __name__ == '__main__':
    sys.exit(main())
