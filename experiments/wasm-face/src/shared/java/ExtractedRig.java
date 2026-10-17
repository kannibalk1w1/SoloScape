/** Drives the extracted closure (JVM or WasmGC). Field names are the native ones the generated stand-ins keep. */
final class ExtractedRig implements FaceRig {
    private Class109 raster;
    private Class64_Sub1 model;
    private Class167 context;
    private int vertices;

    static void transform(Class101_Sub1 t, float[] v) {
        t.aFloat5672 = v[0];
        t.aFloat5673 = v[1];
        t.aFloat5669 = v[2];
        t.aFloat5655 = v[3];
        t.aFloat5678 = v[4];
        t.aFloat5666 = v[5];
        t.aFloat5662 = v[6];
        t.aFloat5680 = v[7];
        t.aFloat5664 = v[8];
        t.aFloat5686 = v[9];
        t.aFloat5685 = v[10];
        t.aFloat5681 = v[11];
    }

    private Class101_Sub1 camera;

    public void setup(FaceCase c, FaceMesh mesh, int[] framebuffer, float[] depth) {
        FaceCounters.reset();
        int w = c.width, h = c.height, cx = w / 2, cy = h / 2;
        ha_Sub1 ha = new ha_Sub1();
        ha.anInt7477 = w;
        ha.anIntArray7483 = framebuffer;
        ha.aFloatArray7511 = depth;
        ha.anInt7482 = c.illegal == 4 ? 2400 : FaceScene.NEAR;
        ha.anInt7485 = 1;
        ha.anInt7494 = 100000;
        ha.anInt7491 = h;
        ha.anInt7497 = h;
        ha.anInt7510 = cx;
        ha.anInt7504 = cy;
        ha.anInt7508 = w - cx;
        ha.anInt7509 = -cx;
        ha.anInt7506 = h - cy;
        ha.anInt7490 = -cy;
        ha.aClass101_Sub1_7492 = new Class101_Sub1();
        transform(ha.aClass101_Sub1_7492, FaceMesh.view(c.camera));
        context = new Class167();
        context.aBoolean2202 = true;
        context.aBoolean2195 = c.illegal == 3;
        context.aRunnable2198 = Thread.currentThread();
        context.anIntArray2222 = new int[4096];
        context.anIntArray2244 = new int[4096];
        context.anIntArray2214 = new int[4096];
        context.anIntArray2237 = new int[4096];
        context.anIntArray2234 = new int[4096];
        context.anIntArray2230 = new int[4096];
        context.anIntArray2213 = new int[4096];
        context.anIntArray2218 = new int[16];
        context.anIntArray2241 = new int[16];
        context.anIntArray2245 = new int[16];
        context.anIntArray2238 = new int[16];
        context.anIntArray2247 = new int[16];
        context.anIntArray2235 = new int[16];
        context.anIntArray2240 = new int[16];
        context.anIntArray2236 = new int[16];
        context.anIntArray2216 = new int[16];
        context.anIntArray2242 = new int[4096];
        java.util.Arrays.fill(context.anIntArray2242, -1);
        ha.aClass167Array7480 = new Class167[] {context};
        Class126.anIntArray4983 = FaceMesh.palette();
        raster = new Class109(ha, context);
        raster.anInt1679 = w;
        raster.anInt1672 = h;
        raster.anInt1665 = cx;
        raster.anInt1668 = cy;
        for (int y = 0; y < h; y++) raster.anIntArray1676[y] = y * w;
        context.aClass109_2220 = raster;

        int n = mesh.vertices, f = mesh.faces;
        vertices = n;
        model = new Class64_Sub1(ha);
        model.anInt5387 = n;
        model.anInt5340 = n;
        model.anInt5351 = f;
        model.anIntArray5356 = mesh.vx;
        model.anIntArray5332 = mesh.vy;
        model.anIntArray5312 = mesh.vz;
        model.aShortArray5317 = mesh.fa;
        model.aShortArray5394 = mesh.fb;
        model.aShortArray5364 = mesh.fc;
        model.anIntArray5368 = mesh.colourIndex;
        model.anIntArray5337 = new int[f];
        model.anIntArray5366 = new int[f];
        java.util.Arrays.fill(model.anIntArray5366, -1);
        model.aShortArray5311 = new short[4];
        model.aByteArray5386 = new byte[4];
        model.anInt5316 = c.variant == 1 ? 0x1000 : 0;
        model.aFloatArrayArray5314 = c.variant == 2 ? new float[1][] : null;
        model.anInt5354 = c.illegal == 1 ? 0 : 2;
        if (c.illegal == 2) {
            model.aShortArray5388 = new short[f];
            java.util.Arrays.fill(model.aShortArray5388, (short) 5);
            model.aFloatArrayArray5314 = new float[f][3];
            model.aFloatArrayArray5345 = new float[f][3];
        }
        camera = new Class101_Sub1();
        transform(camera, FaceMesh.model(c.camera));
    }

    public void project() {
        model.harnessProject(camera, 0);
    }

    public Observed observe(int vertexCount) {
        Observed o = new Observed();
        o.x = java.util.Arrays.copyOf(model.anIntArray5321, vertexCount);
        o.y = java.util.Arrays.copyOf(model.anIntArray5343, vertexCount);
        o.z = java.util.Arrays.copyOf(model.anIntArray5355, vertexCount);
        o.shortCleared = model.aShortArray5311 == null;
        o.byteCleared = model.aByteArray5386 == null;
        o.hasCounters = true;
        o.adapterEntries = FaceCounters.adapterEntries;
        o.adapterIllegal = FaceCounters.adapterIllegal;
        o.stubHits = FaceCounters.stubTotal();
        o.counters = FaceCounters.json();
        return o;
    }

    public void directFill(boolean xClip, float y0, float y1, float y2, float x0, float x1, float x2, float z0, float z1,
        float z2, int colour) {
        raster.anInt1674 = 0;
        raster.aBoolean1671 = xClip;
        raster.method1018(y0, y1, y2, x0, x1, x2, z0, z1, z2, colour);
    }
}
