/** One JSON object per case, identical for native reflection, extracted JVM and browser. Arrays are printed
 *  as stored: int arrays as ints, short arrays as signed shorts (colour stays signed, as the native field does). */
final class DecodeJson {
    private DecodeJson() {}

    static String caseLine(String runtime, String name, String error, int stubCalls, int vertexCount, int faceCount,
                           int maxVertexPlusOne, int[] x, int[] y, int[] z, short[] a, short[] b, short[] c, short[] colour) {
        StringBuilder json = new StringBuilder("{\"runtime\":\"").append(runtime).append("\",\"name\":\"").append(name).append('"');
        json.append(",\"ok\":").append(error == null ? "true" : "false");
        json.append(",\"error\":").append(error == null ? "null" : "\"" + sanitize(error) + "\"");
        json.append(",\"stubCalls\":").append(stubCalls);
        json.append(",\"vertexCount\":").append(vertexCount);
        json.append(",\"faceCount\":").append(faceCount);
        json.append(",\"maxVertexPlusOne\":").append(maxVertexPlusOne);
        appendInts(json.append(",\"x\":"), x);
        appendInts(json.append(",\"y\":"), y);
        appendInts(json.append(",\"z\":"), z);
        appendShorts(json.append(",\"a\":"), a);
        appendShorts(json.append(",\"b\":"), b);
        appendShorts(json.append(",\"c\":"), c);
        appendShorts(json.append(",\"colour\":"), colour);
        return json.append('}').toString();
    }

    private static void appendInts(StringBuilder json, int[] values) {
        if (values == null) { json.append("null"); return; }
        json.append('[');
        for (int i = 0; i < values.length; i++) json.append(i == 0 ? "" : ",").append(values[i]);
        json.append(']');
    }

    private static void appendShorts(StringBuilder json, short[] values) {
        if (values == null) { json.append("null"); return; }
        json.append('[');
        for (int i = 0; i < values.length; i++) json.append(i == 0 ? "" : ",").append(values[i]);
        json.append(']');
    }

    private static String sanitize(String text) {
        return text.replace('\\', '/').replace('"', '\'').replace('\n', ' ').replace('\r', ' ');
    }

}
