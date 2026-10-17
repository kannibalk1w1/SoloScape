"""Cache selector boundaries use only original disposable inputs."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import local_dev
import profile_session


class CacheLocationTests(unittest.TestCase):
    def test_unset_uses_current_source_default(self):
        self.assertEqual(local_dev.cache_directory({}), local_dev.SERVER / 'data/cache')

    def test_external_path_is_selected_without_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'shared cache'
            self.assertEqual(local_dev.cache_directory({local_dev.CACHE_HOME_ENV: str(path)}), path)
            self.assertFalse(path.exists())

    def test_invalid_explicit_paths_never_fall_back_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'file').write_bytes(b'original')
            (root / 'link').symlink_to(root / 'missing', target_is_directory=True)
            before = sorted(root.iterdir())
            for value in ('', '.', 'relative/cache', ' ', 'bad\0path', str(root/'file'), str(root/'link')):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    local_dev.cache_directory({local_dev.CACHE_HOME_ENV: value})
            self.assertEqual(sorted(root.iterdir()), before)
            self.assertEqual((root/'file').read_bytes(), b'original')

    def test_owned_environment_resolves_cache_and_removes_selector(self):
        class FixtureProfile:
            def environment(self, port):
                return {'network.port': str(port), 'storage.players.path': '/disposable/saves/'}
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'shared input'
            with patch.dict(os.environ, {local_dev.CACHE_HOME_ENV: str(cache),
                                         'storage.cache.path': '/inherited/wrong/cache/'}, clear=True):
                env = profile_session.owned_environment(FixtureProfile(), 43596)
            self.assertEqual(env['storage.cache.path'], str(cache) + '/')
            self.assertEqual(env['storage.players.path'], '/disposable/saves/')
            self.assertNotIn(local_dev.CACHE_HOME_ENV, env)
            self.assertFalse(cache.exists())

    def test_doctor_reports_invalid_selector_without_probing_default(self):
        # Keep all unrelated setup checks disposable and stub Java/Git subprocesses.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = []
            with patch.object(local_dev, 'ROOT', root), patch.object(local_dev, 'SERVER', root/'server'), \
                 patch.object(local_dev, 'CLIENT', root/'client'), \
                 patch.object(local_dev, 'java_version', return_value=21), \
                 patch.dict(os.environ, {local_dev.CACHE_HOME_ENV: ''}, clear=True):
                self.assertFalse(local_dev.doctor(require_display=False, check_port=False,
                                                  output=lambda *args: output.append(' '.join(map(str, args)))))
            text = '\n'.join(output)
            self.assertIn('SOLOSCAPE_CACHE_HOME must be', text)
            self.assertNotIn('missing/empty', text)
