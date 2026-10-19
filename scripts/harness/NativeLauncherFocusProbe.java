package net.runelite.client.soloscape.launcher;

import java.awt.*;
import java.awt.event.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.concurrent.*;
import javax.swing.*;

/** Real Swing focus lifecycle; private backend, Steam-mapped keys, no hardware claim. */
public final class NativeLauncherFocusProbe {
    static Object launcher; static Robot robot;
    static <T>T edt(Callable<T> call)throws Exception { FutureTask<T> task=new FutureTask<>(call);SwingUtilities.invokeAndWait(task);return task.get(); }
    static Object field(String name)throws Exception { Field f=SoloScapeLauncher.class.getDeclaredField(name);f.setAccessible(true);return f.get(launcher); }
    static void require(boolean value,String message) { if(!value)throw new IllegalStateException(message); }
    static void waitFor(Callable<Boolean> test,String message)throws Exception { long end=System.currentTimeMillis()+6000;while(!edt(test)){require(System.currentTimeMillis()<end,message);Thread.sleep(40);} }
    static JDialog dialog(String title) { for(Window w:Window.getWindows())if(w instanceof JDialog&&w.isShowing()&&title.equals(((JDialog)w).getTitle()))return (JDialog)w;return null; }
    static JButton button(Component root,String title) { if(root instanceof JButton&&title.equals(((JButton)root).getText()))return (JButton)root;if(root instanceof Container)for(Component c:((Container)root).getComponents()){JButton found=button(c,title);if(found!=null)return found;}return null; }
    static void key(int code)throws Exception { robot.keyPress(code);Thread.sleep(100);robot.keyRelease(code);Thread.sleep(250); }
    static void open(String control,String title)throws Exception {
        edt(()->{((JButton)field(control)).requestFocusInWindow();return null;});
        waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()==field(control),"Missing initial "+control+" focus");
        key(KeyEvent.VK_ENTER);waitFor(()->dialog(title)!=null,"Mapped A did not open "+title);
    }
    static void returned(String control)throws Exception {
        waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getActiveWindow()==field("frame")&&KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()==field(control),"Dialog did not restore "+control+" focus");
        Thread.sleep(150); // Allow the neutral ownership guard to rearm before a fresh press.
        key(KeyEvent.VK_RIGHT);
        waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()!=field(control),"Navigation stopped after dialog exit");
    }
    public static void main(String[] args)throws Exception {
        System.setProperty("soloscape.launcher.steamKeyboard","true");robot=new Robot();
        try {
            launcher=edt(()->{Constructor<?> c=SoloScapeLauncher.class.getDeclaredConstructor(Path.class);c.setAccessible(true);return c.newInstance(Paths.get(args[0]));});
            waitFor(()->((JFrame)field("frame")).isActive(),"Launcher not active");Thread.sleep(500);
            for(String exit:new String[]{"OK","Cancel","title bar","B"}) {
                open("settings","Launcher Settings");
                if(exit.equals("B"))key(KeyEvent.VK_ESCAPE);
                else edt(()->{JDialog d=dialog("Launcher Settings");if(exit.equals("title bar"))d.dispatchEvent(new WindowEvent(d,WindowEvent.WINDOW_CLOSING));else button(d,exit).doClick();return null;});
                returned("settings");
            }
            open("create","New Character");
            edt(()->{button(dialog("New Character"),"Cancel").doClick();return null;});returned("create");
            open("create","New Character");
            edt(()->{JDialog d=dialog("New Character");for(Component c:((JPanel)d.getContentPane().getComponent(0)).getComponents())if(c instanceof JTextField)((JTextField)c).setText("focus");button(d,"Create character").doClick();return null;});
            waitFor(()->dialog("New Character")==null,"Create did not finish");returned("create");
            // Reproduce an active launcher whose child focus was cleared by the window manager.
            edt(()->{KeyboardFocusManager.getCurrentKeyboardFocusManager().clearGlobalFocusOwner();return null;});
            Thread.sleep(150); // Focus clearing is asynchronous; let its queued event finish.
            waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()!=null,"Active launcher never recovered missing component focus");
            Thread.sleep(150); // Neutral input rearms after ownership changes.
            key(KeyEvent.VK_RIGHT);
            waitFor(()->KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner() instanceof JButton,"Mapped navigation did not resume after missing focus");
            // A delayed dialog-close event must not pull focus back from another application window.
            JFrame other=edt(()->{JFrame w=new JFrame("Private unrelated window");w.add(new JTextField("Keep focus"));w.setSize(300,150);w.setVisible(true);return w;});
            waitFor(other::isActive,"Unrelated window not active");
            edt(()->{Method m=SoloScapeLauncher.class.getDeclaredMethod("restoreDialogFocus",Window.class,Component.class);m.setAccessible(true);m.invoke(launcher,field("frame"),field("list"));return null;});Thread.sleep(200);
            require(edt(other::isActive),"Launcher stole focus from unrelated window");edt(()->{other.dispose();return null;});
            System.out.println("Launcher focus: Settings OK/Cancel/title-bar/B, character cancel/create, missing focus recovery and unrelated-window guard passed. No Gaming Mode/hardware acceptance.");
            edt(()->{Method m=SoloScapeLauncher.class.getDeclaredMethod("close");m.setAccessible(true);m.invoke(launcher);return null;});
            waitFor(()->!((JFrame)field("frame")).isDisplayable(),"Launcher did not close");System.exit(0);
        }catch(Exception failure){failure.printStackTrace();System.exit(2);}
    }
}
