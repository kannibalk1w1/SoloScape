#!/usr/bin/env python3
"""Extract the old-format Class124 decode closure verbatim from a locally supplied native source tree.

Copied exactly: Class124.method1103 (226-423) and the Class124(byte[]) constructor (830-837); Packet's
byte[] constructor, readUnsignedShort, method3362, readUnsignedByte and readByte; Class348_Sub21.method2955.
Only the fields those spans reference are declared. Everything else is an ADAPTER and is labelled as such:
the new-format method1106 and Packet's bad-magic writeBytes/writeByteAdd throw and are counted.

Fails closed (nonzero exit) on a changed source digest, a moved span, an unbalanced span, more than 350 body
lines or more than 40 declared fields. Writes ignored output only; nothing native is committed.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

SOURCES = {
    "Class124.java": "26284febbb937e5afbe22f0fb3ebdad74557ffe9010ece3437fc2b4c00e94d3e",
    "Packet.java": "3e217a1d08e82e2f8b329f0a0f8d9bdc67c71ab267405dfb88449c97e987960d",
    "Class348_Sub21.java": "2b9ab115d669baafe7163786c03c902895e327016cb74dd809a3530c7f9b7d7c",
}
# (first native line, last native line, exact first line). The last line must be exactly "    }".
SPANS = {
    "Class124.java": [
        (226, 423, "    private final void method1103(int i, byte[] is) {"),
        (830, 837, "    Class124(byte[] is) {"),
    ],
    "Packet.java": [
        (757, 760, "    Packet(byte[] is) {"),
        (88, 93, "    final int readUnsignedShort(int i) {"),
        (356, 362, "    final int method3362(byte i) {"),
        (643, 647, "    final int readUnsignedByte(int i) {"),
        (649, 653, "    final byte readByte(int i) {"),
    ],
    "Class348_Sub21.java": [
        (69, 71, "    static int method2955(int i, int i_24_) {"),
    ],
}
MAX_BODY_LINES = 350
MAX_FIELDS = 40
FIELD = re.compile(r"^    (?:(?:static|final) )*[\w\[\]]+ (\w+)(?: = .*)?;$")

# ADAPTER members (not native text). Each counts and throws so a reached adapter fails the case.
CLASS124_ADAPTERS = [
    "    /* ADAPTER: native method1106 (new format, footer ends -1,-1) is not extracted. Calling it fails loudly. */",
    "    private final void method1106(byte[] is, byte i) {",
    "        newFormatStubCalls++;",
    "        throw new UnsupportedOperationException(\"ADAPTER: Class124.method1106 new-format decode is not extracted\");",
    "    }",
]
PACKET_ADAPTERS = [
    "    /* ADAPTER: native writeBytes (bad-magic path) is not extracted. Calling it fails loudly. */",
    "    final void writeBytes(int i, int i_73_, byte[] is, int i_74_) {",
    "        badMagicStubCalls++;",
    "        throw new IllegalStateException(\"ADAPTER: Packet.writeBytes bad-magic path is not extracted\");",
    "    }",
    "    /* ADAPTER: native writeByteAdd (bad-magic path) is not extracted. Calling it fails loudly. */",
    "    final void writeByteAdd(byte i, int i_94_) {",
    "        badMagicStubCalls++;",
    "        throw new IllegalStateException(\"ADAPTER: Packet.writeByteAdd bad-magic path is not extracted\");",
    "    }",
]
ADAPTER_COUNTERS = {"Class124.java": ["    static int newFormatStubCalls;"],
                    "Packet.java": ["    static int badMagicStubCalls;"]}
HEADERS = {
    "Class124.java": "final class Class124 {",
    "Packet.java": "class Packet {",
    "Class348_Sub21.java": "final class Class348_Sub21 {",
}


def die(message):
    print("extract_decode_closure: " + message, file=sys.stderr)
    sys.exit(1)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def class_fields(lines):
    fields = []
    for number, line in enumerate(lines, 1):
        match = FIELD.match(line)
        if match:
            fields.append((match.group(1), number, line))
    return fields


def take_span(lines, first, last, head):
    if lines[first - 1] != head:
        die(f"span {first}-{last} does not start with {head!r}")
    if lines[last - 1] != "    }":
        die(f"span {first}-{last} does not end with a method closing brace")
    text = lines[first - 1:last]
    depth = 0
    for line in text:
        depth += line.count("{") - line.count("}")
    if depth != 0:
        die(f"span {first}-{last} is unbalanced")
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    src = pathlib.Path(args.src_dir)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    closure = {"sources": {}, "spans": {}, "fields": {}, "adapters": [], "budgets": {}, "generated": {}}
    body_lines = 0
    field_total = 0
    for name, expected in SOURCES.items():
        raw = (src / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected:
            die(f"{name} digest {digest} differs from the audited {expected}")
        closure["sources"][name] = digest

    for name, spans in SPANS.items():
        lines = (src / name).read_text(encoding="utf-8").splitlines()
        verbatim = []
        closure["spans"][name] = []
        for first, last, head in spans:
            text = take_span(lines, first, last, head)
            verbatim.append(text)
            closure["spans"][name].append({"lines": [first, last],
                                           "sha256": sha256_text("\n".join(text) + "\n")})
            body_lines += len(text)
        referenced = "\n".join("\n".join(block) for block in verbatim)
        adapters = {"Class124.java": CLASS124_ADAPTERS, "Packet.java": PACKET_ADAPTERS}.get(name, [])
        counters = ADAPTER_COUNTERS.get(name, [])
        referenced += "\n" + "\n".join(adapters) + "\n" + "\n".join(counters)
        if adapters:
            body_lines += len(adapters)
        declared = []
        for field, number, line in class_fields(lines):
            if re.search(r"\b" + re.escape(field) + r"\b", referenced):
                declared.append(line)
                closure["fields"].setdefault(name, []).append({"name": field, "nativeLine": number})
        field_total += len(declared) + len(counters)
        body_lines += len(declared) + len(counters)
        closure["adapters"] += [a.strip() for a in adapters if a.strip().startswith("/* ADAPTER")]

        banner = [
            f"/* GENERATED from {name} by tools/extract_decode_closure.py. Do not edit or commit.",
            f" * Source sha256 {closure['sources'][name]}.",
            " * Verbatim native spans: " + ", ".join(f"{a}-{b}" for a, b, _ in spans) + ".",
            " * ADAPTER members are labelled. Members outside these spans do not exist here.",
            " */",
        ]
        body = banner + [HEADERS[name]] + declared + counters + [""] + adapters + [""]
        for block in verbatim:
            body += block + [""]
        body += ["}"]
        text = "\n".join(body) + "\n"
        (out / name).write_text(text, encoding="utf-8")
        closure["generated"][name] = hashlib.sha256(text.encode("utf-8")).hexdigest()

    if body_lines > MAX_BODY_LINES:
        die(f"closure body {body_lines} lines exceeds {MAX_BODY_LINES}")
    if field_total > MAX_FIELDS:
        die(f"closure declares {field_total} fields and counters, above {MAX_FIELDS}")
    closure["budgets"] = {"bodyLines": body_lines, "maxBodyLines": MAX_BODY_LINES,
                          "fields": field_total, "maxFields": MAX_FIELDS}
    (out.parent / "closure.json").write_text(json.dumps(closure, indent=2) + "\n", encoding="utf-8")
    print(f"extracted closure: {body_lines} body lines, {field_total} fields/counters, "
          f"{len(closure['adapters'])} adapters")


if __name__ == "__main__":
    main()
