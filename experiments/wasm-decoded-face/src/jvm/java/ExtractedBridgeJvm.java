/** Extracted JVM run: the generated Class124 decode closure and the extracted face closure, no native jar on the path. */
public final class ExtractedBridgeJvm {
    private ExtractedBridgeJvm() {}

    public static void main(String[] args) {
        System.out.println(BridgeRun.document("extracted-jvm", ExtractedRig::new,
            () -> Packet.badMagicStubCalls + Class124.newFormatStubCalls, (rgba, w, h) -> ""));
    }
}
