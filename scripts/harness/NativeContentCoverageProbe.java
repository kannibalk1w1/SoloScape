import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import com.GameClient.ControllerTarget;
import net.runelite.client.input.controller.*;
/** Native cache/server fixtures: supplied beads/wool and scene placement; no earned-route claim. */
public final class NativeContentCoverageProbe {
 private static int stage,scenario,phase,before;private static long evidenceAt;private static boolean rewardCaptured,introCaptured;private static volatile UiState display;private static long since;private static int choices;
 private static final Map<String,Object> results=new LinkedHashMap<>();
 public static boolean active(){return since!=0&&stage<20;}
 private static void next(){stage++;since=System.currentTimeMillis();choices=0;}
 private static void command(String value){Class82.method812(value,false,false,(byte)-79);}
 private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
 private static ControllerTarget target(String name,String option)throws Exception{
  Method scan=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);scan.setAccessible(true);
  for(ControllerTarget t:(List<ControllerTarget>)scan.invoke(null,true))if(t.name.toLowerCase(Locale.ROOT).contains(name.toLowerCase(Locale.ROOT))&&(t.option.equalsIgnoreCase(option)||option.equals("Use")&&t.option.startsWith("Use ")))return t;
  return null;
 }
 private static boolean dialogue(UiState state){
  if(state.dialogue.length==0)return false;
  for(UiState.Widget row:state.dialogue)if(row.actions.length>0){if(ControllerUi.invoke(row,row.actions[0])){choices++;return true;}return false;}return false;
 }
 private static int count(UiState state,int id){int n=0;for(UiState.Widget w:state.inventory)if(w!=null&&w.itemId==id)n+=w.quantity;return n;}
 public static boolean tick(String marker)throws Exception{
  long now=System.currentTimeMillis();if(since==0)since=now;
  Files.write(Paths.get(marker+".content.status"),("stage="+stage+" scenario="+scenario+" phase="+phase+" choices="+choices+" panel="+(ControllerUi.snapshot().panel==null?-1:ControllerUi.snapshot().panel.id)).getBytes("UTF-8"));
  require(now-since<65000,"Content probe timed out at stage "+stage+" choices="+choices);
  UiState state=ControllerUi.snapshot(true);
  Files.write(Paths.get(marker+".content-ui.json"),new com.google.gson.Gson().toJson(state).getBytes("UTF-8"));
  if((stage==7||stage==8||stage==14)&&state.dialogueId<0&&!ControllerUi.hasModalPanel()&&!state.inventoryVisible){ControllerUi.openInventory();return false;}
  if(stage==0){net.runelite.client.RuneLite.getInjector().getInstance(net.runelite.client.ui.overlay.OverlayManager.class).add(new EvidenceOverlay());command("tele 3104 3163 2");for(String bead:new String[]{"black_bead","white_bead","yellow_bead","red_bead"})command("item "+bead+" 1");next();return false;}
  if(stage==1){if(now-since<2500||!ControllerWorld.ready())return false;ControllerTarget npc=target("Wizard Mizgog","Talk-to");if(npc!=null){require(ControllerWorld.interact(npc),"Mizgog Talk-to rejected");next();}return false;}
  if(stage==2){
   if(state.panel!=null&&(state.panel.id==277||state.panel.id==380)){
    require(state.panel.details.length>0,"Native quest rewards contain no readable rows");
    if(!rewardCaptured){rewardCaptured=true;display=state;evidenceAt=now;return false;}if(now-evidenceAt<1000)return false;capture(marker+".content-rewards.png");
    StringBuilder rewards=new StringBuilder();for(UiState.Widget row:state.panel.details){require(row.actions.length==0,"Reward text fabricated actions");rewards.append(row.name).append("; ");}
    results.put("imp_catcher_rewards",rewards.toString());results.put("native_dialogue_operations",choices);ControllerUi.cancelWorld();next();return false;
   }
   dialogue(state);return false;
  }
  if(stage==3){if(ControllerUi.hasModalPanel())return false;ControllerUi.cancelWorld();command("tele 3245 3198 0");next();return false;}
  if(stage==4){if(now-since<2500||!ControllerWorld.ready())return false;ControllerTarget npc=target("Xenia","Talk-to");if(npc!=null){require(ControllerWorld.interact(npc),"Xenia Talk-to rejected");next();}return false;}
  if(stage==5){
   if(state.panel!=null&&state.panel.id==178){
    require(state.panel.details.length>0,"Quest introduction has no readable requirements/rewards");
    if(!introCaptured){introCaptured=true;display=state;evidenceAt=now;return false;}if(now-evidenceAt<1000)return false;capture(marker+".content-intro.png");
    results.put("blood_pact_intro_rows",state.panel.details.length);
    for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)if((w.id&65535)==73&&w.actions.length>0){require(ControllerUi.invoke(w,w.actions[0]),"Native quest start rejected");next();return false;}
    return false;
   }
   dialogue(state);return false;
  }
  if(stage==6){if(dialogue(state))return false;if(ControllerUi.hasModalPanel()||now-since<2000)return false;command("item wool 1");command("tele 3210 3213 1");next();return false;}
  if(stage==7){
   if(now-since<2500)return false;
   if(count(state,1759)>0&&count(state,1737)==0){results.put("spinning_wool_to_ball_without_mouse",true);next();return false;}
   if(state.dialogueId==905){recipe(state);return false;}
   if(state.dialogue.length>0){dialogue(state);return false;}
   if(choices==0){ControllerTarget wheel=target("Spinning wheel","Spin");if(wheel!=null){require(ControllerWorld.interact(wheel),"Spin operation rejected");choices=1;}}return false;
  }
  if(stage==8){
   String[] names={"pottery_shape","pottery_fire","smelting_bronze","smithing_dagger","fletching_shafts"};
   int[] products={1787,1931,2349,1205,52},sources={1761,-1,-1,2349,946};
   String[] locations={"3086 3410 0","3085 3408 0","3227 3255 0","3187 3426 0","3221 3219 0"};
   if(phase==0){
    ControllerUi.cancelWorld();before=count(state,products[scenario]);command("tele "+locations[scenario]);
    if(scenario==0)command("item soft_clay 1");if(scenario==2){command("item copper_ore 1");command("item tin_ore 1");}
    if(scenario==3)command("item hammer 1");if(scenario==4){command("item knife 1");command("item logs 1");}
    phase=1;since=now;return false;
   }
   if(now-since<2500)return false;
   if(count(state,products[scenario])>before){results.put(names[scenario]+"_produced",count(state,products[scenario])-before);scenario++;phase=0;choices=0;since=now;
    if(scenario==names.length){next();scenario=0;phase=0;}return false;
   }
   if(state.dialogueId==905){recipe(state);return false;}
   if(state.panel!=null&&state.panel.id==300){for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)if(w.itemId==1205||w.name.toLowerCase(Locale.ROOT).contains("dagger"))for(UiState.Action a:w.actions)if(a.label.equals("Make 1")){ControllerUi.invoke(w,a);return false;}return false;}
   if(state.dialogue.length>0){dialogue(state);return false;}
   if(phase==1&&sources[scenario]>=0){for(UiState.Widget w:state.inventory)if(w!=null&&w.itemId==sources[scenario])for(UiState.Action a:w.actions)if(a.type==13&&ControllerUi.invoke(w,a)){phase=2;return false;}return false;}
   if(phase==1||phase==2){
    if(scenario==4){for(UiState.Widget w:state.inventory)if(w!=null&&w.itemId==1511)for(UiState.Action a:w.actions)if(a.type==6&&ControllerUi.invoke(w,a)){phase=3;return false;}}
    else {String[] targetNames={"Potter's wheel","Pottery oven","Furnace","Anvil"};String[] options={"Use","Fire","Smelt","Use"};ControllerTarget t=target(targetNames[scenario],options[scenario]);if(t!=null&&ControllerWorld.interact(t))phase=3;}
   }
   return false;
  }
  if(stage==9){if(!state.inventoryVisible){ControllerUi.openInventory();return false;}for(int id:new int[]{1759,1205,52})for(UiState.Widget w:state.inventory)if(w!=null&&w.itemId==id)for(UiState.Action a:w.actions)if(a.label.equals("Drop")){ControllerUi.invoke(w,a);return false;}ControllerUi.cancelWorld();command("tele 2925 3485 0");for(String raw:new String[]{"raw_beef","raw_rat_meat","raw_bear_meat","raw_chicken"})command("item "+raw+" 1");next();return false;}
  if(stage==10||stage==12||stage==15||stage==17){
   if((stage==12||stage==15)&&phase==0){ControllerUi.cancelWorld();command("tele 2896 3426 1");phase=1;since=now;return false;}
   if(now-since<2500||!ControllerWorld.ready())return false;
   ControllerTarget npc=target(stage==10||stage==17?"Kaqemeex":"Sanfew","Talk-to");
   if(npc!=null&&ControllerWorld.interact(npc)){next();phase=0;}return false;
  }
  if(stage==11||stage==13||stage==16){
   if(druidDialogue(state))return false;
   if(choices==0||state.dialogueId>=0||ControllerUi.hasModalPanel()||!ControllerWorld.ready())return false;
   if(quietSince==0){quietSince=now;return false;}if(now-quietSince<1200)return false;quietSince=0;
   if(stage==13){ControllerUi.cancelWorld();command("tele 2892 9831 0");}
   if(stage==16){for(int id:new int[]{522,523,524,525})require(count(state,id)==0,"Sanfew did not consume enchanted meat "+id);results.put("druidic_meats_handed_in",4);ControllerUi.cancelWorld();command("tele 2925 3485 0");}
   next();return false;
  }
  if(stage==14){
   if(now-since<2500)return false;
   int[] raw={2132,2134,2136,2138};
   if(scenario==4){results.put("druidic_meats_enchanted",4);next();phase=0;return false;}
   if(count(state,522+scenario)==1&&count(state,raw[scenario])==0){scenario++;phase=0;return false;}
   if(phase==0){for(UiState.Widget w:state.inventory)if(w!=null&&w.itemId==raw[scenario])for(UiState.Action a:w.actions)if(a.type==13&&ControllerUi.invoke(w,a)){phase=1;return false;}return false;}
   if(phase==1){ControllerTarget cauldron=target("Cauldron of Thunder","Use");if(cauldron!=null&&ControllerWorld.interact(cauldron)){phase=2;return false;}}
   return false;
  }
  if(stage==18){
   if(state.panel!=null&&(state.panel.id==277||state.panel.id==380)){
    StringBuilder rewards=new StringBuilder();for(UiState.Widget w:state.panel.details)rewards.append(w.name).append("; ");
    require(rewards.toString().contains("250")&&rewards.toString().contains("4"),"Druidic Ritual native reward rows incomplete: "+rewards);
    if(phase==0){results.put("druidic_ritual_rewards",rewards.toString());display=state;evidenceAt=now;phase=1;return false;}
    if(now-evidenceAt<1000)return false;capture(marker+".druidic-rewards.png");ControllerUi.cancelWorld();next();phase=0;return false;
   }
   druidDialogue(state);return false;
  }
  if(stage==19){
   if(druidDialogue(state))return false;
   if(state.panel!=null&&(state.panel.id==277||state.panel.id==380)){ControllerUi.cancelWorld();return false;}
   if(state.panel!=null&&state.panel.id==275){
    StringBuilder journal=new StringBuilder();for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)journal.append(w.name).append("; ");for(UiState.Widget w:state.panel.details)journal.append(w.name).append("; ");
    require(journal.toString().contains("QUEST COMPLETE"),"Completed Druidic journal missing: "+journal);
    if(phase<2){results.put("druidic_completed_journal",journal.toString());display=state;evidenceAt=now;phase=2;return false;}
    if(now-evidenceAt<1000)return false;capture(marker+".druidic-journal.png");ControllerUi.cancelWorld();next();
    Files.write(Paths.get(marker+".content.json"),new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(results).getBytes("UTF-8"));System.out.println("Native quest/production gateways and Druidic Ritual completion passed.");return true;
   }
   if(ControllerUi.hasModalPanel())return false;
   if(state.panel!=null&&state.panel.id==190){UiState.Widget last=null;for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets){last=w;if(w.name.contains("Druidic Ritual")&&w.actions.length>0){if(ControllerUi.invoke(w,w.actions[0]))phase=1;return false;}}if(last!=null)ControllerUi.scroll(last,12);return false;}
   if(phase==0)ControllerUi.openTab(HomeTab.QUESTS.ordinal());return false;
  }
  return true;
 }
 private static long quietSince;
 private static boolean druidDialogue(UiState state){
  if(state.dialogue.length==0)return false;quietSince=0;
  for(String preferred:new String[]{"in search of a quest","Yes.","sent to help purify","Ok, I'll do that"})for(UiState.Widget w:state.dialogue)if(w.name.contains(preferred)&&w.actions.length>0){if(ControllerUi.invoke(w,w.actions[0]))choices++;return true;}
  return dialogue(state);
 }
 private static void capture(String path){javax.swing.SwingUtilities.invokeLater(()->{try{java.awt.Canvas canvas=net.runelite.client.RuneLite.getInjector().getInstance(com.GameClient.class).getCanvas();javax.imageio.ImageIO.write(new java.awt.Robot().createScreenCapture(new java.awt.Rectangle(canvas.getLocationOnScreen(),canvas.getSize())),"png",new java.io.File(path));}catch(Exception error){System.err.println("Content evidence capture failed: "+error);}finally{display=null;}});}
 private static final class EvidenceOverlay extends net.runelite.client.ui.overlay.Overlay {
  EvidenceOverlay(){setPosition(net.runelite.client.ui.overlay.OverlayPosition.DYNAMIC);setLayer(net.runelite.client.ui.overlay.OverlayLayer.ALWAYS_ON_TOP);}
  public java.awt.Dimension render(java.awt.Graphics2D graphics){
   UiState current=display;if(current==null||current.panel==null)return null;
   com.GameClient client=net.runelite.client.RuneLite.getInjector().getInstance(com.GameClient.class);
   PanelPresentation layout=new PanelPresentation(client.getCanvasWidth(),client.getCanvasHeight(),1,current.panel.id);
   UiState shown=layout.present(current,null,true,true,true,true,true,true,true,true,true);UiState.Pane pane=shown.panel.panes[0];
   net.runelite.client.plugins.soloscapecontroller.SoloScapePanelOverlay.paint(graphics,layout,shown.panel.name+" / "+pane.name,pane.widgets,pane.widgets.length==0?null:pane.widgets[0],null,net.runelite.client.plugins.soloscapecontroller.ControllerGlyphs.XBOX,-1,s->s,w->client.getControllerItemImage(w.itemId,w.quantity));return null;
  }
 }
 private static void recipe(UiState state){
  List<String> labels=new ArrayList<>();for(UiState.Widget row:state.dialogue)if(row.actions.length>0)labels.add(row.name+" / "+row.actions[0].label);results.put(stage==7?"spinning_recipes":"production_recipes_"+scenario,labels);
  if(state.amount!=1){for(UiState.Widget w:state.amounts)if((w.id&65535)==5&&w.actions.length>0){ControllerUi.invoke(w,w.actions[0]);return;}}
  for(UiState.Widget w:state.dialogue)if((w.id&65535)==14&&w.actions.length>0){ControllerUi.invoke(w,w.actions[0]);return;}
 }
}
