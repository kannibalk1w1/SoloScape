/** JVM run of the extracted native triangle closure; one JSON line per scene and size. */
public final class VerbatimJvm {
    public static void main(String[] args) {
        Bench.Clock clock = () -> System.nanoTime() / 1.0e6;
        int[][] sizes = {{765, 503}, {1280, 800}};
        for (int[] s : sizes) {
            System.out.println(Bench.measure(clock, new VerbatimFill(), "single", Scene.SINGLE, s[0], s[1]));
            System.out.println(Bench.measure(clock, new VerbatimFill(), "single64", Scene.SINGLE_BATCH, s[0], s[1]));
            System.out.println(Bench.measure(clock, new VerbatimFill(), "mesh", Scene.MESH, s[0], s[1]));
        }
    }
}
