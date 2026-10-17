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
if [[ -v SOLOSCAPE_LAUNCHER_HOME ]]; then export SOLOSCAPE_LAUNCHER_HOME; fi
export SERVER_JAVA=${SERVER_JAVA:-java}
export CLIENT_JAVA=${CLIENT_JAVA:-java}
client_jar=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import local_dev; print(local_dev.jar(local_dev.CLIENT / "client", "void-client-*.jar"))' "$root/scripts")
exec "$CLIENT_JAVA" -cp "$client_jar" net.runelite.client.soloscape.launcher.SoloScapeLauncher "$root"
