"""Read-only public release discovery. Never download or apply executable content."""
import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = 'kannibalk1w1/SoloScape'
ENDPOINT = 'https://api.github.com/repos/' + REPOSITORY + '/releases/latest'
MAX_RESPONSE = 256 * 1024
TIMEOUT = 4
TAG = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z')
BUNDLE_NAME = re.compile(r'soloscape-update-[A-Za-z0-9._-]{1,64}\.zip\Z')
DIGEST = re.compile(r'sha256:([0-9a-f]{64})\Z')
MAX_BUNDLE = 8 << 20  # matches the staging lab's archive bound


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def result(state, message, **fields):
    return dict(state=state, message=message, install_available=False, **fields)


def parse_release(value):
    if (not isinstance(value, dict) or type(value.get('id')) is not int or value['id'] < 1
            or value.get('draft') is not False or value.get('prerelease') is not False):
        raise ValueError('Expected a published stable release.')
    tag = value.get('tag_name')
    if not isinstance(tag, str) or not TAG.fullmatch(tag):
        raise ValueError('Unsupported release tag.')
    url = 'https://github.com/' + REPOSITORY + '/releases/tag/' + urllib.parse.quote(tag, safe='')
    if value.get('html_url') != url:
        raise ValueError('Release URL does not match the project.')
    title, notes = value.get('name'), value.get('body')
    title = tag if title is None else title
    notes = '' if notes is None else notes
    if not isinstance(title, str) or len(title) > 200 or not isinstance(notes, str) or len(notes) > 128 * 1024:
        raise ValueError('Unsupported release text.')
    return result('release_available', 'Published release: ' + tag + '. Automatic installation is not available yet.',
                  tag=tag, title=title, notes=notes, url=url, bundle=parse_bundle(tag, value.get('assets')))


def asset_url(tag, name):
    return 'https://github.com/' + REPOSITORY + '/releases/download/' + urllib.parse.quote(tag, safe='') + '/' + name


def parse_bundle(tag, assets):
    """Return the one declared update bundle, or None. Other assets are ignored, never fetched."""
    if assets is None:
        return None
    if not isinstance(assets, list) or len(assets) > 64:
        raise ValueError('Unsupported release assets.')
    found = []
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get('name'), str):
            raise ValueError('Unsupported release asset.')
        if BUNDLE_NAME.fullmatch(asset['name']):
            found.append(asset)
    if not found:
        return None
    if len(found) > 1:
        raise ValueError('More than one update bundle is published.')
    asset = found[0]
    name = asset['name']
    size, digest = asset.get('size'), asset.get('digest')
    if type(size) is not int or not 1 <= size <= MAX_BUNDLE:
        raise ValueError('Update bundle size is not acceptable.')
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ValueError('Update bundle has no sha256 digest.')
    if asset.get('browser_download_url') != asset_url(tag, name):
        raise ValueError('Update bundle URL does not match the project.')
    return dict(name=name, size=size, sha256=digest[len('sha256:'):], url=asset_url(tag, name))


def check():
    request = urllib.request.Request(ENDPOINT, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'SoloScape-launcher-update-check',
    })
    try:
        with urllib.request.build_opener(NoRedirects()).open(request, timeout=TIMEOUT) as response:
            data = response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise ValueError('Release response is too large.')
        return parse_release(json.loads(data))
    except urllib.error.HTTPError as exc:
        exc.close()
        if exc.code == 404:
            return result('no_public_release', 'No public SoloScape release is available yet.')
        return result('unavailable', 'Update check unavailable. You can keep using your installed version.')
    except (OSError, ValueError, UnicodeError, http.client.HTTPException):
        return result('unavailable', 'Update check unavailable. You can keep using your installed version.')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2))
