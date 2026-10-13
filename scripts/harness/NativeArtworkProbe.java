import java.awt.Canvas;
import java.nio.file.*;
import javax.imageio.ImageIO;
/** Private cache sprite capture. Uses its own software toolkit, never the scene renderer. */
public final class NativeArtworkProbe {
 private static final int[] IDS={1205,315,1511,590,556,558,1925,1933,995,317,1351,1059,995,379,1436,1515,561,563,314,440,453,2357,1623,1777,1519,532,1739,373,554,555,2353,882};
 private static final int[] QTY={1,1,1,1,1250,325,1,1,184520,6,1,1,12480000,312,48200,1840,920,140,25000,670,1204,36,9,450,3300,77,64,140,152000,98500,22,2000};
 private static ha renderer;private static int at,retries;
 public static boolean active(){return renderer!=null&&at<IDS.length;}
 public static boolean tick(String marker)throws Exception{
  if(at==IDS.length)return true;
  if(renderer==null){Canvas canvas=new Canvas();canvas.setSize(36,32);renderer=Class104.method958(true,0,Class348_Sub40_Sub4.aD9113,0,canvas,Class136.aClass45_4796);}
  Exception_Sub1.aClass255_112.method1932(renderer,0,QTY[at],Class240.aClass324_4684,null,0,false,(byte)83,renderer,IDS[at],false,1);
  java.awt.image.BufferedImage image=ControllerItemImages.get(IDS[at],QTY[at]);
  if(image==null){if(++retries>40)throw new IllegalStateException("Native item sprite unavailable: "+IDS[at]);return false;}
  Path directory=Paths.get(marker+".artwork");Files.createDirectories(directory);
  ImageIO.write(image,"png",directory.resolve(IDS[at]+"-"+QTY[at]+".png").toFile());at++;retries=0;
  if(at==IDS.length)System.out.println("Captured "+at+" actual native item sprites.");return at==IDS.length;
 }
}
