#!/usr/bin/env bash
set -euo pipefail
# Add this separately to Steam for Gaming Mode; it uses disposable test worlds.
export _JAVA_AWT_WM_NONREPARENTING=1
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export SERVER_JAVA="$root/.runtime/jdks/jdk21/bin/java"
export CLIENT_JAVA="$root/.runtime/jdks/jdk8/bin/java"
cd "$root"
mkdir -p "$root/.runtime/deck-benchmarks"
run_directory="$root/.runtime/deck-benchmarks/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$run_directory"
log="$run_directory/session.log"
probe=(python3 -u "$root/scripts/smoke_profile.py" --desktop --deck-route-seconds "${SOLOSCAPE_BENCHMARK_SECONDS:-1800}")
if command -v mangohud >/dev/null 2>&1; then
  export MANGOHUD_CONFIG="fps,frametime,cpu_stats,gpu_stats,cpu_temp,gpu_temp,ram,vram,battery,autostart_log=1,log_duration=3600,log_interval=0,permit_upload=0,output_folder=$run_directory"
  exec mangohud --dlsym "${probe[@]}" > "$log" 2>&1
fi
exec "${probe[@]}" > "$log" 2>&1
