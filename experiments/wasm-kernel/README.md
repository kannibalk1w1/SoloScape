# Isolated Java → WasmGC probe

This is a compiler boundary experiment, not a browser client. It uses the existing matched client jar read-only; it does not launch a game, server or launcher, or load game/cache assets. It adds no runtime dependency to the native product. TeaVM 0.16.0 has an Apache-2.0 project licence; dependencies still require their own inventory before distribution.

Prerequisite: pinned, patched source build from README-SOLOSCAPE.md and local JDK 21. From the repository root:

```bash
JAVA_HOME="$PWD/.runtime/jdks/jdk21" bash upstream/runelite-client/gradlew \
  -p "$PWD/experiments/wasm-kernel" -Pprobe=controller buildWasmGC --no-daemon
```

The controller probe invokes the **unchanged** `StickMath` bytecode from the jar and asserts a deadzone result. The presenter probe tries to allocate the native 765×503 software framebuffer surface:

```bash
JAVA_HOME="$PWD/.runtime/jdks/jdk21" bash upstream/runelite-client/gradlew \
  -p "$PWD/experiments/wasm-kernel" -Pprobe=presenter buildWasmGC --no-daemon
```

**Presenter failure is expected on the inspected baseline:** missing `java.awt.Rectangle`, `java.awt.image.DirectColorModel` and `Loader`'s `java.applet.Applet`. This is a measured portability blocker, not a native-product regression. Each variant uses its own ignored build directory, preventing a failed presenter build from being mistaken for the last successful controller module. Normal root CI does not require network downloads or private client jars to run this experiment.

For the successful controller module, place this `index.html` in its generated output directory (`build/controller/generated/teavm/wasm-gc/`) and serve **only that directory**, bound to localhost:

```html
<!doctype html><meta charset="utf-8"><body id="result">WAIT
<script src="probe.wasm-runtime.js"></script><script>
TeaVM.wasmGC.load('probe.wasm').then(runtime => {
  runtime.exports.main([]);
  document.getElementById('result').textContent = 'PASS';
}).catch(error => { document.getElementById('result').textContent = 'FAIL: '+error; });
</script>
```

```bash
python3 -m http.server 8765 --bind 127.0.0.1 \
  --directory experiments/wasm-kernel/build/controller/generated/teavm/wasm-gc
```

Open localhost:8765 in a WasmGC-capable browser, verify PASS and check the console. Do not serve the repository root or any cache/profile directory. The recorded first run used equivalent scaffolding under `.runtime/research-20261017/`; the tracked controller variant was subsequently rebuilt and executed successfully, and the separate tracked presenter variant reproduced the expected compiler rejection. No browser frame-rate, game-memory, whole-client compatibility or renderer benchmark follows from this tiny test. [Evidence](../../docs/evidence/research-20261017/wasm-probe.json), [next gate](../../docs/WASM_SPIKE_PLAN.md).
