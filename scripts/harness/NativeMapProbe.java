import com.GameClient;
import net.runelite.client.RuneLite;
import net.runelite.client.input.controller.*;

/** Opens and closes the real server map through controller gateways, without mouse input. */
public final class NativeMapProbe {
 private static int stage;private static long started;
 public static boolean active(){return stage>0&&stage<3;}
 public static boolean tick() {
  GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
  if(stage==3)return true;
  if(stage==0){
   RuneLite.getInjector().getInstance(net.runelite.client.config.ConfigManager.class).setConfiguration("soloscapecontroller","setupComplete",true);
   client.cancelControllerSelection();
   if(!client.openControllerTab(HomeTab.MAP.ordinal()))return false;
   started=System.nanoTime();stage=1;return false;
  }
  if(System.nanoTime()-started>15_000_000_000L)throw new IllegalStateException("Native map did not open/close");
  UiState state=client.getControllerUiState();
  if(stage==1){
   if(state.panel==null||state.panel.id!=755)return false;
   if(!state.panel.modal)throw new IllegalStateException("Map did not own controller input");
   client.closeControllerPanel();stage=2;return false;
  }
  if(client.isControllerWorldReady()&&client.getControllerAvailableTabs()!=0){stage=3;System.out.println("Native map controller open/close passed.");return true;}
  return false;
 }
}
