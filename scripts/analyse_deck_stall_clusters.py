#!/usr/bin/env python3
"""Attribute native overlay-frame stalls to route steps and client loading state (11); not presentation timing."""
import argparse
import csv
import json
from pathlib import Path


def analyse(rows, stall_ms=300, window=5, floor_ms=100):
    rows = [(r['step'], float(r['interval_ms']), str(r['client_state'])) for r in rows]
    if not rows:
        raise ValueError('Empty frame trace')
    loading = [i for i, r in enumerate(rows) if r[2] == '11']
    stalls = [i for i, r in enumerate(rows) if r[1] >= stall_ms]
    per_step = {}
    for i in stalls:
        per_step.setdefault(rows[i][0], []).append(round(rows[i][1], 1))
    ordered = sorted(r[1] for r in rows if r[1] < floor_ms)
    return {'frames': len(rows), 'stall_threshold_ms': stall_ms, 'stalls': len(stalls),
            'loading_state_frames': len(loading),
            'stalls_near_loading_state': sum(any(abs(i - j) <= window for j in loading) for i in stalls),
            'stall_steps': per_step,
            'excess_ms_from_stalls_over_floor': sum(r[1] - 1000 / 60 for r in rows if r[1] >= floor_ms),
            'frames_over_20_ms_below_floor': sum(20 < x < floor_ms for x in (r[1] for r in rows)),
            'p99_ms_excluding_stalls_over_floor': ordered[(len(ordered) - 1) * 99 // 100] if ordered else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--stall-ms', type=float, default=300)
    args = parser.parse_args()
    with args.trace.open(newline='') as source:
        print(json.dumps(analyse(csv.DictReader(source), args.stall_ms), indent=2))
