/** Times the raster kernel over repeated frames and reports median milliseconds. */
final class Bench {
    interface Clock {
        double nowMs();
    }

    static final int FRAMES = 7;

    /** Returns one JSON object: size, hash and median raster milliseconds (first frame is warm-up). */
    static String measure(Clock clock, Raster raster, int width, int height, int[] framebuffer) {
        double[] times = new double[FRAMES - 1];
        int hash = 0;
        for (int f = 0; f < FRAMES; f++) {
            double t0 = clock.nowMs();
            Scene.render(raster, width, height, framebuffer);
            double t1 = clock.nowMs();
            if (f > 0) times[f - 1] = t1 - t0;
            hash = Scene.hash(framebuffer);
        }
        for (int i = 1; i < times.length; i++) {
            double v = times[i];
            int j = i - 1;
            while (j >= 0 && times[j] > v) {
                times[j + 1] = times[j];
                j--;
            }
            times[j + 1] = v;
        }
        double median = times[times.length / 2];
        return "{\"size\":\"" + width + "x" + height + "\",\"fnv1a\":\"" + Integer.toHexString(hash)
            + "\",\"rasterMedianMs\":" + median + ",\"rasterMinMs\":" + times[0] + "}";
    }
}
