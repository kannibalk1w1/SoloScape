/**
 * Original synthetic geometry: a triangular span mask and a fixed pseudo-random edge set.
 * No native geometry, cache data or assets are used; the generator is a plain integer LCG.
 */
final class Scene {
    static final int EDGES = 6000;
    static final int BACKGROUND = 0xff102030;

    static void render(Raster raster, int width, int height, int[] framebuffer) {
        java.util.Arrays.fill(framebuffer, BACKGROUND);
        raster.bind(framebuffer, width, height);

        int half = width / 2;
        int[] spanStart = new int[height];
        int[] spanLength = new int[height];
        for (int y = 0; y < height; y++) {
            int spread = y * half / (height - 1);
            spanStart[y] = half - spread;
            spanLength[y] = 2 * spread + 1;
        }
        raster.setMask(spanStart, spanLength);

        int seed = 0x5EED;
        for (int e = 0; e < EDGES; e++) {
            seed = seed * 1103515245 + 12345;
            int x0 = (seed >>> 8) % (width + width / 4) - width / 8;
            seed = seed * 1103515245 + 12345;
            int y0 = (seed >>> 8) % (height + height / 4) - height / 8;
            seed = seed * 1103515245 + 12345;
            int x1 = (seed >>> 8) % (width + width / 4) - width / 8;
            seed = seed * 1103515245 + 12345;
            int y1 = (seed >>> 8) % (height + height / 4) - height / 8;
            seed = seed * 1103515245 + 12345;
            int rgb = (seed >>> 8) & 0xffffff;
            int mode = e % 3;
            int alpha = mode == 0 ? 0xff : mode == 1 ? 64 + (seed >>> 4) % 192 : 32 + (seed >>> 4) % 128;
            raster.edge(x0, y0, x1, y1, alpha << 24 | rgb, mode);
        }
    }

    /** FNV-1a over 32-bit framebuffer words; identical arithmetic on the JVM and in WasmGC. */
    static int hash(int[] framebuffer) {
        int h = 0x811c9dc5;
        for (int px : framebuffer) {
            h ^= px;
            h *= 0x01000193;
        }
        return h;
    }
}
