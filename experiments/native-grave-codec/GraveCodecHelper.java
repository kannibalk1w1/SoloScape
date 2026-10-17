import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.Callable;
import java.util.function.Consumer;
import java.util.regex.Pattern;
import world.gregs.voidps.engine.data.PlayerSave;
import world.gregs.voidps.engine.data.file.FileStorage;
import world.gregs.voidps.engine.entity.item.Item;

/**
 * Fixture-only bounded grave/pile snapshot codec, version 1. Original code, no proprietary data.
 * Modes: write ROOT | read ROOT | checks.
 * The encoded snapshot travels as PlayerSave.variables['grave_lab_state'] through the native FileStorage writer
 * and PlayerSave.Companion.load reader. Not a production layout, not a Player.copy, SaveQueue or timer claim.
 */
public final class GraveCodecHelper {
    static final int REFUSED = 2;
    static final int MAX_GRAVES = 64;
    static final int MAX_PILES = 256;
    static final int MAX_TILE = 16383;
    static final int MAX_LEVEL = 3;
    static final String KEY = "grave_lab_state";
    static final String CARRIER = "gravelab";
    static final long FILE_LIMIT = 1L << 20;
    static final Pattern ID = Pattern.compile("[a-z0-9][a-z0-9_-]{0,31}");
    /** Fixture subset only: not proven coverage for production account naming. */
    static final Pattern ACCOUNT = Pattern.compile("[a-z][a-z0-9]{0,11}");
    static final Pattern KIND = Pattern.compile("[a-z][a-z0-9_]{0,63}");
    static final Pattern ITEM = Pattern.compile("[a-z][a-z0-9_]{0,63}");
    static final Set<String> ROOT_KEYS = Set.of("version", "graves", "piles", "latest");
    static final Set<String> GRAVE_KEYS = Set.of("id", "account", "kind", "x", "y", "level", "remaining_seconds", "blessed");
    static final Set<String> PILE_KEYS = Set.of("id", "source_account", "visible_owner", "item", "amount", "charges",
        "x", "y", "level", "reveal_ticks", "disappear_ticks");

    /** remaining_seconds is native grave_timer seconds. Counters accept -1 as their only sentinel below zero. */
    public record Grave(String id, String account, String kind, int x, int y, int level, int remainingSeconds, boolean blessed) {
        public Grave {
            id = safeId(id, "grave id");
            account = safeAccount(account, "grave account");
            kind = text(kind, KIND, "grave kind");
            tile(x, y, level);
            require(remainingSeconds >= 0, "grave remaining_seconds below 0");
        }
    }

    /** Piles are independent records with no grave link. An empty visibleOwner means public. */
    public record Pile(String id, String sourceAccount, String visibleOwner, String item, int amount, int charges,
                       int x, int y, int level, int revealTicks, int disappearTicks) {
        public Pile {
            id = safeId(id, "pile id");
            sourceAccount = safeAccount(sourceAccount, "source_account");
            require(visibleOwner != null, "visible_owner is null");
            require(visibleOwner.isEmpty() || ACCOUNT.matcher(visibleOwner).matches(), "visible_owner is not an account");
            item = text(item, ITEM, "item");
            require(amount >= 1, "amount below 1");
            require(charges >= 0, "charges below 0");
            tile(x, y, level);
            counter(revealTicks, "reveal_ticks");
            counter(disappearTicks, "disappear_ticks");
            if (visibleOwner.isEmpty()) {
                require(revealTicks <= 0, "public pile must not be revealed");
            } else {
                require(visibleOwner.equals(sourceAccount), "private visible_owner must equal source_account");
                require(revealTicks == -1 || revealTicks > 0, "private reveal_ticks must be positive or -1");
            }
        }
    }

    /** latest maps a canonical account to the grave it owns. Map keys are unique by construction. */
    public record Snapshot(int version, List<Grave> graves, List<Pile> piles, Map<String, String> latest) {
        public Snapshot {
            require(version == 1, "unsupported version " + version);
            graves = copy(graves, MAX_GRAVES, "graves");
            piles = copy(piles, MAX_PILES, "piles");
            require(latest != null && latest.size() <= MAX_GRAVES, "latest is null or oversize");
            Map<String, String> copied = new LinkedHashMap<>();
            for (Map.Entry<String, String> entry : latest.entrySet()) {
                require(entry.getValue() != null, "latest holds a null grave id");
                copied.put(safeAccount(entry.getKey(), "latest account"), entry.getValue());
            }
            latest = Map.copyOf(copied);
            Set<String> graveIds = new HashSet<>();
            Map<String, Grave> byId = new HashMap<>();
            for (Grave grave : graves) {
                require(graveIds.add(grave.id()), "duplicate grave id " + grave.id());
                byId.put(grave.id(), grave);
            }
            Set<String> pileIds = new HashSet<>();
            for (Pile pile : piles) require(pileIds.add(pile.id()), "duplicate pile id " + pile.id());
            for (Map.Entry<String, String> entry : latest.entrySet()) {
                Grave grave = byId.get(entry.getValue());
                require(grave != null && grave.account().equals(entry.getKey()), "latest must name a grave of the same account");
            }
        }
    }

    static final class Refusal extends RuntimeException { Refusal(String message) { super(message); } }

    /** Supplied fixture, not an earned or native death snapshot. Grave timers and pile ticks are distinct counters. */
    static final Snapshot FIXTURE = new Snapshot(1,
        List.of(new Grave("g1", "alpha", "memorial_plaque", 3235, 3220, 0, 300, false),
                new Grave("g2", "alpha", "memorial_plaque", 3235, 3220, 0, 180, true),
                new Grave("g3", "beta", "memorial_plaque", 3240, 3220, 0, 120, false)),
        List.of(new Pile("p1", "alpha", "alpha", "coins", 125, 0, 3235, 3220, 0, 300, 60),
                new Pile("p2", "alpha", "alpha", "chaotic_rapier", 1, 12345, 3235, 3220, 0, 250, 60),
                new Pile("p3", "beta", "", "logs", 2, 0, 3240, 3220, 0, 0, 40)),
        Map.of("alpha", "g2", "beta", "g3"));
    public static void main(String[] args) {
        try {
            System.err.println("PROBE_PID " + ProcessHandle.current().pid());
            require(args.length >= 1, "usage: write ROOT | read ROOT | checks");
            switch (args[0]) {
                case "write" -> write(rootArg(args));
                case "read" -> System.out.println(read(rootArg(args)));
                case "checks" -> System.out.println(checks());
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

    // ---- native fixture write and read ----

    static Path rootArg(String[] args) {
        require(args.length == 2, args[0] + " takes ROOT");
        return Paths.get(args[1]).toAbsolutePath();
    }

    static void write(Path root) throws Exception {
        requireNoLinkedAncestors(root);
        require(!Files.exists(root, LinkOption.NOFOLLOW_LINKS), "fixture root already exists");
        Files.createDirectory(root);
        for (String directory : List.of("saves", "sources")) Files.createDirectory(root.resolve(directory));
        Path source = root.resolve("sources").resolve(CARRIER + ".toml");
        Files.write(source, carrierToml().getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        PlayerSave save = PlayerSave.Companion.load(source.toFile());
        save.getVariables().put(KEY, encode(FIXTURE));
        new FileStorage(root.resolve("saves").toFile()).save(List.of(save));
        System.out.println("WROTE " + KEY);
    }

    static String read(Path root) throws Exception {
        requireNoLinkedAncestors(root);
        Path file = root.resolve("saves").resolve(CARRIER + ".toml");
        readRegular(file, FILE_LIMIT);
        PlayerSave save = PlayerSave.Companion.load(file.toFile());
        require(CARRIER.equals(save.getName()), "carrier name differs from its file");
        for (Item[] inventory : save.getInventories().values()) for (Item slot : inventory) {
            require(slot == null || slot.getId() == null || slot.getId().isEmpty(), "native inventory is not empty");
        }
        require(save.getVariables().keySet().equals(Set.of(KEY)), "variable keys differ: " + save.getVariables().keySet());
        Object raw = save.getVariables().get(KEY);
        require(raw != null, KEY + " is missing; refusing to default");
        return json(row("mode", "read", "native_loaded_accounts", 1, "inventories_empty", true,
            "snapshot", encode(decode(raw))));
    }

    static String carrierToml() {
        String zeroes = String.join(",", Collections.nCopies(25, "0"));
        String levels = String.join(",", Collections.nCopies(25, "1"));
        String slots = String.join(", ", Collections.nCopies(28, "{}"));
        return "accountName = \"" + CARRIER + "\"\npasswordHash = \"fixture-only\"\n"
            + "experience = [" + zeroes + "]\nlevels = [" + levels + "]\nlooks = [0,0,0,0,0,0,0]\ncolours = [0,0,0,0,0]\n"
            + "[tile]\nx = 3232\ny = 3232\n"
            + "[variables]\n"
            + "[inventories]\n"
            + "inventory = [" + slots + "]\n"
            + "bank = [" + slots + "]\n";
    }

    // ---- codec ----

    /** Deep-unmodifiable canonical encoding. Callers never receive a mutable nested container. */
    static Map<String, Object> encode(Snapshot snapshot) {
        require(snapshot != null, "snapshot is null");
        List<Object> graves = new ArrayList<>();
        for (Grave g : snapshot.graves()) {
            graves.add(row("id", g.id(), "account", g.account(), "kind", g.kind(), "x", g.x(), "y", g.y(),
                "level", g.level(), "remaining_seconds", g.remainingSeconds(), "blessed", g.blessed()));
        }
        List<Object> piles = new ArrayList<>();
        for (Pile p : snapshot.piles()) {
            piles.add(row("id", p.id(), "source_account", p.sourceAccount(), "visible_owner", p.visibleOwner(),
                "item", p.item(), "amount", p.amount(), "charges", p.charges(), "x", p.x(), "y", p.y(), "level", p.level(),
                "reveal_ticks", p.revealTicks(), "disappear_ticks", p.disappearTicks()));
        }
        return row("version", snapshot.version(), "graves", Collections.unmodifiableList(graves),
            "piles", Collections.unmodifiableList(piles), "latest", Collections.unmodifiableMap(new TreeMap<>(snapshot.latest())));
    }

    /** Ordered, unmodifiable key/value row; keys and values are supplied in pairs. */
    static Map<String, Object> row(Object... pairs) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int index = 0; index < pairs.length; index += 2) out.put((String) pairs[index], pairs[index + 1]);
        return Collections.unmodifiableMap(out);
    }

    /** Strict decode of a native value. Every refusal is a named Refusal; no field is defaulted. */
    static Snapshot decode(Object raw) {
        Map<?, ?> root = fields(raw, ROOT_KEYS, "root");
        int version = number(root.get("version"), 1, 1, "version");
        List<Grave> graves = new ArrayList<>();
        for (Object item : list(root.get("graves"), MAX_GRAVES, "graves")) {
            Map<?, ?> m = fields(item, GRAVE_KEYS, "grave");
            graves.add(new Grave(rawText(m.get("id"), "grave id"), rawText(m.get("account"), "grave account"),
                rawText(m.get("kind"), "grave kind"), number(m.get("x"), 0, MAX_TILE, "x"),
                number(m.get("y"), 0, MAX_TILE, "y"), number(m.get("level"), 0, MAX_LEVEL, "level"),
                number(m.get("remaining_seconds"), 0, Integer.MAX_VALUE, "remaining_seconds"),
                bool(m.get("blessed"))));
        }
        List<Pile> piles = new ArrayList<>();
        for (Object item : list(root.get("piles"), MAX_PILES, "piles")) {
            Map<?, ?> m = fields(item, PILE_KEYS, "pile");
            piles.add(new Pile(rawText(m.get("id"), "pile id"), rawText(m.get("source_account"), "source_account"),
                rawText(m.get("visible_owner"), "visible_owner"), rawText(m.get("item"), "item"),
                number(m.get("amount"), 1, Integer.MAX_VALUE, "amount"), number(m.get("charges"), 0, Integer.MAX_VALUE, "charges"),
                number(m.get("x"), 0, MAX_TILE, "x"), number(m.get("y"), 0, MAX_TILE, "y"),
                number(m.get("level"), 0, MAX_LEVEL, "level"),
                number(m.get("reveal_ticks"), -1, Integer.MAX_VALUE, "reveal_ticks"),
                number(m.get("disappear_ticks"), -1, Integer.MAX_VALUE, "disappear_ticks")));
        }
        Map<?, ?> latest = mapOf(root.get("latest"), "latest");
        Map<String, String> owned = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : latest.entrySet()) {
            owned.put(rawText(entry.getKey(), "latest account"), rawText(entry.getValue(), "latest grave id"));
        }
        return new Snapshot(version, graves, piles, owned);
    }


    static String checks() throws Exception {
        Map<String, String> out = new TreeMap<>();
        probe(out, "valid_fixture_decodes_equal", () -> decode(raw()).equals(FIXTURE) ? "ACCEPTED_EQUAL" : "MISMATCH");
        probe(out, "private_reveal_minus_one_accepted", () -> edited(r -> pile(r, 0).put("reveal_ticks", -1)));
        probe(out, "amount_int_max_accepted", () -> edited(r -> pile(r, 0).put("amount", Integer.MAX_VALUE)));
        probe(out, "item_with_digits_accepted", () -> edited(r -> pile(r, 0).put("item", "rune2_bar")));
        probe(out, "kind_with_digits_accepted", () -> edited(r -> grave(r, 0).put("kind", "plaque2")));
        probe(out, "negative_grave_seconds_refused", () -> edited(r -> grave(r, 2).put("remaining_seconds", -1)));
        probe(out, "latest_oversize_refused", () -> edited(r -> {
            Map<String, Object> many = new LinkedHashMap<>();
            for (int i = 0; i <= MAX_GRAVES; i++) many.put("a" + i, "g2");
            r.put("latest", many);
        }));
        probe(out, "null_snapshot_refused", () -> { decode(null); return "ACCEPTED"; });
        probe(out, "non_map_root_refused", () -> { decode("root"); return "ACCEPTED"; });
        probe(out, "encode_null_refused", () -> { encode(null); return "ACCEPTED"; });
        probe(out, "unsupported_version_refused", () -> edited(r -> r.put("version", 2)));
        probe(out, "version_string_refused", () -> edited(r -> r.put("version", "1")));
        probe(out, "missing_latest_refused", () -> edited(r -> r.remove("latest")));
        probe(out, "unknown_root_key_refused", () -> edited(r -> r.put("extra", 1)));
        probe(out, "unknown_grave_field_refused", () -> edited(r -> grave(r, 0).put("extra", 1)));
        probe(out, "missing_pile_field_refused", () -> edited(r -> pile(r, 0).remove("amount")));
        probe(out, "bool_as_number_refused", () -> edited(r -> grave(r, 0).put("x", Boolean.TRUE)));
        probe(out, "double_number_refused", () -> edited(r -> grave(r, 0).put("remaining_seconds", 300.0)));
        probe(out, "string_number_refused", () -> edited(r -> grave(r, 0).put("y", "3220")));
        probe(out, "amount_zero_refused", () -> edited(r -> pile(r, 0).put("amount", 0)));
        probe(out, "amount_overflow_refused", () -> edited(r -> pile(r, 0).put("amount", 2147483648L)));
        probe(out, "negative_charges_refused", () -> edited(r -> pile(r, 1).put("charges", -1)));
        probe(out, "counter_below_minus_one_refused", () -> edited(r -> grave(r, 0).put("remaining_seconds", -2)));
        probe(out, "tile_x_out_of_range_refused", () -> edited(r -> grave(r, 0).put("x", 16384)));
        probe(out, "negative_tile_refused", () -> edited(r -> pile(r, 0).put("y", -1)));
        probe(out, "level_out_of_range_refused", () -> edited(r -> grave(r, 0).put("level", 4)));
        probe(out, "uppercase_grave_id_refused", () -> edited(r -> grave(r, 0).put("id", "G1")));
        probe(out, "oversize_grave_id_refused", () -> edited(r -> grave(r, 0).put("id", "g" + "x".repeat(32))));
        probe(out, "duplicate_grave_id_refused", () -> edited(r -> grave(r, 1).put("id", "g1")));
        probe(out, "duplicate_pile_id_refused", () -> edited(r -> pile(r, 1).put("id", "p1")));
        probe(out, "unsafe_kind_refused", () -> edited(r -> grave(r, 0).put("kind", "Memorial Plaque")));
        probe(out, "unsafe_item_refused", () -> edited(r -> pile(r, 0).put("item", "coins!")));
        probe(out, "null_visible_owner_refused", () -> edited(r -> pile(r, 0).put("visible_owner", null)));
        probe(out, "private_owner_mismatch_refused", () -> edited(r -> pile(r, 1).put("visible_owner", "beta")));
        probe(out, "public_with_reveal_refused", () -> edited(r -> pile(r, 2).put("reveal_ticks", 5)));
        probe(out, "private_reveal_zero_refused", () -> edited(r -> pile(r, 0).put("reveal_ticks", 0)));
        probe(out, "latest_missing_grave_refused", () -> edited(r -> latest(r).put("alpha", "gZ")));
        probe(out, "latest_wrong_owner_refused", () -> edited(r -> latest(r).put("beta", "g2")));
        probe(out, "latest_uppercase_account_refused", () -> edited(r -> latest(r).put("Alpha", "g2")));
        probe(out, "latest_null_value_refused", () -> edited(r -> latest(r).put("beta", null)));
        probe(out, "graves_map_container_refused", () -> edited(r -> r.put("graves", new LinkedHashMap<>())));
        probe(out, "piles_string_container_refused", () -> edited(r -> r.put("piles", "p1")));
        probe(out, "null_inside_piles_refused", () -> edited(r -> list(r, "piles").add(null)));
        probe(out, "graves_oversize_refused", () -> edited(r -> r.put("graves", oversize(grave(r, 0), MAX_GRAVES + 1))));
        probe(out, "piles_oversize_refused", () -> edited(r -> r.put("piles", oversize(pile(r, 0), MAX_PILES + 1))));
        probe(out, "encoded_root_put_immutable", () -> { encode(FIXTURE).put("x", 1); return "ACCEPTED"; });
        probe(out, "encoded_grave_list_add_immutable", () -> { list(encode(FIXTURE), "graves").add(Map.of()); return "ACCEPTED"; });
        probe(out, "encoded_grave_map_put_immutable", () -> { grave(encode(FIXTURE), 0).put("x", 1); return "ACCEPTED"; });
        probe(out, "encoded_latest_put_immutable", () -> { latest(encode(FIXTURE)).put("alpha", "g1"); return "ACCEPTED"; });
        probe(out, "decoded_graves_add_immutable", () -> { decode(raw()).graves().add(null); return "ACCEPTED"; });
        probe(out, "caller_input_mutation_after_decode_unchanged", () -> {
            Map<String, Object> raw = raw();
            Snapshot snapshot = decode(raw);
            String before = json(encode(snapshot));
            grave(raw, 0).put("remaining_seconds", 1);
            list(raw, "graves").clear();
            latest(raw).put("alpha", "g1");
            return before.equals(json(encode(snapshot))) ? "UNCHANGED" : "CHANGED";
        });
        probe(out, "caller_record_list_mutation_after_construct_unchanged", () -> {
            List<Grave> mine = new ArrayList<>(FIXTURE.graves());
            Snapshot snapshot = new Snapshot(1, mine, FIXTURE.piles(), FIXTURE.latest());
            mine.clear();
            return snapshot.graves().size() == 3 ? "UNCHANGED" : "CHANGED";
        });
        probe(out, "replacement_snapshot_leaves_checkpoint_unchanged", () -> {
            Map<String, Object> checkpoint = encode(FIXTURE);
            String before = json(checkpoint);
            encode(new Snapshot(1, List.of(FIXTURE.graves().get(0)), List.of(), Map.of("alpha", "g1")));
            return before.equals(json(checkpoint)) ? "UNCHANGED" : "CHANGED";
        });
        return json(row("mode", "checks", "outcomes", out));
    }

    static void probe(Map<String, String> out, String name, Callable<String> probe) throws Exception {
        try {
            out.put(name, probe.call());
        } catch (Refusal refusal) {
            out.put(name, "REFUSED");
        } catch (UnsupportedOperationException frozen) {
            out.put(name, "IMMUTABLE_REFUSED");
        }
    }

    /** Decodes a fresh valid raw map after one caller edit. Any harness bug propagates instead of counting as a refusal. */
    static String edited(Consumer<Map<String, Object>> edit) {
        Map<String, Object> raw = raw();
        edit.accept(raw);
        decode(raw);
        return "ACCEPTED";
    }

    static Map<String, Object> raw() {
        return castMap(thaw(encode(FIXTURE)));
    }


    /** Mutable deep copy: the caller-side shape a hostile or careless caller might hand to decode. */
    static Object thaw(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<Object, Object> copy = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) copy.put(entry.getKey(), thaw(entry.getValue()));
            return copy;
        }
        if (value instanceof List<?> list) {
            List<Object> copy = new ArrayList<>();
            for (Object item : list) copy.add(thaw(item));
            return copy;
        }
        return value;
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> castMap(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    static List<Object> list(Map<String, Object> raw, String key) {
        return (List<Object>) raw.get(key);
    }

    static Map<String, Object> latest(Map<String, Object> raw) {
        return castMap(raw.get("latest"));
    }

    /** Copies of one valid record with unique ids, used only to exceed a collection bound. */
    static List<Object> oversize(Map<String, Object> sample, int count) {
        List<Object> many = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            Map<String, Object> copy = new LinkedHashMap<>(sample);
            copy.put("id", "x" + i);
            many.add(copy);
        }
        return many;
    }

    static Map<String, Object> grave(Map<String, Object> raw, int index) {
        return castMap(list(raw, "graves").get(index));
    }

    static Map<String, Object> pile(Map<String, Object> raw, int index) {
        return castMap(list(raw, "piles").get(index));
    }

    static Map<?, ?> fields(Object value, Set<String> keys, String what) {
        require(value instanceof Map<?, ?>, what + " is not a map");
        Map<?, ?> map = (Map<?, ?>) value;
        for (Object key : map.keySet()) require(key instanceof String, what + " has a non-string key");
        require(map.keySet().equals(keys), what + " fields differ: " + map.keySet());
        return map;
    }

    static Map<?, ?> mapOf(Object value, String what) {
        require(value instanceof Map<?, ?>, what + " is not a map");
        return (Map<?, ?>) value;
    }

    static List<?> list(Object value, int max, String what) {
        require(value instanceof List<?>, what + " is not a list");
        require(((List<?>) value).size() <= max, what + " exceeds " + max);
        return (List<?>) value;
    }

    static int number(Object value, int min, int max, String what) {
        require(value instanceof Integer || value instanceof Long, what + " is not an integer");
        long number = ((Number) value).longValue();
        require(number >= min && number <= max, what + " out of range");
        return (int) number;
    }

    static boolean bool(Object value) {
        require(value instanceof Boolean, "blessed is not a boolean");
        return (Boolean) value;
    }

    static String rawText(Object value, String what) {
        require(value instanceof String, what + " is not a string");
        return (String) value;
    }

    static String safeId(String value, String what) {
        return text(value, ID, what);
    }

    static String safeAccount(String value, String what) {
        return text(value, ACCOUNT, what);
    }

    static String text(String value, Pattern pattern, String what) {
        require(value != null && pattern.matcher(value).matches(), what + " is not a bounded safe value");
        return value;
    }

    static void tile(int x, int y, int level) {
        require(x >= 0 && x <= MAX_TILE && y >= 0 && y <= MAX_TILE && level >= 0 && level <= MAX_LEVEL, "tile out of bounds");
    }

    static void counter(int value, String what) {
        require(value >= -1, what + " below -1");
    }

    static <T> List<T> copy(List<T> items, int max, String what) {
        require(items != null && items.size() <= max, what + " is null or oversize");
        for (T item : items) require(item != null, what + " holds a null");
        return List.copyOf(items);
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
                quote(out, (String) key);
                out.append(':');
                append(out, item);
            });
            out.append('}');
        } else if (value instanceof List<?> list) {
            out.append('[');
            list.forEach(item -> {
                if (out.charAt(out.length() - 1) != '[') out.append(',');
                append(out, item);
            });
            out.append(']');
        } else if (value instanceof String text) {
            quote(out, text);
        } else if (value instanceof Integer || value instanceof Long || value instanceof Boolean) {
            out.append(value);
        } else {
            throw new IllegalStateException("harness cannot serialize " + value);
        }
    }

    static void quote(StringBuilder out, String text) {
        out.append('"');
        for (char c : text.toCharArray()) {
            if (c == '"' || c == '\\') out.append('\\');
            out.append(c);
        }
        out.append('"');
    }

    static void readRegular(Path path, long limit) throws IOException {
        requireNoLinkedAncestors(path.toAbsolutePath());
        require(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS), "not a regular account file: " + path.getFileName());
        require(Files.size(path) <= limit, "account file exceeds bound: " + path.getFileName());
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
