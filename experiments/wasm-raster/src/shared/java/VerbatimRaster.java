/** Drives the generated verbatim native kernel with the experiment's explicit adapter state. */
final class VerbatimRaster implements Raster {
    private final NativeFaceKernel kernel;
    private aa_Sub3 mask;

    VerbatimRaster(NativeFaceKernel kernel) {
        this.kernel = kernel;
    }

    @Override
    public void bind(int[] framebuffer, int width, int height) {
        kernel.anIntArray7483 = framebuffer;
        kernel.anInt7477 = width;
        kernel.anInt7476 = 0;
        kernel.anInt7503 = height;
        kernel.anInt7496 = 0;
        kernel.anInt7507 = width;
    }

    @Override
    public void setMask(int[] spanStart, int[] spanLength) {
        mask = new aa_Sub3();
        mask.anIntArray5201 = spanStart;
        mask.anIntArray5202 = spanLength;
    }

    @Override
    public void edge(int x0, int y0, int x1, int y1, int colour, int mode) {
        kernel.method3636(x0, y0, x1, y1, colour, mode, mask, 0, 0);
    }
}
