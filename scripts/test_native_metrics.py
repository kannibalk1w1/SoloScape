import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import native_metrics
from summarise_native_metrics import summarise


def child(pid=1, start=2, ticks=0, rss=2048):
    return {'role': 'client', 'pid': pid, 'start': start, 'cpu_ticks': ticks,
            'rss_kib': rss, 'clock_ticks_per_second': 100}


class NativeMetricTests(unittest.TestCase):
    def test_cpu_uses_same_process_and_real_elapsed_time(self):
        samples = [{'elapsed_seconds': 0, 'children': [child(ticks=0)]},
                   {'elapsed_seconds': 2, 'children': [child(ticks=300, rss=4096)]},
                   {'elapsed_seconds': 3, 'children': [child(start=9, ticks=0)]},
                   {'elapsed_seconds': 5, 'children': [child(start=9, ticks=100)]}]
        result = summarise({'samples': samples})
        self.assertEqual(result['mean_cpu_percent_one_core_100']['client'], 100)
        self.assertEqual(result['peak_rss_mib_by_role']['client'], 4)

    def test_missing_and_reset_counters_never_invent_zero_efficiency(self):
        result = summarise({'samples': [{'elapsed_seconds': 1, 'children': []}]})
        self.assertEqual(result['mean_cpu_percent_one_core_100'], {})
        samples = [{'elapsed_seconds': 1, 'children': [child(ticks=500)]},
                   {'elapsed_seconds': 2, 'children': [child(ticks=10)]}]
        self.assertEqual(summarise({'samples': samples})['mean_cpu_percent_one_core_100'], {})

    def test_charging_temperature_and_truncation_scope(self):
        result = summarise({'truncated': True, 'samples': [{'elapsed_seconds': 0, 'children': [],
            'battery': [{'status': 'Charging'}], 'temperatures_millicelsius': [{'device': 'cpu', 'sensor': 'temp1', 'value': 45000}]}]})
        self.assertEqual(result['battery_statuses'], ['Charging'])
        self.assertEqual(result['host_peak_temperature_celsius'], {'cpu/temp1': 45})
        self.assertTrue(result['truncated'])
        self.assertNotIn('battery_life', result)

    def test_unreadable_and_malformed_sensor_is_absent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'sensor'
            self.assertIsNone(native_metrics.number(path))
            path.write_text('not a number')
            self.assertIsNone(native_metrics.number(path))

    def test_passive_identity_failure_does_not_abort_owned_spawn(self):
        observation = native_metrics.NativeMetrics()
        with patch.object(native_metrics.session_recovery, 'identity', side_effect=OSError):
            observation.add(type('Child', (), {'pid': 123})(), 'client')
        self.assertEqual(observation.children, [])


if __name__ == '__main__':
    unittest.main()
