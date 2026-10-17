import json
from pathlib import Path
import tempfile
import unittest
from current_status import render


class CurrentStatusTests(unittest.TestCase):
    def fixture(self, root):
        (root / 'docs').mkdir()
        (root / 'docs/evidence.md').write_text('Dated evidence')
        for stack in ('client', 'server'):
            directory = root / 'patches' / stack
            directory.mkdir(parents=True)
            (directory / '0001-example.patch').write_text('source A')
        data = {'reviewed_on': '2026-10-17', 'reviewed_base': 'reviewed commit',
                'entries': [{'id': 'controls', 'scope': 'Input',
                             'delivery': 'IMPLEMENTED / AUTOMATED VALIDATION PASSED',
                             'acceptance': 'PHYSICAL ACCEPTANCE REQUIRED',
                             'evidence': 'evidence.md', 'note': 'Scope and limits'}]}
        (root / 'docs/current-status.json').write_text(json.dumps(data))
        return data

    def test_patch_contents_change_identity_without_promoting_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            first = render(root)
            (root / 'patches/client/0001-example.patch').write_text('source B')
            second = render(root)
            self.assertNotEqual(first, second)
            self.assertIn('PHYSICAL ACCEPTANCE REQUIRED', second)
            self.assertNotIn('PHYSICALLY ACCEPTED', second)

    def test_missing_and_outside_evidence_cannot_support_a_status_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.fixture(root)
            for bad in ('missing.md', '../../unrelated.md'):
                data['entries'][0]['evidence'] = bad
                (root / 'docs/current-status.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    render(root)

    def test_duplicate_capability_and_unknown_acceptance_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.fixture(root)
            data['entries'].append(data['entries'][0])
            (root / 'docs/current-status.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                render(root)
            data['entries'].pop()
            data['entries'][0]['acceptance'] = 'seems fine'
            (root / 'docs/current-status.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                render(root)


if __name__ == '__main__':
    unittest.main()
