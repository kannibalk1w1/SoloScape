/** Hand-written counters shared by the generated adapter and stubs (never present in the native jar run). */
final class FaceCounters {
    static int adapterEntries, adapterIllegal, clipBranch, litBranch, textured3720, wire3645, fill1022, fill1024;

    static void reset() {
        adapterEntries = adapterIllegal = clipBranch = litBranch = textured3720 = wire3645 = fill1022 = fill1024 = 0;
    }

    static int stubTotal() {
        return clipBranch + litBranch + textured3720 + wire3645 + fill1022 + fill1024;
    }

    static String json() {
        return "{\"adapterEntries\":" + adapterEntries + ",\"adapterIllegal\":" + adapterIllegal + ",\"method646\":" + clipBranch
            + ",\"method658\":" + litBranch + ",\"method3720\":" + textured3720 + ",\"method3645\":" + wire3645
            + ",\"method1022\":" + fill1022 + ",\"method1024\":" + fill1024 + "}";
    }
}
