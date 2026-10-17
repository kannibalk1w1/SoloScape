#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -f "$root/config/local.env" ]]; then
  # shellcheck source=/dev/null
  source "$root/config/local.env"
fi
# Preserve unset defaults, but export explicit local.env selectors to child processes.
if [[ -v SOLOSCAPE_PROFILE_HOME ]]; then export SOLOSCAPE_PROFILE_HOME; fi
if [[ -v SOLOSCAPE_CACHE_HOME ]]; then export SOLOSCAPE_CACHE_HOME; fi
export SERVER_JAVA=${SERVER_JAVA:-java}
export CLIENT_JAVA=${CLIENT_JAVA:-java}
exec python3 "$root/scripts/smoke_coop.py" "$@"
