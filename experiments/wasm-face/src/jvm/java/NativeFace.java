import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/**
 * Reference run: the same cases through the real Class64_Sub1/Class109 bytecode in the native client jar.
 * ha_Sub1, Class167, Class64_Sub1 and Class101_Sub1 are allocated without constructors (sun.misc.Unsafe) and only
 * the fields the audited path reads are set. method654 is invoked reflectively with i == -1. Never used in the browser.
 */
public final class NativeFace {
    static final class JarRig implements FaceRig {
        private sun.misc.Unsafe unsafe;
        private Class<?> haClass, ctxClass, rasterClass, modelClass, matrixClass, matrixBase, classBase;
        private Object raster, model, camera;
        private Method project, fill;
        private Field blend, xClip;

        private static Field field(Class<?> c, String name) throws ReflectiveOperationException {
            Field f = c.getDeclaredField(name);
            f.setAccessible(true);
            return f;
        }

        private static void set(Class<?> c, Object o, String name, Object value) throws ReflectiveOperationException {
            field(c, name).set(o, value);
        }

        private Object matrix(float[] v) throws ReflectiveOperationException {
            Object m = unsafe.allocateInstance(matrixClass);
            String[] names = {"aFloat5672", "aFloat5673", "aFloat5669", "aFloat5655", "aFloat5678", "aFloat5666", "aFloat5662",
                "aFloat5680", "aFloat5664", "aFloat5686", "aFloat5685", "aFloat5681"};
            for (int i = 0; i < names.length; i++) field(matrixClass, names[i]).setFloat(m, v[i]);
            return m;
        }

        private static void ints(Class<?> c, Object o, String name, int length) throws ReflectiveOperationException {
            set(c, o, name, new int[length]);
        }

        public void setup(FaceCase cs, FaceMesh mesh, int[] framebuffer, float[] depth) {
            try {
                Field unsafeField = Class.forName("sun.misc.Unsafe").getDeclaredField("theUnsafe");
                unsafeField.setAccessible(true);
                unsafe = (sun.misc.Unsafe) unsafeField.get(null);
                haClass = Class.forName("ha_Sub1");
                ctxClass = Class.forName("Class167");
                rasterClass = Class.forName("Class109");
                modelClass = Class.forName("Class64_Sub1");
                matrixClass = Class.forName("Class101_Sub1");
                int w = cs.width, h = cs.height, cx = w / 2, cy = h / 2;
                Object ha = unsafe.allocateInstance(haClass);
                set(haClass, ha, "anInt7477", w);
                set(haClass, ha, "anIntArray7483", framebuffer);
                set(haClass, ha, "aFloatArray7511", depth);
                set(haClass, ha, "anInt7482", cs.illegal == 4 ? 2400 : FaceScene.NEAR);
                set(haClass, ha, "anInt7485", 1);
                set(haClass, ha, "anInt7494", 100000);
                set(haClass, ha, "anInt7491", h);
                set(haClass, ha, "anInt7497", h);
                set(haClass, ha, "anInt7510", cx);
                set(haClass, ha, "anInt7504", cy);
                set(haClass, ha, "anInt7508", w - cx);
                set(haClass, ha, "anInt7509", -cx);
                set(haClass, ha, "anInt7506", h - cy);
                set(haClass, ha, "anInt7490", -cy);
                set(haClass, ha, "aClass101_Sub1_7492", matrix(FaceMesh.view(cs.camera)));
                Object ctx = unsafe.allocateInstance(ctxClass);
                set(ctxClass, ctx, "aBoolean2202", true);
                set(ctxClass, ctx, "aBoolean2195", cs.illegal == 3);
                set(ctxClass, ctx, "aRunnable2198", Thread.currentThread());
                for (String name : new String[] {"anIntArray2222", "anIntArray2244", "anIntArray2214", "anIntArray2237",
                    "anIntArray2234", "anIntArray2230", "anIntArray2213"}) ints(ctxClass, ctx, name, 4096);
                for (String name : new String[] {"anIntArray2218", "anIntArray2241", "anIntArray2245", "anIntArray2238",
                    "anIntArray2247", "anIntArray2235", "anIntArray2240", "anIntArray2236", "anIntArray2216"})
                    ints(ctxClass, ctx, name, 16);
                int[] untextured = new int[4096];
                java.util.Arrays.fill(untextured, -1);
                set(ctxClass, ctx, "anIntArray2242", untextured);
                Object array = java.lang.reflect.Array.newInstance(ctxClass, 1);
                java.lang.reflect.Array.set(array, 0, ctx);
                set(haClass, ha, "aClass167Array7480", array);
                set(Class.forName("Class126"), null, "anIntArray4983", FaceMesh.palette());
                Constructor<?> ctor = rasterClass.getDeclaredConstructor(haClass, ctxClass);
                ctor.setAccessible(true);
                raster = ctor.newInstance(ha, ctx);
                set(rasterClass, raster, "anInt1679", w);
                set(rasterClass, raster, "anInt1672", h);
                set(rasterClass, raster, "anInt1665", cx);
                set(rasterClass, raster, "anInt1668", cy);
                int[] rows = (int[]) field(rasterClass, "anIntArray1676").get(raster);
                for (int y = 0; y < h; y++) rows[y] = y * w;
                set(ctxClass, ctx, "aClass109_2220", raster);
                blend = field(rasterClass, "anInt1674");
                xClip = field(rasterClass, "aBoolean1671");
                fill = rasterClass.getDeclaredMethod("method1018", float.class, float.class, float.class, float.class,
                    float.class, float.class, float.class, float.class, float.class, int.class);
                fill.setAccessible(true);

                int n = mesh.vertices, f = mesh.faces;
                model = unsafe.allocateInstance(modelClass);
                set(modelClass, model, "aHa_Sub1_5353", ha);
                set(modelClass, model, "anInt5387", n);
                set(modelClass, model, "anInt5340", n);
                set(modelClass, model, "anInt5351", f);
                set(modelClass, model, "anIntArray5356", mesh.vx);
                set(modelClass, model, "anIntArray5332", mesh.vy);
                set(modelClass, model, "anIntArray5312", mesh.vz);
                set(modelClass, model, "aShortArray5317", mesh.fa);
                set(modelClass, model, "aShortArray5394", mesh.fb);
                set(modelClass, model, "aShortArray5364", mesh.fc);
                set(modelClass, model, "anIntArray5368", mesh.colourIndex);
                set(modelClass, model, "anIntArray5337", new int[f]);
                int[] flat = new int[f];
                java.util.Arrays.fill(flat, -1);
                set(modelClass, model, "anIntArray5366", flat);
                set(modelClass, model, "aShortArray5311", new short[4]);
                set(modelClass, model, "aByteArray5386", new byte[4]);
                set(modelClass, model, "anInt5316", cs.variant == 1 ? 0x1000 : 0);
                set(modelClass, model, "aFloatArrayArray5314", cs.variant == 2 ? new float[1][] : null);
                set(modelClass, model, "anInt5354", cs.illegal == 1 ? 0 : 2);
                if (cs.illegal == 2) {
                    short[] textured = new short[f];
                    java.util.Arrays.fill(textured, (short) 5);
                    set(modelClass, model, "aShortArray5388", textured);
                    set(modelClass, model, "aFloatArrayArray5314", new float[f][3]);
                    set(modelClass, model, "aFloatArrayArray5345", new float[f][3]);
                }
                camera = matrix(FaceMesh.model(cs.camera));
                project = modelClass.getDeclaredMethod("method654", Class.forName("Class101"), Class.forName("Class318_Sub3"),
                    int.class, int.class);
                project.setAccessible(true);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        public void project() {
            try {
                project.invoke(model, camera, null, -1, 0);
            } catch (InvocationTargetException e) {
                throw new IllegalStateException(e.getCause());
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        public Observed observe(int vertexCount) {
            try {
                Observed o = new Observed();
                o.x = java.util.Arrays.copyOf((int[]) field(modelClass, "anIntArray5321").get(model), vertexCount);
                o.y = java.util.Arrays.copyOf((int[]) field(modelClass, "anIntArray5343").get(model), vertexCount);
                o.z = java.util.Arrays.copyOf((int[]) field(modelClass, "anIntArray5355").get(model), vertexCount);
                o.shortCleared = field(modelClass, "aShortArray5311").get(model) == null;
                o.byteCleared = field(modelClass, "aByteArray5386").get(model) == null;
                return o;
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }

        public void directFill(boolean clip, float y0, float y1, float y2, float x0, float x1, float x2, float z0, float z1,
            float z2, int colour) {
            try {
                blend.setInt(raster, 0);
                xClip.setBoolean(raster, clip);
                fill.invoke(raster, y0, y1, y2, x0, x1, x2, z0, z1, z2, colour);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(e);
            }
        }
    }

    public static void main(String[] args) {
        for (FaceCase c : FaceScene.cases(Integer.getInteger("face.illegal", 0))) {
            System.out.println(FaceScene.run(new JarRig(), c, false));
        }
    }
}
