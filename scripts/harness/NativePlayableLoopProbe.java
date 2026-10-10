import java.lang.reflect.Method;
import java.util.*;
import com.GameClient.ControllerTarget;
import net.runelite.client.input.controller.*;

/** Actual Lumbridge scene, native Walk/Take/stairs/banker/widget actions; disposable worlds only. */
final class NativePlayableLoopProbe {
    private static int step=40;
    private static long since, movedAt, started;
    static String progress(){return "stage="+step+" tile="+(origin==null?"unstarted":Class132.aPlayer_1907==null?"logged out":Arrays.toString(tile()));}
    private static int[] origin;
    private static int walks;
    private static boolean sent;
    private static String probeNonce;
    private static Map<String,Object> observations;
    static boolean tick(Map<String,Object> results) throws Exception {
        long now=System.currentTimeMillis();observations=results;
        if(since==0){since=started=now;origin=tile();require(origin[2]==0,"Journey needs ground-floor spawn");ControllerEntry.enableServerCancel(true);}
        results.put("gameplay_stage",step);results.put("gameplay_tile",Arrays.toString(tile()));
        require(now-since<60000,"Gameplay stage timed out: "+step+" tile="+Arrays.toString(tile()));
        ControllerEntry.prepare();
        if(step==40){if(!sent)sent=ControllerUi.openInventory();if(sent&&findItem(ControllerUi.snapshot(true),1931)!=null)next();return false;}
        if(step==41){UiState.Widget pot=findItem(ControllerUi.snapshot(true),1931);if(pot!=null&&invoke(pot,"Use"))next();return false;}
        if(step==42){require(r.aBoolean9722&&ControllerSelection.valid(),"Native item source selection missing");ControllerUi.cancelSelection();require(!r.aBoolean9722,"Native source cancel failed");results.put("native_item_source_cancel",true);next();return false;}
        if(step==43){UiState.Widget sword=findItem(ControllerUi.snapshot(true),1277);if(sword!=null&&invoke(sword,"Wield"))next();return false;}
        if(step==44){
            if(!sent)sent=ControllerUi.openTab(HomeTab.EQUIPMENT.ordinal());
            UiState.Widget sword=findItem(ControllerUi.snapshot(),1277);if(sent&&sword!=null&&(sword.id>>>16)==387&&invoke(sword,"Remove"))next();return false;
        }
        if(step==45){
            if(!sent)sent=ControllerUi.openInventory();
            if(sent&&findItem(ControllerUi.snapshot(true),1277)!=null&&now-since>1500){results.put("native_equipment_wield_remove",true);next();step=0;}return false;
        }
        if(step==0){if(!sent)sent=ControllerUi.openInventory();if(sent&&at(3211,3214,0))next();return false;}
        if(step==1){
            UiState inventory=ControllerUi.snapshot(true);
            List<String> names=new ArrayList<>();for(UiState.Widget widget:inventory.inventory)if(widget!=null)names.add(widget.itemId+":"+widget.name);results.put("native_inventory_names",names);
            UiState.Widget pot=item(inventory,"Pot",false);
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
                String pending=pendingEntry();if(pending==null)return false;require(pending.equals("int"),"Server did not suspend for Withdraw-X: "+pending);
                results.put("server_pending_before_cancel",pending);
                java.lang.reflect.Field enabled=ControllerEntry.class.getDeclaredField("serverCancel");enabled.setAccessible(true);require(enabled.getBoolean(null),"Server cancellation preference disabled");
                require(ControllerEntry.edit(prompt,"9"),"Native amount edit failed");ControllerEntry.cancel(ControllerEntry.snapshot());results.put("client_withdraw_x_cancel_issued",true);next();}
            return false;
        }
        if(step==14){
            if(ControllerEntry.snapshot()!=null||now-since<1500)return false;
            UiState state=ControllerUi.snapshot();require(state.panel!=null&&state.panel.id==762,"Cancellation closed the bank");
            require(item(state,"Pot",true)!=null&&item(state,"Pot",false)==null,"Cancellation transferred an item");
            String pending=pendingEntry();if(pending==null)return false;require(pending.equals("none"),"Server suspension survived Cancel: "+pending);results.put("server_pending_after_cancel",pending);
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
            if(sent&&now-since>2000){require(Isaac.anIntArray1303[190]==0,"Search toggle left native search armed");results.put("actual_bank_search_edit_cancel_toggle",true);next();}return false;
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
        results.put("gameplay_round_trip_seconds",(now-started)/1000.0);results.put("actual_lumbridge_bank_round_trip",true);results.put("native_walk_dispatches",walks);results.put("journey_final_tile",Arrays.toString(tile()));return true;
    }
    private static void next(){step++;since=System.currentTimeMillis();sent=false;movedAt=0;probeNonce=null;}
    private static int[] tile(){Player p=Class132.aPlayer_1907;return new int[]{(p.x>>9)+za_Sub2.regionTileX,(p.y>>9)+Class90.regionTileY,p.plane};}
    private static boolean at(int x,int y,int plane){
        int[] current=tile();require(current[2]==plane,"Unexpected floor at stage "+step);
        long now=System.currentTimeMillis();if(current[0]==x&&current[1]==y)return now-movedAt>850;
        if(!ControllerWorld.ready()||now-movedAt<850)return false;
        int[] delta=nextStep(x,y);if(delta==null)return false;
        double length=Math.hypot(delta[0],delta[1]);
        if(ControllerWorld.walk((delta[2]==1?.4:delta[2]==2?.7:1)*delta[0]/length,(delta[2]==1?.4:delta[2]==2?.7:1)*delta[1]/length)){walks++;movedAt=now;}return false;
    }
    /** Probe navigation around scene clutter, using exactly the adapter's native collision masks. */
    private static int[] nextStep(int worldX,int worldY){
        Player player=Class132.aPlayer_1907;Class361 map=Class348_Sub45.aClass361Array7108[player.plane];
        int[][] flags=map.anIntArrayArray4438;int size=flags.length;
        int sx=(player.x>>9)-map.anInt4453,sy=(player.y>>9)-map.anInt4441;
        int gx=worldX-za_Sub2.regionTileX-map.anInt4453,gy=worldY-Class90.regionTileY-map.anInt4441;
        if(gx<0||gy<0||gx>=size||gy>=flags[gx].length)return null;
        int[][] parentX=new int[size][size],parentY=new int[size][size];boolean[][] seen=new boolean[size][size];
        ArrayDeque<int[]> todo=new ArrayDeque<>();todo.add(new int[]{sx,sy});seen[sx][sy]=true;
        while(!todo.isEmpty()){
            int[] tile=todo.removeFirst();if(tile[0]==gx&&tile[1]==gy){
                ArrayDeque<int[]> path=new ArrayDeque<>();int px=gx,py=gy;
                while(px!=sx||py!=sy){path.addFirst(new int[]{px,py});int parent=parentX[px][py];py=parentY[px][py];px=parent;}
                int dx=path.peekFirst()[0]-sx,dy=path.peekFirst()[1]-sy,count=0;px=sx;py=sy;
                for(int[] point:path){if(count==3||point[0]-px!=dx||point[1]-py!=dy)break;count++;px=point[0];py=point[1];}
                return new int[]{dx,dy,count};
            }
            for(int dx=-1;dx<=1;dx++)for(int dy=-1;dy<=1;dy++){
                int nx=tile[0]+dx,ny=tile[1]+dy;
                if(dx==0&&dy==0||nx<0||ny<0||nx>=size||ny>=flags[nx].length||seen[nx][ny]
                    ||Math.abs(nx-sx)>32||Math.abs(ny-sy)>32||!WorldInput.canStep(flags,tile[0],tile[1],dx,dy))continue;
                seen[nx][ny]=true;parentX[nx][ny]=tile[0];parentY[nx][ny]=tile[1];todo.addLast(new int[]{nx,ny});
            }
        }return null;
    }
    @SuppressWarnings("unchecked") private static boolean interact(String name,String option,int x,int y)throws Exception{
        Method method=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);method.setAccessible(true);
        List<ControllerTarget> targets=(List<ControllerTarget>)method.invoke(null,true);
        List<String> descriptions=new ArrayList<>();for(ControllerTarget candidate:targets)descriptions.add(candidate.name+"|"+candidate.option+"|"+(candidate.x+candidate.baseX)+","+(candidate.y+candidate.baseY));
        observations.put("candidates_stage_"+step,descriptions);
        for(ControllerTarget target:targets){
            if((target.name.equalsIgnoreCase(name)||name.equals("Pot")&&target.identifier==1931)&&target.option.equalsIgnoreCase(option)
                &&(x<0||target.x+target.baseX==x&&target.y+target.baseY==y))if(ControllerWorld.interact(target)){observations.put("interaction_sent_stage_"+step,descriptions);return true;}
        }return false;
    }
    private static UiState.Widget item(UiState state,String name,boolean bank){
        if(state.panel!=null&&state.panel.id==762){for(UiState.Pane pane:state.panel.panes)for(UiState.Widget widget:pane.widgets)
            if(widget!=null&&widget.itemId>=0&&widget.quantity>0&&(widget.name.equalsIgnoreCase(name)||name.equals("Pot")&&widget.itemId==1931)&&((widget.id>>>16)==762)==bank)return widget;
        }else if(!bank)for(UiState.Widget widget:state.inventory)if(widget!=null&&widget.itemId>=0&&widget.quantity>0&&(widget.name.equalsIgnoreCase(name)||name.equals("Pot")&&widget.itemId==1931))return widget;
        return null;
    }
    private static boolean invoke(UiState.Widget widget,String label){for(UiState.Action action:widget.actions)if(action.label.replace(" ","-").equalsIgnoreCase(label))return ControllerUi.invoke(widget,action);return false;}
    private static boolean panelAction(String label){UiState.Panel panel=ControllerUi.snapshot().panel;if(panel==null)return false;for(UiState.Pane pane:panel.panes)for(UiState.Widget widget:pane.widgets)if(invoke(widget,label))return true;return false;}
    private static UiState.Widget findItem(UiState state,int id){
        if(state.panel!=null)for(UiState.Pane pane:state.panel.panes)for(UiState.Widget widget:pane.widgets)if(widget!=null&&widget.itemId==id&&widget.quantity>0)return widget;
        for(UiState.Widget widget:state.inventory)if(widget!=null&&widget.itemId==id&&widget.quantity>0)return widget;return null;
    }
    private static String pendingEntry(){
        if(probeNonce==null){probeNonce=java.util.UUID.randomUUID().toString().replace("-","");Class82.method812("soloscape_probe_entry "+probeNonce,false,false,(byte)-79);return null;}
        String prefix="SOLOSCAPE-PROBE|"+probeNonce+"|";
        for(ChatMessage message:Class318_Sub2.aClass147Array6400)if(message!=null&&message.aString2028!=null&&message.aString2028.startsWith(prefix))return message.aString2028.substring(prefix.length());
        return null;
    }
    private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
}
