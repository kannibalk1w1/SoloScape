/**
 * Clip mode (opt-in): near-plane clipping through the real method654 projection on original synthetic flat triangles.
 * Camera 0 only (the fast path). Each case is one model, so the model-level and face-level rejections stay separate.
 *
 * Camera-space points come from the integer lattice lat(xc, k, m) = {xc, 4k + 3m, -3k + 4m}. For camera 0 that gives
 * camera x = xc, camera y = 5k and camera depth = 2400 + 5m in real arithmetic (view rows (0.8, 0.6) on y and z).
 * Nothing here decides eligibility or expected counts: the Python checker derives both from the native arrays.
 */
final class ClipScene {
    static final int[][] SIZES = {{765, 503}, {1280, 800}};

    static int[] lat(int xc, int k, int m) {
        return new int[] {xc, 4 * k + 3 * m, -3 * k + 4 * m};
    }

    static final class Case {
        final String name;
        final int[][] vertices, faces;

        Case(String name, int[][] vertices, int[][] faces) {
            this.name = name;
            this.vertices = vertices;
            this.faces = faces;
        }
    }

    private static final int[] F1 = lat(-40, 8, -320), F2 = lat(40, 8, -320), F = lat(0, 8, -320);
    private static final int[] BH = lat(0, -1, -471), B1 = lat(-20, -1, -471), B2 = lat(20, -1, -471), B3 = lat(0, 1, -471);
    /**
     * Front at depth exactly 50.0 in float32, found by emulating method654's float order (2400 + 0.6f * y + 0.8f * z).
     * Lattice points near 50 round just under it (for example lat(0, 8, -470) gives 49.99988), so they are behind.
     */
    private static final int[] E = {0, -1382, -1901};
    /** Depth 49.8 (behind; integer depth 49) and 50.2 (front; integer depth 50): the nearest reachable pair to 50. */
    private static final int[] CM = {0, -1377, -1905}, CP = {0, -1379, -1903};

    static Case[] cases() {
        return new Case[] {
            new Case("one-behind-quad", new int[][] {F1, F2, BH}, new int[][] {{0, 1, 2}}),
            new Case("one-behind-quad-reversed", new int[][] {F1, F2, BH}, new int[][] {{1, 0, 2}}),
            new Case("two-behind-triangle", new int[][] {F, B1, B2}, new int[][] {{0, 2, 1}}),
            new Case("two-behind-triangle-reversed", new int[][] {F, B1, B2}, new int[][] {{0, 1, 2}}),
            new Case("exact-near-50", new int[][] {F1, F2, E}, new int[][] {{1, 0, 2}}),
            new Case("crossing-49.8-behind", new int[][] {F1, F2, CM}, new int[][] {{1, 0, 2}}),
            new Case("crossing-50.2-front", new int[][] {F1, F2, CP}, new int[][] {{1, 0, 2}}),
            // Every vertex is behind and the whole bound (2400 + 0.6 * maxY + radius) is at or under the near plane.
            new Case("model-all-behind", new int[][] {{-40, -5000, -200}, {40, -5000, -200}, {0, -5000, 200}},
                new int[][] {{0, 1, 2}}),
            // Companion front face {2, 1, 0} plus one all-behind face {3, 4, 5} (eligible winding) in the same model.
            new Case("face-all-behind-companion", new int[][] {F2, F1, E, B1, B3, B2}, new int[][] {{0, 1, 2}, {3, 4, 5}}),
        };
    }

    private static void ints(StringBuilder sb, String key, int[] a) {
        sb.append(",\"").append(key).append("\":[");
        for (int i = 0; i < a.length; i++) sb.append(i == 0 ? "" : ",").append(a[i]);
        sb.append(']');
    }

    private static void nested(StringBuilder sb, String key, int[][] rows) {
        sb.append(",\"").append(key).append("\":[");
        for (int i = 0; i < rows.length; i++) {
            sb.append(i == 0 ? "[" : ",[");
            for (int j = 0; j < rows[i].length; j++) sb.append(j == 0 ? "" : ",").append(rows[i][j]);
            sb.append(']');
        }
        sb.append(']');
    }

    /** One JSON object per case and size. Raw observations only: projected and camera arrays, hashes and counters. */
    static String run(FaceRig rig, Case c, int width, int height, int illegal) {
        FaceMesh mesh = FaceMesh.custom(c.vertices, c.faces);
        int[] fb = new int[width * height];
        float[] depth = new float[fb.length];
        java.util.Arrays.fill(fb, FaceScene.BACKGROUND);
        java.util.Arrays.fill(depth, FaceScene.FAR);
        String size = width + "x" + height;
        rig.setup(new FaceCase(c.name, width, height, 0, 0, false, illegal), mesh, fb, depth);
        rig.project();
        Observed o = rig.observe(mesh.vertices);
        int n = mesh.vertices;
        StringBuilder sb = new StringBuilder("{\"case\":\"").append(c.name).append('-').append(size)
            .append("\",\"size\":\"").append(size).append("\",\"illegal\":").append(illegal)
            .append(",\"vertexCount\":").append(n).append(",\"faceCount\":").append(mesh.faces);
        nested(sb, "vertices", c.vertices);
        nested(sb, "faces", c.faces);
        ints(sb, "projX", o.x);
        ints(sb, "projY", o.y);
        ints(sb, "projZ", o.z);
        ints(sb, "camX", o.camX);
        ints(sb, "camY", o.camY);
        ints(sb, "camD", o.camD);
        sb.append(",\"fnv1a\":\"").append(Integer.toHexString(FaceScene.fnv(fb, fb.length))).append("\",\"depthFnv1a\":\"")
            .append(Integer.toHexString(FaceScene.fnvDepth(depth))).append("\",\"covered\":").append(FaceScene.covered(fb))
            .append(",\"adapterEntries\":").append(o.adapterEntries).append(",\"adapterIllegal\":").append(o.adapterIllegal)
            .append(",\"counters\":").append(o.counters);
        ints(sb, "clipOut", o.clipOut == null ? new int[0] : o.clipOut);
        if (o.clipOut == null) sb.append(",\"clipOutNative\":true");
        sb.append(",\"flatFillEntries\":").append(o.flatFillEntries < 0 ? "null" : String.valueOf(o.flatFillEntries));
        return sb.append('}').toString();
    }
}
