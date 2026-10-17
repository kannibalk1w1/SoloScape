/**
 * Runs one case through a rig and validates it. Everything the checker later compares is derived here
 * from the projected integer arrays, never from the implementation's own bookkeeping:
 *  - front/back classification is recomputed from the projected x/y with long arithmetic;
 *  - the framebuffer is re-rendered by calling the flat fill directly for the front faces in index order,
 *    and must equal the framebuffer produced through method650/method643/method635.
 */
final class FaceScene {
    static final int BACKGROUND = 0xff102030;
    static final float FAR = Float.MAX_VALUE;
    static final int NEAR = 50;

    static int fnv(int[] a, int n) {
        int h = 0x811c9dc5;
        for (int i = 0; i < n; i++) {
            h ^= a[i];
            h *= 0x01000193;
        }
        return h;
    }

    static int fnvDepth(float[] d) {
        int h = 0x811c9dc5;
        for (float z : d) {
            h ^= Float.floatToRawIntBits(z);
            h *= 0x01000193;
        }
        return h;
    }

    static int covered(int[] fb) {
        int n = 0;
        for (int px : fb) if (px != BACKGROUND) n++;
        return n;
    }

    static int distinct(int[] fb) {
        int[] copy = fb.clone();
        java.util.Arrays.sort(copy);
        int n = 0;
        for (int i = 0; i < copy.length; i++) if (i == 0 || copy[i] != copy[i - 1]) n++;
        return n;
    }

    private static void clear(int[] fb, float[] depth) {
        java.util.Arrays.fill(fb, BACKGROUND);
        java.util.Arrays.fill(depth, FAR);
    }

    private static void list(StringBuilder sb, String key, int[] a, int n) {
        sb.append(",\"").append(key).append("\":[");
        for (int i = 0; i < n; i++) sb.append(i == 0 ? "" : ",").append(a[i]);
        sb.append(']');
    }

    /** Returns one JSON object, or throws if the run is not a legitimate flat-face run. */
    static String run(FaceRig rig, FaceCase c, boolean perturbOverride) {
        FaceMesh mesh = FaceMesh.build(c.control || perturbOverride);
        int[] fb = new int[c.width * c.height];
        float[] depth = new float[c.width * c.height];
        clear(fb, depth);
        rig.setup(c, mesh, fb, depth);
        rig.project();
        Observed o = rig.observe(mesh.vertices);
        int n = mesh.vertices;
        if (o.x.length < n || o.y.length < n || o.z.length < n) throw new IllegalStateException(c.name + ": short projection arrays");
        if (o.hasCounters) {
            if (o.adapterEntries != 1) throw new IllegalStateException(c.name + ": adapter entries " + o.adapterEntries);
            if (o.adapterIllegal != 0) throw new IllegalStateException(c.name + ": adapter illegal state hit");
            if (o.stubHits != 0) throw new IllegalStateException(c.name + ": stub reached " + o.counters);
        }
        int minDepth = Integer.MAX_VALUE;
        for (int i = 0; i < n; i++) {
            if (o.x[i] == -5000) throw new IllegalStateException(c.name + ": near-plane miss at vertex " + i);
            if (o.z[i] < minDepth) minDepth = o.z[i];
        }
        if (minDepth < NEAR) throw new IllegalStateException(c.name + ": vertex nearer than the near plane");
        boolean expectShort = c.variant == 0;
        if (o.shortCleared != expectShort) throw new IllegalStateException(c.name + ": aShortArray5311 cleared=" + o.shortCleared);
        if (!o.byteCleared) throw new IllegalStateException(c.name + ": aByteArray5386 not cleared");

        int pipelineColour = fnv(fb, fb.length);
        int pipelineDepth = fnvDepth(depth);
        int coveredPixels = covered(fb);
        int distinctColours = distinct(fb);
        if (coveredPixels <= 0) throw new IllegalStateException(c.name + ": nothing was drawn");

        int[] palette = FaceMesh.palette();
        boolean[] front = new boolean[mesh.faces];
        int frontCount = 0;
        for (int f = 0; f < mesh.faces; f++) {
            int a = mesh.fa[f], b = mesh.fb[f], d = mesh.fc[f];
            long area = (long) (o.x[a] - o.x[b]) * (o.y[d] - o.y[b]) - (long) (o.y[a] - o.y[b]) * (o.x[d] - o.x[b]);
            front[f] = area > 0;
            if (front[f]) frontCount++;
        }
        int backCount = mesh.faces - frontCount;
        if (backCount < 1 || frontCount < 1) throw new IllegalStateException(c.name + ": no back-face culling exercised");

        // Independent re-render of exactly the front faces, in index order, straight into the flat fill.
        clear(fb, depth);
        for (int f = 0; f < mesh.faces; f++) {
            if (!front[f]) continue;
            int a = mesh.fa[f], b = mesh.fb[f], d = mesh.fc[f];
            boolean xClip = o.x[a] < 0 || o.x[b] < 0 || o.x[d] < 0 || o.x[a] > c.width || o.x[b] > c.width || o.x[d] > c.width;
            rig.directFill(xClip, o.y[a], o.y[b], o.y[d], o.x[a], o.x[b], o.x[d], o.z[a], o.z[b], o.z[d],
                palette[mesh.colourIndex[f]]);
        }
        int directColour = fnv(fb, fb.length);
        int directDepth = fnvDepth(depth);
        // Native exception counts are unavailable, so this equality detects changed VISIBLE output only; it does
        // not prove that no exception was swallowed inside the native face loop.
        if (directColour != pipelineColour || directDepth != pipelineDepth)
            throw new IllegalStateException(c.name + ": pipeline output differs from the direct front-face fill");

        // Anti-bypass control: the same projected triangles with NO culling (every face straight into the flat fill).
        // The checker requires this to differ from the front-only frame for at least one canonical case per size.
        clear(fb, depth);
        for (int f = 0; f < mesh.faces; f++) {
            int a = mesh.fa[f], b = mesh.fb[f], d = mesh.fc[f];
            boolean xClip = o.x[a] < 0 || o.x[b] < 0 || o.x[d] < 0 || o.x[a] > c.width || o.x[b] > c.width || o.x[d] > c.width;
            rig.directFill(xClip, o.y[a], o.y[b], o.y[d], o.x[a], o.x[b], o.x[d], o.z[a], o.z[b], o.z[d],
                palette[mesh.colourIndex[f]]);
        }
        int allColour = fnv(fb, fb.length);
        int allDepth = fnvDepth(depth);
        int allCovered = covered(fb);
        // Restore the front-only frame (the one the pipeline produced) before anything is presented.
        clear(fb, depth);
        for (int f = 0; f < mesh.faces; f++) {
            if (!front[f]) continue;
            int a = mesh.fa[f], b = mesh.fb[f], d = mesh.fc[f];
            boolean xClip = o.x[a] < 0 || o.x[b] < 0 || o.x[d] < 0 || o.x[a] > c.width || o.x[b] > c.width || o.x[d] > c.width;
            rig.directFill(xClip, o.y[a], o.y[b], o.y[d], o.x[a], o.x[b], o.x[d], o.z[a], o.z[b], o.z[d],
                palette[mesh.colourIndex[f]]);
        }
        if (fnv(fb, fb.length) != pipelineColour || fnvDepth(depth) != pipelineDepth)
            throw new IllegalStateException(c.name + ": front-only frame not restored");

        StringBuilder sb = new StringBuilder("{\"case\":\"").append(c.name).append("\",\"size\":\"").append(c.width).append('x')
            .append(c.height).append("\",\"camera\":").append(c.camera).append(",\"variant\":\"").append(FaceCase.VARIANTS[c.variant])
            .append("\",\"control\":").append(c.control || perturbOverride).append(",\"vertices\":").append(n)
            .append(",\"faces\":").append(mesh.faces).append(",\"front\":").append(frontCount).append(",\"back\":").append(backCount)
            .append(",\"minDepth\":").append(minDepth).append(",\"covered\":").append(coveredPixels)
            .append(",\"distinct\":").append(distinctColours)
            .append(",\"fnv1a\":\"").append(Integer.toHexString(pipelineColour)).append("\",\"depthFnv1a\":\"")
            .append(Integer.toHexString(pipelineDepth)).append("\",\"directFnv1a\":\"").append(Integer.toHexString(directColour))
            .append("\",\"directDepthFnv1a\":\"").append(Integer.toHexString(directDepth))
            .append("\",\"allFacesFnv1a\":\"").append(Integer.toHexString(allColour)).append("\",\"allFacesDepthFnv1a\":\"")
            .append(Integer.toHexString(allDepth)).append("\",\"allFacesCovered\":").append(allCovered)
            .append(",\"shortCleared\":").append(o.shortCleared).append(",\"byteCleared\":").append(o.byteCleared)
            .append(",\"counters\":").append(o.counters);
        list(sb, "projX", o.x, n);
        list(sb, "projY", o.y, n);
        list(sb, "projZ", o.z, n);
        return sb.append('}').toString();
    }

    /** The case matrix every runtime runs, in order. */
    static FaceCase[] cases(int illegal) {
        int[][] sizes = {{765, 503}, {1280, 800}};
        java.util.ArrayList<FaceCase> list = new java.util.ArrayList<>();
        for (int[] s : sizes) {
            String sz = s[0] + "x" + s[1];
            list.add(new FaceCase("cam0-mask0-" + sz, s[0], s[1], 0, 0, false, illegal));
            list.add(new FaceCase("cam1-mask0-" + sz, s[0], s[1], 1, 0, false, illegal));
            list.add(new FaceCase("cam0-maskbit-" + sz, s[0], s[1], 0, 1, false, illegal));
            list.add(new FaceCase("cam0-floatarr-" + sz, s[0], s[1], 0, 2, false, illegal));
            list.add(new FaceCase("cam0-mask0-vertex-control-" + sz, s[0], s[1], 0, 0, true, illegal));
        }
        return list.toArray(new FaceCase[0]);
    }
}
