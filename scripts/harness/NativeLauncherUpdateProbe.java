package net.runelite.client.soloscape.launcher;

import java.awt.*;
import java.awt.event.KeyEvent;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.concurrent.*;
import javax.swing.*;

/** Real Swing/controller adapter and real backend, with private deterministic release metadata. */
public final class NativeLauncherUpdateProbe {
    static Object launcher; static Path root; static Robot robot;
    static <T>T edt(Callable<T> call)throws Exception { FutureTask<T> task=new FutureTask<>(call);SwingUtilities.invokeAndWait(task);return task.get(); }
    static Object field(String name)throws Exception { Field f=SoloScapeLauncher.class.getDeclaredField(name);f.setAccessible(true);return f.get(launcher); }
    static void invoke(String name)throws Exception { Method m=SoloScapeLauncher.class.getDeclaredMethod(name);m.setAccessible(true);m.invoke(launcher); }
    static void require(boolean value,String message) { if(!value)throw new IllegalStateException(message); }
    static void waitFor(Callable<Boolean> condition,String message)throws Exception { long end=System.currentTimeMillis()+10000;while(!edt(condition)){require(System.currentTimeMillis()<end,message);Thread.sleep(40);} }
    static JDialog dialog(String title) { for(Window w:Window.getWindows())if(w instanceof JDialog&&w.isShowing()&&title.equals(((JDialog)w).getTitle()))return (JDialog)w;return null; }
    static JButton button(Component component,String title) { if(component instanceof JButton&&title.equals(((JButton)component).getText()))return (JButton)component;if(component instanceof Container)for(Component c:((Container)component).getComponents()){JButton found=button(c,title);if(found!=null)return found;}return null; }
    static JTextArea notes(Component component) { if(component instanceof JTextArea)return (JTextArea)component;if(component instanceof Container)for(Component c:((Container)component).getComponents()){JTextArea found=notes(c);if(found!=null)return found;}return null; }
    static void key(int code)throws Exception { robot.keyPress(code);Thread.sleep(120);robot.keyRelease(code);Thread.sleep(250); }
    static void openSettings()throws Exception {
        edt(()->{((JButton)field("settings")).requestFocusInWindow();return null;});
        waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()==field("settings"),"Settings did not receive seed focus");
        key(KeyEvent.VK_ENTER);waitFor(()->dialog("Launcher Settings")!=null,"Mapped A did not open Settings");
        require(edt(()->button(dialog("Launcher Settings"),"Check for updates")!=null),"Check button is absent from built launcher");
        for(int i=0;i<16;i++){
            if(edt(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()==button(dialog("Launcher Settings"),"Check for updates")))return;
            key(KeyEvent.VK_DOWN);
        }
        throw new IllegalStateException("Mapped navigation did not reach Check for updates");
    }
    static void fixture(int delay)throws Exception {
        Files.write(root.resolve("update-response.json"),("{\"delay\":"+delay+",\"state\":\"release_available\",\"message\":\"Published release: v0.1.0. Automatic installation is not available yet.\",\"notes\":\"Original fixture notes: <html> stays plain text.\",\"install_available\":false}").getBytes("UTF-8"));
    }
    public static void main(String[] args)throws Exception {
        root=Paths.get(args[0]);robot=new Robot();System.setProperty("soloscape.launcher.steamKeyboard","true");
        try {
            fixture(0);
            launcher=edt(()->{Constructor<?> ctor=SoloScapeLauncher.class.getDeclaredConstructor(Path.class);ctor.setAccessible(true);return ctor.newInstance(root);});
            waitFor(()->((JFrame)field("frame")).isActive(),"Launcher not active");Thread.sleep(400);
            openSettings();key(KeyEvent.VK_ENTER);waitFor(()->dialog("SoloScape updates")!=null,"Mapped A did not check updates");
            edt(()->{JDialog update=dialog("SoloScape updates");require(update.getOwner()==dialog("Launcher Settings"),"Expected nested Settings ownership");require(notes(update).getText().contains("<html> stays plain text."),"Notes did not remain plain text");return null;});
            Rectangle bounds=edt(()->{JDialog update=dialog("SoloScape updates");return new Rectangle(update.getLocationOnScreen(),update.getSize());});
            javax.imageio.ImageIO.write(robot.createScreenCapture(bounds),"png",root.resolve("launcher-update-check.png").toFile());
            key(KeyEvent.VK_ESCAPE);waitFor(()->dialog("SoloScape updates")==null,"Mapped B did not close nested update dialog");
            require(edt(()->dialog("Launcher Settings")!=null),"B also dismissed the parent Settings dialog");
            waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getActiveWindow()==dialog("Launcher Settings"),"Nested B did not restore parent focus");
            key(KeyEvent.VK_ESCAPE);waitFor(()->dialog("Launcher Settings")==null,"Mapped B did not return from Settings");
            fixture(1000);openSettings();key(KeyEvent.VK_ENTER);key(KeyEvent.VK_ESCAPE);
            waitFor(()->dialog("Launcher Settings")==null,"Could not cancel Settings while check pending");Thread.sleep(1400);
            require(edt(()->dialog("SoloScape updates")==null),"Late response reopened a cancelled dialog");
            edt(()->{invoke("close");return null;});waitFor(()->!((JFrame)field("frame")).isDisplayable(),"Launcher did not close");
            Files.write(root.resolve("update-ui-result.json"),("{\"environment\":\"Private Swing/Xvfb and deterministic metadata; no SDL/hardware acceptance\",\"mapped_a_opens_settings\":true,\"mapped_navigation_reaches_check\":true,\"mapped_a_checks\":true,\"plain_text_notes\":true,\"nested_b_preserves_parent\":true,\"late_response_does_not_reopen_dialog\":true}").getBytes("UTF-8"));
            System.out.println("Native launcher update navigation and nested B ancestry passed.");System.exit(0);
        } catch(Exception ex) {
            ex.printStackTrace();try{edt(()->{for(Window w:Window.getWindows())if(w instanceof JDialog)w.dispose();if(launcher!=null)invoke("close");return null;});}catch(Exception ignored){}System.exit(2);
        }
    }
}
