"""Release metadata is advisory; no download/install or dependence on live GitHub."""
import io
import json
import unittest
import urllib.error
from unittest.mock import Mock, patch
import launcher_backend
import release_updates


def release(**fields):
    return dict(id=17, draft=False, prerelease=False, tag_name='v0.1.0', name='A small update',
                body='Changes\n<html>plain release notes</html>',
                html_url='https://github.com/kannibalk1w1/SoloScape/releases/tag/v0.1.0', **fields)


class ReleaseUpdatesTests(unittest.TestCase):
    def fetched(self, payload):
        opener = Mock()
        opener.open.return_value = io.BytesIO(payload)
        with patch.object(release_updates.urllib.request, 'build_opener', return_value=opener):
            result = release_updates.check()
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, release_updates.ENDPOINT)
        self.assertFalse(request.has_header('Authorization'))
        self.assertEqual(opener.open.call_args.kwargs['timeout'], release_updates.TIMEOUT)
        return result

    def test_published_metadata_keeps_plain_notes_and_never_advertises_an_installer(self):
        result = self.fetched(json.dumps(release()).encode())
        self.assertEqual(result['state'], 'release_available')
        self.assertEqual(result['tag'], 'v0.1.0')
        self.assertIn('<html>plain release notes</html>', result['notes'])
        self.assertFalse(result['install_available'])
        data = release();data.update(name=None, body=None)
        parsed = release_updates.parse_release(data)
        self.assertEqual(parsed['title'], 'v0.1.0')
        self.assertEqual(parsed['notes'], '')

    def test_untrusted_or_incompatible_release_records_are_not_offered(self):
        changes = [dict(draft=True), dict(prerelease=True), dict(id=True), dict(id=-1),
                   dict(tag_name='../main'), dict(tag_name='a/b'), dict(name=False), dict(body=[]),
                   dict(html_url='https://evil.invalid/releases/tag/v0.1.0'),
                   dict(html_url='https://github.com/kannibalk1w1/Other/releases/tag/v0.1.0'),
                   dict(name='x' * 201), dict(body='x' * (128 * 1024 + 1))]
        for change in changes:
            with self.subTest(change=list(change)):
                data = release();data.update(change)
                self.assertEqual(self.fetched(json.dumps(data).encode())['state'], 'unavailable')

    def test_bad_json_and_oversized_responses_remain_nonfatal(self):
        for data in (b'{bad', b'[]', b'null', b'\xff', b'x' * (release_updates.MAX_RESPONSE + 1)):
            with self.subTest(size=len(data)):
                self.assertEqual(self.fetched(data)['state'], 'unavailable')

    def test_missing_feed_is_distinct_from_offline_rate_limit_and_server_error(self):
        for code, expected in ((404, 'no_public_release'), (403, 'unavailable'), (429, 'unavailable'), (503, 'unavailable')):
            with self.subTest(code=code):
                response = io.BytesIO(b'untrusted remote error')
                opener = Mock();opener.open.side_effect = urllib.error.HTTPError(release_updates.ENDPOINT, code, 'error', {}, response)
                with patch.object(release_updates.urllib.request, 'build_opener', return_value=opener):
                    self.assertEqual(release_updates.check()['state'], expected)
                self.assertTrue(response.closed)
        opener = Mock();opener.open.side_effect = urllib.error.URLError('offline')
        with patch.object(release_updates.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(release_updates.check()['state'], 'unavailable')

    def test_redirects_are_never_followed(self):
        handler = release_updates.NoRedirects()
        self.assertIsNone(handler.redirect_request(None, None, 302, 'redirect', {}, 'https://elsewhere.invalid'))

    def test_active_world_check_does_not_queue_network_ahead_of_save_and_quit(self):
        backend = launcher_backend.Backend()
        backend.worker = Mock();backend.worker.is_alive.return_value = True
        with patch.object(release_updates, 'check') as fetch:
            result = backend.dispatch({'action': 'update_check'})
            self.assertEqual(result['state'], 'busy')
            fetch.assert_not_called()
            backend.dispatch({'action': 'stop'})
            self.assertTrue(backend.cancelled.is_set())

    def test_backend_discovery_does_not_accept_custom_download_or_feed_targets(self):
        backend = launcher_backend.Backend()
        with patch.object(release_updates, 'check', return_value={'state': 'no_public_release'}) as fetch:
            self.assertEqual(backend.dispatch({'action': 'update_check', 'url': 'https://elsewhere.invalid'})['state'], 'no_public_release')
            fetch.assert_called_once_with()
        with self.assertRaisesRegex(ValueError, 'Unknown launcher action'):
            backend.dispatch({'action': 'update_feed', 'url': 'https://elsewhere.invalid'})
        with self.assertRaisesRegex(RuntimeError, 'cannot install updates'):
            backend.dispatch({'action': 'update_apply'})  # a source copy is never an install target
        with self.assertRaisesRegex(RuntimeError, 'cannot install updates'):
            backend.dispatch({'action': 'update_download', 'url': 'https://elsewhere.invalid'})
        for action in ('update_rebuild', 'update_rollback'):  # neither takes a source, URL or command from the request
            with self.assertRaisesRegex(RuntimeError, 'cannot install updates'):
                backend.dispatch({'action': action, 'url': 'https://elsewhere.invalid', 'command': 'touch /tmp/x', 'commit': 'a' * 40})

    def test_rebuild_and_rollback_refuse_to_start_while_a_world_runs(self):
        backend = launcher_backend.Backend()
        backend.worker = type('Alive', (), {'is_alive': lambda self: True})()
        with self.assertRaisesRegex(RuntimeError, 'Save & Quit before rebuilding'):
            backend.dispatch({'action': 'update_rebuild'})


if __name__ == '__main__':
    unittest.main()
