import java.util.function.IntSupplier;
import java.util.function.Supplier;

/**
 * Shared matrix for the three runtimes. Each fixture is decoded by the runtime's own Class124 and projected by the
 * runtime's own rig at both sizes and both cameras. The same 1280x800 camera-1 frame is then reported (RGBA words) for
 * the presenter. Only the presenter differs by runtime (the browser puts the frame on a canvas).
 */
final class BridgeRun {
    static final int[][] SIZES = {{765, 503}, {1280, 800}};

    /** Returns extra JSON fields for the presented frame, each starting with a comma, or "". */
    interface Presenter {
        String present(int[] rgba, int width, int height);
    }

    private BridgeRun() {}

    static byte[] bytes(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) out[i] = (byte) Integer.parseInt(hex.substring(2 * i, 2 * i + 2), 16);
        return out;
    }

    /** Same packing as FaceProbe: opaque alpha, R in the lowest byte, so the word is RGBA in memory. */
    static int toRgbaWord(int argb) {
        return 0xff000000 | (argb & 0xff00) | ((argb >>> 16) & 0xff) | ((argb & 0xff) << 16);
    }

    static String document(String runtime, Supplier<FaceRig> rigs, IntSupplier decodeStubs, Presenter presenter) {
        StringBuilder json = new StringBuilder("{\"runtime\":\"").append(runtime)
            .append("\",\"palette\":{\"fnv1a\":\"").append(Integer.toHexString(FaceScene.fnv(FaceMesh.palette(), 65536)))
            .append("\"},\"cases\":[");
        boolean first = true;
        for (int i = 0; i < BridgeFixtures.NAMES.length; i++) {
            for (int camera = 0; camera < 2; camera++) {
                for (int[] s : SIZES) {
                    String name = BridgeFixtures.NAMES[i] + "-cam" + camera + "-" + s[0] + "x" + s[1];
                    FaceCase c = new FaceCase(name, s[0], s[1], camera, 0, false, 0);
                    DecodeMesh d = DecodeMesh.decode(bytes(BridgeFixtures.HEX[i]));
                    json.append(first ? "" : ",")
                        .append(BridgeScene.run(runtime, BridgeFixtures.NAMES[i], decodeStubs.getAsInt(), rigs.get(), c, d));
                    first = false;
                }
            }
        }
        FaceCase show = new FaceCase("present", 1280, 800, 1, 0, false, 0);
        DecodeMesh d = DecodeMesh.decode(bytes(BridgeFixtures.HEX[0]));
        int[] fb = new int[show.width * show.height];
        float[] depth = new float[fb.length];
        java.util.Arrays.fill(fb, FaceScene.BACKGROUND);
        java.util.Arrays.fill(depth, FaceScene.FAR);
        FaceRig rig = rigs.get();
        rig.setup(show, d.mesh, fb, depth);
        rig.project();
        int[] rgba = new int[fb.length];
        for (int p = 0; p < fb.length; p++) rgba[p] = toRgbaWord(fb[p]);
        json.append("],\"presented\":{\"fixture\":\"").append(BridgeFixtures.NAMES[0])
            .append("\",\"size\":\"1280x800\",\"camera\":1,\"rgbaFnv1a\":\"")
            .append(Integer.toHexString(FaceScene.fnv(rgba, rgba.length))).append("\",\"frameFnv1a\":\"")
            .append(Integer.toHexString(FaceScene.fnv(fb, fb.length))).append('"')
            .append(presenter.present(rgba, show.width, show.height)).append("}}");
        return json.toString();
    }
}
