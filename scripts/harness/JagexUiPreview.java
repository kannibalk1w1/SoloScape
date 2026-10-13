import com.GameClient;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.*;

/**
 * Renderer fixtures for the Jagex-style controller UI: every SoloScape-owned in-game surface at
 * the classic 765x503 canvas and the Deck's 1280x800, plus a modern reversal check.
 * Synthetic data with real cache-rendered item sprites and bundled native skill icons.
 * Usage: java -cp client.jar:harness JagexUiPreview output-directory [backdrop.png] native-sprite-directory
 */
public final class JagexUiPreview
{
    private static BufferedImage backdrop;
    private static File spriteDirectory;
    private static final java.util.function.Function<String,String> HINTS=ControllerGlyphs.XBOX::text;

    public static void main(String[] args)throws Exception
    {
        spriteDirectory=new File(args[2]);
        if(args.length>1)
        {
            BufferedImage world=ImageIO.read(new File(args[1]));
            // The tracked native capture has a black letterbox; keep only the game canvas.
            backdrop=world.getWidth()==1280&&world.getHeight()==800?world.getSubimage(193,148,894,529):world;
        }
        for(boolean classic:new boolean[]{true,false})
        {
            ControllerTheme.classic(classic);
            String palette=classic?"":"-modern";
            for(int[] size:new int[][]{{765,503},{1280,800}})
            {
                write(args[0],"inventory"+palette,size,g->inventory(g,size));
                if(!classic)continue;
                write(args[0],"bank",size,g->bank(g,size));
                write(args[0],"quests",size,g->quests(g,size));
                write(args[0],"journal",size,g->journal(g,size));
                write(args[0],"settings",size,g->settings(g,size));
                write(args[0],"skills",size,g->skills(g,size));
                write(args[0],"empty",size,g->empty(g,size));
                write(args[0],"tab-wheel",size,g->{TabRadialControls tabs=new TabRadialControls(new TabRadialControls.Gateway(){public int availableTabs(){return ~(1<<3);}public boolean openTab(int index){return false;}});tabs.returnTo(HomeTab.INVENTORY.ordinal(),System.nanoTime());SoloScapeTabRadialOverlay.paint(g,size[0],size[1],tabs,1,ControllerGlyphs.XBOX);});
                write(args[0],"quick-wheel",size,g->SoloScapeQuickRadialOverlay.paint(g,size[0],size[1],quick(),1,ControllerGlyphs.XBOX));
                write(args[0],"text-entry",size,g->SoloScapeTextEntryOverlay.paint(g,new EntryState(7,1,"Enter amount","250"),null,size[0],size[1],1.25));
                write(args[0],"keyboard",size,g->SoloScapeUiOverlay.paint(g,keyboard(),size[0],size[1],1,ControllerGlyphs.XBOX,HINTS));
                write(args[0],"context-menu",size,g->SoloScapeUiOverlay.paint(g,context(),size[0],size[1],1,ControllerGlyphs.XBOX,HINTS));
                write(args[0],"hud-target",size,g->hudTarget(g,size));
                write(args[0],"hud-menu",size,g->hudMenu(g,size,false));
                write(args[0],"hud-loot",size,g->hudMenu(g,size,true));
            }
        }
        ControllerTheme.classic(true);
    }
    private interface Painter{void paint(Graphics2D g);}
    private static void write(String directory,String name,int[] size,Painter painter)throws Exception
    {
        BufferedImage canvas=new BufferedImage(size[0],size[1],BufferedImage.TYPE_INT_RGB);Graphics2D g=canvas.createGraphics();
        try
        {
            if(backdrop!=null){g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BILINEAR);g.drawImage(backdrop,0,0,size[0],size[1],null);}
            else{g.setPaint(new GradientPaint(0,0,new Color(70,92,48),size[0],size[1],new Color(96,86,66)));g.fillRect(0,0,size[0],size[1]);}
            painter.paint(g);
            g.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,10));g.setColor(new Color(255,255,255,170));g.drawString("RENDERER FIXTURE · synthetic data · not gameplay acceptance",size[0]-300,size[1]-4);
        }
        finally{g.dispose();}
        ImageIO.write(canvas,"png",new File(directory,name+"-"+size[0]+"x"+size[1]+".png"));
    }
    private static BufferedImage icon(UiState.Widget widget)
    {
        if(widget.itemId<0)return null;
        File file=new File(spriteDirectory,widget.itemId+"-"+widget.quantity+".png");
        try {BufferedImage image=ImageIO.read(file);if(image==null)throw new IllegalStateException("Missing native sprite: "+file);return image;}
        catch(java.io.IOException error){throw new IllegalStateException("Missing native sprite: "+file,error);}
    }
    private static UiState.Action[] actions(String... labels)
    {UiState.Action[] actions=new UiState.Action[labels.length];for(int i=0;i<labels.length;i++)actions[i]=new UiState.Action(labels[i],18,i);return actions;}
    private static void inventory(Graphics2D g,int[] size)
    {
        String[] names={"Bronze dagger","Shrimps","Logs","Tinderbox","Air rune","Mind rune","Bucket","Pot of flour","Coins","Raw shrimps","Bronze axe","Leather gloves"};
        int[] ids={1205,315,1511,590,556,558,1925,1933,995,317,1351,1059};
        int[] amounts={1,1,1,1,1250,325,1,1,184_520,6,1,1};
        UiState.Widget[] items=new UiState.Widget[28];
        for(int i=0;i<names.length;i++)items[i]=new UiState.Widget(149<<16,i,ids[i],amounts[i],names[i],new Rectangle(0,0,32,32),actions("Eat","Use","Drop","Examine"));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1);
        UiState shown=view.present(new UiState(items,new UiState.Widget[0],-1),items[1],true,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Inventory",shown.inventory,shown.inventory[1],null,ControllerGlyphs.XBOX,1,HINTS,JagexUiPreview::icon);
    }
    private static void bank(Graphics2D g,int[] size)
    {
        String[] names={"Coins","Lobster","Rune essence","Yew logs","Nature rune","Law rune","Feather","Iron ore","Coal","Gold bar","Uncut sapphire","Bowstring","Willow logs","Big bones","Cowhide","Swordfish","Fire rune","Water rune","Steel bar","Bronze arrow"};
        int[] ids={995,379,1436,1515,561,563,314,440,453,2357,1623,1777,1519,532,1739,373,554,555,2353,882};
        int[] amounts={12_480_000,312,48_200,1_840,920,140,25_000,670,1_204,36,9,450,3_300,77,64,140,152_000,98_500,22,2_000};
        UiState.Widget[] items=new UiState.Widget[names.length];
        for(int i=0;i<names.length;i++)items[i]=new UiState.Widget(762<<16|93,i,ids[i],amounts[i],names[i],new Rectangle(0,0,32,32),actions("Withdraw-1","Withdraw-5","Withdraw-10","Withdraw-All","Withdraw-X","Examine"));
        UiState state=new UiState(new UiState.Widget[28],new UiState.Widget[0],-1,true,new UiState.Panel(762,1,"Bank of SoloScape",new UiState.Pane[]{new UiState.Pane("Items",items)}));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1,762);
        UiState shown=view.present(state,items[2],false,false,true,false);
        SoloScapePanelOverlay.paint(g,view,"Bank of SoloScape / Items",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[2],null,ControllerGlyphs.XBOX,3,HINTS,JagexUiPreview::icon);
    }
    private static void quests(Graphics2D g,int[] size)
    {
        String[] names={"Cook's Assistant","Demon Slayer","The Restless Ghost","Romeo & Juliet","Sheep Shearer","Shield of Arrav","Ernest the Chicken","Vampire Slayer","Imp Catcher","Prince Ali Rescue","Doric's Quest","Black Knights' Fortress","Witch's Potion","The Knight's Sword","Goblin Diplomacy","Pirate's Treasure","Dragon Slayer","Rune Mysteries","Blood Pact","Gunnar's Ground","Druidic Ritual"};
        String[] states={"Completed","In progress","Not started"};
        UiState.Widget[] rows=new UiState.Widget[names.length];
        for(int i=0;i<rows.length;i++)rows[i]=new UiState.Widget(190<<16|10,i,-1,0,names[i],new Rectangle(0,i*20,200,18),actions("Read journal"),"",states[i%3==0?0:i%4==1?1:2]);
        UiState state=new UiState(new UiState.Widget[28],new UiState.Widget[0],-1,true,new UiState.Panel(190,1,"Quests",new UiState.Pane[]{new UiState.Pane("Free",rows)},false));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1,190);
        UiState shown=view.present(state,rows[1],false,false,false,false,true,false,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Quests / Free",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[1],null,ControllerGlyphs.XBOX,0,HINTS,w->null);
    }
    private static void journal(Graphics2D g,int[] size)
    {
        UiState.Widget[] rows=new UiState.Widget[12];
        String[] text={"Talk to the cook in Lumbridge castle.","Buy a bucket and an empty pot.","Find top-quality milk and a super large egg.","Return to the cook with all three ingredients."};
        for(int i=0;i<rows.length;i++)rows[i]=new UiState.Widget(275<<16|16+i,-1,-1,0,text[i%text.length],new Rectangle(0,i*32,400,28),new UiState.Action[0],"",i<3?"Completed objective":"");
        UiState state=new UiState(new UiState.Widget[0],new UiState.Widget[0],-1,false,new UiState.Panel(275,1,"Cook's Assistant",new UiState.Pane[]{new UiState.Pane("Journal",rows)}));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1.25,275);
        UiState shown=view.present(state,rows[3],false,false,false,false,true,false,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Cook's Assistant / Journal",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[3],null,ControllerGlyphs.XBOX,-1,HINTS,w->null);
    }
    private static void settings(Graphics2D g,int[] size)
    {
        String[][] rows={{"Preset","DECK"},{"Stick deadzone (%)","18"},{"Overlay size (%)","100"},{"Run threshold (%)","90"},{"Direct movement","On"},{"SoloScape server features","On"},{"Classic controller UI","On"},{"Invert camera Y","Off"}};
        UiState.Widget[] widgets=new UiState.Widget[rows.length];
        for(int i=0;i<rows.length;i++)widgets[i]=new UiState.Widget(ControllerSettingsModel.ID<<16,i,-1,0,rows[i][0],new Rectangle(0,i*20,200,18),actions("Next","Previous"),"A selects the next value. Changes apply on the next input tick and can be reset from the plugin.",rows[i][1]);
        UiState state=new UiState(new UiState.Widget[28],new UiState.Widget[0],-1,true,new UiState.Panel(ControllerSettingsModel.ID,1,"Controller setup",new UiState.Pane[]{new UiState.Pane("Basics",widgets)}));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1,ControllerSettingsModel.ID);
        UiState shown=view.present(state,widgets[6],false,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Controller setup / Basics",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[6],null,ControllerGlyphs.XBOX,0,HINTS,w->null);
    }
    private static void skills(Graphics2D g,int[] size)
    {
        String[] names={"Attack","Defence","Strength","Constitution","Ranged","Prayer","Magic","Cooking","Woodcutting","Fletching","Fishing","Firemaking","Crafting","Smithing","Mining","Herblore","Agility","Thieving","Slayer","Farming","Runecrafting","Hunter","Construction","Summoning","Dungeoneering"};
        int[] components={200,28,11,193,52,76,93,68,165,101,44,172,84,179,186,36,19,60,118,126,110,142,134,150,158};
        UiState.Widget[] widgets=new UiState.Widget[names.length];
        for(int i=0;i<names.length;i++)widgets[i]=new UiState.Widget(320<<16|components[i],-1,-1,0,names[i],new Rectangle(0,i*20,60,18),actions("View guide"),"XP: "+(i*1234+83)+" · Next level at: "+(i*1500+174),(1+i*4%99)+" / "+(1+i*4%99));
        UiState state=new UiState(new UiState.Widget[28],new UiState.Widget[0],-1,true,new UiState.Panel(320,1,"Skills",new UiState.Pane[]{new UiState.Pane("Levels",widgets)},false));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1,320);
        UiState shown=view.present(state,widgets[11],false,false,false,false,false,true,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Skills / Levels",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[11],null,ControllerGlyphs.XBOX,0,HINTS,w->null);
    }
    private static void empty(Graphics2D g,int[] size)
    {
        UiState state=new UiState(new UiState.Widget[28],new UiState.Widget[0],-1,true,new UiState.Panel(620,1,"General Store",new UiState.Pane[]{new UiState.Pane("Stock",new UiState.Widget[0])}));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1,620);
        UiState shown=view.present(state,null,false,false,false,true);
        SoloScapePanelOverlay.paint(g,view,"General Store / Stock",shown.panel.panes[0].widgets,null,null,ControllerGlyphs.XBOX,-1,HINTS,w->null);
    }
    private static QuickRadialControls quick()
    {
        return new QuickRadialControls(new QuickRadialControls.Gateway(){
            public boolean allowed(){return true;} public UiState snapshot(){return UiState.EMPTY;} public boolean openTab(int index){return false;}
            public boolean invoke(UiState.Widget w,UiState.Action a){return false;}
            public QuickBinding binding(int slot){return null;}
            public void bind(int slot,QuickBinding binding){} public void restore(int slot){}});
    }
    private static UiControls controls(UiState state)
    {
        return new UiControls(new UiControls.Gateway(){
            public UiState snapshot(){return state;} public boolean openInventory(){return true;}
            public boolean invoke(UiState.Widget w,UiState.Action a){return false;}
            public void cancelSelection(){} public void cancelDialogue(){}});
    }
    private static UiControls keyboard()
    {
        UiState state=new UiState(new UiState.Widget[28],new UiState.Widget[0],-1,true,null,new EntryState(7,1,"Enter amount","1250"));
        UiControls ui=controls(state);ui.update(new GamepadState(),System.nanoTime());return ui;
    }
    private static UiControls context()
    {
        UiState.Widget[] items=new UiState.Widget[28];
        // Native inventory slot positions on the fixed 765x503 frame stand in for the live widget bounds.
        String[] names={"Shrimps","Logs","Tinderbox","Bronze axe"};
        for(int i=0;i<names.length;i++)items[i]=new UiState.Widget(149<<16,i,100+i,1,names[i],new Rectangle(563+i%4*42,213+i/4*36,36,32),actions("Eat","Use","Drop","Examine"));
        UiState state=new UiState(items,new UiState.Widget[0],-1,true);
        UiControls ui=controls(state);
        GamepadState press=new GamepadState();ui.update(press,System.nanoTime());press.buttonsHeld=press.buttonsPressed=8;ui.update(press,System.nanoTime());
        ui.update(new GamepadState(),System.nanoTime());
        ui.mouseFocus(items[0],true);
        press=new GamepadState();press.buttonsHeld=press.buttonsPressed=1<<12;ui.update(press,System.nanoTime());
        return ui;
    }
    private static void hudTarget(Graphics2D g,int[] size)
    {
        java.util.List<String> notes=new java.util.ArrayList<>(java.util.Arrays.asList("LT: aim · LB/RB: target · X: actions · B: cancel","Action sent"));
        SoloScapeControllerOverlay.paintClassic(g,size[0]/765.0>1.5?1.25:1,size[0],HINTS.apply("A: Attack"),"Goblin (level-2)",1,new GameClient.ControllerTarget[0],0,notes,"Action sent",HINTS);
    }
    private static void hudMenu(Graphics2D g,int[] size,boolean loot)
    {
        GameClient.ControllerTarget[] menu;
        if(loot)
        {
            String[] names={"Bones","Coins","Bronze med helm","Raw beef","Feather","Grimy guam","Air rune","Iron arrow","Cowhide"};
            menu=new GameClient.ControllerTarget[names.length];
            for(int i=0;i<names.length;i++)menu[i]=new GameClient.ControllerTarget(names[i],"Take",21,i,50,50,0,3200,3200);
        }
        else menu=new GameClient.ControllerTarget[]{
            new GameClient.ControllerTarget("Staircase","Climb-up",3,1,50,50,0,3200,3200),
            new GameClient.ControllerTarget("Staircase","Climb-down",4,1,50,50,0,3200,3200),
            new GameClient.ControllerTarget("Hans","Talk-to",20,2,50,50,0,3200,3200),
            new GameClient.ControllerTarget("Staircase","Examine",1007,1,50,50,0,3200,3200)};
        java.util.List<String> notes=new java.util.ArrayList<>(java.util.Collections.singletonList("LS / D-pad: choose · A: confirm · B: back"));
        SoloScapeControllerOverlay.paintClassic(g,size[0]/765.0>1.5?1.25:1,size[0],null,null,0,menu,loot?7:0,notes,null,HINTS);
    }
}
