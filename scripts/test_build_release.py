import contextlib
import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import build_release as release
import managed_fixture as fx
import package_builder
import source_fixture


class ReleaseDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='release-delivery-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.source = source_fixture.Source(self.tmp / 'fixture')
        self.path, _ = self.source.package(self.tmp)

    def test_legacy_format_code_only_package_matches_the_named_source(self):
        manifest = release.audit_package(self.path, 'r2', self.source.commit, self.source.origin)
        self.assertEqual(manifest['files'][fx.SERVER], {'supply': 'local'})

    def test_private_game_payload_and_wrong_source_are_refused(self):
        private, _, _ = fx.make_package(self.tmp, 'r2')
        with self.assertRaises(ValueError):
            release.audit_package(private, 'r2', 'c' * 40)
        for label, commit in (('r3', self.source.commit), ('r2', 'a' * 40)):
            with self.assertRaises(ValueError):
                release.audit_package(self.path, label, commit, self.source.origin)
        (self.source.origin / 'scripts/launcher.sh').write_text('changed')
        with self.assertRaises(ValueError):
            release.audit_package(self.path, 'r2', self.source.commit, self.source.origin)

    def test_one_release_build_emits_both_delivery_paths_with_matching_identity_and_checksums(self):
        (self.source.origin / 'LICENSE').write_text('Original synthetic fixture license\n')
        source_fixture.commit_all(self.source.origin)
        self.source.commit = source_fixture.git(self.source.origin, 'rev-parse', 'HEAD')
        def prepared(checkout, label, versions, destination):
            _, raw = self.source.manifest()
            return package_builder.write_zip(self.source.released, raw, destination)
        destination = self.tmp / 'artifacts'
        with patch.object(release, 'ROOT', self.source.origin), patch.object(package_builder, 'checkout_package', side_effect=prepared), \
                patch.object(release.local_dev, 'build_lock', return_value=contextlib.nullcontext()):
            release.build('r2', destination)
        assets = json.loads((destination / 'release-assets.json').read_text())
        self.assertEqual(set(assets['assets']), {'soloscape-installer.sh', 'soloscape-package-r2.zip'})
        self.assertEqual(assets['source_commit'], self.source.commit)
        for name, metadata in assets['assets'].items():
            digest = hashlib.sha256((destination / name).read_bytes()).hexdigest()
            self.assertEqual(digest, metadata['sha256'])
            self.assertEqual((destination / (name + '.sha256')).read_text(), digest + '  ' + name + '\n')
        with zipfile.ZipFile(destination / 'soloscape-installer.sh') as archive:
            self.assertEqual(json.loads(archive.read('release.json'))['commit'], self.source.commit)
        with zipfile.ZipFile(destination / 'soloscape-package-r2.zip') as archive:
            self.assertEqual(archive.comment, (self.source.origin / 'LICENSE').read_bytes())

    def test_dirty_source_is_refused_before_any_artifact_is_written(self):
        (self.source.origin / 'scripts/launcher.sh').write_text('uncommitted')
        destination = self.tmp / 'artifacts'
        with patch.object(release, 'ROOT', self.source.origin), self.assertRaisesRegex(ValueError, 'Commit'):
            release.build('r2', destination)
        self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
