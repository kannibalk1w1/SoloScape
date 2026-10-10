import java.awt.Component;
import java.awt.Container;
import java.awt.event.InputEvent;
import java.awt.event.KeyEvent;
import java.lang.reflect.Field;
import javax.swing.JButton;
import javax.swing.SwingUtilities;
import net.runelite.client.RuneLite;
import net.runelite.client.input.KeyManager;
import net.runelite.client.plugins.Plugin;
import net.runelite.client.plugins.PluginManager;
import net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin;
import net.runelite.client.ui.ClientUI;

/** Real scene/renderer plus EDT sidebar actions in a disposable profile. */
public final class NativeSidebarProbe {
    private static int step;
    private static long lastStep;
    private static volatile boolean pending;
    private static volatile Throwable failure;
    private static int initialWidth;

    public static boolean tick() throws Exception {
        if (failure != null) throw new IllegalStateException("Native sidebar probe failed", failure);
        if (pending || System.currentTimeMillis() - lastStep < 650) return false;
        final ClientUI ui = RuneLite.getInjector().getInstance(ClientUI.class);
        if (step == 0) {
            PluginManager manager = RuneLite.getInjector().getInstance(PluginManager.class);
            Plugin controller = null;
            for (Plugin plugin : manager.getPlugins()) if (plugin instanceof SoloScapeControllerPlugin) controller = plugin;
            require(controller != null, "Controller plugin missing");
            if (!Boolean.getBoolean("soloscape.sidebar.baseline")) {
                require(manager.isPluginEnabled(controller), "Controller plugin is not enabled on a fresh profile");
                Field active = SoloScapeControllerPlugin.class.getDeclaredField("active");
                active.setAccessible(true);
                require(active.getBoolean(controller), "Controller plugin did not start");
            }
            System.out.println("Sidebar probe renderer: " + Class348_Sub8.aHa6654.getClass().getName());
        }
        if (step > 60) {
            System.out.println("Native sidebar probe passed: 10 open/configuration/panel/close cycles; controller starts by default.");
            return true;
        }
        final int action = step == 0 ? -1 : (step - 1) % 6;
        pending = true;
        SwingUtilities.invokeLater(() -> {
            try {
                if (action == -1) {
                    if ((Boolean) field(ui, "sidebarOpen")) arrow(ui);
                    initialWidth = ((Container) field(ui, "frame")).getWidth();
                } else if (action == 0) {
                    arrow(ui);
                    require((Boolean) field(ui, "sidebarOpen"), "Sidebar arrow did not open toolbar");
                } else if (action == 1) {
                    JButton config = configuration((Container) field(ui, "pluginToolbar"));
                    require(config != null, "Configuration toolbar button missing");
                    // Opening the sidebar restores its previous panel. Exercise
                    // the icon's close/reopen behavior as well as a fresh open.
                    if (field(ui, "pluginPanel") != null) config.doClick(0);
                    config.doClick(0);
                    require(field(ui, "pluginPanel") != null, "Configuration panel did not open");
                } else if (action == 2 || action == 3) {
                    if (action == 3 && !Boolean.getBoolean("soloscape.sidebar.baseline")) require(field(ui, "pluginPanel") == null, "Panel hotkey did not close Configuration");
                    if (!Boolean.getBoolean("soloscape.sidebar.baseline")) hotkey(KeyEvent.VK_F12);
                } else if (action == 4) {
                    require(field(ui, "pluginPanel") != null, "Panel hotkey did not reopen Configuration");
                    if (Boolean.getBoolean("soloscape.sidebar.baseline")) arrow(ui);
                    else hotkey(KeyEvent.VK_F11);
                } else {
                    require(!(Boolean) field(ui, "sidebarOpen"), "Sidebar hotkey did not close toolbar");
                    require(field(ui, "pluginPanel") == null, "Closed sidebar retained the panel");
                    int actualWidth = ((Container) field(ui, "frame")).getWidth();
                    require(actualWidth == initialWidth, "Closing sidebar did not restore window width: " + actualWidth + " instead of " + initialWidth);
                    require(RuneLite.getInjector().getInstance(com.GameClient.class).getCanvas().isFocusOwner(), "Closing sidebar did not restore game focus");
                }
                step++;
            } catch (Throwable ex) { failure = ex; }
            finally { lastStep = System.currentTimeMillis(); pending = false; }
        });
        return false;
    }

    private static Object field(Object object, String name) throws Exception {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(object);
    }

    private static void arrow(ClientUI ui) throws Exception {
        ((JButton) field(ui, "sidebarNavigationJButton")).doClick(0);
    }

    private static JButton configuration(Container parent) {
        for (Component child : parent.getComponents()) {
            if (child instanceof JButton && "Configuration".equals(((JButton) child).getToolTipText())) return (JButton) child;
            if (child instanceof Container) {
                JButton found = configuration((Container) child);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static void hotkey(int key) {
        com.GameClient client = RuneLite.getInjector().getInstance(com.GameClient.class);
        KeyManager manager = RuneLite.getInjector().getInstance(KeyManager.class);
        long now = System.currentTimeMillis();
        // AWT fills extendedKeyCode on OS events; constructed KeyEvents leave it
        // undefined. Supply the same code here when exercising the native adapter.
        KeyEvent press = event(client.getCanvas(), KeyEvent.KEY_PRESSED, now, key);
        manager.processKeyPressed(press);
        require(press.isConsumed(), "Sidebar/panel hotkey was not registered");
        manager.processKeyReleased(event(client.getCanvas(), KeyEvent.KEY_RELEASED, now, key));
    }

    private static KeyEvent event(Component source, int type, long now, int key) {
        return new KeyEvent(source, type, now, InputEvent.CTRL_DOWN_MASK, key, KeyEvent.CHAR_UNDEFINED) {
            @Override public int getExtendedKeyCode() { return key; }
        };
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
