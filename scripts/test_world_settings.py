import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import profiles
import save_sync
from test_profiles import native_save


class WorldSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        mocked = patch.object(profiles, 'PROFILES', Path(self.temp.name) / 'profiles')
        mocked.start()
        self.addCleanup(mocked.stop)
        self.profile = profiles.create('Rates', 'Tester')
        (self.profile.state / 'saves/tester.toml').write_bytes(native_save())

    def test_defaults_isolation_and_server_environment(self):
        other = profiles.create('Other', 'Other')
        uid = self.profile.manifest['id']
        profiles.configure_world(uid, {'xp': 5, 'drops': 3, 'infinite_run': True})
        settings = profiles.load(uid).environment()
        self.assertEqual(settings['world.experienceRate'], '5.0')
        self.assertEqual(settings['world.itemDropRate'], '3.0')
        self.assertEqual(settings['world.players.infiniteRunEnergy'], 'true')
        self.assertEqual(other.environment()['world.experienceRate'], '1.0')

    def test_invalid_rates_do_not_change_manifest(self):
        path = self.profile.directory / 'profile.json'
        before = path.read_bytes()
        for value in (0, -1, 101, math.nan, math.inf, True, '5'):
            with self.assertRaises(ValueError):
                profiles.configure_world(self.profile.manifest['id'], {'xp': value})
            self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ValueError):
            profiles.world_settings({'infinite_run': 'true'})

    def test_active_or_unrecovered_world_cannot_change_settings(self):
        uid = self.profile.manifest['id']
        with self.profile.lock():
            with self.assertRaises(RuntimeError):
                profiles.configure_world(uid, {'xp': 2})
        (self.profile.directory / 'session.json').write_text('{}')
        with self.assertRaises(RuntimeError):
            profiles.configure_world(uid, {'xp': 2})

    def test_backup_restore_and_sync_preserve_rates(self):
        uid = self.profile.manifest['id']
        expected = {'xp': 5.0, 'drops': 2.0, 'infinite_run': True}
        profiles.configure_world(uid, expected)
        self.profile.reload()
        backup = self.profile.backup()
        profiles.configure_world(uid, {'xp': 10})
        profiles.load(uid).restore(backup.name)
        self.assertEqual(profiles.load(uid).metadata()['world'], expected)
        bundle = save_sync.publish(uid, Path(self.temp.name) / 'sync')
        received = save_sync.receive(bundle, 'Transferred')
        self.assertEqual(received.metadata()['world'], expected)
