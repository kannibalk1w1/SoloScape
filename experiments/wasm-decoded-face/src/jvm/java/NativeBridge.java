/**
 * Native reference: the frozen jar's real Class124(byte[]) decodes each fixture and NativeFace.JarRig (reflection plus
 * Unsafe context allocation, as in the prior proof) projects it. Decode and projection counters do not exist here.
 */
public final class NativeBridge {
    private NativeBridge() {}

    public static void main(String[] args) {
        System.out.println(BridgeRun.document("native-jar", NativeFace.JarRig::new, () -> -1, (rgba, w, h) -> ""));
    }
}
