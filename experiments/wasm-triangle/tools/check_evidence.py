#!/usr/bin/env python3
"""Validate one wasm-triangle run and write build/evidence.json; exits nonzero on any mismatch.

For each scene and size the native jar bytecode, the extracted JVM build and the TeaVM WasmGC build
must agree on triangle count, covered pixels, colour hash and depth-buffer hash. Presented canvas
pixels must read back to the hash of the RGBA words handed to putImageData. `--mutate` is a
self-test hook that corrupts one input so the rejection path can be exercised.
"""
import argparse
import html
import json
import math
import pathlib
import re
import sys

SIZES = ["765x503", "1280x800"]
SCENES = ["single", "single64", "mesh"]
MUTATIONS = ("browser-hash", "missing-browser", "zero-timing")


def read_jsonl(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            key = (row["scene"], row["size"])
            if key in rows:
                raise SystemExit(f"{path.name}: duplicate {key}")
            rows[key] = row
    return rows


def read_browser(path, mutate):
    if mutate == "missing-browser":
        raise SystemExit("browser result missing (self-test mutation)")
    dom = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, re.S)
    if not match:
        raise SystemExit("browser DOM has no result element")
    text = html.unescape(match.group(1)).strip()
    if not text.startswith("{"):
        raise SystemExit(f"browser result not produced: {text[:160]!r}")
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args()
    build = args.build

    verbatim = read_jsonl(build / "jvm-verbatim.jsonl")
    native = read_jsonl(build / "jvm-native.jsonl")
    doc = read_browser(build / "browser-dom.html", args.mutate)
    browser = {}
    for row in doc['raster']:
        key = row['scene'], row['size']
        if key in browser:
            raise SystemExit('Duplicate browser raster case: ' + str(key))
        browser[key] = row
    if args.mutate == "browser-hash":
        browser[("mesh", "1280x800")]["fnv1a"] = "deadbeef"
    if args.mutate == "zero-timing":
        browser[("mesh", "765x503")]["rasterMedianMs"] = 0

    results = []
    for size in SIZES:
        for scene in SCENES:
            key = (scene, size)
            for name, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
                if key not in rows:
                    raise SystemExit(f"{name}: missing {scene} {size}")
            ref = native[key]
            for name, rows in (("jvm-verbatim", verbatim), ("browser", browser)):
                for field in ("triangles", "covered", "fnv1a", "depthFnv1a"):
                    if rows[key][field] != ref[field]:
                        raise SystemExit(f"{name} {scene} {size}: {field} {rows[key][field]} != native {ref[field]}")
            if ref["covered"] <= 0:
                raise SystemExit(f"{scene} {size}: nothing was drawn")
            b = browser[key]
            for field in ('rasterMinMs', 'rasterMedianMs', 'rasterP90Ms', 'rasterMaxMs', 'clearMedianMs'):
                value = b[field]
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise SystemExit(f'browser {scene} {size}: invalid {field}')
            # One triangle can fall below the browser's 0.1 ms timer step; single64 and mesh must be timeable.
            for field in (() if scene == "single" else ("rasterMinMs", "rasterMedianMs", "rasterP90Ms", "rasterMaxMs")):
                if not b[field] > 0:
                    raise SystemExit(f"browser {scene} {size}: {field} not positive ({b[field]}); timer unusable")
            results.append({
                "scene": scene, "size": size, "triangles": ref["triangles"], "coveredPixels": ref["covered"],
                "colourFnv1a": ref["fnv1a"], "depthFnv1a": ref["depthFnv1a"], "match": "native-jar == jvm-verbatim == wasmgc",
                "wasmRasterMs": {k: b[k] for k in ("rasterMinMs", "rasterMedianMs", "rasterP90Ms", "rasterMaxMs")},
                "samples": b["samples"], "wasmClearMedianMs": b["clearMedianMs"],
                "jvmVerbatimRasterMedianMs": verbatim[key]["rasterMedianMs"],
                "jvmNativeJarRasterMedianMs": native[key]["rasterMedianMs"],
                "jvmVerbatimClearMedianMs": verbatim[key]["clearMedianMs"],
            })
    # The scenes must differ, or a later scene proves nothing beyond the first gate.
    for size in SIZES:
        hashes = {native[(s, size)]["fnv1a"] for s in SCENES}
        if len(hashes) != len(SCENES):
            raise SystemExit(f"{size}: scene hashes are not distinct")

    present = {}
    for row in doc['present']:
        if row['size'] in present:
            raise SystemExit('Duplicate presentation size')
        present[row['size']] = row
    for size in SIZES:
        p = present.get(size)
        if p is None:
            raise SystemExit(f"missing presentation {size}")
        if p["presentedFnv1a"] != p["canvasReadbackFnv1a"]:
            raise SystemExit(f"{size}: canvas readback {p['canvasReadbackFnv1a']} != presented {p['presentedFnv1a']}")
        for field in ("perPixelJsCallMs", "bulkCopyMs", "putImageDataMs"):
            if not p[field]["median"] > 0:
                raise SystemExit(f"{size}: {field} median not positive")

    meta = json.loads((build / "browser-meta.json").read_text(encoding="utf-8"))
    inputs = json.loads((build / "inputs.json").read_text(encoding="utf-8"))
    evidence = {
        "schema": "soloscape.wasm-triangle.evidence/1",
        "inputsSha256": inputs,
        "runtime": doc["runtime"],
        "browser": meta,
        "results": results,
        "presentation": doc["present"],
    }
    (build / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(results)} scene/size cases match across native jar, JVM verbatim and WasmGC; presentation readback ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
