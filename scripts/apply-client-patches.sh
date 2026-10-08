#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
repo="$root/upstream/runelite-client"
expected=297bc8a4861755b676855664d32859054779c067
if [[ ! -d "$repo/.git" ]]; then
  echo "Missing client checkout. Follow README-SOLOSCAPE.md." >&2
  exit 1
fi
if [[ $(git -C "$repo" rev-parse HEAD) != "$expected" ]]; then
  echo "Controller patches require client base $expected; re-audit before updating it." >&2
  exit 1
fi
mkdir -p "$root/.runtime"
exec 9>"$root/.runtime/client-patches.lock"
flock 9
exec python3 "$root/scripts/apply_client_patches.py" "$repo" "$root"/patches/client/*.patch
