/**
 * The only seam between the original synthetic scene and the native Class109 material fills: the
 * scene sets the state a model caller sets, then submits triangles through four entry points that
 * map one-to-one to Class109.method1022 / 1027 / 1024 / 1020.
 */
interface Fill {
    int SHADED = 0;
    int GOURAUD = 1;
    int TEX1 = 2;
    int TEX3 = 3;

    /** One screen-space triangle plus every per-kind attribute; unused attributes are ignored. */
    final class Tri {
        final float[] y = new float[3];
        final float[] x = new float[3];
        final float[] z = new float[3];
        final float[] u = new float[3];
        final float[] v = new float[3];
        /** Palette index per vertex (SHADED). */
        final float[] palette = new float[3];
        /** ARGB per vertex (GOURAUD, TEX1, TEX3). */
        final int[] colour = new int[3];
        int fogColour;
        final int[] fogAlpha = new int[3];
        /** Texture ids and UV scales for the three layers (TEX1 uses layer 0 only). */
        final int[] texture = new int[3];
        final float[] scale = new float[3];
    }

    /** Binds the buffers and clip rectangle, installs the palette and resets the texture-state cache. */
    void bind(int[] framebuffer, float[] depth, int width, int height);

    void setBlend(int blend);

    void setXClip(boolean needed);

    void draw(int kind, Tri t);
}
