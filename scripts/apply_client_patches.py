#!/usr/bin/env python3
"""Validate a patch stack against a disposable copy before extending the checkout."""
import pathlib
import shutil
import subprocess
import sys
import tempfile


def apply(cwd, patch, reverse=False, check=False):
    args = ["git", "apply"]
    if reverse:
        args.append("--reverse")
    if check:
        args.append("--check")
    return subprocess.run(args + [str(patch)], cwd=cwd, capture_output=True, text=True)


def main():
    repo = pathlib.Path(sys.argv[1]).resolve()
    patches = [pathlib.Path(p).resolve() for p in sys.argv[2:]]
    paths = set()
    for patch in patches:
        stats = subprocess.check_output(["git", "apply", "--numstat", "-z", str(patch)], cwd=repo)
        for record in stats.split(b"\0"):
            if record:
                name = pathlib.PurePosixPath(record.decode().split("\t", 2)[2])
                if name.is_absolute() or ".." in name.parts:
                    raise ValueError(f"Unsafe patch path: {name}")
                paths.add(name)
    # A later patch can edit files created by an earlier one. Undo applied prefixes
    # sequentially in a disposable tree, then validate the complete forward stack.
    for prefix in range(len(patches), -1, -1):
        with tempfile.TemporaryDirectory(prefix="soloscape-patches-") as scratch:
            tree = pathlib.Path(scratch)
            for name in paths:
                source = repo / name
                if source.is_file():
                    dest = tree / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
            if any(apply(tree, patch, reverse=True).returncode for patch in reversed(patches[:prefix])):
                continue
            if any(apply(tree, patch).returncode for patch in patches):
                continue
        for patch in patches[:prefix]:
            print(f"Already applied: {patch.name}")
        for patch in patches[prefix:]:
            result = apply(repo, patch, check=True)
            if result.returncode:
                print(result.stderr, file=sys.stderr)
                return 1
            result = apply(repo, patch)
            if result.returncode:
                print(result.stderr, file=sys.stderr)
                return 1
            print(f"Applied: {patch.name}")
        return 0
    print("Patch conflict: local changes were preserved. Inspect the upstream checkout.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
