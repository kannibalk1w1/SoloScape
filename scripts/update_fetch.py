"""Fetch the one declared update bundle of the latest published release, then stage it. Never activates.

The bundle URL must be the fixed project's release asset URL, and its size and SHA-256 come from the
release's own asset metadata. A matching digest proves the bytes are the bytes GitHub listed for that
release. It does not authenticate the publisher; see docs/GITHUB_UPDATES.md for the trust boundary.
"""
import hashlib
import hmac
import http.client
import importlib.util
import os
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path

import release_updates

# The staging lab is the verifier of record; load it by path, as its own tests do.
STAGE_SPEC = importlib.util.spec_from_file_location(
    'update_staging_stage', Path(__file__).resolve().parent.parent / 'experiments' / 'update-staging' / 'stage.py')
stage = importlib.util.module_from_spec(STAGE_SPEC)
STAGE_SPEC.loader.exec_module(stage)

TIMEOUT = 15
CHUNK = 64 << 10
REDIRECT_HOSTS = frozenset({'objects.githubusercontent.com', 'release-assets.githubusercontent.com'})


class FetchError(Exception):
    """A plain refusal or unavailability. Its message is shown to the player as-is."""


class _ProjectRedirects(urllib.request.HTTPRedirectHandler):
    """GitHub moves release downloads to its object store; follow only those fixed hosts over HTTPS."""
    max_redirections = 3

    def redirect_request(self, request, fp, code, message, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme != 'https' or parts.hostname not in REDIRECT_HOSTS:
            return None
        return super().redirect_request(request, fp, code, message, headers, newurl)


def _open(url):
    request = urllib.request.Request(url, headers={
        'Accept': 'application/octet-stream', 'User-Agent': 'SoloScape-launcher-update-fetch',
    })
    return urllib.request.build_opener(_ProjectRedirects()).open(request, timeout=TIMEOUT)


def fetch_bundle(lab_root, bundle, transport=_open):
    """Download exactly the declared bytes into a temporary file, verify them, then stage them."""
    if not isinstance(bundle, dict) or bundle.get('url') != release_updates.asset_url(
            bundle.get('tag', ''), bundle.get('name', '')):
        raise FetchError('The update bundle is not a file of this project’s release.')
    lab = Path(lab_root)
    if lab.is_symlink() or not lab.is_dir():
        raise FetchError('The update lab must be an existing folder, not a link.')
    fd, name = tempfile.mkstemp(prefix='.download-', dir=lab)
    partial = Path(name)
    try:
        digest, total = hashlib.sha256(), 0
        with os.fdopen(fd, 'wb') as out:
            source = transport(bundle['url'])
            try:
                while chunk := source.read(min(CHUNK, bundle['size'] + 1 - total)):
                    total += len(chunk)
                    if total > bundle['size']:
                        raise FetchError('The download is larger than the release says. Nothing was installed.')
                    digest.update(chunk)
                    out.write(chunk)
            finally:
                source.close()
        if total != bundle['size']:
            raise FetchError('The download stopped early. Try the check again later.')
        if not hmac.compare_digest(digest.hexdigest(), bundle['sha256']):
            raise FetchError('The download does not match the release digest. Nothing was installed.')
        return stage.stage(partial, bundle['sha256'], lab)
    except stage.StageError as exc:
        raise FetchError('The update was refused: ' + str(exc)) from None
    except (OSError, http.client.HTTPException) as exc:
        raise FetchError('The download is unavailable. You can keep using your installed version.') from exc
    finally:
        partial.unlink(missing_ok=True)


def fetch_latest(lab_root, transport=_open, check=release_updates.check):
    """Check the published release, then fetch and stage its declared bundle. Returns the stage report."""
    release = check()
    if release['state'] != 'release_available':
        raise FetchError(release['message'])
    bundle = release.get('bundle')
    if bundle is None:
        raise FetchError('The latest release has no update bundle. You can keep using your installed version.')
    return fetch_bundle(lab_root, dict(bundle, tag=release['tag']), transport=transport)
