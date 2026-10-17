import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import world.gregs.voidps.engine.data.PlayerSave;
import world.gregs.voidps.engine.data.file.FileStorage;
import world.gregs.voidps.engine.entity.item.Item;

/**
 * Fixture-only mechanism proof: immutable generations plus one CURRENT pointer.
 * Modes: baseline ROOT | attempt ROOT HALT_POINT|none | recover ROOT. Not a production storage format.
 * Coins are native inventory Item stacks counted with rawValue(), so no definition or cache lookup occurs.
 */
public final class GraveCheckpointHelper {
    static final int HALTED = 75;
    static final int REFUSED = 2;
    static final String FORMAT = "native-grave-checkpoint-v1";
    static final String BEFORE = "gen-000001";
    static final String AFTER = "gen-000002";
    static final List<String> MEMBERS = List.of("alpha.toml", "beta.toml", "ledger.txt");
    static final List<String> HALT_POINTS = List.of("alpha-write", "beta-write", "ledger-write", "manifest-write",
        "generation-rename", "pointer-temp-fsync", "pointer-replace", "parent-fsync");
    static final Pattern CURRENT = Pattern.compile("format = " + FORMAT + "\ngeneration = (gen-[0-9]{6})\nmanifest_sha256 = ([0-9a-f]{64})\n");
    static final Pattern LEDGER = Pattern.compile("ledger_format = \"" + FORMAT + "\"\npile_coins = ([0-9]+)\nremaining_ticks = ([0-9]+)\nstate_version = ([0-9]+)\n");
    static final long POINTER_LIMIT = 512, MANIFEST_LIMIT = 2048, MEMBER_LIMIT = 65536;
    static final int SLOTS = 28;

    record Generation(String name, int alphaCoins, int betaCoins, int pileCoins, int remainingTicks, int version) {}

    static final Generation BEFORE_STATE = new Generation(BEFORE, 10, 0, 2, 1000, 1);
    static final Generation AFTER_STATE = new Generation(AFTER, 10, 2, 0, 0, 2);

    static final class Refusal extends RuntimeException {
        Refusal(String message) { super(message); }
    }

    public static void main(String[] args) {
        try {
            System.err.println("PROBE_PID " + ProcessHandle.current().pid());
            require(args.length >= 2, "usage: baseline ROOT | attempt ROOT POINT|none | recover ROOT");
            Path root = Paths.get(args[1]).toAbsolutePath();
            switch (args[0]) {
                case "baseline" -> {
                    require(args.length == 2, "baseline takes one root");
                    createFresh(root);
                    publish(root, BEFORE_STATE, "none");
                    System.out.println("BASELINE_CREATED " + BEFORE);
                }
                case "attempt" -> {
                    require(args.length == 3, "attempt takes one halt point");
                    require(args[2].equals("none") || HALT_POINTS.contains(args[2]), "unknown halt point " + args[2]);
                    publish(root, AFTER_STATE, args[2]);
                    System.out.println("PUBLISHED " + AFTER);
                }
                case "recover" -> recover(root);
                default -> throw new Refusal("unknown mode " + args[0]);
            }
        } catch (Refusal refusal) {
            System.err.println("REFUSED: " + refusal.getMessage());
            System.exit(REFUSED);
        } catch (Exception failure) {
            failure.printStackTrace();
            System.exit(1);
        }
    }

    static void createFresh(Path root) throws IOException {
        Files.createDirectory(root);
        Files.createDirectory(root.resolve("sources"));
        Files.createDirectories(root.resolve("state/generations"));
        Files.createDirectory(root.resolve("state/partials"));
    }

    /** Writes one immutable generation: stage, native account saves, ledger, manifest, rename, then pointer swap. */
    static void publish(Path root, Generation state, String requested) throws Exception {
        Path sources = root.resolve("sources");
        Path generations = root.resolve("state/generations");
        Path stage = Files.createDirectory(root.resolve("state/partials").resolve("stage-" + state.name() + "-" + System.nanoTime()));
        FileStorage storage = new FileStorage(stage.toFile());

        storage.save(List.of(account(sources, state, "alpha", state.alphaCoins())));
        fsyncFile(stage.resolve("alpha.toml"));
        halt("alpha-write", requested);

        storage.save(List.of(account(sources, state, "beta", state.betaCoins())));
        fsyncFile(stage.resolve("beta.toml"));
        halt("beta-write", requested);

        writeFsync(stage.resolve("ledger.txt"), ledgerText(state).getBytes(StandardCharsets.UTF_8));
        halt("ledger-write", requested);

        String manifest = manifest(state.name(), stage);
        writeFsync(stage.resolve("MANIFEST"), manifest.getBytes(StandardCharsets.UTF_8));
        halt("manifest-write", requested);
        fsyncDir(stage);

        Files.move(stage, generations.resolve(state.name()), StandardCopyOption.ATOMIC_MOVE);
        fsyncDir(generations);
        halt("generation-rename", requested);

        String current = "format = " + FORMAT + "\ngeneration = " + state.name() + "\nmanifest_sha256 = " + sha(manifest.getBytes(StandardCharsets.UTF_8)) + "\n";
        Path temp = root.resolve("state/CURRENT.tmp-" + System.nanoTime());
        writeFsync(temp, current.getBytes(StandardCharsets.UTF_8));
        halt("pointer-temp-fsync", requested);

        Files.move(temp, root.resolve("state/CURRENT"), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        halt("pointer-replace", requested);

        fsyncDir(root.resolve("state"));
        halt("parent-fsync", requested);
    }

    /** Validates CURRENT and member bytes before native loading, then checks the loaded state tuple. */
    static void recover(Path root) throws Exception {
        requireNoLinkedAncestors(root);
        Path state = root.resolve("state");
        Matcher current = CURRENT.matcher(new String(readRegular(state.resolve("CURRENT"), POINTER_LIMIT), StandardCharsets.UTF_8));
        require(current.matches(), "CURRENT is not the exact pointer shape");
        String generation = current.group(1);
        Path gen = state.resolve("generations").resolve(generation);
        requireNoLinkedAncestors(gen);
        require(Files.isDirectory(gen, LinkOption.NOFOLLOW_LINKS), "pointer target is missing or linked");
        Generation expected = expectedState(generation);

        byte[] manifestBytes = readRegular(gen.resolve("MANIFEST"), MANIFEST_LIMIT);
        require(sha(manifestBytes).equals(current.group(2)), "manifest hash does not match CURRENT");
        Set<String> names = new TreeSet<>();
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(gen)) {
            for (Path entry : entries) names.add(entry.getFileName().toString());
        }
        Set<String> expectedNames = new TreeSet<>(MEMBERS);
        expectedNames.add("MANIFEST");
        require(names.equals(expectedNames), "generation has unlisted entries " + names);
        require(manifest(generation, gen).equals(new String(manifestBytes, StandardCharsets.UTF_8)), "manifest does not match member bytes");

        PlayerSave alpha = PlayerSave.Companion.load(gen.resolve("alpha.toml").toFile());
        PlayerSave beta = PlayerSave.Companion.load(gen.resolve("beta.toml").toFile());
        Matcher ledger = LEDGER.matcher(new String(readRegular(gen.resolve("ledger.txt"), MEMBER_LIMIT), StandardCharsets.UTF_8));
        require(ledger.matches(), "ledger is not the exact shape");

        require(alpha.getName().equals("alpha") && beta.getName().equals("beta"), "account names differ from alpha/beta");
        int alphaCoins = coins(alpha), betaCoins = coins(beta);
        int pileCoins = Integer.parseInt(ledger.group(1)), remaining = Integer.parseInt(ledger.group(2));
        int alphaVersion = version(alpha), betaVersion = version(beta), ledgerVersion = Integer.parseInt(ledger.group(3));
        require(alphaCoins == expected.alphaCoins() && betaCoins == expected.betaCoins() && pileCoins == expected.pileCoins()
            && remaining == expected.remainingTicks() && alphaVersion == expected.version() && betaVersion == expected.version()
            && ledgerVersion == expected.version(), "state tuple is not exactly generation " + generation);
        require(alphaCoins + betaCoins + pileCoins == 12, "coins not conserved");
        String label = generation.equals(BEFORE) ? "BASELINE" : "AFTER";
        System.out.println("{\"generation\":\"" + generation + "\",\"state\":\"" + label + "\",\"alpha_coins\":" + alphaCoins
            + ",\"alpha_version\":" + alphaVersion + ",\"beta_coins\":" + betaCoins + ",\"beta_version\":" + betaVersion
            + ",\"ledger_pile_coins\":" + pileCoins + ",\"ledger_remaining_ticks\":" + remaining + ",\"ledger_version\":" + ledgerVersion
            + ",\"total_coins\":" + (alphaCoins + betaCoins + pileCoins) + ",\"native_loaded_accounts\":2,\"manifest_sha256\":\"" + current.group(2) + "\"}");
    }

    static Generation expectedState(String generation) {
        if (generation.equals(BEFORE)) return BEFORE_STATE;
        if (generation.equals(AFTER)) return AFTER_STATE;
        throw new Refusal("unknown generation label " + generation);
    }

    static void requireNoLinkedAncestors(Path path) {
        for (Path p = path; p != null; p = p.getParent()) {
            if (Files.isSymbolicLink(p)) throw new Refusal("linked path component " + p);
        }
    }

    static String manifest(String generation, Path dir) throws Exception {
        StringBuilder text = new StringBuilder("format = " + FORMAT + "\ngeneration = " + generation + "\n");
        for (String member : MEMBERS) {
            byte[] bytes = readRegular(dir.resolve(member), MEMBER_LIMIT);
            text.append("member ").append(member).append(" sha256 = ").append(sha(bytes)).append(" bytes = ").append(bytes.length).append('\n');
        }
        return text.toString();
    }

    static PlayerSave account(Path sources, Generation state, String name, int coins) throws Exception {
        String zeroes = String.join(",", Collections.nCopies(25, "0"));
        String levels = String.join(",", Collections.nCopies(25, "1"));
        StringBuilder slots = new StringBuilder(coins > 0 ? "{id = \"coins\", amount = " + coins + "}" : "{}");
        for (int slot = 1; slot < SLOTS; slot++) slots.append(", {}");
        String text = "accountName = \"" + name + "\"\npasswordHash = \"fixture-only\"\n"
            + "experience = [" + zeroes + "]\nlevels = [" + levels + "]\nlooks = [0,0,0,0,0,0,0]\ncolours = [0,0,0,0,0]\n"
            + "[tile]\nx = 3232\ny = 3232\n[variables]\nstate_version = " + state.version() + "\n"
            + "[inventories]\ninventory = [" + slots + "]\n";
        Path source = sources.resolve("source-" + state.name() + "-" + name + ".toml");
        Files.write(source, text.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        return PlayerSave.Companion.load(source.toFile());
    }

    static String ledgerText(Generation state) {
        return "ledger_format = \"" + FORMAT + "\"\npile_coins = " + state.pileCoins() + "\nremaining_ticks = " + state.remainingTicks()
            + "\nstate_version = " + state.version() + "\n";
    }

    /** Counts native coin stacks by raw stored amount; no ItemDefinitions or cache lookup. */
    static int coins(PlayerSave save) {
        Item[] slots = save.getInventories().get("inventory");
        require(slots != null && slots.length == SLOTS, "account inventory shape differs");
        int total = 0;
        for (Item slot : slots) {
            if (slot != null && "coins".equals(slot.getId())) total += slot.rawValue();
        }
        return total;
    }

    static int version(PlayerSave save) {
        Object value = save.getVariables().get("state_version");
        require(value instanceof Number, "account lacks numeric state_version");
        return ((Number) value).intValue();
    }

    static byte[] readRegular(Path path, long limit) throws IOException {
        require(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS), "not a regular member: " + path.getFileName());
        require(Files.size(path) <= limit, "member exceeds bound: " + path.getFileName());
        try (InputStream input = Files.newInputStream(path, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(Math.toIntExact(limit) + 1);
            require(bytes.length <= limit, "member grew beyond bound: " + path.getFileName());
            return bytes;
        }
    }

    static void fsyncFile(Path file) throws IOException {
        try (FileChannel channel = FileChannel.open(file, StandardOpenOption.WRITE)) {
            channel.force(true);
        }
    }

    static void writeFsync(Path file, byte[] bytes) throws IOException {
        try (FileChannel channel = FileChannel.open(file, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) channel.write(buffer);
            channel.force(true);
        }
    }

    static void fsyncDir(Path dir) throws IOException {
        try (FileChannel channel = FileChannel.open(dir, StandardOpenOption.READ)) {
            channel.force(true);
        }
    }

    static void halt(String point, String requested) {
        if (point.equals(requested)) {
            System.out.println("HALT " + point);
            System.out.flush();
            Runtime.getRuntime().halt(HALTED);
        }
    }

    static String sha(byte[] bytes) throws Exception {
        StringBuilder hex = new StringBuilder();
        for (byte value : MessageDigest.getInstance("SHA-256").digest(bytes)) hex.append(String.format("%02x", value & 255));
        return hex.toString();
    }

    static void require(boolean ok, String message) {
        if (!ok) throw new Refusal(message);
    }
}
