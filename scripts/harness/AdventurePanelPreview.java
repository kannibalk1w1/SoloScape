import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import net.runelite.client.input.controller.*;
import net.runelite.client.plugins.soloscapecontroller.*;

/** Explicit synthetic renderer fixtures: no game assets, saves or live client. */
public final class AdventurePanelPreview {
    public static void main(String[] args)throws Exception {
        for(int[] size:new int[][]{{765,503},{1280,800}}) {
            UiState.Widget[] rows=new UiState.Widget[18];
            String[] text={"Talk to the cook in Lumbridge castle.","Buy a bucket and an empty pot.","Find top-quality milk and a super large egg.","Speak to Millie about extra-fine flour.","Put grain in the hopper, operate the controls and fill the pot.","Return to the cook with all three ingredients."};
            for(int i=0;i<rows.length;i++)rows[i]=new UiState.Widget(275<<16|16+i,-1,-1,0,text[i%text.length],new Rectangle(0,i*32,400,28),new UiState.Action[0],"",i<3?"Completed objective":"");
            UiState state=new UiState(new UiState.Widget[0],new UiState.Widget[0],-1,false,new UiState.Panel(275,1,"Cook's Assistant",new UiState.Pane[]{new UiState.Pane("Journal",rows)}));
            PanelPresentation view=new PanelPresentation(size[0],size[1],1.25,275);
            UiState shown=view.present(state,rows[4],false,false,false,false,true,false,false,false,false);
            BufferedImage canvas=new BufferedImage(size[0],size[1],BufferedImage.TYPE_INT_RGB);Graphics2D g=canvas.createGraphics();
            try {
                g.setColor(new Color(9,14,19));g.fillRect(0,0,size[0],size[1]);
                SoloScapePanelOverlay.paint(g,view,"Cook's Assistant / Journal",shown.panel.panes[0].widgets,shown.panel.panes[0].widgets[4],null,ControllerGlyphs.XBOX,-1);
                g.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,11));g.setColor(Color.WHITE);g.drawString("SYNTHETIC RENDERER FIXTURE — not gameplay acceptance",8,size[1]-5);
            } finally {g.dispose();}
            ImageIO.write(canvas,"png",new File(args[0]+"/adventure-journal-"+size[0]+"x"+size[1]+".png"));
        }
    }
}
