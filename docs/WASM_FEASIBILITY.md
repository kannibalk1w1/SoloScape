# WebAssembly feasibility for SoloScape

Research date: 17 October 2026. Native baseline: merged `502df96`, revision 634 with client 0053/server 0022. **Keep Steam Deck/native Linux primary.** WASM is a possible deployment track, not a reason to change pre-EoC mechanics, server authority, saves or the native controller architecture.

Recommendation: **later**, a bounded software-framebuffer/compiler-isolation experiment, then an existing Java server behind an explicitly scoped browser transport if rendering succeeds. Do not approve a whole-client rewrite, local browser server or universal transport abstraction now. The small compiler boundary experiment below is complete; a playable browser prototype is not.

Follow-up: the [native flat-colour triangle investigation](WASM_RENDERER_INVESTIGATION.md) now matches colour/depth hashes for original synthetic geometry at two sizes. [Bulk pixel transfer](WASM_TRANSFER_INVESTIGATION.md) removes much of the earlier host-call overhead. Full model/scene rendering and the application/platform boundary remain unproven. This does not change the native-first recommendation.

## Inspection and measured boundary experiment

The client targets/runs Java 8 because `Loader` extends Applet. JDK 21 runs its Gradle build/tooling; the Kotlin server is JVM 21. RuneLite-style plugins, Guice/reflection, Swing/EDT, AWT Canvas, overlays, native rendering, filesystem and socket threads make the client substantially more than a Java rasterizer.

Measured in this checkout: 1,224 client `.java` sources; 243 contain AWT/Swing imports (simple source scan, not a transitive closure). `ha_Sub1` maintains an integer pixel buffer; `Class348_Sub31_Sub1.method3008` wraps an `int[]` with `DataBufferInt`/`DirectColorModel`/`BufferedImage` and presents through AWT. This is a useful boundary, but not an already portable renderer. The RuneLite overlay buffer has another AWT image path.

[Probe source/instructions](../experiments/wasm-kernel/README.md) and [sanitized result](evidence/research-20261017/wasm-probe.json): TeaVM 0.16.0 on JDK 21 compiled **unchanged SoloScape `StickMath` bytecode** to WasmGC and it executed its expected-result assertion in headless Chromium 153. Initial module 24,975 bytes plus 17,268-byte JS loader; this is a tiny kernel, not a whole-game payload estimate. A separate native presenter root failed with missing `java.awt.Rectangle`, `java.awt.image.DirectColorModel` and reachable `Loader extends java.applet.Applet`. This tests that dependency boundary; it is not an attempted full client port, proof of renderer performance, or evidence that replacing three class names fixes all blockers.

## Blocker matrix

Paths are relative to the relevant ignored upstream checkout, reproducible with the tracked patches.

| Subsystem | Current technology / inspected path | Browser/WASM compatibility | Main blocker | Possible bounded approach |
| --- | --- | --- | --- | --- |
| Client runtime | Java 8, `Loader.java`, `client/build.gradle.kts`; Gradle runs JDK 21 | Tool-dependent | Applet lifecycle, JRE APIs and platform bootstrap | Keep native loader; a separate experimental bootstrap only after renderer closure is understood |
| Window/UI | `net/.../ui/ClientUI`, Swing/EDT, AWT Canvas, custom stone/font overlays | Low under AOT; fuller JVM emulation may help | DOM is not AWT; event queue/focus/window peers, scaling | Browser presenter and shell; preserve logical screen/action models |
| Software rendering | `ha_Sub1.anIntArray7483`, `Class348_Sub31_Sub1`, `Class348_Sub31_Sub2` | Plausible subset, unverified full scene | Global native/client dependencies, AWT image presentation, worker/context state | Isolate raster core and expose framebuffer; prove one region before porting interfaces |
| GPU rendering | `ha_Sub2`, bundled `jaggl`; `jagdx`/other wrappers in local jars | Not directly compatible | JNI/OpenGL/DirectX contexts and native binaries | Software first; later WebGL/WebGPU backend if measured CPU budget fails |
| RuneLite integration | Hooks/event bus, plugin manager, Guice, dynamic config proxies and reflection | Partial/rewrite or JVM-emulation evaluation | Class discovery, reflection, desktop plugins and overlays | Small explicit plugin set; retain native RuneLite product; do not claim all plugins portable |
| Input/state | `UiControls.Gateway`, `StickMath`, `WorldControls`, `MenuNavigation`, `SelectionReturn` | Medium–high reusable logic | SDL/JNA polling, AWT focus, Steam keyboard invocation are native adapters | Browser Gamepad/DOM adapter feeding the same normalized states; compile/test actual closure |
| Game/cache network | `Class202`, `Class238_Sub1`, native login/cache handshake and packet stream | Low unchanged | TCP sockets, blocking I/O and asynchronous browser APIs | Authenticated local WebSocket↔TCP bridge or revised client I/O adapter; preserve ordered bytes and protocol parsing |
| Cache/files | Client `Class234` RandomAccessFile; server `FileCache`, disk indices/JS5 | Medium after adapters | Blocking/random-access files, download protocol, quotas and cache integrity | User import → immutable local content-addressed store; async preload/worker adapter; retain index/CRC semantics |
| Threads | Client/render/input/audio/network workers, EDT and `DetachedRenderer`; server coroutines/executors | Tool/backend-dependent | Browser UI cannot block; workers and WasmGC objects are not a shared native JVM heap | One worker for isolated raster/simulation; message passing; audit threading before reuse |
| Reflection/loading | Guice, config proxies, class loaders, script registration/metadata | Poor for unrestricted AOT | Closed-world reachability vs dynamic types | Explicit metadata/generated registration for a selected experiment, not a sweeping native refactor |
| Native libraries | JNA SDL2, jaggl/jagdx, native library loaders and platform helpers | No direct binary reuse | OS ABI/JNI not browser ABI | Replace or exclude adapters; recompiling available C sources still needs browser bindings/licence review |
| Images/fonts | AWT ImageIO/BufferedImage, native cache sprites/bitmap fonts | Partial | JVM image peers/decoders, palette/alpha/layout | Keep native cache decode as data where separable; transfer RGBA; no asset hotlinking |
| Audio | `Class279_Sub1` AudioSystem/SourceDataLine and game sample formats | Requires adapter | User gesture, timing and AudioContext lifecycle | WebAudio bridge after core scene; silent initial graphics spike is explicit |
| Launcher | Swing + ProcessBuilder → Python JSON backend → Java server/client, POSIX locks/pidfd | Not portable | No Python/JVM process launch, `/proc`, flock or host JVM management in ordinary page | Separate browser import/profile shell; remote/local native helper is a different deployment model |
| Server simulation | Kotlin/JVM21, 600 ms `GameLoop`, engine stages, native authority | Low unchanged | JVM dependencies, `ContentLoader.kt` Class.forName/constructors, clocks and platform scheduling | Retain JVM server first; isolated simulation kernel only as later experiment |
| Server networking | Ktor sockets/channels, selector/cached executor, `GameServer.connect` | Low unchanged | Real TCP listener, login/file routing and channels | Preserve real server; bridge ordered transport initially; isolated in-memory channel test later if justified |
| Persistence | TOML player/world/exchange state; generations, zip/checksums, atomic metadata and locks | Concept reusable, implementation not drop-in | Browser transactions/lifetimes/eviction; no native process ownership | Versioned browser generations, transactional commit pointer, export/import and verified external backups |
| Optional DB/web | JDBC/PostgreSQL behind `includeDb`; JVM Ktor web module | No direct page runtime | JDBC/native services and server-side APIs | Keep optional DB excluded from local web spike; do not pretend the full server is Kotlin/Wasm-compatible |
| Suspend/background | Live world/timers plus long-input-gap guard; no true solo pause | High semantic risk | Tab throttling/discard, browser/OS suspension | Explicit safe checkpoint/stop policy; no hidden catch-up, especially with guests |

## Strategy comparison

Feasibility here means **a useful bounded deployment experiment**, not probability of shipping unchanged SoloScape. Cost is relative engineering work, not a calendar quote.

| Route | Feasibility | Cost | Current code reuse | Major blockers | Small discriminating prototype |
| --- | --- | --- | --- | --- | --- |
| A1: TeaVM AOT Java subset → WasmGC/JS | MEDIUM for isolated kernels; LOW for unchanged client | HIGH (whole client VERY HIGH) | Pure maths/navigation, selected codecs/raster algorithms; wider closure unmeasured | AWT/Applet, reflection/Guice, JNI, blocking I/O and globals | Next isolate one actual software raster path and present its framebuffer; compile failures are stop evidence |
| A2: CheerpJ browser JVM | MEDIUM for compatibility evaluation | MEDIUM for evaluation, HIGH for product integration | Potentially much bytecode/AWT/reflection; native methods still need replacements | jaggl/SDL/JNA, TCP bridge, runtime licence/offline hosting, memory/performance | Software-only minimal client/window using locally imported data and documented networking; never assume a successful Swing demo proves this game |
| A3: Bytecoder AOT | LOW for this whole application; MEDIUM for a small kernel | HIGH | Selected Java algorithms; application reuse unmeasured | Partial platform runtime and adapters; no verified RuneLite/AWT/native path | Compile the same kernel/presenter roots before investing in another toolchain |
| B: browser client + existing Java server | MEDIUM after renderer proof | VERY HIGH for a new full frontend; HIGH if current core can be adapted | Most server rules/data; protocol/assets/controller logic selectively | Rendering/widgets/login/cache protocol, frontend input/UI, bridge security | Local ordered-byte WebSocket bridge + a tiny protocol observer, then actual scene; no new full client now |
| C: client + local server in browser worker/WASM | LOW now | VERY HIGH | Some game/domain algorithms; not complete JVM engine/runtime unchanged | JVM21/Ktor/Koin/reflection, sockets, persistence, tick clocks, browser lifetime and memory | Only after A/B: one isolated engine stage/tick with a mocked transport/storage, deterministic JVM parity |
| D: protocol-free integrated solo runtime | LOW near-term | VERY HIGH | Conceptual simulation rules; removing serialization changes current boundary | Two languages/platforms, shared-state ordering, authority, tick/event semantics, multiplayer divergence | Later in-memory channel contract before any protocol-free runtime; do not implement now |

### Tool health and licensing, checked rather than inferred

- **TeaVM:** Apache-2.0; release 0.16.0 published 2 October 2026, source activity 16 October. It is a closed-world compiler with restrictions on reflection/class loading/JNI and does not supply desktop Swing compatibility. Current `TThread.start` uses Fiber/EventQueue on WasmGC; this is not evidence of native shared-memory parallelism. Its new Emscripten integration is a separate binding task, not automatic execution of existing `.so` files. Sources: [overview](https://teavm.org/docs/intro/overview.html), [release](https://github.com/konsoletyper/teavm/releases/tag/0.16.0), [thread implementation](https://github.com/konsoletyper/teavm/blob/cfc0ce2a9874a4ce38b48adb90bc91ca0e75528/classlib/src/main/java/org/teavm/classlib/java/lang/TThread.java), [native interop](https://www.teavm.org/docs/wasm-gc-backend/emscripten.html).
- **CheerpJ:** current documentation describes version 4.3, Java 8/11/17, reflection, dynamic loading and AWT/Swing. That fits the client better than a partial class library, but does not make our Java21 server supported. Native OS/JNI libraries need adaptation. Source: [runtime overview](https://cheerpj.com/docs/overview.html), [compatibility](https://cheerpj.com/compatibility-new/), [native bridge](https://cheerpj.com/docs/guides/implementing-native-libraries). Documentation contains differing example/version pages; evaluate a pinned runtime, not an unversioned promise.
- **CheerpJ licensing:** the documented Community terms cover individuals/FOSS/evaluation with conditions/credits and CDN use; self-hosting/redistribution/OEM require separate commercial terms. Self-contained offline delivery therefore needs explicit review; do not assume a free self-hosted runtime. [Terms](https://cheerpj.com/docs/licensing). Networking supports documented tunnelling options including Tailscale; plain browser pages still do not gain arbitrary TCP. [Networking guide](https://cheerpj.com/docs/guides/Networking.html).
- **Bytecoder:** Apache-2.0; inspected head `67bb35966931`, activity 5 October 2026. README advertises Java 8–20/OpenJDK20 class library. Active repository activity is not proof of Java21/server compatibility or platform desktop support; neither was compiled here. [Project/source](https://github.com/mirkosertic/Bytecoder). Keep as an alternate small-kernel experiment, not the default whole-client recommendation.

No new compiler/runtime dependency was added to the native game. Dependency and game-asset licence inventories remain release gates. The research source inventory records API-reported licences and pins; absence of a detected root licence is not permission.

## Graphics routes

| Approach | Reuse / cost | Evaluation |
| --- | --- | --- |
| CPU raster → Canvas ImageData | Most promising first presentation boundary; retain pixel algorithms and 2011 visuals | Strip/replace presentation, not assume AWT translates. Measure channel order, clipping, alpha, resize and transfers. Integer `0xRRGGBB` needs explicit RGBA conversion; little-endian aliasing is not automatically correct. |
| CPU framebuffer → WebGL texture | Same CPU scene raster, GPU composition/scaling | May reduce presentation/scaling cost; does not accelerate model rasterization. Texture upload/copy bandwidth and context loss require measurement. |
| Direct WebGL renderer | Potentially much faster scenes | Substantial JNI/OpenGL state/shader/texture adaptation, precision and visual parity risk. Current OpenGL wrapper cannot simply be called from Java WASM. |
| WebGPU | Potential later backend | New pipeline/resource model plus browser/device support and port effort. No evidence it is required for the first scene; not a substitute for understanding the current renderer. [WebGPU API](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API). |
| Purpose-built scene renderer | Can consume decoded models/maps/widgets | Approaches a new client. Protocol, animation, UI and pre-EoC presentation parity remain large tasks; reject as the first prototype. |

A CPU framebuffer is an advantage **if** the raster core can be isolated without pulling platform/global client initialization. The measured presenter failure is the reason to test that closure before implementing browser transport or a large UI. Native software timings are not browser performance predictions.

## Networking and authority

Keep the simulation authoritative even when client and server eventually share a device. Browser code submits intentions/actions, not tile/inventory writes. Preserve native packets, ISAAC/framing/login/cache handshakes, ordered stream semantics, negotiated SoloScape features, rejection and disconnect behavior.

A WebSocket bridge is the smallest **later** transport experiment: browser binary messages → bounded byte stream → one explicitly configured JVM endpoint, with backpressure, fragmentation/reassembly tests and orderly close. Both game login and cache traffic need coverage. Do not equate a WebSocket frame with a game packet. Ordinary browsers expose WebSocket, not arbitrary TCP listeners/sockets; WebTransport is not a drop-in TCP implementation. [Browser WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API).

Use loopback-only helper or an authenticated WSS service with an origin allowlist, fixed destination and session authorization. Never expose an arbitrary TCP proxy or assume localhost is accessible/trusted from every HTTPS page. A remote JVM server supports demos/private co-op but is not self-contained offline single-player; a locally installed helper defeats the lowest-admin-device goal.

`network/.../GameServer.kt:connect(ByteReadChannel, ByteWriteChannel, hostname)` already separates accepted sockets from login/file routing. That is a useful experiment seam. The client has several socket wrappers and asynchronous cache/login paths (`Class202`, `Class238_Sub1`), so a single `GameTransport` interface does **not** currently isolate the entire boundary. Existing `UiControls.Gateway` is an action/UI seam, not a transport.

Do not add `TcpGameTransport/WebSocketGameTransport/InProcessGameTransport` across production now. First prove bounded channel parity with the unchanged network parser and record ownership/flush/cancel/error semantics. A later transport seam may help headless testing, replay and co-op; replay additionally requires tick order, seed, clock and external-input determinism. In-process byte channels would preserve protocol authority more safely than immediately removing the protocol. A protocol-free shared object runtime is a separate design decision.

## Browser persistence and lifecycle

Keep the concepts in `scripts/profiles.py`: versioned profile identity, complete world/exchange state, checksummed manifests, retained generations, validated import/restore, explicit retention and a commit pointer switched only after validation. Never reduce saves to one mutable localStorage value or equate a completed JS call with durable backup.

| Store | Use | Limit |
| --- | --- | --- |
| IndexedDB | Transactional profile metadata, active generation pointer and small state | Async APIs and quota; transaction lifetime must not span arbitrary awaits |
| OPFS | Larger imported cache/blobs or immutable world-generation files | Origin-private, quota-bound; worker synchronous access is not POSIX flock/fsync/rename semantics. [OPFS](https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system) |
| Download/import archive | Explicit external verified backup, device transfer and recovery | User must retain it; validate hashes/schema/path traversal/size/ownership before activation |
| File System Access picker | Optional direct user-selected archive/export convenience | Browser/permissions vary; keep ordinary file input/download fallback |
| Service-worker Cache API | Versioned app shell and permitted immutable resources | Derived assets only; not the authoritative save commit store |

Proposed commit: write a new immutable generation, verify hashes/schema, then transactionally switch the IndexedDB pointer; retain the old generation. Crash tests cover each step, multiple tabs need a single-writer lease/lock plus fencing token, and migration runs on a copy. A browser backup in the same origin can be evicted with the original, so it is not an independent backup.

Request persistence via `navigator.storage.persist()`, report estimate/failure, and require/export a verified external archive before an important migration. Persistence can be denied and user clearing/site removal can still delete data. Never promise “no eviction” or silent safe offline storage. [Storage quotas/persistence](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria). Browser visibility/unload hooks are insufficient to guarantee a final save: checkpoint during play, expose explicit Save & Quit and show last successful commit/export. [Page lifecycle limits](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API).

For Strategy B, server saves remain authoritative on the JVM host; a browser export is a request for an owner-authorized snapshot, not access to local server paths. For C/D, background throttling/tab discard can stop timers; design explicit suspension policy and durable checkpoint first. Multiplayer guests preclude silently freezing the shared server. LMS iframes add storage partitioning, focus and Permissions Policy/COOP-COEP constraints; embedding is a later acceptance target.

## Controller/browser interaction

Reuse logical input/state machines where their compile closure permits. Replace SDL/JNA/Steam invocation with an adapter producing `GamepadState`: normalize standard mapping, button edges, stick/deadzone, timestamps, hotplug and disconnect. Poll `navigator.getGamepads()` on the animation/UI side; do not assume a worker has that API. On blur/hidden/tab switch/disconnect, send neutral/stop, clear stale actions, require neutral/release-and-push before world/camera resumes. A throttled callback must not preserve a held movement intent indefinitely.

Browser exposure often requires a secure context and user activation; mappings/indices are not persistent device identity. Test Xbox, PlayStation and actual Steam Deck browser-in-Gaming-Mode exposure with the chosen Steam Input layout: browser exposure has **not** been physically verified here. Haptics are optional/feature-detected; no reliance on universal rumble. [Gamepad guide](https://developer.mozilla.org/en-US/docs/Web/API/Gamepad_API/Using_the_Gamepad_API), [vibration actuator](https://developer.mozilla.org/en-US/docs/Web/API/GamepadHapticActuator).

Browser/Steam shortcuts can steal buttons; focus/held-A/tab ownership needs actual hardware tests. Use real focused HTML text fields for the initial browser shell and one explicit text owner; suppress game actions during IME/virtual keyboard entry. Keep local controller keyboard and touch/trackpad fallback. Never synthesize global browser shortcuts as normal game actions.

## Size, memory and performance envelope

Measured local file sizes, **not web download estimates**:

| Component | Bytes | Meaning |
| --- | ---: | --- |
| Compatible cache files | 193,740,377 (~184.8 MiB) | Logical disk bytes; client need not preload every archive |
| Recorded original cache archive | 160,832,267 (~153.4 MiB) | Historical 7z input from CACHE_SETUP; not an authorized browser distribution package |
| Native shadow client jar | 14,355,677 (~13.7 MiB) | Includes dependencies/resources; AOT reachability may differ |
| Native shadow server jar | 49,790,698 (~47.5 MiB) | JVM server only; not a runnable browser server |
| Tiny measured WasmGC kernel + loader | 24,975 + 17,268 | Only StickMath and minimal runtime closure; not scene/JVM size |

Full browser-runtime, compressed-client and initial-scene payload sizes/startup are **unknown until built and measured**. A naive full-cache path already starts near 185 MiB before runtime, client, indices, decoded structures and duplicated transfer buffers. Initial interactive subset should be measured from actual archive access logs; lazy cache loading needs correct archive integrity and dependency warmup. Content-addressed immutable packs and IndexedDB/OPFS caching are plausible after profiling; do not pre-cache every region on install.

One 1280×800 RGBA framebuffer is 4,096,000 bytes (~3.91 MiB), or 245.76 MB/s at 60 uploads/s before extra copies. At 765×503 it is 1,539,180 bytes, ~92.35 MB/s. These are arithmetic bandwidth envelopes, not GPU/bus benchmarks. Double buffering, JS copies, textures, depth buffers, decoded assets and WasmGC/JVM heaps add memory. Use transferable buffers or suitable interop only after verifying layout/lifetimes.

Native r29 peak client/server RSS was ~1.28/1.62 GiB (sum peaks is not a simultaneous unique-memory measure). It cannot predict browser heap use. Wasm32 linear memory has a 4 GiB address-space ceiling; practical browser allocation/process limits and WasmGC heap limits differ and can be much lower. Memory64 is not a guarantee that a Chromebook/tablet can host the native working set. [WASM memory model](https://webassembly.org/docs/portability/). Shared memory/threads may require secure cross-origin isolation; that affects LMS embedding and third-party resources. [SharedArrayBuffer requirements](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer).

Native server uses a 600 ms tick, but no current browser server tick-cost figure exists. The current headless browser sanity run's process wall time includes browser startup/virtual-time behavior and must not be sold as game startup/latency. Record cold/warm bytes, decoded memory, frame tails, server stage timing, save commit/export time, cache warmth, power and device for any later scene test.

## Distribution boundary and decision

A public web deployment must not silently distribute cache/model/sprite/audio/interface data just because HTTP makes it convenient. First experiments use **local user-selected authorized data**, browser-side inspection/conversion on a disposable import, or original synthetic assets. Do not serve private caches through a repository-root development server, embed keys in a public bundle, or commit generated bytecode/resources copied from opaque native jars. Generated cache patch bytes can themselves contain proprietary data; “patch” is not a rights exemption.

Code/runtime/bundled-library licences and game-asset permissions are separate unresolved distribution questions. OpenRS2 availability and upstream BSD headers are not blanket asset permission. CheerpJ self-host/offline terms need separate review; source-readable libraries without a clear licence need permission before reuse. No legal conclusion about a public RuneScape-derived service is made here.

**Decision:** native physical acceptance and lifecycle/performance fixes first. Retain the successful tiny-kernel and failed-presenter evidence; later fund the [single framebuffer spike](WASM_SPIKE_PLAN.md). Prefer the existing Java server if that succeeds. Defer local WASM server, integrated protocol-free runtime, new renderer and public/offline packaging until separate measured gates pass.

## Tauri follow-up — 17 October 2026

The [Tauri investigation](TAURI_WASM_INVESTIGATION_20261017.md) and [WebKitGTK compatibility probe](../experiments/wasm-webkit/README.md) now pass the existing12-case original decoded-model fixture plus four controls in host WebKitGTK2.54.1. This is engine compatibility, not a Tauri build or performance advantage. A wrapper can aid desktop deployment later; it does not remove full-client/scene, protocol, ownership, target-device or distribution gates. Native Deck remains primary.
