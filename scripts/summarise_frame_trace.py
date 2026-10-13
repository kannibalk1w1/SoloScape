#!/usr/bin/env python3
"""Summarise native overlay-frame traces; these are not hardware presentation timestamps."""
import argparse
import csv
from collections import deque
import json
from pathlib import Path


def summarise(rows):
    intervals, windows = [], []
    window = deque()
    total = 0.0
    states = {}
    for row in rows:
        interval = float(row['interval_ms'])
        if interval <= 0:
            raise ValueError('Frame intervals must be positive')
        state = str(row['client_state'])
        states[state] = states.get(state, 0) + 1
        intervals.append(interval)
        window.append(interval)
        total += interval
        while len(window) > 1 and total - window[0] >= 5000:
            total -= window.popleft()
        if total >= 5000:
            windows.append(len(window) * 1000 / total)
    if not intervals:
        raise ValueError('Empty frame trace')
    ordered = sorted(intervals)
    seconds = sum(intervals) / 1000
    p99 = ordered[(len(ordered) - 1) * 99 // 100]
    return {'method': 'Native overlay frame intervals, including loading and UI. Rolling windows span at least five seconds; no hardware presentation attribution.',
            'seconds': seconds, 'frames': len(intervals), 'average_fps': len(intervals) / seconds,
            'p95_ms': ordered[(len(ordered) - 1) * 95 // 100], 'p99_ms': p99,
            'max_ms': ordered[-1], 'frames_over_20_ms': sum(x > 20 for x in intervals),
            'client_state_frame_counts': states,
            'minimum_rolling_5s_fps': min(windows) if windows else None,
            'rolling_windows_below_58': sum(x < 58 for x in windows),
            'duration_30_minutes_met': seconds >= 1800,
            'full_trace_p99_20ms_met': p99 <= 20,
            'full_trace_rolling_58fps_met': bool(windows) and min(windows) >= 58}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    args = parser.parse_args()
    with args.trace.open(newline='') as source:
        print(json.dumps(summarise(csv.DictReader(source)), indent=2))
