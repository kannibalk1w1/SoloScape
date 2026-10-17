import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * JVM reference: runs the real ha_Sub1.method3636 bytecode from the matched client jar.
 * ha_Sub1 is allocated without its constructor (its renderer needs a live Canvas), so only the
 * raster method and the aa_Sub3 mask it casts to are exercised. Reflection adds per-edge overhead;
 * this run is for the hash, not for timing.
 */
public final class NativeJar {
    public static void main(String[] args) throws Exception {
        Class<?> haSub1 = Class.forName("ha_Sub1");
        Class<?> aaType = Class.forName("aa");
        Class<?> aaSub3 = Class.forName("aa_Sub3");
        Method edgeMethod = haSub1.getDeclaredMethod("method3636", int.class, int.class, int.class, int.class,
            int.class, int.class, aaType, int.class, int.class);
        edgeMethod.setAccessible(true);
        Field clipMinY = field(haSub1, "anInt7476");
        Field stride = field(haSub1, "anInt7477");
        Field clipMinX = field(haSub1, "anInt7496");
        Field clipMaxY = field(haSub1, "anInt7503");
        Field clipMaxX = field(haSub1, "anInt7507");
        Field pixels = field(haSub1, "anIntArray7483");
        Field spanStart = field(aaSub3, "anIntArray5201");
        Field spanLength = field(aaSub3, "anIntArray5202");
        sun.misc.Unsafe unsafe = unsafe();

        for (int[] size : new int[][] {{765, 503}, {1280, 800}}) {
            Object ha = unsafe.allocateInstance(haSub1);
            Object mask = unsafe.allocateInstance(aaSub3);
            int[] framebuffer = new int[size[0] * size[1]];
            Raster raster = new Raster() {
                public void bind(int[] fb, int width, int height) {
                    try {
                        pixels.set(ha, fb);
                        stride.setInt(ha, width);
                        clipMinY.setInt(ha, 0);
                        clipMaxY.setInt(ha, height);
                        clipMinX.setInt(ha, 0);
                        clipMaxX.setInt(ha, width);
                    } catch (IllegalAccessException e) {
                        throw new IllegalStateException(e);
                    }
                }

                public void setMask(int[] start, int[] length) {
                    try {
                        spanStart.set(mask, start);
                        spanLength.set(mask, length);
                    } catch (IllegalAccessException e) {
                        throw new IllegalStateException(e);
                    }
                }

                public void edge(int x0, int y0, int x1, int y1, int colour, int mode) {
                    try {
                        edgeMethod.invoke(ha, x0, y0, x1, y1, colour, mode, mask, 0, 0);
                    } catch (ReflectiveOperationException e) {
                        throw new IllegalStateException(e);
                    }
                }
            };
            Scene.render(raster, size[0], size[1], framebuffer);
            System.out.println("{\"size\":\"" + size[0] + "x" + size[1] + "\",\"fnv1a\":\""
                + Integer.toHexString(Scene.hash(framebuffer)) + "\",\"source\":\"jar-bytecode\"}");
        }
    }

    private static Field field(Class<?> type, String name) throws NoSuchFieldException {
        Field f = type.getDeclaredField(name);
        f.setAccessible(true);
        return f;
    }

    private static sun.misc.Unsafe unsafe() throws ReflectiveOperationException {
        Field f = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
        f.setAccessible(true);
        return (sun.misc.Unsafe) f.get(null);
    }
}
