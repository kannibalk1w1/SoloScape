import java.lang.reflect.Constructor;
import java.lang.reflect.Field;

/** Reference: the REAL Class124(byte[]) from the frozen native jar, constructed by reflection over the original fixtures.
 *  Fields are read by reflection; nothing from the extracted closure is on this classpath. */
public final class NativeDecode {
    private NativeDecode() {}

    static byte[] bytes(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) out[i] = (byte) Integer.parseInt(hex.substring(2 * i, 2 * i + 2), 16);
        return out;
    }

    static Object read(Object model, String field) throws Exception {
        Field f = model.getClass().getDeclaredField(field);
        f.setAccessible(true);
        return f.get(model);
    }

    public static void main(String[] args) throws Exception {
        Class<?> type = Class.forName("Class124");
        Constructor<?> constructor = type.getDeclaredConstructor(byte[].class);
        constructor.setAccessible(true);
        for (int i = 0; i < DecodeFixtures.NAMES.length; i++) {
            String name = DecodeFixtures.NAMES[i];
            try {
                Object model = constructor.newInstance(new Object[] {bytes(DecodeFixtures.HEX[i])});
                System.out.println(DecodeJson.caseLine("native-jar", name, null, -1,
                    (Integer) read(model, "anInt1836"), (Integer) read(model, "anInt1817"), (Integer) read(model, "anInt1821"),
                    (int[]) read(model, "anIntArray1841"), (int[]) read(model, "anIntArray1847"), (int[]) read(model, "anIntArray1852"),
                    (short[]) read(model, "aShortArray1863"), (short[]) read(model, "aShortArray1835"),
                    (short[]) read(model, "aShortArray1855"), (short[]) read(model, "aShortArray1862")));
            } catch (Throwable t) {
                Throwable cause = t.getCause() != null ? t.getCause() : t;
                System.out.println(DecodeJson.caseLine("native-jar", name, cause.toString(), -1,
                    0, 0, 0, null, null, null, null, null, null, null));
            }
        }
    }
}
