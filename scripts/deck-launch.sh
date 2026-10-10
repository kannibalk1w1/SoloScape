#!/usr/bin/env bash
set -euo pipefail
# Gamescope does not reparent X11 windows. Tell AWT before its first window is
# created; the backend and game JVM inherit this too.
export _JAVA_AWT_WM_NONREPARENTING=1
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export SERVER_JAVA="$root/.runtime/jdks/jdk21/bin/java"
export CLIENT_JAVA="$root/.runtime/jdks/jdk8/bin/java"
cd "$root"
client_jar=$(python3 -c 'import sys; sys.path.insert(0,sys.argv[1]); import local_dev; print(local_dev.jar(local_dev.CLIENT / "client", "void-client-*.jar"))' "$root/scripts")
exec "$CLIENT_JAVA" -Dsoloscape.launcher.steamKeyboard=true -cp "$client_jar" net.runelite.client.soloscape.launcher.SoloScapeLauncher "$root"
