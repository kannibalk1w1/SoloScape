/** Runs the extracted old-format closure on the JVM over the original encoded fixtures and prints one line per case. */
public final class ExtractedDecodeJvm {
    private ExtractedDecodeJvm() {}

    static byte[] bytes(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) out[i] = (byte) Integer.parseInt(hex.substring(2 * i, 2 * i + 2), 16);
        return out;
    }

    public static void main(String[] args) {
        for (int i = 0; i < DecodeFixtures.NAMES.length; i++) {
            String name = DecodeFixtures.NAMES[i];
            try {
                Class124 model = new Class124(bytes(DecodeFixtures.HEX[i]));
                System.out.println(DecodeJson.caseLine("extracted-jvm", name, null,
                    Packet.badMagicStubCalls + Class124.newFormatStubCalls,
                    model.anInt1836, model.anInt1817, model.anInt1821,
                    model.anIntArray1841, model.anIntArray1847, model.anIntArray1852,
                    model.aShortArray1863, model.aShortArray1835, model.aShortArray1855, model.aShortArray1862));
            } catch (Throwable t) {
                System.out.println(DecodeJson.caseLine("extracted-jvm", name, t.toString(), -1,
                    0, 0, 0, null, null, null, null, null, null, null));
            }
        }
    }
}
