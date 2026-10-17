/**
 * Real-clock timing. "raster" is only the triangle submissions; buffer clear and context binding are
 * reported separately. Presentation is verified but not timed in this probe; see wasm-raster TransferProbe.
 */
final class Bench {
    interface Clock {
        double nowMs();
    }

    static final int WARMUP = 3;
    static final int SAMPLES = 15;

    /** Returns one JSON object: sizes, hashes and raster-time statistics for one scene kind. */
    static String measure(Clock clock, Fill fill, String name, int kind, int width, int height) {
        int[] framebuffer = new int[width * height];
        float[] depth = new float[width * height];
        Scene scene = new Scene(fill, width, height);
        int triangles = 0;
        for (int i = 0; i < WARMUP; i++) {
            triangles = scene.render(kind, framebuffer, depth);
        }
        double[] times = new double[SAMPLES];
        double[] clears = new double[SAMPLES];
        for (int i = 0; i < SAMPLES; i++) {
            double t0 = clock.nowMs();
            scene.begin(framebuffer, depth);
            double t1 = clock.nowMs();
            scene.bind(framebuffer, depth);
            double t2 = clock.nowMs();
            triangles = scene.draw(kind);
            double t3 = clock.nowMs();
            clears[i] = t1 - t0;
            times[i] = t3 - t2;
        }
        java.util.Arrays.sort(times);
        java.util.Arrays.sort(clears);
        return "{\"scene\":\"" + name + "\",\"size\":\"" + width + "x" + height + "\",\"triangles\":" + triangles
            + ",\"fallbackTriangles\":" + scene.fallbackTriangles
            + ",\"covered\":" + Scene.covered(framebuffer) + ",\"distinct\":" + Scene.distinct(framebuffer)
            + ",\"fnv1a\":\"" + Integer.toHexString(Scene.hash(framebuffer))
            + "\",\"depthFnv1a\":\"" + Integer.toHexString(Scene.hashDepth(depth))
            + "\",\"samples\":" + SAMPLES + ",\"rasterMinMs\":" + times[0]
            + ",\"rasterMedianMs\":" + times[SAMPLES / 2] + ",\"rasterP90Ms\":" + times[SAMPLES * 9 / 10]
            + ",\"rasterMaxMs\":" + times[SAMPLES - 1]
            + ",\"clearMedianMs\":" + clears[SAMPLES / 2] + "}";
    }

    /** One untimed render with SynthAssets variant `variant`; returns a short control row. */
    static String control(String name, Fill fill, int kind, int variant, int width, int height) {
        SynthAssets.setVariant(variant);
        int[] framebuffer = new int[width * height];
        float[] depth = new float[width * height];
        new Scene(fill, width, height).render(kind, framebuffer, depth);
        String row = "{\"scene\":\"" + name + "\",\"size\":\"" + width + "x" + height + "\",\"variant\":" + variant
            + ",\"fnv1a\":\"" + Integer.toHexString(Scene.hash(framebuffer)) + "\"}";
        SynthAssets.setVariant(0);
        return row;
    }

    /** Case list shared by every runtime; the Fill is created per case so state never carries over. */
    static String[] sceneNames() {
        return Scene.NAMES;
    }
}
