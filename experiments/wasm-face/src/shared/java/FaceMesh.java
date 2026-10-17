/**
 * Original synthetic closed meshes: a latitude/longitude sphere and a cube, built with rational circle
 * parametrisation and integer rounding only (no trig), so every runtime derives identical vertices.
 */
final class FaceMesh {
    static final int PERTURBED_VERTEX = 17;
    static final int PERTURB_DX = 50;
    private static final int RADIUS = 600;
    private static final int LAT = 10;
    private static final int LON = 16;
    /** Winding choice, fixed after checking the centre pixel depth: the native cull then keeps the near (outward) faces. */
    private static final boolean FLIP = false;

    final int[] vx, vy, vz;
    final short[] fa, fb, fc;
    final int[] colourIndex;
    final int vertices, faces;

    private int[] tx = new int[400], ty = new int[400], tz = new int[400];
    private int[] ta = new int[1200];
    private int nv, nf;

    private static int round(double v) {
        return (int) (v + (v >= 0 ? 0.5 : -0.5));
    }

    private int vertex(int x, int y, int z) {
        tx[nv] = x;
        ty[nv] = y;
        tz[nv] = z;
        return nv++;
    }

    /** Adds a triangle wound so its normal points away from (cx, cy, cz). */
    private void tri(int a, int b, int c, int cx, int cy, int cz) {
        long ux = tx[b] - tx[a], uy = ty[b] - ty[a], uz = tz[b] - tz[a];
        long wx = tx[c] - tx[a], wy = ty[c] - ty[a], wz = tz[c] - tz[a];
        long nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
        long out = nx * (tx[a] - cx) + ny * (ty[a] - cy) + nz * (tz[a] - cz);
        boolean swap = (out < 0) != FLIP;
        ta[nf * 3] = a;
        ta[nf * 3 + 1] = swap ? c : b;
        ta[nf * 3 + 2] = swap ? b : c;
        nf++;
    }

    private FaceMesh(boolean perturb) {
        int south = vertex(0, -RADIUS, 0);
        int[][] ring = new int[LAT + 1][LON];
        int quarter = LON / 4;
        for (int j = 1; j < LAT; j++) {
            double t = -1.0 + 2.0 * j / LAT;
            double r = (1.0 - t * t) / (1.0 + t * t);
            double h = 2.0 * t / (1.0 + t * t);
            for (int k = 0; k < LON; k++) {
                double u = (k % quarter) / (double) quarter;
                double c = (1.0 - u * u) / (1.0 + u * u);
                double s = 2.0 * u / (1.0 + u * u);
                double cx, cz;
                switch (k / quarter) {
                    case 0: cx = c; cz = s; break;
                    case 1: cx = -s; cz = c; break;
                    case 2: cx = -c; cz = -s; break;
                    default: cx = s; cz = -c; break;
                }
                ring[j][k] = vertex(round(RADIUS * r * cx), round(RADIUS * h), round(RADIUS * r * cz));
            }
        }
        int north = vertex(0, RADIUS, 0);
        for (int k = 0; k < LON; k++) {
            int n = (k + 1) % LON;
            tri(south, ring[1][k], ring[1][n], 0, 0, 0);
            tri(north, ring[LAT - 1][n], ring[LAT - 1][k], 0, 0, 0);
            for (int j = 1; j < LAT - 1; j++) {
                tri(ring[j][k], ring[j + 1][k], ring[j][n], 0, 0, 0);
                tri(ring[j][n], ring[j + 1][k], ring[j + 1][n], 0, 0, 0);
            }
        }
        // Cube, partly outside the right edge of both frame sizes so the x-clip path runs.
        int cx = 1700, cy = -200, cz = 300, half = 400;
        int[] cube = new int[8];
        for (int i = 0; i < 8; i++) {
            cube[i] = vertex(cx + ((i & 1) == 0 ? -half : half), cy + ((i & 2) == 0 ? -half : half),
                cz + ((i & 4) == 0 ? -half : half));
        }
        int[][] quads = {{0, 1, 3, 2}, {4, 5, 7, 6}, {0, 1, 5, 4}, {2, 3, 7, 6}, {0, 2, 6, 4}, {1, 3, 7, 5}};
        for (int[] q : quads) {
            tri(cube[q[0]], cube[q[1]], cube[q[2]], cx, cy, cz);
            tri(cube[q[0]], cube[q[2]], cube[q[3]], cx, cy, cz);
        }
        vertices = nv;
        faces = nf;
        vx = new int[nv];
        vy = new int[nv];
        vz = new int[nv];
        for (int i = 0; i < nv; i++) {
            vx[i] = tx[i];
            vy[i] = ty[i];
            vz[i] = tz[i];
        }
        if (perturb) vx[PERTURBED_VERTEX] += PERTURB_DX;
        fa = new short[nf];
        fb = new short[nf];
        fc = new short[nf];
        colourIndex = new int[nf];
        for (int f = 0; f < nf; f++) {
            fa[f] = (short) ta[f * 3];
            fb[f] = (short) ta[f * 3 + 1];
            fc[f] = (short) ta[f * 3 + 2];
            colourIndex[f] = (f * 1237 + 91) & 0xffff;
        }
    }

    static FaceMesh build(boolean perturb) {
        return new FaceMesh(perturb);
    }

    /** Original synthetic palette: 65,536 opaque colours from an integer mix of the index. */
    static int[] palette() {
        int[] p = new int[65536];
        for (int i = 0; i < p.length; i++) {
            int x = i * 0x9E3779B1;
            x ^= x >>> 15;
            x *= 0x85EBCA6B;
            x ^= x >>> 13;
            p[i] = 0xff000000 | (x & 0xffffff);
            if (p[i] == FaceScene.BACKGROUND) p[i] ^= 1;
        }
        return p;
    }

    /** Twelve transform floats in the order x row, y row, z row, then translation x, y, z (see FaceScene). */
    static float[] model(int camera) {
        if (camera == 0) return new float[] {16384f, 0f, 0f, 0f, 16384f, 0f, 0f, 0f, 16384f, 0f, 0f, 0f};
        float c = (float) (4.0 / 5.0 * 16384.0), s = (float) (3.0 / 5.0 * 16384.0);
        return new float[] {c, 0f, s, 0f, 16384f, 0f, -s, 0f, c, 0f, 0f, 0f};
    }

    static float[] view(int camera) {
        float c, s, k;
        if (camera == 0) {
            c = (float) (4.0 / 5.0);
            s = (float) (3.0 / 5.0);
            k = 1f;
        } else {
            c = (float) (12.0 / 13.0 / 16384.0);
            s = (float) (5.0 / 13.0 / 16384.0);
            k = 1f / 16384f;
        }
        return new float[] {k, 0f, 0f, 0f, c, -s, 0f, s, c, 0f, 0f, 2400f};
    }
}
