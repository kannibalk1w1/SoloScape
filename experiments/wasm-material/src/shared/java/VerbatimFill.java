/** Drives the extracted native Class109 through the Fill seam. */
final class VerbatimFill implements Fill {
    private Class109 raster;

    public void bind(int[] framebuffer, float[] depth, int width, int height) {
        ha_Sub1 renderer = new ha_Sub1();
        renderer.anInt7477 = width;
        renderer.anIntArray7483 = framebuffer;
        renderer.aFloatArray7511 = depth;
        renderer.anInt7501 = SynthAssets.LARGE;
        Class126.anIntArray4983 = SynthAssets.palette();
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

    public void draw(int kind, Tri t) {
        float[] y = t.y, x = t.x, z = t.z, u = t.u, v = t.v;
        int[] c = t.colour, f = t.fogAlpha, id = t.texture;
        switch (kind) {
            case SHADED:
                raster.method1022(y[0], y[1], y[2], x[0], x[1], x[2], z[0], z[1], z[2],
                    t.palette[0], t.palette[1], t.palette[2]);
                break;
            case GOURAUD:
                raster.method1027(y[0], y[1], y[2], x[0], x[1], x[2], z[0], z[1], z[2], c[0], c[1], c[2]);
                break;
            case TEX1:
                raster.method1024(y[0], y[1], y[2], x[0], x[1], x[2], z[0], z[1], z[2],
                    u[0], u[1], u[2], v[0], v[1], v[2], c[0], c[1], c[2], t.fogColour, f[0], f[1], f[2], id[0]);
                break;
            default:
                raster.method1020(y[0], y[1], y[2], x[0], x[1], x[2], z[0], z[1], z[2],
                    u[0], u[1], u[2], v[0], v[1], v[2], c[0], c[1], c[2], t.fogColour, f[0], f[1], f[2],
                    id[0], t.scale[0], id[1], t.scale[1], id[2], t.scale[2]);
                break;
        }
    }
}
