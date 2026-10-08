#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -f "$root/config/local.env" ]]; then
  # shellcheck source=/dev/null
  source "$root/config/local.env"
fi
export SERVER_JAVA=${SERVER_JAVA:-java}
export CLIENT_JAVA=${CLIENT_JAVA:-java}
exec python3 "$root/scripts/smoke_profile.py"
