import java.awt.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import com.GameClient;
import com.GameClient.ControllerTarget;
import net.runelite.api.Perspective;
import net.runelite.api.coords.LocalPoint;
import net.runelite.client.RuneLite;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.input.controller.UiState;
import net.runelite.client.ui.overlay.*;

/** Actual cache, player-lit fire and Blood Pact instance, in an isolated admin fixture. */
public final class NativePlaytestTwoProbe {
    private static int stage;
    private static long since;
    private static int cookedBefore;
    private static final Map<String,Object> results=new LinkedHashMap<>();
    private static final Observation observation=new Observation();
    public static boolean active(){return stage>0&&stage<10;}
    private static void next(){stage++;since=System.currentTimeMillis();}
    private static void command(String value){Class82.method812(value,false,false,(byte)-79);}
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    private static UiState.Widget item(String name){
        int id=name.equals("Tinderbox")?590:name.equals("Logs")?1511:name.equals("Raw shrimps")?317:name.equals("Shrimps")?315:-1;
        for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&(w.itemId==id||w.name.equalsIgnoreCase(name)))return w;return null;
    }
    private static ControllerTarget object(int id) throws Exception {
        Method scan=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);scan.setAccessible(true);
        for(ControllerTarget target:(java.util.List<ControllerTarget>)scan.invoke(null,true))
            if(target.kind()==2&&(int)(target.identifier>>>32)==id)return target;
        return null;
    }
    private static int count(int id){int total=0;for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.itemId==id)total+=w.quantity;return total;}
    private static String inventoryNames(){StringBuilder text=new StringBuilder();for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.itemId>=0)text.append(w.itemId).append(":").append(w.name).append(";");return text.toString();}
    public static boolean tick(String marker) throws Exception {
        if(stage==10)return true;
        long now=System.currentTimeMillis();
        Files.write(Paths.get(marker+".playtest2.status"),("stage="+stage+" ready="+ControllerWorld.ready()+" plane="+Class132.aPlayer_1907.plane+" projection="+observation.success+" polygon="+observation.last+" inventory="+inventoryNames()).getBytes("UTF-8"));
        if(stage>0)require(now-since<60_000,"Playtest 2 native stage timed out: "+stage);
        if(stage==0){
            ConfigManager config=RuneLite.getInjector().getInstance(ConfigManager.class);
            config.setConfiguration("soloscapecontroller","setupComplete",true);
            config.setConfiguration("soloscapecontroller","showMovementTiles",true);
            RuneLite.getInjector().getInstance(OverlayManager.class).add(observation);
            require(SoloScapeConnection.fireUse(),"Matched server did not advertise fire-use");
            command("level Firemaking 99");command("level Cooking 99");command("item logs 1");command("item raw_shrimps 1");
            ControllerUi.openInventory();next();return false;
        }
        if(stage==1){
            ControllerUi.openInventory();
            UiState.Widget box=item("Tinderbox");if(box==null||item("Logs")==null||item("Raw shrimps")==null)return false;
            cookedBefore=count(315);
            for(UiState.Action action:box.actions)if(action.type==13){require(ControllerUi.invoke(box,action),"Tinderbox Use failed");next();return false;}
            return false;
        }
        if(stage==2){
            UiState.Widget log=item("Logs");if(log==null||log.actions.length==0)return false;
            require(log.actions[0].type==6,"Selected tinderbox did not target logs");
            require(ControllerUi.invoke(log,log.actions[0]),"Tinderbox-on-logs failed");next();return false;
        }
        if(stage==3){
            ControllerTarget fire=object(2732);if(fire==null||!ControllerWorld.ready())return false;
            require(fire.option.equals("Use"),"Player-lit fire missing Use");
            require(ControllerWorld.interact(fire),"Native fire Use failed");results.put("player_lit_fire_use",true);next();return false;
        }
        if(stage==4){
            if(count(317)!=0||count(315)<=cookedBefore)return false;
            results.put("cooked_shrimps_without_mouse",true);results.put("cooked_count_before",cookedBefore);results.put("cooked_count_after",count(315));
            command("var blood_pact kayle");command("tele 3246 3198 0");next();return false;
        }
        if(stage==5){
            if(now-since<2000||!ControllerWorld.ready())return false;
            ControllerTarget stairs=object(48797);if(stairs==null)return false;
            require(ControllerWorld.interact(stairs),"Catacomb stairs failed");next();return false;
        }
        if(stage==6){
            if(Class132.aPlayer_1907.plane!=1||!ControllerWorld.ready())return false;
            require(za_Sub2.regionTileX>=6400,"Quest used source map instead of instance: "+za_Sub2.regionTileX);
            observation.success=false;next();return false;
        }
        if(stage==7){
            if(!observation.success)return false;
            results.put("blood_pact_instanced_player_polygon",observation.last);
            ControllerWorld.clearWalkMarker();
            results.put("idle_destination_absent",ControllerWorld.walkDestination()==null);
            results.put("idle_player_tile_pixels",observation.pixels);
            require(observation.pixels>0,"Player tile overlay did not draw without a destination");
            next();return false;
        }
        if(stage==8){
            int x=Class132.aPlayer_1907.x>>9,y=Class132.aPlayer_1907.y>>9;
            Class361 map=Class348_Sub45.aClass361Array7108[Class132.aPlayer_1907.plane];
            boolean marked=false;
            for(int[] delta:new int[][]{{0,1},{1,0},{0,-1},{-1,0}})
                if(net.runelite.client.input.controller.WorldInput.canStep(map.anIntArrayArray4438,x-map.anInt4453,y-map.anInt4441,delta[0],delta[1])) {
                    ControllerWorld.markDirectDestination(delta[0],delta[1]);
                    net.runelite.api.coords.WorldPoint destination=ControllerWorld.walkDestination();
                    require(destination!=null,"Instance direct destination disappeared");
                    LocalPoint local=LocalPoint.fromWorld(RuneLite.getInjector().getInstance(GameClient.class),destination);
                    require(local!=null,"Instance destination not local");
                    results.put("blood_pact_direct_destination",destination.toString());marked=true;break;
                }
            require(marked,"No walkable instance neighbour for marker check");
            command("tele 3221 3219 0");next();return false;
        }
        if(stage==9){
            if(Class132.aPlayer_1907.plane!=0||!ControllerWorld.ready()||now-since<2000)return false;
            RuneLite.getInjector().getInstance(OverlayManager.class).remove(observation);
            Files.write(Paths.get(marker+".playtest2.json"),new com.google.gson.Gson().toJson(results).getBytes("UTF-8"));
            System.out.println("Native playtest 2: player-lit fire Use/cooking and Blood Pact instance projection passed.");next();return true;
        }
        return false;
    }
    private static final class Observation extends Overlay {
        volatile boolean success;volatile int pixels;volatile String last="waiting";
        Observation(){setPosition(OverlayPosition.DYNAMIC);setLayer(OverlayLayer.UNDER_WIDGETS);}
        @Override public Dimension render(Graphics2D graphics){
            GameClient client=RuneLite.getInjector().getInstance(GameClient.class);
            if(!client.isControllerWorldReady())return null;
            LocalPoint tile=LocalPoint.fromScene(client.getLocalPlayerSceneX(),client.getLocalPlayerSceneY());
            Polygon polygon=Perspective.getCanvasTilePoly(client,tile);
            last="plane="+client.getPlane()+" tile="+tile+" height="+client.getTileHeight(tile.getX(),tile.getY(),client.getPlane())+" polygon="+(polygon==null?"null":polygon.getBounds());
            if(stage==7&&polygon!=null&&polygon.getBounds().width>0&&polygon.getBounds().height>0) {
                try {
                    ControllerWorld.clearWalkMarker();
                    java.lang.reflect.Field list=OverlayManager.class.getDeclaredField("overlays");list.setAccessible(true);
                    java.awt.image.BufferedImage image=new java.awt.image.BufferedImage(client.getCanvasWidth(),client.getCanvasHeight(),java.awt.image.BufferedImage.TYPE_INT_ARGB);
                    Graphics2D draw=image.createGraphics();
                    try {for(Overlay overlay:(java.util.List<Overlay>)list.get(RuneLite.getInjector().getInstance(OverlayManager.class)))
                        if(overlay.getClass().getSimpleName().equals("SoloScapeMovementOverlay"))overlay.render(draw);}
                    finally {draw.dispose();}
                    pixels=0;for(int px=0;px<image.getWidth();px++)for(int py=0;py<image.getHeight();py++)if((image.getRGB(px,py)>>>24)!=0)pixels++;
                    success=pixels>0;
                }catch(Exception ex){throw new IllegalStateException("Movement tile render failed",ex);}
            }
            return null;
        }
    }
}
