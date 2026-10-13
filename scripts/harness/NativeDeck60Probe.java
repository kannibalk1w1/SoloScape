import java.awt.*;
import java.lang.management.*;
import java.lang.reflect.Field;
import java.nio.file.*;
import java.util.*;
import com.GameClient;
import com.google.gson.Gson;
import net.runelite.client.RuneLite;
import net.runelite.client.plugins.*;
import net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin;
import net.runelite.client.ui.ClientUI;
import net.runelite.client.ui.overlay.*;

/** Full-resolution, alternating controller/pacing/toolkit comparisons in a disposable world. */
public final class NativeDeck60Probe extends Overlay {
 private static NativeDeck60Probe probe;
 private final ArrayList<Double> intervals=new ArrayList<>();
 private final Map<String,Object> results=new LinkedHashMap<>();
 private final ThreadMXBean cpu=ManagementFactory.getThreadMXBean();
 private long mark,previous,cpuStart;private int stage;private boolean switched;private volatile boolean resized;
 private Plugin controller;
 private final String[] names={"native_unpaced_on","native_60_on","native_60_off","native_60_on_repeat","native_uncapped_on","opengl_60_on","opengl_uncapped_on"};
 private final ArrayList<String> trace=new ArrayList<>();
 public NativeDeck60Probe(){setPosition(OverlayPosition.DYNAMIC);setLayer(OverlayLayer.ALWAYS_ON_TOP);}
 public static boolean active(){return probe!=null;}
 private static Object field(Object object,String name)throws Exception {Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);}
 public static boolean tick(String marker)throws Exception{
  if(probe==null){
   probe=new NativeDeck60Probe();RuneLite.getInjector().getInstance(OverlayManager.class).add(probe);
   for(Plugin p:RuneLite.getInjector().getInstance(PluginManager.class).getPlugins())if(p instanceof SoloScapeControllerPlugin)probe.controller=p;
   net.runelite.client.config.ConfigManager config=RuneLite.getInjector().getInstance(net.runelite.client.config.ConfigManager.class);
   config.setConfiguration("runelite","containInScreen2",net.runelite.client.ui.ContainableFrame.Mode.NEVER);
   config.setConfiguration("runelite","lockWindowSize",false);
   config.setConfiguration("runelite","gameSize",new Dimension(1280,800));
   Class316.aClass348_Sub51_3959.method3429((byte)74,Class316.aClass348_Sub51_3959.aClass239_Sub23_7231,0);
   config.setConfiguration("soloscapecontroller","setupComplete",true);config.setConfiguration("soloscapecontroller","debug",true);
   ControllerUi.openInventory();
   if(probe.controller!=null){((net.runelite.client.input.controller.UiControls)field(probe.controller,"ui")).reset();Field f=SoloScapeControllerPlugin.class.getDeclaredField("settingsOpen");f.setAccessible(true);f.setBoolean(probe.controller,false);}
   final GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
   javax.swing.SwingUtilities.invokeLater(()->{try{
    net.runelite.client.ui.ClientUI ui=RuneLite.getInjector().getInstance(net.runelite.client.ui.ClientUI.class);
    if(!ui.isFullscreen())ui.toggleFullscreen();
    if(!ui.isFullscreen())throw new IllegalStateException("Fullscreen did not open");
    probe.resized=true;
   }catch(Exception ex){throw new IllegalStateException(ex);}});
   probe.results.put("initial_renderer",Class348_Sub8.aHa6654.getClass().getName());
   probe.results.put("initial_pacing",DetachedRenderer.isActive());probe.results.put("initial_fps_target",DetachedRenderer.getFpsTarget());
   probe.stage=Integer.getInteger("soloscape.deck60.startStage",0);
   probe.trace.add("stage,elapsed_ns,interval_ms");probe.mark=System.nanoTime();return false;
  }
  if(probe.stage>=probe.names.length)return ControllerWorld.ready();
  GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
  if(!probe.resized)return false;
  if(!probe.switched){
   PluginManager manager=RuneLite.getInjector().getInstance(PluginManager.class);
   if(probe.stage==0&&Class348_Sub8.aHa6654.getClass()!=oa.class)Class258_Sub3_Sub1.method1971(-2,null,true,2);
   if(probe.stage==2&&probe.controller!=null)manager.stopPlugin(probe.controller);
   if(probe.stage==3&&probe.controller!=null)manager.startPlugin(probe.controller);
   if(probe.stage==5){probe.results.put("preset_previous_shadows",Class316.aClass348_Sub51_3959.aClass239_Sub7_7238.method1748(-32350));if(!client.setControllerDeck60(true))throw new IllegalStateException(client.getControllerPerformanceStatus());probe.results.put("requested_opengl",1);probe.results.put("deck_preset_status",client.getControllerPerformanceStatus());}
   client.setDetachedRendererFpsTarget(probe.stage==4||probe.stage==6?0:60);
   client.setDetachedRendererEnabled(probe.stage!=0);
   probe.switched=true;probe.mark=System.nanoTime();probe.previous=0;probe.intervals.clear();return false;
  }
  if(System.nanoTime()-probe.mark<25_000_000_000L)return false;
  if(!ControllerWorld.ready())return false;
  ArrayList<Double> sorted=new ArrayList<>(probe.intervals);Collections.sort(sorted);
  if(sorted.size()<30){System.out.println("Insufficient frame samples, phase timings: "+new Gson().toJson(timings()));throw new IllegalStateException("Too few full-resolution frame samples at "+probe.names[probe.stage]);}
  Map<String,Object> sample=new LinkedHashMap<>();sample.put("samples",sorted.size());sample.put("median_ms",sorted.get(sorted.size()/2));sample.put("p95_ms",sorted.get((sorted.size()-1)*95/100));sample.put("p99_ms",sorted.get((sorted.size()-1)*99/100));sample.put("max_ms",sorted.get(sorted.size()-1));
  sample.put("average_fps",sorted.size()*1000.0/sorted.stream().mapToDouble(Double::doubleValue).sum());
  sample.put("renderer",Class348_Sub8.aHa6654.getClass().getName());sample.put("toolkit_preference",Class316.aClass348_Sub51_3959.aClass239_Sub25_7271.method1829(-32350));sample.put("native_object_shadow_setting",Class316.aClass348_Sub51_3959.aClass239_Sub7_7238.method1748(-32350));sample.put("pacing",DetachedRenderer.isActive());sample.put("fps_target",DetachedRenderer.getFpsTarget());
  sample.put("canvas",client.getCanvas().getSize().toString());
  if(client.getCanvas().getWidth()!=1280||client.getCanvas().getHeight()!=800)throw new IllegalStateException("Requested full-resolution canvas was not adopted: "+client.getCanvas().getSize());sample.put("native_dimensions",Class321.anInt4017+"x"+Class348_Sub42_Sub8_Sub2.anInt10432);
  sample.put("controller_connected",probe.controller!=null&&((net.runelite.client.input.controller.GamepadState)field(probe.controller,"rawState")).connected);
  sample.put("canvas_focused",client.getCanvas().isFocusOwner());sample.put("client_thread_cpu_ms",(probe.cpu.getCurrentThreadCpuTime()-probe.cpuStart)/1e6);
  if(Class348_Sub8.aHa6654 instanceof ha_Sub2){sample.put("gl_texture_bytes",((ha_Sub2)Class348_Sub8.aHa6654).anInt7748);sample.put("gl_vendor",field(Class348_Sub8.aHa6654,"aString7845"));sample.put("gl_renderer",field(Class348_Sub8.aHa6654,"aString7790"));}
  sample.put("phase_timings",timings());
  probe.results.put(probe.names[probe.stage],sample);
  Files.write(Paths.get(marker+".deck60.json"),new Gson().toJson(probe.results).getBytes("UTF-8"));
  Files.write(Paths.get(marker+".deck60.csv"),probe.trace,java.nio.charset.StandardCharsets.UTF_8);
  System.out.println("Deck60 stage "+probe.names[probe.stage]+": "+new Gson().toJson(sample));
  probe.stage++;probe.switched=false;
  if(probe.stage>=probe.names.length){
   client.setControllerDeck60(false);probe.results.put("preset_restored",client.getControllerPerformanceStatus());probe.results.put("preset_restored_shadows",Class316.aClass348_Sub51_3959.aClass239_Sub7_7238.method1748(-32350));
   if(!probe.results.get("preset_previous_shadows").equals(probe.results.get("preset_restored_shadows")))throw new IllegalStateException("Preset did not restore native shadows");
   Files.write(Paths.get(marker+".deck60.json"),new Gson().toJson(probe.results).getBytes("UTF-8"));
  }
  return false;
 }
 private static Object timings(){try{return Class.forName("com.FrameTimings").getMethod("snapshotAndReset").invoke(null);}catch(ClassNotFoundException ex){return "unavailable in baseline";}catch(Exception ex){throw new IllegalStateException(ex);}}
 @Override public Dimension render(Graphics2D g){
  long now=System.nanoTime();if(switched&&now-mark>=10_000_000_000L){if(previous!=0&&intervals.size()<10000){double interval=(now-previous)/1e6;intervals.add(interval);trace.add(names[stage]+","+(now-mark)+","+interval);}else if(previous==0){cpuStart=cpu.getCurrentThreadCpuTime();timings();}previous=now;}
  return null;
 }
}
