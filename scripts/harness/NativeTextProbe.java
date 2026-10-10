import java.awt.event.KeyEvent;
import java.lang.reflect.*;
import java.util.*;
import com.GameClient;
import net.runelite.api.events.ChatMessage;
import net.runelite.client.RuneLite;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.eventbus.*;
import net.runelite.client.input.KeyManager;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.*;

/** Real native CS2/widget/key pipeline fixture, with fake Steam visibility only. Never physical input acceptance. */
public final class NativeTextProbe {
    private static int stage;private static long stageAt;
    private static SoloScapeControllerPlugin plugin;private static SystemEntryControls original,owned;
    private static boolean priorActive,priorFailed;private static String priorMode;private static Object priorGamepad;
    private static net.runelite.client.input.KeyListener keys;
    private static final List<String> requests=new ArrayList<>(),messages=new ArrayList<>();
    private static final String CHAT="solo_keyboard_probe",CANCEL="solo_cancel_probe";
    private static String initialTile;
    private static final Recorder recorder=new Recorder();
    public static final class Recorder {@Subscribe public void chat(ChatMessage event){messages.add(event.getMessage());}}
    private static Field field(String name)throws Exception{Field field=SoloScapeControllerPlugin.class.getDeclaredField(name);field.setAccessible(true);return field;}
    private static void require(boolean ok,String reason){if(!ok)throw new IllegalStateException(reason);}
    private static void script(int id,String prompt){Class348_Sub36 event=new Class348_Sub36();event.anObjectArray6987=prompt==null?new Object[]{id}:new Object[]{id,prompt};Class66.method705(event);}
    // An active plugin already receives ClientTick from the event bus; tick manually only when it was stopped.
    private static void poll(){if(!priorActive)plugin.onClientTick(new net.runelite.api.events.ClientTick());}
    private static void key(int id,int code,char character){Class346_Sub1 input=(Class346_Sub1)Class182.aClass346_2449;KeyEvent event=new KeyEvent(Class305.aCanvas3869,id,System.currentTimeMillis(),0,code,character);
        if(id==KeyEvent.KEY_PRESSED)input.keyPressed(event);else if(id==KeyEvent.KEY_TYPED)input.keyTyped(event);else input.keyReleased(event);}
    private static String retainedChat(){for(String value:Class258_Sub2.aStringArray8532)if(value!=null&&value.contains(CANCEL))return value;return null;}
    private static void typed(String value){Class346_Sub1 input=(Class346_Sub1)Class182.aClass346_2449;for(char c:value.toCharArray())input.keyTyped(new KeyEvent(Class305.aCanvas3869,KeyEvent.KEY_TYPED,System.currentTimeMillis(),0,KeyEvent.VK_UNDEFINED,c));}
    private static String tile(){return Class132.aPlayer_1907.x+","+Class132.aPlayer_1907.y+","+Class132.aPlayer_1907.plane;}
    private static void next(){stage++;stageAt=System.currentTimeMillis();}
    public static boolean tick(SoloScapeControllerPlugin managed,Map<String,Object> results)throws Exception {
        ConfigManager config=RuneLite.getInjector().getInstance(ConfigManager.class);
        if(plugin==null){
            plugin=managed;original=(SystemEntryControls)field("systemEntry").get(plugin);priorActive=field("active").getBoolean(plugin);priorFailed=field("failed").getBoolean(plugin);priorGamepad=field("gamepad").get(plugin);priorMode=config.getConfiguration("soloscapecontroller","keyboardMode");
            owned=new SystemEntryControls((open,numeric)->requests.add(open+":"+numeric));field("systemEntry").set(plugin,owned);field("active").setBoolean(plugin,true);
            keys=(net.runelite.client.input.KeyListener)field("textKeys").get(plugin);RuneLite.getInjector().getInstance(KeyManager.class).registerKeyListener(keys);
            RuneLite.getInjector().getInstance(EventBus.class).register(recorder);config.setConfiguration("soloscapecontroller","keyboardMode","STEAM");initialTile=tile();
            stageAt=System.currentTimeMillis();return false;
        }
        if(stage==0){
            for(int id:new int[]{108,109,110,112,1564,101})if(Class328.method2609(-122,id)==null){require(System.currentTimeMillis()-stageAt<15000,"Native CS2 fixture script unavailable: "+id);return false;}
            script(108,"Private native amount fixture");next();return false;
        }
        poll();EntryState current=ControllerEntry.snapshot();
        if(stage==1||stage==3||stage==5){
            int type=stage==1?7:stage==3?8:9;String value=type==7?"42":type==8?"Alpha":"Search text";
            if(current==null&&System.currentTimeMillis()-stageAt<15000)return false;
            if(current==null){
                List<String> debug=new ArrayList<>();Class46[] widgets=Class348_Sub40_Sub33.aClass46ArrayArray9427[752];
                if(widgets!=null)for(Class46 widget:widgets)if(widget!=null)debug.add((widget.anInt830&65535)+" parent="+widget.anInt834+" hidden="+widget.aBoolean813+" height="+widget.anInt750+" type="+widget.anInt774+" text="+widget.aString792);
                Field seen=ControllerUi.class.getDeclaredField("visible");seen.setAccessible(true);debug.add("seenKeys="+((Map<?,?>)seen.get(null)).keySet());
                Object promptSeen=((Map<?,?>)seen.get(null)).get(((long)(752<<16|4)<<32)|0xffffffffL);
                if(promptSeen!=null){Field when=promptSeen.getClass().getDeclaredField("time");when.setAccessible(true);debug.add("ageNs="+(System.nanoTime()-when.getLong(promptSeen)));}
                Class46 prompt=widgets[4];Method vis=ControllerUi.class.getDeclaredMethod("isVisible",Class46.class);vis.setAccessible(true);debug.add("visible="+vis.invoke(null,prompt)+" identity="+(Class348_Sub22.method2957(prompt.anInt704,(byte)-54,prompt.anInt830)==prompt)+" child="+prompt.anInt704);
                for(Class348_Sub41 attached=(Class348_Sub41)Class125.aClass356_4915.method3484(0);attached!=null;attached=(Class348_Sub41)Class125.aClass356_4915.method3482(0))if(attached.anInt7050==752)debug.add("attachment="+attached.key);
                results.put("native_prompt_diagnostic",debug);
            }
            require(current!=null&&current.type==type,"Native fixture prompt type missing at "+stage+" nativeType="+Isaac.anIntArray1303[5]+" prompt="+(ControllerUi.entryPrompt()!=null)+" state="+Class240.anInt4674);
            require(owned.active()&&owned.sameSession(current),"Native prompt did not adopt exclusive ownership");
            require(ControllerEntry.edit(current,value),"Native edit rejected fixture value");
            require(ControllerEntry.snapshot().value.equals(value),"Native CS2 edit did not update value");
            results.put("native_text_type_"+type,true);ControllerEntry.cancel(ControllerEntry.snapshot());next();return false;
        }
        if(stage==2||stage==4){if((current!=null||owned.active())&&System.currentTimeMillis()-stageAt<5000)return false;require(current==null&&!owned.active(),"Native cancellation did not release ownership: nativeType="+Isaac.anIntArray1303[5]+" current="+(current!=null)+" owned="+owned.active());script(stage==2?109:110,stage==2?"Private native name fixture":"Private native string fixture");next();return false;}
        if(stage==6){
            require(current==null&&!owned.active(),"String fixture cancellation failed");
            owned.beginManual(true,true);typed(CHAT);next();return false;
        }
        if(stage==7){
            require(owned.manual(),"Chat typing lost manual ownership");
            Method action=SoloScapeControllerPlugin.class.getDeclaredMethod("textEntryAction",long.class,int.class);action.setAccessible(true);action.invoke(plugin,owned.revision(),1);next();return false;
        }
        if(stage==8){
            if(!messages.contains(CHAT)){require(System.currentTimeMillis()-stageAt<10000,"Native Enter did not submit public chat");return false;}
            require(!owned.active(),"Manual chat Done did not release ownership");results.put("native_chat_enter_submission",true);
            owned.beginManual(true,true);typed(CANCEL);next();return false;
        }
        if(stage==9){
            Method action=SoloScapeControllerPlugin.class.getDeclaredMethod("textEntryAction",long.class,int.class);action.setAccessible(true);action.invoke(plugin,owned.revision(),2);next();return false;
        }
        if(stage==10){
            require(!owned.active(),"Manual chat Cancel did not release ownership");require(!messages.contains(CANCEL),"Native Escape submitted cancelled chat");results.put("native_chat_escape_no_submission",true);
            String retained=retainedChat();
            results.put("native_chat_escape_retains_text",retained!=null);
            require(initialTile.equals(tile()),"Native text fixture moved the player");results.put("native_text_visibility_requests",new ArrayList<>(requests));
            results.put("native_text_probe_scope","Real CS2 amount/name/string fixture and native chat key pipeline; Steam visibility injected, no physical SDL/Gaming Mode proof.");
            // Never leave private probe text for a later native Enter: erase it with ordinary native Backspace input.
            if(retained!=null)for(int i=0;i<retained.length();i++){key(KeyEvent.KEY_PRESSED,KeyEvent.VK_BACK_SPACE,'\b');key(KeyEvent.KEY_TYPED,KeyEvent.VK_UNDEFINED,'\b');key(KeyEvent.KEY_RELEASED,KeyEvent.VK_BACK_SPACE,'\b');}
            next();return false;
        }
        if(stage==11){
            // Settle: native key queues drain on later client cycles, not synchronously.
            if(retainedChat()!=null){require(System.currentTimeMillis()-stageAt<5000,"Native Backspace did not clear retained probe chat");return false;}
            require(!owned.active()&&!messages.contains(CANCEL),"Probe chat cleanup changed ownership or submitted text");
            results.put("native_chat_probe_text_cleared",true);
            cleanup();return true;
        }
        throw new IllegalStateException("Unknown text probe stage "+stage);
    }
    public static void cleanup()throws Exception {
        if(plugin==null)return;owned.reset();RuneLite.getInjector().getInstance(EventBus.class).unregister(recorder);
        if(!priorActive)RuneLite.getInjector().getInstance(KeyManager.class).unregisterKeyListener(keys);
        if(!priorActive){
            // Close exactly the SDL provider this probe's manual ticks created; never one the running plugin owns.
            Object created=field("gamepad").get(plugin);
            if(created!=null&&created!=priorGamepad){try{((SdlGamepad)created).close();}catch(RuntimeException|LinkageError ignored){}}
            field("gamepad").set(plugin,priorGamepad);field("failed").setBoolean(plugin,priorFailed);
        }
        field("systemEntry").set(plugin,original);field("active").setBoolean(plugin,priorActive);field("localTextEntry").setBoolean(plugin,false);field("steamTextMode").setBoolean(plugin,false);
        ConfigManager config=RuneLite.getInjector().getInstance(ConfigManager.class);if(priorMode==null)config.unsetConfiguration("soloscapecontroller","keyboardMode");else config.setConfiguration("soloscapecontroller","keyboardMode",priorMode);
    }
}
