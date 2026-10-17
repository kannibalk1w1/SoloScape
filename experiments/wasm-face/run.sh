#!/usr/bin/env bash
# Usage (from anywhere, JAVA_HOME = a JDK 21):
#   JAVA_HOME=/path/to/jdk21 UPSTREAM_GRADLEW=/path/to/gradlew bash experiments/wasm-face/run.sh \
#     /absolute/path/to/client/src /absolute/path/to/void-client-0.2.0_a2.jar
# Exits nonzero on any failed step: input check, closure extraction/audit (line, field and callee budgets),
# JVM runs, Gradle/TeaVM build, headless browser run, or evidence validation (projected arrays element for
# element, colour/depth hashes, adapter side effects, stub counters, controls).
# Self-tests (each must exit nonzero):
#   FACE_SELFTEST=jvm-vertex|browser-vertex      one implementation gets a perturbed vertex
#   FACE_SELFTEST=illegal-state0|illegal-texture|illegal-lit|illegal-clip   the extracted build enters the adapter/stubs illegally
#   FACE_SELFTEST=browser-hash|browser-element|missing-browser|zero-coverage|counter-stub|counter-adapter|duplicate-case|control-equal|no-backface|missing-present|culling-equal
#                                                 corrupts the collected evidence before the checker (checker-only; set FACE_REUSE=1 to reuse an existing build/)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${1:-}"
NATIVE_JAR="${2:-}"
EXPECTED_JAR_SHA=ac6e2671ed548c73ad4dcaf8e4446789f29c2780236059de12e6132795a6f918
EXPECTED_SRC_SHA_64=e02518708ff51fc07c42e1f3fa587810c40c715948054c344b90484afda91398
EXPECTED_SRC_SHA_109=058b9ffd636007796f75dd50f25a422e173e820f7dcee135b6b71989d874308a
die() { echo "wasm-face: $*" >&2; exit 2; }

[ -n "$SRC_DIR" ] && [ -n "$NATIVE_JAR" ] || die "usage: run.sh /absolute/client/src /absolute/void-client-0.2.0_a2.jar (user-supplied native inputs; none are checked in)"
case "$SRC_DIR" in /*) ;; *) die "client/src path must be absolute: $SRC_DIR" ;; esac
case "$NATIVE_JAR" in /*) ;; *) die "jar path must be absolute: $NATIVE_JAR" ;; esac
[ -d "$SRC_DIR" ] || die "native source directory not found: $SRC_DIR"
[ -f "$NATIVE_JAR" ] || die "native client jar not found: $NATIVE_JAR"
for f in Class64_Sub1 Class109 Class167 ha_Sub1 ha Class101_Sub1 Class6 Class350 Class318_Sub3 Class126; do
  [ -f "$SRC_DIR/$f.java" ] || die "missing native source file: $SRC_DIR/$f.java"
done
[ -n "${JAVA_HOME:-}" ] || die "set JAVA_HOME to a JDK 21 directory"
JDK="$JAVA_HOME"; JAVAC="$JDK/bin/javac"; JAVA="$JDK/bin/java"
[ -x "$JAVAC" ] && [ -x "$JAVA" ] || die "JAVA_HOME does not contain javac/java: $JDK"
"$JAVA" -version 2>&1 | head -1 | grep -q '"21' || die "JDK 21 required: $("$JAVA" -version 2>&1 | head -1)"
[ "$(sha256sum "$NATIVE_JAR" | cut -d' ' -f1)" = "$EXPECTED_JAR_SHA" ] || die "jar digest differs from the audited jar ($EXPECTED_JAR_SHA)"
[ "$(sha256sum "$SRC_DIR/Class64_Sub1.java" | cut -d' ' -f1)" = "$EXPECTED_SRC_SHA_64" ] || die "Class64_Sub1.java digest differs from the audited source"
[ "$(sha256sum "$SRC_DIR/Class109.java" | cut -d' ' -f1)" = "$EXPECTED_SRC_SHA_109" ] || die "Class109.java digest differs from the audited source"
UPSTREAM_GRADLEW="${UPSTREAM_GRADLEW:-}"
if [ -z "$UPSTREAM_GRADLEW" ] && ! command -v gradle >/dev/null 2>&1; then die "set UPSTREAM_GRADLEW to the upstream gradlew (or install gradle)"; fi
[ -z "$UPSTREAM_GRADLEW" ] || [ -f "$UPSTREAM_GRADLEW" ] || die "UPSTREAM_GRADLEW not found: $UPSTREAM_GRADLEW"
BUILD="$HERE/build"
OUT="$BUILD/teavm-out"
CHROMIUM="${CHROMIUM:-/usr/bin/chromium}"
[ -x "$CHROMIUM" ] || die "Chromium not found: $CHROMIUM (set CHROMIUM)"
BROWSER_TIMEOUT="${BROWSER_TIMEOUT:-240}"
SELFTEST="${FACE_SELFTEST:-}"
JVM_OPTS=(); BROWSER_QUERY=""; MUTATE_ARGS=()
case "$SELFTEST" in
  "") ;;
  jvm-vertex) JVM_OPTS=(-Dface.perturb=true) ;;
  browser-vertex) BROWSER_QUERY="?perturb=1" ;;
  illegal-state0) JVM_OPTS=(-Dface.illegal=1) ;;
  illegal-texture) JVM_OPTS=(-Dface.illegal=2) ;;
  illegal-lit) JVM_OPTS=(-Dface.illegal=3) ;;
  illegal-clip) JVM_OPTS=(-Dface.illegal=4) ;;
  browser-hash|browser-element|missing-browser|zero-coverage|counter-stub|counter-adapter|duplicate-case|control-equal|no-backface|missing-present|culling-equal)
    MUTATE_ARGS=(--mutate "$SELFTEST") ;;
  *) die "unknown FACE_SELFTEST=$SELFTEST" ;;
esac

if [ "${FACE_REUSE:-}" = 1 ] && [ -n "${MUTATE_ARGS[*]:-}" ]; then
  [ -f "$BUILD/browser-dom.html" ] || die "FACE_REUSE=1 needs a completed build/"
  python3 -I "$HERE/tools/check_evidence.py" --build "$BUILD" "${MUTATE_ARGS[@]}"
  exit $?
fi

rm -rf "$BUILD"
mkdir -p "$BUILD"
python3 -I - "$NATIVE_JAR" "$BUILD/inputs.json" "$SRC_DIR" <<'PY'
import hashlib, json, pathlib, sys
jar, out, src = sys.argv[1:4]
digest = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
inputs = {"client_jar": digest(jar)}
for name in ("Class64_Sub1", "Class109", "Class167", "ha_Sub1", "ha", "Class101_Sub1", "Class6", "Class350", "Class318_Sub3", "Class126"):
    inputs[name + ".java"] = digest(pathlib.Path(src) / (name + ".java"))
pathlib.Path(out).write_text(json.dumps(inputs, indent=2) + "\n")
PY
python3 -I "$HERE/tools/extract_face_closure.py" --src-dir "$SRC_DIR" --out "$BUILD/generated-src"

echo "== closure audit (extracted closure only, no jar on the classpath, -Xlint:all)"
"$JAVAC" -Xlint:all -Xmaxwarns 1000 -d "$BUILD/audit" "$HERE/src/shared/java/FaceCounters.java" "$BUILD"/generated-src/*.java 2> "$BUILD/audit.log" || { cat "$BUILD/audit.log" >&2; exit 1; }
echo "audit: $(grep -c 'warning:' "$BUILD/audit.log" || true) lint warnings from verbatim native code, 0 errors"

echo "== JVM extracted closure"
"$JAVAC" -nowarn -d "$BUILD/jvm-verbatim" "$HERE"/src/shared/java/*.java "$BUILD"/generated-src/*.java "$HERE/src/jvm/java/VerbatimFaceJvm.java"
"$JAVA" ${JVM_OPTS[@]+"${JVM_OPTS[@]}"} -cp "$BUILD/jvm-verbatim" VerbatimFaceJvm > "$BUILD/jvm-verbatim.jsonl"
echo "jvm-verbatim: $(wc -l < "$BUILD/jvm-verbatim.jsonl") cases"

echo "== JVM reference: real jar bytecode (reflection + Unsafe)"
"$JAVAC" -nowarn -cp "$NATIVE_JAR" -d "$BUILD/jvm-native" "$HERE"/src/shared/java/{FaceMesh,FaceRig,FaceScene}.java "$HERE/src/jvm/java/NativeFace.java" 2>/dev/null
"$JAVA" -cp "$BUILD/jvm-native:$NATIVE_JAR" NativeFace > "$BUILD/jvm-native.jsonl"
echo "jvm-native: $(wc -l < "$BUILD/jvm-native.jsonl") cases"

echo "== TeaVM 0.16.0 WasmGC build"
if [ -n "$UPSTREAM_GRADLEW" ]; then
  JAVA_HOME="$JDK" bash "$UPSTREAM_GRADLEW" -p "$HERE" buildWasmGC --no-daemon -q
else
  JAVA_HOME="$JDK" gradle -p "$HERE" buildWasmGC --no-daemon -q
fi
WASM_DIR="$(find "$BUILD" -path '*teavm*wasm-gc*' -name 'face.wasm' -printf '%h\n' | head -1)"
[ -n "$WASM_DIR" ] || { echo "wasm output not found" >&2; exit 1; }
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$WASM_DIR"/face.wasm "$WASM_DIR"/face.wasm-runtime.js "$OUT"/
cp "$HERE/web/index.html" "$OUT"/
echo "module raw bytes: $(stat -c %s "$OUT/face.wasm")  gzip -9 bytes: $(gzip -9 -c "$OUT/face.wasm" | wc -c)"
echo "runtime js bytes: $(stat -c %s "$OUT/face.wasm-runtime.js")"

echo "== headless Chromium run (ephemeral loopback server, serves only $OUT)"
PORT_FILE="$BUILD/server.port"
python3 -I "$HERE/tools/serve_loopback.py" --root "$OUT" --port-file "$PORT_FILE" 2> "$BUILD/server.log" &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do [ -s "$PORT_FILE" ] && break; sleep 0.1; done
[ -s "$PORT_FILE" ] || { echo "loopback server did not bind" >&2; exit 1; }
PORT="$(cat "$PORT_FILE")"
python3 -I "$HERE/tools/serve_loopback.py" --probe "$PORT"
timeout "$BROWSER_TIMEOUT" "${NODE:-node}" "$HERE/tools/browser_probe.mjs" "$CHROMIUM" "http://127.0.0.1:$PORT/index.html$BROWSER_QUERY" "$BUILD"

python3 -I - "$HERE" "$BUILD" "$OUT" "$("$JAVA" -version 2>&1 | head -1)" <<'PY'
import hashlib, json, pathlib, sys
here, build, out, java = (pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4])
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
committed = sorted(p for p in here.rglob("*") if p.is_file() and "build" not in p.relative_to(here).parts
                   and ".gradle" not in p.relative_to(here).parts and "__pycache__" not in p.relative_to(here).parts)
(build / "toolchain.json").write_text(json.dumps({
    "java": java, "teavm": "0.16.0 (org.teavm plugin and teavm-jso)",
    "outputSha256": {"face.wasm": digest(out / "face.wasm"), "face.wasm-runtime.js": digest(out / "face.wasm-runtime.js")},
    "outputBytes": {"face.wasm": (out / "face.wasm").stat().st_size, "face.wasm-runtime.js": (out / "face.wasm-runtime.js").stat().st_size},
    "experimentSourceSha256": {str(p.relative_to(here)): digest(p) for p in committed},
    "generatedSourceSha256": {p.name: digest(p) for p in sorted((build / "generated-src").glob("*.java"))},
    "closure": json.loads((build / "closure.json").read_text()),
}, indent=2) + "\n")
PY

echo "== validation (native jar vs JVM extracted vs WasmGC, both sizes, two cameras, adapter variants, vertex control)"
python3 -I "$HERE/tools/check_evidence.py" --build "$BUILD" ${MUTATE_ARGS[@]+"${MUTATE_ARGS[@]}"}
