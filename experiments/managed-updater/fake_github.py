"""PRIVATE ACCEPTANCE ONLY: stands in for GitHub for a launcher backend started as `python3 <backend>`.

The acceptance puts a `python3` wrapper first on PATH that runs this file, which patches the two network
seams of the real backend (release discovery and the asset transport) before running the real
launcher_backend.py unchanged. Production code has no feed or URL override. Metadata is labelled TEST and
the served bytes are a private package that must never be published. State comes from the JSON file named
by SOLOSCAPE_FAKE_GITHUB, re-read on every call so the coordinator can switch scenarios between steps.
"""
import io
import json
import os
import runpy
import sys
import time
from pathlib import Path

backend = sys.argv[1]
sys.path.insert(0, str(Path(backend).resolve().parent))
import release_updates  # noqa: E402
import update_package  # noqa: E402


def scenario():
    return json.loads(Path(os.environ['SOLOSCAPE_FAKE_GITHUB']).read_text())


def check():
    state = scenario()
    if state['mode'] == 'none':
        return release_updates.result('no_public_release', 'No public SoloScape release is available yet.')
    if state['mode'] == 'offline':
        return release_updates.result('unavailable', 'Update check unavailable. You can keep using your installed version.')
    tag, name = state['tag'], state['name']
    package = dict(name=name, size=state['size'], sha256=state['sha256'], url=release_updates.asset_url(tag, name), tag=tag)
    found = release_updates.result(
        'release_available', 'Published release: ' + tag + '. An installable package is attached.', tag=tag, title=tag,
        notes='PRIVATE TEST METADATA: this is not a published SoloScape release.',
        url='https://github.com/kannibalk1w1/SoloScape/releases/tag/' + tag, bundle=None, package=package)
    found['install_available'] = True
    return found


class Throttled:
    def __init__(self, data, rate):
        self.stream, self.rate = io.BytesIO(data), rate

    def read(self, count):
        chunk = self.stream.read(min(count, 4096))  # small reads so a small package still shows progress
        if chunk:
            time.sleep(len(chunk) / self.rate)
        return chunk

    def close(self):
        self.stream.close()


def opener(url):
    state = scenario()
    if state['mode'] != 'serve':
        raise OSError('offline')
    return Throttled(Path(state['path']).read_bytes(), state['rate'])


release_updates.check = check
update_package._open = opener
sys.argv = [backend]
runpy.run_path(backend, run_name='__main__')
