/** One case's configuration. Variants exercise the adapter's side effects; `illegal` drives negative controls. */
final class FaceCase {
    static final String[] VARIANTS = {"mask0", "maskbit", "floatarr"};
    final String name;
    final int width, height, camera, variant;
    final boolean control;
    /** 0 none; 1 colour pass state 0; 2 textured face; 3 lit path; 4 near-plane misses (JVM negative controls only). */
    final int illegal;

    FaceCase(String name, int width, int height, int camera, int variant, boolean control, int illegal) {
        this.name = name;
        this.width = width;
        this.height = height;
        this.camera = camera;
        this.variant = variant;
        this.control = control;
        this.illegal = illegal;
    }
}

/** What a run exposes after the native `method654` returned. Counters are only available on the extracted builds. */
final class Observed {
    int[] x, y, z;
    boolean shortCleared, byteCleared;
    boolean hasCounters;
    int adapterEntries, adapterIllegal, stubHits;
    String counters = "null";
}

/** The seam between the scene and one implementation (native jar by reflection, or the extracted source). */
interface FaceRig {
    void setup(FaceCase c, FaceMesh mesh, int[] framebuffer, float[] depth);

    /** Runs the native Class64_Sub1.method654 with i == -1 and flags 0. */
    void project();

    Observed observe(int vertexCount);

    /** Class109.method1018 with the translucency 0 and the given x-clip flag, as method635 would call it. */
    void directFill(boolean xClip, float y0, float y1, float y2, float x0, float x1, float x2, float z0, float z1,
        float z2, int colour);
}
