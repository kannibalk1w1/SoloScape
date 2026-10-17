/**
 * Field-only adapter from a decoded Class124 to the existing FaceMesh geometry. It copies the native-decoded vertex
 * X/Y/Z arrays and face A/B/C arrays into FaceMesh.custom and takes each face colour index from the decoded short
 * (& 0xffff). Nothing else is read: no flags, texture, priority or label state. This one source is compiled against the
 * frozen native jar (the real Class124(byte[]) constructor) for the native run, and against only the generated
 * Class124 for the extracted and browser runs.
 */
final class DecodeMesh {
    final int vertexCount, faceCount, maxVertexPlusOne;
    final int[] x, y, z;
    final short[] a, b, c, colour;
    final FaceMesh mesh;

    private DecodeMesh(Class124 model) {
        vertexCount = model.anInt1836;
        faceCount = model.anInt1817;
        maxVertexPlusOne = model.anInt1821;
        x = java.util.Arrays.copyOf(model.anIntArray1841, vertexCount);
        y = java.util.Arrays.copyOf(model.anIntArray1847, vertexCount);
        z = java.util.Arrays.copyOf(model.anIntArray1852, vertexCount);
        a = java.util.Arrays.copyOf(model.aShortArray1863, faceCount);
        b = java.util.Arrays.copyOf(model.aShortArray1835, faceCount);
        c = java.util.Arrays.copyOf(model.aShortArray1855, faceCount);
        colour = java.util.Arrays.copyOf(model.aShortArray1862, faceCount);
        int[][] verts = new int[vertexCount][];
        for (int i = 0; i < vertexCount; i++) verts[i] = new int[] {x[i], y[i], z[i]};
        int[][] tris = new int[faceCount][];
        for (int f = 0; f < faceCount; f++) tris[f] = new int[] {a[f] & 0xffff, b[f] & 0xffff, c[f] & 0xffff};
        mesh = FaceMesh.custom(verts, tris);
        for (int f = 0; f < faceCount; f++) mesh.colourIndex[f] = colour[f] & 0xffff;
    }

    static DecodeMesh decode(byte[] bytes) {
        return new DecodeMesh(new Class124(bytes));
    }
}
