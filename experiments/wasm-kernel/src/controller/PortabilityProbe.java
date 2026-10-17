public class PortabilityProbe {
    public static void main(String[] args) {
        float scaled = net.runelite.client.input.controller.StickMath.deadzoneScale(0.8f, 0, 0.2f);
        if (Math.abs(scaled - 0.9375f) > 0.00001f) throw new AssertionError("Deadzone mismatch");
        System.out.println("SoloScape StickMath passed: " + scaled);
    }
}
