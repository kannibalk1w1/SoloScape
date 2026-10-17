import org.teavm.jso.JSBody;

/** Browser entry point. Decodes the original encoded fixtures with the extracted WasmGC closure; the expected arrays
 *  are never sent to the page. Results are reported as JSON in the DOM for the checker. */
public final class DecodeProbe {
    @JSBody(params = {"s"}, script = "document.getElementById('result').textContent = s;")
    static native void report(String text);

    static byte[] bytes(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) out[i] = (byte) Integer.parseInt(hex.substring(2 * i, 2 * i + 2), 16);
        return out;
    }

    public static void main(String[] args) {
        StringBuilder json = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"cases\":[");
        try {
            for (int i = 0; i < DecodeFixtures.NAMES.length; i++) {
                String name = DecodeFixtures.NAMES[i];
                String line;
                try {
                    Class124 model = new Class124(bytes(DecodeFixtures.HEX[i]));
                    line = DecodeJson.caseLine("teavm-0.16.0-wasmgc", name, null,
                        Packet.badMagicStubCalls + Class124.newFormatStubCalls,
                        model.anInt1836, model.anInt1817, model.anInt1821,
                        model.anIntArray1841, model.anIntArray1847, model.anIntArray1852,
                        model.aShortArray1863, model.aShortArray1835, model.aShortArray1855, model.aShortArray1862);
                } catch (Throwable t) {
                    line = DecodeJson.caseLine("teavm-0.16.0-wasmgc", name, String.valueOf(t), -1,
                        0, 0, 0, null, null, null, null, null, null, null);
                }
                json.append(i == 0 ? "" : ",").append(line);
            }
            json.append("]}");
        } catch (Throwable t) {
            json = new StringBuilder("FAIL: " + t);
        }
        report(json.toString());
    }
}
