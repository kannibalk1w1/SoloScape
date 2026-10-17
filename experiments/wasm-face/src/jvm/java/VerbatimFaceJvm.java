/** JVM run of the extracted closure; one JSON line per case. `-Dface.illegal=N` and `-Dface.perturb=1` are negative controls. */
public final class VerbatimFaceJvm {
    public static void main(String[] args) {
        int illegal = Integer.getInteger("face.illegal", 0);
        boolean perturb = Boolean.getBoolean("face.perturb");
        for (FaceCase c : FaceScene.cases(illegal)) {
            System.out.println(FaceScene.run(new ExtractedRig(), c, perturb));
        }
    }
}
