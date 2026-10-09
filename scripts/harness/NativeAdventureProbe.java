import java.awt.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.lang.management.ManagementFactory;
import com.google.gson.Gson;
import net.runelite.client.RuneLite;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.*;
import net.runelite.client.ui.overlay.*;

/** Disposable native-session integration and software rendering observations, never hardware acceptance. */
public final class NativeAdventureProbe {
 private static long started,lastStep;private static int step;private static FrameProbe frames;
 private static final Map<String,Object> results=new LinkedHashMap<>();
 private static SoloScapeControllerPlugin plugin;private static UiControls ui;
 private static Field settingsOpen;private static boolean checkedSettings;
 private static UiState display;private static UiState.Widget selected;
 private static String failure,oldNonce;
 public static boolean active(){return started!=0;}
 public static boolean tick(String marker) {
  try {
   if(failure!=null)throw new IllegalStateException(failure);
   long now=System.currentTimeMillis();Files.write(Paths.get(marker+".adventure.status"),("step="+step+" panel="+(ControllerUi.snapshot().panel==null?-1:ControllerUi.snapshot().panel.id)).getBytes("UTF-8"));
   if(started==0){
    started=lastStep=now;frames=new FrameProbe();RuneLite.getInjector().getInstance(OverlayManager.class).add(frames);
    results.put("environment","Private owned Xvfb desktop/software rendering. Native overlay-render intervals; settings use the real Gateway/openHomeTab without SDL onClientTick; logout uses native mouse input. No GPU/Deck/controller acceptance.");
    results.put("heap_at_ready",ManagementFactory.getMemoryMXBean().getHeapMemoryUsage().getUsed());
    return false;
   }
   if(step==0){if(now-started<10000)return false;results.put("native_baseline",frames.finish());step++;lastStep=now;ControllerUi.openTab(HomeTab.COMBAT.ordinal());return false;}
   if(now-lastStep<1200)return false;
   UiState state=ControllerUi.snapshot();
   if(step>=1&&step<=4){
    int[] groups={884,271,320,192};HomeTab[] tabs={HomeTab.PRAYER,HomeTab.SKILLS,HomeTab.SPELLBOOK,HomeTab.QUESTS};
    require(state.panel!=null&&state.panel.id==groups[step-1],"Native panel missing at step "+step);
    java.util.List<String> labels=new ArrayList<>();for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)labels.add(w.name+" | "+w.status+" | "+w.detail);
    require(!labels.isEmpty(),"Native panel has no visible controls");results.put("group_"+state.panel.id,labels);
    ControllerUi.openTab(tabs[step-1].ordinal());step++;lastStep=now;return false;
   }
   if(step==5){
    require(state.panel!=null&&state.panel.id==190,"Quest list missing");UiState.Widget cook=null;
    for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)if(w.name.toLowerCase(Locale.ROOT).contains("cook")&&w.actions.length>0)cook=w;
    require(cook!=null,"Native Cook's Assistant entry missing");require(ControllerUi.invoke(cook,cook.actions[0]),"Fresh native quest action rejected");
    step++;lastStep=now;return false;
   }
   if(step==6){
    require(state.panel!=null&&state.panel.id==275,"Native journal missing");require(state.panel.details.length>0,"Native journal text missing");
    results.put("journal_title",state.panel.name);results.put("journal_rows",state.panel.details.length);
    display=state;selected=state.panel.details[0];frames.restart();step++;lastStep=now;return false;
   }
   if(step==7){
    if(now-lastStep<5000)return false;results.put("custom_journal",frames.finish());
    capture(marker+".live-journal.png");ControllerUi.cancelWorld();step++;lastStep=now;return false;
   }
   if(step==8){display=null;selected=null;require(!ControllerUi.hasModalPanel(),"Native journal did not close");require(ControllerUi.openTab(HomeTab.SETTINGS.ordinal()),"Native settings failed to open");step++;lastStep=now;return false;}
   if(step==9){
    require(state.panel!=null&&(state.panel.id==261||state.panel.id==982),"Native settings not visible");
    for(net.runelite.client.plugins.Plugin candidate:RuneLite.getInjector().getInstance(net.runelite.client.plugins.PluginManager.class).getPlugins())if(candidate instanceof SoloScapeControllerPlugin)plugin=(SoloScapeControllerPlugin)candidate;
    require(plugin!=null,"Managed controller plugin missing");
    settingsOpen=SoloScapeControllerPlugin.class.getDeclaredField("settingsOpen");settingsOpen.setAccessible(true);
    Method open=SoloScapeControllerPlugin.class.getDeclaredMethod("openHomeTab",int.class);open.setAccessible(true);require((Boolean)open.invoke(plugin,HomeTab.SETTINGS.ordinal()),"Plugin Settings opening failed");
    Field uiField=SoloScapeControllerPlugin.class.getDeclaredField("ui");uiField.setAccessible(true);ui=(UiControls)uiField.get(plugin);
    ui.focusHomeTab(HomeTab.SETTINGS.ordinal(),System.nanoTime());ui.update(new GamepadState(),System.nanoTime());
    require(settingsOpen.getBoolean(plugin),"Adoption cancelled local settings");require(ui.focusedPanel()!=null&&ui.focusedPanel().id==ControllerSettingsModel.ID,"Local settings not adopted");
    checkedSettings=true;step++;lastStep=now;return false;
   }
   if(step==10){
    ui.update(new GamepadState(),System.nanoTime());require(checkedSettings&&settingsOpen.getBoolean(plugin),"Local settings failed across ticks");
    require(ui.focusedPanel()!=null&&ui.focusedPanel().id==ControllerSettingsModel.ID,"Settings disappeared on second tick");
    display=ui.state();selected=ui.focus();capture(marker+".live-settings.png");results.put("settings_gateway_two_tick_adoption",true);
    ConfigManager config=RuneLite.getInjector().getInstance(ConfigManager.class);SoloScapeControllerConfig preferences=config.getConfig(SoloScapeControllerConfig.class);
    Field modelField=SoloScapeControllerPlugin.class.getDeclaredField("settings");modelField.setAccessible(true);ControllerSettingsModel model=(ControllerSettingsModel)modelField.get(plugin);
    int before=preferences.deadzone();UiState.Widget row=model.snapshot(true).panes[0].widgets[1];
    require(model.invoke(row,row.actions[0],true)==0,"Local preference change rejected");require(preferences.deadzone()!=before,"Config proxy did not receive local change");
    row=model.snapshot(true).panes[0].widgets[1];require(model.invoke(row,row.actions[1],true)==0,"Local preference reversal rejected");require(preferences.deadzone()==before,"Config proxy did not restore local preference");results.put("settings_config_round_trip",true);
    GamepadState back=new GamepadState();back.buttonsHeld=back.buttonsPressed=0;ui.update(back,System.nanoTime());back.buttonsHeld=back.buttonsPressed=2;ui.update(back,System.nanoTime());
    require(!settingsOpen.getBoolean(plugin),"B did not close local settings");require(ui.takeHomeBack()==HomeTab.SETTINGS.ordinal(),"B lost Home ancestry");results.put("settings_back_to_home",true);
    step++;lastStep=now;return false;
   }
   if(step==11){
    display=null;selected=null;
    oldNonce=nonce();require(oldNonce!=null&&SoloScapeConnection.verified(),"Initial capability nonce missing");
    require(clickNative(548<<16|181)||clickNative(746<<16|172),"Visible native Exit control unavailable");
    step++;lastStep=now;return false;
   }
   if(step==12){
    require(clickNative(182<<16|10),"Visible native logout control unavailable");step++;lastStep=now;return false;
   }
   if(step==13){
    if(Class240.anInt4674!=3){require(now-lastStep<15000,"Native logout did not reach login");return false;}
    SoloScapeConnection.update();require(!SoloScapeConnection.verified(),"Capabilities survived logout");
    // Native logout queues despawn/removal on server ticks. Exercise settled relogin,
    // rather than racing that queue and receiving the ordinary ACCOUNT_ONLINE response.
    if(now-lastStep<4000)return false;
    results.put("logout_settle_ms",now-lastStep);
    net.runelite.client.soloscape.launcher.LocalCredentials credentials=net.runelite.client.soloscape.launcher.LocalCredentials.read(Paths.get(System.getenv("SOLOSCAPE_AUTH_FILE")),Loader.address);
    Class64_Sub3.aString5600=credentials.account;Class186.aString2496=credentials.password;RuntimeException_Sub1.anInt4596=-1;Packet.method3379(2,6);
    step++;lastStep=now;return false;
   }
   if(step==14){
    if(!ControllerWorld.ready()||ControllerUi.availableTabs()==0||!SoloScapeConnection.verified()){require(now-lastStep<45000,"Native relog did not become ready/verified");return false;}
    require(!oldNonce.equals(nonce()),"Relog reused the earlier session nonce");results.put("same_client_relogin",true);results.put("fresh_capabilities_after_relogin",true);

    results.put("heap_after_ui",ManagementFactory.getMemoryMXBean().getHeapMemoryUsage().getUsed());
    for(String line:Files.readAllLines(Paths.get("/proc/self/status")))if(line.startsWith("VmRSS:"))results.put("client_rss",line.substring(6).trim());
    results.put("probe_seconds",(now-started)/1000.0);Files.write(Paths.get(marker+".adventure.json"),new Gson().toJson(results).getBytes("UTF-8"));return true;
   }
   return false;
  }catch(Exception ex){failure=ex.toString();throw new IllegalStateException("Native adventure probe failed at step "+step+": "+failure,ex);}
 }
 private static String nonce()throws Exception{
  Field field=SoloScapeConnection.class.getDeclaredField("capabilities");field.setAccessible(true);Object capabilities=field.get(null);
  Field nonce=ServerCapabilities.class.getDeclaredField("nonce");nonce.setAccessible(true);return (String)nonce.get(capabilities);
 }
 private static Class46 widget(int id)throws Exception{
  Method load=ControllerUi.class.getDeclaredMethod("loadedWidget",int.class);load.setAccessible(true);return (Class46)load.invoke(null,id);
 }
 private static Rectangle bounds(Class46 widget,int depth)throws Exception{
  require(depth<32,"Native widget parent cycle");int x=widget.anInt800,y=widget.anInt750;
  if(widget.anInt834!=-1){Class46 parent=widget(widget.anInt834);require(parent!=null,"Missing native parent");Rectangle box=bounds(parent,depth+1);x+=box.x-parent.anInt747;y+=box.y-parent.anInt755;}
  else if(Class125.aClass356_4915!=null){
   Class46 parent=null;
   for(Class348_Sub41 node=(Class348_Sub41)Class125.aClass356_4915.method3484(0);node!=null;node=(Class348_Sub41)Class125.aClass356_4915.method3482(0))if(node.anInt7050==(widget.anInt830>>>16)){parent=widget((int)node.key);break;}
   if(parent!=null){Rectangle box=bounds(parent,depth+1);x+=box.x;y+=box.y;}
  }
  return new Rectangle(x,y,widget.anInt709,widget.anInt789);
 }
 private static boolean clickNative(int id)throws Exception{
  Class46 control=widget(id);if(control==null)return false;
  Method visible=ControllerUi.class.getDeclaredMethod("isVisible",Class46.class);visible.setAccessible(true);
  if(!(Boolean)visible.invoke(null,control))return false;
  String expected=(id>>>16)==182?"exittologin":"exit";
  String label="";
  for(UiState.Action action:ControllerUi.actions(control,true))if(action.label.toLowerCase(Locale.ROOT).replaceAll("\\s+","").contains(expected))label=action.label;
  if(label.isEmpty()&&ControllerUi.clean(control.aString792).toLowerCase(Locale.ROOT).replaceAll("\\s+","").contains(expected))label=ControllerUi.clean(control.aString792);
  Rectangle box=bounds(control,0);if(box.width<1||box.height<1)return false;
  require(!label.isEmpty(),"Visible native control label does not match "+expected+" at "+id);
  com.GameClient client=RuneLite.getInjector().getInstance(com.GameClient.class);Canvas canvas=client.getCanvas();
  Rectangle canvasBox=new Rectangle(0,0,canvas.getWidth(),canvas.getHeight());box=box.intersection(canvasBox);if(box.isEmpty())return false;
  Point origin=canvas.getLocationOnScreen();Robot mouse=new Robot();mouse.mouseMove(origin.x+box.x+box.width/2,origin.y+box.y+box.height/2);
  mouse.mousePress(java.awt.event.InputEvent.BUTTON1_DOWN_MASK);mouse.delay(80);mouse.mouseRelease(java.awt.event.InputEvent.BUTTON1_DOWN_MASK);
  results.put("native_click_"+id,label+" "+box.toString());return true;
 }
 private static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
 private static void capture(String path)throws Exception{
  // Capture on a later Swing callback so the requested overlay has actually rendered.
  javax.swing.SwingUtilities.invokeLater(()->{try{Thread.sleep(100);Rectangle screen=GraphicsEnvironment.getLocalGraphicsEnvironment().getDefaultScreenDevice().getDefaultConfiguration().getBounds();javax.imageio.ImageIO.write(new Robot().createScreenCapture(screen),"png",new java.io.File(path));}catch(Exception ex){System.err.println("Native probe screenshot: "+ex);}});
 }
 private static final class FrameProbe extends Overlay {
  private final java.util.List<Double> intervals=new ArrayList<>();private long previous;private boolean measuring=true;
  FrameProbe(){setPosition(OverlayPosition.DYNAMIC);setLayer(OverlayLayer.ALWAYS_ON_TOP);}
  void restart(){intervals.clear();previous=0;measuring=true;}
  Map<String,Object> finish(){measuring=false;require(intervals.size()>=30,"Too few rendered interval samples");java.util.List<Double> sorted=new ArrayList<>(intervals);Collections.sort(sorted);Map<String,Object> out=new LinkedHashMap<>();out.put("samples",sorted.size());out.put("median_ms",sorted.get(sorted.size()/2));out.put("p95_ms",sorted.get((int)((sorted.size()-1)*.95)));out.put("p99_ms",sorted.get((int)((sorted.size()-1)*.99)));out.put("max_ms",sorted.get(sorted.size()-1));return out;}
  @Override public Dimension render(Graphics2D graphics){
   long now=System.nanoTime();if(measuring){if(previous!=0&&intervals.size()<12000)intervals.add((now-previous)/1000000.0);previous=now;}
   UiState current=display;
   if(current!=null&&current.panel!=null){
    com.GameClient client=RuneLite.getInjector().getInstance(com.GameClient.class);int width=client.getCanvas().getWidth(),height=client.getCanvas().getHeight();
    PanelPresentation layout=new PanelPresentation(width,height,1,current.panel.id);UiState shown=layout.present(current,selected,true,true,true,true,true,true,true,true,true);
    UiState.Pane pane=shown.panel.panes[0];UiState.Widget focus=pane.widgets.length>0?pane.widgets[0]:null;
    SoloScapePanelOverlay.paint(graphics,layout,shown.panel.name+" / "+pane.name,pane.widgets,focus,null,ControllerGlyphs.XBOX,-1,s->s,w->client.getControllerItemImage(w.itemId,w.quantity));
   }
   return null;
  }
 }
}
