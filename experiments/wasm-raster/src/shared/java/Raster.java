/** Adapter boundary for the experiment: the scene drives this, and each backend binds it to a kernel. */
interface Raster {
    /** Binds the target framebuffer (row stride equals width). The clip is the whole target. */
    void bind(int[] framebuffer, int width, int height);

    /** Per-row span mask in target coordinates, as the native face kernel's mask object expects. */
    void setMask(int[] spanStart, int[] spanLength);

    /** Draws one edge through the kernel with the native mode codes: 0 opaque, 1 alpha blend, 2 additive. */
    void edge(int x0, int y0, int x1, int y1, int colour, int mode);
}
