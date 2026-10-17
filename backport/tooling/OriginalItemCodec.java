import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import world.gregs.voidps.buffer.read.ArrayReader;
import world.gregs.voidps.buffer.write.ArrayWriter;
import world.gregs.voidps.cache.definition.data.ItemDefinition;
import world.gregs.voidps.cache.definition.data.ItemDefinitionFull;
import world.gregs.voidps.cache.definition.decoder.ItemDecoder;
import world.gregs.voidps.cache.definition.decoder.ItemDecoderFull;
import world.gregs.voidps.cache.definition.encoder.ItemEncoder;

/** Original definition bytes only. No cache, asset loader, assigned ID or game session. */
public final class OriginalItemCodec {
    private static byte[] encode(int cost, int note) {
        ItemDefinitionFull original = new ItemDefinitionFull();
        original.setId(0); // In-memory fixture identity, never an allocation or cache write.
        original.setName("SoloScape Lab token");
        original.setStackable(1);
        original.setCost(cost);
        original.setSpriteScale(2200);
        original.setNoteId(note); // Numeric codec boundary only; no referenced item is loaded.
        ArrayWriter out = new ArrayWriter();
        new ItemEncoder().encode(out, original);
        return Arrays.copyOf(out.array(), out.position());
    }

    /** Deliberately narrow original subset. Native readers alone do not reject every unknown opcode. */
    static void inspectSubset(byte[] bytes) {
        Set<Integer> seen = new HashSet<>();
        int p = 0;
        while (p < bytes.length) {
            int opcode = bytes[p++] & 255;
            if (!seen.add(opcode)) throw new IllegalArgumentException("Duplicate opcode");
            if (opcode == 0) {
                if (p != bytes.length) throw new IllegalArgumentException("Trailing bytes");
                return;
            }
            switch (opcode) {
                case 2:
                    while (p < bytes.length && bytes[p] != 0) p++;
                    if (p == bytes.length) throw new IllegalArgumentException("Unterminated string");
                    p++;
                    break;
                case 4: case 97: p += 2; break;
                case 11: break;
                case 12: p += 4; break;
                default: throw new IllegalArgumentException("Unsupported original-subset opcode " + opcode);
            }
            if (p > bytes.length) throw new IllegalArgumentException("Truncated value");
        }
        throw new IllegalArgumentException("Missing terminator");
    }

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static String hash(byte[] data) throws Exception {
        StringBuilder out = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(data)) out.append(String.format("%02x", b & 255));
        return out.toString();
    }

    private static String decode(int cost, int note) throws Exception {
        byte[] bytes = encode(cost, note);
        require(Arrays.equals(bytes, encode(cost, note)), "Encoder is not deterministic");
        inspectSubset(bytes);
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
        require(full.getName().equals("SoloScape Lab token") && light.getName().equals(full.getName()) && client.name.equals(full.getName()), "Name disagreement");
        require(full.getCost() == cost && light.getCost() == cost && client.cost == cost, "Cost disagreement");
        require(full.getStackable() == 1 && light.getStackable() == 1 && client.stackable == 1, "Stackability disagreement");
        require(full.getSpriteScale() == 2200 && client.zoom2d == 2200, "Sprite scale disagreement");
        int signed = note == -1 ? -1 : (short) note;
        require(full.getNoteId() == signed && light.getNoteId() == signed, "Unexpected server note decoding");
        require(client.certlink == note, "Unexpected client note decoding");
        boolean equal = full.getNoteId() == client.certlink;
        require(equal == (note < 32768), "Unexpected compatibility boundary");
        return "{\"cost\":" + cost + ",\"note_reference\":" + note + ",\"server_full_note\":" + full.getNoteId()
            + ",\"server_light_note\":" + light.getNoteId() + ",\"client_note\":" + client.certlink
            + ",\"reference_agrees\":" + equal + ",\"bytes\":" + bytes.length + ",\"sha256\":\"" + hash(bytes) + "\"}";
    }

    public static void main(String[] args) throws Exception {
        StringBuilder rows = new StringBuilder();
        for (int note : new int[] {-1, 32767, 32768, 65534, 65535}) {
            if (rows.length() != 0) rows.append(',');
            rows.append(decode(37, note));
        }
        rows.append(',').append(decode(38, -1));
        require(!Arrays.equals(encode(37, -1), encode(38, -1)), "Cost control did not change bytes");
        byte[] good = encode(37, -1);
        byte[] trailing = Arrays.copyOf(good, good.length + 1);
        byte[] duplicate = new byte[good.length + 1];
        duplicate[0] = 11;
        System.arraycopy(good, 0, duplicate, 1, good.length);
        int rejected = 0;
        for (byte[] bad : new byte[][] {{(byte) 250, 0}, {2, 65}, {12, 1, 2},
                Arrays.copyOf(good, good.length - 1), trailing, duplicate}) {
            try { inspectSubset(bad); } catch (IllegalArgumentException expected) { rejected++; }
        }
        require(rejected == 6, "A malformed/unsupported definition passed the original-subset guard");
        System.out.println("{\"mode\":\"original-native-codec-probe\",\"cache_written\":false,\"id_allocated\":false,\"cases\":["
            + rows + "],\"rejected_malformed_controls\":" + rejected + "}");
    }
}
