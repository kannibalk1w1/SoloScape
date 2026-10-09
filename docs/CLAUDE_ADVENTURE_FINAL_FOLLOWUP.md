# Adventure final follow-up: port probe, owned Xvfb, probe wording and native logout clicks

This was a read-only static review. I ran no game, build or test, used no network, made no
commits, and edited no source, configuration, saves, cache or credentials. The only things I
executed were `unzip` and `javap` on local cached artifacts, to check the reuse rationale.
Scope:
- `scripts/local_dev.py` `probe_port`
- `scripts/test_port_probe.py`
- the Xvfb handshake in `scripts/smoke_profile.py`
- `scripts/harness/NativeAdventureProbe.java`: settings opening, wording, `clickNative`

## Verdict
**No correctness blockers.** The port-probe rationale checks out against the local JDK 21
source and the pinned Ktor 3.2.3 bytecode. The display ownership issue from my last review is
fixed. The settings result's wording now matches what it covers. There is one low,
actionable harness finding about native clicks.

## Verified
**`probe_port` reuse matches the server's bind**
- In JDK 21 (`.runtime/jdks/jdk21/lib/src.zip`), `sun/nio/ch/ServerSocketChannelImpl.java:135`
  creates the server fd with `Net.serverSocket(family, true)`, which calls
  `socket0(preferIPv6, stream, true /* reuse */, …)` (`Net.java:553-556`). A Java NIO server
  socket therefore starts with SO_REUSEADDR on (on Unix). I didn't read the native `Net.c` side,
  because it isn't in `src.zip`.
- In Ktor 3.2.3 (the version pinned in `upstream/game-server/gradle/libs.versions.toml`), the
  `ktor-network-jvm-3.2.3.jar` from the repo-local Gradle cache shows
  `JavaSocketOptionsKt.assignOptions`. For a `ServerSocketChannel`, it calls
  `getReuseAddress()` and **only when that is true** does `setOption(SO_REUSEADDR, true)`
  (bytecode offsets 575–608). It never writes `false`, so the JDK default stays.
- So `probe_port` (SO_REUSEADDR=1, `bind 127.0.0.1`, no `listen`) behaves like the server's own
  bind:
  - On Linux it is refused while any socket is **listening** on that address and port, even
    with SO_REUSEADDR.
  - It is allowed when only TIME_WAIT is left after a clean server-side close.
- `test_port_probe.py` covers both cases, and checks that a strict bind (no reuse) really fails
  in the TIME_WAIT case, so the test exercises lingering TCP state rather than an unused port.
- The probe and the server bind both use 127.0.0.1, matching `network.bind`. The usual gap
  between probing and binding remains, and `GameServer`'s failed-bind path handles it (patch
  0004).

**Owned Xvfb display** (`smoke_profile.py:40-59, 115`)
- `Xvfb -displayfd <pipe>` picks a free display itself and reports it through a pipe that only
  this process holds (`pass_fds`, and the parent closes its write end).
- The harness waits up to 10 s, requires a numeric reply *and* a live `Xvfb`, and only then
  sets `DISPLAY`.
- Every iteration checks `x.poll()` again and refuses to fall back to another display. The
  owned server is terminated in `finally`.
- The screenshots can therefore only see this run's private display.

**Probe settings wording**
- Step 9 now opens Settings through the plugin's real `openHomeTab` (by reflection), so
  `settingsOpeningUntil`, the grace, `presented()` and `canPresent` all run.
- The result is named `settings_gateway_two_tick_adoption`.
- The `environment` note says, accurately: "settings use the real Gateway/openHomeTab without
  SDL onClientTick … No GPU/Deck/controller acceptance."

## Finding (low, harness only)
**`clickNative` clicks by id and visibility without checking what the control is**
(`NativeAdventureProbe.java:116-135`).
- It loads 548:181 / 746:172 / 182:10, requires `ControllerUi.isVisible`, works out screen
  bounds from the raw widget geometry and the parent chain, and sends a real mouse click.
- It does **not** check:
  - that the control's native action label is the expected Exit / Logout. `actions(control,
    true)` is available, and the earlier `invokeControl` matched on it;
  - that the widget was rendered this frame, as `ControllerUi` freshness does (`Seen.frame ==
    renderFrame`).
- If the frame layout, interface id or worked-out geometry is wrong, which is most likely in
  resizable or other interface modes, the click lands on whatever is under that point. That
  could be another tab, an interface op, or a world click that walks the character, and the
  run would then fail later with "Native logout did not reach login".
- The run is disposable and private, so this isn't a data risk. But the failure would point to
  the wrong cause, and a stray click could change the private save before the save/reload
  check.

**Fix:** before clicking, require a matching action label (for example `Exit` for 548/746 and
`Logout` / "Click here to logout" for 182:10). Also require the control to be in the
`ControllerUi` recorded set for the current frame. Then record the label alongside
`native_click_<id>`. Optionally check that the centre of the worked-out box falls inside the
recorded native bounds for that widget.

## Limits
- This was static only. I didn't run or see the 47 root tests, the completed native run or
  the New/Continue repeat that is still running; those results come from your report.
- The JDK reuse default rests on the Java-level `reuse=true` argument. I didn't read the native
  `socket0` implementation, and I only checked Linux behaviour.
- No physical SDL controller, Steam Deck, GPU or gameplay acceptance is claimed. The harness
  measures a private Xvfb software session only.
