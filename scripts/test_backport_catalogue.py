"""Original metadata fixtures; no proprietary cache or binary is needed by CI."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import backport_catalogue as lab


def slots():
    return {'schema_version': 1, 'namespaces': [
        {'kind': kind, 'index': index, 'archive_shift': shift,
         'occupied_ids': [0, (2 << shift) | 7]} for kind, (index, shift) in lab.NAMESPACES.items()]}


class CatalogueTests(unittest.TestCase):
    def test_native_namespace_splits_keep_sparse_and_zero_slots(self):
        result = lab.validate_slots(slots())
        self.assertEqual(result['npc']['occupied_ids'], [0, 263])
        self.assertEqual(result['item']['occupied_ids'], [0, 519])
        self.assertEqual(result['item']['count'], 2)
        self.assertEqual(result['item']['highest_occupied_id'], 519)

    def test_invalid_catalogues_cannot_become_occupancy_evidence(self):
        invalid = [None, [], {}, dict(slots(), schema_version=2), dict(slots(), namespaces=[])]
        for field, value in [('kind', 'model'), ('kind', []), ('index', True), ('index', 18),
                             ('archive_shift', 7), ('occupied_ids', []), ('occupied_ids', [False]),
                             ('occupied_ids', [1, 1]), ('occupied_ids', [2, 1]),
                             ('occupied_ids', [-1]), ('occupied_ids', [2147483648])]:
            raw = slots()
            raw['namespaces'][0][field] = value
            invalid.append(raw)
        raw = slots()
        raw['namespaces'].append(copy.deepcopy(raw['namespaces'][0]))
        invalid.append(raw)
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    lab.validate_slots(raw)

    def test_fingerprint_records_all_cache_files_but_no_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            self.make_cache(cache)
            extra = cache / 'main_file_cache.idx7'
            extra.write_bytes(b'original additional index')
            (cache / 'private-keys.json').write_text('not a cache input')
            before = lab.fingerprint(cache)
            self.assertIn(extra.name, before)
            self.assertNotIn('private-keys.json', before)
            extra.write_bytes(b'changed additional index')
            self.assertNotEqual(lab.fingerprint(cache), before)

    def test_missing_and_linked_cache_files_are_refused_without_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            with self.assertRaises(ValueError):
                lab.fingerprint(cache)
            self.make_cache(cache)
            index = cache / 'main_file_cache.idx19'
            index.unlink()
            index.symlink_to(cache / 'main_file_cache.idx18')
            with self.assertRaises(ValueError):
                lab.fingerprint(cache)

    @staticmethod
    def make_cache(cache):
        cache.mkdir(parents=True, exist_ok=True)
        for name in ('dat2', 'idx255', 'idx16', 'idx18', 'idx19', 'idx20'):
            (cache / ('main_file_cache.' + name)).write_bytes(('original ' + name).encode())

    def inspect_fixture(self, mutate=None, output_mode='normal'):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool = root / 'backport/tooling/CacheSlots.java'
            tool.parent.mkdir(parents=True)
            tool.write_bytes((lab.ROOT / 'backport/tooling/CacheSlots.java').read_bytes())
            cache = root / 'input-cache'
            self.make_cache(cache)
            jar = root / 'server.jar'
            jar.write_bytes(b'fixture, not a real jar')
            source = root / 'source/cache/src/main/kotlin/world/gregs/voidps/cache'
            for name in lab.SOURCE_FILES:
                p = source / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('original codec fixture')
            private = root / '.runtime/backport-lab'
            private.mkdir(parents=True)
            output = private / 'report.json'
            if output_mode == 'input':
                output = cache / 'report.json'
            elif output_mode == 'outside':
                output = root / 'report.json'
            elif output_mode == 'existing':
                output.write_text('keep existing evidence')
            elif output_mode == 'link':
                output.symlink_to(root / 'missing-target')

            def fake_run(command, **kwargs):
                if command[0].endswith('/java'):
                    Path(command[-1]).write_text(json.dumps(slots()))
                    if mutate:
                        {'cache': cache / 'main_file_cache.dat2', 'jar': jar, 'tool': tool,
                         'source': source / lab.SOURCE_FILES[0]}[mutate].write_bytes(b'changed during inspection')

            with patch.object(lab, 'ROOT', root), patch.object(lab.subprocess, 'run', side_effect=fake_run) as run:
                if mutate or output_mode != 'normal':
                    with self.assertRaises(ValueError):
                        lab.inspect(cache, jar, root / 'source', root / 'jdk', output)
                    if output_mode == 'existing':
                        self.assertEqual(output.read_text(), 'keep existing evidence')
                    elif output_mode != 'link':
                        self.assertFalse(output.exists())
                    if output_mode != 'normal':
                        run.assert_not_called()
                else:
                    report = lab.inspect(cache, jar, root / 'source', root / 'jdk', output)
                    self.assertFalse(report['allocation_allowed'])
                    self.assertEqual(report, json.loads(output.read_text()))
                    self.assertEqual(report['cache_files'], lab.fingerprint(cache))
                    return lab.canonical(report)

    def test_report_is_deterministic_and_has_no_absolute_input_paths(self):
        first = self.inspect_fixture()
        self.assertEqual(first, self.inspect_fixture())
        self.assertNotIn(b'/tmp/', first)

    def test_changed_inputs_withhold_the_report(self):
        for source in ('cache', 'jar', 'source', 'tool'):
            with self.subTest(source=source):
                self.inspect_fixture(mutate=source)

    def test_output_cannot_replace_inputs_or_existing_evidence(self):
        for mode in ('input', 'outside', 'existing', 'link'):
            with self.subTest(mode=mode):
                self.inspect_fixture(output_mode=mode)


if __name__ == '__main__':
    unittest.main()
