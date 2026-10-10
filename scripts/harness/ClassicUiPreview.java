import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.*;

/**
 * Synthetic renderer fixtures for the classic and modern controller palettes.
 * No game assets, saves, cache or live client; item icons are blank, so only surfaces are compared.
 * Usage: java -cp client.jar:harness ClassicUiPreview output-directory
 */
public final class ClassicUiPreview {
    public static void main(String[] args)throws Exception {
        for(boolean classic:new boolean[]{true,false}) {
            ControllerTheme.classic(classic);
            String palette=classic?"classic":"modern";
            for(int[] size:new int[][]{{765,503},{1280,800}}) {
                write(args[0],"inventory-"+palette,size,g->inventory(g,size));
                write(args[0],"journal-"+palette,size,g->journal(g,size));
                write(args[0],"tab-wheel-"+palette,size,g->{TabRadialControls tabs=new TabRadialControls(new TabRadialControls.Gateway(){public int availableTabs(){return -1;}public boolean openTab(int index){return false;}});tabs.returnTo(HomeTab.INVENTORY.ordinal(),System.nanoTime());SoloScapeTabRadialOverlay.paint(g,size[0],size[1],tabs,1,ControllerGlyphs.XBOX);});
                write(args[0],"text-entry-"+palette,size,g->SoloScapeTextEntryOverlay.paint(g,new EntryState(7,1,"Enter amount","250"),null,size[0],size[1],1.25));
                write(args[0],"quick-wheel-"+palette,size,g->SoloScapeQuickRadialOverlay.paint(g,size[0],size[1],new QuickRadialControls(new QuickRadialControls.Gateway(){
                    public boolean allowed(){return true;} public UiState snapshot(){return UiState.EMPTY;} public boolean openTab(int index){return false;}
                    public boolean invoke(UiState.Widget w,UiState.Action a){return false;} public QuickBinding binding(int slot){return null;}
                    public void bind(int slot,QuickBinding binding){} public void restore(int slot){}}),1,ControllerGlyphs.XBOX));
            }
        }
        ControllerTheme.classic(true);
    }
    private interface Painter{void paint(Graphics2D g);}
    private static void write(String directory,String name,int[] size,Painter painter)throws Exception {
        BufferedImage canvas=new BufferedImage(size[0],size[1],BufferedImage.TYPE_INT_RGB);Graphics2D g=canvas.createGraphics();
        try {
            // A neutral grass/stone backdrop stands in for the unchanged native game frame.
            g.setPaint(new GradientPaint(0,0,new Color(70,92,48),size[0],size[1],new Color(96,86,66)));g.fillRect(0,0,size[0],size[1]);
            painter.paint(g);
            g.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,11));g.setColor(Color.WHITE);g.drawString("SYNTHETIC RENDERER FIXTURE — not gameplay acceptance",8,size[1]-5);
        } finally {g.dispose();}
        ImageIO.write(canvas,"png",new File(directory,name+"-"+size[0]+"x"+size[1]+".png"));
    }
    private static void inventory(Graphics2D g,int[] size) {
        String[] names={"Bronze dagger","Shrimps","Logs","Tinderbox","Air rune","Mind rune","Bucket","Pot of flour"};
        UiState.Widget[] items=new UiState.Widget[names.length];
        for(int i=0;i<items.length;i++)items[i]=new UiState.Widget(149<<16,i,100+i,i==4||i==5?25:1,names[i],new Rectangle(0,0,32,32),
            new UiState.Action[]{new UiState.Action("Use",18,0),new UiState.Action("Drop",18,1),new UiState.Action("Examine",18,2)});
        PanelPresentation view=new PanelPresentation(size[0],size[1],1);
        UiState shown=view.present(new UiState(items,new UiState.Widget[0],-1),items[1],true,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Inventory",shown.inventory,shown.inventory[1],null,ControllerGlyphs.XBOX,1);
    }
    private static void journal(Graphics2D g,int[] size) {
        UiState.Widget[] rows=new UiState.Widget[12];
        String[] text={"Talk to the cook in Lumbridge castle.","Buy a bucket and an empty pot.","Find top-quality milk and a super large egg.","Return to the cook with all three ingredients."};
        for(int i=0;i<rows.length;i++)rows[i]=new UiState.Widget(275<<16|16+i,-1,-1,0,text[i%text.length],new Rectangle(0,i*32,400,28),new UiState.Action[0],"",i<3?"Completed objective":"");
        UiState state=new UiState(new UiState.Widget[0],new UiState.Widget[0],-1,false,new UiState.Panel(275,1,"Cook's Assistant",new UiState.Pane[]{new UiState.Pane("Journal",rows)}));
        PanelPresentation view=new PanelPresentation(size[0],size[1],1.25,275);
        UiState shown=view.present(state,rows[3],false,false,false,false,true,false,false,false,false);
        SoloScapePanelOverlay.paint(g,view,"Cook's Assistant / Journal",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[3],null,ControllerGlyphs.XBOX,-1);
    }
}
