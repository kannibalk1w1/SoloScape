import com.displee.cache.CacheLibrary;
import com.displee.cache.index.Index;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.TreeSet;

/** Optional independent metadata parser. Run ONLY on a disposable cache copy: library opens RW. */
public final class CacheSlotsOracle {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("disposable cache copy and output required");
        Path lab = Path.of(".runtime/backport-lab").toRealPath();
        Path cache = Path.of(args[0]).toRealPath();
        Path requestedOutput = Path.of(args[1]).toAbsolutePath().normalize();
        Path output = requestedOutput.getParent().toRealPath().resolve(requestedOutput.getFileName());
        if (!cache.startsWith(lab) || !cache.getFileName().toString().equals("cache-copy"))
            throw new IllegalArgumentException("Oracle requires a disposable lab cache-copy directory");
        if (!output.getParent().toRealPath().startsWith(lab) || output.startsWith(cache) || Files.exists(output))
            throw new IllegalArgumentException("Oracle output must be new and outside cache-copy, inside lab");
        CacheLibrary library = new CacheLibrary(cache.toString(), false, null);
        try {
            String[] kinds = {"item", "npc", "object", "sequence"};
            int[] indexes = {19, 18, 16, 20};
            int[] shifts = {8, 7, 8, 7};
            StringBuilder out = new StringBuilder("{\"schema_version\":1,\"namespaces\":[");
            for (int i = 0; i < kinds.length; i++) {
                if (i != 0) out.append(',');
                Index index = library.index(indexes[i]);
                TreeSet<Integer> ids = new TreeSet<>();
                for (int archive : index.archiveIds()) {
                    for (int file : index.archive(archive).fileIds()) ids.add((archive << shifts[i]) | file);
                }
                out.append("{\"kind\":\"").append(kinds[i]).append("\",\"index\":")
                   .append(indexes[i]).append(",\"archive_shift\":").append(shifts[i])
                   .append(",\"occupied_ids\":").append(ids).append('}');
            }
            Files.writeString(output, out.append("]}\n").toString(), StandardOpenOption.CREATE_NEW);
        } finally {
            library.close();
        }
    }
}
