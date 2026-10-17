import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import world.gregs.voidps.cache.Cache;
import world.gregs.voidps.cache.FileCache;
import world.gregs.voidps.cache.definition.data.ItemDefinition;
import world.gregs.voidps.cache.definition.decoder.ItemDecoder;
import world.gregs.voidps.engine.data.PlayerSave;
import world.gregs.voidps.engine.data.definition.ItemDefinitions;
import world.gregs.voidps.engine.data.file.FileStorage;
import world.gregs.voidps.engine.entity.item.Item;
import world.gregs.voidps.engine.inv.Inventory;
import world.gregs.voidps.engine.inv.remove.DefaultItemAmountBounds;
import world.gregs.voidps.engine.inv.restrict.NoRestrictions;
import world.gregs.voidps.engine.inv.stack.ItemDependentStack;
import world.gregs.voidps.engine.inv.transact.Transaction;
import world.gregs.voidps.engine.inv.transact.operation.AddItem;
import world.gregs.voidps.engine.inv.transact.operation.RemoveItem;

/**
 * Fixture-only Lab token helper, version 1. Original code, no proprietary assets.
 * Modes: inject CACHE_DIR SAVE_FILE | read CACHE_DIR SAVE_FILE.
 * Inject adds 3, removes 1, proves an over-remove of 3 is rejected and rolled back, then saves through FileStorage.
 * Read loads the save and requires exactly one lab_token stack of 2. Read never rewrites the save; both modes
 * create and delete a temporary mapping file inside the run directory.
 * Not a production item path: the definition comes from the native cache plus one original id mapping.
 */
public final class LabTokenHelper {
    static final int REFUSED = 2;
    /** Only fixture runs under this root may be read or written. Resolved from the repository working directory. */
    static final Path SAVE_ROOT = Paths.get(".runtime/native-lab-token").toAbsolutePath().normalize();
    static final String MARKER = ".lab-token-fixture";
    static final String ACCOUNT = "AlphaTest";
    static final String INVENTORY = "inventory";
    static final String TOKEN = "lab_token";
    static final String NAME = "SoloScape Lab token";
    static final int COST = 37;
    static final int TARGET = 20179;
    /** Item 20179 is index 19, archive 78, file 211 (archive << 8 | file). */
    static final int INDEX = 19;
    static final int ARCHIVE = 78;
    static final int FILE = 211;
    static final long FILE_LIMIT = 1L << 20;

    static final class Refusal extends RuntimeException { Refusal(String message) { super(message); } }

    public static void main(String[] args) {
        try {
            System.err.println("PROBE_PID " + ProcessHandle.current().pid());
            require(args.length == 3, "usage: inject|read CACHE_DIR SAVE_FILE");
            boolean inject = switch (args[0]) {
                case "inject" -> true;
                case "read" -> false;
                default -> throw new Refusal("unknown mode " + args[0]);
            };
            Path cacheDir = Paths.get(args[1]).toAbsolutePath().normalize();
            Path saveFile = Paths.get(args[2]).toAbsolutePath().normalize();
            System.out.println(run(inject, cacheDir, saveFile));
        } catch (Refusal refusal) {
            System.err.println("REFUSED: " + refusal.getMessage());
            System.exit(REFUSED);
        } catch (Exception failure) {
            failure.printStackTrace();
            System.exit(1);
        }
    }

    static String run(boolean inject, Path cacheDir, Path saveFile) throws Exception {
        requireNoLinkedAncestors(cacheDir);
        require(Files.isDirectory(cacheDir, LinkOption.NOFOLLOW_LINKS), "cache is not a directory");
        requireNoLinkedAncestors(saveFile);
        Path run = runDirectory(saveFile);
        // Cache gate first: the save bytes are not touched unless item 20179 decodes from the cache.
        ItemDefinition[] definitions = decodeItems(cacheDir);
        ItemDefinition token = initDefinitions(definitions, run);
        PlayerSave save = loadSave(saveFile);
        Item[] slots = save.getInventories().get(INVENTORY);
        require(slots != null, "save has no " + INVENTORY + " array");
        Map<String, Object> out = row("mode", inject ? "inject" : "read", "semantic", TOKEN, "id", TARGET,
            "name", token.getName(), "cost", token.getCost(), "stackable", token.getStackable(),
            "itemarraycount", definitions.length, "nativearraycount", slots.length);
        if (inject) {
            require(!holdsToken(save), TOKEN + " already present; refusing to inject");
            int[] shape = transact(save, slots, saveFile);
            out.put("tokenquantity", shape[1]);
            out.put("slotcount", shape[2]);
            out.put("transactioncheckflags", row("add3_remove1_committed", true,
                "overremove3_rejected_and_rolled_back", true, "single_stack_qty2", true));
        } else {
            int[] shape = shape(slots);
            require(shape[0] == 1 && shape[1] == 2, TOKEN + " must be one stack of 2, found " + shape[0] + " stacks, quantity " + shape[1]);
            out.put("quantity", shape[1]);
            out.put("slotcount", shape[2]);
        }
        return json(out);
    }

    /** Native cache decode. Refuses before any save byte is read when item 20179 is absent. */
    static ItemDefinition[] decodeItems(Path cacheDir) throws Exception {
        Path main = cacheDir.resolve("main_file_cache.dat2");
        Path table = cacheDir.resolve("main_file_cache.idx255");
        require(Files.isRegularFile(main, LinkOption.NOFOLLOW_LINKS) && Files.isRegularFile(table, LinkOption.NOFOLLOW_LINKS),
            "cache main or idx255 is missing");
        try (RandomAccessFile data = new RandomAccessFile(main.toFile(), "r");
             RandomAccessFile reference = new RandomAccessFile(table.toFile(), "r")) {
            Cache cache = FileCache.Companion.load(cacheDir.toString(), main.toFile(), data, table.toFile(), reference,
                Math.toIntExact(reference.length() / 6), null, null, 1.0);
            try {
                byte[] payload;
                try {
                    payload = cache.data(INDEX, ARCHIVE, FILE, null);
                } catch (RuntimeException missing) {
                    payload = null;
                }
                require(payload != null && payload.length > 0, "cache lacks item " + TARGET + " at " + INDEX + "/" + ARCHIVE + "/" + FILE);
                ItemDefinition[] definitions = new ItemDecoder().load(cache);
                require(definitions.length > TARGET, "decoded item array is too short: " + definitions.length);
                return definitions;
            } finally {
                cache.close();
            }
        }
    }

    /** Binds only the original [lab_token] id mapping. The temporary file lives in the owned run and is always deleted. */
    static ItemDefinition initDefinitions(ItemDefinition[] definitions, Path run) throws Exception {
        Path mapping = Files.createTempFile(run, "lab-token-map", ".toml");
        try {
            Files.writeString(mapping, "[" + TOKEN + "]\nid = " + TARGET + "\n", StandardCharsets.UTF_8);
            ItemDefinitions.INSTANCE.init(definitions).load(List.of(mapping.toString()));
        } finally {
            Files.deleteIfExists(mapping);
        }
        ItemDefinition token = ItemDefinitions.INSTANCE.getOrNull(TOKEN);
        require(token != null && token == definitions[TARGET], "mapping did not bind " + TOKEN + " to " + TARGET);
        require(NAME.equals(token.getName()) && token.getCost() == COST && token.getStackable() == 1,
            TOKEN + " definition differs from the original");
        return token;
    }

    /** Native PlayerSave load. The file name must be the one FileStorage writes for this account, so the save is rewritten in place. */
    static PlayerSave loadSave(Path saveFile) throws Exception {
        String expected = ACCOUNT.toLowerCase(Locale.ROOT) + ".toml";
        require(saveFile.getFileName().toString().equals(expected), "save must be " + expected);
        require(Files.isRegularFile(saveFile, LinkOption.NOFOLLOW_LINKS), "save is not a regular file");
        require(Files.size(saveFile) <= FILE_LIMIT, "save exceeds bound");
        PlayerSave save = PlayerSave.Companion.load(saveFile.toFile());
        require(ACCOUNT.equals(save.getName()), "save account is not " + ACCOUNT);
        return save;
    }

    /** Runs the add/remove/over-remove sequence on the native Inventory, then saves through FileStorage. */
    static int[] transact(PlayerSave save, Item[] slots, Path saveFile) throws Exception {
        Inventory inventory = new Inventory(slots, INVENTORY, NoRestrictions.INSTANCE,
            ItemDependentStack.INSTANCE, DefaultItemAmountBounds.INSTANCE);
        Transaction txn = inventory.getTransaction();
        txn.start();
        AddItem.INSTANCE.add(txn, TOKEN, 3);
        RemoveItem.INSTANCE.remove(txn, TOKEN, 1);
        require(txn.commit(), "add 3 then remove 1 did not commit");
        txn.start();
        RemoveItem.INSTANCE.remove(txn, TOKEN, 3);
        require(!txn.commit(), "over-remove of 3 was not rejected");
        // Revert swaps in a copy of the array, so the save's own Item[] is refreshed from the native state.
        System.arraycopy(inventory.getItems(), 0, slots, 0, slots.length);
        int[] shape = shape(slots);
        require(shape[0] == 1 && shape[1] == 2, "rollback left " + shape[0] + " stacks, quantity " + shape[1]);
        new FileStorage(saveFile.getParent().toFile()).save(List.of(save));
        return shape;
    }

    /** Returns {token stacks, token quantity, used slots}. */
    static int[] shape(Item[] slots) {
        int stacks = 0;
        int quantity = 0;
        int used = 0;
        for (Item item : slots) {
            if (item.isEmpty()) continue;
            used++;
            if (TOKEN.equals(item.getId())) {
                stacks++;
                quantity += item.getAmount();
            }
        }
        return new int[] {stacks, quantity, used};
    }

    static boolean holdsToken(PlayerSave save) {
        return save.getInventories().values().stream()
            .anyMatch(items -> Arrays.stream(items).anyMatch(item -> TOKEN.equals(item.getId())));
    }

    /** Requires SAVE_ROOT/<run>/ to be a real directory holding the marker. The save must sit inside that run. */
    static Path runDirectory(Path saveFile) {
        require(saveFile.startsWith(SAVE_ROOT) && !saveFile.equals(SAVE_ROOT), "save is outside " + SAVE_ROOT);
        Path relative = SAVE_ROOT.relativize(saveFile);
        require(relative.getNameCount() >= 2, "save must sit inside a run directory");
        Path run = SAVE_ROOT.resolve(relative.getName(0));
        require(Files.isDirectory(run, LinkOption.NOFOLLOW_LINKS), "run directory is missing");
        require(Files.isRegularFile(run.resolve(MARKER), LinkOption.NOFOLLOW_LINKS), "run directory lacks " + MARKER);
        return run;
    }

    static Map<String, Object> row(Object... pairs) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) out.put((String) pairs[i], pairs[i + 1]);
        return out;
    }

    static String json(Object value) {
        StringBuilder out = new StringBuilder();
        append(out, value);
        return out.toString();
    }

    static void append(StringBuilder out, Object value) {
        if (value instanceof Map<?, ?> map) {
            out.append('{');
            map.forEach((key, item) -> {
                if (out.charAt(out.length() - 1) != '{') out.append(',');
                out.append('"').append(key).append("\":");
                append(out, item);
            });
            out.append('}');
        } else if (value instanceof String text) {
            out.append('"').append(text.replace("\\", "\\\\").replace("\"", "\\\"")).append('"');
        } else if (value instanceof Integer || value instanceof Boolean) {
            out.append(value);
        } else {
            throw new IllegalStateException("harness cannot serialize " + value);
        }
    }

    static void requireNoLinkedAncestors(Path path) {
        for (Path p = path; p != null; p = p.getParent()) {
            if (Files.isSymbolicLink(p)) throw new Refusal("linked path component " + p);
        }
    }

    static void require(boolean ok, String message) {
        if (!ok) throw new Refusal(message);
    }
}
