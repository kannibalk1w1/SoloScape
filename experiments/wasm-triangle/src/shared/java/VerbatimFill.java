/** Drives the extracted native Class109 through the Fill seam. */
final class VerbatimFill implements Fill {
    private Class109 raster;

    public void bind(int[] framebuffer, float[] depth, int width, int height) {
        ha_Sub1 renderer = new ha_Sub1();
        renderer.anInt7477 = width;
        renderer.anIntArray7483 = framebuffer;
        renderer.aFloatArray7511 = depth;
        Class167 context = new Class167();
        context.aBoolean2202 = true;
        raster = new Class109(renderer, context);
        raster.anInt1679 = width;
        raster.anInt1672 = height;
        for (int y = 0; y < height; y++) {
            raster.anIntArray1676[y] = y * width;
        }
    }

    public void setBlend(int blend) {
        raster.anInt1674 = blend;
    }

    public void setXClip(boolean needed) {
        raster.aBoolean1671 = needed;
    }

    public void triangle(float y0, float y1, float y2, float x0, float x1, float x2, float z0, float z1, float z2, int colour) {
        raster.method1018(y0, y1, y2, x0, x1, x2, z0, z1, z2, colour);
    }
}
