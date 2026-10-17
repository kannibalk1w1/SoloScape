/**
 * Real-clock timing. "raster" is only the triangle submissions; buffer clear is reported separately and
 * presentation is measured by the host.
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
            + ",\"covered\":" + Scene.covered(framebuffer)
            + ",\"fnv1a\":\"" + Integer.toHexString(Scene.hash(framebuffer))
            + "\",\"depthFnv1a\":\"" + Integer.toHexString(Scene.hashDepth(depth))
            + "\",\"samples\":" + SAMPLES + ",\"rasterMinMs\":" + times[0]
            + ",\"rasterMedianMs\":" + times[SAMPLES / 2] + ",\"rasterP90Ms\":" + times[SAMPLES * 9 / 10]
            + ",\"rasterMaxMs\":" + times[SAMPLES - 1]
            + ",\"clearMedianMs\":" + clears[SAMPLES / 2] + "}";
    }
}
