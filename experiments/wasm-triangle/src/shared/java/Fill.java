/**
 * The only seam between the original synthetic scene and the native triangle fill: the scene sets
 * the same Class109 state a model caller sets, then submits one flat-colour triangle.
 */
interface Fill {
    /** Binds the pixel and depth buffers and the clip rectangle (0..width, 0..height). */
    void bind(int[] framebuffer, float[] depth, int width, int height);

    /** Translucency as the native model path sets it: 0 opaque, 1..254 blend weight, 254 special. */
    void setBlend(int blend);

    /** The native callers set this when any x vertex lies outside 0..width. Y is clipped inside the fill. */
    void setXClip(boolean needed);

    /** Screen-space y, x and depth per vertex, then the packed colour word. */
    void triangle(float y0, float y1, float y2, float x0, float x1, float x2, float z0, float z1, float z2, int colour);
}
