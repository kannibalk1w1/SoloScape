import unittest
from summarise_frame_trace import summarise


def rows(intervals):
    return ({'interval_ms': x, 'client_state': 10} for x in intervals)


class FrameTraceTests(unittest.TestCase):
    def test_short_smooth_trace_does_not_pass_long_duration(self):
        result = summarise(rows([1000 / 60] * 600))
        self.assertFalse(result['duration_30_minutes_met'])
        self.assertAlmostEqual(result['minimum_rolling_5s_fps'], 60)
        self.assertTrue(result['full_trace_p99_20ms_met'])

    def test_sustained_slow_period_is_detected_despite_good_overall_average(self):
        result = summarise(rows([1000 / 60] * 3000 + [1000 / 30] * 180 + [1000 / 60] * 3000))
        self.assertGreater(result['average_fps'], 58)
        self.assertLess(result['minimum_rolling_5s_fps'], 31)
        self.assertFalse(result['full_trace_rolling_58fps_met'])

    def test_loading_spike_is_retained(self):
        trace = list(rows([1000 / 60] * 600))
        trace.insert(300, {'interval_ms': 1000, 'client_state': 11})
        result = summarise(trace)
        self.assertEqual(result['max_ms'], 1000)
        self.assertEqual(result['client_state_frame_counts']['11'], 1)
        self.assertFalse(result['full_trace_rolling_58fps_met'])

    def test_empty_or_invalid_trace_fails(self):
        for trace in ([], list(rows([0])), list(rows([-1]))):
            with self.assertRaises(ValueError):
                summarise(trace)
