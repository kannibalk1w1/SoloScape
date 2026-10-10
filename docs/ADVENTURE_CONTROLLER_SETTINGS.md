# Controller settings and setup

With the controller plugin enabled, **Home > Settings** opens the controller preferences screen. Its panes are **Basics**, **Bindings**, **Screens**, and **Finish**. LB/RB changes pane, D-pad or right stick navigates, A advances a value and X exposes Next/Previous actions. Changes persist immediately. Finish returns to Home.

Basics contains presets, deadzone, overlay size, run threshold, direct movement, server features, camera inversion, button labels and the guide. Bindings swaps the existing owner when assigning an occupied button, so a change keeps the eight controls distinct. Release held controls after remapping; the input guard requires neutral input before resuming. Screens contains the nine independent custom-screen toggles.

The first usable controller session offers setup until **Finish controller setup** is selected. It does not enable direct movement, server features or custom adventure screens automatically. **Game settings** opens the native settings tab; B from its root returns to controller preferences, and native submenus keep their existing ancestry.

Disable **Controller settings screen** in the plugin settings to restore native Home > Settings. Mouse controls remain available. Entry prompts, native modal interfaces and logout dismiss the local screen. Preferences use local configuration actions with reserved identifiers; they never dispatch through the native widget action gateway.

Verification includes preference bounds/cycling, stale-value rejection, binding swaps, completion persistence and Home/B navigation. Live controller and first-run acceptance remain separate.
