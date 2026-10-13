import com.GameClient;
import java.awt.*;
import java.awt.event.KeyEvent;
import java.lang.reflect.Field;
import javax.swing.*;
import net.runelite.client.RuneLite;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.input.KeyManager;
import net.runelite.client.ui.ClientUI;

/** Exercise the registered user key against live software and OpenGL canvases. */
public final class NativeFullscreenProbe {
 private static int step;
 private static boolean initialized;
 private static long initializedAt;
 private static volatile boolean pending;
 private static volatile Throwable failure;
 private static long last;
 private static Rectangle windowed;
 private static int decoration;
 private static String savedBounds;
 public static boolean active(){return step>0&&step<9;}
 public static boolean tick() throws Exception {
  if(failure!=null)throw new IllegalStateException("Fullscreen probe failed",failure);
  if(pending||System.currentTimeMillis()-last<1500)return false;
  if(step==9||(step==4&&Boolean.getBoolean("soloscape.fullscreen.softwareOnly"))){System.out.println("Native fullscreen passed: registered F11 enter/exit, autorepeat, locked window restoration, focus and saved bounds; renderers="+(step==4?"software only":Boolean.getBoolean("soloscape.fullscreen.glOnly")?"OpenGL only":"software and OpenGL"));step=10;return true;}
  if(step>9)return true;
  final ClientUI ui=RuneLite.getInjector().getInstance(ClientUI.class);
  final GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
  if(!initialized){
   RuneLite.getInjector().getInstance(ConfigManager.class).setConfiguration("runelite","lockWindowSize",true);
   if(Boolean.getBoolean("soloscape.fullscreen.glOnly")&&!client.setControllerDeck60(true))throw new IllegalStateException(client.getControllerPerformanceStatus());
   initialized=true;initializedAt=System.currentTimeMillis();
   SwingUtilities.invokeLater(ui::requestFocus);return false;
  }
  if(step==0){
   if(System.currentTimeMillis()-initializedAt<5000)return false;
   if(!client.getCanvas().isFocusOwner())throw new IllegalStateException("Fullscreen precondition failed: game canvas was unfocused BEFORE F11, renderer="+Class348_Sub8.aHa6654.getClass().getName());
  }
  if(step==4&&!Boolean.getBoolean("soloscape.fullscreen.glOnly")){
   if(!client.setControllerDeck60(true))throw new IllegalStateException(client.getControllerPerformanceStatus());
   if(!(Class348_Sub8.aHa6654 instanceof ha_Sub2))return false;
  }
  pending=true;
  SwingUtilities.invokeLater(()->{try{
   Field field=ClientUI.class.getDeclaredField("frame");field.setAccessible(true);JFrame frame=(JFrame)field.get(ui);
   ConfigManager config=RuneLite.getInjector().getInstance(ConfigManager.class);
   if(step==0){
    windowed=frame.getBounds();decoration=frame.getRootPane().getWindowDecorationStyle();
    savedBounds=config.getConfiguration("runelite","clientBounds");
    client.getCanvas().requestFocusInWindow();key(client,KeyEvent.KEY_PRESSED);key(client,KeyEvent.KEY_RELEASED);
   }else if(step%2==1){
    require(ui.isFullscreen(),"F11 did not enter fullscreen");
    require(frame.getBounds().equals(frame.getGraphicsConfiguration().getBounds()),"Fullscreen did not fill current monitor: "+frame.getBounds());
    require(frame.getRootPane().getWindowDecorationStyle()==JRootPane.NONE,"Fullscreen retained title bar");
    require(client.getCanvas().isFocusOwner(),"Fullscreen lost game focus at step "+step+": owner="+KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()+" frameActive="+frame.isActive()+" focused="+frame.isFocused()+" canvas="+client.getCanvas());
    require(savedBounds.equals(config.getConfiguration("runelite","clientBounds")),"Fullscreen overwrote saved window bounds");
    key(client,KeyEvent.KEY_PRESSED);key(client,KeyEvent.KEY_PRESSED); // autorepeat must toggle only once
    key(client,KeyEvent.KEY_RELEASED);
   }else{
    require(!ui.isFullscreen(),"F11 did not exit fullscreen");
    require(frame.getBounds().equals(windowed),"Window bounds not restored: "+frame.getBounds()+" expected "+windowed);
    require(!frame.isResizable(),"Window size lock not restored");
    require(frame.getRootPane().getWindowDecorationStyle()==decoration,"Window chrome not restored");
    require(client.getCanvas().isFocusOwner(),"Windowed mode lost game focus");
    Field toolbarField=ClientUI.class.getDeclaredField("titleToolbar");toolbarField.setAccessible(true);
    Component toolbar=(Component)toolbarField.get(ui);
    if(decoration==JRootPane.FRAME)require(SwingUtilities.isDescendingFrom(toolbar,frame),"Windowed sidebar/title toolbar was not restored");
    if(step<8){key(client,KeyEvent.KEY_PRESSED);key(client,KeyEvent.KEY_RELEASED);}
   }
   step++;
  }catch(Throwable ex){failure=ex;}finally{last=System.currentTimeMillis();pending=false;}});
  return false;
 }
 private static void key(GameClient client,int type){
  KeyEvent e=new KeyEvent(client.getCanvas(),type,System.currentTimeMillis(),0,KeyEvent.VK_F11,KeyEvent.CHAR_UNDEFINED){@Override public int getExtendedKeyCode(){return KeyEvent.VK_F11;}};
  KeyManager manager=RuneLite.getInjector().getInstance(KeyManager.class);
  if(type==KeyEvent.KEY_PRESSED){manager.processKeyPressed(e);require(e.isConsumed(),"F11 key listener not registered");}else manager.processKeyReleased(e);
 }
 private static void require(boolean okay,String message){if(!okay)throw new IllegalStateException(message);}
}
