#!/usr/bin/env python3
"""Record XWayland Present completions from explicit windows or an owned Java game PID.

Following a PID tracks the full-size native GL child across toolkit changes. Each
window lifetime has its own epoch. Software-map drawing is not measured by Present;
unobserved gaps must never be interpreted as a continuous presentation stream.
https://xcb.freedesktop.org/manual/group__XCB__Present__API.html
"""
import argparse
import csv
import ctypes as C
import ctypes.util
import json
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import time


class Cookie(C.Structure):
    _fields_ = [('sequence', C.c_uint)]


class Complete(C.Structure):
    # XCB inserts full_sequence after the wire event's first 32 bytes.
    _layout_ = "ms"  # Explicit packed layout; no bitfields, matching the XCB packed C event.
    _pack_ = 1
    _fields_ = [('response', C.c_uint8), ('extension', C.c_uint8),
                ('sequence', C.c_uint16), ('length', C.c_uint32),
                ('event_type', C.c_uint16), ('kind', C.c_uint8), ('mode', C.c_uint8),
                ('event', C.c_uint32), ('window', C.c_uint32), ('serial', C.c_uint32),
                ('ust', C.c_uint64), ('full_sequence', C.c_uint32), ('msc', C.c_uint64)]


class Destroy(C.Structure):
    _fields_ = [('response', C.c_uint8), ('pad', C.c_uint8), ('sequence', C.c_uint16),
                ('event', C.c_uint32), ('window', C.c_uint32)]


def native_bindings():
    libraries = [ctypes.util.find_library(name) for name in ('xcb', 'xcb-present', 'c')]
    if not all(libraries):
        raise RuntimeError('libxcb, libxcb-present and libc are required')
    xcb, present, libc = (C.CDLL(name) for name in libraries)
    signatures = {
        'xcb_connect': ([C.c_char_p, C.POINTER(C.c_int)], C.c_void_p),
        'xcb_connection_has_error': ([C.c_void_p], C.c_int),
        'xcb_generate_id': ([C.c_void_p], C.c_uint32),
        'xcb_request_check': ([C.c_void_p, Cookie], C.c_void_p),
        'xcb_change_window_attributes_checked': ([C.c_void_p, C.c_uint32, C.c_uint32, C.POINTER(C.c_uint32)], Cookie),
        'xcb_flush': ([C.c_void_p], C.c_int),
        'xcb_get_file_descriptor': ([C.c_void_p], C.c_int),
        'xcb_poll_for_event': ([C.c_void_p], C.c_void_p),
        'xcb_disconnect': ([C.c_void_p], None),
    }
    for name, (arguments, result) in signatures.items():
        getattr(xcb, name).argtypes = arguments
        getattr(xcb, name).restype = result
    libc.free.argtypes = [C.c_void_p]
    present.xcb_present_select_input_checked.argtypes = [C.c_void_p, C.c_uint32, C.c_uint32, C.c_uint32]
    present.xcb_present_select_input_checked.restype = Cookie
    return xcb, present, libc


def process_start(pid):
    return (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19]


def game_windows(display, pid):
    """Read only the full-size Java frame owned by the supplied PID, then its GL child."""
    env = dict(os.environ, DISPLAY=display)
    tree = subprocess.check_output(['xwininfo', '-root', '-tree'], env=env, text=True, timeout=3)
    lines = tree.splitlines()
    for index, line in enumerate(lines):
        if 'sun-awt-X11-XFramePeer' not in line or '1280x800' not in line:
            continue
        frame = re.search(r'0x[0-9a-f]+', line).group()
        property_text = subprocess.check_output(['xprop', '-id', frame, '_NET_WM_PID'], env=env, text=True, timeout=3)
        if not re.search(r'=\s*' + str(pid) + r'\s*$', property_text):
            continue
        indentation = len(line) - len(line.lstrip())
        canvas = False
        for child in lines[index+1:]:
            if child.strip() and len(child)-len(child.lstrip()) <= indentation:
                break
            if 'sun-awt-X11-XCanvasPeer' in child and '1280x800' in child:
                canvas = True
            elif canvas and '(has no name)' in child and '1280x800' in child:
                return {int(re.search(r'0x[0-9a-f]+', child).group(), 16)}
        return set()
    return set()


def record(args):
    xcb, present, libc = native_bindings()
    conn = xcb.xcb_connect(args.display.encode(), None)
    stopped = False
    def stop(_signal, _frame):
        nonlocal stopped
        stopped = True
    previous_handler = signal.signal(signal.SIGTERM, stop)
    count = epoch = 0
    active = {}
    started = time.monotonic()
    next_scan = 0.0
    try:
        identity = process_start(args.follow_pid) if args.follow_pid else None
        if xcb.xcb_connection_has_error(conn):
            raise RuntimeError('XCB connection failed')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as output:
            writer = csv.writer(output)
            writer.writerow(['observer_ns', 'window', 'kind', 'mode', 'ust_us', 'msc', 'serial', 'epoch'])
            while not stopped and time.monotonic()-started < args.seconds:
                now = time.monotonic()
                if now >= next_scan:
                    next_scan = now+1
                    if args.follow_pid:
                        try:
                            if process_start(args.follow_pid) != identity:
                                break
                            windows = game_windows(args.display, args.follow_pid)
                        except FileNotFoundError:
                            break
                        except (OSError, subprocess.SubprocessError):
                            windows = set()
                    else:
                        windows = set(args.window)
                    # Deleting our event context prevents duplicates and permits recycled IDs.
                    for window in set(active)-windows:
                        event_id, _epoch = active.pop(window)
                        error = xcb.xcb_request_check(conn, present.xcb_present_select_input_checked(conn, event_id, window, 0))
                        if error:
                            libc.free(error)  # The native window may already have been destroyed.
                    for window in windows-set(active):
                        event_id = xcb.xcb_generate_id(conn)
                        error = xcb.xcb_request_check(conn, present.xcb_present_select_input_checked(conn, event_id, window, 2))
                        if error:
                            libc.free(error)
                            continue  # A toolkit switch can destroy the window during discovery.
                        # StructureNotify detects recreation even if the software-map interval
                        # falls entirely between discovery polls and the numeric ID is recycled.
                        mask = C.c_uint32(1 << 17)
                        error = xcb.xcb_request_check(conn, xcb.xcb_change_window_attributes_checked(conn, window, 1 << 11, C.byref(mask)))
                        if error:
                            libc.free(error)
                            continue
                        epoch += 1
                        active[window] = (event_id, epoch)
                    xcb.xcb_flush(conn)
                    output.flush()
                ptr = xcb.xcb_poll_for_event(conn)
                if not ptr:
                    if xcb.xcb_connection_has_error(conn):
                        raise RuntimeError('XCB connection closed during capture')
                    select.select([xcb.xcb_get_file_descriptor(conn)], [], [], .1)
                    continue
                try:
                    event = C.cast(ptr, C.POINTER(Complete)).contents
                    if event.response & 127 == 17:
                        destroyed = C.cast(ptr, C.POINTER(Destroy)).contents.window
                        active.pop(destroyed, None)
                        next_scan = 0
                    elif event.response & 127 == 35 and event.event_type == 1 and event.window in active and event.event == active[event.window][0]:
                        writer.writerow([time.monotonic_ns(), hex(event.window), event.kind, event.mode,
                                         event.ust, event.msc, event.serial, active[event.window][1]])
                        count += 1
                finally:
                    libc.free(ptr)
        return {'complete_events': count, 'epochs': epoch, 'requested_seconds': args.seconds,
                'observed_wall_seconds': time.monotonic()-started, 'stopped': stopped,
                'output': str(args.output), 'method': 'Separate XWayland GL window lifetimes; software-map frames and physical panel scanout are not measured.'}
    finally:
        xcb.xcb_disconnect(conn)
        signal.signal(signal.SIGTERM, previous_handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--display', required=True)
    parser.add_argument('--seconds', type=float, default=60)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--window', type=lambda value: int(value, 0), action='append')
    source.add_argument('--follow-pid', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('Seconds must be 1–3600.')
    if args.window and (len(args.window)>16 or any(window<=0 or window>0xffffffff for window in args.window)):
        parser.error('Supply 1–16 valid window IDs.')
    if args.follow_pid is not None and args.follow_pid<=0:
        parser.error('Supply a positive owned game PID.')
    print(json.dumps(record(args)))


if __name__ == '__main__':
    main()
