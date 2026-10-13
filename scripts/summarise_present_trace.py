#!/usr/bin/env python3
"""Summarise per-window XWayland presentation completions, preserving skipped requests."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from summarise_frame_trace import summarise as summarise_intervals


def summarise(rows):
    windows = defaultdict(lambda: {'timestamps': [], 'skipped_requests': 0, 'duplicate_completions': 0})
    for row in rows:
        if int(row['kind']) != 0:  # NotifyMSC measures the clock, not a presented game frame.
            continue
        name = row['window'] + ('@'+str(row['epoch']) if row.get('epoch') else '')
        window = windows[name]
        if int(row['mode']) == 2:  # PresentCompleteModeSkip was never displayed.
            window['skipped_requests'] += 1
            continue
        timestamp = int(row['ust_us'])
        if timestamp <= 0:
            raise ValueError('Presentation timestamps must be positive')
        times = window['timestamps']
        if times and timestamp < times[-1]:
            raise ValueError('Presentation timestamps decreased within one window')
        if times and timestamp == times[-1]:
            window['duplicate_completions'] += 1
        else:
            times.append(timestamp)
    result = {}
    for name, window in windows.items():
        times = window.pop('timestamps')
        values = dict(window, completions=len(times))
        if len(times) >= 2:
            values.update(summarise_intervals({'interval_ms': (b-a)/1000, 'client_state': 'present'}
                                              for a, b in zip(times, times[1:])))
            values.pop('client_state_frame_counts')
            values.pop('method')
        result[name] = values
    return {'method': 'Per-window/lifetime XWayland Present pixmap completion UST intervals; skipped requests and duplicate timestamps do not count as delivered frames. Not physical panel scanout.',
            'windows': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    args = parser.parse_args()
    with args.trace.open(newline='') as source:
        print(json.dumps(summarise(csv.DictReader(source)), indent=2))
