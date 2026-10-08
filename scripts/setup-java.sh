#!/usr/bin/env bash
# Install project-local Temurin JDKs without changing system Java.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python3 - "$root" <<'PY'
import hashlib
import json
import platform
from pathlib import Path
import shlex
import subprocess
import sys

root = Path(sys.argv[1])
if platform.system() != "Linux" or platform.machine() != "x86_64":
    sys.exit("This bootstrap installer currently supports Linux x86_64 (including Steam Deck).")
base = root / ".runtime/jdks"
base.mkdir(parents=True, exist_ok=True)
for version in (21, 8):
    target = base / f"jdk{version}"
    if (target / "bin/java").is_file():
        subprocess.run([str(target / "bin/java"), "-version"], check=True)
        continue
    endpoint = (
        f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot"
        "?architecture=x64&image_type=jdk&os=linux&vendor=eclipse"
    )
    metadata = subprocess.check_output(
        ["curl", "--fail", "--location", "--silent", "--show-error", endpoint]
    )
    release = json.loads(metadata)[0]
    package = release["binary"]["package"]
    archive = base / f"jdk{version}.tar.gz"
    subprocess.run([
        "curl", "--fail", "--location", "--silent", "--show-error", "--retry", "2",
        package["link"], "-o", str(archive),
    ], check=True)
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != package["checksum"]:
        sys.exit(f"JDK {version} checksum mismatch; archive was not extracted.")
    target.mkdir(exist_ok=True)
    subprocess.run([
        "tar", "-xzf", str(archive), "--strip-components=1", "-C", str(target),
    ], check=True)
    (base / f"{version}.json").write_bytes(metadata)
    subprocess.run([str(target / "bin/java"), "-version"], check=True)

config = root / "config/local.env"
if not config.exists():
    config.parent.mkdir(exist_ok=True)
    config.write_text(
        "SERVER_JAVA=" + shlex.quote(str(base / "jdk21/bin/java")) + "\n"
        "CLIENT_JAVA=" + shlex.quote(str(base / "jdk8/bin/java")) + "\n"
    )
    print(f"Configured {config}")
else:
    print(f"Preserved existing {config}; local JDKs are in {base}.")
PY
