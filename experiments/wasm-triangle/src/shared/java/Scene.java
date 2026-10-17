/**
 * Original synthetic geometry for the triangle gates. A plain integer LCG and integer projection
 * generate every vertex; no native model, cache data or asset is used. Coordinates scale with the
 * frame size so both sizes show the same composition.
 */
final class Scene {
    static final int BACKGROUND = 0xff102030;
    static final int SINGLE = 0;
    static final int MESH = 1;
    /** The single triangle repeated 64 times at decreasing depth, so each pass writes and is timeable. */
    static final int SINGLE_BATCH = 2;
    private static final float FAR = Float.MAX_VALUE;

    private final Fill fill;
    private final int width;
    private final int height;
    private int seed;
    int triangles;

    Scene(Fill fill, int width, int height) {
        this.fill = fill;
        this.width = width;
        this.height = height;
    }

    private int next() {
        seed = seed * 1103515245 + 12345;
        return seed >>> 8;
    }

    private static int rgb(int r, int g, int b) {
        return 0xff000000 | (r & 0xff) << 16 | (g & 0xff) << 8 | (b & 0xff);
    }

    /** Submits one triangle, setting the x-clip flag the way the native model callers derive it. */
    private void tri(int x0, int y0, float z0, int x1, int y1, float z1, int x2, int y2, float z2, int colour, int blend) {
        boolean xClip = x0 < 0 || x1 < 0 || x2 < 0 || x0 > width || x1 > width || x2 > width;
        fill.setXClip(xClip);
        fill.setBlend(blend);
        fill.triangle(y0, y1, y2, x0, x1, x2, z0, z1, z2, colour);
        triangles++;
    }

    /** Clears both buffers and binds a fresh native raster context. This is set-up, not triangle work. */
    void begin(int[] framebuffer, float[] depth) {
        java.util.Arrays.fill(framebuffer, BACKGROUND);
        java.util.Arrays.fill(depth, FAR);
    }

    /** Binds a fresh native raster context (constructor plus row-offset table). */
    void bind(int[] framebuffer, float[] depth) {
        fill.bind(framebuffer, depth, width, height);
    }

    /** Submits every triangle of one scene; returns the number submitted. This is the timed raster step. */
    int draw(int kind) {
        triangles = 0;
        seed = 0x7A11;
        if (kind == SINGLE) {
            single();
        } else if (kind == SINGLE_BATCH) {
            for (int i = 0; i < 64; i++) {
                tri(pw(20), ph(15), 100f - i * 0.5f, pw(80), ph(30), 100f - i * 0.5f, pw(40), ph(85), 100f - i * 0.5f,
                    rgb(0x30 + i, 0x90, 0xe0 - i), 0);
            }
        } else {
            mesh();
        }
        return triangles;
    }

    /** Convenience for correctness runs: begin, bind and draw. */
    int render(int kind, int[] framebuffer, float[] depth) {
        begin(framebuffer, depth);
        bind(framebuffer, depth);
        return draw(kind);
    }

    private void single() {
        tri(pw(20), ph(15), 100f, pw(80), ph(30), 100f, pw(40), ph(85), 100f, rgb(0x30, 0x90, 0xe0), 0);
    }

    private int pw(int percent) {
        return width * percent / 100;
    }

    private int ph(int percent) {
        return height * percent / 100;
    }

    private void mesh() {
        terrain();
        // Two large triangles whose depth planes cross, so the per-pixel depth test decides the seam.
        tri(pw(5), ph(20), 200f, pw(95), ph(25), 900f, pw(40), ph(95), 500f, rgb(0xe0, 0x60, 0x40), 0);
        tri(pw(8), ph(88), 900f, pw(92), ph(80), 200f, pw(55), ph(12), 500f, rgb(0x40, 0xd0, 0x70), 0);
        // Triangles that run past every screen edge exercise vertical and horizontal clipping.
        tri(-pw(30), -ph(40), 650f, pw(130), ph(30), 650f, pw(20), ph(140), 650f, rgb(0x90, 0x40, 0xc0), 0);
        tri(pw(60), -ph(30), 150f, pw(120), ph(10), 150f, pw(80), ph(70), 150f, rgb(0xf0, 0xd0, 0x30), 0);
        tri(-pw(20), ph(60), 120f, pw(30), ph(120), 120f, -pw(25), ph(110), 120f, rgb(0x30, 0xc0, 0xc0), 0);
        // Translucent overlays (native blend weight in the model path) and the 254 special mode.
        tri(pw(10), ph(30), 80f, pw(70), ph(35), 80f, pw(30), ph(75), 80f, rgb(0xff, 0xff, 0xff), 128);
        tri(pw(35), ph(10), 60f, pw(90), ph(60), 60f, pw(25), ph(70), 60f, rgb(0x20, 0x20, 0xa0), 64);
        tri(pw(45), ph(40), 50f, pw(95), ph(45), 50f, pw(60), ph(90), 50f, rgb(0x80, 0x20, 0x20), 254);
        // Many small triangles with random depth stress overlap and the depth buffer.
        int small = 1500;
        for (int i = 0; i < small; i++) {
            int cx = next() % width;
            int cy = next() % height;
            int r = 6 + next() % (width / 20);
            int x0 = cx + next() % r - r / 2;
            int y0 = cy + next() % r - r / 2;
            int x1 = cx + next() % r - r / 2;
            int y1 = cy + next() % r - r / 2;
            int x2 = cx + next() % r - r / 2;
            int y2 = cy + next() % r - r / 2;
            float z = 40 + next() % 1000;
            tri(x0, y0, z, x1, y1, z + next() % 40, x2, y2, z + next() % 40, rgb(next(), next(), next()), 0);
        }
    }

    /** A 24x14 height-field in perspective: cheap integer projection, per-triangle flat colour. */
    private void terrain() {
        final int cols = 24, rows = 14;
        int[] sx = new int[(cols + 1) * (rows + 1)];
        int[] sy = new int[sx.length];
        float[] sz = new float[sx.length];
        int focal = width;
        for (int j = 0; j <= rows; j++) {
            for (int i = 0; i <= cols; i++) {
                int bump = next() % 60;
                int wx = (i - cols / 2) * 140;
                int wz = 260 + j * 90;
                int wy = 220 - bump;
                int k = j * (cols + 1) + i;
                sx[k] = width / 2 + wx * focal / (wz * 2);
                sy[k] = height * 40 / 100 + wy * focal / (wz * 2);
                sz[k] = wz;
            }
        }
        for (int j = 0; j < rows; j++) {
            for (int i = 0; i < cols; i++) {
                int a = j * (cols + 1) + i, b = a + 1, c = a + cols + 1, d = c + 1;
                int shade = 70 + (next() % 90);
                int g = shade + j * 6;
                tri(sx[a], sy[a], sz[a], sx[b], sy[b], sz[b], sx[c], sy[c], sz[c], rgb(shade / 2, g, shade / 3), 0);
                tri(sx[b], sy[b], sz[b], sx[d], sy[d], sz[d], sx[c], sy[c], sz[c], rgb(shade / 3, g - 20, shade / 2), 0);
            }
        }
    }

    /** FNV-1a over the 32-bit colour words; identical arithmetic on the JVM and in WasmGC. */
    static int hash(int[] framebuffer) {
        int h = 0x811c9dc5;
        for (int px : framebuffer) {
            h ^= px;
            h *= 0x01000193;
        }
        return h;
    }

    /** FNV-1a over the raw bit patterns of the depth buffer. */
    static int hashDepth(float[] depth) {
        int h = 0x811c9dc5;
        for (float z : depth) {
            h ^= Float.floatToRawIntBits(z);
            h *= 0x01000193;
        }
        return h;
    }

    static int covered(int[] framebuffer) {
        int n = 0;
        for (int px : framebuffer) {
            if (px != BACKGROUND) n++;
        }
        return n;
    }
}
