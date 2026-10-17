#!/usr/bin/env python3
"""Extract the native 634 flat-colour triangle closure from a locally supplied source tree.

Copies, verbatim, from Class109.java: the field block, the constructor, method1018 (flat-colour
triangle set-up and scan conversion) and method1026 (depth-tested span fill). Writes them with
minimal stand-ins for ha_Sub1 and Class167 into a generated directory. Nothing from the native
source is committed; run.sh points --out at the ignored build directory.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT_METHODS = ("method1018",)
INPUT_FILES = ("Class109.java", "Class167.java", "ha_Sub1.java", "ha.java", "Class64_Sub1.java")


def method_span(lines, name):
    pattern = re.compile(r"^    (?:(?:private|final|static)\s+)*[\w\[\]]+\s+" + name + r"\(")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        raise SystemExit(f"{name} not found")
    depth, opened = 0, False
    for end in range(start, len(lines)):
        for ch in lines[end]:
            if ch == "{":
                depth, opened = depth + 1, True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            return start, end
    raise SystemExit(f"unterminated body for {name}")


def called_methods(text):
    return set(re.findall(r"\b(method\d+)\(", text))


def declared_type(source, name):
    match = re.search(r"^\s*(?:private\s+|final\s+|static\s+)*([\w\[\]]+)\s+" + re.escape(name) + r"\b\s*[;=]",
                      source, re.M)
    if not match:
        raise SystemExit(f"no native declaration for {name}")
    return match.group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-dir", required=True, type=pathlib.Path, help="absolute path to client/src")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="generated source directory")
    args = parser.parse_args()

    digests = {}
    for name in INPUT_FILES:
        digests[name] = hashlib.sha256((args.src_dir / name).read_bytes()).hexdigest()
    source = (args.src_dir / "Class109.java").read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)

    # Reachability inside Class109: transitive closure over methodNNNN( calls.
    wanted, queue = [], list(ROOT_METHODS)
    spans = {}
    while queue:
        name = queue.pop(0)
        if name in wanted:
            continue
        spans[name] = method_span(lines, name)
        wanted.append(name)
        body = "".join(lines[spans[name][0]:spans[name][1] + 1])
        for callee in sorted(called_methods(body)):
            if callee != name and re.search(r"^    (?:\w+\s+)*[\w\[\]]+\s+" + callee + r"\(", source, re.M):
                if re.search(r"^    (?:(?:private|final)\s+)*[\w\[\]]+\s+" + callee + r"\(", source, re.M):
                    queue.append(callee)

    header_end = next(i for i, line in enumerate(lines) if re.match(r"^    (?:private |final )*void method", line))
    class_open = next(i for i, line in enumerate(lines) if line.startswith("final class Class109"))
    field_block = "".join(lines[:header_end]).rstrip() + "\n\n"
    ctor_start = next(i for i, line in enumerate(lines) if line.startswith("    Class109("))
    depth, opened = 0, False
    for ctor_end in range(ctor_start, len(lines)):
        for ch in lines[ctor_end]:
            if ch == "{":
                depth, opened = depth + 1, True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            break
    ctor = "".join(lines[ctor_start:ctor_end + 1])
    bodies = "\n".join("".join(lines[spans[n][0]:spans[n][1] + 1]) for n in sorted(wanted))
    text = field_block + ctor + "\n\n" + bodies + "}\n"

    ha_src = (args.src_dir / "ha_Sub1.java").read_text(encoding="utf-8")
    c167_src = (args.src_dir / "Class167.java").read_text(encoding="utf-8")
    ctor_uses = sorted(set(re.findall(r"aHa_Sub1_1666\.(\w+)", ctor)))
    wire_uses = sorted(set(re.findall(r"aHa_Sub1_1666\.(method\d+)\(", bodies)))
    c167_uses = sorted(set(re.findall(r"aClass167_1670\.(\w+)", text)))
    ha_decls = "\n".join(f"    {declared_type(ha_src, f)} {f};" for f in ctor_uses)

    args.out.mkdir(parents=True, exist_ok=True)
    banner = ("// GENERATED from a locally supplied native source. Do not commit.\n"
              f"// Source: Class109.java sha256={digests['Class109.java']}\n")
    (args.out / "Class109.java").write_text(banner + text, encoding="utf-8")
    (args.out / "ha_Sub1.java").write_text(
        "// Generated stand-in for the native ha_Sub1 renderer. Only the pixel-buffer fields that the\n"
        "// Class109 constructor reads are kept; the wireframe branch of the fill is NOT supported.\n"
        "final class ha_Sub1 {\n" + ha_decls + "\n"
        "    final void method3645(int a, int b, int c, int d, int e, int f) {\n"
        "        throw new UnsupportedOperationException(\"wireframe line path excluded from closure\");\n"
        "    }\n}\n", encoding="utf-8")
    c167_decls = "\n".join(f"    {declared_type(c167_src, f)} {f};" for f in c167_uses)
    (args.out / "Class167.java").write_text(
        "// Generated stand-in for the native per-thread Class167 context: only the depth-test flag.\n"
        "final class Class167 {\n" + c167_decls + "\n}\n", encoding="utf-8")

    call_sites = []
    for path in sorted(args.src_dir.glob("*.java")):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if re.search(r"\.method1018\(", line):
                call_sites.append(f"{path.name}:{number}")
    report = {
        "inputs_sha256": digests,
        "extracted_methods": wanted,
        "extracted_lines": sum(spans[n][1] - spans[n][0] + 1 for n in wanted),
        "class109_total_lines": len(lines),
        "native_methods_not_extracted": sorted(set(re.findall(r"^    (?:(?:private|final)\s+)*[\w\[\]]+\s+(method\d+)\(", source, re.M)) - set(wanted)),
        "ha_Sub1_members_read_by_constructor": ctor_uses,
        "ha_members_called_by_bodies": wire_uses,
        "class167_members_read": c167_uses,
        "method1018_call_sites": call_sites,
    }
    (args.out.parent / "closure.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("extracted_methods", "extracted_lines", "ha_Sub1_members_read_by_constructor",
                                              "ha_members_called_by_bodies", "class167_members_read")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
