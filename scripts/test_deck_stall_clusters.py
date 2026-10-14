import unittest
from analyse_deck_stall_clusters import analyse


def trace(intervals, step='walk', state=10):
    return [{'step': step, 'interval_ms': x, 'client_state': state} for x in intervals]


class StallClusterTests(unittest.TestCase):
    def test_stall_next_to_loading_state_is_attributed_to_its_step(self):
        rows = trace([16.7] * 50) + trace([40], 'farm_road', 11) + trace([800], 'farm_road') + trace([16.7] * 50)
        result = analyse(rows)
        self.assertEqual(result['stalls'], 1)
        self.assertEqual(result['stalls_near_loading_state'], 1)
        self.assertEqual(result['stall_steps'], {'farm_road': [800.0]})

    def test_stall_without_loading_state_is_not_attributed(self):
        result = analyse(trace([16.7] * 20 + [500] + [16.7] * 20))
        self.assertEqual(result['stalls'], 1)
        self.assertEqual(result['stalls_near_loading_state'], 0)

    def test_p99_excludes_only_whole_stalls_so_jitter_remains_visible(self):
        result = analyse(trace(([16.7] * 95 + [24] * 5) * 10 + [900]))
        self.assertGreater(result['p99_ms_excluding_stalls_over_floor'], 20)
        self.assertEqual(result['frames_over_20_ms_below_floor'], 50)
        self.assertAlmostEqual(result['excess_ms_from_stalls_over_floor'], 900 - 1000 / 60)

    def test_empty_trace_fails(self):
        with self.assertRaises(ValueError):
            analyse([])


if __name__ == '__main__':
    unittest.main()
