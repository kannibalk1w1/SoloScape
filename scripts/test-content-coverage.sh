#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -f "$root/config/local.env" ]]; then
  source "$root/config/local.env"
fi
export SERVER_JAVA=${SERVER_JAVA:-java}
exec python3 "$root/scripts/content_coverage.py" "$@"
