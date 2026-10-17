#!/usr/bin/env python3
"""Extract the native 634 software face-edge kernel from a locally supplied source tree.

The method body is copied verbatim into a generated file under the build directory; nothing
from the native source is committed. Fields are re-declared with the types the native class
declares, so any identifier that escapes this closure fails the compile in the audit step.
"""
import argparse
import hashlib
import pathlib
import re
import sys

METHOD = "method3636"
METHOD_START = re.compile(r"^    final void method3636\(")
FIELD = r"^\s*(?:private\s+|final\s+)*({type})\s+({name})\b"


def extract_method(lines):
    start = next((i for i, line in enumerate(lines) if METHOD_START.match(line)), None)
    if start is None:
        raise SystemExit(f"{METHOD} not found")
    depth, opened = 0, False
    for end in range(start, len(lines)):
        for ch in lines[end]:
            if ch == "{":
                depth, opened = depth + 1, True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            return lines[start:end + 1]
    raise SystemExit("unterminated method body")


def declared_type(source, name):
    for kind in ("int[]", "int"):
        if re.search(FIELD.format(type=re.escape(kind), name=re.escape(name)), source, re.M):
            return kind
    raise SystemExit(f"no native declaration found for field {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, type=pathlib.Path, help="absolute path to ha_Sub1.java")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="generated source directory")
    args = parser.parse_args()

    source = args.src.read_text(encoding="utf-8")
    body = extract_method(source.splitlines(keepends=True))
    text = "".join(body)
    fields = sorted(set(re.findall(r"\bthis\.(\w+)", text)))
    digest = hashlib.sha256(args.src.read_bytes()).hexdigest()

    args.out.mkdir(parents=True, exist_ok=True)
    decls = "\n".join(f"    {declared_type(source, f)} {f};" for f in fields)
    (args.out / "NativeFaceKernel.java").write_text(
        "// GENERATED from a locally supplied native source. Do not commit.\n"
        f"// Source: ha_Sub1.java sha256={digest}\n"
        "// Body of ha_Sub1.method3636 is verbatim; only the declaring class and fields are synthesised.\n"
        "final class NativeFaceKernel {\n"
        f"{decls}\n\n{text}}}\n",
        encoding="utf-8",
    )
    # Minimal stand-ins for the two native types the method's signature and cast reference.
    (args.out / "aa.java").write_text("abstract class aa {\n}\n", encoding="utf-8")
    (args.out / "aa_Sub3.java").write_text(
        "final class aa_Sub3 extends aa {\n    int[] anIntArray5201;\n    int[] anIntArray5202;\n}\n",
        encoding="utf-8",
    )
    print(f"extracted {len(body)} lines, fields={fields}, source sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
