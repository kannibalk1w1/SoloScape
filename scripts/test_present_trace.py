import unittest
from summarise_present_trace import summarise


def event(ust, window='0x1', kind=0, mode=1):
    return {'ust_us': ust, 'window': window, 'kind': kind, 'mode': mode}


class PresentTraceTests(unittest.TestCase):
    def test_clock_notifications_and_skipped_requests_do_not_inflate_fps(self):
        result = summarise([event(1000), event(11000, mode=2), event(16000, kind=1), event(21000)])
        window = result['windows']['0x1']
        self.assertEqual(window['average_fps'], 50)
        self.assertEqual(window['skipped_requests'], 1)
        self.assertEqual(window['completions'], 2)

    def test_multiple_windows_are_never_counted_as_one_faster_stream(self):
        result = summarise([event(1000), event(1000, window='0x2'),
                            event(21000), event(41000, window='0x2')])
        self.assertEqual(result['windows']['0x1']['average_fps'], 50)
        self.assertEqual(result['windows']['0x2']['average_fps'], 25)

    def test_duplicate_completion_and_missing_frames_do_not_invent_fps(self):
        window = summarise([event(1000), event(1000)])['windows']['0x1']
        self.assertEqual(window['duplicate_completions'], 1)
        self.assertNotIn('average_fps', window)
        self.assertEqual(summarise([])['windows'], {})

    def test_recreated_window_lifetimes_do_not_conflate_an_unobserved_gap(self):
        rows = [dict(event(1000), epoch=1), dict(event(21000), epoch=1),
                dict(event(3100000), epoch=2), dict(event(3120000), epoch=2)]
        result = summarise(rows)['windows']
        self.assertEqual(set(result), {'0x1@1', '0x1@2'})
        self.assertEqual(result['0x1@1']['max_ms'], 20)
        self.assertEqual(result['0x1@2']['average_fps'], 50)

    def test_timestamp_errors_are_rejected(self):
        for rows in ([event(0)], [event(2000), event(1000)]):
            with self.assertRaises(ValueError):
                summarise(rows)

    def test_loading_hitch_is_preserved(self):
        rows = [event(1_000_000+n*16667) for n in range(400)]
        rows.extend(event(1_000_000+400*16667+1_000_000+n*16667) for n in range(400))
        window = summarise(rows)['windows']['0x1']
        self.assertGreater(window['max_ms'], 1000)
        self.assertFalse(window['full_trace_rolling_58fps_met'])
        self.assertFalse(window['duration_30_minutes_met'])
