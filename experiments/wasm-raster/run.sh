#!/usr/bin/env bash
# Usage (from the repository root, with JAVA_HOME pointing at a JDK 21):
#   JAVA_HOME=/path/to/jdk21 bash experiments/wasm-raster/run.sh \
#     /absolute/path/to/ha_Sub1.java /absolute/path/to/void-client-0.2.0_a2.jar
# Exits nonzero on any failed step: closure audit, JVM runs, Gradle/TeaVM build, headless browser run
# (exit status and DOM result), or evidence validation across both sizes and all three hash sources.
# Self-test: RASTER_SELFTEST_MUTATE=browser-hash|missing-browser must make the run fail.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
NATIVE_SRC="${1:?absolute path to ha_Sub1.java required}"
NATIVE_JAR="${2:?absolute path to void-client-0.2.0_a2.jar required}"
JDK="${JAVA_HOME:?set JAVA_HOME to a JDK 21 directory}"
JAVAC="$JDK/bin/javac"
JAVA="$JDK/bin/java"
UPSTREAM_GRADLEW="${UPSTREAM_GRADLEW:-$HERE/../../upstream/runelite-client/gradlew}"
BUILD="$HERE/build"
OUT="$BUILD/teavm-out"
CHROMIUM="${CHROMIUM:-/usr/bin/chromium}"
BROWSER_TIMEOUT="${BROWSER_TIMEOUT:-180}"
MUTATE_ARGS=()
if [ -n "${RASTER_SELFTEST_MUTATE:-}" ]; then MUTATE_ARGS=(--mutate "$RASTER_SELFTEST_MUTATE"); fi

case "$NATIVE_SRC" in /*) ;; *) echo "ha_Sub1.java path must be absolute" >&2; exit 2 ;; esac
case "$NATIVE_JAR" in /*) ;; *) echo "jar path must be absolute" >&2; exit 2 ;; esac
[ -f "$NATIVE_SRC" ] && [ -f "$NATIVE_JAR" ] || { echo "missing native input" >&2; exit 2; }
[ -x "$JAVAC" ] && [ -x "$JAVA" ] || { echo "JAVA_HOME does not contain javac/java: $JDK" >&2; exit 2; }

rm -rf "$BUILD"
mkdir -p "$BUILD"
python3 -I "$HERE/tools/extract_face_kernel.py" --src "$NATIVE_SRC" --out "$BUILD/generated-src"

echo "== closure audit (verbatim kernel, no jar on classpath)"
"$JAVAC" -Xlint:all -d "$BUILD/audit" "$BUILD"/generated-src/*.java
echo "audit: PASS"

echo "== JVM verbatim kernel"
"$JAVAC" -d "$BUILD/jvm-verbatim" "$HERE"/src/shared/java/*.java "$BUILD"/generated-src/*.java "$HERE"/src/jvm/java/VerbatimJvm.java
"$JAVA" -cp "$BUILD/jvm-verbatim" VerbatimJvm > "$BUILD/jvm-verbatim.jsonl"
cat "$BUILD/jvm-verbatim.jsonl"

echo "== JVM reference: real jar bytecode"
"$JAVAC" -nowarn -cp "$NATIVE_JAR" -d "$BUILD/jvm-native" "$HERE"/src/shared/java/Raster.java "$HERE"/src/shared/java/Scene.java "$HERE"/src/jvm/java/NativeJar.java
"$JAVA" -cp "$BUILD/jvm-native:$NATIVE_JAR" NativeJar > "$BUILD/jvm-native.jsonl"
cat "$BUILD/jvm-native.jsonl"

echo "== TeaVM 0.16.0 WasmGC build"
if [ -f "$UPSTREAM_GRADLEW" ]; then
  JAVA_HOME="$JDK" bash "$UPSTREAM_GRADLEW" -p "$HERE" buildWasmGC --no-daemon -q
elif command -v gradle >/dev/null 2>&1; then
  JAVA_HOME="$JDK" gradle -p "$HERE" buildWasmGC --no-daemon -q
else
  echo "neither the upstream gradlew nor an installed gradle is available" >&2
  exit 1
fi
WASM_DIR="$(find "$BUILD" -path '*teavm*wasm-gc*' -name 'raster.wasm' -printf '%h\n' | head -1)"
[ -n "$WASM_DIR" ] || { echo "wasm output not found" >&2; exit 1; }
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$WASM_DIR"/raster.wasm "$WASM_DIR"/raster.wasm-runtime.js "$OUT"/
cp "$HERE/web/index.html" "$OUT"/
echo "module raw bytes: $(stat -c %s "$OUT/raster.wasm")  gzip -9 bytes: $(gzip -9 -c "$OUT/raster.wasm" | wc -c)"
echo "runtime js bytes: $(stat -c %s "$OUT/raster.wasm-runtime.js")"
echo "sha256 raster.wasm: $(sha256sum "$OUT/raster.wasm" | cut -d' ' -f1)"

echo "== headless Chromium run (ephemeral loopback server, serves only $OUT)"
PORT_FILE="$BUILD/server.port"
python3 -I "$HERE/tools/serve_loopback.py" --root "$OUT" --port-file "$PORT_FILE" 2> "$BUILD/server.log" &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do [ -s "$PORT_FILE" ] && break; sleep 0.1; done
[ -s "$PORT_FILE" ] || { echo "loopback server did not bind" >&2; exit 1; }
PORT="$(cat "$PORT_FILE")"
python3 -I "$HERE/tools/serve_loopback.py" --probe "$PORT"

set +e
timeout "$BROWSER_TIMEOUT" "$CHROMIUM" --headless=new --no-sandbox --disable-gpu \
  --virtual-time-budget=30000 --dump-dom "http://127.0.0.1:$PORT/index.html" \
  > "$BUILD/browser-dom.html" 2> "$BUILD/chromium.log"
BROWSER_RC=$?
set -e
if [ "$BROWSER_RC" -ne 0 ]; then
  echo "headless Chromium failed with status $BROWSER_RC; log tail:" >&2
  tail -20 "$BUILD/chromium.log" >&2 || true
  exit 1
fi

echo "== validation (both sizes; jvm-native vs jvm-verbatim vs browser)"
python3 -I "$HERE/tools/check_evidence.py" --build "$BUILD" ${MUTATE_ARGS[@]+"${MUTATE_ARGS[@]}"}
