/** JVM run of the extracted native material closure; one JSON line per scene, size and control. */
public final class VerbatimJvm {
    public static void main(String[] args) {
        Bench.Clock clock = () -> System.nanoTime() / 1.0e6;
        int[][] sizes = {{765, 503}, {1280, 800}};
        for (int[] s : sizes) {
            for (int kind = 0; kind < Scene.NAMES.length; kind++) {
                System.out.println(Bench.measure(clock, new VerbatimFill(), Scene.NAMES[kind], kind, s[0], s[1]));
            }
            System.out.println(Bench.control("shaded-palette-control", new VerbatimFill(), Scene.SHADED, 1, s[0], s[1]));
            System.out.println(Bench.control("tex1-texel-control", new VerbatimFill(), Scene.TEX1, 1, s[0], s[1]));
            System.out.println(Bench.control("tex3-texel-control", new VerbatimFill(), Scene.TEX3, 1, s[0], s[1]));
        }
    }
}
