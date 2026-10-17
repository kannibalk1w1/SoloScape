#!/usr/bin/env bash
# Decode-only equality proof (original synthetic old-format Class124 bytes).
# Usage (JAVA_HOME = a JDK 21 directory):
#   JAVA_HOME=/path/to/jdk21 UPSTREAM_GRADLEW=/path/to/gradlew bash experiments/wasm-model-decode/run.sh \
#     /absolute/path/to/client/src /absolute/path/to/frozen-client.jar
# Exits nonzero on any failed step: input digests, closure extraction (spans, budgets), fixture encoding,
# standalone compile, JVM runs, Gradle/TeaVM build, headless browser run, or the checker.
# Checker controls (run against the finished build, each must exit nonzero with a FAIL: line):
#   DECODE_REUSE=1 DECODE_SELFTEST=native-design|extracted-vertex|browser-face|browser-colour bash run.sh ...
# Private logs go to .runtime/wasm-model-boundary-20261017 (ignored); generated output stays in build/ (ignored).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${1:-}"
NATIVE_JAR="${2:-}"
EXPECTED_JAR_SHA=ac6e2671ed548c73ad4dcaf8e4446789f29c2780236059de12e6132795a6f918
LOG_DIR="$HERE/../../.runtime/wasm-model-boundary-20261017"
BUILD="$HERE/build"
OUT="$BUILD/teavm-out"
GEN="$BUILD/generated-src"
CHROMIUM="${CHROMIUM:-/usr/bin/chromium}"
BROWSER_TIMEOUT="${BROWSER_TIMEOUT:-240}"
SELFTEST="${DECODE_SELFTEST:-}"
CHECKER="$HERE/tools/check_decode_evidence.py"
die() { echo "wasm-model-decode: $*" >&2; exit 2; }

[ -n "$SRC_DIR" ] && [ -n "$NATIVE_JAR" ] || die "usage: run.sh /absolute/client/src /absolute/frozen-client.jar"
case "$SRC_DIR" in /*) ;; *) die "client/src path must be absolute" ;; esac
case "$NATIVE_JAR" in /*) ;; *) die "jar path must be absolute" ;; esac
[ -d "$SRC_DIR" ] || die "native source directory not found"
[ -f "$NATIVE_JAR" ] || die "native client jar not found"
[ -n "${JAVA_HOME:-}" ] || die "set JAVA_HOME to a JDK 21 directory"
JDK="$JAVA_HOME"; JAVAC="$JDK/bin/javac"; JAVA="$JDK/bin/java"
[ -x "$JAVAC" ] && [ -x "$JAVA" ] || die "JAVA_HOME does not contain javac/java"
"$JAVA" -version 2>&1 | head -1 | grep -q '"21' || die "JDK 21 required"
[ "$(sha256sum "$NATIVE_JAR" | cut -d' ' -f1)" = "$EXPECTED_JAR_SHA" ] || die "jar digest differs from the audited jar"
UPSTREAM_GRADLEW="${UPSTREAM_GRADLEW:-}"
[ -n "$UPSTREAM_GRADLEW" ] && [ -f "$UPSTREAM_GRADLEW" ] || die "set UPSTREAM_GRADLEW to the upstream gradlew"
[ -x "$CHROMIUM" ] || die "Chromium not found: $CHROMIUM"
mkdir -p "$LOG_DIR"

if [ -n "$SELFTEST" ]; then
  case "$SELFTEST" in
    native-design|extracted-vertex|browser-face|browser-colour) ;;
    *) die "unknown DECODE_SELFTEST=$SELFTEST" ;;
  esac
  [ "${DECODE_REUSE:-}" = 1 ] || die "controls reuse the finished build: set DECODE_REUSE=1"
  [ -f "$BUILD/fixtures.json" ] && [ -f "$BUILD/jvm-native.jsonl" ] && [ -f "$BUILD/browser-dom.html" ] \
    || die "DECODE_REUSE=1 needs a completed build/"
  python3 -I "$CHECKER" --build "$BUILD" --mutate "$SELFTEST"
  exit $?
fi

rm -rf "$BUILD"
mkdir -p "$GEN"

echo "== inputs"
python3 -I - "$NATIVE_JAR" "$SRC_DIR" "$BUILD/inputs.json" <<'PY' | tee "$LOG_DIR/inputs.log"
import hashlib, json, pathlib, sys
jar, src, out = sys.argv[1:4]
digest = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
inputs = {"client_jar": digest(jar)}
for name in ("Class124", "Packet", "Class348_Sub21"):
    inputs[name + ".java"] = digest(pathlib.Path(src) / (name + ".java"))
pathlib.Path(out).write_text(json.dumps(inputs, indent=2) + "\n")
print(json.dumps(inputs, indent=2))
PY

echo "== extract verbatim decode closure (fail-closed on spans, digests, budgets)"
python3 -I "$HERE/tools/extract_decode_closure.py" --src-dir "$SRC_DIR" --out "$GEN" | tee "$LOG_DIR/extract.log"

echo "== encode original synthetic fixtures from independent designs"
python3 -I "$HERE/tools/encode_decode_fixtures.py" --out "$BUILD" | tee "$LOG_DIR/encode.log"

echo "== standalone compile of the extracted closure (no jar on the classpath, -Xlint:all)"
set +e
"$JAVAC" -Xlint:all -Xmaxwarns 1000 -d "$BUILD/audit" "$GEN"/*.java 2> "$LOG_DIR/audit-javac.log"
audit_status=$?
set -e
cat "$LOG_DIR/audit-javac.log" >&2
[ "$audit_status" = 0 ] || die "standalone compile failed (see $LOG_DIR/audit-javac.log)"
echo "audit: $(grep -c 'warning:' "$LOG_DIR/audit-javac.log" || true) lint warnings, 0 errors"

echo "== JVM extracted closure over the original fixtures"
"$JAVAC" -nowarn -d "$BUILD/jvm-extracted" "$HERE"/src/shared/java/DecodeJson.java "$HERE/src/jvm/java/ExtractedDecodeJvm.java" "$GEN"/*.java
"$JAVA" -cp "$BUILD/jvm-extracted" ExtractedDecodeJvm > "$BUILD/jvm-extracted.jsonl" 2> "$LOG_DIR/jvm-extracted.stderr"
echo "jvm-extracted: $(wc -l < "$BUILD/jvm-extracted.jsonl") cases"

echo "== JVM reference: real native jar Class124(byte[]) by reflection"
"$JAVAC" -nowarn -cp "$NATIVE_JAR" -d "$BUILD/jvm-native" "$HERE"/src/shared/java/DecodeJson.java "$HERE/src/jvm/java/NativeDecode.java" "$GEN/DecodeFixtures.java"
"$JAVA" -cp "$BUILD/jvm-native:$NATIVE_JAR" NativeDecode > "$BUILD/jvm-native.jsonl" 2> "$LOG_DIR/jvm-native.stderr"
echo "jvm-native: $(wc -l < "$BUILD/jvm-native.jsonl") cases"

echo "== TeaVM 0.16.0 WasmGC build (offline, cached tooling)"
JAVA_HOME="$JDK" bash "$UPSTREAM_GRADLEW" -p "$HERE" buildWasmGC --offline --no-daemon -q 2> "$LOG_DIR/gradle.stderr" \
  || { tail -40 "$LOG_DIR/gradle.stderr" >&2; die "Gradle/TeaVM build failed"; }
WASM="$(find "$BUILD" -name 'decode.wasm' -path '*wasm-gc*' | head -1)"
[ -n "$WASM" ] || die "decode.wasm not produced"
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$WASM" "$OUT/"
cp "$(dirname "$WASM")/decode.wasm-runtime.js" "$OUT/"
cp "$HERE/web/index.html" "$OUT/"
echo "module raw bytes: $(stat -c %s "$OUT/decode.wasm")  gzip -9 bytes: $(gzip -9 -c "$OUT/decode.wasm" | wc -c)"
echo "runtime js bytes: $(stat -c %s "$OUT/decode.wasm-runtime.js")  raw; gzip -9: $(gzip -9 -c "$OUT/decode.wasm-runtime.js" | wc -c)"

echo "== headless Chromium run (ephemeral loopback server, serves only $OUT)"
PORT_FILE="$BUILD/server.port"
python3 -I "$HERE/tools/serve_decode.py" --root "$OUT" --port-file "$PORT_FILE" 2> "$LOG_DIR/server.log" &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do [ -s "$PORT_FILE" ] && break; sleep 0.1; done
[ -s "$PORT_FILE" ] || die "loopback server did not bind"
PORT="$(cat "$PORT_FILE")"
python3 -I "$HERE/tools/serve_decode.py" --probe "$PORT"
timeout "$BROWSER_TIMEOUT" "${NODE:-node}" "$HERE/../wasm-face/tools/browser_probe.mjs" "$CHROMIUM" \
  "http://127.0.0.1:$PORT/index.html" "$BUILD" 2> "$LOG_DIR/browser.stderr" | tee "$LOG_DIR/browser.log"
kill "$SERVER" 2>/dev/null || true
trap - EXIT

echo "== checker (native jar vs extracted JVM vs WasmGC vs original design)"
python3 -I "$CHECKER" --build "$BUILD" | tee "$LOG_DIR/checker.log"

# Bind the successful result to the exact local sources, adapters and tooling.
python3 -I "$HERE/tools/record_decode_provenance.py"
