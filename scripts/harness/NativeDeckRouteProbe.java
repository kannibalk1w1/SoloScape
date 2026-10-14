import java.awt.*;
import java.lang.reflect.Method;
import java.lang.reflect.Field;
import java.lang.management.ManagementFactory;
import java.lang.management.GarbageCollectorMXBean;
import java.nio.file.*;
import java.util.*;
import com.GameClient;
import com.google.gson.Gson;
import net.runelite.client.RuneLite;
import net.runelite.client.eventbus.EventBus;
import net.runelite.client.eventbus.Subscribe;
import net.runelite.api.events.ClientTick;
import net.runelite.client.input.controller.*;
import net.runelite.client.ui.overlay.*;

/** Repeatable real-map route and frame trace in disposable worlds; no injected progression. */
public final class NativeDeckRouteProbe extends Overlay {
 private static NativeDeckRouteProbe probe;
 private final ArrayList<Double> intervals=new ArrayList<>();
 private final ArrayList<String> trace=new ArrayList<>();
 private final Map<String,Object> report=new LinkedHashMap<>();
 private final ArrayList<Map<String,Object>> rendererTransitions=new ArrayList<>();private String previousRenderer;
 private Field phaseTotalsField,logicCyclesField;private long[] previousPhaseTotals;private long previousLogicCycles,previousGcMs;private final java.util.List<GarbageCollectorMXBean> gcBeans=ManagementFactory.getGarbageCollectorMXBeans();
 private long started,previous,stepSince,lastWalk,lastProgress;private int step,loops;private boolean sent,combatDone,finished;private int combatStage,combatXpBefore,combatXpGain;private volatile boolean resized;
 /** Software-renderer host run: the same real-map route without OpenGL/Deck 60 (Xvfb cannot start the OpenGL toolkit). */
 private static final boolean SOFTWARE=Boolean.getBoolean("soloscape.deck60.route.software");
 private final int seconds=Integer.getInteger("soloscape.deck60.route.seconds",1800);
 private net.runelite.client.input.controller.UiControls controllerUi;
 private static final String[] STEPS={"origin","courtyard","castle_door","open_door","castle_inside","stairs","up1","up2","bank_approach","bank","close_bank","stairs2","down1","down0","castle_inside","door_inside","courtyard","shop_approach","shop","close_shop","road","farm_road","farm","mill_road","mill","mill_dialogue","close_dialogue","farm_return","combat","cancel_combat","road_return","courtyard_return","origin_return","inventory","close_inventory","map","close_map"};
 public NativeDeckRouteProbe(){setPosition(OverlayPosition.DYNAMIC);setLayer(OverlayLayer.ALWAYS_ON_TOP);}
 public static boolean active(){return probe!=null;}
 public static boolean tick(String marker)throws Exception{
  if(probe==null){
   probe=new NativeDeckRouteProbe();probe.step=Integer.getInteger("soloscape.deck60.route.startStep",0);if(probe.step<0||probe.step>=STEPS.length)throw new IllegalArgumentException("Invalid diagnostic route start step");probe.report.put("start_step",STEPS[probe.step]);RuneLite.getInjector().getInstance(OverlayManager.class).add(probe);RuneLite.getInjector().getInstance(EventBus.class).register(probe);
   GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
   net.runelite.client.config.ConfigManager config=RuneLite.getInjector().getInstance(net.runelite.client.config.ConfigManager.class);
   for(net.runelite.client.plugins.Plugin plugin:RuneLite.getInjector().getInstance(net.runelite.client.plugins.PluginManager.class).getPlugins())if(plugin instanceof net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin){
    java.lang.reflect.Field ui=plugin.getClass().getDeclaredField("ui");ui.setAccessible(true);probe.controllerUi=(net.runelite.client.input.controller.UiControls)ui.get(plugin);probe.controllerUi.reset();java.lang.reflect.Field settings=plugin.getClass().getDeclaredField("settingsOpen");settings.setAccessible(true);settings.setBoolean(plugin,false);
   }
   config.setConfiguration("soloscapecontroller","setupComplete",true);
   config.setConfiguration("runelite","lockWindowSize",false);config.setConfiguration("runelite","containInScreen2",net.runelite.client.ui.ContainableFrame.Mode.NEVER);
   Class316.aClass348_Sub51_3959.method3429((byte)74,Class316.aClass348_Sub51_3959.aClass239_Sub23_7231,0);
   probe.report.put("initial_preset_status",client.getControllerPerformanceStatus());ControllerUi.cancelSelection();config.setConfiguration("soloscapecontroller","deck60",true);
   if(!SOFTWARE&&!client.setControllerDeck60(true))throw new IllegalStateException(client.getControllerPerformanceStatus());
   if(Boolean.getBoolean("soloscape.deck60.route.staticShadows")){Class316.aClass348_Sub51_3959.method3429((byte)74,Class316.aClass348_Sub51_3959.aClass239_Sub7_7238,1);System.out.println("Diagnostic graphics: static object shadows; animated object shadows disabled");}
   probe.report.put("native_object_shadow_setting",Class316.aClass348_Sub51_3959.aClass239_Sub7_7238.method1748(-32350));
   javax.swing.SwingUtilities.invokeLater(()->{try{
    net.runelite.client.ui.ClientUI ui=RuneLite.getInjector().getInstance(net.runelite.client.ui.ClientUI.class);
    if(!ui.isFullscreen())ui.toggleFullscreen();
    if(!ui.isFullscreen())throw new IllegalStateException("Fullscreen did not open");
    probe.resized=true;
   }catch(Exception ex){throw new IllegalStateException(ex);}});
   probe.trace.add("elapsed_ns,step,interval_ms,client_state,tile_x,tile_y,plane,scene_base_x,scene_base_y,renderer,logic_cycles_delta,logic_ms_delta,plugins_ms_delta,overlay_paint_ms_delta,overlay_upload_ms_delta,frame_ms_delta,event_queue_ms_delta,present_ms_delta,gc_ms_delta");probe.stepSince=System.nanoTime();return false;
  }
  return probe.finished||probe.update(marker);
 }
 private boolean update(String marker)throws Exception{
  GameClient client=RuneLite.getInjector().getInstance(GameClient.class);long now=System.nanoTime();
  if(started==0){
   if(!resized||!ControllerWorld.ready()||now-stepSince<10_000_000_000L)return false;
   if(client.getCanvas().getWidth()!=1280||client.getCanvas().getHeight()!=800)throw new IllegalStateException("Route canvas is not 1280x800: "+client.getCanvas().getSize());
   if(Class321.anInt4017!=1280||Class348_Sub42_Sub8_Sub2.anInt10432!=800)throw new IllegalStateException("Native renderer dimensions differ from 1280x800");
   if(!SOFTWARE&&!(Class348_Sub8.aHa6654 instanceof ha_Sub2))throw new IllegalStateException("OpenGL was not adopted");
   Class.forName("com.FrameTimings").getMethod("snapshotAndReset").invoke(null);preparePhaseTrace();started=stepSince=now;report.put("phase_trace_method","Cumulative completed phase/cycle deltas between overlay callbacks; not same-frame durations. Frame/present completion crosses callback boundaries; phases overlap, do not sum them. GC collection-time deltas are coarse JVM counters, not event timestamps. Added diagnostic sampling/allocation can affect timing.");report.put("started_monotonic_ns",started);report.put("native_dimensions",Class321.anInt4017+"x"+Class348_Sub42_Sub8_Sub2.anInt10432);report.put("preset_status",client.getControllerPerformanceStatus());report.put("fps_target",DetachedRenderer.getFpsTarget());report.put("pacing",DetachedRenderer.isActive());report.put("start_tile",Arrays.toString(tile()));report.put("renderer",Class348_Sub8.aHa6654.getClass().getName());report.put("canvas",client.getCanvas().getSize().toString());return false;
  }
  if(seconds==0&&now-started>=10_000_000_000L)return finish(marker,now);
  if(seconds==0)return false;
  if(Files.exists(Paths.get(marker+".route.stop"))||now-stepSince>90_000_000_000L){dumpState(marker);throw new IllegalStateException("Route stalled at "+STEPS[step]+" tile "+Arrays.toString(tile()));}
  Files.write(Paths.get(marker+".route.status"),(STEPS[step]+" loop="+loops+" seconds="+(now-started)/1e9+" tile="+Arrays.toString(tile())).getBytes("UTF-8"));
  if(now-lastProgress>=5_000_000_000L){
   lastProgress=now;int count=intervals.size(),begin=Math.max(0,count-300);double elapsed=0;for(int n=begin;n<count;n++)elapsed+=intervals.get(n);
   Map<String,Object> progress=new LinkedHashMap<>();progress.put("scene_size",Arrays.asList(Class367_Sub4.anInt7319,Class348_Sub40_Sub3.anInt9109));progress.put("combat_stage",combatStage);progress.put("combat_xp_gained",combatXpGain);progress.put("camera_yaw",client.getCameraYaw());progress.put("scene_base",Arrays.asList(za_Sub2.regionTileX,Class90.regionTileY));progress.put("step",STEPS[step]);progress.put("loops",loops);progress.put("seconds",(now-started)/1e9);progress.put("recent_fps",elapsed==0?null:(count-begin)*1000/elapsed);progress.put("canvas_focused",client.getCanvas().isFocusOwner());progress.put("renderer",renderer());progress.put("gl_texture_bytes",Class348_Sub8.aHa6654 instanceof ha_Sub2?((ha_Sub2)Class348_Sub8.aHa6654).anInt7748:null);
   Files.write(Paths.get(marker+".route.progress.json"),new Gson().toJson(progress).getBytes("UTF-8"));
  }
  boolean complete=false;
  switch(step){
   case 0:complete=at(3221,3219,0);break;
   case 1:complete=at(3215,3224,0);break;
   case 2:complete=at(3208,3227,0);break;
   case 3:complete=actionThenWait("Door","Open",3207,3227,1500);break;
   case 4:complete=at(3206,3227,0);break;
   case 5:complete=at(3205,3228,0);break;
   case 6:complete=stairs("Climb-up",1);break;
   case 7:complete=stairs("Climb-up",2);break;
   case 8:complete=at(3208,3219,2);break;
   case 9:complete=openPanel("Banker","Bank",762);break;
   case 10:complete=closePanel(762);break;
   case 11:complete=at(3205,3228,2);break;
   case 12:complete=stairs("Climb-down",1);break;
   case 13:complete=stairs("Climb-down",0);break;
   case 14:complete=at(3206,3227,0);break;
   case 15:complete=actionThenWait("Door","Open",3207,3227,1500);break;
   case 16:complete=at(3215,3224,0);break;
   case 17:if(!sent){if(at(3222,3241,0))sent=true;}else complete=at(3217,3241,0);break;
   case 18:complete=openPanel("Shopkeeper","Trade",620);break;
   case 19:complete=closePanel(620);break;
   case 20:complete=at(3205,3246,0);break;
   case 21:if(!sent){if(at(3217,3260,0))sent=true;}else complete=at(3217,3274,0);break;
   case 22:complete=at(3183,3277,0);break;
   case 23:complete=at(3167,3299,0);break;
   case 24:if(!sent){if(at(3166,3302,0))sent=true;}else complete=at(3169,3305,0);break;
   case 25:if(!sent)sent=interact("Millie Miller","Talk-to",-1,-1);complete=ControllerUi.hasDialogue();break;
   case 26:ControllerUi.cancelDialogue();complete=!ControllerUi.hasDialogue();break;
   case 27:complete=at(3183,3277,0);break;
   case 28:
    if(combatDone){complete=true;break;}
    if(combatStage==0){
     if(at(3189,3277,0)){combatXpBefore=combatXp();combatStage++;}
     else if(!interact("Door","Open",3187,3272))interact("Door","Open",3189,3275);
    }
    else{if(!sent)sent=interact("Chicken","Attack",-1,-1);combatXpGain=combatXp()-combatXpBefore;complete=sent&&combatXpGain>0;}
    break;
   case 29:ControllerDirectMovement.cancelAction();combatDone=true;complete=true;break;
   case 30:if(now-stepSince>2_500_000_000L){if(!sent){if(at(3200,3277,0))sent=true;}else complete=at(3217,3274,0);}break;
   case 31:if(!sent){if(at(3226,3245,0))sent=true;}else complete=at(3215,3224,0);break;
   case 32:complete=at(3221,3219,0);break;
   case 33:if(!sent){sent=client.openControllerInventory();if(sent&&controllerUi!=null)controllerUi.focusInventory(now);}complete=sent&&now-stepSince>2_000_000_000L;break;
   case 34:back();complete=controllerUi==null||!controllerUi.active();break;
   case 35:if(!sent)sent=client.openControllerTab(HomeTab.MAP.ordinal());complete=client.getControllerUiState().panel!=null&&client.getControllerUiState().panel.id==755;if(complete)lastProgress=0;break;
   case 36:back();complete=ControllerWorld.ready();if(complete&&!SOFTWARE&&!(Class348_Sub8.aHa6654 instanceof ha_Sub2))throw new IllegalStateException("OpenGL did not restore after map close");break;
  }
  if(complete){
   System.out.println("Deck route "+STEPS[step]+" complete at "+Arrays.toString(tile()));step++;stepSince=now;sent=false;
   if(step>=STEPS.length){step=0;loops++;if(Boolean.getBoolean("soloscape.deck60.route.singleLoop")||now-started>=seconds*1_000_000_000L)return finish(marker,now);}
  }
  return false;
 }
 private boolean finish(String marker,long now)throws Exception{
  GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
  ArrayList<Double> sorted=new ArrayList<>(intervals);Collections.sort(sorted);if(sorted.size()<30)throw new IllegalStateException("Too few route frames");
  report.put("diagnostic_single_loop",Boolean.getBoolean("soloscape.deck60.route.singleLoop"));report.put("renderer_after_route",renderer());report.put("renderer_transitions",rendererTransitions);report.put("seconds",(now-started)/1e9);report.put("loops",loops);report.put("samples",sorted.size());report.put("average_fps",sorted.size()*1000/sorted.stream().mapToDouble(Double::doubleValue).sum());report.put("p95_ms",sorted.get((sorted.size()-1)*95/100));report.put("p99_ms",sorted.get((sorted.size()-1)*99/100));report.put("max_ms",sorted.get(sorted.size()-1));report.put("finish_tile",Arrays.toString(tile()));report.put("canvas_focused",client.getCanvas().isFocusOwner());
  for(net.runelite.client.plugins.Plugin plugin:RuneLite.getInjector().getInstance(net.runelite.client.plugins.PluginManager.class).getPlugins())if(plugin instanceof net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin){java.lang.reflect.Field raw=plugin.getClass().getDeclaredField("rawState");raw.setAccessible(true);report.put("controller_connected",((GamepadState)raw.get(plugin)).connected);}report.put("combat_attempted",combatDone);report.put("combat_xp_gained",combatXpGain);
  report.put("phase_timings",Class.forName("com.FrameTimings").getMethod("snapshotAndReset").invoke(null));
  ArrayList<Map<String,Object>> gc=new ArrayList<>();for(java.lang.management.GarbageCollectorMXBean bean:java.lang.management.ManagementFactory.getGarbageCollectorMXBeans()){Map<String,Object> item=new LinkedHashMap<>();item.put("name",bean.getName());item.put("collections",bean.getCollectionCount());item.put("milliseconds",bean.getCollectionTime());gc.add(item);}report.put("gc_since_process_start",gc);
  finished=true;client.setControllerCameraInput(0,0);RuneLite.getInjector().getInstance(EventBus.class).unregister(this);
  Files.write(Paths.get(marker+".route.json"),new Gson().toJson(report).getBytes("UTF-8"));Files.write(Paths.get(marker+".route.csv"),trace,java.nio.charset.StandardCharsets.UTF_8);return true;
 }
 @Subscribe(priority=-1000) public void onClientTick(ClientTick event){
  if(started!=0&&!finished&&seconds!=0)RuneLite.getInjector().getInstance(GameClient.class).setControllerCameraInput(ControllerWorld.ready()&&(controllerUi==null||!controllerUi.active())?25:0,0);
 }
 private static int combatXp(){int total=0;for(GameClient.SkillSnapshot skill:RuneLite.getInjector().getInstance(GameClient.class).getSkillSnapshots())switch(skill.getSkill()){case ATTACK:case STRENGTH:case DEFENCE:case HITPOINTS:total+=skill.getXp();break;default:break;}return total;}
 public static void failed(String marker,Exception failure)throws Exception{
  if(probe!=null&&probe.started!=0&&!probe.finished){probe.report.put("failure",failure.toString());probe.finish(marker+".failed",System.nanoTime());}
 }
 private static String renderer(){return Class348_Sub8.aHa6654==null?"none":Class348_Sub8.aHa6654.getClass().getName();}
 private static int[] tile(){Player p=Class132.aPlayer_1907;return new int[]{(p.x>>9)+za_Sub2.regionTileX,(p.y>>9)+Class90.regionTileY,p.plane};}
 private void nextWalk(){lastWalk=System.nanoTime();}
 private boolean at(int x,int y,int plane)throws Exception{
  int[] pos=tile();if(pos[2]!=plane)throw new IllegalStateException("Unexpected route floor");
  if(pos[0]==x&&pos[1]==y)return System.nanoTime()-lastWalk>850_000_000L;
  if(!ControllerWorld.ready()||System.nanoTime()-lastWalk<850_000_000L)return false;
  Method method=NativePlayableLoopProbe.class.getDeclaredMethod("nextStep",int.class,int.class);method.setAccessible(true);int[] delta=(int[])method.invoke(null,x,y);if(delta==null){openNearby(x,y);return false;}
  if(System.nanoTime()-lastWalk>3_000_000_000L)ControllerWorld.reset();
  double length=Math.hypot(delta[0],delta[1]);if(ControllerWorld.walk((delta[2]==1?.4:delta[2]==2?.7:1)*delta[0]/length,(delta[2]==1?.4:delta[2]==2?.7:1)*delta[1]/length))nextWalk();return false;
 }
 @SuppressWarnings("unchecked") private static boolean interact(String name,String option,int x,int y)throws Exception{
  Method method=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);method.setAccessible(true);
  for(GameClient.ControllerTarget target:(java.util.List<GameClient.ControllerTarget>)method.invoke(null,true))if(ControllerUi.clean(target.name).toLowerCase(java.util.Locale.ROOT).replaceAll("[^a-z]","").equals(name.toLowerCase(java.util.Locale.ROOT).replaceAll("[^a-z]",""))&&(target.option.equalsIgnoreCase(option)||option.equals("Trade")&&target.option.startsWith("Trade"))&&(x<0||target.x+target.baseX==x&&target.y+target.baseY==y))if(ControllerWorld.interact(target))return true;
  return false;
 }
 private static void openNearby()throws Exception{int[] pos=tile();openNearby(pos[0],pos[1]);}
 @SuppressWarnings("unchecked") private static void openNearby(int goalX,int goalY)throws Exception{
  Method method=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);method.setAccessible(true);
  java.util.List<GameClient.ControllerTarget> targets=new ArrayList<>((java.util.List<GameClient.ControllerTarget>)method.invoke(null,true));
  targets.sort(Comparator.comparingDouble(t->Math.hypot(t.x+t.baseX-goalX,t.y+t.baseY-goalY)));
  for(GameClient.ControllerTarget target:targets){String name=ControllerUi.clean(target.name).toLowerCase(java.util.Locale.ROOT);if(target.option.equalsIgnoreCase("Open")&&(name.contains("door")||name.contains("gate")))if(ControllerWorld.interact(target))return;}
 }
 private boolean actionThenWait(String name,String option,int x,int y,int ms)throws Exception{if(!sent)sent=interact(name,option,x,y);return System.nanoTime()-stepSince>ms*1_000_000L;}
 private boolean stairs(String option,int floor)throws Exception{if(tile()[2]==floor)return true;if(!sent&&System.nanoTime()-stepSince>2_500_000_000L)sent=interact("Staircase",option,3204,3229);return false;}
 private boolean openPanel(String name,String option,int id)throws Exception{UiState.Panel p=ControllerUi.snapshot().panel;if(p!=null&&p.id==id)return true;if(!sent){sent=interact(name,option,-1,-1);if(!sent)openNearby();}return false;}
 @SuppressWarnings("unchecked") private void dumpState(String marker)throws Exception{
  Map<String,Object> info=new LinkedHashMap<>();info.put("scene_base",Arrays.asList(za_Sub2.regionTileX,Class90.regionTileY));info.put("combat_stage",combatStage);info.put("step",STEPS[step]);info.put("sent",sent);info.put("tile",Arrays.toString(tile()));info.put("world_ready",ControllerWorld.ready());Method navigation=NativePlayableLoopProbe.class.getDeclaredMethod("nextStep",int.class,int.class);navigation.setAccessible(true);info.put("return_path_next_step",navigation.invoke(null,3217,3274));info.put("dialogue",ControllerUi.snapshot().dialogueId);info.put("panel",ControllerUi.snapshot().panel==null?-1:ControllerUi.snapshot().panel.id);
  Method method=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);method.setAccessible(true);ArrayList<String> names=new ArrayList<>();for(GameClient.ControllerTarget target:(java.util.List<GameClient.ControllerTarget>)method.invoke(null,true))names.add(target.name+"|"+target.option+"|"+(target.x+target.baseX)+","+(target.y+target.baseY));info.put("candidates",names);Files.write(Paths.get(marker+".route.failure.json"),new Gson().toJson(info).getBytes("UTF-8"));System.out.println(new Gson().toJson(info));finish(marker+".failed",System.nanoTime());
 }
 private void back(){if(controllerUi==null){ControllerUi.closePanel();return;}GamepadState neutral=new GamepadState();controllerUi.update(neutral,System.nanoTime());GamepadState back=new GamepadState();back.buttonsPressed=back.buttonsHeld=2;controllerUi.update(back,System.nanoTime());}
 private boolean closePanel(int id){UiState.Panel p=ControllerUi.snapshot().panel;if(p==null||p.id!=id)return ControllerWorld.ready();ControllerUi.closePanel();return false;}
 private long gcMilliseconds(){long total=0;for(GarbageCollectorMXBean bean:gcBeans){long value=bean.getCollectionTime();if(value>=0)total+=value;}return total;}
 private void preparePhaseTrace()throws Exception{
  Class<?> timings=Class.forName("com.FrameTimings");if(!timings.getField("ENABLED").getBoolean(null))throw new IllegalStateException("Route phase tracing requires performance timings");
  phaseTotalsField=timings.getDeclaredField("totals");phaseTotalsField.setAccessible(true);logicCyclesField=timings.getDeclaredField("cycles");logicCyclesField.setAccessible(true);previousPhaseTotals=((long[])phaseTotalsField.get(null)).clone();previousLogicCycles=logicCyclesField.getLong(null);previousGcMs=gcMilliseconds();
 }
 private String phaseTrace(){
  try{
   long[] totals=(long[])phaseTotalsField.get(null);long cycles=logicCyclesField.getLong(null),gc=gcMilliseconds();int[] position=tile();StringBuilder out=new StringBuilder();out.append(',').append(position[0]).append(',').append(position[1]).append(',').append(position[2]).append(',').append(za_Sub2.regionTileX).append(',').append(Class90.regionTileY).append(',').append(renderer()).append(',').append(cycles-previousLogicCycles);
   for(int i=0;i<totals.length;i++){out.append(',').append((totals[i]-previousPhaseTotals[i])/1e6);previousPhaseTotals[i]=totals[i];}out.append(',').append(gc-previousGcMs);previousLogicCycles=cycles;previousGcMs=gc;return out.toString();
  }catch(Exception error){throw new IllegalStateException("Route phase trace unavailable",error);}
 }
 @Override public Dimension render(Graphics2D g){long now=System.nanoTime();if(started!=0&&!finished&&intervals.size()<500000){String currentRenderer=renderer();if(!Objects.equals(currentRenderer,previousRenderer)&&rendererTransitions.size()<64){Map<String,Object> transition=new LinkedHashMap<>();transition.put("elapsed_ns",now-started);transition.put("renderer",currentRenderer);transition.put("step",STEPS[step]);rendererTransitions.add(transition);previousRenderer=currentRenderer;}if(previous!=0){double delta=(now-previous)/1e6;intervals.add(delta);trace.add((now-started)+","+STEPS[step]+","+delta+","+Class240.anInt4674+phaseTrace());}else phaseTrace();previous=now;}return null;}
}
