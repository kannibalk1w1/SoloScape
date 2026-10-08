"""Process lifecycle tests, using simulated JVMs without game data or Java."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

LAUNCHER = Path(__file__).with_name("local_dev.py")
FAKE_JAVA = '''#!/usr/bin/env python3
import os
from pathlib import Path
import signal
import sys
import time
root = Path(os.environ["TEST_ROOT"])
role = "server" if "void-server" in sys.argv[2] else "client"
(root / (role + ".pid")).write_text(str(os.getpid()))
def stop(*args):
    (root / (role + ".stopped")).write_text("graceful")
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
if role == "server":
    if os.environ["TEST_CASE"] == "server-failure":
        sys.exit(7)
    if os.environ["TEST_CASE"] != "timeout":
        time.sleep(0.15)
        (root / "world-ready").write_text("ready")
        print("[Main] Void loaded in 150ms", flush=True)
else:
    if not (root / "world-ready").exists():
        sys.exit(8)
    (root / "client.args").write_text(" ".join(sys.argv))
    if os.environ["TEST_CASE"] == "client-exit":
        sys.exit(3)
while True:
    time.sleep(0.05)
'''


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="soloscape-test-")
        self.root = Path(self.temp.name)
        for role, name in (("game-server/game", "void-server-dev.jar"), ("runelite-client/client", "void-client-test.jar")):
            libs = self.root / "upstream" / role / "build/libs"
            libs.mkdir(parents=True)
            (libs / name).touch()
        self.java = self.root / "java"
        self.java.write_text(FAKE_JAVA)
        self.java.chmod(0o755)
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        self.temp.cleanup()

    def start(self, case):
        # Bypass only doctor/build; exercise real process ownership/readiness/cleanup.
        harness = f'''
import importlib.util
import signal
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("local_dev", {str(LAUNCHER)!r})
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.ROOT = Path({str(self.root)!r})
m.SERVER = m.ROOT / "upstream/game-server"
m.CLIENT = m.ROOT / "upstream/runelite-client"
m.RUNTIME = m.ROOT / ".runtime"
m.READY_TIMEOUT = 0.4 if {case!r} == "timeout" else 3
m.doctor = lambda: True
signal.signal(signal.SIGTERM, m.interrupted)
try:
    sys.exit(m.launch(skip_build=True))
except KeyboardInterrupt:
    sys.exit(130)
except RuntimeError as e:
    sys.exit(str(e))
'''
        env = os.environ.copy()
        env.update(SERVER_JAVA=str(self.java), CLIENT_JAVA=str(self.java), TEST_ROOT=str(self.root), TEST_CASE=case)
        process = subprocess.Popen([sys.executable, "-c", harness], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.processes.append(process)
        return process

    def finish(self, process):
        output, _ = process.communicate(timeout=6)
        for role in ("server", "client"):
            pid_file = self.root / f"{role}.pid"
            if pid_file.exists():
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(pid_file.read_text()), 0)
        return output

    def test_client_exit_stops_server_and_uses_localhost(self):
        process = self.start("client-exit")
        output = self.finish(process)
        self.assertEqual(process.returncode, 3, output)
        self.assertEqual((self.root / "server.stopped").read_text(), "graceful")
        self.assertIn("--address 127.0.0.1 --port 43594", (self.root / "client.args").read_text())
        self.assertIn("Void loaded in 150ms", output)

    def test_server_failure_never_starts_client(self):
        process = self.start("server-failure")
        output = self.finish(process)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("Server exited during startup", output)
        self.assertFalse((self.root / "client.pid").exists())

    def test_readiness_timeout_stops_server(self):
        process = self.start("timeout")
        output = self.finish(process)
        self.assertIn("readiness timed out", output)
        self.assertEqual((self.root / "server.stopped").read_text(), "graceful")
        self.assertFalse((self.root / "client.pid").exists())

    def test_interrupt_stops_both_children(self):
        process = self.start("interrupt")
        deadline = time.monotonic() + 4
        while not (self.root / "client.args").exists():
            if process.poll() is not None or time.monotonic() > deadline:
                self.fail("Simulated client never started")
            time.sleep(0.02)
        process.send_signal(signal.SIGTERM)
        output = self.finish(process)
        self.assertEqual(process.returncode, 130, output)
        for role in ("server", "client"):
            self.assertEqual((self.root / f"{role}.stopped").read_text(), "graceful")


if __name__ == "__main__":
    unittest.main()
