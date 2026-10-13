# Cross-device character saves

Research checked 12 October 2026. [OpenSave's user guide](https://github.com/Liquid-co/OpenSave/blob/main/USER_GUIDE.md) supports tracking an arbitrary folder or file and pairing devices. [Its CLI](https://github.com/Liquid-co/OpenSave/blob/main/docs/CLI.md) also supports Steam Deck workflows. [OpenCloudSaves](https://github.com/DavidDeSimone/OpenCloudSaves) is another candidate for provider-backed storage. Neither provider has been installed or paired by this change.

SoloScape now offers a provider-independent, **manual stopped-world transfer**. It preserves native character and exchange state, validates archive paths/checksums/size, and excludes native/server caches, session ownership records, plaintext login credentials, and client preferences. A received save creates a separate local character/world, preserving any competing local progress. Automatic selection, conflict resolution, and automatic pre-launch/post-save sync are not implemented.

1. Save & Quit on the source device. Use `python3 scripts/save_sync.py list` to identify the local profile ID and label.
2. Publish to a dedicated folder outside `.runtime/profiles`:

   ```bash
   python3 scripts/save_sync.py publish PROFILE_ID /path/to/SoloScape-sync
   ```

3. Track that dedicated folder with OpenSave on both devices using the same game/location names. Exclude `*.partial`. Pair/sync through the provider and wait until the complete `.zip` arrives.
4. On the receiving device, import the chosen bundle:

   ```bash
   python3 scripts/save_sync.py receive /path/to/SoloScape-sync/CHOSEN_BUNDLE.zip --label 'Character from Deck'
   ```

5. Open the launcher and Continue that received character. Native saved authentication is preserved; if it requests a password, use the original native character password. An empty local login password never resets the native password hash.

Bundles use unique names and remain immutable. Both devices can therefore publish without silently overwriting one another; choose which branch to continue. Old exported bundles remain until explicitly removed. Keep this folder private: native account authentication hashes are part of a save. Use the launcher's verified backups before selecting progress from another device.

Do not point a sync provider at the whole profile directory or running `states/`: runtime paths, locks and ownership records are local, and a provider cannot guarantee a coherent multi-file world while the server is saving. A later automatic integration should publish only after server shutdown and verified backup, receive before world launch under the profile lock, and require an explicit branch choice when both devices have new progress.
