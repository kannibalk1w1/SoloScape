package net.runelite.client.soloscape.launcher;

import java.awt.*;
import java.awt.event.KeyEvent;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;
import javax.swing.*;

/**
 * Private acceptance of the launcher-driven Java-changing update and the user-triggered rollback, through the real
 * launcher, mapped controller input and the real backend. Launch 1 (release a): play a world, Check, Download (refused: the
 * release needs a local build), Update Source and Rebuild, cancel it mid-build, rebuild again, Install and Restart.
 * Launch 2 (the rebuilt release): acknowledge the result, Continue, Roll Back (confirmed). Launch 3 (release a again):
 * acknowledge the result, Continue. The coordinator verifies the stopped world after every round.
 */
public final class NativeManagedRebuildProbe {
    static Object launcher; static Path dir; static Robot robot; static int launch;
    static <T>T edt(Callable<T> call)throws Exception { if(SwingUtilities.isEventDispatchThread())return call.call();FutureTask<T> task=new FutureTask<>(call);SwingUtilities.invokeAndWait(task);return task.get(); }
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
    static String text() throws Exception { return edt(()->first(dialog("SoloScape updates"),JTextArea.class).getText()); }
    static String bar() throws Exception { return edt(()->first(dialog("SoloScape updates"),JProgressBar.class).getString()); }
    static boolean enabled(String name)throws Exception { return edt(()->button(dialog("SoloScape updates"),name).isEnabled()); }
    /** One mapped A on the named button while it holds focus; pressed again only if nothing happened for 4 s (a lost press). */
    static void activate(String name,Callable<Boolean> done,int seconds,String message)throws Exception {
        long end=System.currentTimeMillis()+seconds*1000L,lastPress=0;
        while(System.currentTimeMillis()<end){
            if(edt(done))return;
            boolean ready=edt(()->{JDialog d=dialog("SoloScape updates");JButton b=d==null?null:button(d,name);return b!=null&&b.isEnabled()&&focus()==b;});
            if(ready&&System.currentTimeMillis()-lastPress>4000){key(KeyEvent.VK_ENTER);lastPress=System.currentTimeMillis();}
            Thread.sleep(100);
        }
        throw new IllegalStateException(message);
    }
    static void acknowledgeResult(String expect)throws Exception {
        waitFor(()->dialog("SoloScape updates")!=null,30,"Previous apply result was not shown");
        String message=edt(()->labels(dialog("SoloScape updates"))+first(dialog("SoloScape updates"),JOptionPane.class).getMessage());
        require(message.contains(expect),"Unexpected apply result: "+message);
        shot("result");
        pressUntil(KeyEvent.VK_ENTER,()->dialog("SoloScape updates")==null,"Mapped A did not acknowledge the result");
    }
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]);dir=Paths.get(args[1]);robot=new Robot();System.setProperty("soloscape.launcher.steamKeyboard","true");
        Path counter=dir.resolve("launches");
        launch=(Files.exists(counter)?Integer.parseInt(new String(Files.readAllBytes(counter),StandardCharsets.UTF_8).trim()):0)+1;
        Files.write(counter,Integer.toString(launch).getBytes(StandardCharsets.UTF_8));
        try {
            launcher=edt(()->{Constructor<?> ctor=SoloScapeLauncher.class.getDeclaredConstructor(Path.class);ctor.setAccessible(true);return ctor.newInstance(root);});
            waitFor(()->((JFrame)field("frame")).isActive(),30,"Launcher not active");Thread.sleep(600);
            Files.write(dir.resolve("launch"+launch+".started"),new byte[0]);
            if(launch==1){
                playRound("Start Character",0);
                log("launch 1: world played and verified");
                openUpdates();
                require(edt(()->labels(dialog("SoloScape updates"))).contains("Installed: release private-test-a"),"Wrong installed identity");
                require(edt(()->labels(dialog("SoloScape updates"))).contains("Previous version: none"),"A first install has no previous version");
                require(!enabled("Roll Back")&&!enabled("Update Source and Rebuild"),"Roll back and rebuild must not be offered yet");
                require(text().contains("Roll Back is unavailable: There is no earlier version"),"No plain reason for the disabled Roll Back: "+text());
                pressUntil(KeyEvent.VK_ENTER,()->text().contains("An installable package is attached"),"Mapped A did not check updates");
                focusButton("SoloScape updates","Download",KeyEvent.VK_RIGHT);
                activate("Download",()->text().contains("needs a different build"),120,"Download was not refused with the rebuild message");
                waitFor(()->enabled("Update Source and Rebuild"),20,"Update Source and Rebuild not offered after the refusal");
                require(text().contains("choose Update Source and Rebuild"),"The refusal does not point at the button: "+text());
                shot("1-needs-rebuild");
                log("refusal: "+text().replace('\n',' ').substring(0,Math.min(300,text().length())));
                focusButton("SoloScape updates","Update Source and Rebuild",KeyEvent.VK_RIGHT);
                activate("Update Source and Rebuild",()->bar().contains("building"),900,"The rebuild never reached its build stage");
                shot("2-building");
                log("progress string while building: "+bar());
                require(edt(()->first(dialog("SoloScape updates"),JProgressBar.class).isIndeterminate()),"A build has no known total, so progress must be indeterminate");
                require(enabled("Cancel")&&!enabled("Update Source and Rebuild")&&!enabled("Install and Restart")&&!enabled("Roll Back"),"Only Cancel may be active during a rebuild");
                Files.write(dir.resolve("building.flag"),new byte[0]);
                focusButton("SoloScape updates","Cancel",KeyEvent.VK_LEFT);
                activate("Cancel",()->text().toLowerCase().contains("cancelled"),60,"Cancel did not report during the build");
                waitFor(()->enabled("Update Source and Rebuild"),30,"Rebuild not offered again after cancelling");
                shot("3-cancelled");
                Files.write(dir.resolve("cancelled.flag"),new byte[0]);
                focusButton("SoloScape updates","Update Source and Rebuild",KeyEvent.VK_LEFT);
                activate("Update Source and Rebuild",()->bar().length()>1,120,"The second rebuild did not start");
                waitFor(()->labels(dialog("SoloScape updates")).contains("Downloaded and verified: release private-test-j"),2400,"The rebuilt release never became ready");
                waitFor(()->enabled("Install and Restart"),10,"Install not offered");
                shot("4-ready");
                focusButton("SoloScape updates","Install and Restart",KeyEvent.VK_LEFT);
                log("launch 1: requesting install and restart");
                key(KeyEvent.VK_ENTER);
                Thread.sleep(120_000);
                throw new IllegalStateException("Launcher did not exit for restart");
            } else if(launch==2){
                acknowledgeResult("Updated.");
                openUpdates();
                require(edt(()->labels(dialog("SoloScape updates"))).contains("Installed: release private-test-j"),"Wrong installed identity after the Java-changing update");
                require(edt(()->labels(dialog("SoloScape updates"))).contains("Previous version: release private-test-a"),"Previous version not shown");
                require(enabled("Roll Back"),"Roll Back must be offered with a previous version and stopped worlds");
                shot("5-installed-j");
                closeUpdates();
                playRound("Continue",1);
                log("launch 2: continued after the Java-changing update");
                openUpdates();
                focusButton("SoloScape updates","Roll Back",KeyEvent.VK_RIGHT);
                pressUntil(KeyEvent.VK_ENTER,()->{for(Window w:Window.getWindows())if(w.isShowing()&&w instanceof JDialog&&"Roll back".equals(((JDialog)w).getTitle()))return true;return false;},"Roll Back did not ask for confirmation");
                String ask=edt(()->{for(Window w:Window.getWindows())if(w.isShowing()&&w instanceof JDialog&&"Roll back".equals(((JDialog)w).getTitle()))return first(w,JOptionPane.class).getMessage().toString();return "";});
                require(ask.contains("no save or backup is restored")&&ask.contains("private-test-a"),"Confirmation does not explain the rollback: "+ask);
                shot("6-confirm");
                log("confirmation: "+ask.replace('\n',' '));
                // B declines: nothing may change
                pressUntil(KeyEvent.VK_ESCAPE,()->{for(Window w:Window.getWindows())if(w.isShowing()&&w instanceof JDialog&&"Roll back".equals(((JDialog)w).getTitle()))return false;return true;},"B did not decline the confirmation");
                require(edt(()->dialog("SoloScape updates")!=null),"B declined the confirmation but also closed the Updates dialog");
                waitFor(()->enabled("Roll Back"),10,"Roll Back disappeared after declining");
                pressUntil(KeyEvent.VK_ENTER,()->{for(Window w:Window.getWindows())if(w.isShowing()&&w instanceof JDialog&&"Roll back".equals(((JDialog)w).getTitle()))return true;return false;},"Roll Back did not ask again");
                final Window confirm=edt(()->{for(Window w:Window.getWindows())if(w.isShowing()&&w instanceof JDialog&&"Roll back".equals(((JDialog)w).getTitle()))return w;return null;});
                require(confirm!=null,"The confirmation vanished");
                require(edt(()->focus()==button(confirm,"Cancel")),"The confirmation must open on Cancel, the safe choice");
                for(int i=0;i<10&&!edt(()->focus()==button(confirm,"Roll Back"));i++)key(KeyEvent.VK_LEFT);   // move to Roll Back; retry a lost press
                require(edt(()->focus()==button(confirm,"Roll Back")),"Mapped navigation did not reach the Roll Back choice");
                log("launch 2: confirming roll back");
                key(KeyEvent.VK_ENTER);  // the launcher closes its backend and exits 75; nothing below runs
                Thread.sleep(120_000);
                throw new IllegalStateException("Launcher did not exit for the rollback restart");
            } else {
                acknowledgeResult("Rolled back to release private-test-a");
                openUpdates();
                require(edt(()->labels(dialog("SoloScape updates"))).contains("Installed: release private-test-a"),"Wrong installed identity after the rollback");
                require(edt(()->labels(dialog("SoloScape updates"))).contains("Previous version: release private-test-j"),"The version rolled back from should be the new previous version");
                shot("7-rolled-back");
                closeUpdates();
                playRound("Continue",2);
                log("launch 3: continued after the rollback");
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
