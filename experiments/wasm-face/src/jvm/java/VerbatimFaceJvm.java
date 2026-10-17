/** JVM run of the extracted closure; one JSON line per case. `-Dface.illegal=N` and `-Dface.perturb=1` are negative controls. */
public final class VerbatimFaceJvm {
    public static void main(String[] args) {
        int illegal = Integer.getInteger("face.illegal", 0);
        if (Boolean.getBoolean("face.clip")) {
            for (int[] s : ClipScene.SIZES) {
                for (ClipScene.Case c : ClipScene.cases()) System.out.println(ClipScene.run(new ExtractedRig(), c, s[0], s[1], illegal));
            }
            return;
        }
        boolean perturb = Boolean.getBoolean("face.perturb");
        for (FaceCase c : FaceScene.cases(illegal)) {
            System.out.println(FaceScene.run(new ExtractedRig(), c, perturb));
        }
    }
}
