"""Catch omitted native hooks and changed contents, using an isolated real Git repo."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from verify_patches import verify


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        def git(*args):
            return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        self.git = git
        git("init", "--quiet")
        git("config", "user.name", "Patch test")
        git("config", "user.email", "patch-test@example.invalid")
        (self.repo / "Hook.java").write_text("old hook\n")
        git("add", ".")
        git("commit", "--quiet", "-m", "base")
        (self.repo / "Hook.java").write_text("new hook\n")
        self.patch = self.root / "0001.patch"
        self.patch.write_bytes(git("diff", "HEAD").stdout)

    def test_exact_export_passes_and_verification_does_not_change_source(self):
        before = self.git("status", "--porcelain").stdout
        self.assertEqual(1, verify(self.repo, [self.patch]))
        self.assertEqual(before, self.git("status", "--porcelain").stdout)
        self.assertEqual("new hook\n", (self.repo / "Hook.java").read_text())

    def test_missing_tracked_or_new_hook_fails(self):
        with self.assertRaisesRegex(ValueError, "Hook.java"):
            verify(self.repo, [])
        (self.repo / "NewAdapter.java").write_text("unexported source\n")
        with self.assertRaisesRegex(ValueError, "NewAdapter.java"):
            verify(self.repo, [self.patch])

    def test_changed_content_of_already_exported_file_fails(self):
        (self.repo / "Hook.java").write_text("later changed hook\n")
        with self.assertRaisesRegex(ValueError, "Hook.java"):
            verify(self.repo, [self.patch])


if __name__ == "__main__":
    unittest.main()
