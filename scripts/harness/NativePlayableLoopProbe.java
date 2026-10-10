import java.lang.reflect.Method;
import java.util.*;
import com.GameClient.ControllerTarget;
import net.runelite.client.input.controller.*;

/** Actual Lumbridge scene, native Walk/Take/stairs/banker/widget actions; disposable worlds only. */
final class NativePlayableLoopProbe {
    private static int step;
    private static long since, movedAt;
    private static int[] origin;
    private static int walks;
    private static boolean sent;
    static boolean tick(Map<String,Object> results) throws Exception {
        long now=System.currentTimeMillis();
        if(since==0){since=now;origin=tile();require(origin[2]==0,"Journey needs ground-floor spawn");ControllerEntry.enableServerCancel(true);}
        require(now-since<45000,"Gameplay stage timed out: "+step+" tile="+Arrays.toString(tile()));
        ControllerEntry.prepare();
        if(step==0){if(!sent)sent=ControllerUi.openTab(HomeTab.INVENTORY.ordinal());if(sent&&at(3211,3214,0))next();return false;}
        if(step==1){
            UiState.Widget pot=item(ControllerUi.snapshot(true),"Pot",false);
            if(pot!=null){results.put("existing_pot_reused",true);next();return false;}
            if(!sent){sent=interact("Pot","Take",3209,3214);}
            if(item(ControllerUi.snapshot(true),"Pot",false)!=null){results.put("actual_kitchen_pot_gathered",true);next();}return false;
        }
        if(step==2){if(at(3215,3216,0))next();return false;}
        if(step==3){if(at(3215,3224,0))next();return false;}
        if(step==4){if(at(3208,3227,0))next();return false;}
        if(step==5){
            if(!sent)sent=interact("Door","Open",3207,3227);
            if(now-since>1500)next();return false;
        }
        if(step==6){if(at(3206,3227,0))next();return false;}
        if(step==7){if(at(3205,3228,0))next();return false;}
        if(step==8||step==9){
            int floor=step==8?1:2;
            if(tile()[2]==floor){results.put("actual_castle_floor_"+floor,true);next();return false;}
            if(!sent)sent=interact("Staircase","Climb-up",3204,3229);return false;
        }
        if(step==10){if(at(3208,3219,2))next();return false;}
        if(step==11){
            UiState.Panel panel=ControllerUi.snapshot().panel;
            if(panel!=null&&panel.id==762){results.put("actual_banker_opened",true);next();return false;}
            if(!sent)sent=interact("Banker","Bank",-1,-1);return false;
        }
        if(step==12){
            UiState state=ControllerUi.snapshot();
            if(item(state,"Pot",true)!=null){next();return false;}
            if(!sent){UiState.Widget pot=item(state,"Pot",false);if(pot!=null)sent=invoke(pot,"Deposit-1");}return false;
        }
        if(step==13){
            if(!sent){UiState.Widget pot=item(ControllerUi.snapshot(),"Pot",true);if(pot!=null)sent=invoke(pot,"Withdraw-X");}
            EntryState prompt=ControllerEntry.snapshot();
            if(prompt!=null){require(prompt.type==7,"Withdraw-X did not open native amount");require(SoloScapeConnection.entryCancel(),"Fresh typed-cancel capability missing");
                require(ControllerEntry.edit(prompt,"9"),"Native amount edit failed");ControllerEntry.cancel(ControllerEntry.snapshot());results.put("real_withdraw_x_cancel_sent",true);next();}
            return false;
        }
        if(step==14){
            if(ControllerEntry.snapshot()!=null||now-since<1500)return false;
            UiState state=ControllerUi.snapshot();require(state.panel!=null&&state.panel.id==762,"Cancellation closed the bank");
            require(item(state,"Pot",true)!=null&&item(state,"Pot",false)==null,"Cancellation transferred an item");
            results.put("cancel_preserved_bank_and_items",true);next();return false;
        }
        if(step==15){
            if(!sent)sent=panelAction("Search");
            EntryState prompt=ControllerEntry.snapshot();if(prompt!=null){require(prompt.type==11,"Bank Search type missing");require(ControllerEntry.edit(prompt,"pot"),"Search edit failed");next();}return false;
        }
        if(step==16){
            if(now-since<1000)return false;EntryState prompt=ControllerEntry.snapshot();require(prompt!=null&&prompt.type==11,"Search prompt disappeared");
            require(item(ControllerUi.snapshot(),"Pot",true)!=null,"Native search lost matching item");ControllerEntry.cancel(prompt);next();return false;
        }
        if(step==17){
            if(ControllerEntry.snapshot()!=null||now-since<1000)return false;
            if(!sent)sent=panelAction("Search");
            if(sent&&now-since>2000){results.put("actual_bank_search_edit_cancel_toggle",true);next();}return false;
        }
        if(step==18){
            UiState state=ControllerUi.snapshot();
            if(item(state,"Pot",false)!=null){results.put("normal_withdraw_after_cancel",true);next();return false;}
            if(!sent){UiState.Widget pot=item(state,"Pot",true);if(pot!=null)sent=invoke(pot,"Withdraw-1");}return false;
        }
        if(step==19){if(!sent){ControllerUi.cancelWorld();sent=true;}if(!ControllerUi.hasModalPanel()&&now-since>1000)next();return false;}
        if(step==20){if(at(3205,3228,2))next();return false;}
        if(step==21||step==22){int floor=step==21?1:0;if(tile()[2]==floor){next();return false;}if(!sent)sent=interact("Staircase","Climb-down",3204,3229);return false;}
        if(step==23){if(at(3206,3227,0))next();return false;}
        if(step==24){if(!sent)sent=interact("Door","Open",3207,3227);if(now-since>1500)next();return false;}
        if(step==25){if(at(3208,3227,0))next();return false;}
        if(step==26){if(at(3215,3224,0))next();return false;}
        if(step==27){if(at(3215,3216,0))next();return false;}
        if(step==28){if(at(origin[0],origin[1],origin[2]))next();return false;}
        results.put("actual_lumbridge_bank_round_trip",true);results.put("native_walk_dispatches",walks);results.put("journey_final_tile",Arrays.toString(tile()));return true;
    }
    private static void next(){step++;since=System.currentTimeMillis();sent=false;movedAt=0;}
    private static int[] tile(){Player p=Class132.aPlayer_1907;return new int[]{(p.x>>9)+za_Sub2.regionTileX,(p.y>>9)+Class90.regionTileY,p.plane};}
    private static boolean at(int x,int y,int plane){
        int[] current=tile();require(current[2]==plane,"Unexpected floor at stage "+step);
        long now=System.currentTimeMillis();if(current[0]==x&&current[1]==y)return now-movedAt>850;
        if(!ControllerWorld.ready()||now-movedAt<850)return false;
        int dx=Integer.signum(x-current[0]),dy=Integer.signum(y-current[1]);double length=Math.hypot(dx,dy);
        if(ControllerWorld.walk(.4*dx/length,.4*dy/length)){walks++;movedAt=now;}return false;
    }
    @SuppressWarnings("unchecked") private static boolean interact(String name,String option,int x,int y)throws Exception{
        Method method=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);method.setAccessible(true);
        for(ControllerTarget target:(List<ControllerTarget>)method.invoke(null,true)){
            if(target.name.equalsIgnoreCase(name)&&target.option.equalsIgnoreCase(option)
                &&(x<0||target.x+target.baseX==x&&target.y+target.baseY==y))if(ControllerWorld.interact(target))return true;
        }return false;
    }
    private static UiState.Widget item(UiState state,String name,boolean bank){
        if(state.panel!=null&&state.panel.id==762){for(UiState.Pane pane:state.panel.panes)for(UiState.Widget widget:pane.widgets)
            if(widget.itemId>=0&&widget.quantity>0&&widget.name.equalsIgnoreCase(name)&&((widget.id>>>16)==762)==bank)return widget;
        }else if(!bank)for(UiState.Widget widget:state.inventory)if(widget.itemId>=0&&widget.quantity>0&&widget.name.equalsIgnoreCase(name))return widget;
        return null;
    }
    private static boolean invoke(UiState.Widget widget,String label){for(UiState.Action action:widget.actions)if(action.label.replace(" ","-").equalsIgnoreCase(label))return ControllerUi.invoke(widget,action);return false;}
    private static boolean panelAction(String label){UiState.Panel panel=ControllerUi.snapshot().panel;if(panel==null)return false;for(UiState.Pane pane:panel.panes)for(UiState.Widget widget:pane.widgets)if(invoke(widget,label))return true;return false;}
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
}
