import org.teavm.jso.JSBody;
import org.teavm.jso.typedarrays.Int32Array;

/** Browser entry point: runs the same case matrix on the extracted closure in WasmGC and reports JSON in the DOM. */
public final class FaceProbe {
    @JSBody(script = "return performance.now();")
    static native double now();

    @JSBody(script = "return new URLSearchParams(location.search).get('perturb') === '1';")
    static native boolean perturbRequested();

    @JSBody(params = {"a", "w", "h"}, script = "const c = document.getElementById('frame');"
        + " c.width = w; c.height = h;"
        + " c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(a.buffer), w, h), 0, 0);")
    static native void present(Int32Array array, int width, int height);

    @JSBody(params = {"w", "h"}, script = "const d = new Int32Array(document.getElementById('frame')"
        + ".getContext('2d').getImageData(0, 0, w, h).data.buffer);"
        + " let x = 0x811c9dc5 | 0; for (let i = 0; i < d.length; i++) { x ^= d[i]; x = Math.imul(x, 0x01000193); } return x;")
    static native int readbackHash(int width, int height);

    @JSBody(params = {"s"}, script = "document.getElementById('result').textContent = s;")
    static native void report(String text);

    static int toRgbaWord(int argb) {
        return 0xff000000 | (argb & 0xff00) | ((argb >>> 16) & 0xff) | ((argb & 0xff) << 16);
    }

    public static void main(String[] args) {
        try {
            boolean perturb = perturbRequested();
            StringBuilder json = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"cases\":[");
            double t0 = now();
            FaceCase[] cases = FaceScene.cases(0);
            for (int i = 0; i < cases.length; i++) {
                json.append(i == 0 ? "" : ",").append(FaceScene.run(new ExtractedRig(), cases[i], perturb));
            }
            double elapsed = now() - t0;
            // Present the 1280x800 camera-1 frame once through a canvas and compare the readback hash.
            FaceCase show = new FaceCase("present", 1280, 800, 1, 0, false, 0);
            int[] fb = new int[show.width * show.height];
            float[] depth = new float[fb.length];
            java.util.Arrays.fill(fb, FaceScene.BACKGROUND);
            java.util.Arrays.fill(depth, FaceScene.FAR);
            ExtractedRig rig = new ExtractedRig();
            rig.setup(show, FaceMesh.build(perturb), fb, depth);
            rig.project();
            int[] rgba = new int[fb.length];
            for (int p = 0; p < fb.length; p++) rgba[p] = toRgbaWord(fb[p]);
            Int32Array words = Int32Array.create(fb.length);
            words.set(rgba);
            present(words, show.width, show.height);
            json.append("],\"present\":{\"size\":\"1280x800\",\"presentedFnv1a\":\"").append(Integer.toHexString(FaceScene.fnv(rgba, rgba.length)))
                .append("\",\"canvasReadbackFnv1a\":\"").append(Integer.toHexString(readbackHash(show.width, show.height)))
                .append("\",\"frameFnv1a\":\"").append(Integer.toHexString(FaceScene.fnv(fb, fb.length)))
                .append("\"},\"wholeMatrixMs\":").append(elapsed).append('}');
            report(json.toString());
        } catch (Throwable t) {
            report("FAIL: " + t);
        }
    }
}
