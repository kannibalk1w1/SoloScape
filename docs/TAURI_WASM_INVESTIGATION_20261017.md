# Tauri and the WASM experiment — 17 October 2026

Tauri is a plausible future desktop shell for a browser-capable SoloScape frontend. It is **not an established performance upgrade** over the current JVM client. Continue native Deck delivery; keep this investigation on draft PR27.

## What the wrapper changes

Tauri's core is native Rust, but its frontend executes in the platform webview. Linux uses WebKitGTK, Windows uses WebView2 and macOS uses WKWebView. Avoiding a bundled web engine can reduce shell distribution size; it does not remove SoloScape's cache or the Java server runtime, nor prove lower game CPU/memory cost. [Official process model](https://v2.tauri.app/concept/process-model/).

A Tauri shell could provide native windows, file selection and controlled access to local saves. Its sidecar support can launch an external executable, but ordinary sidecar launching is not proof of SoloScape's inherited guards, process ownership, primary-save acknowledgement or recovery. Those contracts need explicit integration. [External binaries](https://v2.tauri.app/develop/sidecar/).

The updater plugin supports signed artifacts. That is useful package-authority machinery, not an implementation of matched client/server/cache identity, stopped-world activation, backups, compatibility or rollback retaining later progress. Do not replace the current native launcher merely to obtain this plugin. [Official updater](https://v2.tauri.app/plugin/updater/).

## Actual engine proof

The unchanged decoded-face WasmGC module now passes in host **WebKitGTK2.54.1**, using an ephemeral webview on an owned Xvfb display with software GL. The [original probe](../experiments/wasm-webkit/README.md) serves only the existing three fixture frontend files over ephemeral loopback. It does not build Tauri or use the owner desktop/browser.

All12 model/camera/size cases match the existing native-jar and extracted-JVM output, including decoded/projected arrays, face selection, palette and colour/depth hashes. The1280×800 Canvas readback matches`a0bf99a6`. Four deliberately corrupted inputs fail in the existing checker with exit1. Bridge inputs remain byte-identical before/after. [Sanitized evidence](evidence/wasm-webkit-20261017.json).

This establishes this host engine's ability to run this exact TeaVM0.16 WasmGC fixture. It does not prove the Deck's installed WebKit version, packaged custom-protocol/MIME/CSP behaviour, an actual Tauri executable, accelerated presentation, native save/controller integration or a full game scene. No comparative timing was measured.

## Performance judgement

The wrapper changes presentation and platform integration, not the core raster algorithm. A CPU rasterizer still spends CPU time on pixels and copies a framebuffer into the browser. Rust around that code does not automatically accelerate it. Java HotSpot and a browser Wasm engine optimize differently; this repository has no matched full-scene comparison establishing a winner. These are engineering inferences, not benchmark results.

Tauri documents Linux graphics failures and possible slow WebGL/Canvas paths. A successful context or renderer string alone does not establish hardware acceleration. Our software-Xvfb proof cannot resolve target-device performance. [Official Linux graphics notes](https://v2.tauri.app/develop/debug/linux-graphics/).

| Candidate | Expected value | Outstanding evidence |
| --- | --- | --- |
| Tauri around current Java game as a sidecar | Alternate launcher/platform integration | Extra webview cannot be assumed to speed up the separate Java game; ownership and shutdown must be preserved |
| Tauri around a WASM client, existing Java server | Reuse a future web frontend with native filesystem/deployment access | Full model/scene/frontend, protocol bridge and target WebKit/performance still unproven |
| Rust/native renderer inside Tauri | Potential different rendering cost | Substantial renderer work, not a wrapper benefit; no approval or evidence for a rewrite |

## Next useful measurement

After one representative real scene is available, compare the same scene, camera, resolution and workloads on native Java, Chromium and the target WebKit/Tauri shell. Record cold/warm startup, scene/raster time, RGBA conversion, presentation, frame tails, RSS and actual Deck power/input behaviour separately. Keep pixel data inside the frontend; avoid copying every frame through Rust IPC. Use a release build and record engine/toolchain versions.

Proceed with a small Tauri executable only when its packaging/custom-protocol and lifecycle behaviour is the next uncertainty, or when a real-scene benchmark justifies the platform cost. Do not pitch Tauri/WASM as a native performance fix based on this fixture. No public package, proprietary asset redistribution or owner deployment is added.

## Bounded follow-up — 18 October 2026

Reran the existing isolated engine probe, without changing the frontend or native game.
WebKitGTK 2.54.1 passed all 12 decoded-model/camera/resolution cases against the
existing native-jar and extracted-JVM references. Canvas presentation and readback
both returned `a0bf99a6`. All four deliberately corrupted evidence variants were
rejected with exit 1; the positive check returned 0. All seven fixture/reference
input files retained their before/after SHA-256 values.
[Fresh evidence](evidence/wasm-webkit-20261018.json).

This is a fresh WebKit execution against existing native reference outputs, not a
fresh native benchmark. It uses owned Xvfb and software GL. No Tauri executable,
Deck deployment, save access or speed comparison was attempted. The result supports
keeping Tauri as a packaging option. It supplies no evidence of better FPS, memory,
power consumption or startup than the current Java app. For a small next performance
lab, use one fixed representative scene in both native Java and this same WebKit
engine, separating raster, framebuffer transfer and presentation time before adding
a shell. Do not extrapolate original-fixture timings to gameplay.
