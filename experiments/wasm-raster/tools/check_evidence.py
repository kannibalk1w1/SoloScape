#!/usr/bin/env python3
"""Validate and record one wasm-raster run; exits nonzero on any missing or mismatched result.

Compares, for every expected size, the native jar bytecode hash, the extracted JVM hash and the
browser (TeaVM WasmGC) hash, and keeps the browser timings. `--mutate` is a self-test hook that
deliberately corrupts one input so the rejection path can be exercised by the wrapper.
"""
import argparse
import hashlib
import html
import json
import pathlib
import re
import sys

EXPECTED_SIZES = ["765x503", "1280x800"]
MUTATIONS = ("browser-hash", "missing-browser")


def read_jsonl(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["size"] in rows:
            raise SystemExit(f"{path.name}: duplicate size {row['size']}")
        rows[row["size"]] = row
    return rows


def read_browser(dom_path, mutate):
    if mutate == "missing-browser":
        raise SystemExit("browser result missing (self-test mutation)")
    dom = dom_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'<pre id="result">(.*?)</pre>', dom, re.S)
    if not match:
        raise SystemExit("browser DOM has no result element")
    text = html.unescape(match.group(1)).strip()
    if text == "WAIT" or not text.startswith("{"):
        raise SystemExit(f"browser result not produced: {text[:120]!r}")
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args()
    build = args.build

    verbatim = read_jsonl(build / "jvm-verbatim.jsonl")
    native = read_jsonl(build / "jvm-native.jsonl")
    browser_doc = read_browser(build / "browser-dom.html", args.mutate)

    raster, present = {}, {}
    for row in browser_doc["sizes"]:
        if "fnv1a" in row:
            if row["size"] in raster:
                raise SystemExit(f"browser: duplicate raster entry for {row['size']}")
            raster[row["size"]] = row
        else:
            if row["size"] in present:
                raise SystemExit(f"browser: duplicate presentation entry for {row['size']}")
            present[row["size"]] = row

    if args.mutate == "browser-hash":
        first = EXPECTED_SIZES[0]
        raster[first]["fnv1a"] = "00000000" if raster[first]["fnv1a"] != "00000000" else "00000001"

    failures = []
    evidence = {"sizes": []}
    for size in EXPECTED_SIZES:
        for label, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", raster)):
            if size not in rows:
                failures.append(f"{size}: missing {label} result")
        if size not in present:
            failures.append(f"{size}: missing browser presentation timings")
        if failures:
            continue
        hashes = {"jvm-native": native[size]["fnv1a"], "jvm-verbatim": verbatim[size]["fnv1a"],
                  "browser": raster[size]["fnv1a"]}
        if len(set(hashes.values())) != 1:
            failures.append(f"{size}: hash mismatch {hashes}")
        evidence["sizes"].append({
            "size": size,
            "fnv1a": hashes["browser"],
            "hashes": hashes,
            "timings": {
                "verbatimJvmRasterMedianMs": verbatim[size].get("rasterMedianMs"),
                "browserRasterMedianMs": raster[size].get("rasterMedianMs"),
                "browserRasterMinMs": raster[size].get("rasterMinMs"),
                "browserConvertMs": present[size].get("convertMs"),
                "browserPutImageDataMs": present[size].get("putImageDataMs"),
            },
        })

    if failures:
        for failure in failures:
            print("FAIL:", failure, file=sys.stderr)
        return 1

    digests = {}
    for name in ("jvm-verbatim.jsonl", "jvm-native.jsonl", "browser-dom.html", "teavm-out/raster.wasm"):
        digests[name] = hashlib.sha256((build / name).read_bytes()).hexdigest()
    evidence.update({"runtime": browser_doc.get("runtime"), "sha256": digests,
                     "expectedSizes": EXPECTED_SIZES, "validated": True})
    (build / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(EXPECTED_SIZES)} sizes, hashes agree across jvm-native, jvm-verbatim, browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
