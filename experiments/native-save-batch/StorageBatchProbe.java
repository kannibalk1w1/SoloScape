import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import world.gregs.voidps.engine.data.PlayerSave;
import world.gregs.voidps.engine.data.file.FileStorage;

/** Original fixtures only. Diagnoses the account-file batch boundary, not game acceptance. */
public final class StorageBatchProbe {
    private static String hash(Path path) throws Exception {
        byte[] bytes = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path));
        StringBuilder result = new StringBuilder();
        for (byte value : bytes) result.append(String.format("%02x", value & 255));
        return result.toString();
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new IllegalStateException(message);
    }

    private static PlayerSave fixture(Path root, String account, int xp) throws Exception {
        String zeroes = String.join(",", Collections.nCopies(25, "0"));
        String levels = String.join(",", Collections.nCopies(25, "1"));
        String data = "accountName = \"" + account + "\"\npasswordHash = \"original-fixture\"\n"
            + "experience = [" + xp + zeroes.substring(1) + "]\n"
            + "levels = [" + levels + "]\nlooks = [0,0,0,0,0,0,0]\ncolours = [0,0,0,0,0]\n"
            + "[tile]\nx = 3232\ny = 3232\n[variables]\noriginal_fixture = true\n";
        Path source = root.resolve(account + "-" + xp + ".toml");
        Files.write(source, data.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        return PlayerSave.Companion.load(source.toFile());
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 1, "Expected a new disposable directory");
        Path root = Paths.get(args[0]).toAbsolutePath();
        Files.createDirectory(root); // refuse existing state; do not clean it on failure
        Path sources = Files.createDirectory(root.resolve("original-fixtures"));
        Path target = Files.createDirectory(root.resolve("native-storage"));
        PlayerSave alpha0 = fixture(sources, "alpha", 0);
        PlayerSave beta0 = fixture(sources, "beta", 0);
        PlayerSave alpha1 = fixture(sources, "alpha", 10);
        PlayerSave beta1 = fixture(sources, "beta", 20);
        FileStorage storage = new FileStorage(target.toFile());
        storage.save(Arrays.asList(alpha0, beta0));
        Path alpha = target.resolve("alpha.toml"), beta = target.resolve("beta.toml");
        String before = hash(alpha), betaBefore = hash(beta);
        Path expected = root.resolve("expected-alpha.toml");
        alpha1.save(expected.toFile());
        String wanted = hash(expected);
        require(!before.equals(wanted), "Snapshots must differ before attempting the batch");
        Path expectedBeta = root.resolve("expected-beta.toml");
        beta1.save(expectedBeta.toFile());
        storage.save(Arrays.asList(alpha1, beta1));
        require(wanted.equals(hash(alpha)) && hash(expectedBeta).equals(hash(beta)), "Positive batch must update both accounts");
        storage.save(Arrays.asList(alpha0, beta0));
        require(before.equals(hash(alpha)) && betaBefore.equals(hash(beta)), "Restore original fixture state before refusal");
        Path retained = root.resolve("retained-beta.toml");
        Files.move(beta, retained);
        Files.createDirectory(beta);
        Path sentinel = beta.resolve("sentinel.txt");
        Files.write(sentinel, "original failure fixture".getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        String sentinelBefore = hash(sentinel);
        boolean refused = false;
        String failureClass = "";
        try {
            storage.save(Arrays.asList(alpha1, beta1));
        } catch (Exception failure) {
            refused = true;
            failureClass = failure.getClass().getName();
        }
        require(refused, "Native storage must refuse replacing a nonempty directory with an account file");
        require(Files.isDirectory(beta) && sentinelBefore.equals(hash(sentinel)), "Failure fixture changed");
        require(betaBefore.equals(hash(retained)), "Retained original beta changed");
        String after = hash(alpha);
        require(after.equals(before) || after.equals(wanted), "First account has unexpected bytes");
        boolean partial = after.equals(wanted);
        String report = "{\n  \"mode\": \"native-file-storage-batch-diagnostic\",\n"
            + "  \"positive_complete_batch\": true,\n  \"batch_refused\": true,\n  \"observed_partial_commit\": " + partial + ",\n"
            + "  \"failure_class\": \"" + failureClass + "\",\n"
            + "  \"alpha_before_sha256\": \"" + before + "\",\n"
            + "  \"alpha_after_sha256\": \"" + after + "\",\n"
            + "  \"alpha_expected_new_sha256\": \"" + wanted + "\",\n"
            + "  \"retained_beta_unchanged\": true,\n  \"failure_sentinel_unchanged\": true,\n"
            + "  \"scope\": \"Original account files; deliberate second-target directory refusal. No world, SaveQueue or power-cut test.\"\n}\n";
        Files.write(root.resolve("result.json"), report.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        System.out.print(report);
    }
}
