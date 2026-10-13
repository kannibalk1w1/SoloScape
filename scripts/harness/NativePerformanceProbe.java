import java.awt.*;
import java.nio.file.*;
import java.util.*;
import com.GameClient;
import com.google.gson.Gson;
import net.runelite.client.RuneLite;
import net.runelite.client.plugins.*;
import net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin;
import net.runelite.client.ui.overlay.*;

/** Stationary scene comparisons in disposable profiles; no player settings are changed. */
public final class NativePerformanceProbe extends Overlay {
 private static NativePerformanceProbe probe;
 private final java.util.List<Double> intervals=new ArrayList<>();
 private final Map<String,Object> results=new LinkedHashMap<>();
 private long mark,previous;private int stage;
 private Plugin controller;
 private final String[] names={"controller_on","controller_off","reduced_scene"};
 public NativePerformanceProbe(){setPosition(OverlayPosition.DYNAMIC);setLayer(OverlayLayer.ALWAYS_ON_TOP);}
 public static boolean active(){return probe!=null;}
 public static boolean tick(String marker)throws Exception{
  if(probe==null){
   probe=new NativePerformanceProbe();RuneLite.getInjector().getInstance(OverlayManager.class).add(probe);
   probe.mark=System.nanoTime();GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
   probe.results.put("renderer",Class348_Sub8.aHa6654.getClass().getName());
   probe.results.put("canvas",client.getCanvas().getSize().toString());
   for(Plugin p:RuneLite.getInjector().getInstance(PluginManager.class).getPlugins())if(p instanceof SoloScapeControllerPlugin)probe.controller=p;
   RuneLite.getInjector().getInstance(net.runelite.client.config.ConfigManager.class).setConfiguration("soloscapecontroller","setupComplete",true);
   ControllerUi.openInventory();
   if(probe.controller!=null){
    java.lang.reflect.Field field=SoloScapeControllerPlugin.class.getDeclaredField("ui");field.setAccessible(true);((net.runelite.client.input.controller.UiControls)field.get(probe.controller)).reset();
    field=SoloScapeControllerPlugin.class.getDeclaredField("settingsOpen");field.setAccessible(true);field.setBoolean(probe.controller,false);
   }
   return false;
  }
  if(probe.stage>=3)return true;
  if(System.nanoTime()-probe.mark<12_000_000_000L)return false;
  java.util.List<Double> sorted=new ArrayList<>(probe.intervals);Collections.sort(sorted);
  if(sorted.size()<30)throw new IllegalStateException("Too few frame samples");
  Map<String,Object> sample=new LinkedHashMap<>();sample.put("samples",sorted.size());sample.put("median_ms",sorted.get(sorted.size()/2));sample.put("p95_ms",sorted.get((sorted.size()-1)*95/100));
  sample.put("average_fps",sorted.size()*1000.0/sorted.stream().mapToDouble(Double::doubleValue).sum());
  probe.results.put(probe.names[probe.stage],sample);probe.stage++;
  if(probe.stage==3){Files.write(Paths.get(marker+".performance.json"),new Gson().toJson(probe.results).getBytes("UTF-8"));return true;}
  if(probe.stage==1&&probe.controller!=null)RuneLite.getInjector().getInstance(PluginManager.class).stopPlugin(probe.controller);
  if(probe.stage==2){GameClient client=RuneLite.getInjector().getInstance(GameClient.class);client.setDrawRadiusScale(65);client.setHideUpperFloors(true);}
  probe.mark=System.nanoTime();probe.previous=0;probe.intervals.clear();return false;
 }
 @Override public Dimension render(Graphics2D g){long now=System.nanoTime();if(previous!=0&&intervals.size()<5000)intervals.add((now-previous)/1000000.0);previous=now;return null;}
}
