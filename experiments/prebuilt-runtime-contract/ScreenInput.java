import java.awt.Rectangle;
import java.awt.Robot;
import java.awt.Toolkit;
import java.awt.event.InputEvent;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;

/**
 * Private helper for the native lifecycle probe. Compile against JDK8 only, outside the payload.
 * Usage: screenshot OUT.png  |  click X Y   (left button, on the DISPLAY it is run under).
 * It never reads game classes, saves, logins or audio.
 */
public final class ScreenInput {
    private ScreenInput() {
    }

    public static void main(String[] args) throws Exception {
        Robot robot = new Robot();
        Rectangle screen = new Rectangle(Toolkit.getDefaultToolkit().getScreenSize());
        if (args.length == 2 && args[0].equals("screenshot")) {
            BufferedImage image = robot.createScreenCapture(screen);
            ImageIO.write(image, "png", new File(args[1]));
            System.out.println("screenshot " + screen.width + "x" + screen.height);
            return;
        }
        if (args.length == 3 && args[0].equals("click")) {
            int x = Integer.parseInt(args[1]);
            int y = Integer.parseInt(args[2]);
            if (!screen.contains(x, y)) {
                System.err.println("click outside the display: " + x + "," + y);
                System.exit(3);
            }
            robot.mouseMove(x, y);
            robot.delay(150);
            robot.mousePress(InputEvent.BUTTON1_DOWN_MASK);
            robot.delay(60);
            robot.mouseRelease(InputEvent.BUTTON1_DOWN_MASK);
            robot.delay(200);
            System.out.println("clicked " + x + "," + y);
            return;
        }
        System.err.println("usage: screenshot OUT.png | click X Y");
        System.exit(2);
    }
}
