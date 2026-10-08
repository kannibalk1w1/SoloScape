# Controller provider decision

The first camera prototype uses **SDL2's GameController API** with direct native
mapping through **JNA 5.19.1** (`net.java.dev.jna:jna`). Decision recorded before
adding the dependency. No JNA platform module or rendering/game engine is needed.

- [JNA](https://github.com/java-native-access/jna) is maintained and publishes
  prebuilt JNI dispatch libraries in its core Maven artifact. Its current
  [licence](https://github.com/java-native-access/jna/blob/master/LICENSE) offers
  Apache-2.0 or LGPL-2.1-or-later; choose Apache-2.0 and preserve notices.
  Java 8 bytecode compatibility will be verified by the build/runtime tests.
- [SDL2](https://github.com/libsdl-org/SDL/tree/SDL2) uses the zlib licence. Use
  the system `libSDL2` on Linux/SteamOS. Require SDL2 **2.0.22+** for Deck-era
  mapping support; actual Steam Deck hardware still needs acceptance testing.
  Xbox/PlayStation mappings come from SDL, not hardcoded Linux event numbers.
- Poll [SDL_GameControllerUpdate](https://wiki.libsdl.org/SDL2/SDL_GameControllerUpdate)
  and mapped axes/buttons on the client thread. SDL handles attached-device state;
  the provider closes detached handles and scans for a replacement controller.
- Packaging: Shadow includes JNA and its platform dispatch resources. SDL2 itself
  remains a system prerequisite. A missing/incompatible native library disables
  the plugin with an actionable error; keyboard/mouse still work. Bundling SDL2
  or supporting Windows is a later packaging decision.
- Keep mutable input state and primitive direct mappings so polling does not
  construct a new controller-state object each update. Device strings are read
  only when a controller connects. Do not claim zero allocations inside JNA/SDL.
- Jamepad was considered. Its original project's current README points to a
  successor and additional wrappers; this narrow binding needs fewer dependencies
  and can use the maintained system SDL2 directly. Raw `/dev/input` access was
  rejected because it would duplicate device mapping and hotplug handling.

Runtime licence inventory for this addition is separate from the pending licence
audit of existing upstream client binaries. No proprietary game data is included
in the controller patch.
