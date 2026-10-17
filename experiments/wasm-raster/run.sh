#!/usr/bin/env bash
# Usage (from the repository root):
#   bash experiments/wasm-raster/run.sh /absolute/path/to/ha_Sub1.java /absolute/path/to/void-client-0.2.0_a2.jar
# Extracts the native kernel into build/, runs the JVM reference variants, builds the TeaVM WasmGC
# module, and serves only the generated output directory on loopback for one headless Chromium run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
NATIVE_SRC="${1:?absolute path to ha_Sub1.java required}"
NATIVE_JAR="${2:?absolute path to void-client-0.2.0_a2.jar required}"
JDK="${JAVA_HOME:?set JAVA_HOME to a JDK 21 directory}"
JAVAC="$JDK/bin/javac"
JAVA="$JDK/bin/java"
UPSTREAM_GRADLEW="${UPSTREAM_GRADLEW:-$HERE/../../upstream/runelite-client/gradlew}"
PORT="${PORT:-8765}"
BUILD="$HERE/build"
OUT="$BUILD/teavm-out"
CHROMIUM="${CHROMIUM:-/usr/bin/chromium}"

case "$NATIVE_SRC" in /*) ;; *) echo "ha_Sub1.java path must be absolute" >&2; exit 2 ;; esac
case "$NATIVE_JAR" in /*) ;; *) echo "jar path must be absolute" >&2; exit 2 ;; esac
[ -f "$NATIVE_SRC" ] && [ -f "$NATIVE_JAR" ] || { echo "missing native input" >&2; exit 2; }

rm -rf "$BUILD"
mkdir -p "$BUILD"
python3 -I "$HERE/tools/extract_face_kernel.py" --src "$NATIVE_SRC" --out "$BUILD/generated-src"

echo "== closure audit (verbatim kernel, no jar on classpath)"
"$JAVAC" -Xlint:all -d "$BUILD/audit" "$BUILD"/generated-src/*.java
echo "audit: PASS"

echo "== JVM verbatim kernel"
"$JAVAC" -d "$BUILD/jvm-verbatim" "$HERE"/src/shared/java/*.java "$BUILD"/generated-src/*.java "$HERE"/src/jvm/java/VerbatimJvm.java
"$JAVA" -cp "$BUILD/jvm-verbatim" VerbatimJvm | tee "$BUILD/jvm-verbatim.jsonl"

echo "== JVM reference: real jar bytecode"
"$JAVAC" -nowarn -cp "$NATIVE_JAR" -d "$BUILD/jvm-native" "$HERE"/src/shared/java/Raster.java "$HERE"/src/shared/java/Scene.java "$HERE"/src/jvm/java/NativeJar.java
"$JAVA" -cp "$BUILD/jvm-native:$NATIVE_JAR" NativeJar | tee "$BUILD/jvm-native.jsonl"

echo "== TeaVM 0.16.0 WasmGC build"
if [ -f "$UPSTREAM_GRADLEW" ]; then GRADLE="$UPSTREAM_GRADLEW"; else GRADLE="${GRADLE:-gradle}"; fi
JAVA_HOME="$JDK" bash "$GRADLE" -p "$HERE" buildWasmGC --no-daemon -q
WASM_DIR="$(find "$HERE/build" -path '*teavm*wasm-gc*' -name 'raster.wasm' -printf '%h\n' | head -1)"
[ -n "$WASM_DIR" ] || { echo "wasm output not found" >&2; exit 1; }
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$WASM_DIR"/raster.wasm "$WASM_DIR"/raster.wasm-runtime.js "$OUT"/
cp "$HERE/web/index.html" "$OUT"/
echo "module raw bytes: $(stat -c %s "$OUT/raster.wasm")  gzip -9 bytes: $(gzip -9 -c "$OUT/raster.wasm" | wc -c)"
echo "runtime js bytes: $(stat -c %s "$OUT/raster.wasm-runtime.js")"
echo "sha256 raster.wasm: $(sha256sum "$OUT/raster.wasm" | cut -d' ' -f1)"

echo "== headless Chromium run (serves only $OUT on 127.0.0.1:$PORT)"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$OUT" >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
sleep 1
"$CHROMIUM" --headless=new --no-sandbox --disable-gpu --virtual-time-budget=30000 \
  --dump-dom "http://127.0.0.1:$PORT/index.html" 2>/dev/null > "$BUILD/browser-dom.html" || true
python3 -I - "$BUILD/browser-dom.html" <<'PY'
import html, re, sys
dom = open(sys.argv[1], encoding="utf-8", errors="replace").read()
m = re.search(r'<pre id="result">(.*?)</pre>', dom, re.S)
print(html.unescape(m.group(1)) if m else "NO RESULT IN DOM")
PY
