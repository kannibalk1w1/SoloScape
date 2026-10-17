/**
 * Original synthetic geometry for the material gates. A plain integer LCG and integer projection
 * generate every vertex; no native model, cache data or asset is used. The same geometry is shaded,
 * Gouraud-coloured or textured depending on the scene kind, so kinds are comparable.
 */
final class Scene {
    static final int BACKGROUND = 0xff102030;
    static final int SHADED = 0;
    static final int GOURAUD = 1;
    static final int TEX1 = 2;
    static final int TEX3 = 3;
    /** Every fill kind in one depth-tested frame. */
    static final int MIXED = 4;
    static final String[] NAMES = {"shaded", "gouraud", "tex1", "tex3", "mixed"};
    private static final float FAR = Float.MAX_VALUE;

    private final Fill fill;
    private final int width;
    private final int height;
    private final Fill.Tri t = new Fill.Tri();
    private int seed;
    private int kind;
    private int serial;
    int triangles;
    int fallbackTriangles;

    Scene(Fill fill, int width, int height) {
        this.fill = fill;
        this.width = width;
        this.height = height;
    }

    private int next() {
        seed = seed * 1103515245 + 12345;
        return seed >>> 8;
    }

    private int pw(int percent) {
        return width * percent / 100;
    }

    private int ph(int percent) {
        return height * percent / 100;
    }

    private int clampX(float x) {
        return Math.max(0, Math.min(width, (int) x));
    }

    private int clampY(float y) {
        return Math.max(0, Math.min(height, (int) y));
    }

    /**
     * Submits one triangle in the current scene kind. Vertex attributes derive from the vertex
     * position (palette index, colour) or from the supplied texture coordinates.
     */
    private void tri(int x0, int y0, float z0, int x1, int y1, float z1, int x2, int y2, float z2,
                     float[] uv, int blend, int fogBase) {
        int k = kind == MIXED ? serial++ & 3 : kind;
        boolean xClip = x0 < 0 || x1 < 0 || x2 < 0 || x0 > width || x1 > width || x2 > width;
        fill.setXClip(xClip);
        fill.setBlend(blend);
        float[] xs = {x0, x1, x2};
        float[] ys = {y0, y1, y2};
        float[] zs = {z0, z1, z2};
        for (int i = 0; i < 3; i++) {
            t.x[i] = xs[i];
            t.y[i] = ys[i];
            t.z[i] = zs[i];
            t.u[i] = uv[i * 2];
            t.v[i] = uv[i * 2 + 1];
            int cx = clampX(xs[i]);
            int cy = clampY(ys[i]);
            t.palette[i] = 1000 + (cx * 40000 / width + cy * 18000 / height);
            t.colour[i] = 0xff000000 | (cx * 255 / width) << 16 | (cy * 255 / height) << 8 | (255 - cx * 200 / width);
            t.fogAlpha[i] = fogBase;
        }
        t.fogColour = 0x6080a0;
        if (k == Fill.TEX1 || k == Fill.TEX3) {
            // A tenth of the textured triangles reference an id that is not loaded, so the native
            // null-texture fallback (method1027 with blended colours) is exercised too.
            boolean missing = (serial++ % 10) == 9;
            for (int i = 0; i < 3; i++) {
                t.colour[i] = 0xff000000 | 0xe0e0e0 - (i * 0x181818);
            }
            if (missing) {
                fallbackTriangles++;
            }
            int base = 1 + (serial & 3);
            t.texture[0] = missing ? SynthAssets.T_MISSING : base;
            t.texture[1] = 1 + ((base + 1) & 3);
            t.texture[2] = 1 + ((base + 2) & 3);
            t.scale[0] = 1.0f;
            t.scale[1] = 0.5f;
            t.scale[2] = 2.0f;
        }
        fill.draw(k, t);
        triangles++;
    }

    private void tri(int x0, int y0, float z0, int x1, int y1, float z1, int x2, int y2, float z2, int blend) {
        float[] uv = {x0 * 4f / width, y0 * 4f / height, x1 * 4f / width, y1 * 4f / height, x2 * 4f / width, y2 * 4f / height};
        tri(x0, y0, z0, x1, y1, z1, x2, y2, z2, uv, blend, 0);
    }

    /** Clears both buffers. This is set-up, not triangle work. */
    void begin(int[] framebuffer, float[] depth) {
        java.util.Arrays.fill(framebuffer, BACKGROUND);
        java.util.Arrays.fill(depth, FAR);
    }

    /** Binds a fresh native raster context (constructor, palette, row-offset table). */
    void bind(int[] framebuffer, float[] depth) {
        fill.bind(framebuffer, depth, width, height);
    }

    /** Submits every triangle of one scene; returns the number submitted. This is the timed raster step. */
    int draw(int sceneKind) {
        kind = sceneKind;
        triangles = 0;
        fallbackTriangles = 0;
        serial = 0;
        seed = 0x7A11;
        terrain();
        // Two large triangles whose depth planes cross, so the per-pixel depth test decides the seam.
        tri(pw(5), ph(20), 200f, pw(95), ph(25), 900f, pw(40), ph(95), 500f, 0);
        tri(pw(8), ph(88), 900f, pw(92), ph(80), 200f, pw(55), ph(12), 500f, 0);
        // Triangles past every screen edge exercise vertical and horizontal clipping.
        tri(-pw(30), -ph(40), 650f, pw(130), ph(30), 650f, pw(20), ph(140), 650f, 0);
        tri(pw(60), -ph(30), 150f, pw(120), ph(10), 150f, pw(80), ph(70), 150f, 0);
        tri(-pw(20), ph(60), 120f, pw(30), ph(120), 120f, -pw(25), ph(110), 120f, 0);
        // Translucent overlays (native blend weight) and fog-tinted triangles.
        tri(pw(10), ph(30), 80f, pw(70), ph(35), 80f, pw(30), ph(75), 80f, 128);
        tri(pw(35), ph(10), 60f, pw(90), ph(60), 60f, pw(25), ph(70), 60f, 64);
        float[] uv = {0f, 0f, 3f, 0f, 0f, 3f};
        tri(pw(45), ph(40), 50f, pw(95), ph(45), 50f, pw(60), ph(90), 50f, uv, 0, 160);
        // Many small triangles with random depth stress overlap and the depth buffer.
        for (int i = 0; i < 300; i++) {
            int cx = next() % width;
            int cy = next() % height;
            int r = 8 + next() % (width / 12);
            int x0 = cx + next() % r - r / 2;
            int y0 = cy + next() % r - r / 2;
            int x1 = cx + next() % r - r / 2;
            int y1 = cy + next() % r - r / 2;
            int x2 = cx + next() % r - r / 2;
            int y2 = cy + next() % r - r / 2;
            float z = 40 + next() % 1000;
            tri(x0, y0, z, x1, y1, z + next() % 40, x2, y2, z + next() % 40, 0);
        }
        return triangles;
    }

    /** Convenience for correctness runs: begin, bind and draw. */
    int render(int sceneKind, int[] framebuffer, float[] depth) {
        begin(framebuffer, depth);
        bind(framebuffer, depth);
        return draw(sceneKind);
    }

    /** A 24x14 height-field in perspective with world-linear texture coordinates. */
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
                float[] uv1 = {i / 3f, j / 3f, (i + 1) / 3f, j / 3f, i / 3f, (j + 1) / 3f};
                float[] uv2 = {(i + 1) / 3f, j / 3f, (i + 1) / 3f, (j + 1) / 3f, i / 3f, (j + 1) / 3f};
                int fog = j * 14;
                tri(sx[a], sy[a], sz[a], sx[b], sy[b], sz[b], sx[c], sy[c], sz[c], uv1, 0, fog);
                tri(sx[b], sy[b], sz[b], sx[d], sy[d], sz[d], sx[c], sy[c], sz[c], uv2, 0, fog);
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

    /** Number of distinct pixel values: a flat-colour stand-in would produce a handful. */
    static int distinct(int[] framebuffer) {
        int[] sorted = framebuffer.clone();
        java.util.Arrays.sort(sorted);
        int n = 0;
        for (int i = 0; i < sorted.length; i++) {
            if (i == 0 || sorted[i] != sorted[i - 1]) n++;
        }
        return n;
    }
}
