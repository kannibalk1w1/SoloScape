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
   long deadline=started+150000;
   while(System.currentTimeMillis()<deadline) {
    try {
     Thread.sleep(500);
     if(RuneLite.getInjector()==null)continue;
     RuneLite.getInjector().getInstance(ClientThread.class).invokeLater(()->{
      ControllerUi.enable(true);
      net.runelite.client.input.controller.UiState ui=ControllerUi.snapshot();
      if(ui.dialogue.length>0 && ui.dialogue[0].actions.length>0)
          ControllerUi.invoke(ui.dialogue[0],ui.dialogue[0].actions[0]); // ordinary fresh Continue, not a fabricated packet
      try {
       Files.write(Paths.get(marker+".status"),("state="+Class240.anInt4674+" camera="+Class348_Sub40_Sub21.anInt9282+" player="+(Class132.aPlayer_1907!=null)+" ready="+ControllerWorld.ready()+" tabs="+ControllerUi.availableTabs()+" dialogue="+ControllerUi.hasDialogue()+" dialogueId="+ControllerUi.snapshot().dialogueId+" modal="+ControllerUi.hasModalPanel()+" entry="+ControllerEntry.active()+" menu="+Class305.aBoolean3870+" loading="+Class36.anInt489+" dirty="+Canvas_Sub1.mapRegionDirty).getBytes("UTF-8"));
      } catch(Exception ignored) { }
      if(System.currentTimeMillis()-started>15000 && ControllerWorld.ready() && ControllerUi.availableTabs()!=0) {
       try {
        Path path=Paths.get(marker);
        if(!Files.exists(path)) {
         Files.write(path,("state=10\nworldReady=true\nvisibleTabs="+ControllerUi.availableTabs()+"\nsceneX="+Class132.aPlayer_1907.x+"\nsceneY="+Class132.aPlayer_1907.y+"\n").getBytes("UTF-8"));
         SwingUtilities.invokeLater(()->{try {
          Rectangle area=GraphicsEnvironment.getLocalGraphicsEnvironment().getDefaultScreenDevice().getDefaultConfiguration().getBounds();
          BufferedImage image=new Robot().createScreenCapture(area);ImageIO.write(image,"png",new java.io.File(marker+".png"));
         }catch(Exception ex){System.err.println("Private screenshot failed.");}});
        }
       } catch(Exception ex){System.err.println("Private marker failed.");}
      }
      return true;
     });
     if(Files.exists(Paths.get(marker))){Thread.sleep(2500);System.exit(0);}
    }catch(Exception ex){System.err.println("Private harness probe failed.");}
   }
   System.err.println("Private login did not reach in-game state.");System.exit(2);
  },"private-smoke-probe").start();
 }
}
