package net.runelite.client.soloscape.launcher;

import java.awt.*;
import java.awt.event.KeyEvent;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;
import javax.swing.*;

/**
 * Private acceptance of the managed updater through the real launcher, mapped controller input and the real backend.
 * Launch 1 (private-test-a): play a world, then Check, cancel a download, Download, Install and Restart (the JVM
 * exits 75 from the launcher itself). Launch 2 (private-test-b): acknowledge the result, then Continue.
 * Input is synthetic AWT Robot on an owned Xvfb display; this is not SDL/hardware acceptance.
 */
public final class NativeManagedUpdateProbe {
    static Object launcher; static Path dir; static Robot robot; static int launch;
    static <T>T edt(Callable<T> call)throws Exception { FutureTask<T> task=new FutureTask<>(call);SwingUtilities.invokeAndWait(task);return task.get(); }
    static Object field(String name)throws Exception { Field f=SoloScapeLauncher.class.getDeclaredField(name);f.setAccessible(true);return f.get(launcher); }
    static void require(boolean value,String message) { if(!value)throw new IllegalStateException(message); }
    static void waitFor(Callable<Boolean> condition,int seconds,String message)throws Exception { long end=System.currentTimeMillis()+seconds*1000L;while(!edt(condition)){require(System.currentTimeMillis()<end,message);Thread.sleep(40);} }
    static JDialog dialog(String title) { for(Window w:Window.getWindows())if(w instanceof JDialog&&w.isShowing()&&title.equals(((JDialog)w).getTitle()))return (JDialog)w;return null; }
    static JButton button(Component component,String title) { if(component instanceof JButton&&title.equals(((JButton)component).getText()))return (JButton)component;if(component instanceof Container)for(Component c:((Container)component).getComponents()){JButton found=button(c,title);if(found!=null)return found;}return null; }
    static <T extends Component> T first(Component component,Class<T> type) { if(type.isInstance(component))return type.cast(component);if(component instanceof Container)for(Component c:((Container)component).getComponents()){T found=first(c,type);if(found!=null)return found;}return null; }
    static String labels(Component component) { StringBuilder out=new StringBuilder();if(component instanceof JLabel)out.append(((JLabel)component).getText()).append('\n');if(component instanceof Container)for(Component c:((Container)component).getComponents())out.append(labels(c));return out.toString(); }
    static void key(int code)throws Exception { robot.keyPress(code);Thread.sleep(400);robot.keyRelease(code);Thread.sleep(350); }
    static void pressUntil(int code,Callable<Boolean> done,String message)throws Exception {
        for(int attempt=0;attempt<4;attempt++){ key(code);long end=System.currentTimeMillis()+2500;while(System.currentTimeMillis()<end){if(edt(done))return;Thread.sleep(40);} }
        throw new IllegalStateException(message);
    }
    static Component focus() { return KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner(); }
    static void shot(String name)throws Exception {
        Rectangle bounds=edt(()->{Window active=KeyboardFocusManager.getCurrentKeyboardFocusManager().getActiveWindow();return new Rectangle(active.getLocationOnScreen(),active.getSize());});
        javax.imageio.ImageIO.write(robot.createScreenCapture(bounds),"png",dir.resolve("launch"+launch+"-"+name+".png").toFile());
    }
    static void focusButton(String dialogTitle,String text,int direction)throws Exception {
        for(int i=0;i<30;i++){   // a mapped press can be lost while the EDT repaints the animated scene; retry, but bounded
            if(edt(()->focus()==button(dialog(dialogTitle),text)))return;
            key(direction);
        }
        throw new IllegalStateException("Mapped navigation did not reach "+text);
    }
    /** With no window manager the launcher may not hold X focus after the game client closes; click an inert area. */
    static void activateLauncher()throws Exception {
        JFrame frame=(JFrame)field("frame");
        edt(()->{frame.toFront();frame.requestFocus();return null;});
        long end=System.currentTimeMillis()+3000;
        while(!edt(()->frame.isActive())&&System.currentTimeMillis()<end)Thread.sleep(50);
        if(!edt(()->frame.isActive())){
            Point at=edt(()->frame.getLocationOnScreen());Dimension size=edt(()->frame.getSize());
            robot.mouseMove(at.x+size.width/2,at.y+70);robot.mousePress(java.awt.event.InputEvent.BUTTON1_DOWN_MASK);robot.mouseRelease(java.awt.event.InputEvent.BUTTON1_DOWN_MASK);
        }
        waitFor(()->frame.isActive(),10,"Launcher frame could not be activated");
    }
    static void openUpdates()throws Exception {
        Thread.sleep(2500);   // let the session teardown and scene animation settle before synthetic input
        activateLauncher();
        edt(()->{((JButton)field("settings")).requestFocusInWindow();return null;});
        waitFor(()->focus()==field("settings"),10,"Settings did not receive seed focus");
        pressUntil(KeyEvent.VK_ENTER,()->dialog("Launcher Settings")!=null,"Mapped A did not open Settings");
        focusButton("Launcher Settings","Updates…",KeyEvent.VK_DOWN);
        pressUntil(KeyEvent.VK_ENTER,()->dialog("SoloScape updates")!=null,"Mapped A did not open updates");
        edt(()->{require(dialog("SoloScape updates").getOwner()==dialog("Launcher Settings"),"Updates must be owned by Settings");return null;});
        waitFor(()->focus()==button(dialog("SoloScape updates"),"Check for updates"),10,"Updates dialog did not seed focus on Check");
    }
    static void closeUpdates()throws Exception {
        pressUntil(KeyEvent.VK_ESCAPE,()->dialog("SoloScape updates")==null,"Mapped B did not close updates");
        require(edt(()->dialog("Launcher Settings")!=null),"B also dismissed the parent Settings dialog");
        waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getActiveWindow()==dialog("Launcher Settings"),10,"Nested B did not restore parent focus");
        pressUntil(KeyEvent.VK_ESCAPE,()->dialog("Launcher Settings")==null,"Mapped B did not return from Settings");
    }
    static void playRound(String label,int round)throws Exception {
        waitFor(()->((JList<?>)field("list")).getModel().getSize()==1&&((JButton)field("play")).isEnabled()&&((JButton)field("play")).getText().equals(label),60,label+" unavailable");
        long started=System.nanoTime();
        edt(()->{((JButton)field("play")).doClick();return null;});
        waitFor(()->(Boolean)field("running"),30,"World worker did not start");
        waitFor(()->!(Boolean)field("running")&&((JLabel)field("status")).getText().contains("saved and verified"),240,"Native session did not verify closure");
        String json="{\"round\":"+round+",\"launch\":"+launch+",\"label\":\""+label+"\",\"elapsedSeconds\":"+(System.nanoTime()-started)/1e9+"}";
        Files.write(dir.resolve("round"+round+".json"),json.getBytes(StandardCharsets.UTF_8));
        long deadline=System.nanoTime()+30_000_000_000L;
        while(!Files.exists(dir.resolve("round"+round+".ack"))&&System.nanoTime()<deadline)Thread.sleep(50);
        require(Files.exists(dir.resolve("round"+round+".ack")),"Coordinator did not verify the stopped world");
    }
    static void log(String line)throws Exception { Files.write(dir.resolve("probe.log"),(line+"\n").getBytes(StandardCharsets.UTF_8),StandardOpenOption.CREATE,StandardOpenOption.APPEND); }
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);dir=Paths.get(args[1]);robot=new Robot();System.setProperty("soloscape.launcher.steamKeyboard","true");
        Path counter=dir.resolve("launches");
        launch=(Files.exists(counter)?Integer.parseInt(new String(Files.readAllBytes(counter),StandardCharsets.UTF_8).trim()):0)+1;
        Files.write(counter,Integer.toString(launch).getBytes(StandardCharsets.UTF_8));
        try {
            launcher=edt(()->{Constructor<?> ctor=SoloScapeLauncher.class.getDeclaredConstructor(Path.class);ctor.setAccessible(true);return ctor.newInstance(root);});
            waitFor(()->((JFrame)field("frame")).isActive(),30,"Launcher not active");Thread.sleep(600);
            if(launch==1){
                playRound("Start Character",0);
                log("launch 1: world played and verified");
                openUpdates();
                String installed=edt(()->labels(dialog("SoloScape updates")));
                require(installed.contains("Installed: release private-test-a"),"Wrong installed identity: "+installed);
                edt(()->{JDialog d=dialog("SoloScape updates");require(!button(d,"Download").isEnabled()&&!button(d,"Install and Restart").isEnabled()&&!button(d,"Cancel Download").isEnabled(),"Nothing may be actionable before a check");return null;});
                pressUntil(KeyEvent.VK_ENTER,()->first(dialog("SoloScape updates"),JTextArea.class).getText().contains("An installable package is attached"),"Mapped A did not check updates");
                require(edt(()->first(dialog("SoloScape updates"),JTextArea.class).getText().contains("PRIVATE TEST METADATA")),"Notes missing");
                shot("1-checked");
                closeUpdates();   // controller ancestry: B closes only the nested dialog, then Settings
                openUpdates();
                pressUntil(KeyEvent.VK_ENTER,()->first(dialog("SoloScape updates"),JTextArea.class).getText().contains("An installable package is attached"),"Mapped A did not recheck");
                focusButton("SoloScape updates","Download",KeyEvent.VK_RIGHT);
                pressUntil(KeyEvent.VK_ENTER,()->first(dialog("SoloScape updates"),JProgressBar.class).getValue()>40,"Download progress never advanced");
                shot("2-downloading");
                log("progress string while downloading: "+edt(()->first(dialog("SoloScape updates"),JProgressBar.class).getString()));
                focusButton("SoloScape updates","Cancel Download",KeyEvent.VK_LEFT);
                pressUntil(KeyEvent.VK_ENTER,()->first(dialog("SoloScape updates"),JTextArea.class).getText().toLowerCase().contains("cancelled"),"Cancel did not report");
                waitFor(()->button(dialog("SoloScape updates"),"Download").isEnabled(),20,"Download not offered again after cancel");
                shot("3-cancelled");
                Files.write(dir.resolve("cancelled.flag"),new byte[0]);
                focusButton("SoloScape updates","Download",KeyEvent.VK_LEFT);
                pressUntil(KeyEvent.VK_ENTER,()->first(dialog("SoloScape updates"),JProgressBar.class).getValue()>0||labels(dialog("SoloScape updates")).contains("Downloaded and verified"),"Second download did not start");
                waitFor(()->labels(dialog("SoloScape updates")).contains("Downloaded and verified: release private-test-b"),180,"Candidate never became ready");
                waitFor(()->button(dialog("SoloScape updates"),"Install and Restart").isEnabled(),10,"Install not offered");
                shot("4-ready");
                focusButton("SoloScape updates","Install and Restart",KeyEvent.VK_LEFT);
                log("launch 1: requesting install and restart");
                key(KeyEvent.VK_ENTER);   // the launcher closes its backend and exits 75; nothing below runs
                Thread.sleep(120_000);
                throw new IllegalStateException("Launcher did not exit for restart");
            } else if(launch>2){
                playRound("Continue",launch-1);   // after a rollback: the older version must still continue the same world
                log("launch "+launch+": continued");
                edt(()->{Method close=SoloScapeLauncher.class.getDeclaredMethod("close");close.setAccessible(true);close.invoke(launcher);return null;});
                long until=System.nanoTime()+120_000_000_000L;
                while(System.nanoTime()<until&&edt(()->((JFrame)field("frame")).isDisplayable()))Thread.sleep(100);
                require(!edt(()->((JFrame)field("frame")).isDisplayable()),"Launcher/backend did not close normally");
                Files.write(dir.resolve("passed"+launch),new byte[0]);
                System.exit(0);
            } else {
                waitFor(()->dialog("SoloScape updates")!=null,30,"Previous apply result was not shown");
                String message=edt(()->labels(dialog("SoloScape updates"))+first(dialog("SoloScape updates"),JOptionPane.class).getMessage());
                require(message.contains("Updated."),"Unexpected apply result: "+message);
                shot("5-applied");
                pressUntil(KeyEvent.VK_ENTER,()->dialog("SoloScape updates")==null,"Mapped A did not acknowledge the apply result");
                openUpdates();
                String installed=edt(()->labels(dialog("SoloScape updates")));
                require(installed.contains("Installed: release private-test-b"),"Wrong installed identity after update: "+installed);
                shot("6-installed-b");
                closeUpdates();
                playRound("Continue",1);
                log("launch 2: continued after update");
                edt(()->{Method close=SoloScapeLauncher.class.getDeclaredMethod("close");close.setAccessible(true);close.invoke(launcher);return null;});
                long until=System.nanoTime()+120_000_000_000L;
                while(System.nanoTime()<until&&edt(()->((JFrame)field("frame")).isDisplayable()))Thread.sleep(100);
                require(!edt(()->((JFrame)field("frame")).isDisplayable()),"Launcher/backend did not close normally");
                Files.write(dir.resolve("passed"+launch),new byte[0]);
                System.exit(0);
            }
        } catch(Throwable ex) {
            ex.printStackTrace();
            try{log("FAILED: "+ex);edt(()->{for(Window w:Window.getWindows())if(w instanceof JDialog)w.dispose();return null;});}catch(Exception ignored){}
            System.exit(2);
        }
    }
}
