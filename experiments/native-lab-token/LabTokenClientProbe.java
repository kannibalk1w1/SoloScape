import java.nio.file.*;
import java.util.concurrent.atomic.AtomicBoolean;
import net.runelite.client.RuneLite;
import net.runelite.client.callback.ClientThread;
import net.runelite.client.input.controller.HomeTab;
import net.runelite.client.input.controller.UiState;

/** External fixture-only client: ordinary login/Continue, native inventory and JS5 definition. */
public final class LabTokenClientProbe {
    private static final AtomicBoolean queued = new AtomicBoolean();
    private static int consecutive;
    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("MARKER PORT EXPECTED_QUANTITY");
        final Path marker = Paths.get(args[0]);
        final int expected = Integer.parseInt(args[2]);
        if (expected != 0 && expected != 2) throw new IllegalArgumentException("fixture quantities only");
        Loader.main(new String[]{"--address", "127.0.0.1", "--port", args[1]});
        new Thread(() -> {
            long started = System.currentTimeMillis();
            while (System.currentTimeMillis() - started < 150000) {
                try {
                    Thread.sleep(500);
                    if (Files.exists(marker)) { Thread.sleep(2500); System.exit(0); }
                    if (RuneLite.getInjector() == null || !queued.compareAndSet(false, true)) continue;
                    RuneLite.getInjector().getInstance(ClientThread.class).invokeLater(() -> {
                        try {
                            ControllerUi.enable(true);
                            SoloScapeConnection.update();
                            UiState ui = ControllerUi.snapshot();
                            if (ui.dialogue.length > 0 && ui.dialogue[0].actions.length > 0) {
                                ControllerUi.invoke(ui.dialogue[0], ui.dialogue[0].actions[0]);
                                return true;
                            }
                            if (System.currentTimeMillis() - started < 15000 || !ControllerWorld.ready()
                                    || !SoloScapeConnection.verified()) return true;
                            if (!ControllerUi.openTab(HomeTab.INVENTORY.ordinal())) return true;
                            ui = ControllerUi.snapshot();
                            if (!ui.hasInventory()) return true;
                            ObjType definition = Exception_Sub1.aClass255_112.getItemDefinitions(-115, 20179);
                            if (!"SoloScape Lab token".equals(definition.name) || definition.cost != 37
                                    || definition.stackable != 1 || definition.certlink != -1)
                                throw new IllegalStateException("live JS5 definition mismatch");
                            int quantity = 0, stacks = 0;
                            StringBuilder slots = new StringBuilder("[");
                            for (UiState.Widget slot : ui.inventory) {
                                if (slot == null || slot.itemId < 0) continue;
                                if (slots.length() > 1) slots.append(',');
                                slots.append('[').append(slot.itemId).append(',').append(slot.quantity).append(',').append(slot.child).append(']');
                                if (slot.itemId == 20179) {
                                    quantity += slot.quantity;
                                    stacks++;
                                    if (!"SoloScape Lab token".equals(slot.name))
                                        throw new IllegalStateException("native inventory label mismatch");
                                }
                            }
                            slots.append(']');
                            if (quantity != expected || stacks != (expected == 0 ? 0 : 1)) {
                                consecutive = 0;
                                return true;
                            }
                            if (++consecutive < 3) return true;
                            String json = "{\"ready\":true,\"capabilities_verified\":true,"
                                + "\"definition_id\":20179,\"name\":\"SoloScape Lab token\","
                                + "\"cost\":37,\"stackable\":1,\"quantity\":" + quantity
                                + ",\"stacks\":" + stacks + ",\"slots\":" + slots + "}\n";
                            Files.write(marker, json.getBytes("UTF-8"), StandardOpenOption.CREATE_NEW);
                        } catch (Exception failure) {
                            failure.printStackTrace();
                            System.exit(2);
                        } finally { queued.set(false); }
                        return true;
                    });
                } catch (Exception failure) { failure.printStackTrace(); System.exit(2); }
            }
            System.err.println("Lab token client fixture timed out");
            System.exit(2);
        }, "lab-token-fixture").start();
    }
}
