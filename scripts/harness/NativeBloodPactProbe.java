import com.GameClient;
import com.GameClient.ControllerTarget;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.List;
import net.runelite.api.Perspective;
import net.runelite.api.coords.LocalPoint;
import net.runelite.client.RuneLite;
import net.runelite.client.config.ConfigManager;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.SoloScapeControllerPlugin;
import net.runelite.client.ui.overlay.*;

/**
 * The Blood Pact played through from a fresh character with no admin commands, item grants, teleports or
 * injected damage. World movement, aiming, target cycling, attacks, loot-pile browsing and B cancellation run
 * as scripted gamepad states through the controller plugin's own input tick; dialogue rows go through the
 * native widget gateway. Movement steers the left stick along a route found on the client's own collision map,
 * the way a player who knows the way would. Combat is earned. Quest-scripted fades and stairs are the only
 * position changes not walked. Synthetic input on a private display: no physical controller or Deck acceptance.
 */
public final class NativeBloodPactProbe {
 private static final int A=1,B=2,X=4,LB=1<<9,RB=1<<10,UP=1<<11,DOWN=1<<12;
 private static final int DONE=99;
 private static final boolean KILL_CULTISTS=Boolean.getBoolean("soloscape.bloodpact.killCultists");
 /** Per-cultist fates; the all-kill flag is the default for both. Reese's end choice defaults to kill. */
 private static final boolean KILL_KAYLE=choice("kayle");private static final boolean KILL_CAITLIN=choice("caitlin");
 private static final boolean SPARE_REESE="spare".equals(System.getProperty("soloscape.bloodpact.reese"));
 /** Wield Caitlin's staff and beat Reese with an autocast spell. */
 private static final boolean MAGIC=Boolean.getBoolean("soloscape.bloodpact.magic");
 /** Druidic Ritual mode: same pad, travel and dialogue helpers, a different earned route. */
 private static final boolean DRUIDIC="druidic".equals(System.getProperty("soloscape.bloodpact.route"));
 private static final int HP_XP_GOAL=Integer.getInteger("soloscape.druidic.hpXp",0);
 private static long stageLimit=150_000;
 private static boolean choice(String who){String v=System.getProperty("soloscape.bloodpact."+who);return v==null?KILL_CULTISTS:v.equals("kill");}
 private static Map<String,Integer> beforeReese;
 private static int stage,phase,sub,heldBefore,attempts,cycles,represses;private static long stageAt,phaseAt,subAt,started,lastPress;
 private static SoloScapeControllerPlugin plugin;private static Method process;private static Field failed;
 private static GamepadState raw;private static WorldControls world;
 private static final Map<String,Object> results=new LinkedHashMap<>();
 private static final List<String> timeline=new ArrayList<>();
 private static final Observation observation=new Observation();
 private static volatile Throwable failure;private static String probeMarker;private static boolean unregistered;
 private static int offX=Integer.MIN_VALUE,offY;private static String[] preferred={};private static long lastDialogue;private static boolean conversed;
 private static int minHp=99,meals;private static boolean asked,healing;private static int notReady;private static long lastNotReady;private static final StringBuilder notReadyWhy=new StringBuilder();private static int lastTileX,lastTileY;private static long lastMoveAt;
 private static float stickX,stickY,trigger;private static int held;

 public static boolean active(){return stage>0&&stage<DONE;}
 private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
 private static void next(String label){timeline.add(String.format("%.1fs %s",(System.currentTimeMillis()-started)/1000.0,label));stage++;phase=0;sub=0;conversed=false;notReady=0;notReadyWhy.setLength(0);attempts=0;cycles=0;stageAt=phaseAt=subAt=System.currentTimeMillis();}
 private static void phase(int value){phase=value;phaseAt=System.currentTimeMillis();}
 private static void sub(int value){sub=value;subAt=System.currentTimeMillis();phase(0);}

 // ---- native state ----
 private static Player me(){return Class132.aPlayer_1907;}
 private static int sceneX(){return me().x>>9;} private static int sceneY(){return me().y>>9;}
 private static int worldX(){return sceneX()+za_Sub2.regionTileX;} private static int worldY(){return sceneY()+Class90.regionTileY;}
 private static int plane(){return me().plane;}
 private static boolean instanced(){return za_Sub2.regionTileX>=6400;}
 private static int hp(){return Class161.anIntArray2145==null?-1:Class161.anIntArray2145[3];}
 private static GameClient client(){return RuneLite.getInjector().getInstance(GameClient.class);}
 @SuppressWarnings("unchecked")
 private static List<ControllerTarget> candidates()throws Exception{
  Method scan=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);scan.setAccessible(true);
  return (List<ControllerTarget>)scan.invoke(null,true);
 }
 private static ControllerTarget find(String name,String option)throws Exception{
  for(ControllerTarget t:candidates())if(t.name.toLowerCase(Locale.ROOT).contains(name.toLowerCase(Locale.ROOT))&&t.option.equalsIgnoreCase(option))return t;
  return null;
 }
 /** Item count from the visible inventory; -1 while it is closed (it is opened, as a player would). */
 private static int count(String name){
  UiState state=ControllerUi.snapshot(true);
  if(!state.inventoryVisible){long now=System.currentTimeMillis();if(now-lastInventoryOpen>1000){lastInventoryOpen=now;ControllerUi.openInventory();}return -1;}
  int n=0;for(UiState.Widget w:state.inventory)if(w!=null&&w.itemId>=0&&w.name.equalsIgnoreCase(name))n+=Math.max(1,w.quantity);return n;
 }
 private static long lastInventoryOpen;
 private static Map<String,Integer> experience(){Map<String,Integer> xp=new LinkedHashMap<>();for(GameClient.SkillSnapshot s:client().getSkillSnapshots())xp.put(s.getSkill().getName(),s.getXp());return xp;}
 private static int[] instance(int x,int y){require(offX!=Integer.MIN_VALUE,"Instance offset unknown");return new int[]{x+offX,y+offY};}

 // ---- scripted pad ----
 /** One plugin input tick; press/release edges follow from the previous tick. */
 private static void input()throws Exception{
  raw.connected=true;raw.leftX=stickX;raw.leftY=stickY;raw.rightX=raw.rightY=raw.rightTrigger=0;raw.leftTrigger=trigger;
  raw.buttonsPressed=held&~heldBefore;raw.buttonsReleased=heldBefore&~held;raw.buttonsHeld=held;heldBefore=held;
  process.invoke(plugin,0L);
 }
 private static void neutral(){stickX=stickY=trigger=0;held=0;}
 /** The plugin's stick-to-world mapping is a reflection and therefore its own inverse. */
 private static void stickToward(double dx,double dy,float magnitude){
  int yaw=client().getCameraYaw();double length=Math.hypot(dx,dy);if(length<1e-6){stickX=stickY=0;return;}
  stickX=(float)(WorldInput.worldX((float)(dx/length),(float)(dy/length),yaw)*magnitude);
  stickY=(float)(WorldInput.worldY((float)(dx/length),(float)(dy/length),yaw)*magnitude);
 }

 // ---- route on the client's collision map ----
 private static final int[][] STEPS={{0,1},{1,0},{0,-1},{-1,0},{1,1},{1,-1},{-1,1},{-1,-1}};
 private static String travelDiag="";private static int[] field;private static String fieldKey="";
 /** Steps-to-goal for every scene tile, by reverse BFS over the client's own collision flags. */
 private static int[] distances(int goalX,int goalY,int tolerance){
  String key=goalX+","+goalY+","+tolerance+","+plane()+","+za_Sub2.regionTileX+","+Class90.regionTileY;
  if(key.equals(fieldKey))return field;
  Class361 map=Class348_Sub45.aClass361Array7108[plane()];
  int w=Class367_Sub4.anInt7319,h=Class348_Sub40_Sub3.anInt9109;int[] dist=new int[w*h];Arrays.fill(dist,Integer.MAX_VALUE);
  ArrayDeque<Integer> open=new ArrayDeque<>();
  for(int x=Math.max(0,goalX-tolerance);x<=Math.min(w-1,goalX+tolerance);x++)for(int y=Math.max(0,goalY-tolerance);y<=Math.min(h-1,goalY+tolerance);y++){dist[x*h+y]=0;open.add(x*h+y);}
  while(!open.isEmpty()){
   int cell=open.poll(),x=cell/h,y=cell%h;
   for(int[] d:STEPS){int nx=x-d[0],ny=y-d[1];if(nx<0||ny<0||nx>=w||ny>=h||dist[nx*h+ny]!=Integer.MAX_VALUE)continue;
    if(!WorldInput.canStep(map.anIntArrayArray4438,nx-map.anInt4453,ny-map.anInt4441,d[0],d[1]))continue;dist[nx*h+ny]=dist[cell]+1;open.add(nx*h+ny);}
  }
  field=dist;fieldKey=key;return dist;
 }
 /** Holds the stick toward a world tile; true once within {@code tolerance}. */
 private static boolean travel(int goalWorldX,int goalWorldY,int tolerance,String label){
  long now=System.currentTimeMillis();int gx=goalWorldX-za_Sub2.regionTileX,gy=goalWorldY-Class90.regionTileY;
  if(sceneX()!=lastTileX||sceneY()!=lastTileY){lastTileX=sceneX();lastTileY=sceneY();lastMoveAt=now;}
  if(Math.max(Math.abs(sceneX()-gx),Math.abs(sceneY()-gy))<=tolerance){neutral();return true;}
  if(!ControllerWorld.ready()){neutral();lastMoveAt=now;return false;}
  require(now-lastMoveAt<15_000,"Stuck while travelling to "+label+" at "+worldX()+","+worldY()+","+plane()+" "+travelDiag);
  int h=Class348_Sub40_Sub3.anInt9109,x=sceneX(),y=sceneY();int[] dist=distances(gx,gy,tolerance);
  if(dist[x*h+y]==Integer.MAX_VALUE){ // doors and gates open a tick after the script that removes them
   travelDiag="no route on the client collision map yet";fieldKey="";neutral();return false;}
  // Like a player nudging the stick: choose the angle whose native walk destination gets closest.
  Class361 map=Class348_Sub45.aClass361Array7108[plane()];double bestX=0,bestY=0;float bestMagnitude=.95f;int best=dist[x*h+y];
  for(float magnitude:new float[]{.95f,.7f,.4f})for(int i=0;i<16;i++){ // full push walks three tiles; ease off near the goal
   double angle=i*Math.PI/8,dx=Math.cos(angle),dy=Math.sin(angle);
   long tile=WorldInput.destination(map.anIntArrayArray4438,x-map.anInt4453,y-map.anInt4441,dx*magnitude,dy*magnitude);
   int tx=WorldInput.x(tile)+map.anInt4453,ty=WorldInput.y(tile)+map.anInt4441;
   if(tx<0||ty<0||tx*h+ty>=dist.length)continue;
   if(dist[tx*h+ty]<best){best=dist[tx*h+ty];bestX=dx;bestY=dy;bestMagnitude=magnitude;}
  }
  String walkGuards="?";
  try{
   long tile=WorldInput.destination(map.anIntArrayArray4438,x-map.anInt4453,y-map.anInt4441,bestX*bestMagnitude,bestY*bestMagnitude);
   int dx=WorldInput.x(tile)+map.anInt4453,dy=WorldInput.y(tile)+map.anInt4441;
   Method reach=ControllerWorld.class.getDeclaredMethod("reachable",int.class,int.class,int.class,int.class,int.class,int.class,int.class);reach.setAccessible(true);
   Field last=ControllerWorld.class.getDeclaredField("lastWalk");last.setAccessible(true);
   walkGuards="dest="+dx+","+dy+" reachable="+reach.invoke(null,dx,dy,1,1,-4,0,0)+" selection="+r.aBoolean9722+" lastWalkSame="+(last.getLong(null)==WorldInput.pack(dx+za_Sub2.regionTileX,dy+Class90.regionTileY))
    +" controls="+fields(world,"armed","moving","walkingPaused","haveAim","directMode","lastWalk")+" cw="+fields(null,"lastWalk","lastPosition","lastProgress")+" now="+System.nanoTime()
    +" marker="+Class248.anInt3203+","+Class97.anInt1548+" pathHead="+me().anIntArray10320[0]+","+me().anIntArray10317[0]+" scene="+x+","+y+" mapOrigin="+map.anInt4453+","+map.anInt4441;
  }catch(Exception ex){walkGuards="diag failed "+ex;}
  travelDiag=walkGuards+" dist="+dist[x*h+y]+" best="+best+" angle="+String.format("%.2f,%.2f",bestX,bestY)+" native="+ControllerWorld.walkDestination()+" feedback="+world.feedback(System.nanoTime())+" stick="+String.format("%.2f,%.2f",stickX,stickY)+" yaw="+client().getCameraYaw();
  if(bestX==0&&bestY==0){neutral();return false;} // no single stick push helps yet; the stuck timer reports it
  // Not moving for a while: let go and push again, as a player would. World input re-arms only from neutral
  // after any readiness change (fades, tab refreshes), so a stick held through one does nothing.
  if(now-lastMoveAt>1500&&now-lastRelease>1500){lastRelease=now;releases++;results.put("stick_releases_while_travelling",releases);}
  if(now-lastRelease<250){neutral();return false;}
  trigger=0;held=0;stickToward(bestX,bestY,bestMagnitude);return false;
 }
 private static long lastRelease;private static int releases;

 private static String fields(Object owner,String... names){
  StringBuilder out=new StringBuilder("{");Class<?> type=owner==null?ControllerWorld.class:owner.getClass();
  for(String name:names){try{Field f=type.getDeclaredField(name);f.setAccessible(true);out.append(name).append('=').append(f.get(owner)).append(' ');}catch(Exception ex){out.append(name).append("=? ");}}
  return out.append('}').toString();
 }

 // ---- targeting through LT aim, LB/RB cycling and A ----
 private static int focusFailures;private static int[] pileTile;
 private static boolean matches(ControllerTarget t,String name,String option){if(pileTile!=null&&t!=null&&option.equals("Take")&&t.kind()==3&&t.x==pileTile[0]&&t.y==pileTile[1])return true;return t!=null&&t.name.toLowerCase(Locale.ROOT).contains(name.toLowerCase(Locale.ROOT))&&t.option.equalsIgnoreCase(option);}
 /**
  * Aims the left stick at the entity, cycles with RB while the shown focus is something else, then presses
  * {@code button}. Returns the focused target once pressed, null while still working.
  */
 private static ControllerTarget aimAndPress(String name,String option,int button)throws Exception{
  long now=System.currentTimeMillis();
  ControllerTarget wanted=find(name,option);
  if(wanted==null||!ControllerWorld.ready()){neutral();return null;}
  if(phase==0){ // a neutral beat first: world input re-arms only from neutral after dialogue or any readiness change
   if(now-phaseAt<150){neutral();return null;}
   trigger=1;held=0;stickToward(wanted.x+wanted.width/2.0-(sceneX()+.5),wanted.y+wanted.height/2.0-(sceneY()+.5),.6f);if(now-phaseAt>400)phase(1);return null;}
  if(phase==1){neutral();trigger=1;if(now-phaseAt>150)phase(2);return null;} // aim kept, stick released
  ControllerTarget shown=world.getTarget();
  if(phase==2){
   trigger=0;stickX=stickY=0;
   if(matches(shown,name,option)){held=button;phase(3);return null;}
   if(cycles==12&&DRUIDIC&&focusFailures<80){focusFailures++;results.put("focus_retries",focusFailures);cycles=0;neutral();phase(0);return null;} // ground clutter can win the focus; try another aim
   if(cycles==12){
    StringBuilder d=new StringBuilder();
    try{
     double fx=wanted.x+wanted.width/2.0-(sceneX()+.5),fy=wanted.y+wanted.height/2.0-(sceneY()+.5),l=Math.hypot(fx,fy);
     ControllerTarget direct=ControllerWorld.findTarget(fx/l,fy/l,null);
     Method scan=ControllerWorld.class.getDeclaredMethod("candidates",boolean.class);scan.setAccessible(true);
     d.append(" findTarget=").append(direct==null?"null":direct.name+"/"+direct.option).append(" defaults=");
     for(Object o:(List<?>)scan.invoke(null,false)){ControllerTarget t=(ControllerTarget)o;d.append(t.name).append('/').append(t.option).append('@').append(t.x-sceneX()).append(',').append(t.y-sceneY()).append(" approach=").append(t.serverApproach).append("; ");}
     Field uiField=SoloScapeControllerPlugin.class.getDeclaredField("ui");uiField.setAccessible(true);UiControls ui=(UiControls)uiField.get(plugin);
     d.append(" uiActive=").append(ui.active()).append(" inventoryFocused=").append(ui.inventoryFocused()).append(" panel=").append(ui.focusedPanel()).append(" inDialogue=").append(ui.inDialogue());
     d.append(" plugin=").append(fields(plugin,"mappingArmed","settingsOpen","restoringSource","lastInputTick"));
     d.append(" controls=").append(fields(world,"armed","haveAim","facingX","facingY","walkingPaused","lastFind"));
     d.append(" notReadyTicks=").append(notReady).append(" why=").append(notReadyWhy);
     d.append(" wanted=").append(wanted.x-sceneX()).append(',').append(wanted.y-sceneY()).append(" size=").append(wanted.width);
     d.append(" scoreOk=").append(Double.isFinite(WorldInput.areaScore(sceneX()+.5,sceneY()+.5,wanted.x,wanted.y,wanted.width,wanted.height,fx/l,fy/l,false,10)));
    }catch(Exception ex){d.append(ex);}
    throw new IllegalStateException("Could not focus "+name+"/"+option+" with LB/RB; showing "+(shown==null?"nothing":shown.name+"/"+shown.option)+d);
   }
   cycles++;
   held=RB;phase(4);return null;
  }
  if(phase==4){held=0;if(now-phaseAt>120)phase(2);return null;}
  held=0;phase(0);return shown; // phase 3: button released after one tick
 }

 // ---- dialogue through native widgets; choices must be expected ----
 private static boolean dialogue()throws Exception{
  UiState state=ControllerUi.snapshot(true);
  List<UiState.Widget> rows=new ArrayList<>();for(UiState.Widget row:state.dialogue)if(row.actions.length>0)rows.add(row);
  if(rows.isEmpty())return state.dialogue.length>0;
  conversed=true;
  long now=System.currentTimeMillis();if(now-lastDialogue<450)return true;lastDialogue=now;
  if(rows.size()==1){ControllerUi.invoke(rows.get(0),rows.get(0).actions[0]);return true;}
  List<String> wantedList=new ArrayList<>(Arrays.asList(preferred));wantedList.addAll(Arrays.asList("I can handle this.","Let's get on with this.","I think I'll go now."));
  for(String wanted:wantedList)for(UiState.Widget row:rows)if(row.name.contains(wanted)){
   if(ControllerUi.invoke(row,row.actions[0]))timeline.add("chose: "+row.name);return true;}
  StringBuilder seen=new StringBuilder();for(UiState.Widget row:rows)seen.append(row.name).append(" | ");
  throw new IllegalStateException("Unexpected choice at stage "+stage+": "+seen);
 }
 /** Quest intro "Yes", quest-complete scroll and level-up panels. */
 private static boolean panels()throws Exception{
  UiState state=ControllerUi.snapshot(true);
  if(state.panel==null)return false;
  if(state.panel.id==178){
   results.put("blood_pact_intro_rows",state.panel.details.length);
   for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)if((w.id&65535)==73&&w.actions.length>0){
    long now=System.currentTimeMillis();if(now-lastDialogue>450){lastDialogue=now;if(ControllerUi.invoke(w,w.actions[0]))timeline.add("quest intro: Yes");}return true;}
   return true;
  }
  if(state.panel.id==277||state.panel.id==380){
   StringBuilder rewards=new StringBuilder();for(UiState.Widget row:state.panel.details)rewards.append(row.name).append("; ");
   results.put("quest_complete_panel",rewards.toString());ControllerUi.cancelWorld();return true;
  }
  if(stage==journalStage()&&(state.panel.id==275||state.panel.id==190))return false; // the journal check reads these
  if(state.panel.modal&&seenPanels.add(state.panel.id))timeline.add("modal panel "+state.panel.id+" "+state.panel.name);
  return ControllerUi.hasModalPanel();
 }
 private static final Set<Integer> seenPanels=new HashSet<>();

 // ---- magic: the new character's own starter runes, then Wind Strike as the staff's autocast ----
 private static long lastTab;
 /** Opens the spellbook tab and uses Wind Strike's native Autocast action. */
 private static boolean autocast()throws Exception{
  long now=System.currentTimeMillis();UiState state=ControllerUi.snapshot(true);
  if(state.panel==null||!state.panel.name.equals("Spellbook")){if(now-lastTab>900){lastTab=now;ControllerUi.openTab(HomeTab.SPELLBOOK.ordinal());}return false;}
  if(now-lastTab<600)return false;
  StringBuilder seen=new StringBuilder();
  for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:state.panel.panes.length>0?pane.widgets:new UiState.Widget[0]){
   if(w==null)continue;if(seen.length()<900&&!w.name.isEmpty())seen.append(w.name).append(w.actions.length>0?Arrays.toString(Arrays.stream(w.actions).map(a->a.label).toArray()):"").append(" | ");
   if(!w.name.equalsIgnoreCase("Wind Strike"))continue;
   for(UiState.Action a:w.actions)if(a.label.toLowerCase(Locale.ROOT).contains("autocast")){
    ControllerUi.invoke(w,a);results.put("autocast_action",a.label+" on "+w.name);timeline.add("selected Wind Strike autocast");lastTab=now;
    ControllerUi.cancelWorld();return true;}
   StringBuilder labels=new StringBuilder();for(UiState.Action a:w.actions)labels.append(a.label).append(',');
   throw new IllegalStateException("Wind Strike offers no Autocast action; actions="+labels+" panel widgets="+seen);
  }
  require(now-subAt<10_000,"Wind Strike not found in the spellbook panel: "+seen);
  return false;
 }
 private static int[] runesBefore;private static boolean shot;
 /** Window screenshot from a side thread so the client thread is never stalled past the 750 ms input reset. */
 private static void screenshot(String suffix){
  try{Canvas canvas=client().getCanvas();Rectangle area=new Rectangle(canvas.getLocationOnScreen(),canvas.getSize());String file=probeMarker+suffix;
   new Thread(()->{try{javax.imageio.ImageIO.write(new Robot().createScreenCapture(area),"png",new java.io.File(file));}catch(Exception ignored){}}).start();
  }catch(Exception ignored){}
 }
 /** Before Reese: the starter rune counts that his fight must spend. */
 private static boolean noteRunes(){
  if(!MAGIC||runesBefore!=null)return true;int air=count("Air rune"),mind=count("Mind rune");if(air<0||mind<0)return false;
  runesBefore=new int[]{air,mind};results.put("runes_before_reese",air+" air, "+mind+" mind");return true;
 }
 /** During Reese's fight: a screenshot once the first cast has paid out Magic XP. */
 private static void watchCasting(){
  if(!MAGIC||shot)return;if(experience().get("Magic")>beforeReese.get("Magic")){shot=true;screenshot(".magic-fight.png");timeline.add("first Magic XP: screenshot");}
 }
 /** Runes spent and Magic XP gained during Reese's fight, with Attack XP unchanged: the staff really cast. */
 private static boolean magicEvidence(){
  if(!MAGIC)return true;Map<String,Integer> now=experience();
  results.put("magic_xp_before_reese",beforeReese.get("Magic"));results.put("magic_xp_after_reese",now.get("Magic"));
  results.put("attack_xp_before_reese",beforeReese.get("Attack"));results.put("attack_xp_after_reese",now.get("Attack"));
  require(now.get("Magic")>beforeReese.get("Magic"),"No Magic XP earned against Reese: "+beforeReese.get("Magic")+" -> "+now.get("Magic"));
  require(now.get("Attack").equals(beforeReese.get("Attack")),"Reese fight gave melee XP, so the staff meleed: "+beforeReese.get("Attack")+" -> "+now.get("Attack"));
  int air=count("Air rune"),mind=count("Mind rune");if(air<0||mind<0)return false;
  results.put("runes_after_reese",air+" air, "+mind+" mind");
  // The inventory widget can lag the server by a tick or two; the authoritative rune counts are checked in the saved file.
  return true;
 }


 // ---- Druidic Ritual: earned meats, long walks, the quest NPCs and the dungeon cauldron ----
 private static final Map<Long,Integer> seenBlocks=new HashMap<>();
 private static int[] waypoint;private static long waypointAt,lastBlockTick;private static int lastBlockX=-1,lastBlockY=-1,stuckCount;
 private static final int EDGE=6;
 private static ControllerTarget nearest(String name,String option)throws Exception{
  ControllerTarget best=null;int bestD=Integer.MAX_VALUE;
  for(ControllerTarget t:candidates())if(matches(t,name,option)){int d=Math.max(Math.abs(t.x-sceneX()),Math.abs(t.y-sceneY()));if(d<bestD){bestD=d;best=t;}}
  return best;
 }
 /** Forward steps from the player over the client's own collision flags. */
 private static int[] reachable(){
  Class361 map=Class348_Sub45.aClass361Array7108[plane()];int w=Class367_Sub4.anInt7319,h=Class348_Sub40_Sub3.anInt9109;
  int[] dist=new int[w*h];Arrays.fill(dist,Integer.MAX_VALUE);ArrayDeque<Integer> open=new ArrayDeque<>();
  if(sceneX()<0||sceneY()<0||sceneX()>=w||sceneY()>=h)return dist; // the scene is reloading after a region change
  dist[sceneX()*h+sceneY()]=0;open.add(sceneX()*h+sceneY());
  while(!open.isEmpty()){int cell=open.poll(),x=cell/h,y=cell%h;
   for(int[] d:STEPS){int nx=x+d[0],ny=y+d[1];if(nx<0||ny<0||nx>=w||ny>=h||dist[nx*h+ny]!=Integer.MAX_VALUE)continue;
    if(!WorldInput.canStep(map.anIntArrayArray4438,x-map.anInt4453,y-map.anInt4441,d[0],d[1]))continue;dist[nx*h+ny]=dist[cell]+1;open.add(nx*h+ny);}}
  return dist;
 }
 private static long block(int wx,int wy){return ((long)(wx>>2)<<32)|(wy>>2);}
 /**
  * Long-distance stick travel. The scene only spans about 100 tiles, so far goals are approached through
  * reachable in-scene waypoints chosen by distance to the goal, with a penalty on blocks already walked
  * so concave walls and rivers are routed around instead of hugged.
  */
 private static boolean walkTo(int goalX,int goalY,int tolerance,String label){
  long now=System.currentTimeMillis();int w=Class367_Sub4.anInt7319,h=Class348_Sub40_Sub3.anInt9109;
  int gx=goalX-za_Sub2.regionTileX,gy=goalY-Class90.regionTileY;
  if(sceneX()<0||sceneY()<0||sceneX()>=w||sceneY()>=h){neutral();return false;}
  if(sceneX()!=lastBlockX||sceneY()!=lastBlockY){lastBlockX=sceneX();lastBlockY=sceneY();if(now-lastBlockTick>400){lastBlockTick=now;seenBlocks.merge(block(worldX(),worldY()),1,Integer::sum);}}
  if(Math.max(Math.abs(worldX()-goalX),Math.abs(worldY()-goalY))<=tolerance){neutral();waypoint=null;return true;}
  int[] dist=reachable();
  boolean inScene=gx>=EDGE&&gy>=EDGE&&gx<w-EDGE&&gy<h-EDGE;
  if(inScene){ // a direct route may exist
   int[] toGoal=distances(gx,gy,tolerance);if(now>directBanUntil&&toGoal[sceneX()*h+sceneY()]!=Integer.MAX_VALUE)return guardedTravel(goalX,goalY,tolerance,label);
   try{if(openToward(gx,gy,dist))return false;}catch(Exception ex){throw new IllegalStateException(ex);}
  }
  if(waypoint==null||now-waypointAt>9000||Math.max(Math.abs(sceneX()-waypoint[0]),Math.abs(sceneY()-waypoint[1]))<=1){
   double best=Double.MAX_VALUE;int bx=-1,by=-1;
   for(int x=EDGE;x<w-EDGE;x++)for(int y=EDGE;y<h-EDGE;y++){int d=dist[x*h+y];if(d==Integer.MAX_VALUE||d>70)continue;
    double score=Math.hypot(x-gx,y-gy)+7.0*seenBlocks.getOrDefault(block(x+za_Sub2.regionTileX,y+Class90.regionTileY),0)+(d<4?20:0);
    if(score<best){best=score;bx=x;by=y;}}
   if(bx<0){neutral();return false;}
   waypoint=new int[]{bx,by};waypointAt=now;int wc=(Integer)results.getOrDefault("walk_waypoints",0)+1;results.put("walk_waypoints",wc);
   if(wc==40||wc==100)dumpMap(dist,gx,gy,wc);
  }
  return guardedTravel(waypoint[0]+za_Sub2.regionTileX,waypoint[1]+Class90.regionTileY,0,label);
 }
 private static long directBanUntil;
 /** ASCII picture of what the client's collision map lets the player reach: debugging aid for long walks. */
 private static void dumpMap(int[] dist,int gx,int gy,int n){
  try{int w=Class367_Sub4.anInt7319,h=Class348_Sub40_Sub3.anInt9109;StringBuilder o=new StringBuilder("player scene "+sceneX()+","+sceneY()+" world "+worldX()+","+worldY()+" goal scene "+gx+","+gy+" (x right, y up)\n");
   for(int y=h-1;y>=0;y--){for(int x=0;x<w;x++){char c=dist[x*h+y]!=Integer.MAX_VALUE?'.':'#';if(x==sceneX()&&y==sceneY())c='P';else if(x==gx&&y==gy)c='G';o.append(c);}o.append('\n');}
   Files.write(Paths.get(probeMarker+".walkmap"+n+".txt"),o.toString().getBytes("UTF-8"));}catch(Exception ignored){}
 }
 /** Varrock to Taverley the way a traveller would go: Barbarian Village, round Falador's north-east, then the road west. */
 private static final int[][] TAVERLEY_ROAD={{3080,3420},{3030,3392},{2990,3376},{2965,3378},{2940,3379},{2925,3392},{2905,3412},{2905,3440},{2920,3470},{2925,3483}};
 private static int routeIndex;private static long routeAt;
 private static boolean walkVia(int[][] route,String label){
  long now=System.currentTimeMillis();if(routeAt==0)routeAt=now;
  // start from the leg nearest the goal that is not already behind us
  int[] w=route[routeIndex];
  boolean last=routeIndex==route.length-1;
  if(walkTo(w[0],w[1],last?2:4,label+" (leg "+(routeIndex+1)+"/"+route.length+")")){if(last){return true;}routeIndex++;routeAt=now;results.put("route_legs_done",routeIndex);timeline.add("reached road waypoint "+w[0]+","+w[1]);waypoint=null;return false;}
  if(now-routeAt>420_000){timeline.add("gave up on road waypoint "+w[0]+","+w[1]+" at "+worldX()+","+worldY());dumpMap(reachable(),w[0]-za_Sub2.regionTileX,w[1]-Class90.regionTileY,500+routeIndex);routeIndex=Math.min(routeIndex+1,route.length-1);routeAt=now;waypoint=null;}
  return false;
 }
 private static final Map<Long,Integer> doorTries=new HashMap<>();private static long doorAt,doorReset;
 /** Closed doors and gates are not on the collision map as passable; open the one nearest the goal that we can reach. */
 private static boolean openToward(int gx,int gy,int[] dist)throws Exception{
  long now=System.currentTimeMillis();int h=Class348_Sub40_Sub3.anInt9109;
  if(now-doorReset>40_000){doorReset=now;doorTries.clear();} // gates swing shut again
  boolean guards=false;for(ControllerTarget t:candidates())if(t.name.contains("Border Guard"))guards=true;
  ControllerTarget best=null;double bestScore=Double.MAX_VALUE;
  for(ControllerTarget t:candidates()){
   if(!t.option.equalsIgnoreCase("Open")||(guards&&t.name.equals("Gate")&&Math.abs(worldX()-3267)<12))continue;
   long key=((long)(t.x+za_Sub2.regionTileX)<<32)|(t.y+Class90.regionTileY);if(doorTries.getOrDefault(key,0)>=3)continue;
   int near=Integer.MAX_VALUE;for(int dx=-1;dx<=t.width;dx++)for(int dy=-1;dy<=t.height;dy++){int x=t.x+dx,y=t.y+dy;if(x<0||y<0||x*h+y>=dist.length)continue;near=Math.min(near,dist[x*h+y]);}
   if(near==Integer.MAX_VALUE)continue;
   double score=Math.hypot(t.x-gx,t.y-gy)+near*0.3;if(score<bestScore){bestScore=score;best=t;}
  }
  if(best==null)return false;
  long key=((long)(best.x+za_Sub2.regionTileX)<<32)|(best.y+Class90.regionTileY);
  int dist1=Math.max(Math.abs(best.x-sceneX()),Math.abs(best.y-sceneY()));
  if(dist1>1){guardedTravel(best.x+za_Sub2.regionTileX,best.y+Class90.regionTileY,1,"closed "+best.name);return true;}
  if(now-doorAt<2500){neutral();return true;}
  if(press(best.name,"Open",A)!=null){doorAt=now;doorTries.merge(key,1,Integer::sum);timeline.add("opened "+best.name+" at "+(best.x+za_Sub2.regionTileX)+","+(best.y+Class90.regionTileY));fieldKey="";}
  return true;
 }
 /** travel(), but a stuck report penalises this spot and picks another waypoint instead of failing the run. */
 private static boolean guardedTravel(int wx,int wy,int tol,String label){
  try{return travel(wx,wy,tol,label);}
  catch(IllegalStateException ex){
   if(!String.valueOf(ex.getMessage()).startsWith("Stuck"))throw ex;
   stuckCount++;results.put("walk_stuck_recoveries",stuckCount);require(stuckCount<40,"Too many stuck recoveries: "+ex.getMessage());
   seenBlocks.merge(block(worldX(),worldY()),5,Integer::sum);waypoint=null;directBanUntil=System.currentTimeMillis()+25_000;lastMoveAt=System.currentTimeMillis();lastTileX=-1;neutral();timeline.add("stuck at "+worldX()+","+worldY()+" while walking to "+label+(stuckCount<=2?": "+ex.getMessage():""));return false;}
 }
 private static long lastVictim=-1;private static boolean resting;private static long restAt;private static int restX,restY,restCount;
 private static String huntDiag="",lootDebug="";private static int lootFails;private static long lootBanUntil;private static int lootSub;private static long lootAt,huntPressAt;private static int lootBefore;
 /** X opens the pile, D-pad finds the wanted entry, A takes it. True once the count rose. */
 private static boolean pickUp(String item)throws Exception{
  long now=System.currentTimeMillis();ControllerTarget pile=nearest(item,"Take");
  switch(lootSub){
   case 0:{if(pile==null)return false;
    if(Math.max(Math.abs(pile.x-sceneX()),Math.abs(pile.y-sceneY()))>1){walkTo(pile.x+za_Sub2.regionTileX,pile.y+Class90.regionTileY,1,item);return false;}
    int n=count(item);if(n<0)return false;lootBefore=n;
    pileTile=new int[]{pile.x,pile.y}; // the pile's focus may name another item in it (feathers, bones)
    if(find(item,"Take")!=null&&press(item,"Take",X)!=null){lootSub=1;lootAt=now;}return false;}
   case 1:{ControllerTarget[] menu=world.getMenu();
    pileTile=null;if(menu.length==0){if(now-lootAt>2500){lootSub=0;}neutral();return false;}
    int index=world.getMenuIndex(),want=-1;
    for(int i=0;i<menu.length;i++)if(menu[i].option.equalsIgnoreCase("Take")&&menu[i].name.toLowerCase(Locale.ROOT).contains(item.toLowerCase(Locale.ROOT)))want=i;
    if(want<0){held=B;lootSub=0;return false;}
    if(index==want){held=A;lootSub=2;lootAt=now;StringBuilder e=new StringBuilder();for(ControllerTarget m:menu)e.append(m.name).append('/').append(m.option).append(", ");lootDebug="menu["+e+"] index="+index+" want="+want+" before="+lootBefore;return false;}
    held=held!=0?0:(want>index?DOWN:UP);return false;}
   default:{held=0;pileTile=null;int n=count(item);if(n>lootBefore){lootSub=0;results.put("picked_up_"+item.toLowerCase(Locale.ROOT).replace(' ','_'),n);return true;}
    if(now-lootAt>4000){lootSub=0;lootFails++;results.put("loot_failures",lootFails);results.put("loot_failure_last",lootDebug+" inventory="+inventory());lootBanUntil=now+20_000;}return false;}
  }
 }
 /**
  * Earned hunting: attack the nearest named animal, pick up the wanted drop when it appears, and keep going
  * until the item is held and the Hitpoints XP target is met. Eating is handled by the shared low-health step.
  */
 private static boolean hunt(String npc,String item,int needItems,int minHpXp,int anchorX,int anchorY)throws Exception{
  long now=System.currentTimeMillis();restX=anchorX-2;restY=anchorY-14;int have=count(item);if(have<0){neutral();return false;}
  boolean wantItem=have<needItems;
  if(wantItem&&(lootSub!=0||nearest(item,"Take")!=null&&now>=lootBanUntil)){if(pickUp(item))return false;if(lootSub!=0||nearest(item,"Take")!=null)return false;}
  if(!wantItem&&experience().get("Hitpoints")>=minHpXp){neutral();return true;}
  int[] reach=reachable();int rh=Class348_Sub40_Sub3.anInt9109;ControllerTarget victim=null;ControllerTarget fenced=null;int bestD=Integer.MAX_VALUE;
  for(ControllerTarget t:candidates()){if(!matches(t,npc,"Attack"))continue;
   int d=Math.max(Math.abs(t.x-sceneX()),Math.abs(t.y-sceneY()));if(d>16)continue;
   int steps=Integer.MAX_VALUE;Class361 fm=Class348_Sub45.aClass361Array7108[plane()];
   for(int dx=-1;dx<=t.width;dx++)for(int dy=-1;dy<=t.height;dy++){int x=t.x+dx,y=t.y+dy;if(x<0||y<0||x*rh+y>=reach.length||reach[x*rh+y]==Integer.MAX_VALUE)continue;
    // melee needs an unobstructed step from the standing tile onto the animal's tile (a fence between does not count)
    int sx=Integer.signum(t.x-x),sy=Integer.signum(t.y-y);if(sx==0&&sy==0)continue;if(Math.max(Math.abs(t.x-x),Math.abs(t.y-y))!=1)continue;
    if(WorldInput.canStep(fm.anIntArrayArray4438,x-fm.anInt4453,y-fm.anInt4441,sx,sy))steps=Math.min(steps,reach[x*rh+y]);}
   if(steps<=24){if(steps<bestD){bestD=steps;victim=t;}}else if(fenced==null)fenced=t;}
  if(victim==null){ // behind a fence or gate: open the nearest way in, else go to the usual ground
   if(fenced!=null&&openToward(fenced.x,fenced.y,reach))return false;
   walkTo(anchorX,anchorY,4,"hunting ground for "+npc);return false;}
  huntDiag="victim="+victim.x+","+victim.y+" me="+sceneX()+","+sceneY()+" steps="+bestD+" fenced="+(fenced!=null);
  if(bestD>2&&phase==0){guardedTravel(victim.x+za_Sub2.regionTileX,victim.y+Class90.regionTileY,1,npc);return false;} // walk up to it ourselves; the server will not path around fences
  if(phase==0&&victim.identifier==lastVictim&&now-huntPressAt<10000){neutral();return false;} // same animal: the fight is running
  if(press(npc,"Attack",A)!=null){huntPressAt=now;lastVictim=victim.identifier;if(!shot&&(Integer)results.getOrDefault(npc.toLowerCase(Locale.ROOT).replace(' ','_')+"_attacks",0)==8){shot=true;screenshot(".hunt.png");}results.put(npc.toLowerCase(Locale.ROOT).replace(' ','_')+"_attacks",(Integer)results.getOrDefault(npc.toLowerCase(Locale.ROOT).replace(' ','_')+"_attacks",0)+1);}
  return false;
 }

 // ---- earned supplies: chop, light, cook through native item-use ----
 private static UiState.Widget invItem(String name){for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.itemId>=0&&w.name.equalsIgnoreCase(name))return w;return null;}
 private static boolean useItem(UiState.Widget w,int type){for(UiState.Action a:w.actions)if(a.type==type)return ControllerUi.invoke(w,a);return false;}
 /** With an item selected every target's option reads "Use <item> →"; match both forms. */
 private static ControllerTarget nearestUse(String name)throws Exception{
  ControllerTarget best=null;int bd=Integer.MAX_VALUE;
  for(ControllerTarget t:candidates())if(t.name.toLowerCase(Locale.ROOT).contains(name.toLowerCase(Locale.ROOT))&&(t.option.equalsIgnoreCase("Use")||t.option.startsWith("Use "))){int d=Math.max(Math.abs(t.x-sceneX()),Math.abs(t.y-sceneY()));if(d<bd){bd=d;best=t;}}
  return best;
 }
 private static boolean relighting;private static int cookRaw;private static long toolAt;private static int[] spot;
 private static boolean chopLogs(int hx,int hy,int need)throws Exception{
  long now=System.currentTimeMillis();int logs=count("Logs");if(logs<0){neutral();return false;}if(logs>=need){neutral();return true;}
  ControllerTarget tree=null;int td=Integer.MAX_VALUE;
  for(ControllerTarget t:candidates())if(t.option.equals("Chop down")&&(t.name.equals("Tree")||t.name.equals("Dead tree"))){int d=Math.max(Math.abs(t.x-sceneX()),Math.abs(t.y-sceneY()));if(d<td){td=d;tree=t;}}
  if(tree==null){walkTo(hx,hy,2,"a tree");return false;}
  if(Math.max(Math.abs(tree.x-sceneX()),Math.abs(tree.y-sceneY()))>2){guardedTravel(tree.x+za_Sub2.regionTileX,tree.y+Class90.regionTileY,1,"tree");return false;}
  if(phase==0&&now-toolAt<8000){neutral();return false;}
  if(press(tree.name,"Chop down",A)!=null)toolAt=now;return false;
 }
 private static boolean lightFire()throws Exception{
  long now=System.currentTimeMillis();
  if(nearest("Fire","Use")!=null){neutral();results.put("fire_target","Fire/Use");return true;}
  if(now-toolAt<2500){neutral();return false;}
  UiState state=ControllerUi.snapshot(true);if(!state.inventoryVisible){count("Logs");return false;}
  // fires cannot be lit on a tile holding items (feathers, bones, eggs) or an object: walk to a bare one first
  boolean occupied=false;if(sub==0)for(ControllerTarget t:candidates())if(t.option.startsWith("Use")==false&&t.x<=sceneX()&&sceneX()<t.x+t.width&&t.y<=sceneY()&&sceneY()<t.y+t.height&&!t.option.equals("Examine"))occupied=true;
  if(occupied||spot!=null){
   if(spot==null){int[] reach=reachable();int h=Class348_Sub40_Sub3.anInt9109;int bd=Integer.MAX_VALUE;
    for(int x=EDGE;x<Class367_Sub4.anInt7319-EDGE;x++)for(int y=EDGE;y<h-EDGE;y++){int d=reach[x*h+y];if(d==Integer.MAX_VALUE||d<2||d>8||d>=bd)continue;
     boolean busy=false;for(ControllerTarget t:candidates())if(Math.max(Math.abs(t.x-x),Math.abs(t.y-y))<=0)busy=true;if(!busy){bd=d;spot=new int[]{x,y};}}
    if(spot==null){neutral();return false;}}
   if(sceneX()==spot[0]&&sceneY()==spot[1]){spot=null;neutral();toolAt=now;return false;}
   guardedTravel(spot[0]+za_Sub2.regionTileX,spot[1]+Class90.regionTileY,0,"a bare tile for the fire");return false;
  }
  if(sub==0){UiState.Widget box=invItem("Tinderbox");if(box!=null&&useItem(box,13)){toolAt=now;sub=1;timeline.add("tinderbox selected");}return false;}
  UiState.Widget log=invItem("Logs");if(log==null){sub=0;timeline.add("logs not in the inventory view");return false;}
  StringBuilder acts=new StringBuilder();for(UiState.Action a:log.actions)acts.append(a.label).append(':').append(a.type).append(' ');
  if(!useItem(log,6)){timeline.add("logs offer no item-on-item action: "+acts);toolAt=now;sub=0;ControllerUi.cancelWorld();return false;}
  if(true){toolAt=now+9000;sub=0;timeline.add("tinderbox used on logs");}return false;
 }
 private static boolean cookAll(String raw,String cooked)throws Exception{
  long now=System.currentTimeMillis();int n=count(raw);if(n<0){neutral();return false;}
  if(n<=1){neutral();return true;} // the last raw chicken is the quest's
  if(now-toolAt<2500){neutral();return false;}
  if(cookRaw>0&&n>=cookRaw&&now-toolAt<9000){neutral();return false;} // let the cook finish before selecting again
  cookRaw=0;
  ControllerTarget fire=nearestUse("Fire");
  if(fire==null&&results.containsKey("cook_uses")){ // fires are short-lived: light the next log
   int logs=count("Logs");if(logs<0)return false;
   if(logs==0){ControllerUi.cancelWorld();results.put("fire_burnt_out_after_cooks",results.get("cook_uses"));return true;}
   if(!relighting){ControllerUi.cancelWorld();relighting=true;sub=0;toolAt=now;return false;}
   if(lightFire()){relighting=false;results.put("fires_lit",(Integer)results.getOrDefault("fires_lit",1)+1);}return false;}
  relighting=false;
  if(fire==null){throw new IllegalStateException("The fire went out before cooking finished (sub="+sub+", cook uses="+results.get("cook_uses")+", nearby="+nearby()+")");}
  if(Math.max(Math.abs(fire.x-sceneX()),Math.abs(fire.y-sceneY()))>1){guardedTravel(fire.x+za_Sub2.regionTileX,fire.y+Class90.regionTileY,1,"fire");return false;}
  if(sub==0){UiState.Widget w=invItem(raw);if(w!=null&&useItem(w,13)){toolAt=now;sub=1;timeline.add("selected "+raw+" next to fire "+fire.name+"/"+fire.option+"@"+fire.x+","+fire.y);}return false;}
  if(ControllerWorld.interact(fire)){timeline.add("used "+raw+" on "+fire.name);cookRaw=n;toolAt=now+4000;sub=0;results.put("cook_uses",(Integer)results.getOrDefault("cook_uses",0)+1);}else sub=0;return false;
 }
 /** Production menu (id 905): pick "all" and the first recipe, like the content probe. */
 private static boolean production()throws Exception{
  UiState state=ControllerUi.snapshot(true);if(state.dialogueId!=905)return false;
  long now=System.currentTimeMillis();if(now-lastDialogue<500)return true;lastDialogue=now;
  if(!results.containsKey("production_menu")){List<String> labels=new ArrayList<>();for(UiState.Widget row:state.dialogue)labels.add((row.id&65535)+":"+row.name+" / "+(row.actions.length>0?row.actions[0].label:"-"));for(UiState.Widget row:state.amounts)labels.add("amount "+(row.id&65535)+":"+row.name+" / "+(row.actions.length>0?row.actions[0].label:"-"));timeline.add("production menu "+labels+" amount="+state.amount);results.put("production_menu","seen");}
  if(state.amount!=1)for(UiState.Widget w:state.amounts)if((w.id&65535)==5&&w.actions.length>0){ControllerUi.invoke(w,w.actions[0]);return true;}
  for(UiState.Widget w:state.dialogue)if((w.id&65535)==14&&w.actions.length>0){ControllerUi.invoke(w,w.actions[0]);return true;}
  return true;
 }
 private static long devGrace;
 private static final int DEV_STAGE=Integer.getInteger("soloscape.druidic.devStage",0);
 private static void devFixture(){
  String[][] steps={{"6","tele 3231 3296 0"},{"8","tele 3231 3296 0","item raw_chicken 7","item logs 2"},
   {"11","tele 3260 3345 0","item raw_beef 1","item raw_chicken 1","item cooked_chicken 4"},{"150","tele 2981 3467 0","item raw_beef 1","item raw_chicken 1","item raw_rat_meat 1","item raw_bear_meat 1"},{"15","tele 3292 3335 0","item raw_beef 1","item raw_chicken 1","item raw_rat_meat 1","item raw_bear_meat 1"}};
  for(String[] f:steps)if(Integer.parseInt(f[0])==DEV_STAGE){for(int i=1;i<f.length;i++)Class82.method812(f[i],false,false,(byte)-79);}
  results.put("DEV_FIXTURE","debug start at stage "+DEV_STAGE+" with admin teleport/items: NOT an earned-route result");stage=DEV_STAGE==150?15:DEV_STAGE;limit(3_600_000);phase=0;sub=0;stageAt=System.currentTimeMillis();devGrace=stageAt+8000;
 }
 private static int journalStage(){return DRUIDIC?27:31;}
 private static void limit(long ms){stageLimit=ms;}
 private static void druidic(long now)throws Exception{
  if(now>devGrace&&stage>=3&&!instanced()&&plane()==0&&Math.abs(worldX()-3221)<3&&Math.abs(worldY()-3219)<3)throw new IllegalStateException("Player died and respawned at Lumbridge");
  if(resting){ // out of food and nearly dead: step back from the animals and let health regenerate
   if(hp()>=9||now-restAt>150_000){resting=false;timeline.add("rested to "+hp());}
   else{if(walkTo(restX,restY,2,"a rest spot"))neutral();return;}
  }else if(hp()>0&&hp()<=3&&stage>=3){resting=true;restAt=now;restCount++;results.put("rests",restCount);timeline.add("resting at constitution "+hp()+" with no food");return;}
  switch(stage){
   case 1:{
    if(sub==0){ControllerUi.openInventory();sub(1);neutral();return;}
    neutral();UiState.Widget sword=null;for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.name.equalsIgnoreCase("Bronze sword"))sword=w;
    if(sword==null){if(count("Bronze sword")==0&&now-subAt>1500){ControllerUi.cancelWorld();next("wielded bronze sword");limit(600_000);if(DEV_STAGE>0)devFixture();}return;}
    if(now-lastPress>800)for(UiState.Action action:sword.actions)if(action.label.equalsIgnoreCase("Wield")){lastPress=now;ControllerUi.invoke(sword,action);subAt=now;}
    return;}
   case 2:if(walkTo(3254,3266,3,"Lumbridge cow field")){next("reached cow field");limit(2_400_000);}return;
   case 3:if(hunt("Cow","Raw beef",1,HP_XP_GOAL,3256,3262)){results.put("hp_xp_after_cows",experience().get("Hitpoints"));next("raw beef held and trained on cows");limit(900_000);}return;
   case 4:if(walkTo(3259,3252,2,"the trees beside the cow field")){next("reached trees");limit(600_000);}return;
   case 5:if(chopLogs(3259,3252,2)){next("logs chopped");limit(900_000);}return;
   case 6:if(walkTo(3231,3296,3,"Lumbridge chickens")){next("reached chickens");limit(900_000);}return;
   case 7:if(hunt("Chicken","Raw chicken",7,0,3231,3298)){next("seven raw chickens held (six to cook as food)");limit(300_000);}return;
   case 8:if(lightFire()){next("player-lit fire burning");limit(900_000);}return;
   case 9:if(cookAll("Raw chicken","Cooked chicken")){results.put("cooked_chicken_held",Math.max(0,count("Cooked chicken")));results.put("raw_chicken_left_for_quest",Math.max(0,count("Raw chicken")));next("chickens cooked on the player's fire");limit(900_000);}return;
   case 10:if(hunt("Chicken","Raw chicken",1,0,3231,3298)){next("quest raw chicken held");limit(900_000);}return;
   case 11:if(walkTo(3260,3345,3,"giant rats east of Varrock")){next("reached giant rats");limit(900_000);}return;
   case 12:if(hunt("Giant rat","Raw rat meat",1,0,3260,3351)){next("raw rat meat held");limit(900_000);}return;
   case 13:if(walkTo(3294,3345,3,"black bear east of Varrock")){next("reached black bear");limit(1_800_000);}return;
   case 14:if(hunt("Black bear","Raw bear meat",1,0,3296,3347)){results.put("hp_after_bear_xp",experience().get("Hitpoints"));next("raw bear meat held");limit(3_600_000);}return;
   case 15:if(walkVia(TAVERLEY_ROAD,"Kaqemeex at the Taverley stone circle")){next("reached Kaqemeex");limit(300_000);}return;
   case 16:{preferred=new String[]{"I'm in search of a quest.","Yes."};
    if(conversed&&!ControllerUi.hasDialogue()&&now-lastDialogue>2500){next("started Druidic Ritual");return;}
    if(!conversed&&press("Kaqemeex","Talk-to",A)!=null)results.put("kaqemeex_target_focus","Kaqemeex/Talk-to");return;}
   case 17:if(walkTo(2897,3423,2,"Sanfew's house")){next("reached Sanfew's house");limit(300_000);}return;
   case 18:{
    if(plane()==1){next("upstairs with Sanfew");return;}
    if(now-lastPress>2500&&press("","Climb-up",A)!=null)lastPress=now;
    else if(nearest("","Climb-up")==null&&now-stageAt>20000)throw new IllegalStateException("No staircase in sight: "+nearby());
    return;}
   case 19:{preferred=new String[]{"I've been sent to help purify the Varrock stone circle.","Ok, I'll do that then."};
    if(conversed&&!ControllerUi.hasDialogue()&&now-lastDialogue>2500){next("Sanfew explained the ritual");return;}
    if(!conversed&&press("Sanfew","Talk-to",A)!=null)results.put("sanfew_target_focus","Sanfew/Talk-to");return;}
   case 20:{if(plane()==1){if(now-lastPress>2500&&press("","Climb-down",A)!=null)lastPress=now;return;}
    if(walkTo(2884,3399,1,"Taverley dungeon entrance")){next("at the dungeon ladder");}return;}
   case 21:{if(plane()==0&&worldY()>9000){next("in Taverley Dungeon");return;}
    if(now-lastPress>2500&&press("","Climb-down",A)!=null)lastPress=now;return;}
   case 22:if(walkTo(2893,9829,1,"Cauldron of Thunder")){next("at the Cauldron of Thunder");limit(600_000);}return;
   case 23:{ // each raw meat is dipped on its own: select it, then use it on the cauldron
    String[][] meats={{"Raw beef","Enchanted beef"},{"Raw rat meat","Enchanted rat meat"},{"Raw bear meat","Enchanted bear meat"},{"Raw chicken","Enchanted chicken"}};
    if(now-toolAt<2500){neutral();return;}
    if(sub>=4){results.put("druidic_meats_enchanted",4);next("all four meats enchanted");return;}
    int raw=count(meats[sub][0]),done=count(meats[sub][1]);if(raw<0||done<0)return;
    if(raw==0&&done>=1){sub=sub+1;toolAt=now;phase=0;return;}
    if(phase==0){UiState.Widget w=invItem(meats[sub][0]);if(w!=null&&useItem(w,13)){phase=1;toolAt=now;}return;}
    ControllerTarget cauldron=nearestUse("Cauldron of Thunder");
    if(cauldron==null){ControllerUi.cancelWorld();phase=0;require(now-stageAt<120_000,"No Cauldron of Thunder in reach: "+nearby());return;}
    if(Math.max(Math.abs(cauldron.x-sceneX()),Math.abs(cauldron.y-sceneY()))>2){ControllerUi.cancelWorld();phase=0;guardedTravel(cauldron.x+za_Sub2.regionTileX,cauldron.y+Class90.regionTileY,1,"cauldron");return;}
    if(ControllerWorld.interact(cauldron)){toolAt=now+1500;phase=0;results.put("cauldron_uses",(Integer)results.getOrDefault("cauldron_uses",0)+1);}return;}
   case 24:{ // back up the ladder
    if(plane()==0&&worldY()<9000){next("out of the dungeon");return;}
    if(now-lastPress>2500&&press("","Climb-up",A)!=null)lastPress=now;
    else if(nearest("","Climb-up")==null)walkTo(2884,9798,2,"the way out");
    return;}
   case 25:{ // hand the enchanted meats to Sanfew (the stairs again)
    preferred=new String[]{"Yes, I have all four now!"};
    if(plane()==0){if(walkTo(2897,3423,2,"Sanfew's house")){if(now-lastPress>2500&&press("","Climb-up",A)!=null)lastPress=now;}return;}
    if(conversed&&!ControllerUi.hasDialogue()&&now-lastDialogue>2500){
     int e=count("Enchanted beef")+count("Enchanted rat meat")+count("Enchanted bear meat")+count("Enchanted chicken");
     if(e<0)return;require(e==0,"Sanfew kept "+e+" meat(s) uncounted");results.put("druidic_meats_handed_in",4);next("Sanfew took the meats");return;}
    if(!conversed&&press("Sanfew","Talk-to",A)!=null)results.put("sanfew_hand_in_focus","Sanfew/Talk-to");return;}
   case 26:{ // Kaqemeex pays the reward
    if(plane()==1){if(now-lastPress>2500&&press("","Climb-down",A)!=null)lastPress=now;return;}
    if(!results.containsKey("quest_complete_panel")){
     if(walkTo(2925,3483,2,"Kaqemeex")){if(!conversed&&press("Kaqemeex","Talk-to",A)!=null)results.put("kaqemeex_reward_focus","Kaqemeex/Talk-to");}return;}
    if(!ControllerUi.hasModalPanel()&&now-lastDialogue>2500){next("quest complete panel shown");}return;}
   case 27:journal(now);return;
   default:
  }
 }

 // ---- top-level ----
 public static boolean tick(String marker)throws Exception{
  GameClient client=client();
  if(stage==0){
   ConfigManager config=RuneLite.getInjector().getInstance(ConfigManager.class);
   config.setConfiguration("soloscapecontroller","setupComplete",true);config.setConfiguration("soloscapecontroller","showMovementTiles",true);
   for(net.runelite.client.plugins.Plugin candidate:RuneLite.getInjector().getInstance(net.runelite.client.plugins.PluginManager.class).getPlugins())if(candidate instanceof SoloScapeControllerPlugin)plugin=(SoloScapeControllerPlugin)candidate;
   require(plugin!=null,"Controller plugin missing");
   failed=SoloScapeControllerPlugin.class.getDeclaredField("failed");failed.setAccessible(true);failed.setBoolean(plugin,true); // pause SDL polling only
   process=SoloScapeControllerPlugin.class.getDeclaredMethod("processInput",long.class);process.setAccessible(true);
   Field f=SoloScapeControllerPlugin.class.getDeclaredField("rawState");f.setAccessible(true);raw=(GamepadState)f.get(plugin);
   f=SoloScapeControllerPlugin.class.getDeclaredField("world");f.setAccessible(true);world=(WorldControls)f.get(plugin);
   RuneLite.getInjector().getInstance(OverlayManager.class).add(observation);
   started=System.currentTimeMillis();probeMarker=marker;
   results.put("fixtures","none: no admin commands, item grants, teleports or injected damage");
   results.put("cultist_choices","Kayle: "+(KILL_KAYLE?"kill":"spare")+", Caitlin: "+(KILL_CAITLIN?"kill":"spare")+", Reese: "+(SPARE_REESE?"offer mercy (he still dies)":"kill"));
   results.put("route_variant",MAGIC?"magic: starter runes, staff, autocast Wind Strike against Reese":"melee Reese");
   results.put("start_tile",worldX()+","+worldY()+","+plane());results.put("start_experience",experience());
   results.put("start_inventory",inventory());
   next("setup");
   RuneLite.getInjector().getInstance(net.runelite.client.eventbus.EventBus.class).register(LISTENER);return false;
  }
  Files.write(Paths.get(marker+".bloodpact.status"),status().getBytes("UTF-8"));
  if((failure!=null||stage==DONE)&&!unregistered){
   unregistered=true;RuneLite.getInjector().getInstance(net.runelite.client.eventbus.EventBus.class).unregister(LISTENER);
   RuneLite.getInjector().getInstance(OverlayManager.class).remove(observation);failed.setBoolean(plugin,false);
   results.put("timeline",timeline);
   Files.write(Paths.get(marker+".bloodpact.json"),new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(results).getBytes("UTF-8"));
  }
  if(failure!=null)throw new IllegalStateException("Blood Pact probe failed at stage "+stage+" phase "+phase+": "+status(),failure);
  if(stage==DONE)System.out.println("Native Blood Pact: earned controller-only quest completion passed.");
  return stage==DONE;
 }
 private static String readiness(){
  Player p=me();
  return "state="+Class240.anInt4674+" size="+p.method2436((byte)70)+" camera="+Class348_Sub40_Sub21.anInt9282+" sel="+r.aBoolean9722+" menu="+Class305.aBoolean3870+" dialogue="+ControllerUi.hasDialogue()+" modal="+ControllerUi.hasModalPanel()+" entry="+ControllerEntry.active();
 }
 private static String nearby(){
  try{if(me()==null)return "";Set<String> seen=new LinkedHashSet<>();for(ControllerTarget t:candidates())if(DRUIDIC&&stage>=5&&stage<=10?!t.option.equals("Examine"):(t.kind()==1||t.kind()==3))seen.add(t.name+"/"+t.option+"@"+(t.x-sceneX())+","+(t.y-sceneY()));return seen.toString();}catch(Exception ex){return "?";}
 }
 private static String inventory(){if(!ControllerUi.snapshot(true).inventoryVisible)return "(inventory tab closed)";StringBuilder s=new StringBuilder();for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.itemId>=0)s.append(w.name).append(w.quantity>1?" x"+w.quantity:"").append("; ");return s.toString();}
 private static String status(){
  ControllerTarget shown=world==null?null:world.getTarget();
  return "stage="+stage+" phase="+phase+" tile="+(me()==null?"?":worldX()+","+worldY()+","+plane())+" instanced="+(me()!=null&&instanced())+" offset="+offX+","+offY
   +" ready="+ControllerWorld.ready()+" hp="+hp()+(DRUIDIC?" xp="+experience().get("Hitpoints")+"/"+experience().get("Attack")+" attacks="+results.getOrDefault("cow_attacks",0)+" "+huntDiag+" lootSub="+lootSub+" fails="+lootFails+" "+lootDebug+" last="+results.getOrDefault("loot_failure_last","")+" waypoints="+results.getOrDefault("walk_waypoints",0):"")+" target="+(shown==null?"none":shown.name+"/"+shown.option)+" menu="+(world==null?0:world.getMenu().length)
   +" dialogue="+ControllerUi.hasDialogue()+" modal="+ControllerUi.hasModalPanel()+" nearby="+nearby()+" travel="+travelDiag+" timeline="+timeline;
 }

 public static final class Listener {
  @net.runelite.client.eventbus.Subscribe(priority=-1000) public void onClientTick(net.runelite.api.events.ClientTick event){
   if(stage<1||stage>=DONE||failure!=null)return;
   try{step();input();}catch(Throwable error){failure=error;}
  }
 }
 private static final Listener LISTENER=new Listener();

 private static void step()throws Exception{
  long now=System.currentTimeMillis();
  require(now-stageAt<stageLimit,"Stage timed out");
  Canvas canvas=client().getCanvas();
  if(!canvas.isFocusOwner()){neutral();javax.swing.SwingUtilities.invokeLater(()->{Window owner=javax.swing.SwingUtilities.getWindowAncestor(canvas);if(owner!=null)owner.toFront();canvas.requestFocusInWindow();});return;}
  if(me()==null){neutral();return;}
  if(!ControllerWorld.ready()){lastNotReady=now;if(phase!=0)phase(0);notReady++;notReadyWhy.append(now-stageAt).append("ms:").append(readiness()).append(';');if(notReadyWhy.length()>1500)notReadyWhy.delete(0,notReadyWhy.length()-1500);}
  if(hp()>0)minHp=Math.min(minHp,hp());
  if(!DRUIDIC&&stage>=6&&stage<30&&!instanced()&&plane()==0&&Math.abs(worldX()-3221)<3&&Math.abs(worldY()-3219)<3)throw new IllegalStateException("Player died and respawned");
  // Modal UI first: dialogue makes the world deliberately not ready.
  if(DRUIDIC&&production()){neutral();return;}
  if(panels()||dialogue()){lastNotReady=now;if(phase!=0)phase(0);neutral();return;}
  if(hp()>0&&hp()<=4&&now-lastPress>2400&&(!DRUIDIC||stage>=14||hp()<=2)){
   if(eat()){lastPress=now;neutral();return;}
   if(instanced()&&find("Xenia","Talk-to")!=null&&!asked&&!healing){healing=true;phase(0);timeline.add("going to Xenia for food at constitution "+hp());}
  }
  if(healing){ // she shares food with wounded adventurers who carry none
   if(find("Xenia","Talk-to")==null&&!ControllerUi.hasDialogue()){healing=false;phase(0);return;}
   if(aimAndPress("Xenia","Talk-to",A)!=null){asked=true;healing=false;lastPress=now;phase(0);}
   return;
  }
  if(hp()>5)asked=false;
  if(DRUIDIC){druidic(now);return;}
  switch(stage){
   case 1:{ // wield the starter sword through the inventory gateway
    if(sub==0){ControllerUi.openInventory();sub(1);neutral();return;}
    neutral();UiState.Widget sword=null;for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.name.equalsIgnoreCase("Bronze sword"))sword=w;
    if(sword==null){if(count("Bronze sword")==0&&now-subAt>1500){ControllerUi.cancelWorld();results.put("wielded","Bronze sword");next("wielded bronze sword");}return;}
    if(now-lastPress>800)for(UiState.Action action:sword.actions)if(action.label.equalsIgnoreCase("Wield")){lastPress=now;ControllerUi.invoke(sword,action);subAt=now;}
    return;
   }
   case 2:{
    if(travel(3244,3199,2,"Xenia in Lumbridge cemetery"))next("walked to Xenia");return;}
   case 3:{preferred=new String[]{"What do you need help with?","I'll help you."};
    if(press("Xenia","Talk-to",A)!=null){results.put("xenia_target_focus","Xenia/Talk-to");next("talked to Xenia");}return;}
   case 4:if(now-stageAt>2500&&ControllerWorld.ready())next("quest accepted");return;
   case 5:if(press("","Climb-down",A)!=null)next("climbed down catacomb stairs");return;
   case 6:{ // the cutscene plays through ordinary Continue; it ends with us on the instance origin tile
    if(!instanced()||plane()!=1)return;
    int ox=Math.round((worldX()-3877)/64f)*64,oy=Math.round((worldY()-5527)/64f)*64; // instances are region aligned
    if(worldX()-ox!=3877||worldY()-oy!=5527||!ControllerWorld.ready()||now-stageAt<4000)return;
    offX=ox;offY=oy;
    results.put("instance_region_base",za_Sub2.regionTileX+","+Class90.regionTileY);results.put("instance_offset",offX+","+offY);
    observation.request(1);next("cutscene finished in instance");return;
   }
   case 7:{int[] t=instance(3877,5531);if(travel(t[0],t[1],0,"Kayle's doorway"))next("entered Kayle's room");return;}
   case 8:{int[] t=instance(3876,5528);if(worldX()==t[0]&&worldY()==t[1]&&ControllerWorld.ready()&&now-stageAt>3000)next("Xenia wounded");return;}
   case 9:{int[] t=instance(3877,5537);if(find("Kayle","Talk-to")!=null||travel(t[0],t[1],1,"Kayle's approach")){results.put("movement_tile_plane1_pixels",observation.pixels(1));next("approached Kayle");}return;}
   case 10:{ControllerTarget p=press("Kayle","Attack",A);if(p!=null||find("Kayle","Talk-to")!=null){results.put("kayle_target",p==null?"defeated by retaliation":p.name+"/"+p.option+" serverApproach="+p.serverApproach);observation.watch("Kayle");next("attacked Kayle");}return;}
   case 11:if(fight("Kayle")){results.put("kayle_health_hud",observation.health());results.put("hp_after_kayle",hp());next("Kayle defeated");}return;
   case 12:{preferred=new String[]{KILL_KAYLE?"Yes. Now die!":"give me your stuff"};if(talk("Kayle"))next(KILL_KAYLE?"killed Kayle":"spared Kayle");return;}
   case 13:if(loot("Kayle's sling",3877,5543,"kayle"))next("looted Kayle's sling");return;
   case 14:if(cancelWalk(3868,5540))next("B cancelled a walk");return;
   case 15:{if(sub==0){neutral();if(wield("Kayle's sling"))sub(1);return;} // Xenia: ranged beats magic users
    int[] t=instance(3868,5540);if(travel(t[0],t[1],1,"Caitlin's gallery"))next("approached Caitlin");return;}
   case 16:{ControllerTarget p=press("Caitlin","Attack",A);if(p!=null||find("Caitlin","Talk-to")!=null){results.put("caitlin_target",p==null?"defeated by retaliation":p.name+"/"+p.option);observation.watch("Caitlin");next("attacked Caitlin");}return;}
   case 17:if(fight("Caitlin")){results.put("caitlin_health_hud",observation.health());results.put("hp_after_caitlin",hp());next("Caitlin defeated");}return;
   case 18:if(walkThenPress(3871,5535,2,"","Operate"))next("operated winch: gallery gates open");return;
   case 19:{if(now-stageAt<1500)return;preferred=new String[]{KILL_CAITLIN?"Time for you to die!":"I'm not killing you"};if(talk("Caitlin"))next(KILL_CAITLIN?"killed Caitlin":"spared Caitlin");return;}
   case 20:if(loot("Caitlin's staff",3864,5538,"caitlin"))next("looted Caitlin's staff");return;
   case 21:if(now-stageAt>1500&&walkThenPress(3859,5533,2,"","Climb-down"))next("climbed down to Reese's level");return;
   case 22:{if(plane()!=0||!ControllerWorld.ready())return;if(sub==0){neutral();if(wield(MAGIC?"Caitlin's staff":"Bronze sword"))sub(MAGIC?2:1);return;}
    if(sub==2){neutral();if(autocast())sub(1);return;}
    observation.request(0);int[] t=instance(3866,5528);if(travel(t[0],t[1],1,"tomb door")){results.put("movement_tile_plane0_pixels",observation.pixels(0));next("reached tomb door");}return;}
   case 23:{preferred=new String[]{KILL_KAYLE!=KILL_CAITLIN?"I'm the one who":"I'm an adventurer"};if(press("","Open",A)!=null)next("opened tomb door");return;}
   case 24:{if(now-stageAt<2000||now-lastNotReady<1000){neutral();return;}if(!noteRunes())return;if(beforeReese==null)beforeReese=experience();ControllerTarget p=press("Reese","Attack",A);
    if(p!=null||find("Reese","Talk-to")!=null){results.put("reese_target",p==null?"defeated by retaliation":p.name+"/"+p.option);observation.watch("Reese");next("attacked Reese");}return;}
   case 25:{watchCasting();if(fight("Reese")){if(!magicEvidence())return;results.put("reese_health_hud",observation.health());results.put("hp_after_reese",hp());next("Reese defeated");}return;}
   case 26:{preferred=new String[]{SPARE_REESE?"I'm not killing you":"Time for you to die!"};if(talk("Reese"))next(SPARE_REESE?"offered Reese mercy; he drank poison":"killed Reese");return;}
   case 27:if(now-stageAt>3000&&loot("Reese's sword",3865,5525,"reese"))next("looted Reese's sword");return;
   case 28:{preferred=new String[]{"Yes, rescue Ilona."};if(walkThenPress(3864,5524,1,"Ilona","Untie"))next("untied Ilona");return;}
   case 29:{preferred=new String[]{"Yes, rescue Ilona.","I'm ready for my reward."};if(!instanced()&&ControllerWorld.ready()&&now-stageAt>3000)next("back on the surface");return;}
   case 30:{ // the quest's own Talk-to normally reaches the reward; otherwise ask Xenia like a player
    preferred=new String[]{"I'm ready for my reward."};
    if(results.containsKey("quest_complete_panel")){next("quest complete panel shown");return;}
    if(now-stageAt>6000&&now-lastPress>3000)press("Xenia","Talk-to",A);else neutral();return;}
   case 31:journal(now);return;
   default:
  }
 }
 /** Wields an inventory item through the native inventory gateway; true once it has left the inventory. */
 private static boolean wield(String name){
  long now=System.currentTimeMillis();int n=count(name);
  if(n<0)return false;
  if(n==0){results.put("wielded_"+name.toLowerCase(Locale.ROOT).replace(' ','_').replace("'",""),true);return true;}
  if(now-lastPress<900)return false;
  for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.name.equalsIgnoreCase(name))for(UiState.Action a:w.actions)
   if(a.label.equalsIgnoreCase("Wield")||a.label.equalsIgnoreCase("Wear")){lastPress=now;ControllerUi.invoke(w,a);timeline.add("wield "+name);return false;}
  throw new IllegalStateException(name+" has no Wield action");
 }
 /** A press after a cooldown so repeated attempts look like a player pressing again. */
 private static ControllerTarget press(String name,String option,int button)throws Exception{
  if(phase==0&&System.currentTimeMillis()-lastPress<1200){neutral();return null;}
  ControllerTarget pressed=aimAndPress(name,option,button);if(pressed!=null)lastPress=System.currentTimeMillis();return pressed;
 }
 private static boolean walkThenPress(int x,int y,int tolerance,String name,String option)throws Exception{
  if(sub==0){int[] t=instance(x,y);if(!travel(t[0],t[1],tolerance,option+" "+name))return false;sub(1);}
  return press(name,option,A)!=null;
 }
 /** Earned combat; press Attack again if the fight stalls, as a player would. */
 private static boolean fight(String name)throws Exception{
  if(find(name,"Talk-to")!=null)return true;
  if(System.currentTimeMillis()-subAt>8000&&find(name,"Attack")!=null){if(press(name,"Attack",A)!=null){represses++;results.put("attack_represses",represses);subAt=System.currentTimeMillis();}}else neutral();
  return false;
 }
 private static boolean eat(){
  for(String food:new String[]{"Shrimps","Bread","Cooked meat","Cooked chicken"})for(UiState.Widget w:ControllerUi.snapshot(true).inventory)if(w!=null&&w.name.equalsIgnoreCase(food))for(UiState.Action a:w.actions)if(a.label.equalsIgnoreCase("Eat")&&ControllerUi.invoke(w,a)){meals++;results.put("meals",meals);timeline.add("ate "+food+" at constitution "+hp());return true;}
  return false;
 }
 private static boolean talk(String name)throws Exception{
  // Once the conversation opened, the quest's fade removes the cultist a few ticks later; don't interrupt it.
  if(conversed&&attempts>0){neutral();return find(name,"Talk-to")==null&&find(name,"Attack")==null&&ControllerWorld.ready();}
  // Walk up to the cultist first; Talk-to is only offered nearby and within a short path.
  ControllerTarget npc=find(name,"Talk-to");
  if(npc!=null&&phase==0&&Math.max(Math.abs(npc.x-sceneX()),Math.abs(npc.y-sceneY()))>1&&!travel(npc.x+za_Sub2.regionTileX,npc.y+Class90.regionTileY,1,name))return false;
  // A just-defeated cultist settles out of combat for a few ticks; press A again like a player would.
  if(press(name,"Talk-to",A)!=null){attempts++;conversed=false;results.put(name.toLowerCase(Locale.ROOT)+"_talk_presses",attempts);require(attempts<=20,"Talk-to never opened for "+name);}
  return false;
 }
 /** X opens the whole pile, D-pad browses, B backs out without taking; then X again, focus Take and A. */
 private static boolean loot(String item,int x,int y,String key)throws Exception{
  long now=System.currentTimeMillis();ControllerTarget[] menu=world.getMenu();
  switch(sub){
   case 0:{int[] t=instance(x,y);if(travel(t[0],t[1],1,item)&&count(item)==0)sub(1);return false;}
   case 1:if(press(item,"Take",X)!=null)sub(2);return false;
   case 2:{
    if(menu.length==0){require(now-subAt<2000,"X did not open the loot pile for "+item);neutral();return false;}
    List<String> entries=new ArrayList<>();for(ControllerTarget m:menu){require(m.kind()==3&&m.x==menu[0].x&&m.y==menu[0].y,"Loot menu mixed in a non-pile entry");entries.add(m.name+"/"+m.option);}
    results.put(key+"_loot_pile_menu",entries);results.put(key+"_menu_index_before",world.getMenuIndex());held=DOWN;sub(3);return false;}
   case 3:held=0;if(now-subAt>200){results.put(key+"_menu_index_after_down",world.getMenuIndex());held=B;sub(4);}return false;
   case 4:held=0;if(now-subAt>800){
    if(count(item)<0)return false;require(world.getMenu().length==0,"B did not close the loot pile menu");require(count(item)==0,"B took the item");
    require(find(item,"Take")!=null,"Pile vanished after B");results.put(key+"_loot_menu_b_closed_without_taking",true);sub(5);}return false;
   case 5:if(press(item,"Take",X)!=null)sub(6);return false;
   case 6:{
    if(menu.length==0){require(now-subAt<2000,"Second X did not reopen the loot pile");neutral();return false;}
    int index=world.getMenuIndex(),want=-1;
    for(int i=0;i<menu.length;i++)if(menu[i].option.equalsIgnoreCase("Take")&&menu[i].name.toLowerCase(Locale.ROOT).contains(item.toLowerCase(Locale.ROOT)))want=i;
    require(want>=0,"Take entry missing from loot pile");
    if(index==want){held=A;sub(7);results.put(key+"_take_from_offset",(menu[want].x-sceneX())+","+(menu[want].y-sceneY()));return false;}
    held=held!=0?0:(want>index?DOWN:UP);return false;}
   default:
    held=0;if(count(item)>0){results.put(key+"_looted",item);return true;}
    if(now-subAt>300&&!results.containsKey(key+"_take_feedback"))results.put(key+"_take_feedback",String.valueOf(world.feedback(System.nanoTime())));
    require(now-subAt<8000,"Take did not add "+item+" feedback="+results.get(key+"_take_feedback")+" offset="+results.get(key+"_take_from_offset")+" inventory="+inventory()+" pile="+(find(item,"Take")!=null));return false;
  }
 }
 /** Starts a walk with the stick, then B: the action must stop rather than continue to the old destination. */
 private static boolean cancelWalk(int x,int y)throws Exception{
  long now=System.currentTimeMillis();int[] t=instance(x,y);
  switch(sub){
   case 0:if(travel(t[0],t[1],0,"cancel test")){results.put("b_cancel","not exercised: arrived before cancel");return true;}
    if(now-subAt>700&&ControllerWorld.walkDestination()!=null){results.put("b_cancel_destination",String.valueOf(ControllerWorld.walkDestination()));held=B;sub(1);}return false;
   case 1:held=0;results.put("b_cancel_feedback",world.feedback(System.nanoTime()));sub(2);return false; // stick still held; walking stays paused
   case 2:if(now-subAt>1500){lastTileX=worldX();lastTileY=worldY();sub(3);}return false;
   default:if(now-subAt<1200)return false;
    require(worldX()==lastTileX&&worldY()==lastTileY,"Player kept walking after B");
    results.put("b_cancel_stopped_at",worldX()+","+worldY());neutral();return true;
  }
 }
 private static void journal(long now)throws Exception{
  UiState state=ControllerUi.snapshot(true);
  if(state.panel!=null&&state.panel.id==275){
   StringBuilder text=new StringBuilder();for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets)text.append(w.name).append("; ");for(UiState.Widget w:state.panel.details)text.append(w.name).append("; ");
   require(text.toString().contains("QUEST COMPLETE"),(DRUIDIC?"Druidic Ritual":"Blood Pact")+" journal not complete: "+text);
   results.put("journal_complete",true);results.put("end_experience",experience());results.put("end_inventory",inventory());results.put("lowest_constitution_level",minHp);
   results.put("end_tile",worldX()+","+worldY()+","+plane());ControllerUi.cancelWorld();neutral();stage=DONE;timeline.add("journal shows QUEST COMPLETE");return;
  }
  if(ControllerUi.hasModalPanel())return;
  if(state.panel!=null&&state.panel.id==190){UiState.Widget last=null;for(UiState.Pane pane:state.panel.panes)for(UiState.Widget w:pane.widgets){last=w;if(w.name.contains(DRUIDIC?"Druidic Ritual":"Blood Pact")&&w.actions.length>0){if(now-lastDialogue>450){lastDialogue=now;ControllerUi.invoke(w,w.actions[0]);}return;}}if(last!=null&&now-lastDialogue>450){lastDialogue=now;ControllerUi.scroll(last,12);}return;}
  if(now-lastDialogue>800){lastDialogue=now;ControllerUi.openTab(HomeTab.QUESTS.ordinal());}
 }

 /** Measures movement tiles and the corner HUD against the fought NPC inside the real render pass. */
 private static final class Observation extends Overlay {
  private volatile int planeRequested=-1;private final int[] pixels={0,0,0,0};private volatile String watched;private volatile String health="not observed";
  Observation(){setPosition(OverlayPosition.DYNAMIC);setLayer(OverlayLayer.UNDER_WIDGETS);}
  void request(int plane){planeRequested=plane;} int pixels(int plane){return pixels[plane];}
  void watch(String name){watched=name;health="not observed";} String health(){watched=null;return health;}
  @Override public Dimension render(Graphics2D graphics){
   GameClient client=client();
   if(!client.isControllerWorldReady()||me()==null)return null;
   try{
    if(planeRequested==plane()&&ControllerWorld.walkDestination()!=null){
     BufferedImage image=new BufferedImage(client.getCanvasWidth(),client.getCanvasHeight(),BufferedImage.TYPE_INT_ARGB);Graphics2D draw=image.createGraphics();
     try{for(Overlay overlay:overlays())if(overlay.getClass().getSimpleName().equals("SoloScapeMovementOverlay"))overlay.render(draw);}finally{draw.dispose();}
     int n=0;for(int px=0;px<image.getWidth();px+=2)for(int py=0;py<image.getHeight();py+=2)if((image.getRGB(px,py)>>>24)!=0)n++;
     pixels[plane()]=Math.max(pixels[plane()],n);
    }
    String name=watched;
    if(name!=null){
     ControllerTarget npc=find(name,"Attack");if(npc==null)npc=find(name,"Talk-to");
     Rectangle hud=null;for(Overlay overlay:overlays())if(overlay.getClass().getSimpleName().equals("SoloScapeControllerOverlay"))hud=overlay.getBounds();
     if(npc!=null){
      net.runelite.api.Point head=Perspective.localToCanvas(client,new LocalPoint(npc.x*128+64,npc.y*128+64),plane(),220);
      if(head!=null){
       Rectangle bar=new Rectangle(head.getX()-40,head.getY()-30,80,40); // where the native health bar draws above the head
       boolean clear=hud==null||hud.isEmpty()||!hud.intersects(bar);
       if(health.startsWith("not")||!clear)health=(clear?"clear":"OBSCURED")+" head="+head.getX()+","+head.getY()+" hud="+(hud==null?"none":hud.x+","+hud.y+" "+hud.width+"x"+hud.height);
       if(!clear)throw new IllegalStateException("Corner HUD overlaps "+name+"'s health bar: "+health);
      }
     }
    }
   }catch(IllegalStateException ex){failure=ex;}catch(Exception ex){failure=new IllegalStateException("Observation failed",ex);}
   return null;
  }
  @SuppressWarnings("unchecked") private static List<Overlay> overlays()throws Exception{Field list=OverlayManager.class.getDeclaredField("overlays");list.setAccessible(true);return (List<Overlay>)list.get(RuneLite.getInjector().getInstance(OverlayManager.class));}
 }
}
