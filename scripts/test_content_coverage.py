from pathlib import Path
import tempfile
import unittest

from content_coverage import read_results


class CoverageEvidenceTests(unittest.TestCase):
    def test_missing_or_empty_suite_cannot_be_counted_as_a_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, 'Missing'):
                read_results(root, ['Selected'], root)
            (root / 'TEST-Selected.xml').write_text('<testsuite tests="0" failures="0" errors="0" skipped="0"/>')
            with self.assertRaisesRegex(RuntimeError, 'no tests'):
                read_results(root, ['Selected'], root)

    def test_failed_and_skipped_results_are_preserved_for_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'archive'
            archive.mkdir()
            raw = '<testsuite tests="4" failures="1" errors="1" skipped="1"/>'
            (root / 'TEST-Selected.xml').write_text(raw)
            rows = read_results(root, ['Selected'], archive)
            self.assertEqual((rows[0]['failures'], rows[0]['errors'], rows[0]['skipped']), (1, 1, 1))
            self.assertEqual((archive / 'TEST-Selected.xml').read_text(), raw)

    def test_unselected_historical_results_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'archive'
            archive.mkdir()
            for name, count in [('Selected', 2), ('Historical', 500)]:
                (root / f'TEST-{name}.xml').write_text(f'<testsuite tests="{count}" failures="0" errors="0" skipped="0"/>')
            rows = read_results(root, ['Selected'], archive)
            self.assertEqual(sum(row['tests'] for row in rows), 2)
            self.assertFalse((archive / 'TEST-Historical.xml').exists())
