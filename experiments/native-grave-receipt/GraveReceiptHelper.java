import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.Pattern;
import world.gregs.voidps.engine.data.PlayerSave;
import world.gregs.voidps.engine.data.file.FileStorage;
import world.gregs.voidps.engine.entity.item.Item;

/**
 * Fixture-only mechanism proof: whole-pile receipts stored inside existing per-account PlayerSave variables.
 * Modes: baseline ROOT | step ROOT ACTION HALT|none | gc ROOT HALT|none | dump ROOT | recover ROOT.
 * Coins are native inventory Item stacks counted with rawValue(). Not a production format or a save-format decision.
 */
public final class GraveReceiptHelper {
    static final int HALTED = 75;
    static final int REFUSED = 2;
    static final int SLOTS = 28;
    static final long FILE_LIMIT = 65536;
    static final String OWNER = "alpha";
    static final String GUEST = "beta";
    static final String PILE = "original-pile-1";
    static final String CLAIM = "claim-1";
    static final int PILE_COINS = 2;
    static final int PILE_TICKS = 1000;
    static final Pattern IDENT = Pattern.compile("[a-z0-9][a-z0-9-]{0,31}");
    static final Set<String> ACCOUNT_KEYS = Set.of("consumed_coins", "death_sequence", "source_high_water", "save_generation", "piles", "receipts");
    static final Set<String> PILE_KEYS = Set.of("id", "base", "source_seq", "remaining_ticks");
    static final Set<String> RECEIPT_KEYS = Set.of("owner", "pile_id", "source_seq", "quantity", "claim_id");
    static int nativeLoads;

    record Pile(String id, int base, int sourceSeq, int remainingTicks) {}
    record Receipt(String owner, String pileId, int sourceSeq, int quantity, String claimId) {}
    /** inventory and bank hold native coin stacks; consumed is the explicit fixture sink counter. */
    record Acct(String name, int inventory, int bank, int consumed, int deathSequence, int highWater, int saveGeneration,
                List<Pile> piles, List<Receipt> receipts) {}
    /** Protocol result: per-pile claimed and floor coins, and one status per guest receipt ("applied" or "retired"). */
    record Result(int floor, List<Integer> claimed, List<Integer> pileFloors, List<String> receiptStatus) {}

    static final class Refusal extends RuntimeException {
        Refusal(String message) { super(message); }
    }

    public static void main(String[] args) {
        try {
            System.err.println("PROBE_PID " + ProcessHandle.current().pid());
            require(args.length >= 2, "usage: baseline ROOT | step ROOT ACTION HALT|none | gc ROOT HALT|none | dump ROOT | recover ROOT");
            Path root = Paths.get(args[1]).toAbsolutePath();
            switch (args[0]) {
                case "baseline" -> {
                    require(args.length == 2, "baseline takes one root");
                    baseline(root);
                    System.out.println("BASELINE_CREATED");
                }
                case "step" -> {
                    require(args.length == 4, "step takes ROOT ACTION HALT|none");
                    step(root, args[2], args[3]);
                }
                case "gc" -> {
                    require(args.length == 3, "gc takes ROOT HALT|none");
                    gc(root, args[2]);
                }
                case "dump" -> System.out.println(dump(root));
                case "recover" -> System.out.println(recover(root));
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

    static void baseline(Path root) throws Exception {
        requireNoLinkedAncestors(root);
        Files.createDirectory(root);
        for (String directory : List.of("sources", "saves", "errors")) Files.createDirectory(root.resolve(directory));
        persist(root, root.resolve("saves"), List.of(
            new Acct(OWNER, 10, 0, 0, 0, 0, 1, List.of(), List.of()),
            new Acct(GUEST, 0, 0, 0, 0, 0, 1, List.of(), List.of())));
    }

    /** One protocol-visible action on one account file. Each action is a separate JVM with at most one halt point. */
    static void step(Path root, String action, String halt) throws Exception {
        requireLayout(root);
        require(halt.equals("none") || halt.equals(action + "-before-save") || halt.equals(action + "-after-save"),
            "halt point " + halt + " does not belong to " + action);
        Path saves = root.resolve("saves");
        Acct owner = load(saves, OWNER);
        Acct guest = load(saves, GUEST);
        switch (action) {
            case "death" -> {
                require(owner.deathSequence() == 0 && owner.piles().isEmpty(), "death requires a pre-death owner file");
                require(owner.inventory() >= PILE_COINS, "owner has too few coins for the pile");
                save(root, saves, action, halt, new Acct(OWNER, owner.inventory() - PILE_COINS, owner.bank(), owner.consumed(), 1, 1,
                    owner.saveGeneration() + 1, List.of(new Pile(PILE, PILE_COINS, 1, PILE_TICKS)), List.of()));
            }
            case "pickup", "fallback-pickup" -> {
                Result result = reconcile(owner, guest);
                require(owner.piles().size() == 1 && PILE.equals(owner.piles().get(0).id()) && owner.piles().get(0).sourceSeq() == 1,
                    "source barrier: primary owner file lacks the committed pile record");
                int quantity = result.floor();
                require(quantity > 0, "pile has no unclaimed coins");
                Path target = action.equals("fallback-pickup") ? root.resolve("errors") : saves;
                save(root, target, action, halt, new Acct(GUEST, guest.inventory() + quantity, guest.bank(), guest.consumed(),
                    guest.deathSequence(), guest.highWater(), guest.saveGeneration() + 1, guest.piles(),
                    append(guest.receipts(), new Receipt(OWNER, PILE, 1, quantity, CLAIM))));
            }
            case "bypass-pickup" -> save(root, saves, action, halt, new Acct(GUEST, guest.inventory() + PILE_COINS, guest.bank(),
                guest.consumed(), guest.deathSequence(), guest.highWater(), guest.saveGeneration() + 1, guest.piles(),
                append(guest.receipts(), new Receipt(OWNER, PILE, 1, PILE_COINS, CLAIM))));
            case "resave" -> save(root, saves, action, halt, new Acct(OWNER, owner.inventory(), owner.bank(), owner.consumed(),
                owner.deathSequence(), owner.highWater(), owner.saveGeneration() + 1, owner.piles(), owner.receipts()));
            case "bank" -> save(root, saves, action, halt, new Acct(GUEST, 0, guest.bank() + guest.inventory(), guest.consumed(),
                guest.deathSequence(), guest.highWater(), guest.saveGeneration() + 1, guest.piles(), guest.receipts()));
            case "consume" -> save(root, saves, action, halt, new Acct(GUEST, 0, guest.bank(), guest.consumed() + guest.inventory(),
                guest.deathSequence(), guest.highWater(), guest.saveGeneration() + 1, guest.piles(), guest.receipts()));
            case "erase-receipt" -> save(root, saves, action, halt, new Acct(GUEST, guest.inventory(), guest.bank(), guest.consumed(),
                guest.deathSequence(), guest.highWater(), guest.saveGeneration() + 1, guest.piles(), List.of()));
            default -> throw new Refusal("unknown action " + action);
        }
        System.out.println("STEP_DONE " + action);
    }

    /** Exclusive boot phase: reconcile first (refusals write nothing), then retire fully claimed piles, then GC their receipts. */
    static void gc(Path root, String halt) throws Exception {
        requireLayout(root);
        require(List.of("none", "retire-before-save", "retire-after-save", "gc-before-save", "gc-after-save").contains(halt),
            "halt point " + halt + " does not belong to gc");
        Path saves = root.resolve("saves");
        Acct owner = load(saves, OWNER);
        Acct guest = load(saves, GUEST);
        Result result = reconcile(owner, guest);
        List<Pile> retire = new ArrayList<>();
        for (int index = 0; index < owner.piles().size(); index++) {
            if (result.pileFloors().get(index) == 0) retire.add(owner.piles().get(index));
        }
        if (!retire.isEmpty()) {
            List<Pile> kept = owner.piles().stream().filter(pile -> !retire.contains(pile)).toList();
            owner = new Acct(OWNER, owner.inventory(), owner.bank(), owner.consumed(), owner.deathSequence(), owner.highWater(),
                owner.saveGeneration() + 1, kept, owner.receipts());
            save(root, saves, "retire", halt, owner);
            result = reconcile(owner, guest);
        }
        List<Receipt> kept = new ArrayList<>();
        for (int index = 0; index < guest.receipts().size(); index++) {
            if (!"retired".equals(result.receiptStatus().get(index))) kept.add(guest.receipts().get(index));
        }
        if (kept.size() != guest.receipts().size()) {
            save(root, saves, "gc", halt, new Acct(GUEST, guest.inventory(), guest.bank(), guest.consumed(), guest.deathSequence(),
                guest.highWater(), guest.saveGeneration() + 1, guest.piles(), kept));
        }
        System.out.println("GC_DONE");
    }

    /** Protocol: receipts are applied once to a live pile; a missing pile is retired only with a retained high-water mark. */
    static Result reconcile(Acct owner, Acct guest) {
        require(owner.name().equals(OWNER) && guest.name().equals(GUEST), "account identity differs");
        Set<String> claims = new HashSet<>();
        for (Receipt receipt : guest.receipts()) {
            require(OWNER.equals(receipt.owner()), "receipt names unknown source " + receipt.owner());
            require(claims.add(receipt.claimId()), "duplicate claim " + receipt.claimId());
        }
        List<Integer> claimed = new ArrayList<>();
        List<Integer> floors = new ArrayList<>();
        int floor = 0;
        for (Pile pile : owner.piles()) {
            require(pile.sourceSeq() <= owner.deathSequence(), "live pile lacks a committed death sequence " + pile.id());
            int total = 0;
            for (Receipt receipt : guest.receipts()) {
                if (sameSource(receipt, pile)) total += receipt.quantity();
            }
            require(total <= pile.base(), "receipts exceed pile base " + pile.id());
            claimed.add(total);
            floors.add(pile.base() - total);
            floor += pile.base() - total;
        }
        List<String> statuses = new ArrayList<>();
        for (Receipt receipt : guest.receipts()) {
            if (owner.piles().stream().anyMatch(pile -> sameSource(receipt, pile))) {
                statuses.add("applied");
            } else {
                require(owner.deathSequence() >= receipt.sourceSeq(), "missing owner record below receipt sequence; refusing");
                require(owner.highWater() >= receipt.sourceSeq(), "missing owner record without retained high-water; refusing");
                statuses.add("retired");
            }
        }
        return new Result(floor, claimed, floors, statuses);
    }

    static boolean sameSource(Receipt receipt, Pile pile) {
        return receipt.pileId().equals(pile.id()) && receipt.sourceSeq() == pile.sourceSeq();
    }

    static String dump(Path root) throws Exception {
        requireLayout(root);
        Path saves = root.resolve("saves");
        Acct owner = load(saves, OWNER);
        Acct guest = load(saves, GUEST);
        return "{\"" + OWNER + "\":" + accountJson(owner) + ",\"" + GUEST + "\":" + accountJson(guest)
            + ",\"native_loaded_accounts\":" + nativeLoads + "}";
    }

    static String recover(Path root) throws Exception {
        requireLayout(root);
        Path saves = root.resolve("saves");
        Acct owner = load(saves, OWNER);
        Acct guest = load(saves, GUEST);
        Result result = reconcile(owner, guest);
        List<String> piles = new ArrayList<>();
        for (int index = 0; index < owner.piles().size(); index++) {
            Pile pile = owner.piles().get(index);
            piles.add(String.format("{\"id\":\"%s\",\"base\":%d,\"source_seq\":%d,\"claimed\":%d,\"floor\":%d}",
                pile.id(), pile.base(), pile.sourceSeq(), result.claimed().get(index), result.pileFloors().get(index)));
        }
        List<String> receipts = new ArrayList<>();
        for (int index = 0; index < guest.receipts().size(); index++) {
            Receipt receipt = guest.receipts().get(index);
            receipts.add(String.format("{\"claim_id\":\"%s\",\"quantity\":%d,\"source_seq\":%d,\"status\":\"%s\"}",
                receipt.claimId(), receipt.quantity(), receipt.sourceSeq(), result.receiptStatus().get(index)));
        }
        return String.format("{\"owner\":{\"inventory\":%d,\"bank\":%d},\"guest\":{\"inventory\":%d,\"bank\":%d,\"consumed_coins\":%d},"
                + "\"floor\":%d,\"live_piles\":[%s],\"receipts\":[%s],\"native_loaded_accounts\":%d}",
            owner.inventory(), owner.bank(), guest.inventory(), guest.bank(), guest.consumed(), result.floor(),
            String.join(",", piles), String.join(",", receipts), nativeLoads);
    }

    static String accountJson(Acct account) {
        List<String> piles = account.piles().stream().map(pile -> String.format(
            "{\"id\":\"%s\",\"base\":%d,\"source_seq\":%d,\"remaining_ticks\":%d}",
            pile.id(), pile.base(), pile.sourceSeq(), pile.remainingTicks())).toList();
        List<String> receipts = account.receipts().stream().map(receipt -> String.format(
            "{\"owner\":\"%s\",\"pile_id\":\"%s\",\"source_seq\":%d,\"quantity\":%d,\"claim_id\":\"%s\"}",
            receipt.owner(), receipt.pileId(), receipt.sourceSeq(), receipt.quantity(), receipt.claimId())).toList();
        return String.format("{\"name\":\"%s\",\"inventory\":%d,\"bank\":%d,\"consumed_coins\":%d,\"death_sequence\":%d,"
                + "\"source_high_water\":%d,\"save_generation\":%d,\"piles\":[%s],\"receipts\":[%s]}",
            account.name(), account.inventory(), account.bank(), account.consumed(), account.deathSequence(), account.highWater(),
            account.saveGeneration(), String.join(",", piles), String.join(",", receipts));
    }

    static Acct load(Path saves, String name) throws Exception {
        Path file = saves.resolve(name + ".toml");
        readRegular(file, FILE_LIMIT);
        PlayerSave save = PlayerSave.Companion.load(file.toFile());
        nativeLoads++;
        require(name.equals(save.getName()), "account name differs from its file " + name);
        require(save.getInventories().containsKey("inventory"), "inventory section missing");
        int[] coins = new int[2];
        for (Map.Entry<String, Item[]> inventory : save.getInventories().entrySet()) {
            int index = switch (inventory.getKey()) {
                case "inventory" -> 0;
                case "bank" -> 1;
                default -> throw new Refusal("unexpected inventory " + inventory.getKey());
            };
            for (Item slot : inventory.getValue()) {
                if (slot == null || slot.getId() == null || slot.getId().isEmpty()) continue;
                require("coins".equals(slot.getId()), "fixture holds a non-coin item " + slot.getId());
                coins[index] += slot.rawValue();
            }
        }
        Map<String, Object> variables = save.getVariables();
        require(variables.keySet().equals(ACCOUNT_KEYS), "variable keys differ: " + variables.keySet());
        return new Acct(name, coins[0], coins[1], integer(variables.get("consumed_coins"), 0),
            integer(variables.get("death_sequence"), 0), integer(variables.get("source_high_water"), 0),
            integer(variables.get("save_generation"), 1), decodePiles(variables.get("piles")),
            decodeReceipts(variables.get("receipts")));
    }

    static List<Pile> decodePiles(Object value) {
        require(value instanceof List<?>, "piles is not a list");
        List<Pile> piles = new ArrayList<>();
        for (Object element : (List<?>) value) {
            Map<String, Object> fields = fields(element, PILE_KEYS);
            piles.add(new Pile(identifier(fields.get("id")), integer(fields.get("base"), 0),
                integer(fields.get("source_seq"), 1), integer(fields.get("remaining_ticks"), 0)));
        }
        return piles;
    }

    static List<Receipt> decodeReceipts(Object value) {
        require(value instanceof List<?>, "receipts is not a list");
        List<Receipt> receipts = new ArrayList<>();
        for (Object element : (List<?>) value) {
            Map<String, Object> fields = fields(element, RECEIPT_KEYS);
            receipts.add(new Receipt(identifier(fields.get("owner")), identifier(fields.get("pile_id")),
                integer(fields.get("source_seq"), 1), integer(fields.get("quantity"), 1), identifier(fields.get("claim_id"))));
        }
        return receipts;
    }

    static Map<String, Object> fields(Object value, Set<String> keys) {
        require(value instanceof Map<?, ?>, "record is not a map");
        Map<?, ?> map = (Map<?, ?>) value;
        require(map.keySet().equals(keys), "record fields differ: " + map.keySet());
        Map<String, Object> fields = new TreeMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) fields.put((String) entry.getKey(), entry.getValue());
        return fields;
    }

    static int integer(Object value, int min) {
        require(value instanceof Integer || value instanceof Long, "value is not an integer");
        long number = ((Number) value).longValue();
        require(number >= min && number <= Integer.MAX_VALUE, "integer out of range");
        return (int) number;
    }

    static String identifier(Object value) {
        require(value instanceof String text && IDENT.matcher(text).matches(), "identity is not a bounded identifier");
        return (String) value;
    }

    static String toml(Acct account) {
        String zeroes = String.join(",", Collections.nCopies(25, "0"));
        String levels = String.join(",", Collections.nCopies(25, "1"));
        List<String> piles = account.piles().stream().map(pile -> String.format(
            "{id = \"%s\", base = %d, source_seq = %d, remaining_ticks = %d}",
            pile.id(), pile.base(), pile.sourceSeq(), pile.remainingTicks())).toList();
        List<String> receipts = account.receipts().stream().map(receipt -> String.format(
            "{owner = \"%s\", pile_id = \"%s\", source_seq = %d, quantity = %d, claim_id = \"%s\"}",
            receipt.owner(), receipt.pileId(), receipt.sourceSeq(), receipt.quantity(), receipt.claimId())).toList();
        return "accountName = \"" + account.name() + "\"\npasswordHash = \"fixture-only\"\n"
            + "experience = [" + zeroes + "]\nlevels = [" + levels + "]\nlooks = [0,0,0,0,0,0,0]\ncolours = [0,0,0,0,0]\n"
            + "[tile]\nx = 3232\ny = 3232\n"
            + "[variables]\n"
            + "consumed_coins = " + account.consumed() + "\n"
            + "death_sequence = " + account.deathSequence() + "\n"
            + "source_high_water = " + account.highWater() + "\n"
            + "save_generation = " + account.saveGeneration() + "\n"
            + "piles = [" + String.join(", ", piles) + "]\n"
            + "receipts = [" + String.join(", ", receipts) + "]\n"
            + "[inventories]\n"
            + "inventory = [" + slots(account.inventory()) + "]\n"
            + "bank = [" + slots(account.bank()) + "]\n";
    }

    static String slots(int coins) {
        List<String> entries = new ArrayList<>();
        entries.add(coins > 0 ? "{id = \"coins\", amount = " + coins + "}" : "{}");
        for (int slot = 1; slot < SLOTS; slot++) entries.add("{}");
        return String.join(", ", entries);
    }

    /** Writes account TOML as a fixture source, loads it through the native reader, then saves through FileStorage. */
    static void persist(Path root, Path directory, List<Acct> accounts) throws Exception {
        List<PlayerSave> loaded = new ArrayList<>();
        for (Acct account : accounts) {
            Path source = root.resolve("sources").resolve(account.name() + "-" + System.nanoTime() + ".toml");
            Files.write(source, toml(account).getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
            loaded.add(PlayerSave.Companion.load(source.toFile()));
        }
        new FileStorage(directory.toFile()).save(loaded);
    }

    static void save(Path root, Path directory, String action, String halt, Acct next) throws Exception {
        halt(action + "-before-save", halt);
        persist(root, directory, List.of(next));
        halt(action + "-after-save", halt);
    }

    static void halt(String point, String requested) {
        if (point.equals(requested)) {
            System.out.println("HALT " + point);
            System.out.flush();
            Runtime.getRuntime().halt(HALTED);
        }
    }

    static <T> List<T> append(List<T> items, T item) {
        List<T> out = new ArrayList<>(items);
        out.add(item);
        return out;
    }

    static void requireLayout(Path root) throws IOException {
        requireNoLinkedAncestors(root);
        for (Path directory : List.of(root, root.resolve("saves"), root.resolve("errors"), root.resolve("sources"))) {
            require(Files.isDirectory(directory, LinkOption.NOFOLLOW_LINKS), "not a plain directory: " + directory.getFileName());
        }
    }

    static void requireNoLinkedAncestors(Path path) {
        for (Path p = path; p != null; p = p.getParent()) {
            if (Files.isSymbolicLink(p)) throw new Refusal("linked path component " + p);
        }
    }

    static byte[] readRegular(Path path, long limit) throws IOException {
        require(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS), "not a regular account file: " + path.getFileName());
        require(Files.size(path) <= limit, "account file exceeds bound: " + path.getFileName());
        try (InputStream input = Files.newInputStream(path, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(Math.toIntExact(limit) + 1);
            require(bytes.length <= limit, "account file grew beyond bound: " + path.getFileName());
            return bytes;
        }
    }

    static void require(boolean ok, String message) {
        if (!ok) throw new Refusal(message);
    }
}
