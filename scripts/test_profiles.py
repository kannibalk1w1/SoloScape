"""Recovery/isolation tests use disposable copies; never read real accounts or caches."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import profiles


def native_save(name='Tester'):
    return ('accountName = '+json.dumps(name)+'\npasswordHash = "fixture-hash"\nexperience = '+str([0]*25)+'\nlevels = '+str([1]*25)+'\nlooks = '+str([0]*7)+'\ncolours = '+str([0]*5)+'\nmale = true\n[tile]\nx = 3221\ny = 3219\n[variables]\nquest_state = "completed"\n[inventories]\ninventory = [{id = "bronze_sword", amount = 1}, {}]\n').encode()


WORLD_PAYLOAD = 'piles = []\n[[graves]]\nid = "0f8fad5b-d9cb-469f-a165-000000000001"\naccount = "tester"\nname = "Tester grave"\nmale = true\nkind = "player_grave"\ntile = 3221\ndirection = 0\nremaining = 300\nblessed = false\nlatest = true\n'


def world_file(payload=WORLD_PAYLOAD, digest=None):
    raw = payload.encode()
    digest = hashlib.sha256(raw).hexdigest() if digest is None else digest
    return ('format = 1\npayload = "' + base64.b64encode(raw).decode() + '"\nsha256 = "' + digest + '"\n').encode()


def versioned_save(version, name='Tester'):
    return b'storage_version = ' + str(version).encode() + b'\n' + native_save(name)


def pending_batch(members):
    rows = ''.join(f'{name}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\n' for name, data in sorted(members.items()))
    files = {'manifest.tsv': ('SOLOSCAPE_ACCOUNT_BATCH_V1\n' + rows).encode()}
    files.update(members)
    return {'saves/.soloscape-account-save/' + name: data for name, data in files.items()}


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

    def test_pending_first_checkpoint_imports_without_a_canonical_primary_account(self):
        source = Path(self.temp.name) / 'stopped'
        source.mkdir()
        members = pending_batch({'tester.toml': versioned_save(1), '.soloscape-death-loot.v1': world_file()})
        for name, data in members.items():
            target = source / name.removeprefix('saves/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        imported = profiles.import_world_copy(source, 'Committed first save', 'Tester')
        self.assertFalse((imported.state / 'saves/tester.toml').exists())
        self.assertTrue(imported.metadata()['saved'])
        self.assertIsNone(imported.metadata()['error'])
        archive = imported.backup('pending-first-save')
        _, copied = imported.validate_backup(archive)
        self.assertEqual(copied, members)
        # The same exact pending decision covers a damaged old canonical primary.
        (imported.state / 'saves/tester.toml').write_bytes(b'corrupt canonical')
        archive = imported.backup('covered-damage')
        imported.restore(archive.name)
        self.assertEqual((imported.state / 'saves/tester.toml').read_bytes(), b'corrupt canonical')
        self.assertTrue(imported.metadata()['saved'])
        self.assertIsNone(imported.metadata()['error'])
        self.assertTrue((imported.state / 'saves/.soloscape-account-save/manifest.tsv').is_file())

    def test_malformed_pending_layout_refuses_backup_without_changing_saved_world(self):
        healthy = self.profile.backup()
        original = self.save.read_bytes()
        pending = self.profile.state / 'saves/.soloscape-account-save'
        pending.mkdir()
        with self.assertRaisesRegex(ValueError, 'manifest'):
            self.profile.backup()
        self.assertEqual(self.save.read_bytes(), original)
        self.assertEqual(list((self.profile.directory / 'backups').glob('*.zip')), [healthy])
        # Even an empty unlisted directory cannot disappear from the byte-map
        # validation and turn an invalid live journal into a verified backup.
        member = native_save()
        import hashlib
        (pending / 'tester.toml').write_bytes(member)
        (pending / 'manifest.tsv').write_text('SOLOSCAPE_ACCOUNT_BATCH_V1\n' + f'tester.toml\t{len(member)}\t{hashlib.sha256(member).hexdigest()}\n')
        (pending / 'unexpected-empty-directory').mkdir()
        with self.assertRaisesRegex(ValueError, 'unsupported member'):
            self.profile.backup()
        self.assertEqual(self.save.read_bytes(), original)
        self.assertTrue((pending / 'unexpected-empty-directory').is_dir())
        self.assertEqual(list((self.profile.directory / 'backups').glob('*.zip')), [healthy])

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

    def test_broken_deflate_stream_does_not_hide_verified_backups_or_change_world(self):
        good = self.profile.backup()
        with zipfile.ZipFile(good) as archive:
            contents = {entry.filename: archive.read(entry) for entry in archive.infolist()}
        for member in ('backup.json', 'state/saves/tester.toml'):
            with self.subTest(member=member):
                bad = good.with_name('broken-' + ('header' if member == 'backup.json' else 'save') + '.zip')
                with zipfile.ZipFile(bad, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for name, data in contents.items():
                        archive.writestr(name, data)
                damaged = bytearray(bad.read_bytes())
                with zipfile.ZipFile(bad) as archive:
                    offset = archive.getinfo(member).header_offset
                # Local ZIP header followed by name/extra fields, then raw DEFLATE.
                start = offset + 30 + int.from_bytes(damaged[offset+26:offset+28], 'little') + int.from_bytes(damaged[offset+28:offset+30], 'little')
                damaged[start] = 0x07  # BFINAL=1, reserved BTYPE=3: deterministic decompression failure.
                bad.write_bytes(damaged)
                before_manifest = (self.profile.directory / 'profile.json').read_bytes()
                before_state = self.profile.state
                generations = set((self.profile.directory / 'states').iterdir())

                rows = {row['name']: row for row in profiles.list_backups(self.profile.manifest['id'])}
                self.assertFalse(rows[bad.name]['valid'])
                self.assertTrue(rows[good.name]['valid'])
                with self.assertRaises(ValueError):
                    self.profile.restore(bad.name)
                self.assertEqual((self.profile.directory / 'profile.json').read_bytes(), before_manifest)
                self.assertEqual(set((self.profile.directory / 'states').iterdir()), generations)
                self.assertEqual((before_state / 'saves/tester.toml').read_bytes(), native_save())
                self.assertEqual(bad.read_bytes(), damaged)

                self.profile.restore(good.name)
                self.assertNotEqual(self.profile.state, before_state)
                self.assertEqual((self.profile.state / 'saves/tester.toml').read_bytes(), native_save())
                self.assertTrue(before_state.is_dir())
                self.assertEqual(bad.read_bytes(), damaged)

    def test_checksums_do_not_make_a_wrong_primary_account_restorable(self):
        backup = self.profile.backup()
        before_manifest = (self.profile.directory / 'profile.json').read_bytes()
        before_state = self.profile.state
        with zipfile.ZipFile(backup) as archive:
            contents = {entry.filename: archive.read(entry) for entry in archive.infolist()}
        wrong_account = native_save('Other')
        contents['state/saves/tester.toml'] = wrong_account
        metadata = json.loads(contents['backup.json'])
        metadata['files']['saves/tester.toml'] = {
            'size': len(wrong_account), 'sha256': profiles.hash_bytes(wrong_account),
        }
        contents['backup.json'] = json.dumps(metadata).encode()
        with zipfile.ZipFile(backup, 'w') as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
        archive_bytes = backup.read_bytes()
        self.assertFalse(profiles.list_backups(self.profile.manifest['id'])[0]['valid'])
        with self.assertRaisesRegex(ValueError, 'different account'):
            self.profile.restore(backup.name)
        self.assertEqual(self.profile.state, before_state)
        self.assertEqual((self.profile.directory / 'profile.json').read_bytes(), before_manifest)
        self.assertEqual(self.save.read_bytes(), native_save())
        self.assertEqual(backup.read_bytes(), archive_bytes)
        self.assertEqual(len(list((self.profile.directory / 'states').iterdir())), 1)

    def test_backup_refuses_wrong_primary_account_without_publishing_an_archive(self):
        self.save.write_bytes(native_save('Other'))
        before = self.save.read_bytes()
        with self.assertRaisesRegex(ValueError, 'different account'):
            self.profile.backup()
        self.assertEqual(self.save.read_bytes(), before)
        self.assertEqual(list((self.profile.directory / 'backups').iterdir()), [])

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

    def test_invalid_account_metadata_isolated_and_recoverable_without_data_loss(self):
        healthy = profiles.create('Healthy character', 'Healthy')
        healthy_bytes = (healthy.directory / 'profile.json').read_bytes()
        backup = self.profile.backup()
        uid = self.profile.manifest['id']
        original_state = self.profile.state
        manifest_path = self.profile.directory / 'profile.json'
        valid_manifest = dict(self.profile.manifest)
        for account in (None, 42, [], {}, True, '   '):
            with self.subTest(account=account):
                manifest_path.write_text(json.dumps(dict(valid_manifest, account=account)))
                damaged_bytes = manifest_path.read_bytes()
                listed = {row['id']: row for row in profiles.list_profiles()}
                self.assertTrue(listed[uid]['error'])
                self.assertFalse(listed[uid]['saved'])
                self.assertIsNone(listed[healthy.manifest['id']]['error'])
                self.assertEqual(manifest_path.read_bytes(), damaged_bytes)
                self.assertTrue(profiles.list_backups(uid)[0]['valid'])
                profiles.restore_profile(uid, backup.name)
                restored = profiles.load(uid)
                self.assertEqual(restored.manifest['account'], 'Tester')
                self.assertEqual((restored.state / 'saves/tester.toml').read_bytes(), native_save())
                preserved = restored.directory / restored.manifest['recovered_from_manifest']
                self.assertEqual(preserved.read_bytes(), damaged_bytes)
                self.assertEqual((original_state / 'saves/tester.toml').read_bytes(), native_save())
                self.assertEqual((healthy.directory / 'profile.json').read_bytes(), healthy_bytes)

    def test_recovery_refuses_active_profile_and_tampered_archive(self):
        backup=self.profile.backup();uid=self.profile.manifest['id']
        with self.profile.lock():
            (self.profile.directory/'profile.json').write_text('broken')
            with self.assertRaises(RuntimeError):profiles.restore_profile(uid,backup.name)
        backup.write_bytes(b'not a zip')
        with self.assertRaises(ValueError):profiles.restore_profile(uid,backup.name)
        self.assertEqual((self.profile.directory/'profile.json').read_text(),'broken')

    def write_state(self, contents):
        for relative, data in contents.items():
            path = self.profile.state / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def state_files(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / 'saves').rglob('*') if p.is_file()}

    def test_pending_mixed_batch_backup_and_restore_keep_journal_and_logical_world(self):
        self.save.write_bytes(native_save())
        self.write_state({'saves/other.toml': native_save('Other')})
        self.write_state(pending_batch({'tester.toml': versioned_save(1), profiles.death_loot_state.WORLD_FILE: world_file()}))
        before = self.state_files(self.profile.state)
        backup = self.profile.backup()
        _, contents = self.profile.validate_backup(backup)
        self.assertEqual({k: v for k, v in contents.items() if k.startswith('saves/')}, before)
        self.profile.restore(backup.name)
        self.assertEqual(self.state_files(self.profile.state), before)
        logical = profiles.death_loot_state.validate_state(before, profiles.validate_save)
        self.assertEqual(logical['accounts']['tester']['storage_version'], 1)
        self.assertEqual([g['name'] for g in logical['world']['graves']], ['Tester grave'])
        self.assertEqual(sorted(logical['accounts']), ['other', 'tester'])

    def test_storage_version_one_without_world_refuses_backup_and_keeps_healthy_backup(self):
        healthy = self.profile.backup()
        self.save.write_bytes(versioned_save(1))
        before = self.save.read_bytes()
        backups = sorted((self.profile.directory / 'backups').iterdir())
        with self.assertRaisesRegex(ValueError, 'world'):
            self.profile.backup()
        self.assertEqual(self.save.read_bytes(), before)
        self.assertEqual(sorted((self.profile.directory / 'backups').iterdir()), backups)
        self.write_state({'saves/' + profiles.death_loot_state.WORLD_FILE: world_file(digest='0' * 64)})
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.profile.backup()
        self.assertTrue(profiles.list_backups(self.profile.manifest['id'])[0]['valid'])
        self.assertEqual(self.profile.directory.joinpath('backups', healthy.name).read_bytes(), healthy.read_bytes())
        self.assertEqual(self.save.read_bytes(), before)

    def test_tampered_journal_member_with_consistent_record_is_refused_on_restore(self):
        self.write_state(pending_batch({'tester.toml': versioned_save(1), profiles.death_loot_state.WORLD_FILE: world_file()}))
        backup = self.profile.backup()
        with zipfile.ZipFile(backup) as archive:
            contents = {entry.filename: archive.read(entry) for entry in archive.infolist()}
        member = 'state/saves/.soloscape-account-save/tester.toml'
        contents[member] = versioned_save(1, 'Other')
        metadata = json.loads(contents['backup.json'])
        metadata['files']['saves/.soloscape-account-save/tester.toml'] = {'size': len(contents[member]), 'sha256': profiles.hash_bytes(contents[member])}
        contents['backup.json'] = json.dumps(metadata).encode()
        with zipfile.ZipFile(backup, 'w') as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
        before_manifest = (self.profile.directory / 'profile.json').read_bytes()
        self.assertFalse(profiles.list_backups(self.profile.manifest['id'])[0]['valid'])
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.profile.restore(backup.name)
        self.assertEqual((self.profile.directory / 'profile.json').read_bytes(), before_manifest)

    def test_native_storage_version_accepts_only_absent_zero_or_one(self):
        for prefix in (b'', b'storage_version = 0\n', b'storage_version = 1\n'):
            with self.subTest(prefix=prefix):
                profiles.validate_save(prefix + native_save())
        for value in (b'2', b'-1', b'true', b'"1"'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    profiles.validate_save(b'storage_version = ' + value + b'\n' + native_save())

    def test_world_copy_import_requires_the_world_file_for_versioned_accounts(self):
        source = Path(self.temp.name) / 'versioned-world'
        source.mkdir()
        (source / 'tester.toml').write_bytes(versioned_save(1))
        with self.assertRaisesRegex(ValueError, 'world'):
            profiles.import_world_copy(source, 'Refused', 'Tester')
        self.assertEqual(len(profiles.list_profiles()), 1)
        (source / profiles.death_loot_state.WORLD_FILE).write_bytes(world_file())
        imported = profiles.import_world_copy(source, 'Accepted', 'Tester')
        self.assertEqual((imported.state / 'saves' / profiles.death_loot_state.WORLD_FILE).read_bytes(), world_file())
        self.assertEqual(len(profiles.list_profiles()), 2)

    def test_failed_import_removes_only_its_new_profile(self):
        source=Path(self.temp.name)/'original.toml';source.write_bytes(native_save())
        with patch.object(profiles.Profile,'_backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):profiles.import_character(source,'Imported')
        self.assertEqual(source.read_bytes(),native_save())
        self.assertEqual(len(profiles.list_profiles()),1)

    def test_world_copy_migration_preserves_accounts_exchange_and_authentication_bytes(self):
        source=Path(self.temp.name)/'stopped-world';source.mkdir()
        (source/'tester.toml').write_bytes(native_save());(source/'other.toml').write_bytes(native_save('Other'))
        exchange=source/'grand_exchange';exchange.mkdir();(exchange/'counter.toml').write_text('counter = 123\n')
        migrated=profiles.import_world_copy(source,'Migrated','Tester','existing-pass')
        self.assertEqual((migrated.state/'saves/tester.toml').read_bytes(),native_save())
        self.assertEqual((migrated.state/'saves/other.toml').read_bytes(),native_save('Other'))
        self.assertEqual((migrated.state/'saves/grand_exchange/counter.toml').read_bytes(),(exchange/'counter.toml').read_bytes())
        self.assertEqual((source/'tester.toml').read_bytes(),native_save())
        self.assertEqual(json.loads((migrated.directory/'login.json').read_text())['password'],'existing-pass')
        self.assertEqual(len(profiles.list_backups(migrated.manifest['id'])),1)

    def test_world_migration_refuses_original_paths_and_unsafe_copies(self):
        with patch.object(profiles,'ROOT',Path(self.temp.name)):
            source=Path(self.temp.name)/'upstream/game-server/data/saves';source.mkdir(parents=True)
            with self.assertRaises(ValueError):profiles.import_world_copy(source,'Unsafe','Tester')
        source=Path(self.temp.name)/'copied-world';source.mkdir();(source/'tester.toml').write_bytes(native_save())
        (source/'linked').symlink_to(self.save)
        with self.assertRaises(ValueError):profiles.import_world_copy(source,'Unsafe','Tester')
        self.assertEqual(len(profiles.list_profiles()),1)
        with self.assertRaises(ValueError):profiles.import_world_copy(self.profile.state/'saves','Unsafe','Tester')

    def test_import_is_hidden_until_copy_and_verified_backup_finish(self):
        source=Path(self.temp.name)/'copy';source.mkdir();(source/'tester.toml').write_bytes(native_save())
        original=profiles.Profile._backup
        def check(profile,reason):
            self.assertEqual(len(profiles.list_profiles()),1)
            return original(profile,reason)
        with patch.object(profiles.Profile,'_backup',check):
            imported=profiles.import_world_copy(source,'Imported','Tester')
        self.assertEqual(len(profiles.list_profiles()),2)
        self.assertEqual(imported.directory.parent,profiles.PROFILES)
        self.assertFalse(list(profiles.PROFILES.glob('.import-*')))

    def test_retention_preview_and_cleanup_keep_manual_damaged_and_newest_automatic_backups(self):
        manual=self.profile.backup('manual')
        for i in range(6):self.profile.backup('after-clean-shutdown')
        damaged=self.profile.directory/'backups/damaged.zip';damaged.write_bytes(b'damaged')
        uid=self.profile.manifest['id'];oldstate=self.profile.state
        plan=profiles.preview_retention(uid,2);self.assertEqual(len(plan['remove']),4)
        result=profiles.apply_retention(uid,2,plan['token']);self.assertEqual(result['removed'],4)
        self.assertTrue(manual.exists());self.assertTrue(damaged.exists());self.assertEqual(self.profile.state,oldstate)
        self.assertEqual(len(list((self.profile.directory/'backups').glob('*.zip'))),4)
        self.assertEqual(self.save.read_bytes(),native_save())

    def test_retention_refuses_changed_preview_active_lock_and_symlink_directory(self):
        uid=self.profile.manifest['id']
        for i in range(4):self.profile.backup('before-launch')
        plan=profiles.preview_retention(uid,2);self.profile.backup('after-clean-shutdown')
        before=set((self.profile.directory/'backups').glob('*.zip'))
        with self.assertRaises(ValueError):profiles.apply_retention(uid,2,plan['token'])
        self.assertEqual(set((self.profile.directory/'backups').glob('*.zip')),before)
        with self.profile.lock():
            with self.assertRaises(RuntimeError):profiles.preview_retention(uid,2)
        backups=self.profile.directory/'backups';backups.rename(self.profile.directory/'held-backups');backups.symlink_to(self.profile.directory/'held-backups')
        with self.assertRaises(ValueError):profiles.preview_retention(uid,2)

    def test_retention_protects_the_automatic_backup_used_for_latest_restore(self):
        origin=self.profile.backup('before-launch')
        for i in range(4):self.profile.backup('after-clean-shutdown')
        self.profile.restore(origin.name)
        old=self.profile.state
        plan=profiles.preview_retention(self.profile.manifest['id'],2)
        self.assertNotIn(origin.name,[row['name'] for row in plan['remove']])
        self.assertEqual(len(plan['remove']),2)
        profiles.apply_retention(self.profile.manifest['id'],2,plan['token'])
        self.assertTrue(origin.exists());self.assertEqual(self.profile.state,old)
        self.assertEqual((old/'saves/tester.toml').read_bytes(),native_save())

    def test_native_writer_escapes_decode_identically_in_strict_toml(self):
        # Exact bytes asserted by server ConfigStringEscapeTest's writer test.
        escaped=b'desc = "q\\" b\\\\ n\\n t\\t r\\r e\\u001B d\\u007F \xc3\xa9"\n'
        save=native_save().replace(b'[variables]\n',b'[variables]\n'+escaped+b'"Mod \\"Mark\\"" = "Ye \\"Olde\\" C:\\\\Clan\\\\"\n')
        variables=profiles.validate_save(save)['variables']
        self.assertEqual(variables['desc'],'q" b\\ n\n t\t r\r e\x1b d\x7f \u00e9')
        self.assertEqual(variables['Mod "Mark"'],'Ye "Olde" C:\\Clan\\')
        # Before server 0022 a trailing backslash was written raw and broke strict validation.
        with self.assertRaises(ValueError):profiles.validate_save(native_save().replace(b'[variables]\n',b'[variables]\nclan = "C:\\Clan\\"\n'))

    def test_derived_logs_and_cache_are_not_backed_up_but_failed_saves_are(self):
        (self.profile.state/'temp/derived.map').write_bytes(b'cache')
        (self.profile.state/'logs/session.log').write_text('logs')
        (self.profile.state/'errors/failed.toml').write_bytes(native_save())
        backup=self.profile.backup();_,contents=self.profile.validate_backup(backup)
        self.assertEqual(set(contents),{'saves/tester.toml','errors/failed.toml'})


if __name__=='__main__':unittest.main()
