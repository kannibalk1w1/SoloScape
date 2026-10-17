import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Reference run: the same Scene driven through the real Class109 bytecode in the native client jar.
 * ha_Sub1 and Class167 are allocated without running their constructors (sun.misc.Unsafe). The
 * texture provider is the real ha_Sub1 texture-cache path, fed with the ORIGINAL SynthAssets texels
 * through a stub `d` material source and pre-populated cache nodes, so the jar's own method3718/3719/
 * 3726/3727/3714 and cache code run. Correctness comparison only; never used in the browser.
 */
public final class NativeJar {
    static final class JarFill implements Fill {
        private Object raster;
        private Field blend, xClip;
        private Method shaded, gouraud, tex1, tex3;

        private static Field field(Class<?> c, String name) throws ReflectiveOperationException {
            Field f = c.getDeclaredField(name);
            f.setAccessible(true);
            return f;
        }

        private static void set(Class<?> c, Object o, String name, Object value) throws ReflectiveOperationException {
            field(c, name).set(o, value);
        }

        private static Method method(Class<?> c, String name) throws ReflectiveOperationException {
            Method found = null;
            for (Method m : c.getDeclaredMethods()) {
                if (m.getName().equals(name)) {
                    if (found != null) throw new IllegalStateException("overloaded " + name);
                    found = m;
                }
            }
            if (found == null) throw new IllegalStateException("missing " + name);
            found.setAccessible(true);
            return found;
        }

        public void bind(int[] framebuffer, float[] depth, int w, int h) {
            try {
                Field unsafeField = Class.forName("sun.misc.Unsafe").getDeclaredField("theUnsafe");
                unsafeField.setAccessible(true);
                sun.misc.Unsafe unsafe = (sun.misc.Unsafe) unsafeField.get(null);
                Class<?> haBase = Class.forName("ha");
                Class<?> haClass = Class.forName("ha_Sub1");
                Class<?> ctxClass = Class.forName("Class167");
                Class<?> rasterClass = Class.forName("Class109");
                Class<?> materialSource = Class.forName("d");
                Class<?> materialClass = Class.forName("Class12");
                Class<?> cacheClass = Class.forName("ReferenceCache");
                Class<?> nodeClass = Class.forName("Class348_Sub25");

                Object ha = unsafe.allocateInstance(haClass);
                set(haClass, ha, "anInt7477", w);
                set(haClass, ha, "anIntArray7483", framebuffer);
                set(haClass, ha, "aFloatArray7511", depth);
                set(haClass, ha, "anInt7501", SynthAssets.LARGE);

                // Material source: method3 (the material record) and method4 (is the id loaded) are answered; the texel generators
                // must never run because the cache below is pre-populated.
                Object source = Proxy.newProxyInstance(materialSource.getClassLoader(), new Class<?>[] {materialSource},
                    (proxy, m, a) -> {
                        if (m.getName().equals("method4")) return SynthAssets.texels((Integer) a[1]) != null;
                        if (!m.getName().equals("method3")) throw new IllegalStateException("unexpected d." + m.getName());
                        int id = (Integer) a[0];
                        Object rec = unsafe.allocateInstance(materialClass);
                        set(materialClass, rec, "aBoolean199", SynthAssets.small(id));
                        set(materialClass, rec, "anInt200", SynthAssets.mode(id));
                        set(materialClass, rec, "aBoolean217", SynthAssets.wrapsRepeat(id));
                        set(materialClass, rec, "aBoolean215", false);
                        return rec;
                    });
                set(haBase, ha, "aD4579", source);

                Constructor<?> cacheCtor = cacheClass.getDeclaredConstructor(int.class);
                cacheCtor.setAccessible(true);
                Object cache = cacheCtor.newInstance(64);
                Constructor<?> nodeCtor = nodeClass.getDeclaredConstructor(int.class, int.class, int[].class, boolean.class);
                nodeCtor.setAccessible(true);
                Method put = method(cacheClass, "method582");
                for (int id = 1; id <= 4; id++) {
                    int size = SynthAssets.small(id) ? SynthAssets.SMALL : SynthAssets.LARGE;
                    // bool=false: keep the synthetic texels as given (no native box-blur pass).
                    put.invoke(cache, nodeCtor.newInstance(id, size, SynthAssets.texels(id), false), (long) id, (byte) -122);
                    put.invoke(cache, nodeCtor.newInstance(id, size, SynthAssets.texels(id), false),
                        (long) id | ~0x7fffffffffffffffL, (byte) -126);
                }
                set(haClass, ha, "aClass60_7498", cache);

                Class<?> palette = Class.forName("Class126");
                set(palette, null, "anIntArray4983", SynthAssets.palette());

                Object ctx = unsafe.allocateInstance(ctxClass);
                set(ctxClass, ctx, "aBoolean2202", true);
                Constructor<?> ctor = rasterClass.getDeclaredConstructor(haClass, ctxClass);
                ctor.setAccessible(true);
                raster = ctor.newInstance(ha, ctx);
                set(rasterClass, raster, "anInt1679", w);
                set(rasterClass, raster, "anInt1672", h);
                int[] offsets = (int[]) field(rasterClass, "anIntArray1676").get(raster);
                for (int y = 0; y < h; y++) offsets[y] = y * w;
                blend = field(rasterClass, "anInt1674");
                xClip = field(rasterClass, "aBoolean1671");
                shaded = method(rasterClass, "method1022");
                gouraud = method(rasterClass, "method1027");
                tex1 = method(rasterClass, "method1024");
                tex3 = method(rasterClass, "method1020");
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
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

        public void draw(int kind, Tri t) {
            Object[] a;
            Method m;
            switch (kind) {
                case SHADED:
                    m = shaded;
                    a = new Object[] {t.y[0], t.y[1], t.y[2], t.x[0], t.x[1], t.x[2], t.z[0], t.z[1], t.z[2],
                        t.palette[0], t.palette[1], t.palette[2]};
                    break;
                case GOURAUD:
                    m = gouraud;
                    a = new Object[] {t.y[0], t.y[1], t.y[2], t.x[0], t.x[1], t.x[2], t.z[0], t.z[1], t.z[2],
                        t.colour[0], t.colour[1], t.colour[2]};
                    break;
                case TEX1:
                    m = tex1;
                    a = new Object[] {t.y[0], t.y[1], t.y[2], t.x[0], t.x[1], t.x[2], t.z[0], t.z[1], t.z[2],
                        t.u[0], t.u[1], t.u[2], t.v[0], t.v[1], t.v[2], t.colour[0], t.colour[1], t.colour[2],
                        t.fogColour, t.fogAlpha[0], t.fogAlpha[1], t.fogAlpha[2], t.texture[0]};
                    break;
                default:
                    m = tex3;
                    a = new Object[] {t.y[0], t.y[1], t.y[2], t.x[0], t.x[1], t.x[2], t.z[0], t.z[1], t.z[2],
                        t.u[0], t.u[1], t.u[2], t.v[0], t.v[1], t.v[2], t.colour[0], t.colour[1], t.colour[2],
                        t.fogColour, t.fogAlpha[0], t.fogAlpha[1], t.fogAlpha[2],
                        t.texture[0], t.scale[0], t.texture[1], t.scale[1], t.texture[2], t.scale[2]};
                    break;
            }
            try {
                m.invoke(raster, a);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }
    }

    public static void main(String[] args) {
        Bench.Clock clock = () -> System.nanoTime() / 1.0e6;
        int[][] sizes = {{765, 503}, {1280, 800}};
        for (int[] s : sizes) {
            for (int kind = 0; kind < Scene.NAMES.length; kind++) {
                System.out.println(Bench.measure(clock, new JarFill(), Scene.NAMES[kind], kind, s[0], s[1]));
            }
            System.out.println(Bench.control("shaded-palette-control", new JarFill(), Scene.SHADED, 1, s[0], s[1]));
            System.out.println(Bench.control("tex1-texel-control", new JarFill(), Scene.TEX1, 1, s[0], s[1]));
            System.out.println(Bench.control("tex3-texel-control", new JarFill(), Scene.TEX3, 1, s[0], s[1]));
        }
    }
}
