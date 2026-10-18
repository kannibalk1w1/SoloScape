"""Bundle fetch: fixed-project URLs, declared size/digest, bounded download, then the existing stager.

Original dummy fixtures only. No network: transports are fakes, and the release check is exercised
through its real parser with a mocked opener.
"""
import hashlib
import io
import json
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import release_updates
import update_fetch

stage = update_fetch.stage

TAG = 'v0.2.0'
NAME = 'soloscape-update-v0.2.0.zip'
PAYLOAD = {
    'app/bin/launcher': b'launcher fixture\n',
    'app/client.jar': b'client fixture\n',
    'app/server.jar': b'server fixture\n',
}


def bundle_bytes(files=PAYLOAD):
    listed = dict(files)
    manifest = {
        'format': 1, 'repository': 'kannibalk1w1/SoloScape', 'platform': 'linux-x86_64',
        'source_commit40': 'a' * 40, 'cache_revision': 634,
        'roles': {'launcher': 'app/bin/launcher', 'client': 'app/client.jar', 'server': 'app/server.jar'},
        'files': {path: {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'mode': '0644'}
                  for path, data in listed.items()},
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as zf:
        zf.writestr(member('manifest.json'), json.dumps(manifest, sort_keys=True))
        for path, data in listed.items():
            zf.writestr(member(path), data)
    return buf.getvalue()


def member(name):
    info = zipfile.ZipInfo(name)
    info.external_attr = (0o100644) << 16  # a regular file, as a real archiver records it
    return info


def asset(data, **fields):
    return dict(dict(name=NAME, size=len(data), digest='sha256:' + hashlib.sha256(data).hexdigest(),
                     browser_download_url=release_updates.asset_url(TAG, NAME)), **fields)


def release_json(assets):
    return json.dumps(dict(id=17, draft=False, prerelease=False, tag_name=TAG, name='Update',
                           body='Plain notes.', html_url='https://github.com/kannibalk1w1/SoloScape/releases/tag/' + TAG,
                           assets=assets)).encode()


class Source:
    """A fake download: serves fixed bytes, optionally failing after a number of reads."""
    def __init__(self, data, fail_after=None):
        self.stream = io.BytesIO(data)
        self.fail_after = fail_after
        self.reads = 0
        self.closed = False

    def read(self, size):
        self.reads += 1
        if self.fail_after is not None and self.reads > self.fail_after:
            raise OSError('connection reset')
        return self.stream.read(size)

    def close(self):
        self.closed = True


class BundleFetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Path(self.tmp.name) / 'update-lab'
        self.lab.mkdir()
        self.data = bundle_bytes()
        self.bundle = dict(release_updates.parse_bundle(TAG, [asset(self.data)]), tag=TAG)
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def transport(self, data=None, **kwargs):
        def open_url(url):
            self.calls.append(url)
            return Source(self.data if data is None else data, **kwargs)
        return open_url

    def lab_names(self):
        return sorted(p.name for p in self.lab.iterdir() if p.name != stage.LOCK_NAME)

    def refused(self, bundle=None, transport=None, message=''):
        with self.assertRaisesRegex(update_fetch.FetchError, message):
            update_fetch.fetch_bundle(self.lab, self.bundle if bundle is None else bundle,
                                      transport=transport or self.transport())
        self.assertEqual(self.lab_names(), [], 'a refused fetch must leave nothing behind')

    def test_valid_bundle_is_fetched_exactly_once_verified_and_staged(self):
        report = update_fetch.fetch_bundle(self.lab, self.bundle, transport=self.transport())
        self.assertEqual(self.calls, [release_updates.asset_url(TAG, NAME)])
        candidate = self.lab / self.bundle['sha256']
        self.assertEqual(report['candidate'], str(candidate))
        for path, data in PAYLOAD.items():
            self.assertEqual((candidate / path).read_bytes(), data)
        self.assertEqual(self.lab_names(), [self.bundle['sha256']], 'the download itself is removed after staging')

    def test_digest_mismatch_is_refused_before_staging(self):
        flipped = self.data[:-1] + bytes([self.data[-1] ^ 1])
        self.refused(transport=self.transport(flipped), message='does not match the release digest')

    def test_truncated_download_is_refused(self):
        self.refused(transport=self.transport(self.data[:-5]), message='stopped early')

    def test_download_larger_than_declared_is_refused_without_reading_forever(self):
        self.refused(transport=self.transport(self.data + b'x' * 4096), message='larger than the release')

    def test_interrupted_download_removes_its_partial_file(self):
        self.refused(transport=self.transport(fail_after=1), message='unavailable')

    def test_digest_matching_but_unsafe_bundle_is_refused_by_the_stager(self):
        bad = bundle_bytes({'app/../escape': b'x\n', 'app/client.jar': b'c\n', 'app/server.jar': b's\n'})
        bundle = dict(release_updates.parse_bundle(TAG, [asset(bad)]), tag=TAG)
        self.assertEqual(bundle['sha256'], hashlib.sha256(bad).hexdigest())
        self.data = bad
        self.refused(bundle=bundle, message='refused')

    def test_existing_candidate_for_the_same_digest_is_refused_and_untouched(self):
        update_fetch.fetch_bundle(self.lab, self.bundle, transport=self.transport())
        candidate = self.lab / self.bundle['sha256']
        before = sorted(p.name for p in candidate.iterdir())
        with self.assertRaisesRegex(update_fetch.FetchError, 'already exists'):
            update_fetch.fetch_bundle(self.lab, self.bundle, transport=self.transport())
        self.assertEqual(sorted(p.name for p in candidate.iterdir()), before)
        self.assertEqual(self.lab_names(), [self.bundle['sha256']])

    def test_bundle_url_outside_the_project_is_never_requested(self):
        self.refused(bundle=dict(self.bundle, url='https://evil.invalid/' + NAME), message='not a file of this project')
        self.assertEqual(self.calls, [])

    def test_linked_lab_is_refused_before_any_request(self):
        link = Path(self.tmp.name) / 'link'
        link.symlink_to(self.lab, target_is_directory=True)
        with self.assertRaisesRegex(update_fetch.FetchError, 'not a link'):
            update_fetch.fetch_bundle(link, self.bundle, transport=self.transport())
        self.assertEqual(self.calls, [])

    def test_redirects_are_followed_only_to_github_object_hosts_over_https(self):
        handler = update_fetch._ProjectRedirects()
        request = update_fetch.urllib.request.Request(release_updates.asset_url(TAG, NAME))
        allowed = 'https://objects.githubusercontent.com/github-production-release-asset/x'
        self.assertIsNotNone(handler.redirect_request(request, None, 302, 'Found', {}, allowed))
        for target in ('https://evil.invalid/x', 'http://objects.githubusercontent.com/x',
                       'https://objects.githubusercontent.com.evil.invalid/x'):
            with self.subTest(target=target):
                self.assertIsNone(handler.redirect_request(request, None, 302, 'Found', {}, target))


class ReleaseBundleTests(unittest.TestCase):
    def test_only_the_one_declared_bundle_is_selected(self):
        data = bundle_bytes()
        art = dict(name='art.png', size=3, digest='sha256:' + '0' * 64, browser_download_url='https://example.invalid/x')
        found = release_updates.parse_bundle(TAG, [art, asset(data)])
        self.assertEqual(found['name'], NAME)
        self.assertEqual(found['sha256'], hashlib.sha256(data).hexdigest())
        self.assertIsNone(release_updates.parse_bundle(TAG, None))
        self.assertIsNone(release_updates.parse_bundle(TAG, []))

    def test_malformed_or_foreign_bundle_metadata_is_not_offered(self):
        data = bundle_bytes()
        changes = [
            dict(size=0), dict(size=(8 << 20) + 1), dict(size='12'), dict(digest=None), dict(digest='md5:' + '0' * 32),
            dict(digest='sha256:' + 'A' * 64), dict(browser_download_url='https://evil.invalid/' + NAME),
            dict(browser_download_url='https://github.com/kannibalk1w1/Other/releases/download/%s/%s' % (TAG, NAME)),
        ]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    release_updates.parse_bundle(TAG, [asset(data, **change)])

    def test_multiple_bundles_or_unsupported_assets_are_refused(self):
        data = bundle_bytes()
        other = asset(data, name='soloscape-update-v0.2.1.zip',
                      browser_download_url=release_updates.asset_url(TAG, 'soloscape-update-v0.2.1.zip'))
        with self.assertRaisesRegex(ValueError, 'More than one'):
            release_updates.parse_bundle(TAG, [asset(data), other])
        with self.assertRaises(ValueError):
            release_updates.parse_bundle(TAG, ['soloscape-update-v0.2.0.zip'])

    def test_traversal_name_is_not_a_bundle_and_is_never_fetched(self):
        data = bundle_bytes()
        self.assertIsNone(release_updates.parse_bundle(TAG, [asset(data, name='../' + NAME)]))


class FetchLatestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Path(self.tmp.name) / 'update-lab'
        self.lab.mkdir()
        self.data = bundle_bytes()
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def transport(self, data=None):
        def open_url(url):
            self.calls.append(url)
            return Source(self.data if data is None else data)
        return open_url

    def opener(self, payload=None, error=None):
        opener = Mock()
        if error is not None:
            opener.open.side_effect = error
        else:
            opener.open.return_value = io.BytesIO(payload)
        return opener

    def run_latest(self, opener, transport=None):
        with patch.object(release_updates.urllib.request, 'build_opener', return_value=opener):
            return update_fetch.fetch_latest(self.lab, transport=transport or self.transport())

    def test_check_then_fetch_stages_the_declared_bundle_end_to_end(self):
        report = self.run_latest(self.opener(release_json([asset(self.data)])))
        self.assertEqual(self.calls, [release_updates.asset_url(TAG, NAME)])
        candidate = self.lab / hashlib.sha256(self.data).hexdigest()
        self.assertEqual(report['candidate'], str(candidate))
        self.assertEqual((candidate / 'app' / 'client.jar').read_bytes(), PAYLOAD['app/client.jar'])

    def test_offline_rate_limited_and_missing_releases_fetch_nothing(self):
        cases = [
            (self.opener(error=urllib.error.URLError('offline')), 'Update check unavailable'),
            (self.opener(error=urllib.error.HTTPError('u', 403, 'rate limit', {}, None)), 'Update check unavailable'),
            (self.opener(error=urllib.error.HTTPError('u', 404, 'missing', {}, None)), 'No public SoloScape release'),
        ]
        for opener, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(update_fetch.FetchError, message):
                    self.run_latest(opener)
                self.assertEqual(self.calls, [])
                self.assertEqual([p.name for p in self.lab.iterdir() if p.name != stage.LOCK_NAME], [])

    def test_release_without_a_bundle_is_a_plain_refusal(self):
        with self.assertRaisesRegex(update_fetch.FetchError, 'no update bundle'):
            self.run_latest(self.opener(release_json([])))
        self.assertEqual(self.calls, [])

    def test_bad_bundle_metadata_makes_the_release_unavailable_and_fetches_nothing(self):
        bad = asset(self.data, digest=None)
        with self.assertRaisesRegex(update_fetch.FetchError, 'Update check unavailable'):
            self.run_latest(self.opener(release_json([bad])))
        self.assertEqual(self.calls, [])

    def test_fetch_latest_refuses_a_digest_mismatch_from_the_real_check_path(self):
        wrong = asset(self.data)
        wrong['digest'] = 'sha256:' + '0' * 64
        with self.assertRaisesRegex(update_fetch.FetchError, 'does not match the release digest'):
            self.run_latest(self.opener(release_json([wrong])), transport=self.transport(self.data))
        self.assertEqual([p.name for p in self.lab.iterdir() if p.name != stage.LOCK_NAME], [])


if __name__ == '__main__':
    unittest.main()
