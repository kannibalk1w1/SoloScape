#!/usr/bin/env bash
# Usage (from anywhere, JAVA_HOME = a JDK 21):
#   JAVA_HOME=/path/to/jdk21 GRADLE_USER_HOME=/path/to/.gradle bash experiments/wasm-triangle/run.sh \
#     /absolute/path/to/client/src /absolute/path/to/void-client-0.2.0_a2.jar
# Exits nonzero on any failed step: closure extraction/audit, JVM runs, Gradle/TeaVM build, headless
# browser run (exit status and DOM result), or evidence validation across both sizes and scenes.
# Self-test: TRIANGLE_SELFTEST_MUTATE=browser-hash|missing-browser|zero-timing must make the run fail.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${1:?absolute path to the native client/src directory required}"
NATIVE_JAR="${2:?absolute path to void-client-0.2.0_a2.jar required}"
JDK="${JAVA_HOME:?set JAVA_HOME to a JDK 21 directory}"
JAVAC="$JDK/bin/javac"
JAVA="$JDK/bin/java"
UPSTREAM_GRADLEW="${UPSTREAM_GRADLEW:-$HERE/../../upstream/runelite-client/gradlew}"
BUILD="$HERE/build"
OUT="$BUILD/teavm-out"
CHROMIUM="${CHROMIUM:-/usr/bin/chromium}"
BROWSER_TIMEOUT="${BROWSER_TIMEOUT:-240}"
MUTATE_ARGS=()
if [ -n "${TRIANGLE_SELFTEST_MUTATE:-}" ]; then MUTATE_ARGS=(--mutate "$TRIANGLE_SELFTEST_MUTATE"); fi

case "$SRC_DIR" in /*) ;; *) echo "client/src path must be absolute" >&2; exit 2 ;; esac
case "$NATIVE_JAR" in /*) ;; *) echo "jar path must be absolute" >&2; exit 2 ;; esac
[ -d "$SRC_DIR" ] && [ -f "$NATIVE_JAR" ] || { echo "missing native input" >&2; exit 2; }
[ -x "$JAVAC" ] && [ -x "$JAVA" ] || { echo "JAVA_HOME does not contain javac/java: $JDK" >&2; exit 2; }

rm -rf "$BUILD"
mkdir -p "$BUILD"
python3 -I - "$NATIVE_JAR" "$BUILD/inputs.json" "$SRC_DIR" <<'PY'
import hashlib, json, pathlib, sys
jar, out, src = sys.argv[1:4]
digest = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
inputs = {"client_jar": digest(jar)}
for name in ("Class109.java", "Class167.java", "ha_Sub1.java", "ha.java", "Class64_Sub1.java"):
    inputs[name] = digest(pathlib.Path(src) / name)
pathlib.Path(out).write_text(json.dumps(inputs, indent=2) + "\n")
PY
python3 -I "$HERE/tools/extract_triangle_closure.py" --src-dir "$SRC_DIR" --out "$BUILD/generated-src"

echo "== closure audit (extracted closure, no jar on classpath, -Xlint:all)"
"$JAVAC" -Xlint:all -d "$BUILD/audit" "$BUILD"/generated-src/*.java
echo "audit: PASS"

echo "== JVM extracted closure"
"$JAVAC" -d "$BUILD/jvm-verbatim" "$HERE"/src/shared/java/*.java "$BUILD"/generated-src/*.java "$HERE"/src/jvm/java/VerbatimJvm.java
"$JAVA" -cp "$BUILD/jvm-verbatim" VerbatimJvm > "$BUILD/jvm-verbatim.jsonl"
cat "$BUILD/jvm-verbatim.jsonl"

echo "== JVM reference: real jar bytecode"
"$JAVAC" -nowarn -cp "$NATIVE_JAR" -d "$BUILD/jvm-native" "$HERE"/src/shared/java/{Fill,Scene,Bench}.java "$HERE"/src/jvm/java/NativeJar.java
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
WASM_DIR="$(find "$BUILD" -path '*teavm*wasm-gc*' -name 'triangle.wasm' -printf '%h\n' | head -1)"
[ -n "$WASM_DIR" ] || { echo "wasm output not found" >&2; exit 1; }
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$WASM_DIR"/triangle.wasm "$WASM_DIR"/triangle.wasm-runtime.js "$OUT"/
cp "$HERE/web/index.html" "$OUT"/
echo "module raw bytes: $(stat -c %s "$OUT/triangle.wasm")  gzip -9 bytes: $(gzip -9 -c "$OUT/triangle.wasm" | wc -c)"
echo "runtime js bytes: $(stat -c %s "$OUT/triangle.wasm-runtime.js")"
echo "sha256 triangle.wasm: $(sha256sum "$OUT/triangle.wasm" | cut -d' ' -f1)"

echo "== headless Chromium run (ephemeral loopback server, serves only $OUT)"
PORT_FILE="$BUILD/server.port"
python3 -I "$HERE/tools/serve_loopback.py" --root "$OUT" --port-file "$PORT_FILE" 2> "$BUILD/server.log" &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do [ -s "$PORT_FILE" ] && break; sleep 0.1; done
[ -s "$PORT_FILE" ] || { echo "loopback server did not bind" >&2; exit 1; }
PORT="$(cat "$PORT_FILE")"
python3 -I "$HERE/tools/serve_loopback.py" --probe "$PORT"

# Real clocks only: a CDP pipe, no virtual-time budget, so performance.now() advances during raster.
timeout "$BROWSER_TIMEOUT" "${NODE:-node}" "$HERE/tools/browser_probe.mjs" "$CHROMIUM" "http://127.0.0.1:$PORT/index.html" "$BUILD"

echo "== validation (native jar vs JVM extracted vs WasmGC, both sizes, both scenes)"
python3 -I "$HERE/tools/check_evidence.py" --build "$BUILD" ${MUTATE_ARGS[@]+"${MUTATE_ARGS[@]}"}
