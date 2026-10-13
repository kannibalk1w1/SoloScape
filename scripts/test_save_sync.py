import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import profiles
import save_sync
from test_profiles import native_save


class SaveSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = patch.object(profiles, 'PROFILES', self.root / 'profiles')
        self.store.start()
        self.profile = profiles.create('Source', 'Tester')
        (self.profile.state / 'saves/tester.toml').write_bytes(native_save())
        (self.profile.state / 'saves/grand_exchange').mkdir()
        (self.profile.state / 'saves/grand_exchange/counter.toml').write_text('counter = 123\n')
        (self.profile.state / 'temp/cache.dat').write_bytes(b'cache')
        (self.profile.directory / 'session-logs').mkdir()
        (self.profile.directory / 'session-logs/client.log').write_text('private log')

    def tearDown(self):
        self.store.stop()
        self.temp.cleanup()

    def test_round_trip_preserves_world_and_keeps_existing_character(self):
        bundle = save_sync.publish(self.profile.manifest['id'], self.root / 'sync')
        _, contents = save_sync.validate_bundle(bundle)
        self.assertEqual(set(contents), {'saves/tester.toml', 'saves/grand_exchange/counter.toml'})
        imported = save_sync.receive(bundle, 'Received')
        self.assertNotEqual(imported.manifest['id'], self.profile.manifest['id'])
        self.assertEqual((imported.state / 'saves/tester.toml').read_bytes(), native_save())
        self.assertEqual((imported.state / 'saves/grand_exchange/counter.toml').read_text(), 'counter = 123\n')
        self.assertEqual((self.profile.state / 'saves/tester.toml').read_bytes(), native_save())

    def test_running_or_unrecovered_world_cannot_publish(self):
        with self.profile.lock():
            with self.assertRaises(RuntimeError):
                save_sync.publish(self.profile.manifest['id'], self.root / 'sync')
        (self.profile.directory / 'session.json').write_text('{}')
        with self.assertRaises(RuntimeError):
            save_sync.publish(self.profile.manifest['id'], self.root / 'sync')

    def test_corrupt_bundle_cannot_create_profile(self):
        bundle = self.root / 'bad.zip'
        bundle.write_bytes(b'broken')
        before = set(profiles.PROFILES.iterdir())
        with self.assertRaises(Exception):
            save_sync.receive(bundle, 'Bad')
        self.assertEqual(set(profiles.PROFILES.iterdir()), before)

    def test_exports_are_immutable_and_exclude_runtime_storage(self):
        folder = self.root / 'sync'
        a = save_sync.publish(self.profile.manifest['id'], folder)
        b = save_sync.publish(self.profile.manifest['id'], folder)
        self.assertNotEqual(a, b)
        self.assertTrue(a.exists())
        with self.assertRaises(ValueError):
            save_sync.publish(self.profile.manifest['id'], self.profile.directory / 'sync')
