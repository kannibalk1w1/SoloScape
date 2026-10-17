import org.teavm.jso.JSBody;
import org.teavm.jso.typedarrays.Int32Array;

/**
 * Browser entry point: runs the extracted native triangle fill in WasmGC with real-clock timing and
 * presents through Canvas ImageData. Raster time and presentation time are reported separately.
 */
public final class TriangleProbe {
    private static final int[][] SIZES = {{765, 503}, {1280, 800}};
    private static final int PRESENT_SAMPLES = 7;

    @JSBody(script = "return performance.now();")
    static native double now();

    @JSBody(params = {"a", "i", "v"}, script = "a[i] = v;")
    static native void put(Int32Array array, int index, int value);

    @JSBody(params = {"a", "w", "h"}, script = "const c = document.getElementById('frame');"
        + " c.width = w; c.height = h;"
        + " c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(a.buffer), w, h), 0, 0);")
    static native void present(Int32Array array, int width, int height);

    /** FNV-1a over the canvas words as the browser holds them after putImageData. */
    @JSBody(params = {"w", "h"}, script = "const d = new Int32Array(document.getElementById('frame')"
        + ".getContext('2d').getImageData(0, 0, w, h).data.buffer);"
        + " let x = 0x811c9dc5 | 0; for (let i = 0; i < d.length; i++) { x ^= d[i]; x = Math.imul(x, 0x01000193); } return x;")
    static native int readbackHash(int width, int height);

    @JSBody(params = {"s"}, script = "document.getElementById('result').textContent = s;")
    static native void report(String text);

    /** ARGB to the little-endian word whose bytes are R,G,B,A (alpha forced opaque). */
    static int toRgbaWord(int argb) {
        return 0xff000000 | (argb & 0xff00) | ((argb >>> 16) & 0xff) | ((argb & 0xff) << 16);
    }

    private static double median(double[] values) {
        double[] copy = values.clone();
        java.util.Arrays.sort(copy);
        return copy[copy.length / 2];
    }

    private static String stats(String name, double[] values) {
        double[] copy = values.clone();
        java.util.Arrays.sort(copy);
        return "\"" + name + "\":{\"min\":" + copy[0] + ",\"median\":" + copy[copy.length / 2] + ",\"max\":"
            + copy[copy.length - 1] + ",\"n\":" + copy.length + "}";
    }

    public static void main(String[] args) {
        Bench.Clock clock = TriangleProbe::now;
        StringBuilder json = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"raster\":[");
        StringBuilder present = new StringBuilder();
        for (int s = 0; s < SIZES.length; s++) {
            int width = SIZES[s][0];
            int height = SIZES[s][1];
            json.append(s == 0 ? "" : ",").append(Bench.measure(clock, new VerbatimFill(), "single", Scene.SINGLE, width, height));
            json.append(',').append(Bench.measure(clock, new VerbatimFill(), "single64", Scene.SINGLE_BATCH, width, height));
            json.append(',').append(Bench.measure(clock, new VerbatimFill(), "mesh", Scene.MESH, width, height));

            // Presentation of one mesh frame: per-pixel JS call, bulk typed-array copy, then putImageData.
            int[] framebuffer = new int[width * height];
            float[] depth = new float[width * height];
            new Scene(new VerbatimFill(), width, height).render(Scene.MESH, framebuffer, depth);
            int[] rgba = new int[framebuffer.length];
            double[] perPixel = new double[PRESENT_SAMPLES];
            double[] bulk = new double[PRESENT_SAMPLES];
            double[] upload = new double[PRESENT_SAMPLES];
            Int32Array words = Int32Array.create(framebuffer.length);
            for (int i = 0; i < PRESENT_SAMPLES; i++) {
                double t0 = now();
                for (int p = 0; p < framebuffer.length; p++) {
                    put(words, p, toRgbaWord(framebuffer[p]));
                }
                perPixel[i] = now() - t0;
            }
            for (int i = 0; i < PRESENT_SAMPLES; i++) {
                double t0 = now();
                for (int p = 0; p < framebuffer.length; p++) {
                    rgba[p] = toRgbaWord(framebuffer[p]);
                }
                words.set(rgba);
                bulk[i] = now() - t0;
            }
            for (int i = 0; i < PRESENT_SAMPLES; i++) {
                double t0 = now();
                present(words, width, height);
                upload[i] = now() - t0;
            }
            int expected = Scene.hash(rgba);
            int readback = readbackHash(width, height);
            present.append(s == 0 ? "" : ",").append("{\"size\":\"").append(width).append('x').append(height)
                .append("\",").append(stats("perPixelJsCallMs", perPixel)).append(',')
                .append(stats("bulkCopyMs", bulk)).append(',').append(stats("putImageDataMs", upload))
                .append(",\"presentedFnv1a\":\"").append(Integer.toHexString(expected))
                .append("\",\"canvasReadbackFnv1a\":\"").append(Integer.toHexString(readback)).append("\"}");
        }
        json.append("],\"present\":[").append(present).append("]}");
        report(json.toString());
    }
}
