import os
import unittest
import csv
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

    def test_offset_distinguishes_flag_frame_from_stall_frame(self):
        rows = trace([16.7] * 20) + trace([30], 'a', 11) + trace([700], 'a') + trace([16.7] * 20)
        self.assertEqual(analyse(rows)['stall_offset_from_loading_frame'], {1: 1})

    @unittest.skipUnless(os.environ.get('SOLOSCAPE_R29_ROUTE_CSV'), 'private r29 trace not supplied')
    def test_full_r29_route_trace(self):
        with open(os.environ['SOLOSCAPE_R29_ROUTE_CSV'], newline='') as source:
            result = analyse(csv.DictReader(source))
        self.assertEqual((result['frames'], result['stalls'], result['loading_state_frames'], result['stalls_near_loading_state']), (128025, 40, 29, 38))
        self.assertEqual(sum(len(v) for k, v in result['stall_steps'].items() if k != 'map' and k != 'close_map'), 20)
        self.assertAlmostEqual(result['p99_ms_excluding_stalls_over_floor'], 22.28, places=1)

    def test_empty_trace_fails(self):
        with self.assertRaises(ValueError):
            analyse([])


if __name__ == '__main__':
    unittest.main()
