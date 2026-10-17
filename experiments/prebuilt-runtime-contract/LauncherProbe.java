import java.lang.reflect.*;
import java.nio.file.*;
import java.util.concurrent.Callable;
import javax.swing.*;
import com.google.gson.*;

/** Original private Xvfb fixture: real launcher buttons and native owned backend, no physical input claim. */
public final class LauncherProbe {
    private static Object launcher;
    private static Class<?> type;
    private static Path output;
    private static Object field(String name) throws Exception { Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(launcher); }
    private static <T> T edt(Callable<T> action) throws Exception {
        final Object[] result=new Object[1]; final Throwable[] error=new Throwable[1];
        SwingUtilities.invokeAndWait(()->{try{result[0]=action.call();}catch(Throwable ex){error[0]=ex;}});
        if(error[0]!=null)throw new RuntimeException(error[0]);
        return (T)result[0];
    }
    private static void await(Callable<Boolean> condition,int seconds,String stage) throws Exception {
        long until=System.nanoTime()+seconds*1000000000L;
        while(System.nanoTime()<until){if(edt(condition))return;Thread.sleep(100);}
        throw new IllegalStateException(stage+": "+edt(()->((JLabel)field("status")).getText()));
    }
    public static void main(String[] args) throws Exception {
        output=Paths.get(args[1]); int port=Integer.parseInt(args[2]);JsonArray rounds=new JsonArray();
        boolean passed=false;
        try {
            type=Class.forName("net.runelite.client.soloscape.launcher.SoloScapeLauncher");
            Constructor<?> constructor=type.getDeclaredConstructor(Path.class);constructor.setAccessible(true);
            edt(()->{launcher=constructor.newInstance(Paths.get(args[0]));return null;});
            await(()->((JList<?>)field("list")).getModel().getSize()==1&&((Integer)field("port"))==port
                  &&((JButton)field("play")).isEnabled(),30,"Launcher did not load its fixture/settings");
            for(int i=0;i<2;i++){
                final String label=i==0?"Start Character":"Continue";
                await(()->((JButton)field("play")).isEnabled()&&((JButton)field("play")).getText().equals(label),30,label+" unavailable");
                long started=System.nanoTime();
                edt(()->{((JButton)field("play")).doClick();return null;});
                await(()->(Boolean)field("running"),20,"World worker did not start");
                await(()->!(Boolean)field("running")&&((JLabel)field("status")).getText().contains("saved and verified"),210,"Native session did not verify closure");
                JsonObject round=new JsonObject();round.addProperty("round",i==0?"new":"continue");
                round.addProperty("elapsedSeconds",(System.nanoTime()-started)/1000000000.0);
                round.addProperty("finalStatus",edt(()->((JLabel)field("status")).getText()));rounds.add(round);
                Path checkpoint=output.resolveSibling("round"+i+".json");
                Files.write(checkpoint,new Gson().toJson(round).getBytes("UTF-8"));
                Path ack=output.resolveSibling("round"+i+".ack");
                long deadline=System.nanoTime()+15000000000L;
                while(!Files.exists(ack)&&System.nanoTime()<deadline)Thread.sleep(50);
                if(!Files.exists(ack))throw new IllegalStateException("Coordinator did not verify stopped-world checkpoint");
            }
            passed=true;
        } finally {
            JsonObject report=new JsonObject();report.addProperty("passed",passed);report.add("rounds",rounds);
            Files.write(output,new GsonBuilder().setPrettyPrinting().create().toJson(report).getBytes("UTF-8"));
            if(launcher!=null){
                edt(()->{Method close=type.getDeclaredMethod("close");close.setAccessible(true);close.invoke(launcher);return null;});
                long until=System.nanoTime()+90000000000L;
                while(System.nanoTime()<until&&edt(()->((JFrame)field("frame")).isDisplayable()))Thread.sleep(100);
                if(edt(()->((JFrame)field("frame")).isDisplayable()))throw new IllegalStateException("Launcher/backend did not close normally");
            }
        }
        System.exit(0);
    }
}
