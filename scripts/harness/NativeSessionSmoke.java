import java.awt.*;
import java.awt.image.BufferedImage;
import java.nio.file.*;
import javax.imageio.ImageIO;
import javax.swing.*;
import net.runelite.client.RuneLite;
import net.runelite.client.callback.ClientThread;
public class NativeSessionSmoke {
 public static void main(String[] args) throws Exception {
  String marker=args[0]; Loader.main(new String[]{"--address","127.0.0.1","--port",args[1]});
  new Thread(()->{
   long started=System.currentTimeMillis();
   long deadline=started+(Boolean.getBoolean("soloscape.deck60.route")?(Integer.getInteger("soloscape.deck60.route.seconds",1800)*1000L+900000):Boolean.getBoolean("soloscape.deck60.probe")?420000:Boolean.getBoolean("soloscape.playable.probe")?420000:150000);
   while(System.currentTimeMillis()<deadline) {
    try {
     Thread.sleep(500);
     if(RuneLite.getInjector()==null)continue;
     RuneLite.getInjector().getInstance(ClientThread.class).invokeLater(()->{
      ControllerUi.enable(true);
      SoloScapeConnection.update();
      net.runelite.client.input.controller.UiState ui=ControllerUi.snapshot();
      if(ui.dialogue.length>0 && ui.dialogue[0].actions.length>0 && !(Boolean.getBoolean("soloscape.deck60.route")&&NativeDeckRouteProbe.active()))
          ControllerUi.invoke(ui.dialogue[0],ui.dialogue[0].actions[0]); // ordinary fresh Continue, not a fabricated packet
      try {
       Files.write(Paths.get(marker+".status"),("state="+Class240.anInt4674+" camera="+Class348_Sub40_Sub21.anInt9282+" player="+(Class132.aPlayer_1907!=null)+" ready="+ControllerWorld.ready()+" tabs="+ControllerUi.availableTabs()+" dialogue="+ControllerUi.hasDialogue()+" dialogueId="+ControllerUi.snapshot().dialogueId+" modal="+ControllerUi.hasModalPanel()+" entry="+ControllerEntry.active()+" menu="+Class305.aBoolean3870+" loading="+Class36.anInt489+" dirty="+Canvas_Sub1.mapRegionDirty+" capabilities="+SoloScapeConnection.status()).getBytes("UTF-8"));
      } catch(Exception ignored) { }
      if(System.currentTimeMillis()-started>15000 && ((ControllerWorld.ready() && ControllerUi.availableTabs()!=0 && SoloScapeConnection.verified())
          || Boolean.getBoolean("soloscape.adventure.probe")&&NativeAdventureProbe.active()
          || Boolean.getBoolean("soloscape.performance.probe")&&NativePerformanceProbe.active()
          || Boolean.getBoolean("soloscape.fullscreen.probe")&&NativeFullscreenProbe.active()
          || Boolean.getBoolean("soloscape.playtest2.probe")&&NativePlaytestTwoProbe.active()
          || Boolean.getBoolean("soloscape.map.probe")&&NativeMapProbe.active()
          || Boolean.getBoolean("soloscape.artwork.probe")&&NativeArtworkProbe.active()
          || Boolean.getBoolean("soloscape.tabbar.probe")&&NativeTabBarProbe.active()
          || Boolean.getBoolean("soloscape.deck60.probe")&&NativeDeck60Probe.active()
          || Boolean.getBoolean("soloscape.deck60.route")&&NativeDeckRouteProbe.active())) {
       try {
        if(Boolean.getBoolean("soloscape.deck60.route")&&!NativeDeckRouteProbe.tick(marker))return true;
        if(Boolean.getBoolean("soloscape.deck60.probe")&&!NativeDeck60Probe.tick(marker))return true;
        if(Boolean.getBoolean("soloscape.fullscreen.probe")&&!NativeFullscreenProbe.tick())return true;
        if(Boolean.getBoolean("soloscape.playtest2.probe")&&!NativePlaytestTwoProbe.tick(marker))return true;
        if(Boolean.getBoolean("soloscape.map.probe")&&!NativeMapProbe.tick())return true;
        if(Boolean.getBoolean("soloscape.artwork.probe")&&!NativeArtworkProbe.tick(marker))return true;
        if(Boolean.getBoolean("soloscape.tabbar.probe")&&!NativeTabBarProbe.tick(marker))return true;
        if(Boolean.getBoolean("soloscape.performance.probe")&&!NativePerformanceProbe.tick(marker))return true;
        if(Boolean.getBoolean("soloscape.sidebar.probe")&&!NativeSidebarProbe.tick())return true;
        if(Boolean.getBoolean("soloscape.adventure.probe")&&!NativeAdventureProbe.tick(marker))return true;
        Path path=Paths.get(marker);
        if(!Files.exists(path)) {
         Files.write(path,("state=10\nworldReady=true\nserverCapabilities=verified\nvisibleTabs="+ControllerUi.availableTabs()+"\nsceneX="+Class132.aPlayer_1907.x+"\nsceneY="+Class132.aPlayer_1907.y+"\n").getBytes("UTF-8"));
         SwingUtilities.invokeLater(()->{try {
          Canvas canvas=RuneLite.getInjector().getInstance(com.GameClient.class).getCanvas();
          Rectangle area=new Rectangle(canvas.getLocationOnScreen(),canvas.getSize());
          BufferedImage image=new Robot().createScreenCapture(area);ImageIO.write(image,"png",new java.io.File(marker+".png"));
         }catch(Exception ex){System.err.println("Private screenshot failed.");}});
        }
       } catch(Exception ex){ex.printStackTrace();if(Boolean.getBoolean("soloscape.deck60.route"))try{NativeDeckRouteProbe.failed(marker,ex);}catch(Exception traceFailure){System.err.println("Could not retain failed route trace: "+traceFailure);}System.exit(2);}
      }
      return true;
     });
     if(Files.exists(Paths.get(marker))){Thread.sleep(2500);System.exit(0);}
    }catch(Exception ex){System.err.println("Private harness probe failed.");}
   }
   System.err.println("Private native probe timed out: "+(Boolean.getBoolean("soloscape.playable.probe")?NativePlayableLoopProbe.progress():"login/adventure incomplete"));System.exit(2);
  },"private-smoke-probe").start();
 }
}
