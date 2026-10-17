import org.teavm.jso.JSBody;

/** Browser entry point for clip mode: the same clip case matrix on the extracted closure, JSON reported in the DOM. */
public final class ClipProbe {
    @JSBody(params = {"s"}, script = "document.getElementById('result').textContent = s;")
    static native void report(String text);

    public static void main(String[] args) {
        try {
            StringBuilder json = new StringBuilder("{\"runtime\":\"teavm-0.16.0-wasmgc\",\"cases\":[");
            boolean first = true;
            for (int[] s : ClipScene.SIZES) {
                for (ClipScene.Case c : ClipScene.cases()) {
                    json.append(first ? "" : ",").append(ClipScene.run(new ExtractedRig(), c, s[0], s[1], 0));
                    first = false;
                }
            }
            report(json.append("]}").toString());
        } catch (Throwable t) {
            report("FAIL: " + t);
        }
    }
}
