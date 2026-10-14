#!/usr/bin/env python3
"""Attribute native overlay-frame stalls to route steps and client loading state (11); not presentation timing."""
import argparse
import csv
import json
from pathlib import Path


POSITION_FIELDS = ('tile_x', 'tile_y', 'plane', 'scene_base_x', 'scene_base_y')
PHASE_FIELDS = ('logic_cycles_delta', 'logic_ms_delta', 'plugins_ms_delta', 'overlay_paint_ms_delta',
                'overlay_upload_ms_delta', 'frame_ms_delta', 'event_queue_ms_delta', 'present_ms_delta', 'gc_ms_delta')
OPTIONAL_FIELDS = POSITION_FIELDS + ('renderer',) + PHASE_FIELDS
TOP_STALLS = 20
JITTER_MIN_MS = 20
FRAME_MS = 1000 / 60
PHASE_NOTE = ('Phase and GC values are completed cumulative-counter deltas between overlay callbacks, not same-frame '
              'durations. Phases overlap and FRAME/PRESENT completion can cross a callback boundary, so they must not '
              'be summed into a causal total; GC is coarse collection time with no per-event timestamp or cause.')


def _optional(row, name):
    """Return the measurement, or None when the column is absent/blank (never a guessed default)."""
    value = row.get(name)
    if value is None or str(value).strip() == '':
        return None
    if name == 'renderer':
        return str(value)
    try:
        number = float(value)
    except ValueError:
        return str(value)
    return int(number) if number.is_integer() and name in POSITION_FIELDS + ('logic_cycles_delta',) else number


def _percentile(values, pct):
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) * pct // 100] if ordered else None


def _band(values, floor_ms=FRAME_MS):
    return {'frames': len(values), 'excess_ms_over_16_7': round(sum(v - floor_ms for v in values), 1),
            'p50_ms': _percentile(values, 50), 'p99_ms': _percentile(values, 99), 'max_ms': max(values, default=None)}


def analyse(rows, stall_ms=300, window=5, floor_ms=100):
    rows = list(rows)
    if not rows:
        raise ValueError('Empty frame trace')
    raw = rows
    rows = [(r['step'], float(r['interval_ms']), str(r['client_state'])) for r in raw]
    loading = [i for i, r in enumerate(rows) if r[2] == '11']
    stalls = [i for i, r in enumerate(rows) if r[1] >= stall_ms]
    offsets = {}
    for i in stalls:
        if loading:
            nearest = min(loading, key=lambda j: abs(i - j))
            if abs(i - nearest) <= window:
                offsets[i - nearest] = offsets.get(i - nearest, 0) + 1
    per_step = {}
    for i in stalls:
        per_step.setdefault(rows[i][0], []).append(round(rows[i][1], 1))
    ordered = sorted(r[1] for r in rows if r[1] < floor_ms)
    present = [f for f in OPTIONAL_FIELDS if any(f in r for r in raw)]
    worst = []
    for i in sorted(stalls, key=lambda k: (-rows[k][1], k))[:TOP_STALLS]:
        near = [j for j in loading if abs(i - j) <= window]
        entry = {'frame_index': i, 'step': rows[i][0], 'interval_ms': round(rows[i][1], 1),
                 'client_state': rows[i][2],
                 'loading_state_offset': (i - min(near, key=lambda j: abs(i - j))) if near else None}
        if 'elapsed_ns' in raw[i]:
            entry['elapsed_ns'] = raw[i]['elapsed_ns']
        for f in OPTIONAL_FIELDS:
            if f in present:
                entry[f] = _optional(raw[i], f)
        worst.append(entry)
    jitter = [r[1] for r in rows if JITTER_MIN_MS <= r[1] < floor_ms]
    result = {'frames': len(rows), 'stall_threshold_ms': stall_ms, 'stalls': len(stalls),
              'loading_state_frames': len(loading),
              'stalls_near_loading_state': sum(any(abs(i - j) <= window for j in loading) for i in stalls),
              'stall_offset_from_loading_frame': dict(sorted(offsets.items())),
              'stall_steps': per_step,
              'excess_ms_from_stalls_over_floor': sum(r[1] - FRAME_MS for r in rows if r[1] >= floor_ms),
              'frames_over_20_ms_below_floor': sum(20 < r[1] < floor_ms for r in rows),
              'p99_ms_excluding_stalls_over_floor': ordered[(len(ordered) - 1) * 99 // 100] if ordered else None,
              'schema_optional_columns_present': present,
              'interval_bands': {
                  'steady_jitter_20_to_100ms': _band(jitter),
                  'stalls_at_or_above_threshold': _band([rows[i][1] for i in stalls]),
                  'between_floor_and_threshold': _band([r[1] for r in rows if floor_ms <= r[1] < stall_ms])},
              'worst_stalls': worst}
    if any(f in present for f in PHASE_FIELDS):
        result['phase_note'] = PHASE_NOTE
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--stall-ms', type=float, default=300)
    args = parser.parse_args()
    with args.trace.open(newline='') as source:
        print(json.dumps(analyse(csv.DictReader(source), args.stall_ms), indent=2))
