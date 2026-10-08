"""Recovery/isolation tests use disposable copies; never read real accounts or caches."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import profiles


def native_save(name='Tester'):
    return ('accountName = '+json.dumps(name)+'\npasswordHash = "fixture-hash"\nexperience = '+str([0]*25)+'\nlevels = '+str([1]*25)+'\nlooks = '+str([0]*7)+'\ncolours = '+str([0]*5)+'\nmale = true\n[tile]\nx = 3221\ny = 3219\n[variables]\nquest_state = "completed"\n[inventories]\ninventory = [{id = "bronze_sword", amount = 1}, {}]\n').encode()


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(profiles,'PROFILES',Path(self.temp.name)/'profiles')
        self.patch.start()
        self.profile = profiles.create('Test character','Tester')
        self.save = self.profile.state/'saves/tester.toml'
        self.save.write_bytes(native_save())

    def tearDown(self):
        self.patch.stop();self.temp.cleanup()

    def test_profile_creation_is_private_and_separates_mutable_world_paths(self):
        another=profiles.create('Other','Tester')
        a,b=self.profile.environment(),another.environment()
        for key in ('storage.players.path','storage.players.logs','storage.players.errors','storage.data.modified','storage.wildcards','storage.caching.path'):
            self.assertNotEqual(a[key],b[key]);self.assertTrue(a[key].startswith(str(self.profile.state)))
        self.assertEqual(a['network.bind'],'127.0.0.1')
        self.assertEqual(self.profile.directory.stat().st_mode&0o777,0o700)
        self.assertEqual((self.profile.directory/'login.json').stat().st_mode&0o777,0o600)
        metadata=self.profile.metadata();self.assertTrue(metadata['saved']);self.assertEqual(metadata['location']['x'],3221)
        self.assertNotIn('password',json.dumps(metadata));self.assertNotIn('fixture-hash',json.dumps(metadata))

    def test_verified_restore_switches_generation_and_retains_corrupt_original(self):
        offer=self.profile.state/'saves/grand_exchange/offers.toml';offer.parent.mkdir();offer.write_text('counter = 123\n')
        backup=self.profile.backup();old=self.profile.state
        self.save.write_bytes(b'corrupt native save')
        self.assertIsNotNone(self.profile.metadata()['error'])
        self.profile.restore(backup.name)
        self.assertNotEqual(old,self.profile.state);self.assertEqual((old/'saves/tester.toml').read_bytes(),b'corrupt native save')
        self.assertEqual((self.profile.state/'saves/tester.toml').read_bytes(),native_save())
        self.assertEqual((self.profile.state/'saves/grand_exchange/offers.toml').read_text(),'counter = 123\n')
        self.assertTrue(self.profile.metadata()['saved'])

    def test_atomic_switch_failure_preserves_previous_generation(self):
        backup=self.profile.backup();old=self.profile.state
        with patch.object(profiles,'atomic_json',side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):self.profile.restore(backup.name)
        self.assertEqual(old,self.profile.state);self.assertEqual(profiles.load(self.profile.manifest['id']).state,old)
        self.assertEqual(len(list((self.profile.directory/'states').iterdir())),1)

    def test_running_profile_refuses_backup_or_restore(self):
        backup=self.profile.backup()
        with self.profile.lock():
            with self.assertRaises(RuntimeError):self.profile.backup()
            with self.assertRaises(RuntimeError):self.profile.restore(backup.name)
        self.assertEqual((self.profile.state/'saves/tester.toml').read_bytes(),native_save())

    def test_corrupt_checksum_or_foreign_backup_cannot_change_active_world(self):
        backup=self.profile.backup();old=self.profile.state
        with zipfile.ZipFile(backup) as z:contents={i.filename:z.read(i) for i in z.infolist()}
        contents['state/saves/tester.toml']=native_save('Other')
        with zipfile.ZipFile(backup,'w') as z:
            for key,value in contents.items():z.writestr(key,value)
        with self.assertRaises(ValueError):self.profile.restore(backup.name)
        self.assertEqual(old,self.profile.state)
        other=profiles.create('Other','Other')
        with self.assertRaises(ValueError):other.validate_backup(self.profile.backup())

    def test_unsafe_zip_paths_duplicates_and_symbolic_links_are_rejected(self):
        backup=self.profile.backup();old=self.profile.state
        for member in ('../escape','/absolute','saves\\escape'):
            data=b'unsafe';record={'format':1,'profile':self.profile.manifest['id'],'account':'Tester','files':{member:{'size':len(data),'sha256':profiles.hash_bytes(data)}}}
            with zipfile.ZipFile(backup,'w') as z:z.writestr('backup.json',json.dumps(record));z.writestr('state/'+member,data)
            with self.assertRaises(ValueError):self.profile.restore(backup.name)
            self.assertEqual(old,self.profile.state)
        (self.profile.state/'saves/link').symlink_to(Path(self.temp.name))
        with self.assertRaises(ValueError):self.profile.backup()

    def test_state_symlink_is_rejected_before_launch_environment(self):
        logs=self.profile.state/'logs';logs.rmdir();logs.symlink_to(Path(self.temp.name))
        with self.assertRaises(ValueError):self.profile.environment()

    def test_native_validation_rejects_wrong_account_and_malformed_items(self):
        with self.assertRaises(ValueError):profiles.validate_save(native_save(),'Other')
        with self.assertRaises(ValueError):profiles.validate_save(native_save().replace(b'amount = 1',b'amount = -1'))
        with self.assertRaises(ValueError):profiles.validate_save(b'not valid toml')

    def test_import_copies_bytes_and_never_changes_source(self):
        source=Path(self.temp.name)/'original.toml';source.write_bytes(native_save())
        imported=profiles.import_character(source,'Imported')
        self.assertEqual(source.read_bytes(),native_save());self.assertEqual((imported.state/'saves/tester.toml').read_bytes(),native_save())
        self.assertEqual(json.loads((imported.directory/'login.json').read_text())['password'],'')
        self.assertEqual(len(list((imported.directory/'backups').glob('*.zip'))),1)

    def test_missing_or_damaged_manifest_is_recovered_from_verified_backup_and_preserved(self):
        backup=self.profile.backup();uid=self.profile.manifest['id'];old=self.profile.state
        manifest=self.profile.directory/'profile.json';manifest.write_text('broken metadata')
        self.assertTrue(profiles.list_backups(uid)[0]['valid'])
        profiles.restore_profile(uid,backup.name)
        restored=profiles.load(uid)
        self.assertEqual(restored.manifest['label'],'Test character')
        self.assertEqual((restored.state/'saves/tester.toml').read_bytes(),native_save())
        self.assertNotEqual(old,restored.state)
        self.assertEqual(next(self.profile.directory.glob('damaged-manifest-*.json')).read_text(),'broken metadata')
        manifest.unlink();profiles.restore_profile(uid,backup.name)
        self.assertTrue(profiles.load(uid).metadata()['saved'])

    def test_recovery_refuses_active_profile_and_tampered_archive(self):
        backup=self.profile.backup();uid=self.profile.manifest['id']
        with self.profile.lock():
            (self.profile.directory/'profile.json').write_text('broken')
            with self.assertRaises(RuntimeError):profiles.restore_profile(uid,backup.name)
        backup.write_bytes(b'not a zip')
        with self.assertRaises(ValueError):profiles.restore_profile(uid,backup.name)
        self.assertEqual((self.profile.directory/'profile.json').read_text(),'broken')

    def test_failed_import_removes_only_its_new_profile(self):
        source=Path(self.temp.name)/'original.toml';source.write_bytes(native_save())
        with patch.object(profiles.Profile,'_backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):profiles.import_character(source,'Imported')
        self.assertEqual(source.read_bytes(),native_save())
        self.assertEqual(len(profiles.list_profiles()),1)

    def test_derived_logs_and_cache_are_not_backed_up_but_failed_saves_are(self):
        (self.profile.state/'temp/derived.map').write_bytes(b'cache')
        (self.profile.state/'logs/session.log').write_text('logs')
        (self.profile.state/'errors/failed.toml').write_bytes(native_save())
        backup=self.profile.backup();_,contents=self.profile.validate_backup(backup)
        self.assertEqual(set(contents),{'saves/tester.toml','errors/failed.toml'})


if __name__=='__main__':unittest.main()
