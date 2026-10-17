# WebKitGTK compatibility probe

Runs the existing `wasm-decoded-face` WasmGC module unchanged in a WebKitGTK view.
This checks a relevant Linux Tauri engine boundary. It builds/runs no Tauri binary
and supplies no performance, gamepad, Gamescope or full-client evidence.

First build the [decoded-face experiment](../wasm-decoded-face/README.md), then run:

```sh
python3 -I experiments/wasm-webkit/probe.py
```

Requires Linux, Xvfb, PyGObject with GTK3 and WebKit2 4.1 introspection. It uses an
owned Xvfb display, forced software GL, an ephemeral WebKit data store and a local
HTTP server serving only the three existing original-fixture frontend files.
It does not open the owner's browser, display, profiles, saves or native game.

The existing checker compares all12 cases with the native jar and extracted JVM,
including Canvas readback and the four actual corruption controls. Inputs are
hashed before/after. Results, DOM and diagnostics remain ignored under
`.runtime/wasm-webkit/run-*`. Missing inputs/dependencies or an unfinished run
fail; there is no fallback to Chromium or a previously collected result.

The measured host result and deployment recommendation are in
[the dated Tauri investigation](../../docs/TAURI_WASM_INVESTIGATION_20261017.md).
