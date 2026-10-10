#!/usr/bin/env python3
"""Summarise private native-probe samples without conflating charging power with runtime."""
import argparse
import json
from pathlib import Path


def summarise(observation):
    peaks = {}
    previous = {}
    cpu = {}
    combined = 0
    sensors = {}
    batteries = set()
    samples = observation['samples']
    for sample in samples:
        combined = max(combined, sum(child['rss_kib'] for child in sample['children']))
        elapsed = sample['elapsed_seconds']
        for child in sample['children']:
            role = child['role']
            peaks[role] = max(peaks.get(role, 0), child['rss_kib'])
            identity = (role, child['pid'], child['start'])
            if identity in previous:
                last_time, last_ticks = previous[identity]
                delta = child['cpu_ticks'] - last_ticks
                duration = elapsed - last_time
                if duration > 0 and delta >= 0:
                    seconds, measured = cpu.get(role, (0.0, 0.0))
                    cpu[role] = (seconds + delta / child['clock_ticks_per_second'], measured + duration)
            previous[identity] = (elapsed, child['cpu_ticks'])
        for battery in sample.get('battery', []):
            batteries.add(battery['status'])
        for sensor in sample.get('temperatures_millicelsius', []):
            key = sensor['device'] + '/' + sensor['sensor']
            sensors[key] = max(sensors.get(key, sensor['value']), sensor['value'])
    return {'sample_count': len(samples), 'truncated': observation.get('truncated', False),
            'worker_alive': observation.get('worker_alive', False),
            'peak_rss_mib_by_role': {key: round(value / 1024, 2) for key, value in peaks.items()},
            'peak_combined_rss_mib': round(combined / 1024, 2),
            'mean_cpu_percent_one_core_100': {key: round(seconds / duration * 100, 2) for key, (seconds, duration) in cpu.items() if duration > 0},
            'host_peak_temperature_celsius': {key: round(value / 1000, 2) for key, value in sensors.items()},
            'battery_statuses': sorted(batteries), 'phases': observation.get('phases', []),
            'scope': 'Whole observed session including startup/login/UI/save; CPU samples stay within each PID/start identity. Host-wide temperature. No battery-life, GPU or Gaming Mode budget.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    options = parser.parse_args()
    print(json.dumps({path.name: summarise(json.loads(path.read_text())) for path in options.files}, indent=2))
