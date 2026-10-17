import org.teavm.jso.JSBody;
import org.teavm.jso.typedarrays.Int32Array;

/**
 * Browser entry point: the same matrix on the extracted closure in TeaVM WasmGC, then the presented frame on a canvas.
 * Results are reported as JSON in the DOM for the checker. The expected arrays are never sent to the page.
 */
public final class BridgeProbe {
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

    public static void main(String[] args) {
        String json;
        try {
            json = BridgeRun.document("teavm-0.16.0-wasmgc", ExtractedRig::new,
                () -> Packet.badMagicStubCalls + Class124.newFormatStubCalls, (rgba, w, h) -> {
                    Int32Array words = Int32Array.create(rgba.length);
                    words.set(rgba);
                    present(words, w, h);
                    return ",\"canvasReadbackFnv1a\":\"" + Integer.toHexString(readbackHash(w, h)) + "\"";
                });
        } catch (Throwable t) {
            json = "FAIL: " + t;
        }
        report(json);
    }
}
