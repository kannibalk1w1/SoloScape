import com.displee.cache.CacheLibrary;
import com.displee.cache.index.Index;
import com.displee.cache.index.archive.Archive;
import java.io.InputStream;
import java.io.RandomAccessFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.ArrayList;
import java.util.zip.CRC32;
import java.util.List;
import world.gregs.voidps.buffer.read.ArrayReader;
import world.gregs.voidps.buffer.write.ArrayWriter;
import world.gregs.voidps.cache.Cache;
import world.gregs.voidps.cache.CacheDelegate;
import world.gregs.voidps.cache.FileCache;
import world.gregs.voidps.cache.definition.data.ItemDefinition;
import world.gregs.voidps.cache.definition.data.ItemDefinitionFull;
import world.gregs.voidps.cache.definition.decoder.ItemDecoder;
import world.gregs.voidps.cache.definition.decoder.ItemDecoderFull;
import world.gregs.voidps.cache.definition.encoder.ItemEncoder;
import world.gregs.voidps.cache.secure.CRC;
import world.gregs.voidps.cache.secure.Whirlpool;

/**
 * One fixed original Lab token on a disposable cache copy, with whole-container integrity checks.
 * Write:  LabTokenCache <cache-copy> <new-report> <lab-root>
 * Verify: LabTokenCache --verify <cache-copy> <new-report> <lab-root>   (read-only; no decode before the CRC gate)
 * Not a general allocator or backport API.
 */
public final class LabTokenCache {
    static final int INDEX = 19;
    static final int REFERENCE_INDEX = 255;
    static final int ARCHIVE = 78;
    static final int FILE = 211;
    static final int TARGET = 20179;
    static final String NAME = "SoloScape Lab token";
    static final int COST = 37;
    static final int[] ALLOWED_OPCODES = {2, 11, 12};

    /** Original definition bytes: name, stackable and cost only; no note/lend/stack/wearable/model links. */
    static byte[] encode() {
        ItemDefinitionFull original = new ItemDefinitionFull();
        original.setId(TARGET);
        original.setName(NAME);
        original.setStackable(1);
        original.setCost(COST);
        original.setNoteId(-1);
        ArrayWriter out = new ArrayWriter();
        new ItemEncoder().encode(out, original);
        return Arrays.copyOf(out.array(), out.position());
    }

    /** Strict opcode walk for the subset this token may use; returns the opcode sequence. */
    static int[] opcodes(byte[] bytes) {
        List<Integer> seen = new ArrayList<>();
        Set<Integer> allowed = new HashSet<>();
        for (int o : ALLOWED_OPCODES) allowed.add(o);
        int p = 0;
        while (p < bytes.length) {
            int opcode = bytes[p++] & 255;
            seen.add(opcode);
            if (opcode == 0) {
                if (p != bytes.length) throw new IllegalStateException("Trailing bytes after terminator");
                break;
            }
            if (!allowed.contains(opcode)) throw new IllegalStateException("Opcode outside token subset: " + opcode);
            if (opcode == 2) {
                while (p < bytes.length && bytes[p] != 0) p++;
                if (p == bytes.length) throw new IllegalStateException("Unterminated string");
                p++;
            } else if (opcode == 12) {
                p += 4;
            }
            if (p > bytes.length) throw new IllegalStateException("Truncated value");
        }
        if (seen.isEmpty() || seen.get(seen.size() - 1) != 0) throw new IllegalStateException("Missing terminator");
        int[] result = new int[seen.size()];
        for (int i = 0; i < result.length; i++) result[i] = seen.get(i);
        return result;
    }

    static void require(boolean value, String message) {
        if (!value) throw new IllegalStateException(message);
    }

    static String hex(byte[] data) {
        StringBuilder out = new StringBuilder();
        for (byte b : data) out.append(String.format("%02x", b & 255));
        return out.toString();
    }

    static String sha(byte[] data) throws Exception {
        return hex(MessageDigest.getInstance("SHA-256").digest(data));
    }

    /** Streams a file through SHA-256 without loading it whole. */
    static String shaFile(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[1 << 16];
        try (InputStream in = Files.newInputStream(path)) {
            int read;
            while ((read = in.read(buffer)) != -1) digest.update(buffer, 0, read);
        }
        return hex(digest.digest());
    }

    static String whirlpool(byte[] data) {
        Whirlpool whirlpool = new Whirlpool();
        whirlpool.reset();
        whirlpool.add(data, 0, data.length);
        byte[] out = new byte[64];
        whirlpool.finalize(out, 0);
        return hex(out);
    }

    static int crc(byte[] data) {
        return new CRC().calculate(data, 0, data.length);
    }

    /** Displee Index.write: archive CRC and Whirlpool cover compressed bytes minus the 2-byte trailer. */
    static byte[] archiveBody(byte[] container) {
        require(container.length >= 2, "Container shorter than its trailer");
        return Arrays.copyOf(container, container.length - 2);
    }

    /** Trailer short, which Displee writes from the archive revision. */
    static int trailerRevision(byte[] container) {
        return ((container[container.length - 2] & 255) << 8) | (container[container.length - 1] & 255);
    }

    /** Decodes with the three native readers; each must consume the whole stream and agree on the token fields. */
    static String verifyDecoders(byte[] bytes) throws Exception {
        ItemDefinitionFull full = new ItemDefinitionFull();
        ArrayReader fullInput = new ArrayReader(bytes);
        new ItemDecoderFull().readLoop(full, fullInput);
        ItemDefinition light = new ItemDefinition();
        ArrayReader lightInput = new ArrayReader(bytes);
        new ItemDecoder().readLoop(light, lightInput);
        ObjType client = new ObjType();
        Packet packet = new Packet(bytes);
        client.decode(768, packet);
        require(fullInput.position() == bytes.length && lightInput.position() == bytes.length && packet.pos == bytes.length,
            "A native decoder left bytes unread");
        require(NAME.equals(full.getName()) && NAME.equals(light.getName()) && NAME.equals(client.name), "Name disagreement");
        require(full.getCost() == COST && light.getCost() == COST && client.cost == COST, "Cost disagreement");
        require(full.getStackable() == 1 && light.getStackable() == 1 && client.stackable == 1, "Stackability disagreement");
        require(full.getNoteId() == -1 && light.getNoteId() == -1 && client.certlink == -1, "Unexpected note link");
        return "{\"server_full_cost\":" + full.getCost() + ",\"server_light_cost\":" + light.getCost()
            + ",\"client_cost\":" + client.cost + ",\"consumed_bytes\":" + bytes.length + "}";
    }

    /** Hashes every decoded item entry in index 19 through the native FileCache reader. */
    static TreeMap<Integer, String> items(Cache cache) throws Exception {
        TreeMap<Integer, String> hashes = new TreeMap<>();
        for (int archive : cache.archives(INDEX)) {
            for (int file : cache.files(INDEX, archive)) {
                byte[] data = cache.data(INDEX, archive, file, null);
                require(data != null, "Unreadable item entry " + archive + "/" + file);
                hashes.put((archive << 8) | file, sha(data));
            }
        }
        return hashes;
    }

    static String namespaceDigest(Map<Integer, String> hashes) throws Exception {
        StringBuilder lines = new StringBuilder();
        for (Map.Entry<Integer, String> e : hashes.entrySet()) lines.append(e.getKey()).append(':').append(e.getValue()).append('\n');
        return sha(lines.toString().getBytes("UTF-8"));
    }

    /** Native read-only FileCache; the caller closes the cache and then the reference handle. */
    static Cache openRead(Path directory, RandomAccessFile reference) throws Exception {
        Path main = directory.resolve("main_file_cache.dat2");
        Path table = directory.resolve("main_file_cache.idx255");
        RandomAccessFile data = new RandomAccessFile(main.toFile(), "r");
        return FileCache.Companion.load(directory.toString(), main.toFile(), data,
            table.toFile(), reference, Math.toIntExact(reference.length() / 6), null, null, 1.0);
    }

    static Map<String, String> rawFileHashes(Path directory) throws Exception {
        TreeMap<String, String> result = new TreeMap<>();
        List<Path> paths = new ArrayList<>();
        try (java.util.stream.Stream<Path> files = Files.list(directory)) {
            files.filter(p -> p.getFileName().toString().matches("main_file_cache\\.(dat2|idx[0-9]+)")).sorted().forEach(paths::add);
        }
        for (Path p : paths) {
            require(!Files.isSymbolicLink(p) && Files.isRegularFile(p), "Cache entries must be regular files");
            result.put(p.getFileName().toString(), shaFile(p));
        }
        return result;
    }

    static Path guardedCopy(String argument, Path lab) throws Exception {
        Path cacheDir = Path.of(argument).toAbsolutePath().normalize();
        require(cacheDir.getFileName().toString().equals("cache-copy") && !Files.isSymbolicLink(cacheDir)
            && Files.isDirectory(cacheDir) && cacheDir.toRealPath().equals(cacheDir) && cacheDir.startsWith(lab)
            && lab.relativize(cacheDir).getNameCount() >= 2
            && lab.relativize(cacheDir).getName(0).toString().startsWith("lab-token-"),
            "Writes require an ordinary cache-copy inside this checkout lab");
        try (java.util.stream.Stream<Path> entries = Files.list(cacheDir)) {
            entries.forEach(p -> require(!Files.isSymbolicLink(p) && Files.isRegularFile(p), "Cache input must be an ordinary file"));
        }
        return cacheDir;
    }

    /** Whole-container snapshot from fresh native and Displee readers. Items are decoded only when asked. */
    static final class Snapshot {
        final Map<String, String> rawFiles = new TreeMap<>();
        final Map<Integer, String> referenceContainer = new TreeMap<>();   // index -> sha(sector(255,index))
        final Map<Integer, Integer> referenceCrc = new TreeMap<>();        // index -> CRC(sector(255,index))
        final Map<Integer, Integer> indexStoredCrc = new TreeMap<>();      // index -> Displee Index.crc
        final Map<String, String> archiveContainer = new TreeMap<>();     // "i/a" -> sha(sector(i,a))
        final Map<String, Integer> archiveNativeCrc = new TreeMap<>();    // "i/a" -> native CRC
        final Map<String, Integer> archiveStoredCrc = new TreeMap<>();    // "i/a" -> Displee stored CRC
        final Map<String, Integer> archiveStoredRevision = new TreeMap<>();
        final Map<String, Integer> archiveTrailerRevision = new TreeMap<>();
        final Map<String, String> archiveNativeWhirlpool = new TreeMap<>();
        final Map<String, String> archiveStoredWhirlpool = new TreeMap<>();
        Map<Integer, String> items;
        int archivesWhirlpoolCompared;
    }

    /** Reads every reference container and archive container via FileCache.sector; compares with Displee stored tables. */
    static Snapshot capture(Path dir, boolean withItems) throws Exception {
        Snapshot s = new Snapshot();
        s.rawFiles.putAll(rawFileHashes(dir));
        CacheLibrary library = new CacheLibrary(dir.toString(), false, null);
        try (RandomAccessFile reference = new RandomAccessFile(dir.resolve("main_file_cache.idx255").toFile(), "r")) {
            Cache cache = openRead(dir, reference);
            try {
                for (int index : cache.indices()) {
                    byte[] ref = cache.sector(REFERENCE_INDEX, index);
                    // An index without a reference container is recorded as absent, not as corruption.
                    s.referenceContainer.put(index, ref == null ? "absent" : sha(ref));
                    if (ref != null) s.referenceCrc.put(index, crc(ref));
                    Index stored = library.index(index);
                    if (stored != null && ref != null) s.indexStoredCrc.put(index, stored.getCrc());
                    require(stored != null || ref == null, "Native/Displee reference membership differs at " + index);
                    if (stored == null) continue;
                    for (int archive : cache.archives(index)) {
                        String key = index + "/" + archive;
                        byte[] container = cache.sector(index, archive);
                        require(container != null, "Missing archive container " + key);
                        s.archiveContainer.put(key, sha(container));
                        s.archiveNativeCrc.put(key, crc(archiveBody(container)));
                        s.archiveTrailerRevision.put(key, trailerRevision(container));
                        Archive row = stored.archive(archive);
                        require(row != null, "Displee table lacks archive " + key);
                        s.archiveStoredCrc.put(key, row.getCrc());
                        s.archiveStoredRevision.put(key, row.getRevision());
                        if (row.getWhirlpool() != null) {
                            s.archiveStoredWhirlpool.put(key, hex(row.getWhirlpool()));
                            s.archiveNativeWhirlpool.put(key, whirlpool(archiveBody(container)));
                            s.archivesWhirlpoolCompared++;
                        }
                    }
                }
                if (withItems) s.items = items(cache);
            } finally {
                cache.close();
            }
        } finally {
            library.close();
        }
        return s;
    }

    /**
     * Target archive gate, scope from Displee Index.write (javap evidence): CRC32 over the compressed container
     * minus its 2-byte trailer, and the trailer short must equal the stored revision. No decode is performed.
     */
    static String gate(Path dir) throws Exception {
        CacheLibrary library = new CacheLibrary(dir.toString(), false, null);
        try (RandomAccessFile reference = new RandomAccessFile(dir.resolve("main_file_cache.idx255").toFile(), "r")) {
            Cache cache = openRead(dir, reference);
            try {
                byte[] container = cache.sector(INDEX, ARCHIVE);
                require(container != null, "Target container is missing");
                Archive row = library.index(INDEX).archive(ARCHIVE);
                require(row != null, "Target is absent from the reference table");
                byte[] body = archiveBody(container);
                int nativeCrc = crc(body);
                CRC32 javaCrc = new CRC32();
                javaCrc.update(body);
                require((int) javaCrc.getValue() == nativeCrc, "Native CRC differs from java.util.zip.CRC32");
                int trailer = trailerRevision(container);
                boolean crcOk = nativeCrc == row.getCrc();
                boolean footerOk = trailer == (row.getRevision() & 0xFFFF);
                boolean whirlpoolOk = row.getWhirlpool() == null || hex(row.getWhirlpool()).equals(whirlpool(body));
                boolean passed = crcOk && footerOk && whirlpoolOk;
                return "{\"target\":\"19/78\",\"container_bytes\":" + container.length + ",\"container_sha256\":\"" + sha(container)
                    + "\",\"body_bytes\":" + body.length + ",\"native_crc32\":" + nativeCrc + ",\"stored_crc32\":" + row.getCrc()
                    + ",\"trailer_revision\":" + trailer + ",\"stored_revision\":" + row.getRevision()
                    + ",\"whirlpool_present\":" + (row.getWhirlpool() != null) + ",\"crc_ok\":" + crcOk
                    + ",\"footer_ok\":" + footerOk + ",\"whirlpool_ok\":" + whirlpoolOk + ",\"gate_passed\":" + passed + "}";
            } finally {
                cache.close();
            }
        } finally {
            library.close();
        }
    }

    static boolean gatePassed(String gateJson) {
        return gateJson.contains("\"gate_passed\":true");
    }

    public static void main(String[] args) throws Exception {
        boolean verify = args.length > 0 && args[0].equals("--verify");
        String[] rest = verify ? Arrays.copyOfRange(args, 1, args.length) : args;
        require(rest.length == 3, "cache-copy directory, new report file and lab root required");
        Path expectedLab = Path.of("").toAbsolutePath().normalize().resolve(".runtime/backport-lab");
        Path lab = Path.of(rest[2]).toAbsolutePath().normalize();
        require(lab.equals(expectedLab) && lab.toRealPath().equals(lab), "Use this checkout ordinary backport lab");
        Path cacheDir = guardedCopy(rest[0], lab);
        Path output = Path.of(rest[1]).toAbsolutePath().normalize();
        require(output.getParent().toRealPath().equals(output.getParent()) && output.startsWith(lab)
            && !output.startsWith(cacheDir) && !Files.exists(output),
            "Report must be new and inside the lab, outside the cache copy");
        require(TARGET == ARCHIVE * 256 + FILE && TARGET < 32768, "Candidate arithmetic or ceiling failed");
        String key = INDEX + "/" + ARCHIVE;

        if (verify) {
            // Gate first: the CRC decision is made before any item decode or whole-cache comparison.
            String gateRow = gate(cacheDir);
            boolean passed = gatePassed(gateRow);
            if (!passed) {
                String refusal = "{\"mode\":\"lab-token-integrity-verify\",\"refused_at\":\"crc-gate\",\"gate\":" + gateRow + ",\"cache_written\":false}";
                Files.writeString(output, refusal + "\n", StandardOpenOption.CREATE_NEW);
                System.out.println(refusal);
                throw new IllegalStateException("CRC gate refused target 19/78 before decode");
            }
            Snapshot s = capture(cacheDir, false);
            int archiveMatches = 0;
            List<String> mismatches = new ArrayList<>();
            for (Map.Entry<String, Integer> e : s.archiveNativeCrc.entrySet()) {
                if (e.getValue().equals(s.archiveStoredCrc.get(e.getKey()))) archiveMatches++;
                else mismatches.add(e.getKey());
            }
            int whirlpoolMatches = 0;
            for (Map.Entry<String, String> e : s.archiveNativeWhirlpool.entrySet()) {
                if (e.getValue().equals(s.archiveStoredWhirlpool.get(e.getKey()))) whirlpoolMatches++;
                else mismatches.add("whirlpool " + e.getKey());
            }
            int footerMatches = 0;
            for (Map.Entry<String, Integer> e : s.archiveTrailerRevision.entrySet()) {
                if (e.getValue() == (s.archiveStoredRevision.get(e.getKey()) & 0xFFFF)) footerMatches++;
                else mismatches.add("footer " + e.getKey());
            }
            int indexMatches = 0;
            for (Map.Entry<Integer, Integer> e : s.referenceCrc.entrySet()) {
                if (e.getValue().equals(s.indexStoredCrc.get(e.getKey()))) indexMatches++;
                else mismatches.add("reference-crc " + e.getKey());
            }
            String report = "{\"mode\":\"lab-token-integrity-verify\",\"gate\":" + gateRow
                + ",\"archives_compared\":" + s.archiveNativeCrc.size() + ",\"archive_crc_matches\":" + archiveMatches
                + ",\"whirlpool_compared\":" + s.archivesWhirlpoolCompared + ",\"whirlpool_matches\":" + whirlpoolMatches
                + ",\"footer_matches\":" + footerMatches + ",\"footer_compared\":" + s.archiveTrailerRevision.size()
                + ",\"reference_full_crc_compared_informational\":" + s.referenceCrc.size()
                + ",\"reference_full_crc_matches_informational\":" + indexMatches
                + ",\"mismatches\":" + quoteList(mismatches) + ",\"cache_written\":false}";
            Files.writeString(output, report + "\n", StandardOpenOption.CREATE_NEW);
            System.out.println(report);
            require(mismatches.isEmpty(), "Whole-cache integrity refused: " + mismatches);
            return;
        }

        byte[] token = encode();
        require(Arrays.equals(opcodes(token), new int[] {2, 11, 12, 0}), "Unexpected token opcode sequence");
        String decoded = verifyDecoders(token);
        require(Arrays.equals(token, encode()), "Encoder not deterministic");

        // Pre-state must pass the gate and must not already contain the candidate.
        String preGate = gate(cacheDir);
        require(gatePassed(preGate), "Baseline copy fails the CRC gate; refusing to write");
        Snapshot pre = capture(cacheDir, true);
        require(!pre.items.containsKey(TARGET), "Candidate item slot is already occupied");

        CacheDelegate writer = new CacheDelegate(cacheDir.toString(), null, null);
        try {
            writer.write(INDEX, ARCHIVE, FILE, token, null);
            require(writer.update(), "Cache update reported failure");
        } finally {
            writer.close();
        }

        // Fresh reopen after the write; metadata is read only through new readers.
        String postGate = gate(cacheDir);
        Snapshot post = capture(cacheDir, true);

        int refSame = 0;
        List<String> refChanged = new ArrayList<>();
        for (Map.Entry<Integer, String> e : pre.referenceContainer.entrySet()) {
            if (e.getValue().equals(post.referenceContainer.get(e.getKey()))) refSame++;
            else refChanged.add(String.valueOf(e.getKey()));
        }
        int archiveSame = 0;
        List<String> archiveChanged = new ArrayList<>();
        for (Map.Entry<String, String> e : pre.archiveContainer.entrySet()) {
            if (e.getValue().equals(post.archiveContainer.get(e.getKey()))) archiveSame++;
            else archiveChanged.add(e.getKey());
        }
        List<String> failures = new ArrayList<>();
        if (!pre.archiveContainer.keySet().equals(post.archiveContainer.keySet())) failures.add("archive-set");
        if (!pre.referenceContainer.keySet().equals(post.referenceContainer.keySet())) failures.add("reference-set");
        if (!pre.rawFiles.keySet().equals(post.rawFiles.keySet())) failures.add("raw-file-set");
        int crcMismatch = 0;
        for (Map.Entry<String, Integer> e : post.archiveNativeCrc.entrySet()) {
            if (!e.getValue().equals(post.archiveStoredCrc.get(e.getKey()))) { crcMismatch++; failures.add("crc " + e.getKey()); }
        }
        int whirlpoolMismatch = 0;
        for (Map.Entry<String, String> e : post.archiveNativeWhirlpool.entrySet()) {
            if (!e.getValue().equals(post.archiveStoredWhirlpool.get(e.getKey()))) { whirlpoolMismatch++; failures.add("whirlpool " + e.getKey()); }
        }
        int footerMismatch = 0;
        for (Map.Entry<String, Integer> e : post.archiveTrailerRevision.entrySet()) {
            if (e.getValue() != (post.archiveStoredRevision.get(e.getKey()) & 0xFFFF)) { footerMismatch++; failures.add("footer " + e.getKey()); }
        }
        int indexCrcMatches = 0;
        for (Map.Entry<Integer, Integer> e : post.referenceCrc.entrySet()) {
            if (e.getValue().equals(post.indexStoredCrc.get(e.getKey()))) indexCrcMatches++;
            else failures.add("reference-crc " + e.getKey());
        }
        int identical = 0;
        for (Map.Entry<Integer, String> e : pre.items.entrySet()) {
            if (e.getValue().equals(post.items.get(e.getKey()))) identical++;
            else failures.add("item " + e.getKey());
        }
        if (!(post.items.size() == pre.items.size() + 1 && post.items.containsKey(TARGET)
            && post.items.get(TARGET).equals(sha(token)))) failures.add("item-set");
        List<String> rawChanged = new ArrayList<>();
        for (String name : pre.rawFiles.keySet()) {
            if (!pre.rawFiles.get(name).equals(post.rawFiles.get(name))) rawChanged.add(name);
        }
        for (String name : refChanged) if (!name.equals(String.valueOf(INDEX))) failures.add("reference " + name);
        for (String name : archiveChanged) if (!name.equals(key)) failures.add("archive " + name);
        if (!gatePassed(postGate)) failures.add("post-gate");
        if (!archiveChanged.equals(java.util.List.of(key))) failures.add("target-not-rewritten-alone");
        if (!refChanged.equals(java.util.List.of(String.valueOf(INDEX)))) failures.add("target-reference-not-rewritten-alone");
        boolean verdict = failures.isEmpty();

        String report = "{\"mode\":\"lab-token-integrity-write\",\"verdict\":" + verdict + ",\"failures\":" + quoteList(failures)
            + ",\"target\":{\"index\":" + INDEX + ",\"archive\":" + ARCHIVE + ",\"file\":" + FILE + ",\"id\":" + TARGET
            + "},\"cost\":" + COST + ",\"opcodes\":[2,11,12,0],\"encoded_bytes\":" + token.length
            + ",\"new_entry_sha256\":\"" + sha(token) + "\",\"decoders\":" + decoded
            + ",\"pre_gate\":" + preGate + ",\"post_gate\":" + postGate
            + ",\"target_revision_before\":" + pre.archiveStoredRevision.get(key)
            + ",\"target_revision_after\":" + post.archiveStoredRevision.get(key)
            + ",\"target_container_before_sha256\":\"" + pre.archiveContainer.get(key)
            + "\",\"target_container_after_sha256\":\"" + post.archiveContainer.get(key)
            + "\",\"reference_container_before_19_sha256\":\"" + pre.referenceContainer.get(INDEX)
            + "\",\"reference_container_after_19_sha256\":\"" + post.referenceContainer.get(INDEX) + "\""
            + ",\"reference_containers_compared\":" + pre.referenceContainer.size() + ",\"reference_containers_identical\":" + refSame
            + ",\"reference_containers_changed\":" + quoteList(refChanged)
            + ",\"reference_full_crc_compared_informational\":" + post.referenceCrc.size() + ",\"reference_full_crc_matches_informational\":" + indexCrcMatches
            + ",\"archive_footer_mismatches_after\":" + footerMismatch
            + ",\"archive_containers_compared\":" + pre.archiveContainer.size() + ",\"archive_containers_identical\":" + archiveSame
            + ",\"archive_containers_changed\":" + quoteList(archiveChanged)
            + ",\"archive_crc_mismatches_after\":" + crcMismatch + ",\"archive_whirlpool_compared\":" + post.archivesWhirlpoolCompared
            + ",\"archive_whirlpool_mismatches_after\":" + whirlpoolMismatch
            + ",\"item_entries_before\":" + pre.items.size() + ",\"item_entries_after\":" + post.items.size()
            + ",\"preexisting_entries_identical\":" + identical
            + ",\"item_namespace_before_sha256\":\"" + namespaceDigest(pre.items)
            + "\",\"item_namespace_after_sha256\":\"" + namespaceDigest(post.items)
            + "\",\"raw_files_changed\":" + quoteList(rawChanged)
            + ",\"cache_written\":true,\"cache_copy_only\":true,\"appearance_proof\":false}";
        Files.writeString(output, report + "\n", StandardOpenOption.CREATE_NEW);
        System.out.println(report);
        require(verdict, "Integrity verdict false: " + failures);
    }

    static String quoteList(List<String> names) {
        StringBuilder out = new StringBuilder("[");
        for (int i = 0; i < names.size(); i++) {
            if (i != 0) out.append(',');
            out.append('"').append(names.get(i)).append('"');
        }
        return out.append(']').toString();
    }
}
