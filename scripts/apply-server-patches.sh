#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
repo="$root/upstream/game-server"
expected=9f9113559eb686abd917893b5dca16404be07f93
if [[ ! -d "$repo/.git" ]]; then
  echo "Missing server checkout. Follow README-SOLOSCAPE.md." >&2
  exit 1
fi
if [[ $(git -C "$repo" rev-parse HEAD) != "$expected" ]]; then
  echo "SoloScape patches require server base $expected; re-audit before updating it." >&2
  exit 1
fi
mkdir -p "$root/.runtime"
exec 9>"$root/.runtime/server-patches.lock"
flock 9
exec python3 "$root/scripts/apply_client_patches.py" "$repo" "$root"/patches/server/*.patch
