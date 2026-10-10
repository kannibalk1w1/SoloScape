import json
import os
from pathlib import Path
import tempfile
import unittest
import deck_export
import deck_runtime
import local_dev


class DeckSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'payload').write_bytes(b'checked build')
        self.manifest = {'format': 1, 'pins': local_dev.PINNED, 'files': {
            'payload': {'size': 13, 'sha256': local_dev.file_hash(self.root / 'payload')}}}
        self.write_manifest()

    def write_manifest(self):
        (self.root / 'deck-manifest.json').write_text(json.dumps(self.manifest))

    def test_verified_and_corrupt_payload(self):
        self.assertEqual(deck_runtime.verify(self.root), 1)
        (self.root / 'payload').write_bytes(b'changed build')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            deck_runtime.verify(self.root)

    def test_missing_and_symlink_replacement(self):
        (self.root / 'payload').unlink()
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            deck_runtime.verify(self.root)
        (self.root / 'other').write_bytes(b'checked build')
        (self.root / 'payload').symlink_to('other')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            deck_runtime.verify(self.root)

    def test_traversal_and_absolute_names(self):
        for name in ('../payload', '/tmp/payload'):
            self.manifest['files'] = {name: {'size': 0, 'sha256': ''}}
            self.write_manifest()
            with self.assertRaisesRegex(ValueError, 'path'):
                deck_runtime.verify(self.root)

    def test_external_link_refused(self):
        (self.root / 'link').symlink_to('/etc/passwd')
        self.manifest['files'] = {'link': {'link': '/etc/passwd'}}
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'leaves'):
            deck_runtime.verify(self.root)

    def test_contained_runtime_link_and_target(self):
        (self.root / 'link').symlink_to('payload')
        self.manifest['files']['link'] = {'link': 'payload'}
        self.write_manifest()
        self.assertEqual(deck_runtime.verify(self.root), 2)
        (self.root / 'link').unlink()
        (self.root / 'link').symlink_to('wrong')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            deck_runtime.verify(self.root)

    def test_config_preserves_existing_and_quotes_path(self):
        root = self.root / "space and ' quote"
        root.mkdir()
        deck_runtime.configure(root)
        config = root / 'config/local.env'
        initial = config.read_bytes()
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        import subprocess
        result = subprocess.check_output(['bash', '-c', 'source "$1"; printf "%s" "$CLIENT_JAVA"', 'bash', str(config)], text=True)
        self.assertEqual(result, str(root / '.runtime/jdks/jdk8/bin/java'))
        with self.assertRaisesRegex(ValueError, 'retained'):
            deck_runtime.configure(root)
        self.assertEqual(config.read_bytes(), initial)

    def test_mutable_source_exclusion_and_near_names(self):
        for name in ('data/saves/account.toml', 'data/errors/failure', 'data/.temp/a', 'data/exchange/a', 'data/cache/a', '../a', '/tmp/a'):
            self.assertFalse(deck_export.safe_source(name), name)
        self.assertTrue(deck_export.safe_source('data/cache-definition.toml'))
        self.assertTrue(deck_export.safe_source('game/src/PlayerSave.kt'))

    def test_pin_mismatch(self):
        self.manifest['pins'] = {}
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'pins'):
            deck_runtime.verify(self.root)

    def test_parent_directory_link_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / 'payload').write_bytes(b'secret')
        (self.root / 'redirect').symlink_to(outside.name, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'leaves'):
            deck_export.copy_file(self.root / 'redirect/payload', self.root / 'copy', self.root)

    def test_only_pin_reachable_objects_exported(self):
        import subprocess
        repo = self.root / 'repo'
        repo.mkdir()
        def git(*args, **kw):
            return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL, **kw).decode().strip()
        git('init')
        (repo / 'tracked').write_text('pinned')
        git('add', 'tracked')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'pin')
        pin = git('rev-parse', 'HEAD')
        (repo / 'private-save').write_text('dummy private save must never travel')
        git('add', 'private-save')
        blob = git('hash-object', 'private-save')
        git('reset', 'HEAD', '--', 'private-save')
        target = self.root / 'snapshot'
        target.mkdir()
        (target / 'tracked').write_text('pinned')
        deck_export.copy_pin_metadata(repo, target, pin)
        self.assertEqual(subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD']).decode().strip(), pin)
        result = subprocess.run(['git', '-C', str(target), 'cat-file', '-e', blob], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((target / '.git/refs/stash').exists())
        self.assertFalse((target / '.git/objects/info/alternates').exists())


if __name__ == '__main__':
    unittest.main()
