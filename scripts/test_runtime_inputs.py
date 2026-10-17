"""Boundary tests for experiments/native-prebuilt-server/runtime_inputs.py.

Every repo is a temporary fake git repo; nothing in the real tree is touched.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "native-prebuilt-server"))

import runtime_inputs  # noqa: E402
from runtime_inputs import RuntimeInputError, collect_data  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(root: Path) -> dict[str, tuple[bytes | str, int]]:
    """Map every path under root to (content-or-link-target, mtime_ns)."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                out[rel] = (os.readlink(full), os.lstat(full).st_mtime_ns)
            elif full.is_file():
                out[rel] = (full.read_bytes(), full.stat().st_mtime_ns)
    return out


class FakeRepo:
    def __init__(
        self, tmp: Path, files: dict[str, bytes], tracked: list[str], name: str = "repo"
    ):
        self.root = tmp / name
        self.root.mkdir()
        for rel, data in files.items():
            self.write(rel, data)
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        if tracked:
            subprocess.run(
                ["git", "-C", str(self.root), "add", "--", *tracked], check=True
            )

    def write(self, rel: str, data: bytes) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def write_patch(tmp: Path, body: str, name: str = "stack.patch") -> Path:
    path = tmp / name
    path.write_text(body, encoding="utf-8")
    return path


def modify(path: str, old: str, new: str, extra: str = "") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -1,1 +1,1 @@\n"
        f"-{old}\n"
        f"+{new}\n" + extra
    )


class RuntimeInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_tracked_and_patch_sources_selected_with_metadata(self) -> None:
        keep = b'name = "keep"\n'
        repo = FakeRepo(
            self.tmp,
            {
                "data/a.toml": b"a = 1\n",
                "data/sub/b.txt": b"b\n",
                "data/new/c.toml": b"c = 3\n",  # patch-added, untracked
            },
            ["data/a.toml", "data/sub/b.txt"],
        )
        repo.write("data/a.toml", keep)  # worktree text differs from patch view
        patch = write_patch(
            self.tmp,
            "diff --git a/data/new/c.toml b/data/new/c.toml\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/data/new/c.toml\n"
            "@@ -0,0 +1,1 @@\n"
            "+c = 3\n"
            + modify("data/a.toml", 'name = "keep"', 'name = "keep"'),
        )
        got = collect_data(repo.root, [patch])
        self.assertEqual(
            got,
            [
                {"path": "data/a.toml", "sha256": sha(keep), "size": len(keep)},
                {"path": "data/new/c.toml", "sha256": sha(b"c = 3\n"), "size": 6},
                {"path": "data/sub/b.txt", "sha256": sha(b"b\n"), "size": 2},
            ],
        )
        self.assertTrue(all(set(d) == {"path", "sha256", "size"} for d in got))

    def test_private_tracked_and_untracked_never_opened_or_mutated(self) -> None:
        repo = FakeRepo(
            self.tmp,
            {
                "data/keep.toml": b"k\n",
                "data/extra.toml": b"CANARY-UNTRACKED\n",
                "data/saves/slot.txt": b"CANARY-SAVE\n",
                "data/cache/art.txt": b"CANARY-CACHE\n",
            },
            ["data/keep.toml", "data/saves/slot.txt", "data/cache/art.txt"],
        )
        # A broken symlink would make any lstat/open raise. Private paths are
        # excluded before inspection, so this must still succeed.
        os.symlink(self.tmp / "missing-target", repo.root / "data" / "errors")
        os.makedirs(repo.root / "data" / "logs")
        os.symlink(self.tmp / "missing-logs-target", repo.root / "data" / "logs" / "x.txt")
        subprocess.run(
            ["git", "-C", str(repo.root), "add", "--", "data/logs/x.txt"], check=True
        )
        patch = write_patch(
            self.tmp,
            "diff --git a/data/exchange/e.txt b/data/exchange/e.txt\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/data/exchange/e.txt\n"
            "@@ -0,0 +1,1 @@\n"
            "+CANARY-EXCHANGE\n"
            "diff --git a/data/.temp/t.toml b/data/.temp/t.toml\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/data/.temp/t.toml\n"
            "@@ -0,0 +1,1 @@\n"
            "+CANARY-TEMP\n",
        )
        before = snapshot(repo.root)
        got = collect_data(repo.root, [patch])
        self.assertEqual([d["path"] for d in got], ["data/keep.toml"])
        self.assertEqual(snapshot(repo.root), before)
        self.assertNotIn("CANARY", repr(got))

    def test_patch_deletion_and_rename_drop_old_path_without_requiring_it(self) -> None:
        repo = FakeRepo(
            self.tmp,
            {"data/old.toml": b"old\n", "data/keep.toml": b"keep\n", "data/ren.toml": b"r\n"},
            ["data/old.toml", "data/keep.toml", "data/ren.toml"],
        )
        os.remove(repo.root / "data" / "old.toml")  # deleted by a later patch
        os.remove(repo.root / "data" / "ren.toml")  # renamed away
        repo.write("data/moved.toml", b"r\n")
        patch = write_patch(
            self.tmp,
            "diff --git a/data/old.toml b/data/old.toml\n"
            "deleted file mode 100644\n"
            "--- a/data/old.toml\n"
            "+++ /dev/null\n"
            "@@ -1,1 +0,0 @@\n"
            "-old\n"
            "diff --git a/data/ren.toml b/data/moved.toml\n"
            "similarity index 100%\n"
            "rename from data/ren.toml\n"
            "rename to data/moved.toml\n"
            "--- a/data/ren.toml\n"
            "+++ b/data/moved.toml\n",
        )
        got = collect_data(repo.root, [patch])
        self.assertEqual([d["path"] for d in got], ["data/keep.toml", "data/moved.toml"])

    def test_hunk_body_lines_are_not_treated_as_headers(self) -> None:
        repo = FakeRepo(
            self.tmp,
            {"data/a.toml": b"a\ny = 2\n", "data/victim.toml": b"v\n"},
            ["data/a.toml", "data/victim.toml"],
        )
        # The removed content line "-- a/data/victim.toml" reads as a header
        # if the hunk body is not skipped; the added "++ b/data/ghost.toml"
        # line is content too and ghost.toml does not exist.
        patch = write_patch(
            self.tmp,
            "diff --git a/data/a.toml b/data/a.toml\n"
            "--- a/data/a.toml\n"
            "+++ b/data/a.toml\n"
            "@@ -1,2 +1,2 @@\n"
            "-a\n"
            "+a2\n"
            " y = 2\n"
            "@@ -5,2 +5,2 @@\n"
            "--- a/data/victim.toml\n"
            "+++ b/data/ghost.toml\n"
            " y = 2\n",
        )
        got = collect_data(repo.root, [patch])
        self.assertEqual([d["path"] for d in got], ["data/a.toml", "data/victim.toml"])

    def test_selected_file_symlink_refused(self) -> None:
        repo = FakeRepo(self.tmp, {"data/real.toml": b"r\n"}, ["data/real.toml"])
        outside = self.tmp / "outside.toml"
        outside.write_bytes(b"secret\n")
        (repo.root / "data" / "real.toml").unlink()
        os.symlink(outside, repo.root / "data" / "real.toml")
        with self.assertRaises(RuntimeInputError):
            collect_data(repo.root, [])

    def test_ancestor_symlink_refused_for_tracked_and_patch_added(self) -> None:
        repo = FakeRepo(
            self.tmp,
            {"data/real/x.toml": b"x\n", "data/elsewhere/y.toml": b"y\n"},
            ["data/real/x.toml"],
        )
        shutil.rmtree(repo.root / "data" / "real")
        os.symlink(repo.root / "data" / "elsewhere", repo.root / "data" / "real")
        with self.assertRaises(RuntimeInputError):
            collect_data(repo.root, [])

        repo2 = FakeRepo(self.tmp, {"data/dir/z.toml": b"z\n"}, [], name="repo2")
        os.symlink(repo2.root / "data" / "dir", repo2.root / "data" / "alias")
        patch = write_patch(
            self.tmp,
            "diff --git a/data/alias/z.toml b/data/alias/z.toml\n"
            "--- /dev/null\n"
            "+++ b/data/alias/z.toml\n"
            "@@ -0,0 +1,1 @@\n"
            "+z\n",
        )
        with self.assertRaises(RuntimeInputError):
            collect_data(repo2.root, [patch])

    def test_unsafe_patch_paths_refused(self) -> None:
        repo = FakeRepo(self.tmp, {"data/ok.toml": b"o\n"}, ["data/ok.toml"])
        bad_names = [
            "data/../escape.toml",
            "data//double.toml",
            "data/./dot.toml",
            "data/",
            "data\\win.toml",
            "data/nul\x00.toml",
            "/data/abs.toml",
            "data/quoted\".toml",
        ]
        for name in bad_names:
            with self.subTest(name=name):
                patch = write_patch(
                    self.tmp,
                    "diff --git a/x b/x\n--- /dev/null\n"
                    f"+++ b/{name}\n@@ -0,0 +1,1 @@\n+x\n",
                )
                with self.assertRaises(RuntimeInputError):
                    collect_data(repo.root, [patch])

    def test_unknown_extension_refused_tracked_or_patched(self) -> None:
        repo = FakeRepo(
            self.tmp,
            {"data/art/icon.png": b"\x89PNG", "data/new/model.bin": b"\x00"},
            ["data/art/icon.png"],
        )
        with self.assertRaises(RuntimeInputError):
            collect_data(repo.root, [])
        patch = write_patch(
            self.tmp,
            "diff --git a/data/new/model.bin b/data/new/model.bin\n"
            "--- /dev/null\n+++ b/data/new/model.bin\n@@ -0,0 +1,1 @@\n+x\n",
        )
        shutil.rmtree(repo.root / "data" / "art")
        subprocess.run(["git", "-C", str(repo.root), "rm", "-q", "--cached", "-r", "data/art"], check=True)
        with self.assertRaises(RuntimeInputError):
            collect_data(repo.root, [patch])

    def test_missing_expected_source_refused(self) -> None:
        repo = FakeRepo(self.tmp, {"data/gone.toml": b"g\n"}, ["data/gone.toml"])
        os.remove(repo.root / "data" / "gone.toml")
        with self.assertRaises(RuntimeInputError):
            collect_data(repo.root, [])

        patch = write_patch(
            self.tmp,
            "diff --git a/data/never.toml b/data/never.toml\n"
            "--- /dev/null\n+++ b/data/never.toml\n@@ -0,0 +1,1 @@\n+n\n",
        )
        with self.assertRaises(RuntimeInputError):
            collect_data(repo.root, [patch])

    def test_size_count_and_total_caps(self) -> None:
        repo = FakeRepo(
            self.tmp,
            {"data/one.toml": b"0123456789A", "data/two.toml": b"0123456789"},
            ["data/one.toml", "data/two.toml"],
        )
        with mock.patch.object(runtime_inputs, "MAX_FILE_BYTES", 10):
            with self.assertRaises(RuntimeInputError):
                collect_data(repo.root, [])
        with mock.patch.object(runtime_inputs, "MAX_TOTAL_BYTES", 15):
            with self.assertRaises(RuntimeInputError):
                collect_data(repo.root, [])
        with mock.patch.object(runtime_inputs, "MAX_FILES", 1):
            with self.assertRaises(RuntimeInputError):
                collect_data(repo.root, [])

    def test_malformed_patch_refused(self) -> None:
        repo = FakeRepo(self.tmp, {"data/ok.toml": b"o\n"}, ["data/ok.toml"])
        bodies = [
            # new-side header with no old-side header
            "+++ b/data/ok.toml\n",
            # hunk counts exceed the body
            "--- a/data/ok.toml\n+++ b/data/ok.toml\n@@ -1,3 +1,3 @@\n-a\n",
            # hunk body line with an unknown tag
            "--- a/data/ok.toml\n+++ b/data/ok.toml\n@@ -1,1 +1,1 @@\n?x\n",
        ]
        for body in bodies:
            with self.subTest(body=body[:30]):
                with self.assertRaises(RuntimeInputError):
                    collect_data(repo.root, [write_patch(self.tmp, body)])


if __name__ == "__main__":
    unittest.main()
