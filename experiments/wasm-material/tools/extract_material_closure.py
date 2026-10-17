#!/usr/bin/env python3
"""Extract the native 634 shaded and textured triangle closure from a locally supplied source tree.

Roots: Class109.method1022 (palette-shaded), method1027 (RGB Gouraud), method1020 (three-layer
textured) and method1024 (single-texture). Copies, verbatim, the Class109 field block, constructor
and every Class109 method reachable from those roots, plus Class6.method206 (colour blend). Writes
them with minimal stand-ins for ha_Sub1, Class167 and Class126 into a generated directory.

Fails closed: any reference from the extracted bodies to a class member that is not in the explicit
allow-lists below aborts the run and names the member. Nothing from the native source is committed;
run.sh points --out at the ignored build directory.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT_METHODS = ("method1022", "method1027", "method1020", "method1024")
INPUT_FILES = ("Class109.java", "Class167.java", "ha_Sub1.java", "ha.java", "Class64_Sub1.java",
               "s_Sub1.java", "Class6.java", "Class126.java", "d.java", "Class12.java")
# Everything the extracted bodies may touch outside Class109, each with its stand-in treatment.
ALLOWED_HA = {"anInt7477", "anIntArray7483", "aFloatArray7511", "anInt7501", "method3645", "method3714",
              "method3718", "method3719", "method3726", "method3727"}
ALLOWED_CTX = {"aBoolean2202"}
ALLOWED_STATIC = {("Class126", "anIntArray4983"), ("Class6", "method206")}
# Native signatures the generated ha_Sub1 stand-in must be compatible with, checked against the source.
HA_SIGNATURES = {
    "method3714": ("boolean", "(int i)"),
    "method3718": ("int[]", "(int i)"),
    "method3719": ("int[]", "(int i)"),
    "method3726": ("int", "(int i)"),
    "method3727": ("boolean", "(int i)"),
}


def block_end(lines, start):
    depth, opened = 0, False
    for end in range(start, len(lines)):
        for ch in lines[end]:
            if ch == "{":
                depth, opened = depth + 1, True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            return end
    raise SystemExit(f"unterminated block at line {start + 1}")


def method_span(lines, name):
    pattern = re.compile(r"^    (?:(?:private|final|static)\s+)*[\w\[\]]+\s+" + name + r"\(")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        raise SystemExit(f"{name} not found")
    return start, block_end(lines, start)


def declared_type(source, name):
    match = re.search(r"^\s*(?:private\s+|final\s+|static\s+)*([\w\[\]]+)\s+" + re.escape(name) + r"\b\s*[;=]",
                      source, re.M)
    if not match:
        raise SystemExit(f"no native declaration for {name}")
    return match.group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    read = lambda n: (args.src_dir / n).read_text(encoding="utf-8")

    digests = {n: hashlib.sha256((args.src_dir / n).read_bytes()).hexdigest() for n in INPUT_FILES}
    source = read("Class109.java")
    lines = source.splitlines(keepends=True)
    private_or_final = re.compile(r"^    (?:(?:private|final)\s+)*[\w\[\]]+\s+(method\d+)\(", re.M)
    all_methods = set(private_or_final.findall(source))

    wanted, queue, spans = [], list(ROOT_METHODS), {}
    while queue:
        name = queue.pop(0)
        if name in wanted:
            continue
        spans[name] = method_span(lines, name)
        wanted.append(name)
        body = "".join(lines[spans[name][0]:spans[name][1] + 1])
        for callee in sorted(set(re.findall(r"\b(method\d+)\(", body))):
            if callee != name and callee in all_methods:
                queue.append(callee)

    header_end = next(i for i, line in enumerate(lines) if re.match(r"^    (?:private |final )*void method", line))
    field_block = "".join(lines[:header_end]).rstrip() + "\n\n"
    ctor_start = next(i for i, line in enumerate(lines) if line.startswith("    Class109("))
    ctor = "".join(lines[ctor_start:block_end(lines, ctor_start) + 1])
    bodies = "\n".join("".join(lines[spans[n][0]:spans[n][1] + 1]) for n in sorted(wanted))
    text = field_block + ctor + "\n\n" + bodies + "}\n"

    # Fail-closed dependency audit of everything outside Class109.
    ha_uses = set(re.findall(r"aHa_Sub1_1666\.(\w+)", text))
    ctx_uses = set(re.findall(r"aClass167_1670\.(\w+)", text))
    static_uses = set(re.findall(r"\b(Class\d+(?:_Sub\d+)*)\.(\w+)", bodies + ctor))
    unexpected = ([f"ha_Sub1.{m}" for m in sorted(ha_uses - ALLOWED_HA)]
                  + [f"Class167.{m}" for m in sorted(ctx_uses - ALLOWED_CTX)]
                  + [f"{c}.{m}" for c, m in sorted(static_uses - ALLOWED_STATIC)])
    other_types = set(re.findall(r"\bnew\s+([A-Z]\w*)", bodies + ctor)) - {"Class109"}
    unexpected += [f"new {t}" for t in sorted(other_types)]
    if unexpected:
        raise SystemExit("closure grew beyond the audited dependency list; stop and re-audit: " + ", ".join(unexpected))

    # The stand-ins must match the native signatures they replace.
    ha_src, c167_src = read("ha_Sub1.java"), read("Class167.java")
    for name, (ret, params) in HA_SIGNATURES.items():
        if not re.search(r"^\s*final\s+" + re.escape(ret) + r"\s+" + name + re.escape(params), ha_src, re.M):
            raise SystemExit(f"native ha_Sub1.{name} signature changed: expected {ret} {name}{params}")
    if not re.search(r"final\s+void\s+method3645\(int \w+, int \w+, int \w+, int \w+, int \w+, int \w+\)", read("ha.java")):
        raise SystemExit("native ha.method3645 signature changed")

    # Class6.method206 verbatim, with its own static dependencies audited.
    c6 = read("Class6.java").splitlines(keepends=True)
    s206, e206 = method_span(c6, "method206")
    m206 = "".join(c6[s206:e206 + 1])
    c6_statics = set(re.findall(r"\b(anInt\d+)\b", m206))
    if re.findall(r"\b(Class\d+\w*)\.", m206) or len(c6_statics) != 1:
        raise SystemExit("Class6.method206 has dependencies beyond a single counter field")
    c6_field = sorted(c6_statics)[0]
    palette_type = declared_type(read("Class126.java"), "anIntArray4983")

    args.out.mkdir(parents=True, exist_ok=True)
    banner = ("// GENERATED from a locally supplied native source. Do not commit.\n"
              f"// Source: {{file}} sha256={{sha}}\n")
    (args.out / "Class109.java").write_text(
        banner.format(file="Class109.java", sha=digests["Class109.java"]) + text, encoding="utf-8")
    (args.out / "Class6.java").write_text(
        banner.format(file="Class6.java (method206 only)", sha=digests["Class6.java"])
        + f"final class Class6 {{\n    static {declared_type(read('Class6.java'), c6_field)} {c6_field};\n\n" + m206 + "}\n",
        encoding="utf-8")
    (args.out / "Class126.java").write_text(
        "// Generated stand-in for the native HSL palette holder. The array is filled by the ORIGINAL\n"
        "// synthetic SynthAssets.palette(); the native palette builder (jittered by Math.random) is excluded.\n"
        f"final class Class126 {{\n    static {palette_type} anIntArray4983;\n}}\n", encoding="utf-8")
    ha_decls = "\n".join(f"    {declared_type(ha_src, f)} {f};"
                         for f in sorted(ALLOWED_HA & {"anInt7477", "anIntArray7483", "aFloatArray7511", "anInt7501"}))
    (args.out / "ha_Sub1.java").write_text(
        "// Generated stand-in for the native ha_Sub1 renderer. Pixel/depth buffer fields and a texture\n"
        "// provider backed by the ORIGINAL synthetic SynthAssets; the wireframe line path is NOT supported.\n"
        "final class ha_Sub1 {\n" + ha_decls + "\n"
        "    final boolean method3714(int i) { return SynthAssets.wrapsRepeat(i); }\n"
        "    final int[] method3718(int i) { return SynthAssets.texels(i); }\n"
        "    final int[] method3719(int i) { return SynthAssets.texels(i); }\n"
        "    final int method3726(int i) { return SynthAssets.mode(i); }\n"
        "    final boolean method3727(int i) { return SynthAssets.small(i); }\n"
        "    final void method3645(int a, int b, int c, int d, int e, int f) {\n"
        "        throw new UnsupportedOperationException(\"wireframe line path excluded from closure\");\n"
        "    }\n}\n", encoding="utf-8")
    ctx_decls = "\n".join(f"    {declared_type(c167_src, f)} {f};" for f in sorted(ctx_uses))
    (args.out / "Class167.java").write_text(
        "// Generated stand-in for the native per-thread Class167 context: only the depth-test flag.\n"
        "final class Class167 {\n" + ctx_decls + "\n}\n", encoding="utf-8")

    call_sites = {}
    for path in sorted(args.src_dir.glob("*.java")):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for root in ROOT_METHODS:
                if re.search(r"\.%s\(" % root, line) and path.name != "Class109.java":
                    call_sites.setdefault(root, []).append(f"{path.name}:{number}")
    report = {
        "inputs_sha256": digests,
        "roots": list(ROOT_METHODS),
        "extracted_methods": sorted(wanted),
        "extracted_lines": sum(spans[n][1] - spans[n][0] + 1 for n in wanted),
        "class109_total_lines": len(lines),
        "native_methods_not_extracted": sorted(all_methods - set(wanted)),
        "ha_Sub1_members_used": sorted(ha_uses),
        "class167_members_used": sorted(ctx_uses),
        "external_statics_used": sorted(f"{c}.{m}" for c, m in static_uses),
        "root_call_sites": call_sites,
    }
    (args.out.parent / "closure.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("extracted_methods", "extracted_lines", "ha_Sub1_members_used",
                                              "class167_members_used", "external_statics_used")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
