import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * Reference run: the same Scene driven through the real Class109 bytecode in the native client jar.
 * ha_Sub1 and Class167 are allocated without running their constructors (sun.misc.Unsafe) and only
 * the fields Class109 reads are set. This is used for correctness comparison only, never in the browser.
 */
public final class NativeJar {
    static final class JarFill implements Fill {
        private Object raster;
        private Field blend, xClip;
        private Method triangle;
        private Field width, height, rows;

        public void bind(int[] framebuffer, float[] depth, int w, int h) {
            try {
                Field unsafeField = Class.forName("sun.misc.Unsafe").getDeclaredField("theUnsafe");
                unsafeField.setAccessible(true);
                sun.misc.Unsafe unsafe = (sun.misc.Unsafe) unsafeField.get(null);
                Class<?> haClass = Class.forName("ha_Sub1");
                Class<?> ctxClass = Class.forName("Class167");
                Class<?> rasterClass = Class.forName("Class109");
                Object ha = unsafe.allocateInstance(haClass);
                set(haClass, ha, "anInt7477", w);
                set(haClass, ha, "anIntArray7483", framebuffer);
                set(haClass, ha, "aFloatArray7511", depth);
                Object ctx = unsafe.allocateInstance(ctxClass);
                set(ctxClass, ctx, "aBoolean2202", true);
                Constructor<?> ctor = rasterClass.getDeclaredConstructor(haClass, ctxClass);
                ctor.setAccessible(true);
                raster = ctor.newInstance(ha, ctx);
                set(rasterClass, raster, "anInt1679", w);
                set(rasterClass, raster, "anInt1672", h);
                Field table = rasterClass.getDeclaredField("anIntArray1676");
                table.setAccessible(true);
                int[] offsets = (int[]) table.get(raster);
                for (int y = 0; y < h; y++) offsets[y] = y * w;
                blend = rasterClass.getDeclaredField("anInt1674");
                xClip = rasterClass.getDeclaredField("aBoolean1671");
                blend.setAccessible(true);
                xClip.setAccessible(true);
                triangle = rasterClass.getDeclaredMethod("method1018", float.class, float.class, float.class,
                    float.class, float.class, float.class, float.class, float.class, float.class, int.class);
                triangle.setAccessible(true);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        private static void set(Class<?> c, Object o, String name, Object value) throws ReflectiveOperationException {
            Field f = c.getDeclaredField(name);
            f.setAccessible(true);
            f.set(o, value);
        }

        public void setBlend(int value) {
            try {
                blend.setInt(raster, value);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        public void setXClip(boolean needed) {
            try {
                xClip.setBoolean(raster, needed);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        public void triangle(float y0, float y1, float y2, float x0, float x1, float x2, float z0, float z1, float z2, int colour) {
            try {
                triangle.invoke(raster, y0, y1, y2, x0, x1, x2, z0, z1, z2, colour);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }
    }

    public static void main(String[] args) {
        Bench.Clock clock = () -> System.nanoTime() / 1.0e6;
        int[][] sizes = {{765, 503}, {1280, 800}};
        for (int[] s : sizes) {
            System.out.println(Bench.measure(clock, new JarFill(), "single", Scene.SINGLE, s[0], s[1]));
            System.out.println(Bench.measure(clock, new JarFill(), "single64", Scene.SINGLE_BATCH, s[0], s[1]));
            System.out.println(Bench.measure(clock, new JarFill(), "mesh", Scene.MESH, s[0], s[1]));
        }
    }
}
