import org.teavm.jso.JSBody;
import org.teavm.jso.JSObject;

/** Browser entry point: runs the verbatim native kernel in WasmGC and presents through Canvas ImageData. */
public final class RasterProbe {
    private static final int[][] SIZES = {{765, 503}, {1280, 800}};

    @JSBody(script = "return performance.now();")
    static native double now();

    @JSBody(params = {"n"}, script = "return new Int32Array(n);")
    static native JSObject newInt32Array(int n);

    @JSBody(params = {"a", "i", "v"}, script = "a[i] = v;")
    static native void put(JSObject array, int index, int value);

    @JSBody(params = {"a", "w", "h"}, script = "const c = document.getElementById('frame');"
        + " c.width = w; c.height = h;"
        + " c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(a.buffer), w, h), 0, 0);")
    static native void present(JSObject array, int width, int height);

    @JSBody(params = {"s"}, script = "document.getElementById('result').textContent = s;")
    static native void report(String text);

    /** ARGB to the little-endian word whose bytes are R,G,B,A, so Canvas can view the buffer directly. */
    static int toRgbaWord(int argb) {
        return (argb & 0xff00ff00) | ((argb >>> 16) & 0xff) | ((argb & 0xff) << 16);
    }

    public static void main(String[] args) {
        Bench.Clock clock = RasterProbe::now;
        StringBuilder json = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"sizes\":[");
        for (int s = 0; s < SIZES.length; s++) {
            int width = SIZES[s][0];
            int height = SIZES[s][1];
            int[] framebuffer = new int[width * height];
            VerbatimRaster raster = new VerbatimRaster(new NativeFaceKernel());
            json.append(s == 0 ? "" : ",").append(Bench.measure(clock, raster, width, height, framebuffer));

            JSObject words = newInt32Array(width * height);
            double c0 = now();
            for (int i = 0; i < framebuffer.length; i++) {
                put(words, i, toRgbaWord(framebuffer[i]));
            }
            double c1 = now();
            present(words, width, height);
            double c2 = now();
            json.append(",{\"size\":\"").append(width).append('x').append(height)
                .append("\",\"convertMs\":").append(c1 - c0)
                .append(",\"putImageDataMs\":").append(c2 - c1).append('}');
        }
        json.append("]}");
        report(json.toString());
    }
}
