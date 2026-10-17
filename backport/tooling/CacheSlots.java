import java.io.RandomAccessFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.TreeSet;
import world.gregs.voidps.cache.Cache;
import world.gregs.voidps.cache.FileCache;

/** Read reference-table occupancy, including unnamed slots; never decode or write assets. */
public final class CacheSlots {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("cache directory and output required");
        Path directory = Path.of(args[0]);
        Path main = directory.resolve("main_file_cache.dat2");
        Path table = directory.resolve("main_file_cache.idx255");
        // Own the checksum descriptor too: native FileCache.close only closes main/index files.
        try (RandomAccessFile data = new RandomAccessFile(main.toFile(), "r");
             RandomAccessFile reference = new RandomAccessFile(table.toFile(), "r")) {
            if (reference.length() % 6 != 0) throw new IllegalArgumentException("Invalid index255 size");
            Cache cache = FileCache.Companion.load(directory.toString(), main.toFile(), data,
                table.toFile(), reference, Math.toIntExact(reference.length() / 6), null, null, 1.0);
            try {
                String[] kinds = {"item", "npc", "object", "sequence"};
                int[] indexes = {19, 18, 16, 20};
                int[] shifts = {8, 7, 8, 7};
                StringBuilder out = new StringBuilder("{\"schema_version\":1,\"namespaces\":[");
                for (int i = 0; i < kinds.length; i++) {
                    if (i != 0) out.append(',');
                    TreeSet<Integer> ids = new TreeSet<>();
                    for (int archive : cache.archives(indexes[i])) {
                        if (archive < 0 || archive > (Integer.MAX_VALUE >> shifts[i]))
                            throw new IllegalArgumentException("Archive ID overflow");
                        for (int file : cache.files(indexes[i], archive)) {
                            if (file < 0 || file >= (1 << shifts[i]))
                                throw new IllegalArgumentException("File ID outside native split");
                            if (!ids.add((archive << shifts[i]) | file))
                                throw new IllegalArgumentException("Duplicate definition slot");
                        }
                    }
                    if (ids.isEmpty()) throw new IllegalArgumentException("Missing namespace " + kinds[i]);
                    out.append("{\"kind\":\"").append(kinds[i]).append("\",\"index\":")
                       .append(indexes[i]).append(",\"archive_shift\":").append(shifts[i])
                       .append(",\"occupied_ids\":").append(ids).append('}');
                }
                Files.writeString(Path.of(args[1]), out.append("]}\n").toString(), StandardOpenOption.CREATE_NEW);
            } finally {
                cache.close();
            }
        }
    }
}
