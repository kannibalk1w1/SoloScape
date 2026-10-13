import java.lang.reflect.*;
import java.nio.file.*;
import net.runelite.client.RuneLite;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin;
/** Execute the local confirmed quit gateway, then let the profile owner save the world normally. */
public final class NativeQuitProbe {
 private static int stage;private static SoloScapeControllerPlugin plugin;private static UiState.Widget quit;private static Method invoke;
 public static boolean active(){return stage>0&&stage<2;}
 public static boolean tick(String marker)throws Exception{
  if(stage==2)return true;
  if(stage==0){
   for(net.runelite.client.plugins.Plugin p:RuneLite.getInjector().getInstance(net.runelite.client.plugins.PluginManager.class).getPlugins())if(p instanceof SoloScapeControllerPlugin)plugin=(SoloScapeControllerPlugin)p;
   if(plugin==null)throw new IllegalStateException("Missing controller");
   Field failed=SoloScapeControllerPlugin.class.getDeclaredField("failed");failed.setAccessible(true);failed.setBoolean(plugin,true);
   Field settingsOpen=SoloScapeControllerPlugin.class.getDeclaredField("settingsOpen");settingsOpen.setAccessible(true);settingsOpen.setBoolean(plugin,true);
   Field model=SoloScapeControllerPlugin.class.getDeclaredField("settings");model.setAccessible(true);
   net.runelite.client.config.ConfigManager config=RuneLite.getInjector().getInstance(net.runelite.client.config.ConfigManager.class);config.setConfiguration("soloscapecontroller","setupComplete",true);
   quit=((ControllerSettingsModel)model.get(plugin)).snapshot(false).panes[3].widgets[3];
   invoke=SoloScapeControllerPlugin.class.getDeclaredMethod("invokeUi",UiState.Widget.class,UiState.Action.class);invoke.setAccessible(true);
   if((Boolean)invoke.invoke(plugin,quit,quit.actions[0]))throw new IllegalStateException("First press quit without confirmation");
   stage=1;return false;
  }
  if(!(Boolean)invoke.invoke(plugin,quit,quit.actions[0]))throw new IllegalStateException("Second distinct press did not request shutdown");
  Files.write(Paths.get(marker+".quit.json"),"{\"first_press_blocked\":true,\"confirmed_quit_requested\":true}".getBytes("UTF-8"));stage=2;return true;
 }
}
