# Damaged compressed backup recovery — 17 October 2026

A corrupted DEFLATE stream inside an otherwise readable ZIP raised `zlib.error` out of backup discovery. One damaged archive could therefore hide every healthy recovery option. Both the metadata reader and the full archive validator now translate that specific decoding failure into the existing invalid-backup result. The archive is retained; no repair or deletion is attempted.

The regression modifies the first compressed byte to the reserved DEFLATE block type, separately in `backup.json` and the primary character save. Before the fix both cases crash discovery. After the fix each damaged archive is listed as invalid beside the healthy archive, restore refuses it without changing the manifest, save or generation set, and restoring the healthy archive succeeds. The damaged bytes and previous save generation remain available.

Validation: all 24 profile tests pass; all 141 tooling cases pass with one existing optional skip. Logs are private under `.runtime/corrupt-deflate-{before,after,tooling}-20261017.log`. The change is limited to the two ZIP decoding boundaries and one two-case regression. These disposable host tests do not replace physical launcher/Deck acceptance.
