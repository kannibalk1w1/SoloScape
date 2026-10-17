"""Original-archive checks for the metadata-only distribution inventory."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

SPEC = importlib.util.spec_from_file_location('runtime_inventory', Path(__file__).resolve().parents[1] / 'experiments/runtime-inventory/run.py')
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class RuntimeInventoryTests(unittest.TestCase):
    def archive(self, directory, entries):
        path = Path(directory) / 'original.jar'
        with warnings.catch_warnings(), zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as target:
            warnings.simplefilter('ignore', UserWarning)
            for name, data in entries:
                target.writestr(name, data)
        return path

    def test_notice_candidates_are_metadata_not_class_names(self):
        for name in ('META-INF/LICENSE.txt', 'META-INF/NOTICE', 'Intellij.license', 'COPYING', 'META-INF/soloscape-controller-NOTICES.txt'):
            self.assertTrue(inventory.notice_candidate(name))
        for name in ('example/License.class', 'example/Notices.class', 'image.png'):
            self.assertFalse(inventory.notice_candidate(name))

    def test_original_archive_records_hashes_without_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, [('META-INF/LICENSE', b'Original fixture notice'),
                                             ('fixture/Example.class', b'not executable'),
                                             ('fixture/libexample.so', b'original inert bytes')])
            result = inventory.inspect_archive(path)
            self.assertEqual(result['classes'], 1)
            self.assertEqual(result['notice_candidates'][0]['sha256'], hashlib.sha256(b'Original fixture notice').hexdigest())
            self.assertEqual(result['embedded_native_libraries'][0]['size'], len(b'original inert bytes'))
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_duplicate_names_and_oversized_compressed_notice_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, [('META-INF/LICENSE', b'one'), ('META-INF/LICENSE', b'two')])
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                inventory.inspect_archive(path)
            path = self.archive(directory, [('META-INF/LICENSE', b'x' * (inventory.MAX_NOTICE + 1))])
            with self.assertRaisesRegex(ValueError, 'Bounded'):
                inventory.inspect_archive(path)

    def test_unattributed_file_dependency_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, [('fixture/Example.class', b'original inert bytes')])
            rows = inventory.artifact_rows('SOLOSCAPE_RUNTIME_ARTIFACTS ' + json.dumps([
                dict(path=str(path), coordinate=None, origin='file-or-unattributed')]))
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0]['coordinate'])
            self.assertEqual(rows[0]['origin'], 'file-or-unattributed')
            self.assertEqual(rows[0]['notice_candidates'], [])

    def test_missing_or_ambiguous_gradle_inventory_cannot_pass(self):
        for text in ('BUILD SUCCESSFUL', 'SOLOSCAPE_RUNTIME_ARTIFACTS []',
                     'SOLOSCAPE_RUNTIME_ARTIFACTS []\nSOLOSCAPE_RUNTIME_ARTIFACTS []'):
            with self.assertRaises(ValueError):
                inventory.artifact_rows(text)
