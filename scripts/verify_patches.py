#!/usr/bin/env python3
"""Read-only comparison of the full modified source tree with its pinned patch stack."""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def verify(repo, patches):
    paths = set(git(repo, "diff", "--name-only", "-z", "HEAD").decode().rstrip("\0").split("\0"))
    paths.update(git(repo, "ls-files", "--others", "--exclude-standard", "-z").decode().rstrip("\0").split("\0"))
    paths.discard("")
    for patch in patches:
        rows = subprocess.check_output(["git", "apply", "--numstat", str(patch)], text=True)
        paths.update(row.split("\t", 2)[2] for row in rows.splitlines())
    tracked = git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", *sorted(paths)).decode().splitlines() if paths else []
    with tempfile.TemporaryDirectory(prefix="soloscape-verify-") as directory:
        scratch = Path(directory)
        if tracked:
            with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "HEAD", *tracked))) as archive:
                archive.extractall(scratch, filter="data")
        for patch in patches:
            subprocess.run(["git", "apply", str(patch)], cwd=scratch, check=True, capture_output=True)
        differences = [name for name in sorted(paths)
                       if (scratch / name).is_file() != (repo / name).is_file()
                       or ((scratch / name).is_file() and (scratch / name).read_bytes() != (repo / name).read_bytes())]
        if differences:
            raise ValueError("Source differs from exported patches: " + ", ".join(differences))
    return len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["client", "server"])
    args = parser.parse_args()
    repo = ROOT / "upstream" / ("runelite-client" if args.kind == "client" else "game-server")
    patches = sorted((ROOT / "patches" / args.kind).glob("*.patch"))
    try:
        count = verify(repo, patches)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
    print(f"{args.kind}: all {count} modified/patched source files match the exported stack")


if __name__ == "__main__":
    main()
