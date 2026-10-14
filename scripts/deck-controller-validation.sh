#!/usr/bin/env bash
set -euo pipefail
# Internal validation shortcut: every probe creates a disposable isolated world.
export _JAVA_AWT_WM_NONREPARENTING=1
# Java 8 otherwise uses ASCII in Steam's C locale. This also supports older
# installed smoke tooling; new harness compilers explicitly request UTF-8.
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:+$JAVA_TOOL_OPTIONS }-Dfile.encoding=UTF-8"
task_root=${SOLOSCAPE_VALIDATION_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}
export SERVER_JAVA="$task_root/.runtime/jdks/jdk21/bin/java"
export CLIENT_JAVA="$task_root/.runtime/jdks/jdk8/bin/java"
task_probe_script=smoke_profile.py
case ${1:-quick} in
  quick) task_probe_args=(--desktop --deck60-gl-only --tab-bar) ;;
  cook) task_probe_args=(--desktop --gather-cook) ;;
  shop) task_probe_args=(--desktop --shop-trade) ;;
  route) task_probe_args=(--desktop --deck-route-seconds "${SOLOSCAPE_BENCHMARK_SECONDS:-1800}") ;;
  launcher) task_probe_script=smoke-launcher.py; task_probe_args=(--desktop) ;;
  *) echo 'Choose quick, cook, shop, route or launcher.' >&2; exit 2 ;;
esac
cd "$task_root"
task_run_directory="$task_root/.runtime/deck-controller-validation/$(date -u +%Y%m%dT%H%M%SZ)-${1:-quick}"
mkdir -p "$task_run_directory"
printf '%s\n' "$task_run_directory" > "$task_root/.runtime/deck-controller-validation/latest-run"
exec python3 -u "$task_root/scripts/$task_probe_script" "${task_probe_args[@]}" > "$task_run_directory/session.log" 2>&1
