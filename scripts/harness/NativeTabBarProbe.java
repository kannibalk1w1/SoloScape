import com.GameClient;
import java.awt.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import net.runelite.client.RuneLite;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin;

/**
 * D-pad tab-bar focus in the real client. Device polling is paused and scripted gamepad states run
 * through the plugin's own input tick (mapping, radials, bar, UI and world wiring), so this checks
 * native slot bounds, visual order, the highlight, A ownership, real tab opening and B back to the
 * world. Synthetic input on a private display; no physical controller or Deck acceptance.
 */
public final class NativeTabBarProbe {
 private static final int A=1,B=2,LEFT=1<<13,RIGHT=1<<14;
 private static int stage,wait,settle,heldBefore;private static boolean shotFocus,shotPanel;
 /** Screenshots stall the client thread past the plugin's idle-input reset, so assertions restart afterwards. */
 private static void restart(){stage=1;wait=0;settle=0;}private static long started;
 private static SoloScapeControllerPlugin plugin;private static Method process;private static Field failed;private static GamepadState raw;
 private static TabBarControls bar;private static UiControls ui;private static TabRadialControls radial;
 private static final Map<String,Object> results=new LinkedHashMap<>();
 private static int target=-1;
 public static boolean active(){return stage>0&&stage<99;}
 private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
 /** One plugin input tick with {@code held} buttons; press/release edges follow from the previous tick. */
 private static void input(int held)throws Exception{
  raw.connected=true;raw.leftX=raw.leftY=raw.rightX=raw.rightY=raw.leftTrigger=raw.rightTrigger=0;
  raw.buttonsPressed=held&~heldBefore;raw.buttonsReleased=heldBefore&~held;raw.buttonsHeld=held;heldBefore=held;
  boolean before=bar.active();long gap=System.nanoTime()-lastInput;lastInput=System.nanoTime();
  process.invoke(plugin,0L);
  if(before&&!bar.active()&&trace.length()<600)trace.append("[bar released held=").append(held).append(" gap_ms=").append(gap/1_000_000).append(" focus=").append(RuneLite.getInjector().getInstance(GameClient.class).getCanvas().isFocusOwner()).append(" ui=").append(ui.active()).append(" tabs=").append(RuneLite.getInjector().getInstance(GameClient.class).getControllerAvailableTabs()).append("]");
 }
 private static long lastInput;private static final StringBuilder trace=new StringBuilder();
 private static void capture(String path){
  javax.swing.SwingUtilities.invokeLater(()->{try{Canvas canvas=RuneLite.getInjector().getInstance(GameClient.class).getCanvas();javax.imageio.ImageIO.write(new Robot().createScreenCapture(new Rectangle(canvas.getLocationOnScreen(),canvas.getSize())),"png",new java.io.File(path));}catch(Exception ex){System.err.println("Tab-bar probe screenshot failed.");}});
 }
 public static boolean tick(String marker)throws Exception{
  GameClient client=RuneLite.getInjector().getInstance(GameClient.class);

  if(stage<99&&failure==null&&started!=0&&System.nanoTime()-started>40_000_000_000L)throw new IllegalStateException("Tab-bar probe timed out at stage "+stage);
  if(stage==0){
   net.runelite.client.config.ConfigManager config=RuneLite.getInjector().getInstance(net.runelite.client.config.ConfigManager.class);
   config.setConfiguration("soloscapecontroller","setupComplete",true);config.setConfiguration("soloscapecontroller","customSkills",true);
   for(net.runelite.client.plugins.Plugin candidate:RuneLite.getInjector().getInstance(net.runelite.client.plugins.PluginManager.class).getPlugins())if(candidate instanceof SoloScapeControllerPlugin)plugin=(SoloScapeControllerPlugin)candidate;
   require(plugin!=null,"Controller plugin missing");
   failed=SoloScapeControllerPlugin.class.getDeclaredField("failed");failed.setAccessible(true);failed.setBoolean(plugin,true); // pause SDL polling only
   process=SoloScapeControllerPlugin.class.getDeclaredMethod("processInput",long.class);process.setAccessible(true);
   Field f=SoloScapeControllerPlugin.class.getDeclaredField("rawState");f.setAccessible(true);raw=(GamepadState)f.get(plugin);
   f=SoloScapeControllerPlugin.class.getDeclaredField("tabBar");f.setAccessible(true);bar=(TabBarControls)f.get(plugin);
   f=SoloScapeControllerPlugin.class.getDeclaredField("ui");f.setAccessible(true);ui=(UiControls)f.get(plugin);
   f=SoloScapeControllerPlugin.class.getDeclaredField("radial");f.setAccessible(true);radial=(TabRadialControls)f.get(plugin);
   client.cancelControllerSelection();started=System.nanoTime();probeMarker=marker;stage=1;
   RuneLite.getInjector().getInstance(net.runelite.client.eventbus.EventBus.class).register(LISTENER);return false;
  }
  if((failure!=null||stage==99)&&!unregistered){unregistered=true;RuneLite.getInjector().getInstance(net.runelite.client.eventbus.EventBus.class).unregister(LISTENER);}
  if(failure!=null){if(failed!=null)failed.setBoolean(plugin,false);throw new IllegalStateException("Tab-bar probe failed",failure);}
  return stage==99;
 }
 private static volatile Throwable failure;private static boolean unregistered;private static String probeMarker;
 /** Scripted input must arrive every client tick: the plugin deliberately resets after 750 ms without input. */
 public static final class Listener {
  @net.runelite.client.eventbus.Subscribe(priority=-1000) public void onClientTick(net.runelite.api.events.ClientTick event){
   if(stage<1||stage>=99||failure!=null)return;
   try{step(probeMarker);}catch(Throwable error){failure=error;}
  }
 }
 private static final Listener LISTENER=new Listener();
 private static void step(String marker)throws Exception{
  GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
  Canvas canvas=client.getCanvas();
  if(!canvas.isFocusOwner()){javax.swing.SwingUtilities.invokeLater(()->{Window owner=javax.swing.SwingUtilities.getWindowAncestor(canvas);if(owner!=null)owner.toFront();canvas.requestFocusInWindow();});return;}
  if(stage==1){ // neutral ticks arm the action map and every consumer
   if(ui.active()||bar.active()){if(++wait>30)throw new IllegalStateException("Could not return to world input");input(B);input(0);return;}
   input(0);if(++settle<4)return;
   require(!ui.active()&&!bar.active(),"World input was not idle before the probe");wait=0;settle=0;stage=2;return;
  }
  if(stage==2){ // enter with A pressed at the same time: highlight only, nothing opens
   input(RIGHT|A);
   require(bar.active(),"Right D-pad did not enter tab-bar focus");
   require(!ui.active(),"Entering the bar opened controller UI");
   int[] order=bar.order();Rectangle[] bounds=client.getControllerTabBounds();
   require(order.length>=8,"Too few native tab slots: "+order.length);
   for(int i=1;i<order.length;i++){Rectangle p=bounds[order[i-1]],q=bounds[order[i]];
    require(p!=null&&q!=null,"Missing native slot bounds");
    boolean sameRow=Math.abs(p.getCenterY()-q.getCenterY())<Math.min(p.height,q.height)/2.0;
    require(sameRow?q.x>p.x:q.getCenterY()>p.getCenterY(),"Slots out of native visual order at "+i);}
   require(bar.highlight()!=null&&bar.highlight().equals(bounds[bar.selected()]),"Highlight does not match the native slot bounds");
   String[] names=new String[order.length];for(int i=0;i<order.length;i++)names[i]=HomeTab.values()[order[i]].label;
   results.put("visual_order",String.join(", ",names));results.put("entered_on",HomeTab.values()[bar.selected()].label);
   results.put("highlight",bar.highlight().toString());
   stage=3;return;
  }
  if(stage==3){input(A);require(bar.active()&&!ui.active(),"Held A confirmed while entering");input(0);stage=4;return;}
  if(stage==4){ // cycle towards Skills one press at a time; never opens
   target=HomeTab.SKILLS.ordinal();boolean available=false;for(int tab:bar.order())available|=tab==target;
   require(available,"Skills slot not available");
   int[] order=bar.order();int before=bar.selected(),at=0;for(int i=0;i<order.length;i++)if(order[i]==before)at=i;
   if(before==target){stage=5;return;}
   input(LEFT);input(0);
   require(bar.selected()==order[Math.floorMod(at-1,order.length)],"Left press did not move one slot in visual order");
   require(bar.active()&&!ui.active(),"Cycling opened a tab");
   if(++wait>20)throw new IllegalStateException("Could not reach Skills");return;
  }
  if(stage==5){
   if(!shotFocus){capture(marker+".tab-bar-focus.png");shotFocus=true;restart();return;}
   input(A|RIGHT);require(bar.active()&&bar.selected()!=target,"A with a direction confirmed: bar="+bar.active()+" selected="+bar.selected()+" ui="+ui.active()+" panel="+(ui.focusedPanel()==null?-1:ui.focusedPanel().id)+" hint="+client.getControllerSelectionHint()+" trace="+trace);
   input(0);input(LEFT);input(0);require(bar.selected()==target,"Did not return to Skills");
   input(A);require(!bar.active(),"Fresh A did not confirm the highlighted tab");
   require(ui.active(),"Opened tab did not take controller UI focus");input(0);
   wait=0;stage=6;return;
  }
  if(stage==6){ // wait for the native skills panel to be adopted by controller focus
   input(0);
   if(ui.focusedPanel()==null||ui.focusedPanel().id!=320){if(++wait>200)throw new IllegalStateException("Skills panel was not focused");return;}
   if(!shotPanel){if(++settle<20)return;results.put("opened_panel",ui.focusedPanel().name);capture(marker+".tab-bar-skills.png");shotPanel=true;restart();return;}
   if(++settle<15)return;
   require(ui.focusedPanel()!=null&&ui.focusedPanel().id==320,"Skills focus lost before B");
   input(B);wait=0;stage=7;return;
  }
  if(stage==7){
   input(B); // held B must not leak into the world or re-enter anything
   if(ui.active()){if(++wait>60)throw new IllegalStateException("B did not return from the opened tab to world input");return;}
   require(!radial.active(),"B from a bar tab went to the Home wheel instead of the world");
   require(!bar.active(),"B left the tab bar focused");
   input(0);input(0);require(!ui.active()&&!bar.active(),"World input not restored after B");
   results.put("b_returns_to_world",true);
   input(LEFT);require(bar.active(),"Bar could not be re-entered from world input");input(B);require(!bar.active(),"B did not deselect the bar");input(0);
   failed.setBoolean(plugin,false);
   results.put("environment","Private Xvfb/software rendering; scripted gamepad states through the plugin input tick. No physical controller or Deck acceptance.");
   Files.write(Paths.get(marker+".tab-bar.json"),new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(results).getBytes("UTF-8"));
   System.out.println("Native D-pad tab-bar focus passed: "+results);stage=99;return;
  }
  return;
 }
}
