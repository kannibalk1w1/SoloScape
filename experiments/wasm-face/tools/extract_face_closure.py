#!/usr/bin/env python3
"""Extract the native 634 projected flat-face closure from a locally supplied source tree.

Copies, verbatim, nine Class64_Sub1 methods (method654 projection, method650 face loop, method643
face gates, method635 flat dispatch, method634, method632, method655, method629, method638), the
Class109 field block, constructor and the flat-fill methods (method1018 -> method1026) plus the
method1023 wireframe setter, into a generated directory. Everything else is a labelled stand-in:
  * method657 is replaced by a HAND-WRITTEN guarded adapter (state 2 only; counts, throws otherwise);
  * method646, method658, ha_Sub1.method3720, Class109.method1022/1024 and ha.method3645 are
    generated stubs that count and throw.
Fails closed: the nine-method set, the 450-line and 65-field budgets, the callee set and every class
referenced by the extracted text are checked before anything is written. Nothing from the native
source is committed; run.sh points --out at the ignored build directory.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "wasm-triangle" / "tools"))
import extract_triangle_closure as tri  # noqa: E402  (flat-fill extractor helpers: method_span, declared_type)

METHODS = ("method654", "method650", "method643", "method635", "method634", "method632", "method655",
           "method629", "method638")
FLAT_ROOT = "method1018"
MAX_VERBATIM_LINES = 450
MAX_FIELDS = 65
MAX_ADAPTER_LINES = 20
# Clip mode (opt-in, --clip): method646 is copied verbatim and the verbatim budget becomes the audited 580 lines.
# The only non-verbatim line is one counter inserted before the output switch, and it is verified to be the sole diff.
CLIP_METHOD = "method646"
MAX_VERBATIM_LINES_CLIP = 580
STUB_646 = "    private final void method646(int i) { FaceCounters.clipBranch++; throw new IllegalStateException(\"method646 (clip branch) reached\"); }\n"
CLIP_COUNTER_ANCHOR = "        int i_563_ = anIntArray5315[0];\n"
CLIP_COUNTER_LINE = ("        FaceCounters.clipOut[i_540_]++; // HARNESS COUNTER (clip mode): the only non-verbatim line in method646\n")
# Clip mode: one entry counter at the top of the generated Class109.method1018 (the flat fill every path calls).
FILL_SIGNATURE = re.compile(r"^    final void method1018\(.*\{\s*$")
FILL_COUNTER_LINE = ("        FaceCounters.flatFillEntries++; // HARNESS COUNTER (clip mode): the only non-verbatim line in Class109.method1018\n")
INPUT_FILES = ("Class64_Sub1.java", "Class109.java", "Class167.java", "ha_Sub1.java", "ha.java",
               "Class101_Sub1.java", "Class6.java", "Class350.java", "Class318_Sub3.java", "Class126.java")
# Methods the nine bodies may call: the nine themselves, the adapter, stubs, and these external ones.
ALLOWED_CALLS = set(METHODS) | {"method657", "method646", "method658", "method3720", "method3724",
                                "method1018", "method1022", "method1024", "method1023", "method3645"}
STUB_TYPES = {"Class6", "Class350", "Class129", "Class342", "Class167", "Class109", "Class101", "Class101_Sub1",
              "Class318_Sub3", "ha_Sub1"}
ADAPTER_FIELDS = ("anInt5354", "aShortArray5311", "aByteArray5386")

ADAPTER = """
    // NON-VERBATIM ADAPTER (hand-written; replaces native method657, same signature). State 2 only.
    private final void method657(boolean bool) {
        FaceCounters.adapterEntries++;
        if (anInt5354 != 2) {
            FaceCounters.adapterIllegal++;
            throw new IllegalStateException("method657 adapter supports state 2 only: " + anInt5354);
        }
        if ((anInt5316 & 0x97098) == 0 && aFloatArrayArray5314 == null) aShortArray5311 = null;
        if (bool) aByteArray5386 = null;
    }
"""
# Harness glue (hand-written, not native): constructor and an entry that calls the native method654(i == -1).
GLUE = """
    // HARNESS GLUE (hand-written)
    Class64_Sub1(ha_Sub1 renderer) { aHa_Sub1_5353 = renderer; }
    void harnessProject(Class101 camera, int flags) { method654(camera, null, -1, flags); }
    // STUBS (hand-written): every branch outside the audited flat path counts and throws.
    private final void method646(int i) { FaceCounters.clipBranch++; throw new IllegalStateException("method646 (clip branch) reached"); }
    private final void method658(int i) { FaceCounters.litBranch++; throw new IllegalStateException("method658 (lit branch) reached"); }
"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message):
    raise SystemExit("face closure: " + message)


def parse_fields(lines, first_method_line):
    """Instance field declarations from the class header: (name, type, declaration line)."""
    fields = []
    for line in lines[:first_method_line]:
        m = re.match(r"^    (?:(private|final)\s+)*(?!static)([\w\[\]]+)\s+(\w+)(\s*=\s*[^;]+)?;\s*$", line)
        if m and "static" not in line:
            fields.append((m.group(3), m.group(2), line))
    return fields


def stub_members(text, patterns):
    found = set()
    for pattern in patterns:
        found |= set(re.findall(pattern, text))
    return sorted(found)


def decl(source, name):
    return tri.declared_type(source, name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--clip", action="store_true", help="opt-in: method646 verbatim, one counter line, 580-line budget")
    args = parser.parse_args()
    read = lambda n: (args.src_dir / n).read_text(encoding="utf-8")
    digests = {n: sha(args.src_dir / n) for n in INPUT_FILES}
    methods = METHODS + ((CLIP_METHOD,) if args.clip else ())
    budget = MAX_VERBATIM_LINES_CLIP if args.clip else MAX_VERBATIM_LINES
    glue = GLUE
    if args.clip:
        if STUB_646 not in GLUE:
            fail("method646 stub line not found in the glue; re-audit")
        glue = GLUE.replace(STUB_646, "").replace("every branch outside the audited flat path counts and throws.",
                                                   "every branch outside the audited flat and clip paths counts and throws.")

    # ---- Class64_Sub1: verbatim methods (nine, plus method646 in clip mode) ------------------------
    src64 = read("Class64_Sub1.java")
    lines = src64.splitlines(keepends=True)
    spans = {n: tri.method_span(lines, n) for n in methods}
    verbatim = {n: "".join(lines[s:e + 1]) for n, (s, e) in spans.items()}
    verbatim_lines = sum(e - s + 1 for s, e in spans.values())
    if verbatim_lines > budget:
        fail(f"verbatim closure is {verbatim_lines} lines, budget {budget}; stop and re-audit")
    if args.clip:
        native646 = verbatim[CLIP_METHOD]
        if native646.count(CLIP_COUNTER_ANCHOR) != 1:
            fail("method646 counter anchor is not unique; re-audit")
        counted646 = native646.replace(CLIP_COUNTER_ANCHOR, CLIP_COUNTER_LINE + CLIP_COUNTER_ANCHOR)
        if counted646.replace(CLIP_COUNTER_LINE, "") != native646:
            fail("counter insertion is not the only change to method646")
        verbatim[CLIP_METHOD] = counted646
    bodies = "\n".join(verbatim[n] for n in methods)
    adapter_lines = len([l for l in ADAPTER.strip("\n").splitlines() if l.strip()])
    if adapter_lines > MAX_ADAPTER_LINES:
        fail(f"adapter is {adapter_lines} lines, budget {MAX_ADAPTER_LINES}")

    callees = set(re.findall(r"\b(method\d+)\(", bodies))
    if callees - ALLOWED_CALLS:
        fail("unaudited callees: " + ", ".join(sorted(callees - ALLOWED_CALLS)))
    if not {"method657", "method646", "method658"} <= callees:
        fail("expected call sites to method657/646/658 were not found; source changed, re-audit")
    classes = set(re.findall(r"\b(Class\d+(?:_Sub\d+)*)\b", bodies))
    if classes - STUB_TYPES - {"Class126", "Class64_Sub1"}:
        fail("unaudited classes: " + ", ".join(sorted(classes - STUB_TYPES - {"Class126", "Class64_Sub1"})))
    if re.search(r"\bClass64_Sub1\.", bodies) or re.search(r"\bsuper\b", bodies):
        fail("static member of Class64_Sub1 or super referenced")

    first_method = next(i for i, l in enumerate(lines) if re.match(r"^    (?:private |final )*[\w\[\]]+ \w+\(", l))
    fields = parse_fields(lines, first_method)
    text_for_fields = bodies + ADAPTER + glue
    kept = [(n, t, l) for n, t, l in fields if re.search(r"\b" + n + r"\b", text_for_fields)]
    if len(kept) > MAX_FIELDS:
        fail(f"{len(kept)} instance fields, budget {MAX_FIELDS}")
    kept_names = {n for n, _, _ in kept}
    for needed in ADAPTER_FIELDS:
        if needed not in kept_names:
            fail(f"adapter field {needed} not declared natively")
    for _, t, _ in kept:
        base = t.rstrip("[]")
        if base not in {"int", "short", "byte", "boolean", "float"} | STUB_TYPES:
            fail(f"field type {t} is outside the audited stand-in set")
    statics = re.findall(r"^\s*(?:private\s+)?static\s+[\w\[\]]+\s+(\w+)", "".join(lines[:first_method]), re.M)
    if [s for s in statics if re.search(r"\b" + s + r"\b", bodies)]:
        fail("a static field of Class64_Sub1 is referenced")

    # ---- Class109: field block, ctor, flat-fill closure + wireframe setter --------------------------
    src109 = read("Class109.java")
    l109 = src109.splitlines(keepends=True)
    all109 = set(re.findall(r"^    (?:(?:private|final)\s+)*[\w\[\]]+\s+(method\d+)\(", src109, re.M))
    wanted, queue, spans109 = [], [FLAT_ROOT, "method1023"], {}
    while queue:
        name = queue.pop(0)
        if name in wanted:
            continue
        spans109[name] = tri.method_span(l109, name)
        wanted.append(name)
        body = "".join(l109[spans109[name][0]:spans109[name][1] + 1])
        queue += [c for c in sorted(set(re.findall(r"\b(method\d+)\(", body))) if c != name and c in all109]
    header_end = next(i for i, l in enumerate(l109) if re.match(r"^    (?:private |final )*void method", l))
    ctor_start = next(i for i, l in enumerate(l109) if l.startswith("    Class109("))
    depth, opened = 0, False
    for ctor_end in range(ctor_start, len(l109)):
        for ch in l109[ctor_end]:
            if ch == "{":
                depth, opened = depth + 1, True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            break
    field_block = "".join(l109[:header_end]).rstrip() + "\n\n"
    ctor = "".join(l109[ctor_start:ctor_end + 1])
    native109 = {n: "".join(l109[spans109[n][0]:spans109[n][1] + 1]) for n in wanted}
    if args.clip:
        fill = l109[spans109[FLAT_ROOT][0]:spans109[FLAT_ROOT][1] + 1]
        sigs = [i for i, l in enumerate(fill) if FILL_SIGNATURE.match(l)]
        if len(sigs) != 1:
            fail("method1018 signature not unique; re-audit")
        counted = fill[:sigs[0] + 1] + [FILL_COUNTER_LINE] + fill[sigs[0] + 1:]
        counted_text = "".join(counted)
        # Deleting the single counter line must restore the exact native method1018 body.
        if counted_text.replace(FILL_COUNTER_LINE, "") != native109[FLAT_ROOT]:
            fail("method1018 counter is not the only change to the native body")
        native109[FLAT_ROOT] = counted_text
    bodies109 = "\n".join(native109[n] for n in sorted(wanted))
    text109 = field_block + ctor + "\n\n" + bodies109 + "\n"
    # Stubs for the other fills Class64_Sub1.method635 can reach; signatures taken from the native source.
    stubs109 = ""
    for name, counter in (("method1022", "fill1022"), ("method1024", "fill1024")):
        sig = next((l for l in l109 if re.match(r"^    final void " + name + r"\(", l)), None)
        if sig is None:
            fail(f"Class109.{name} signature not found")
        stubs109 += (sig.rstrip().rstrip("{") + "{ FaceCounters." + counter
                     + "++; throw new IllegalStateException(\"" + name + " (not in the flat path) reached\"); }\n")
    text109 += "    // STUBS (hand-written signatures): fills outside the flat path count and throw.\n" + stubs109 + "}\n"
    ext_ha = sorted(set(re.findall(r"aHa_Sub1_1666\.(\w+)", ctor + bodies109)))
    ext_ctx = sorted(set(re.findall(r"aClass167_1670\.(\w+)", text109)))

    # ---- stand-in members ---------------------------------------------------------------------------
    ha_src, c167_src = read("ha_Sub1.java"), read("Class167.java")
    ha64 = sorted(set(re.findall(r"aHa_Sub1_5353\.(\w+)", bodies)))
    ha_fields = sorted((set(ha64) | set(ext_ha)) - {m for m in ha64 + ext_ha if m.startswith("method")})
    ha_calls = sorted({m for m in ha64 + ext_ha if m.startswith("method")})
    if set(ha_calls) - {"method3720", "method3645", "method3724"}:
        fail("unaudited ha_Sub1 method: " + ", ".join(sorted(set(ha_calls) - {"method3720", "method3645", "method3724"})))
    m3720 = re.search(r"\bmethod3720\(([^)]*)\)", ha_src)
    m3645 = re.search(r"final void method3645\(([^)]*)\)", read("ha.java"))
    if not m3720 or not m3645:
        fail("ha_Sub1.method3720 / ha.method3645 signature not found")
    ctx64 = stub_members(bodies, [r"aClass167_5367\.(\w+)", r"\bclass167\.(\w+)"])
    ctx_fields = sorted(set(ctx64) | set(ext_ctx))
    floats = sorted(set(re.findall(r"\b(aFloat\d+)\b", bodies)))
    c6 = stub_members(bodies, [r"\bclass6\.(\w+)", r"aClass6Array5361\[[^\]]*\]\.(\w+)"])
    c350 = stub_members(bodies, [r"\bclass350\.(\w+)", r"aClass350Array5363\[[^\]]*\]\.(\w+)"])
    c318 = stub_members(bodies, [r"\bclass318_sub3\.(\w+)"])
    src = {"Class6": read("Class6.java"), "Class350": read("Class350.java"), "Class318_Sub3": read("Class318_Sub3.java"),
           "Class101_Sub1": read("Class101_Sub1.java")}
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    jode = "".join(lines[:3])

    def banner(name, extra=""):
        return (jode + "// GENERATED from a locally supplied native source. Do not commit.\n"
                f"// Source: {name} sha256={digests[name]}{extra}\n")

    members = "".join(l.replace("private ", "", 1) for _, _, l in kept)
    (out / "Class64_Sub1.java").write_text(
        banner("Class64_Sub1.java", f" ({len(methods)} native method spans; disclosed harness counters in clip mode; field declarations except private modifier)\n"
               "// Hand-written parts are marked ADAPTER / HARNESS GLUE / STUBS; the class no longer extends Class64.")
        + "\nfinal class Class64_Sub1 {\n" + members + "\n" + "\n".join(verbatim[n] for n in methods)
        + ADAPTER + glue + "}\n", encoding="utf-8")
    (out / "Class109.java").write_text(banner("Class109.java") + text109, encoding="utf-8")

    def cls(name, fields, source, extends=""):
        return (f"final class {name}{extends} {{\n" + "".join(f"    {decl(source, f)} {f};\n" for f in fields) + "}\n")

    (out / "Class6.java").write_text("// Generated type stand-in (textured branch only; never reached).\n" + cls("Class6", c6, src["Class6"]))
    (out / "Class350.java").write_text("// Generated type stand-in (textured branch only; never reached).\n" + cls("Class350", c350, src["Class350"]))
    (out / "Class318_Sub3.java").write_text("// Generated type stand-in (the harness passes null).\n" + cls("Class318_Sub3", c318, src["Class318_Sub3"]))
    (out / "Class129.java").write_text("// Generated type stand-in (always null).\nfinal class Class129 {}\n")
    (out / "Class342.java").write_text("// Generated type stand-in (always null).\nfinal class Class342 {}\n")
    (out / "Class101.java").write_text("// Generated type stand-in.\nabstract class Class101 {}\n")
    (out / "Class101_Sub1.java").write_text(
        "// Generated stand-in: only the twelve transform floats the face path reads.\n"
        + cls("Class101_Sub1", floats, src["Class101_Sub1"], " extends Class101"))
    (out / "Class126.java").write_text(
        "// Generated stand-in for the palette holder; filled with the ORIGINAL synthetic palette by the harness.\n"
        f"final class Class126 {{\n    static {decl(read('Class126.java'), 'anIntArray4983')} anIntArray4983;\n}}\n")
    (out / "Class167.java").write_text(
        "// Generated stand-in for the per-thread context: only the members the face path reads or writes.\n"
        + cls("Class167", ctx_fields, c167_src))
    ha_decls = "".join(f"    {decl(ha_src, f)} {f};\n" for f in ha_fields)
    (out / "ha_Sub1.java").write_text(
        "// Generated stand-in for ha_Sub1: viewport/projection fields, the context lookup, and counting stubs.\n"
        "final class ha_Sub1 {\n" + ha_decls + "    Class167[] aClass167Array7480;\n"
        "    final Class167 method3724(Runnable runnable) {\n"
        "        for (int i = 0; i < anInt7485; i++) if (aClass167Array7480[i].aRunnable2198 == runnable) return aClass167Array7480[i];\n"
        "        return null;\n    }\n"
        f"    final void method3720({m3720.group(1)}) {{ FaceCounters.textured3720++; throw new IllegalStateException(\"method3720 (textured) reached\"); }}\n"
        f"    final void method3645({m3645.group(1)}) {{ FaceCounters.wire3645++; throw new IllegalStateException(\"wireframe reached\"); }}\n}}\n")
    if "aRunnable2198" not in ctx_fields:
        # the lookup stub above reads it, so make sure the Class167 stand-in carries it
        (out / "Class167.java").write_text((out / "Class167.java").read_text().rstrip().rstrip("}")
                                           + f"    {decl(c167_src, 'aRunnable2198')} aRunnable2198;\n}}\n")

    report = {
        "inputs_sha256": digests,
        "clip_mode": args.clip,
        "class64_sub1_methods_verbatim": list(methods),
        "class64_sub1_verbatim_lines": verbatim_lines,
        "class64_sub1_line_budget": budget,
        "class64_sub1_non_verbatim_lines": 1 if args.clip else 0,
        "class109_non_verbatim_lines": 1 if args.clip else 0,
        "class109_non_verbatim_note": ("FaceCounters.flatFillEntries++ at the top of method1018" if args.clip else "none"),
        "class64_sub1_per_method_lines": {n: spans[n][1] - spans[n][0] + 1 for n in methods},
        "class64_sub1_native_instance_fields_kept": len(kept),
        "class64_sub1_field_budget": MAX_FIELDS,
        "class64_sub1_fields": sorted(kept_names),
        "adapter_lines": adapter_lines,
        "adapter_line_budget": MAX_ADAPTER_LINES,
        "class109_methods_verbatim": sorted(wanted),
        "class109_verbatim_lines": sum(e - s + 1 for s, e in spans109.values()),
        "class109_stubbed": ["method1022", "method1024"],
        "stubs": (["Class64_Sub1.method658"] if args.clip else ["Class64_Sub1.method646", "Class64_Sub1.method658"])
                 + ["ha_Sub1.method3720", "ha.method3645", "Class109.method1022", "Class109.method1024"],
        "callees_found": sorted(callees),
        "ha_Sub1_members": ha_fields + ha_calls,
        "class167_members": ctx_fields,
        "type_stubs": ["Class6", "Class350", "Class318_Sub3", "Class129", "Class342", "Class101", "Class101_Sub1", "Class126"],
    }
    (out.parent / "closure.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("class64_sub1_verbatim_lines", "class64_sub1_native_instance_fields_kept",
                                              "adapter_lines", "class109_methods_verbatim", "callees_found")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
