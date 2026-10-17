/** JVM run of the same generated verbatim kernel, without the jar on the classpath. */
public final class VerbatimJvm {
    public static void main(String[] args) {
        Bench.Clock clock = () -> System.nanoTime() / 1e6;
        for (int[] size : new int[][] {{765, 503}, {1280, 800}}) {
            int[] framebuffer = new int[size[0] * size[1]];
            VerbatimRaster raster = new VerbatimRaster(new NativeFaceKernel());
            System.out.println(Bench.measure(clock, raster, size[0], size[1], framebuffer));
        }
    }
}
