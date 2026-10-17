/**
 * ORIGINAL synthetic palette and textures for the material gates. Pure integer arithmetic, no cache
 * data, no native assets. The variant switch exists for negative controls: a different variant must
 * change the rendered pixels, which a flat-fill stand-in could not do.
 */
final class SynthAssets {
    static final int SMALL = 64;
    static final int LARGE = 128;
    /** Texture ids with content; every other id is "not loaded" and takes the native null-texture fallback. */
    static final int T_OPAQUE = 1;
    static final int T_ALPHA_TEST = 2;
    static final int T_ALPHA_CHANNEL = 3;
    static final int T_OPAQUE_LARGE = 4;
    static final int T_MISSING = 99;

    private static int variant;
    private static int[] palette;
    private static final int[][] TEXELS = new int[5][];

    private SynthAssets() {
    }

    /** Variant 0 is the reference; any other value perturbs palette and texels. */
    static void setVariant(int v) {
        variant = v;
        palette = null;
        for (int i = 0; i < TEXELS.length; i++) {
            TEXELS[i] = null;
        }
    }

    /** 65536 opaque entries: hue from the high byte, lightness from the low byte. */
    static int[] palette() {
        if (palette == null) {
            int[] p = new int[65536];
            for (int i = 0; i < p.length; i++) {
                int hue = ((i >> 8) * 6 + variant * 40) & 0xff;
                int light = i & 0xff;
                int r = wave(hue) * light / 255;
                int g = wave(hue + 85) * light / 255;
                int b = wave(hue + 170) * light / 255;
                p[i] = 0xff000000 | r << 16 | g << 8 | b;
            }
            palette = p;
        }
        return palette;
    }

    private static int wave(int h) {
        int t = h & 0xff;
        t = t < 128 ? t : 255 - t;
        return 64 + t * 191 / 127;
    }

    static boolean small(int id) {
        return id == T_OPAQUE || id == T_ALPHA_CHANNEL;
    }

    /** Texture mode as the native material record exposes it: 0 opaque, 1 alpha test, 2 alpha channel. */
    static int mode(int id) {
        return id == T_ALPHA_TEST ? 1 : id == T_ALPHA_CHANNEL ? 2 : 0;
    }

    static boolean wrapsRepeat(int id) {
        return true;
    }

    /** Returns the texel array for a loaded id, or null (native: material not available). */
    static int[] texels(int id) {
        if (id < 1 || id > 4) {
            return null;
        }
        if (TEXELS[id] == null) {
            int size = small(id) ? SMALL : LARGE;
            int[] t = new int[size * size];
            for (int y = 0; y < size; y++) {
                for (int x = 0; x < size; x++) {
                    t[y * size + x] = texel(id, x, y, size);
                }
            }
            TEXELS[id] = t;
        }
        return TEXELS[id];
    }

    private static int texel(int id, int x, int y, int size) {
        int cell = (x * 8 / size + y * 8 / size) & 1;
        switch (id) {
            case T_OPAQUE: {
                int r = cell == 0 ? 220 : 60;
                int g = 40 + x * 190 / size;
                int b = 40 + y * 190 / size;
                return 0xff000000 | (r + variant * 11 & 0xff) << 16 | g << 8 | b;
            }
            case T_ALPHA_TEST: {
                int dx = x - size / 2;
                int dy = y - size / 2;
                int d2 = dx * dx + dy * dy;
                boolean ring = d2 > size * size / 25 && d2 < size * size / 5;
                if (!ring) {
                    return 0;
                }
                return 0xff000000 | (200 - (x * 3 + variant * 9 & 0x7f)) << 16 | 0xd0 << 8 | (60 + y);
            }
            case T_ALPHA_CHANNEL: {
                int a = 255 - x * 3;
                return a << 24 | (30 + y * 3 & 0xff) << 16 | (x * 4 & 0xff) << 8 | (200 + variant * 5 & 0xff);
            }
            default: {
                int band = (x / 8 + y / 16) & 3;
                int r = band * 60 + 20;
                return 0xff000000 | r << 16 | (255 - r) << 8 | (x * 2 & 0xff);
            }
        }
    }
}
