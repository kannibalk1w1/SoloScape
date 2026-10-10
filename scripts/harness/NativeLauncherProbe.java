package net.runelite.client.soloscape.launcher;

import java.awt.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.concurrent.*;
import java.util.function.*;
import javax.swing.*;
import net.runelite.client.input.controller.*;

/** Actual Swing launcher/entry/backend on a private fixture root; no SDL/hardware claim. */
public final class NativeLauncherProbe
{
    static Object launcher;static Path root;
    static <T>T edt(Callable<T> call)throws Exception{FutureTask<T> task=new FutureTask<>(call);SwingUtilities.invokeAndWait(task);return task.get();}
    static Object field(Object object,String name)throws Exception{Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);}
    static void invoke(String name)throws Exception{Method m=SoloScapeLauncher.class.getDeclaredMethod(name);m.setAccessible(true);m.invoke(launcher);}
    static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    static void waitFor(Callable<Boolean> predicate,String message)throws Exception{long end=System.currentTimeMillis()+15000;while(!edt(predicate)){require(System.currentTimeMillis()<end,message);Thread.sleep(50);}}
    static JTextField text(Component root,String name){if(root instanceof JTextField&&name.equals(root.getName()))return (JTextField)root;if(root instanceof Container)for(Component child:((Container)root).getComponents()){JTextField found=text(child,name);if(found!=null)return found;}return null;}
    static JButton button(Component root,String name){if(root instanceof JButton&&name.equals(((JButton)root).getText()))return (JButton)root;if(root instanceof Container)for(Component child:((Container)root).getComponents()){JButton found=button(child,name);if(found!=null)return found;}return null;}
    static void press(LauncherKeyboard keyboard,int mask){GamepadState pad=new GamepadState();keyboard.update(pad,System.nanoTime());pad.buttonsHeld=pad.buttonsPressed=mask;keyboard.update(pad,System.nanoTime());}
    static LauncherKeyboard open()throws Exception{
        SwingUtilities.invokeLater(()->{try{invoke("newCharacter");}catch(Exception e){throw new RuntimeException(e);}});
        waitFor(()->field(launcher,"keyboard")!=null&&((LauncherKeyboard)field(launcher,"keyboard")).owner.isShowing(),"Character dialog did not open");
        LauncherKeyboard keyboard=(LauncherKeyboard)edt(()->field(launcher,"keyboard"));
        waitFor(()->keyboard.active(),"First name field did not adopt keyboard");return keyboard;
    }
    public static void main(String[] args)throws Exception{
        root=Paths.get(args[0]);
        try{
            launcher=edt(()->{Constructor<?> ctor=SoloScapeLauncher.class.getDeclaredConstructor(Path.class);ctor.setAccessible(true);return ctor.newInstance(root);});
            LauncherKeyboard keyboard=open();JTextField label=edt(()->text(keyboard.owner,"Character label"));JTextField account=edt(()->text(keyboard.owner,"Account name"));
            edt(()->{require(label.getText().isEmpty(),"Label changed before entry probe");keyboard.deactivate();keyboard.activate(label);GamepadState held=new GamepadState();held.buttonsHeld=held.buttonsPressed=1;keyboard.update(held,System.nanoTime());require(label.getText().isEmpty(),"Opening held A typed a key");press(keyboard,1);require(label.getText().equals("a"),"Controller did not type label");press(keyboard,8);return null;});
            waitFor(()->field(keyboard,"field")==account,"Y did not move to account field");
            edt(()->{press(keyboard,1);require(account.getText().equals("a"),"Controller did not type account");account.setText("bad-name");require(account.getText().equals("a"),"Invalid pasted account changed field");press(keyboard,2);require(keyboard.owner.isShowing()&&!keyboard.active(),"B closed form instead of keyboard");require(account.getText().equals("a"),"B lost entered name");keyboard.activate(account);return null;});
            Thread.sleep(200);
            Rectangle screen=edt(()->new Rectangle(keyboard.owner.getLocationOnScreen(),keyboard.owner.getSize()));javax.imageio.ImageIO.write(new Robot().createScreenCapture(screen),"png",root.resolve("launcher-name-entry.png").toFile());
            edt(()->{press(keyboard,8);require(!keyboard.active(),"Y did not finish name entry");button(keyboard.owner,"Create character").doClick();return null;});
            waitFor(()->!keyboard.owner.isShowing(),"Valid create did not close form");
            waitFor(()->((DefaultListModel<?>)field(launcher,"characters")).size()==1,"Backend did not create exactly one private profile");
            LauncherKeyboard second=open();JTextField secondLabel=edt(()->text(second.owner,"Character label"));JTextField secondAccount=edt(()->text(second.owner,"Account name"));
            edt(()->{secondLabel.setText("\u00a0");secondAccount.setText("b");second.deactivate();button(second.owner,"Create character").doClick();return null;});
            waitFor(()->button(second.owner,"Create character").isEnabled(),"Backend validation did not re-enable form");
            edt(()->{require(second.owner.isShowing()&&secondLabel.getText().equals("\u00a0")&&secondAccount.getText().equals("b"),"Backend error discarded the form");require(((DefaultListModel<?>)field(launcher,"characters")).size()==1,"Rejected create added a character");second.owner.dispose();return null;});
            java.util.List<Boolean> requests=new java.util.ArrayList<>();
            LauncherKeyboard system=edt(()->{
                JDialog dialog=new JDialog((JFrame)field(launcher,"frame"),"Private Steam ownership probe",false);
                LauncherKeyboard entry=new LauncherKeyboard(true,requests::add);entry.owner=dialog;
                JTextField first=new JTextField(),last=new JTextField();first.setName("Steam label");last.setName("Steam account");JButton done=new JButton("Done");
                entry.register(first,EntryState.LAUNCHER_LABEL,()->{last.requestFocusInWindow();entry.activate(last);});entry.register(last,EntryState.LAUNCHER_ACCOUNT,done::requestFocusInWindow);
                JPanel pane=new JPanel(new GridLayout(0,1));pane.add(first);pane.add(last);pane.add(entry);pane.add(done);dialog.add(pane);dialog.setSize(840,350);dialog.setVisible(true);first.requestFocusInWindow();entry.activate(first);return entry;
            });
            waitFor(()->system.active()&&field(system,"field")==text(system.owner,"Steam label"),"Steam field did not own input");
            edt(()->{JTextField first=text(system.owner,"Steam label");first.setText("steam_label");press(system,1);press(system,2);press(system,8);require(first.getText().equals("steam_label")&&system.active(),"SDL leaked into Steam entry");first.postActionEvent();return null;});
            waitFor(()->system.active()&&field(system,"field")==text(system.owner,"Steam account"),"Steam Enter did not advance field");
            edt(()->{JTextField last=text(system.owner,"Steam account");last.setText("steam_name");press(system,1);require(last.getText().equals("steam_name"),"Steam account duplicated controller key");last.postActionEvent();return null;});
            waitFor(()->!system.active(),"Steam Enter did not finish entry");
            edt(()->{require(requests.equals(java.util.Arrays.asList(true,false,true,false)),"Unexpected Steam visibility requests: "+requests);system.owner.dispose();return null;});
            edt(()->{invoke("close");return null;});
            waitFor(()->!((JFrame)field(launcher,"frame")).isDisplayable(),"Launcher did not close gracefully");
            System.out.println("Native launcher adapter/backend: held-A guard, controller name entry, account filter, B preserves form, Y advances, private creation and inline backend rejection and exclusive Steam-mode focus/Enter passed. No SDL/hardware acceptance.");System.exit(0);
        }catch(Exception failure){failure.printStackTrace();try{edt(()->{if(launcher!=null){LauncherKeyboard k=(LauncherKeyboard)field(launcher,"keyboard");if(k!=null)k.owner.dispose();invoke("close");}return null;});}catch(Exception ignored){}System.exit(2);}
    }
}
