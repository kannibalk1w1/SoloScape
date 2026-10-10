"""Bounded passive observations of our own native probe children and host sensors."""
import os
from pathlib import Path
import threading
import time
import session_recovery


def number(path):
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


class NativeMetrics:
    def __init__(self):
        self.children = []
        self.samples = []
        self.phases = []
        self.lock = threading.Lock()
        self.closed = threading.Event()
        self.started = time.monotonic()
        self.worker = threading.Thread(target=self.collect, name='private-native-metrics', daemon=True)

    def start(self):
        self.worker.start()

    def add(self, process, role):
        try:
            identity = session_recovery.identity(process.pid)
        except (OSError, ValueError):
            return  # Passive observation cannot lose the profile session's Popen handle.
        with self.lock:
            self.children.append((process, role, identity))

    def stage(self, stage):
        with self.lock:
            self.phases.append({'stage': stage, 'elapsed_seconds': round(time.monotonic() - self.started, 3)})

    def sample(self):
        result = {'elapsed_seconds': round(time.monotonic() - self.started, 3), 'children': []}
        with self.lock:
            children = list(self.children)
        for process, role, identity in children:
            if process.poll() is not None or not session_recovery.same_process(identity):
                continue
            try:
                base = Path('/proc') / str(process.pid)
                status = dict(line.split(':', 1) for line in (base / 'status').read_text().splitlines() if ':' in line)
                stat = (base / 'stat').read_text().rsplit(')', 1)[1].split()
                if not session_recovery.same_process(identity):
                    continue
                result['children'].append({'role': role, 'pid': process.pid, 'start': identity['start'],
                    'rss_kib': int(status['VmRSS'].split()[0]), 'cpu_ticks': int(stat[11]) + int(stat[12]),
                    'clock_ticks_per_second': os.sysconf('SC_CLK_TCK')})
            except (OSError, ValueError, KeyError):
                pass  # An exiting child or unavailable sensor is not a fabricated zero.
        result['battery'] = []
        for battery in Path('/sys/class/power_supply').glob('BAT*'):
            try:
                status = (battery / 'status').read_text().strip()
            except OSError:
                status = 'unavailable'
            result['battery'].append({'status': status, 'capacity_percent': number(battery / 'capacity'),
                'power_now_microwatts': number(battery / 'power_now'),
                'current_now_microamps': number(battery / 'current_now'),
                'voltage_now_microvolts': number(battery / 'voltage_now')})
        result['temperatures_millicelsius'] = []
        for device in Path('/sys/class/hwmon').glob('hwmon*'):
            try:
                name = (device / 'name').read_text().strip()
            except OSError:
                continue
            for sensor in device.glob('temp*_input'):
                value = number(sensor)
                if value is not None:
                    result['temperatures_millicelsius'].append({'device': name, 'sensor': sensor.name, 'value': value})
        result['gpu_busy_percent'] = [value for path in Path('/sys/class/drm').glob('card*/device/gpu_busy_percent')
                                      if (value := number(path)) is not None]
        return result

    def collect(self):
        while not self.closed.is_set():
            with self.lock:
                if len(self.samples) >= 1200:
                    break
            sample = self.sample()
            with self.lock:
                self.samples.append(sample)
            self.closed.wait(0.5)

    def finish(self):
        self.closed.set()
        self.worker.join(3)
        with self.lock:
            samples, phases = list(self.samples), list(self.phases)
        return {'method': '0.5-second owned PID/start RSS/CPU samples; host-wide sysfs sensors, not per-game GPU/power attribution. Xvfb uses software rendering. Charging power is not battery-life evidence.',
                'sample_count': len(samples), 'truncated': len(samples) >= 1200,
                'worker_alive': self.worker.is_alive(), 'phases': phases, 'samples': samples}
