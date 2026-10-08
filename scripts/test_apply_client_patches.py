#!/usr/bin/env python3
"""Checks stacked updates and preservation of conflicting user changes."""
import pathlib
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("apply_client_patches.py").resolve()
FIRST = """diff --git a/input.txt b/input.txt
new file mode 100644
--- /dev/null
+++ b/input.txt
@@ -0,0 +1 @@
+camera
"""
SECOND = """diff --git a/input.txt b/input.txt
--- a/input.txt
+++ b/input.txt
@@ -1 +1,2 @@
 camera
+movement
"""


class PatchStackTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="soloscape-stack-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.repo = self.root / "client"
        self.repo.mkdir()
        self.patches = [self.root / "first.patch", self.root / "second.patch"]
        self.patches[0].write_text(FIRST)
        self.patches[1].write_text(SECOND)

    def run_stack(self):
        return subprocess.run(["python3", str(SCRIPT), str(self.repo), *map(str, self.patches)], capture_output=True, text=True)

    def test_fresh_checkout_and_repeated_application(self):
        self.assertEqual(0, self.run_stack().returncode)
        expected = b"camera\nmovement\n"
        self.assertEqual(expected, (self.repo / "input.txt").read_bytes())
        result = self.run_stack()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, result.stdout.count("Already applied:"))
        self.assertEqual(expected, (self.repo / "input.txt").read_bytes())

    def test_upgrades_existing_camera_build(self):
        (self.repo / "input.txt").write_text("camera\n")
        result = self.run_stack()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Already applied: first.patch", result.stdout)
        self.assertIn("Applied: second.patch", result.stdout)
        self.assertEqual("camera\nmovement\n", (self.repo / "input.txt").read_text())

    def test_conflict_preserves_all_source_files(self):
        (self.repo / "input.txt").write_text("local changes\n")
        result = self.run_stack()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("preserved", result.stderr)
        self.assertEqual("local changes\n", (self.repo / "input.txt").read_text())
        self.assertEqual(["input.txt"], sorted(p.name for p in self.repo.iterdir()))


if __name__ == "__main__":
    unittest.main()
