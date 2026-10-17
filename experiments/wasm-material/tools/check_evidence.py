#!/usr/bin/env python3
"""Validate one wasm-material run and write build/evidence.json; exits nonzero on any problem.

For each scene and size the native jar bytecode, the extracted JVM build and the TeaVM WasmGC build
must agree on triangle count, fallback count, covered pixels, distinct colours, colour hash and
depth-buffer hash. Negative controls (a different palette or texel variant) must change the pixels
identically on all three runtimes and differ from the reference scene, which a flat-fill stand-in
could not satisfy. The canvas readback of the presented frame must equal the words handed to
putImageData. `--mutate` is a self-test hook that corrupts one input so rejection can be exercised.
"""
import argparse
import html
import json
import math
import pathlib
import re
import sys

SIZES = ["765x503", "1280x800"]
SCENES = ["shaded", "gouraud", "tex1", "tex3", "mixed"]
CONTROLS = {"shaded-palette-control": "shaded", "tex1-texel-control": "tex1", "tex3-texel-control": "tex3"}
MUTATIONS = ("browser-hash", "missing-browser", "zero-timing", "flat-standin", "duplicate-case", "nan-timing",
             "control-equal")
# A flat-colour stand-in produces a few hundred values at most; real interpolation produces tens of thousands.
MIN_DISTINCT = {"shaded": 10000, "gouraud": 10000, "tex1": 10000, "tex3": 50000, "mixed": 10000}
EXPECTED_SAMPLES = 15
TIMING_FIELDS = ("rasterMinMs", "rasterMedianMs", "rasterP90Ms", "rasterMaxMs")


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


def index(rows, label):
    out = {}
    for row in rows:
        key = (row["scene"], row["size"])
        if key in out:
            raise SystemExit(f"{label}: duplicate case {key}")
        out[key] = row
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args()
    build = args.build

    verbatim = read_jsonl(build / "jvm-verbatim.jsonl")
    native = read_jsonl(build / "jvm-native.jsonl")
    doc = read_browser(build / "browser-dom.html", args.mutate)
    if args.mutate == "duplicate-case":
        doc["raster"].append(dict(doc["raster"][0]))
    browser = index(doc["raster"], "browser")
    browser_controls = index(doc.get("controls", []), "browser controls")
    if args.mutate == "browser-hash":
        browser[("tex3", "1280x800")]["fnv1a"] = "deadbeef"
    if args.mutate == "zero-timing":
        browser[("tex1", "765x503")]["rasterMedianMs"] = 0
    if args.mutate == "nan-timing":
        browser[("mixed", "765x503")]["rasterMedianMs"] = float("nan")
    if args.mutate == "flat-standin":
        # A flat fill would cover the same pixels but with a handful of colours.
        for runtime in (browser, native, verbatim):
            runtime[("tex3", "765x503")]["distinct"] = 12
    if args.mutate == "control-equal":
        for runtime in (browser_controls, native, verbatim):
            runtime[("tex1-texel-control", "765x503")]["fnv1a"] = browser[("tex1", "765x503")]["fnv1a"]

    expected_cases = {(scene, size) for scene in SCENES for size in SIZES}
    expected_controls = {(control, size) for control in CONTROLS for size in SIZES}
    for label, actual, expected in (("native", set(native), expected_cases | expected_controls),
                                     ("verbatim", set(verbatim), expected_cases | expected_controls),
                                     ("browser", set(browser), expected_cases),
                                     ("browser controls", set(browser_controls), expected_controls)):
        if actual != expected:
            raise SystemExit(f"{label}: unexpected/missing case identities: {actual ^ expected}")

    results = []
    for size in SIZES:
        for scene in SCENES:
            key = (scene, size)
            for name, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
                if key not in rows:
                    raise SystemExit(f"{name}: missing {scene} {size}")
            ref = native[key]
            for name, rows in (("jvm-verbatim", verbatim), ("browser", browser)):
                for field in ("triangles", "fallbackTriangles", "covered", "distinct", "fnv1a", "depthFnv1a"):
                    if rows[key][field] != ref[field]:
                        raise SystemExit(f"{name} {scene} {size}: {field} {rows[key][field]} != native {ref[field]}")
            if ref["covered"] <= 0 or ref["triangles"] <= 0:
                raise SystemExit(f"{scene} {size}: nothing was drawn")
            if ref["distinct"] < MIN_DISTINCT[scene]:
                raise SystemExit(f"{scene} {size}: only {ref['distinct']} distinct colours; looks like a flat fill")
            if scene in ("tex1", "tex3", "mixed") and ref["fallbackTriangles"] <= 0:
                raise SystemExit(f"{scene} {size}: the null-texture fallback path was not exercised")
            b = browser[key]
            for name, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
                n = rows[key]["samples"]
                if not isinstance(n, int) or n != EXPECTED_SAMPLES:
                    raise SystemExit(f"{name} {scene} {size}: sample count {n!r} != {EXPECTED_SAMPLES}")
            for name, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
                measured = rows[key]
                for field in TIMING_FIELDS + ("clearMedianMs",):
                    value = measured[field]
                    floor = 0 if field == "clearMedianMs" else 1e-9
                    if not isinstance(value, (int, float)) or not math.isfinite(value) or value < floor:
                        raise SystemExit(f"{name} {scene} {size}: invalid {field} ({value})")
                if not measured["rasterMinMs"] <= measured["rasterMedianMs"] <= measured["rasterP90Ms"] <= measured["rasterMaxMs"]:
                    raise SystemExit(f"{name} {scene} {size}: timing statistics are not ordered")
            results.append({
                "scene": scene, "size": size, "triangles": ref["triangles"],
                "nullTextureFallbackTriangles": ref["fallbackTriangles"], "coveredPixels": ref["covered"],
                "distinctColours": ref["distinct"], "colourFnv1a": ref["fnv1a"], "depthFnv1a": ref["depthFnv1a"],
                "match": "native-jar == jvm-verbatim == wasmgc",
                "wasmRasterMs": {k: b[k] for k in TIMING_FIELDS}, "samples": b["samples"],
                "wasmClearMedianMs": b["clearMedianMs"],
                "jvmVerbatimRasterMedianMs": verbatim[key]["rasterMedianMs"],
                "jvmNativeJarRasterMedianMs": native[key]["rasterMedianMs"],
            })
        hashes = {native[(s, size)]["fnv1a"] for s in SCENES}
        if len(hashes) != len(SCENES):
            raise SystemExit(f"{size}: scene hashes are not distinct")

    controls = []
    for size in SIZES:
        for control, base in CONTROLS.items():
            key = (control, size)
            for name, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser_controls)):
                if key not in rows:
                    raise SystemExit(f"{name}: missing control {control} {size}")
            hashes = {native[key]["fnv1a"], verbatim[key]["fnv1a"], browser_controls[key]["fnv1a"]}
            if len(hashes) != 1:
                raise SystemExit(f"{control} {size}: runtimes disagree {sorted(hashes)}")
            reference = native[(base, size)]["fnv1a"]
            if native[key]["fnv1a"] == reference:
                raise SystemExit(f"{control} {size}: changing the {'palette' if 'palette' in control else 'texels'}"
                                 " did not change the pixels; the fill is not sampling it")
            controls.append({"control": control, "size": size, "baseScene": base,
                             "referenceFnv1a": reference, "variantFnv1a": native[key]["fnv1a"],
                             "match": "native-jar == jvm-verbatim == wasmgc, and differs from the reference"})

    present = index([dict(r, scene="present") for r in doc["present"]], "presentation")
    for size in SIZES:
        p = present.get(("present", size))
        if p is None:
            raise SystemExit(f"missing presentation {size}")
        if p["presentedFnv1a"] != p["canvasReadbackFnv1a"]:
            raise SystemExit(f"{size}: canvas readback {p['canvasReadbackFnv1a']} != presented {p['presentedFnv1a']}")

    meta = json.loads((build / "browser-meta.json").read_text(encoding="utf-8"))
    inputs = json.loads((build / "inputs.json").read_text(encoding="utf-8"))
    toolchain = json.loads((build / "toolchain.json").read_text(encoding="utf-8"))
    evidence = {
        "schema": "soloscape.wasm-material.evidence/1",
        "inputsSha256": inputs,
        "toolchain": toolchain,
        "runtime": doc["runtime"],
        "browser": meta,
        "results": results,
        "negativeControls": controls,
        "presentation": doc["present"],
    }
    (build / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(results)} scene/size cases and {len(controls)} controls match across native jar, "
          "JVM verbatim and WasmGC; presentation readback ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
