#!/usr/bin/env bash
# Decoded-model bridge (DRAFT27 only). Original encoded old-format Class124 bytes -> the real Class124 decode (frozen native
# jar, and the generated closure on the JVM and in TeaVM WasmGC) -> a field-only FaceMesh adapter -> the existing
# FaceRig / NativeFace.JarRig native math -> framebuffer. Not a model constructor, lighting or product port.
# Usage (JAVA_HOME = a JDK 21 directory):
#   JAVA_HOME=/path/to/jdk21 UPSTREAM_GRADLEW=/path/to/gradlew bash experiments/wasm-decoded-face/run.sh \
#     /absolute/path/to/client/src /absolute/path/to/frozen-client.jar
# Both existing extractors run unchanged (wasm-face and wasm-model-decode, budgets and digests enforced by them).
# Exits nonzero on any failed step. Checker controls run at the end and must each exit 1 with a FAIL: line.
# A checker-only control on the finished build: BRIDGE_REUSE=1 BRIDGE_SELFTEST=decoded-array|browser-projected|browser-frame|palette
# Private logs: .runtime/wasm-decoded-face-20261017 (ignored). Generated output: build/ (ignored).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/../.."
WASM_FACE="$HERE/../wasm-face"
DECODE="$HERE/../wasm-model-decode"
SRC_DIR="${1:-}"
NATIVE_JAR="${2:-}"
EXPECTED_JAR_SHA=ac6e2671ed548c73ad4dcaf8e4446789f29c2780236059de12e6132795a6f918
LOG_DIR="$ROOT/.runtime/wasm-decoded-face-20261017"
BUILD="$HERE/build"
CHROMIUM="${CHROMIUM:-/usr/bin/chromium}"
BROWSER_TIMEOUT="${BROWSER_TIMEOUT:-240}"
CHECKER="$HERE/tools/check_bridge_evidence.py"
die() { echo "wasm-decoded-face: $*" >&2; exit 2; }

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
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-"$ROOT/.gradle"}"
mkdir -p "$LOG_DIR"

SELFTEST="${BRIDGE_SELFTEST:-}"
if [ -n "$SELFTEST" ]; then
  case "$SELFTEST" in
    decoded-array|browser-projected|browser-frame|palette) ;;
    *) die "unknown BRIDGE_SELFTEST=$SELFTEST" ;;
  esac
  [ "${BRIDGE_REUSE:-}" = 1 ] || die "controls reuse the finished build: set BRIDGE_REUSE=1"
  [ -f "$BUILD/browser/browser-dom.html" ] && [ -f "$BUILD/native.json" ] || die "BRIDGE_REUSE=1 needs a completed build/"
  python3 -I "$CHECKER" --build "$BUILD" --mutate "$SELFTEST"
  exit $?
fi

rm -rf "$BUILD"
mkdir -p "$BUILD/reused" "$BUILD/reused-native" "$BUILD/bridge" "$BUILD/generated-src"

echo "== inputs"
python3 -I - "$NATIVE_JAR" "$SRC_DIR" "$BUILD/inputs.json" <<'PY' | tee "$LOG_DIR/inputs.log"
import hashlib, json, pathlib, sys
jar, src, out = sys.argv[1:4]
digest = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
inputs = {"client_jar": digest(jar)}
for name in ("Class124", "Packet", "Class348_Sub21", "Class64_Sub1", "Class109", "Class167", "ha_Sub1", "ha",
             "Class101_Sub1", "Class6", "Class350", "Class318_Sub3", "Class126"):
    inputs[name + ".java"] = digest(pathlib.Path(src) / (name + ".java"))
pathlib.Path(out).write_text(json.dumps(inputs, indent=2) + "\n")
print(json.dumps(inputs, indent=2))
PY

echo "== reused read-only copies (wasm-face shared rig/scene sources; NativeFace and ClipScene are native-only)"
for name in FaceMesh FaceRig FaceScene FaceCounters ExtractedRig; do
  cp "$WASM_FACE/src/shared/java/$name.java" "$BUILD/reused/"
done
cp "$WASM_FACE/src/shared/java/ClipScene.java" "$WASM_FACE/src/jvm/java/NativeFace.java" "$BUILD/reused-native/"

echo "== extract face closure (wasm-face extractor, unchanged; fail-closed budgets)"
python3 -I "$WASM_FACE/tools/extract_face_closure.py" --src-dir "$SRC_DIR" --out "$BUILD/face/generated-src" | tee "$LOG_DIR/extract-face.log"

echo "== extract decode closure (wasm-model-decode extractor, unchanged; fail-closed budgets)"
python3 -I "$DECODE/tools/extract_decode_closure.py" --src-dir "$SRC_DIR" --out "$BUILD/decode/generated-src" | tee "$LOG_DIR/extract-decode.log"

echo "== compose generated closures (no name collisions allowed)"
python3 -I - "$BUILD" <<'PY' | tee "$LOG_DIR/compose.log"
import pathlib, shutil, sys
build = pathlib.Path(sys.argv[1])
seen = {}
for part in ("face", "decode"):
    for source in sorted((build / part / "generated-src").glob("*.java")):
        if source.name in seen:
            raise SystemExit(f"generated class name collision: {source.name} ({seen[source.name]} and {part})")
        seen[source.name] = part
        shutil.copy2(source, build / "generated-src" / source.name)
print(f"composed {len(seen)} generated files: " + ", ".join(f"{n}({p})" for n, p in sorted(seen.items())))
PY

echo "== encode original synthetic tetrahedra from declared designs (imports wasm-model-decode encode())"
python3 -I "$HERE/tools/encode_bridge_fixtures.py" --out "$BUILD" | tee "$LOG_DIR/encode.log"

echo "== standalone lint compile of the composed closure (no jar on the classpath, -Xlint:all)"
set +e
"$JAVAC" -Xlint:all -Xmaxwarns 1000 -d "$BUILD/audit" "$BUILD/reused/FaceCounters.java" "$BUILD"/generated-src/*.java \
  2> "$LOG_DIR/audit-javac.log"
audit_status=$?
set -e
[ "$audit_status" = 0 ] || { cat "$LOG_DIR/audit-javac.log" >&2; die "standalone compile of the composed closure failed"; }
echo "audit: $(grep -c 'warning:' "$LOG_DIR/audit-javac.log" || true) lint warnings, 0 errors"

echo "== native jar: real Class124(byte[]) decode + NativeFace.JarRig (compiled against the frozen jar only)"
mkdir -p "$BUILD/jvm-native"
"$JAVAC" -nowarn -cp "$NATIVE_JAR" -d "$BUILD/jvm-native" \
  "$BUILD/reused/FaceMesh.java" "$BUILD/reused/FaceRig.java" "$BUILD/reused/FaceScene.java" "$BUILD/reused/FaceCounters.java" \
  "$BUILD/reused-native/ClipScene.java" "$BUILD/reused-native/NativeFace.java" \
  "$HERE/src/shared/java/BridgeScene.java" "$HERE/src/shared/java/BridgeRun.java" "$HERE/src/shared/java/DecodeMesh.java" \
  "$BUILD/bridge/BridgeFixtures.java" "$HERE/src/jvm/java/NativeBridge.java"
"$JAVA" -cp "$BUILD/jvm-native:$NATIVE_JAR" NativeBridge > "$BUILD/native.json" 2> "$LOG_DIR/native.stderr"
echo "native-jar: $(grep -c '"runtime":"native-jar"' "$BUILD/native.json") runtime line(s)"

echo "== extracted JVM: generated Class124 + extracted face closure (no native jar on the path)"
mkdir -p "$BUILD/jvm-extracted"
"$JAVAC" -nowarn -d "$BUILD/jvm-extracted" \
  "$BUILD/reused/FaceMesh.java" "$BUILD/reused/FaceRig.java" "$BUILD/reused/FaceScene.java" "$BUILD/reused/FaceCounters.java" \
  "$BUILD/reused/ExtractedRig.java" \
  "$HERE/src/shared/java/BridgeScene.java" "$HERE/src/shared/java/BridgeRun.java" "$HERE/src/shared/java/DecodeMesh.java" \
  "$BUILD/bridge/BridgeFixtures.java" "$BUILD"/generated-src/*.java "$HERE/src/jvm/java/ExtractedBridgeJvm.java"
"$JAVA" -cp "$BUILD/jvm-extracted" ExtractedBridgeJvm > "$BUILD/extracted-jvm.json" 2> "$LOG_DIR/extracted-jvm.stderr"

echo "== TeaVM 0.16.0 WasmGC build (offline, cached tooling)"
JAVA_HOME="$JDK" bash "$UPSTREAM_GRADLEW" -p "$HERE" buildWasmGC --offline --no-daemon -q 2> "$LOG_DIR/gradle.stderr" \
  || { tail -40 "$LOG_DIR/gradle.stderr" >&2; die "Gradle/TeaVM build failed"; }
WASM="$(find "$BUILD" -name 'bridge.wasm' -path '*wasm-gc*' | head -1)"
[ -n "$WASM" ] || die "bridge.wasm not produced"
OUT="$BUILD/web-out"
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$WASM" "$OUT/"
cp "$(dirname "$WASM")/bridge.wasm-runtime.js" "$OUT/"
cp "$HERE/web/index.html" "$OUT/"
echo "module raw bytes: $(stat -c %s "$OUT/bridge.wasm")  gzip -9 bytes: $(gzip -9 -c "$OUT/bridge.wasm" | wc -c)"

echo "== headless Chromium run (ephemeral loopback server, serves only $OUT)"
mkdir -p "$BUILD/browser"
PORT_FILE="$BUILD/server.port"
python3 -I "$HERE/tools/serve_bridge.py" --root "$OUT" --port-file "$PORT_FILE" 2> "$LOG_DIR/server.log" &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do [ -s "$PORT_FILE" ] && break; sleep 0.1; done
[ -s "$PORT_FILE" ] || die "loopback server did not bind"
PORT="$(cat "$PORT_FILE")"
python3 -I "$HERE/tools/serve_bridge.py" --probe "$PORT"
timeout "$BROWSER_TIMEOUT" node "$WASM_FACE/tools/browser_probe.mjs" "$CHROMIUM" \
  "http://127.0.0.1:$PORT/index.html" "$BUILD/browser" 2> "$LOG_DIR/browser.stderr" | tee "$LOG_DIR/browser.log"
kill "$SERVER" 2>/dev/null || true
trap - EXIT

echo "== checker (native jar vs extracted JVM vs WasmGC vs original design)"
python3 -I "$CHECKER" --build "$BUILD" | tee "$LOG_DIR/checker.log"

echo "== corruption controls (each must exit 1 inside the checker with a FAIL: line)"
for control in decoded-array browser-projected browser-frame palette; do
  set +e
  python3 -I "$CHECKER" --build "$BUILD" --mutate "$control" > "$LOG_DIR/control-$control.log" 2>&1
  status=$?
  set -e
  [ "$status" = 1 ] && grep -q '^FAIL:' "$LOG_DIR/control-$control.log" || die "control $control did not fail inside the checker"
  echo "control $control: exit $status, $(grep '^FAIL:' "$LOG_DIR/control-$control.log" | head -1)"
done

echo "== provenance (sources, reused tools, inputs, tool versions, closures, module sizes)"
python3 -I "$HERE/tools/record_bridge_provenance.py" --build "$BUILD" --log "$LOG_DIR" --jdk "$JDK" \
  --node "$(command -v node)" --chromium "$CHROMIUM" > /dev/null
echo "provenance: $LOG_DIR/provenance.json"
