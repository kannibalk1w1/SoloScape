/**
 * One case of the decoded-model bridge. It mirrors FaceScene.run (projection through the rig, adapter counters, a
 * front-face fill re-rendered directly, and an all-faces bypass that must differ) but takes its mesh from DecodeMesh,
 * the native-decoded Class124 arrays, instead of FaceMesh.build. The output also carries the decoded arrays, so the
 * checker compares them with the original design.
 */
final class BridgeScene {
    private BridgeScene() {}

    private static void clear(int[] fb, float[] depth) {
        java.util.Arrays.fill(fb, FaceScene.BACKGROUND);
        java.util.Arrays.fill(depth, FaceScene.FAR);
    }

    private static boolean clipped(Observed o, int a, int b, int k, int width) {
        return o.x[a] < 0 || o.x[b] < 0 || o.x[k] < 0 || o.x[a] > width || o.x[b] > width || o.x[k] > width;
    }

    /** Flat fill of each selected face (all faces when select is null), in index order, straight from projected x/y/z. */
    private static void fill(FaceRig rig, FaceMesh mesh, Observed o, boolean[] select, int width, int[] palette) {
        for (int f = 0; f < mesh.faces; f++) {
            if (select != null && !select[f]) continue;
            int a = mesh.fa[f], b = mesh.fb[f], k = mesh.fc[f];
            rig.directFill(clipped(o, a, b, k, width), o.y[a], o.y[b], o.y[k], o.x[a], o.x[b], o.x[k], o.z[a], o.z[b],
                o.z[k], palette[mesh.colourIndex[f]]);
        }
    }

    private static void ints(StringBuilder sb, String key, int[] values) {
        sb.append(",\"").append(key).append("\":[");
        for (int i = 0; i < values.length; i++) sb.append(i == 0 ? "" : ",").append(values[i]);
        sb.append(']');
    }

    private static void shorts(StringBuilder sb, String key, short[] values) {
        sb.append(",\"").append(key).append("\":[");
        for (int i = 0; i < values.length; i++) sb.append(i == 0 ? "" : ",").append(values[i]);
        sb.append(']');
    }

    private static String hex(int value) {
        return Integer.toHexString(value);
    }

    /** Returns one JSON object, or throws if the run is not a legitimate decoded flat-face run. */
    static String run(String runtime, String fixture, int decodeStubs, FaceRig rig, FaceCase c, DecodeMesh d) {
        FaceMesh mesh = d.mesh;
        int n = mesh.vertices;
        if (n != d.vertexCount || mesh.faces != d.faceCount) throw new IllegalStateException(c.name + ": mesh counts differ");
        int[] palette = FaceMesh.palette();
        int[] fb = new int[c.width * c.height];
        float[] depth = new float[fb.length];
        clear(fb, depth);
        rig.setup(c, mesh, fb, depth);
        rig.project();
        Observed o = rig.observe(n);
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
        if (minDepth < FaceScene.NEAR) throw new IllegalStateException(c.name + ": vertex nearer than the near plane");
        if (o.shortCleared != (c.variant == 0)) throw new IllegalStateException(c.name + ": aShortArray5311 cleared=" + o.shortCleared);
        if (!o.byteCleared) throw new IllegalStateException(c.name + ": aByteArray5386 not cleared");

        int pipelineColour = FaceScene.fnv(fb, fb.length);
        int pipelineDepth = FaceScene.fnvDepth(depth);
        int covered = FaceScene.covered(fb);
        int distinct = FaceScene.distinct(fb);
        if (covered <= 0) throw new IllegalStateException(c.name + ": nothing was drawn");

        boolean[] front = new boolean[mesh.faces];
        int frontCount = 0;
        for (int f = 0; f < mesh.faces; f++) {
            int a = mesh.fa[f], b = mesh.fb[f], k = mesh.fc[f];
            long area = (long) (o.x[a] - o.x[b]) * (o.y[k] - o.y[b]) - (long) (o.y[a] - o.y[b]) * (o.x[k] - o.x[b]);
            front[f] = area > 0;
            if (front[f]) frontCount++;
        }
        int backCount = mesh.faces - frontCount;
        if (backCount < 1 || frontCount < 1) throw new IllegalStateException(c.name + ": no back-face culling exercised");

        // Independent re-render of exactly the front faces, in index order, straight into the flat fill.
        clear(fb, depth);
        fill(rig, mesh, o, front, c.width, palette);
        int directColour = FaceScene.fnv(fb, fb.length);
        int directDepth = FaceScene.fnvDepth(depth);
        if (directColour != pipelineColour || directDepth != pipelineDepth)
            throw new IllegalStateException(c.name + ": pipeline output differs from the direct front-face fill");

        // Anti-bypass control: every projected face straight into the flat fill, with no culling.
        clear(fb, depth);
        fill(rig, mesh, o, null, c.width, palette);
        int allColour = FaceScene.fnv(fb, fb.length);
        int allDepth = FaceScene.fnvDepth(depth);
        int allCovered = FaceScene.covered(fb);

        // Restore the front-only frame, the one the pipeline produced, before anything is presented.
        clear(fb, depth);
        fill(rig, mesh, o, front, c.width, palette);
        if (FaceScene.fnv(fb, fb.length) != pipelineColour || FaceScene.fnvDepth(depth) != pipelineDepth)
            throw new IllegalStateException(c.name + ": front-only frame not restored");

        StringBuilder sb = new StringBuilder("{\"runtime\":\"").append(runtime).append("\",\"name\":\"").append(c.name)
            .append("\",\"fixture\":\"").append(fixture).append("\",\"size\":\"").append(c.width).append('x').append(c.height)
            .append("\",\"camera\":").append(c.camera).append(",\"variant\":\"").append(FaceCase.VARIANTS[c.variant])
            .append("\",\"decodeStubCalls\":").append(decodeStubs < 0 ? "null" : String.valueOf(decodeStubs))
            .append(",\"decoded\":{\"vertexCount\":").append(d.vertexCount).append(",\"faceCount\":").append(d.faceCount)
            .append(",\"maxVertexPlusOne\":").append(d.maxVertexPlusOne);
        ints(sb, "x", d.x);
        ints(sb, "y", d.y);
        ints(sb, "z", d.z);
        shorts(sb, "a", d.a);
        shorts(sb, "b", d.b);
        shorts(sb, "c", d.c);
        shorts(sb, "colour", d.colour);
        ints(sb, "colourIndex", mesh.colourIndex);
        sb.append('}');
        sb.append(",\"vertices\":").append(n).append(",\"faces\":").append(mesh.faces).append(",\"front\":").append(frontCount)
            .append(",\"back\":").append(backCount).append(",\"minDepth\":").append(minDepth).append(",\"covered\":").append(covered)
            .append(",\"distinct\":").append(distinct).append(",\"fnv1a\":\"").append(hex(pipelineColour))
            .append("\",\"depthFnv1a\":\"").append(hex(pipelineDepth)).append("\",\"directFnv1a\":\"").append(hex(directColour))
            .append("\",\"directDepthFnv1a\":\"").append(hex(directDepth)).append("\",\"allFacesFnv1a\":\"").append(hex(allColour))
            .append("\",\"allFacesDepthFnv1a\":\"").append(hex(allDepth)).append("\",\"allFacesCovered\":").append(allCovered)
            .append(",\"shortCleared\":").append(o.shortCleared).append(",\"byteCleared\":").append(o.byteCleared)
            .append(",\"counters\":").append(o.counters);
        ints(sb, "projX", java.util.Arrays.copyOf(o.x, n));
        ints(sb, "projY", java.util.Arrays.copyOf(o.y, n));
        ints(sb, "projZ", java.util.Arrays.copyOf(o.z, n));
        return sb.append('}').toString();
    }
}
