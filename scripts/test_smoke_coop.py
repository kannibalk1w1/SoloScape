"""Reject false two-client evidence without bundling native jars or caches in CI."""
import copy
import unittest

from smoke_coop import validate_pair


def pair(observe=False):
    names, positions = ['CoopAlpha', 'CoopBeta'], [[3222, 3219, 0], [3221, 3220, 0]]
    return [dict(self={'account': names[i], 'index': i+1, 'tile': positions[i]},
                 peer={'account': names[1-i], 'index': 2-i, 'tile': positions[1-i]},
                 observe=observe, initial_tile=positions[i] if observe else [3221, 3219, 0],
                 bronze_dagger=i, walk_sent=not observe, drop_sent=not observe and i == 0)
            for i in range(2)]


class CoopEvidenceTests(unittest.TestCase):
    def test_independent_client_views_and_readonly_restart_views_agree(self):
        self.assertTrue(validate_pair(*pair()))
        self.assertTrue(validate_pair(*pair(True), observe=True))

    def test_false_identity_position_inventory_and_dispatch_evidence_is_rejected(self):
        changes = [
            lambda a: a[0]['self'].update(account='CoopBeta'),
            lambda a: a[0]['self'].update(index=2),
            lambda a: a[0]['self'].update(index=-1),
            lambda a: a[0]['peer'].update(index=1025),
            lambda a: a[0]['self'].update(index=True),
            lambda a: a[0]['peer'].update(tile=[3222, 3220, 0]),
            lambda a: a[0]['self'].update(tile=[True, 3219, 0]),
            lambda a: a[0]['self'].update(tile=[3222, 3219, 4]),
            lambda a: a[0]['self'].update(tile=[-1, 3219, 0]),
            lambda a: a[0].update(bronze_dagger=1),
            lambda a: a[0].update(bronze_dagger=False),
            lambda a: a[1].update(bronze_dagger=0),
            lambda a: a[0].update(walk_sent=False),
            lambda a: a[0].update(drop_sent=False),
            lambda a: a[1].update(drop_sent=True),
            lambda a: a[0].update(observe=True),
            lambda a: a[0].update(initial_tile=a[0]['self']['tile']),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                evidence = copy.deepcopy(pair())
                change(evidence)
                with self.assertRaises(ValueError):
                    validate_pair(*evidence)

    def test_missing_evidence_and_observer_movement_are_rejected(self):
        for bad in (None, [], {}, {'self': None}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_pair(bad, pair()[1])
        observed = pair(True)
        observed[0]['initial_tile'] = [3221, 3219, 0]
        with self.assertRaises(ValueError):
            validate_pair(*observed, observe=True)
