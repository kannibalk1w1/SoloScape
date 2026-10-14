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

    def test_30fps_reference_does_not_count_normal_pacing_as_stall_cost(self):
        result = analyse(trace([1000 / 30] * 20 + [900]), fps_reference=30)
        self.assertEqual(result['stalls'], 1)
        self.assertEqual(result['fps_reference'], 30)
        self.assertAlmostEqual(result['stall_excess_ms_over_reference'], 900 - 1000 / 30)

    def test_empty_trace_fails(self):
        with self.assertRaises(ValueError):
            analyse([])

NEW_COLS = dict(tile_x=3200, tile_y=3200, plane=0, scene_base_x=3136, scene_base_y=3136, renderer='gpu')


def new_row(interval, step='walk', state=10, **phase):
    row = {'elapsed_ns': 1, 'step': step, 'interval_ms': interval, 'client_state': state, **NEW_COLS}
    row.update(phase)
    return row


class OptionalSchemaTests(unittest.TestCase):
    def test_old_schema_has_no_optional_fields_or_phase_note(self):
        result = analyse(trace([16.7] * 10 + [500]))
        self.assertEqual(result['schema_optional_columns_present'], [])
        self.assertNotIn('phase_note', result)
        self.assertNotIn('tile_x', result['worst_stalls'][0])
        self.assertNotIn('gc_ms_delta', result['worst_stalls'][0])

    def test_new_schema_record_preserves_fields_and_types(self):
        rows = [new_row(16.7)] * 10 + [new_row(640, 'farm_road', 11, logic_cycles_delta='3', logic_ms_delta='4.5',
                                               gc_ms_delta='120')]
        worst = analyse(rows)['worst_stalls'][0]
        self.assertEqual((worst['tile_x'], worst['plane'], worst['renderer']), (3200, 0, 'gpu'))
        self.assertEqual((worst['logic_cycles_delta'], worst['logic_ms_delta'], worst['gc_ms_delta']), (3, 4.5, 120.0))
        self.assertEqual(worst['frame_index'], 10)

    def test_absent_or_blank_measurements_are_none_not_zero(self):
        stalled = new_row(700, logic_ms_delta='', gc_ms_delta='0')
        rows = [new_row(16.7, gc_ms_delta='0')] * 3 + [stalled]
        worst = analyse(rows)['worst_stalls'][0]
        self.assertIsNone(worst['logic_ms_delta'])
        self.assertNotIn('plugins_ms_delta', worst)  # column absent from the trace entirely
        self.assertEqual(worst['gc_ms_delta'], 0.0)

    def test_overlapping_phases_are_reported_individually_never_summed(self):
        phases = dict(logic_ms_delta=500, frame_ms_delta=450, present_ms_delta=400)
        result = analyse([new_row(16.7)] * 3 + [new_row(600, **phases)])
        worst = result['worst_stalls'][0]
        self.assertEqual((worst['logic_ms_delta'], worst['frame_ms_delta'], worst['present_ms_delta']), (500, 450, 400))
        self.assertNotIn('phase_total_ms', worst)
        self.assertNotIn('phase_total_ms', result)
        self.assertIn('not be summed', result['phase_note'])

    def test_worst_stalls_bounded_sorted_and_attributed(self):
        rows = trace([16.7] * 5)
        for k in range(30):
            rows += trace([400 + k]) + trace([16.7] * 8)
        rows += trace([30], 'a', 11) + trace([350], 'a')
        result = analyse(rows)
        worst = result['worst_stalls']
        self.assertEqual(len(worst), 20)
        self.assertEqual(worst[0]['interval_ms'], 429.0)
        self.assertEqual([w['interval_ms'] for w in worst], sorted((w['interval_ms'] for w in worst), reverse=True))
        self.assertEqual(result['stalls'], 31)
        self.assertEqual(analyse(trace([16.7] * 5 + [30]) + trace([30], 'a', 11) + trace([350], 'a'))
                         ['worst_stalls'][0]['loading_state_offset'], 1)
        self.assertIsNone(analyse(trace([16.7] * 20 + [500]))['worst_stalls'][0]['loading_state_offset'])

    def test_bands_separate_jitter_from_stalls(self):
        result = analyse(trace([16.7] * 10 + [25, 50, 99.9, 150, 300, 800]))
        bands = result['interval_bands']
        self.assertEqual(bands['steady_jitter_20_to_100ms']['frames'], 3)
        self.assertEqual(bands['stalls_at_or_above_threshold']['frames'], 2)
        self.assertEqual(bands['stalls_at_or_above_threshold']['max_ms'], 800)
        self.assertEqual(bands['between_floor_and_threshold']['frames'], 1)
        self.assertAlmostEqual(bands['stalls_at_or_above_threshold']['excess_ms_over_16_7'], 1100 - 2 * 1000 / 60, places=1)


if __name__ == '__main__':
    unittest.main()
