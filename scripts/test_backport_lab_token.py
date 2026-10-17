import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import backport_lab_token as token


class LabTokenBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.lab = self.root / 'lab'
        self.lab.mkdir()
        self.manifest = json.loads(token.MANIFEST.read_text())

    def tearDown(self):
        self.temporary.cleanup()

    def test_manifest_matches_the_single_candidate(self):
        self.assertEqual(token.validate_manifest(self.manifest)['target']['id'], 20179)

    def test_manifest_rejects_production_or_appearance_claims(self):
        for key, value in (('enabled_in_production', True), ('appearance_proof', True)):
            with self.subTest(key=key):
                bad = dict(self.manifest, **{key: value})
                with self.assertRaises(ValueError):
                    token.validate_manifest(bad)

    def test_manifest_rejects_wearable_or_dependency_changes(self):
        with self.assertRaises(ValueError):
            token.validate_manifest(dict(self.manifest, dependencies=['model:1']))
        bad = json.loads(json.dumps(self.manifest))
        bad['definition']['wearable'] = True
        with self.assertRaises(ValueError):
            token.validate_manifest(bad)

    def test_candidate_refuses_occupied_or_out_of_range_ids(self):
        with self.assertRaises(ValueError):
            token.check_candidate({20178, 20179})
        token.check_candidate({20178})
        with mock.patch.object(token, 'TARGET', token.CEILING):
            with self.assertRaises(ValueError):
                token.check_candidate(set())

    def test_guard_requires_a_real_cache_copy_inside_lab(self):
        good = self.lab / 'lab-token-1' / 'cache-copy'
        good.mkdir(parents=True)
        token.guard_copy(good, self.lab)
        wrong_name = self.lab / 'lab-token-1' / 'copy'
        wrong_name.mkdir()
        with self.assertRaises(ValueError):
            token.guard_copy(wrong_name, self.lab)
        outside = self.root / 'cache-copy'
        outside.mkdir()
        with self.assertRaises(ValueError):
            token.guard_copy(outside, self.lab)
        link = self.lab / 'linked' / 'cache-copy'
        link.parent.mkdir()
        os.symlink(good, link)
        with self.assertRaises(ValueError):
            token.guard_copy(link, self.lab)

    def test_scan_blocks_item_reservations_and_reports_other_hits(self):
        data = self.root / 'data'
        (data / 'npc').mkdir(parents=True)
        (data / 'npc' / 'wander.tables.toml').write_text('#[.20179]\nwander_range = 0\n')
        self.assertEqual(token.scan_reservations(data, [])['other_toml_occurrences'][0]['commented'], True)
        (data / 'x.items.toml').write_text('[[item]]\nid = 20179\n')
        with self.assertRaises(ValueError):
            token.scan_reservations(data, [])

    def test_scan_ignores_negative_hash_offsets(self):
        data = self.root / 'data'
        data.mkdir()
        source = self.root / 'src'
        source.mkdir()
        (source / 'Hash.java').write_text('x.method(-20179);\n')
        self.assertEqual(token.scan_reservations(data, [source])['source_literal_occurrences'], 0)

    def test_copy_baseline_refuses_symlink_entries(self):
        baseline = self.root / 'baseline'
        baseline.mkdir()
        for name in ('dat2', 'idx255', 'idx16', 'idx18', 'idx19', 'idx20'):
            (baseline/('main_file_cache.'+name)).write_bytes(b'original cache metadata fixture')
        (baseline/'main_file_cache.idx20').unlink()
        os.symlink(baseline/'main_file_cache.idx19', baseline/'main_file_cache.idx20')
        original = token.BASELINE
        token.BASELINE = baseline
        try:
            with self.assertRaises(ValueError):
                token.copy_baseline(self.root / 'copy' / 'cache-copy')
        finally:
            token.BASELINE = original


    def test_manifest_binds_fields_to_the_actual_fixed_definition(self):
        for key, value in (('name', 'Other'), ('cost', 38), ('cost', True), ('stackable', True),
                           ('note_link', 32768), ('lend_link', 1), ('stack_variants', [1]),
                           ('animations', 1), ('opcodes', [2, 11, 12, 97, 0])):
            with self.subTest(key=key, value=value):
                bad = json.loads(json.dumps(self.manifest))
                bad['definition'][key] = value
                with self.assertRaises(ValueError):
                    token.validate_manifest(bad)
        with self.assertRaises(ValueError):
            token.validate_manifest(dict(self.manifest, schema_version=True))
        with self.assertRaises(ValueError):
            token.validate_manifest(dict(self.manifest, extra='not declared'))

    def test_manifest_loader_rejects_duplicate_and_nonfinite_values(self):
        path = self.root/'manifest.json'
        good = json.dumps(self.manifest)
        for bad in ('{"schema_version":1,'+good[1:], good.replace('37', 'NaN')):
            path.write_text(bad)
            with self.assertRaises(ValueError):
                token.load_manifest(path)

    def test_copy_guard_rejects_a_linked_ancestor(self):
        real = self.lab/'real'
        (real/'cache-copy').mkdir(parents=True)
        alias = self.lab/'alias'
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ValueError):
            token.guard_copy(alias/'cache-copy', self.lab)

    def test_copy_is_exact_refuses_existing_output_and_protects_baseline(self):
        baseline = self.root/'baseline'
        baseline.mkdir()
        for name in ('dat2', 'idx255', 'idx16', 'idx18', 'idx19', 'idx20'):
            (baseline/('main_file_cache.'+name)).write_bytes(b'original cache metadata fixture')
        with mock.patch.object(token, 'BASELINE', baseline):
            before = token.fingerprint(baseline)
            target = self.lab/'copy'/'cache-copy'
            token.copy_baseline(target)
            self.assertEqual(token.fingerprint(target), before)
            self.assertEqual(token.fingerprint(baseline), before)
            with self.assertRaises(FileExistsError):
                token.copy_baseline(target)
            with self.assertRaises(ValueError):
                token.copy_baseline(baseline/'cache-copy')
            (baseline/'unexpected.txt').write_bytes(b'original extra fixture')
            with self.assertRaises(ValueError):
                token.copy_baseline(self.lab/'other'/'cache-copy')

    def test_reservation_scan_fingerprint_detects_source_changes(self):
        data = self.root/'data'
        data.mkdir()
        path = data/'example.items.toml'
        path.write_text('id = 123\n')
        before = token.scan_reservations(data, [])
        path.write_text('id = 124\n')
        after = token.scan_reservations(data, [])
        self.assertEqual(before['inspected_files'], 1)
        self.assertNotEqual(before['inspected_files_sha256'], after['inspected_files_sha256'])


    def test_wrong_baseline_identity_refuses_before_native_execution(self):
        baseline = self.root/'baseline'
        baseline.mkdir()
        for name in ('dat2', 'idx255', 'idx16', 'idx18', 'idx19', 'idx20'):
            (baseline/('main_file_cache.'+name)).write_bytes(b'original incompatible cache fixture')
        with mock.patch.object(token, 'BASELINE', baseline), mock.patch.object(token.subprocess, 'run') as native:
            with self.assertRaisesRegex(ValueError, 'Baseline fingerprint differs'):
                token.perform(object())
            native.assert_not_called()


    def test_source_scan_prunes_mutable_state_before_traversing_it(self):
        data = self.root/'data'
        (data/'source').mkdir(parents=True)
        (data/'source/example.items.toml').write_text('id = 123\n')
        excluded_files = set()
        for name in token.MUTABLE_DATA_DIRS:
            directory = data/name
            directory.mkdir()
            path = directory/'sentinel.items.toml'
            path.write_text('id = 20179\n')  # original fixture, never owner data
            excluded_files.add(path)
        original_read = Path.read_text
        def read_source_only(path, *args, **kwargs):
            if path in excluded_files:
                self.fail('Excluded state file was read')
            return original_read(path, *args, **kwargs)
        walked = []
        original_walk = os.walk
        def record_walk(*args, **kwargs):
            for row in original_walk(*args, **kwargs):
                walked.append(Path(row[0]))
                yield row
        with mock.patch.object(Path, 'read_text', read_source_only), mock.patch.object(token.os, 'walk', record_walk):
            result = token.scan_reservations(data, [])
        self.assertEqual(result['inspected_files'], 1)
        self.assertEqual(result['other_toml_occurrences'], [])
        self.assertFalse(any(path.parent == data and path.name in token.MUTABLE_DATA_DIRS for path in walked))


if __name__ == '__main__':
    unittest.main()
