import org.teavm.jso.JSBody;
import org.teavm.jso.typedarrays.Int32Array;

/**
 * Browser entry point: runs the extracted native shaded/textured fills in WasmGC with real-clock
 * timing, negative controls, and a Canvas ImageData readback of the mixed frame.
 */
public final class MaterialProbe {
    private static final int[][] SIZES = {{765, 503}, {1280, 800}};

    @JSBody(script = "return performance.now();")
    static native double now();

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

    public static void main(String[] args) {
        Bench.Clock clock = MaterialProbe::now;
        StringBuilder json = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"raster\":[");
        StringBuilder controls = new StringBuilder();
        StringBuilder present = new StringBuilder();
        boolean firstRow = true;
        boolean firstControl = true;
        for (int s = 0; s < SIZES.length; s++) {
            int width = SIZES[s][0];
            int height = SIZES[s][1];
            for (int kind = 0; kind < Scene.NAMES.length; kind++) {
                json.append(firstRow ? "" : ",").append(
                    Bench.measure(clock, new VerbatimFill(), Scene.NAMES[kind], kind, width, height));
                firstRow = false;
            }
            String[] names = {"shaded-palette-control", "tex1-texel-control", "tex3-texel-control"};
            int[] kinds = {Scene.SHADED, Scene.TEX1, Scene.TEX3};
            for (int c = 0; c < names.length; c++) {
                controls.append(firstControl ? "" : ",").append(
                    Bench.control(names[c], new VerbatimFill(), kinds[c], 1, width, height));
                firstControl = false;
            }

            // Presentation of one mixed frame: wasm-side RGBA swizzle, bulk copy, putImageData, readback.
            int[] framebuffer = new int[width * height];
            float[] depth = new float[width * height];
            new Scene(new VerbatimFill(), width, height).render(Scene.MIXED, framebuffer, depth);
            int[] rgba = new int[framebuffer.length];
            for (int p = 0; p < framebuffer.length; p++) {
                rgba[p] = toRgbaWord(framebuffer[p]);
            }
            Int32Array words = Int32Array.create(framebuffer.length);
            words.set(rgba);
            present(words, width, height);
            present.append(s == 0 ? "" : ",").append("{\"size\":\"").append(width).append('x').append(height)
                .append("\",\"presentedFnv1a\":\"").append(Integer.toHexString(Scene.hash(rgba)))
                .append("\",\"canvasReadbackFnv1a\":\"").append(Integer.toHexString(readbackHash(width, height)))
                .append("\"}");
        }
        json.append("],\"controls\":[").append(controls).append("],\"present\":[").append(present).append("]}");
        report(json.toString());
    }
}
