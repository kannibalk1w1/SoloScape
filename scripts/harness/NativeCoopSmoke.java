import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.Arrays;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import net.runelite.client.RuneLite;
import net.runelite.client.callback.ClientThread;
import net.runelite.client.input.controller.UiState;

/**
 * Two native clients on one loopback server, driven through file handshakes in a marker directory.
 * Usage: NativeCoopSmoke markerDirectory port alpha|beta. Harness-only; not product multiplayer.
 * Fresh mode walks one client and drops alpha's dagger. Observe mode (-Dsoloscape.coop.observe=true)
 * sends no walk or drop and only reads the restored inventories and coordinates.
 */
public final class NativeCoopSmoke {
    private static final long DEADLINE_MS = 180000L;
    private static final long STABLE_MS = 2000L;
    private static final int BRONZE_DAGGER = 1205;
    private static final boolean OBSERVE = Boolean.getBoolean("soloscape.coop.observe");
    private static final String INVOCATION = UUID.randomUUID().toString();
    private static final AtomicReference<String> failure = new AtomicReference<>();
    private static volatile String stage = "start";
    private static volatile boolean holding;
    private static long started;
    private static Path dir;
    private static String role;
    private static String selfName;
    private static String peerName;
    private static double walkX;
    private static double walkY;
    private static int expectedDagger;

    private enum Phase { LOGIN, WAIT_GO, WALK, WAIT_CHECK, HOLD }

    private static Phase phase = Phase.LOGIN;
    private static int[] initialTile;
    private static int[] lastTile;
    private static long lastChange;
    private static long walkSentAt;
    private static boolean walkSent;
    private static boolean dropSent;
    private static boolean moved;
    private static boolean openSent;
    private static boolean readyWritten;
    private static int readyDagger;
    private static int movedDagger;
    private static int[] movedTile;
    private static int[] movedPeerTile;
    private static int[] readyPeerTile;

    public static void main(String[] args) {
        try {
            run(args);
        } catch (Throwable t) {
            exit(2, "setup at stage " + stage + ": " + describe(t));
        }
    }

    private static void run(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("usage: markerDirectory port alpha|beta");
        dir = Paths.get(args[0]);
        role = args[2];
        if (role.equals("alpha")) {
            selfName = "CoopAlpha";
            peerName = "CoopBeta";
            walkX = 0.4;
            walkY = 0;
            expectedDagger = OBSERVE ? 0 : 1;
        } else if (role.equals("beta")) {
            selfName = "CoopBeta";
            peerName = "CoopAlpha";
            walkX = 0;
            walkY = 0.4;
            expectedDagger = 1;
        } else {
            throw new IllegalArgumentException("role must be alpha or beta");
        }
        if (!Files.isDirectory(dir)) throw new IllegalArgumentException("marker directory missing");
        for (String suffix : new String[] {"ready.json", "moved.json", "result.json"}) {
            if (Files.exists(dir.resolve(role + "." + suffix))) {
                throw new IllegalStateException("stale " + role + "." + suffix + " present; use a fresh marker directory");
            }
        }
        started = System.currentTimeMillis();
        Loader.main(new String[] {"--address", "127.0.0.1", "--port", args[1]});
        Thread poller = new Thread(NativeCoopSmoke::poll, "coop-harness-poller");
        poller.setDaemon(true);
        poller.start();
    }

    private static void poll() {
        try {
            while (true) {
                String error = failure.get();
                if (error != null) exit(2, error);
                if (System.currentTimeMillis() - started > DEADLINE_MS) exit(2, "180s deadline at stage " + stage);
                if (holding && Files.exists(dir.resolve("finish"))) exit(0, "finish received");
                Thread.sleep(500);
                if (RuneLite.getInjector() == null) continue;
                RuneLite.getInjector().getInstance(ClientThread.class).invokeLater(() -> {
                    try {
                        step();
                    } catch (Throwable t) {
                        failure.compareAndSet(null, "stage " + stage + ": " + describe(t));
                    }
                    return true;
                });
            }
        } catch (InterruptedException e) {
            exit(2, "poller interrupted at stage " + stage);
        }
    }

    private static void step() throws Exception {
        ControllerUi.enable(true);
        SoloScapeConnection.update();
        long now = System.currentTimeMillis();
        switch (phase) {
            case LOGIN:
                login(now);
                break;
            case WAIT_GO:
                stage = "wait-go";
                if (Files.exists(dir.resolve("go"))) {
                    phase = Phase.WALK;
                    lastChange = now;
                    stage = OBSERVE ? "observe-stable" : "walk";
                }
                break;
            case WALK:
                if (OBSERVE) observeStable(now); else walkAndDrop(now);
                break;
            case WAIT_CHECK:
                stage = "wait-check";
                if (Files.exists(dir.resolve("check"))) writeResult(now);
                break;
            case HOLD:
                stage = "hold";
                break;
            default:
                throw new IllegalStateException("unknown phase " + phase);
        }
    }

    private static void login(long now) throws Exception {
        stage = "login";
        UiState ui = ControllerUi.snapshot();
        if (ui.dialogue.length > 0 && ui.dialogue[0].actions.length > 0) {
            ControllerUi.invoke(ui.dialogue[0], ui.dialogue[0].actions[0]);
            return;
        }
        if (!ControllerWorld.ready() || ControllerUi.availableTabs() == 0 || !SoloScapeConnection.verified()) return;
        Player self = Class132.aPlayer_1907;
        if (self == null) return;
        if (self.aString10537 != null && !selfName.equals(self.aString10537)) {
            throw new IllegalStateException("logged-in account is not " + selfName + " for role " + role);
        }
        if (!selfName.equals(self.aString10537)) return;
        if (!openSent) {
            openSent = ControllerUi.openInventory();
            return;
        }
        UiState inventory = ControllerUi.snapshot(true);
        // A freshly opened widget can render empty before its first server container update.
        // The retained sword is a positive data-ready witness, particularly when alpha expects zero daggers.
        if (!inventoryReady(inventory)) return;
        int[] peer = findPeer(self, false);
        if (peer == null) return;
        int dagger = daggerCount(inventory);
        if (dagger != expectedDagger) {
            throw new IllegalStateException("fresh bronze_dagger count must be " + expectedDagger + " for " + role + ", was " + dagger);
        }
        initialTile = tileOf(self);
        lastTile = initialTile;
        readyDagger = dagger;
        readyPeerTile = tileOf(Class294.aPlayerArray5058[peer[1]]);
        writeJson("ready.json", json(selfName, initialTile, peerName, readyPeerTile, peer, dagger, null, null));
        readyWritten = true;
        phase = Phase.WAIT_GO;
        stage = "wait-go";
    }

    private static void walkAndDrop(long now) throws Exception {
        Player self = Class132.aPlayer_1907;
        int[] tile = tileOf(self);
        if (!walkSent) {
            stage = "walk";
            if (!ControllerWorld.ready()) return;
            if (ControllerWorld.walk(walkX, walkY)) {
                walkSent = true;
                walkSentAt = now;
                lastChange = now;
            }
            return;
        }
        if (!Arrays.equals(tile, lastTile)) {
            lastTile = tile;
            lastChange = now;
        }
        if (!moved && !Arrays.equals(tile, initialTile)) moved = true;
        if (!moved) {
            if (now - walkSentAt > 30000) throw new IllegalStateException("walk sent but own tile never changed");
            return;
        }
        if (now - lastChange < STABLE_MS) return;
        stage = "action";
        if (role.equals("alpha") && !dropSent) {
            UiState.Widget dagger = findDagger(ControllerUi.snapshot(true));
            if (dagger == null) throw new IllegalStateException("alpha has no visible bronze_dagger to drop");
            UiState.Action drop = findAction(dagger, "Drop");
            if (drop == null) throw new IllegalStateException("bronze_dagger has no visible Drop action");
            dropSent = ControllerUi.invoke(dagger, drop);
            if (!dropSent) throw new IllegalStateException("native Drop invoke was not sent");
            lastChange = now;
            return;
        }
        int count = daggerCount(ControllerUi.snapshot(true));
        int want = role.equals("alpha") ? 0 : 1;
        if (count != want) {
            if (now - lastChange > 20000) throw new IllegalStateException("inventory " + count + ", expected " + want);
            return;
        }
        finishMoved(self, tile, count, now);
    }

    private static void observeStable(long now) throws Exception {
        Player self = Class132.aPlayer_1907;
        int[] tile = tileOf(self);
        if (!Arrays.equals(tile, lastTile)) {
            lastTile = tile;
            lastChange = now;
        }
        if (now - lastChange < STABLE_MS) return;
        stage = "observe-read";
        int count = daggerCount(ControllerUi.snapshot(true));
        if (count != expectedDagger) {
            throw new IllegalStateException("restored inventory " + count + ", expected " + expectedDagger);
        }
        if (!Arrays.equals(tile, initialTile)) {
            throw new IllegalStateException("observed tile changed without any walk");
        }
        finishMoved(self, tile, count, now);
    }

    private static void finishMoved(Player self, int[] tile, int count, long now) throws Exception {
        movedTile = tile;
        movedDagger = count;
        moved = true;
        int[] peer = findPeer(self, true);
        if (peer == null) throw new IllegalStateException("peer not visible when writing moved");
        movedPeerTile = tileOf(Class294.aPlayerArray5058[peer[1]]);
        writeJson("moved.json", json(selfName, tile, peerName, movedPeerTile, peer, count, walkSent, dropSent));
        phase = Phase.WAIT_CHECK;
        stage = "wait-check";
    }

    private static void writeResult(long now) throws Exception {
        stage = "result";
        Player self = Class132.aPlayer_1907;
        if (!moved) throw new IllegalStateException("check arrived before moved");
        boolean selfReady = ControllerWorld.ready() && ControllerUi.availableTabs() != 0 && SoloScapeConnection.verified();
        if (!selfReady) throw new IllegalStateException("self not ready at check");
        int[] peer = findPeer(self, true);
        if (peer == null) throw new IllegalStateException("peer not visible at check");
        int[] tile = tileOf(self);
        int[] peerTile = tileOf(Class294.aPlayerArray5058[peer[1]]);
        UiState inventory = ControllerUi.snapshot(true);
        if (!inventoryReady(inventory)) return;
        int count = daggerCount(inventory);
        if (OBSERVE && (!Arrays.equals(tile, movedTile) || !Arrays.equals(peerTile, movedPeerTile) || count != movedDagger)) {
            throw new IllegalStateException("observed coordinates or inventory changed after moved");
        }
        writeJson("result.json", json(selfName, tile, peerName, peerTile, peer, count, walkSent, dropSent));
        phase = Phase.HOLD;
        holding = true;
        stage = "hold";
    }

    /** Returns {ownIndex, peerIndex} after proving the peer is a distinct Player instance with the expected name. */
    private static int[] findPeer(Player self, boolean require) {
        Player[] players = Class294.aPlayerArray5058;
        if (players == null) return null;
        int ownIndex = -1;
        int peerIndex = -1;
        for (int i = 0; i < players.length; i++) {
            Player candidate = players[i];
            if (candidate == null) continue;
            if (candidate == self) {
                if (ownIndex != -1) throw new IllegalStateException("own player appears twice in aPlayerArray5058");
                ownIndex = i;
            } else if (peerName.equals(candidate.aString10537)) {
                if (peerIndex != -1) throw new IllegalStateException("peer name appears twice in aPlayerArray5058");
                peerIndex = i;
            }
        }
        if (ownIndex == -1) {
            if (require) throw new IllegalStateException("own player missing from aPlayerArray5058");
            return null;
        }
        if (peerIndex == -1 || peerIndex == ownIndex) return null;
        if (players[peerIndex] == self) throw new IllegalStateException("peer resolves to the own instance");
        return new int[] {ownIndex, peerIndex};
    }

    private static int[] tileOf(Player p) {
        return new int[] {(p.x >> 9) + za_Sub2.regionTileX, (p.y >> 9) + Class90.regionTileY, p.plane};
    }

    private static int daggerCount(UiState state) {
        int count = 0;
        for (UiState.Widget widget : state.inventory) {
            if (widget != null && widget.itemId == BRONZE_DAGGER && widget.quantity > 0) count += widget.quantity;
        }
        return count;
    }

    private static boolean inventoryReady(UiState state) {
        if (!state.inventoryVisible) return false;
        for (UiState.Widget widget : state.inventory) {
            if (widget != null && widget.itemId == 1277 && widget.quantity == 1) return true;
        }
        return false;
    }

    private static UiState.Widget findDagger(UiState state) {
        for (UiState.Widget widget : state.inventory) {
            if (widget != null && widget.itemId == BRONZE_DAGGER && widget.quantity > 0) return widget;
        }
        return null;
    }

    private static UiState.Action findAction(UiState.Widget widget, String label) {
        for (UiState.Action action : widget.actions) {
            if (action.label.equalsIgnoreCase(label)) return action;
        }
        return null;
    }

    private static String json(String self, int[] selfTile, String peer, int[] peerTile,
                               int[] indexes, int dagger, Boolean walked, Boolean dropped) {
        StringBuilder out = new StringBuilder("{");
        out.append("\"invocation\":").append(quote(INVOCATION));
        out.append(",\"role\":").append(quote(role));
        out.append(",\"observe\":").append(OBSERVE);
        out.append(",\"self\":{\"account\":").append(quote(self)).append(",\"index\":").append(indexes[0])
           .append(",\"tile\":").append(tile(selfTile)).append('}');
        out.append(",\"peer\":{\"account\":").append(quote(peer)).append(",\"index\":").append(indexes[1])
           .append(",\"tile\":").append(tile(peerTile)).append('}');
        // findPeer has already proven the peer is a different array slot holding a different Player instance.
        out.append(",\"distinct_instance\":true");
        out.append(",\"initial_tile\":").append(tile(initialTile));
        out.append(",\"bronze_dagger\":").append(dagger);
        out.append(",\"expected_dagger\":").append(expectedDagger);
        if (walked != null) out.append(",\"walk_sent\":").append(walked);
        if (dropped != null) out.append(",\"drop_sent\":").append(dropped);
        out.append('}');
        return out.toString();
    }

    private static String tile(int[] tile) {
        return "[" + tile[0] + "," + tile[1] + "," + tile[2] + "]";
    }

    private static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private static void writeJson(String suffix, String json) throws Exception {
        Path target = dir.resolve(role + "." + suffix);
        if (Files.exists(target)) throw new IllegalStateException("refusing to replace existing " + target.getFileName());
        Path temporary = dir.resolve(role + "." + suffix + ".tmp");
        Files.write(temporary, json.getBytes(StandardCharsets.UTF_8));
        Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE);
    }

    private static String describe(Throwable t) {
        return t.getClass().getSimpleName() + ": " + t.getMessage();
    }

    private static void exit(int code, String message) {
        System.err.println("NativeCoopSmoke " + role + " exit " + code + ": " + message);
        System.exit(code);
    }
}
