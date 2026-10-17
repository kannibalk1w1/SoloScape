#!/usr/bin/env python3
"""Validate one wasm-face run and write build/evidence.json; exits nonzero on any mismatch.

For each case the native jar bytecode, the extracted JVM build and the TeaVM WasmGC build must agree
ELEMENT FOR ELEMENT on the projected x/y/depth integer arrays and on the framebuffer colour and depth
hashes, with nonzero coverage and at least one culled back face. `--mutate` corrupts one input so the
rejection path can be exercised.
"""
import argparse
import html
import json
import math
import pathlib
import re
import sys

SIZES = ["765x503", "1280x800"]
CASE_NAMES = [f"{base}-{size}" for size in SIZES
              for base in ("cam0-mask0", "cam1-mask0", "cam0-maskbit", "cam0-floatarr", "cam0-mask0-vertex-control")]
MUTATIONS = ("browser-hash", "browser-element", "missing-browser", "zero-coverage", "counter-stub", "counter-adapter",
             "duplicate-case", "control-equal", "no-backface", "missing-present", "culling-equal")
COMPARED = ("projX", "projY", "projZ", "fnv1a", "depthFnv1a", "directFnv1a", "directDepthFnv1a", "allFacesFnv1a",
            "allFacesDepthFnv1a", "allFacesCovered", "covered", "distinct",
            "shortCleared", "byteCleared", "size", "camera", "variant", "control", "vertices", "faces", "front", "back",
            "minDepth")
EXPECT_SHORT = {"mask0": True, "maskbit": False, "floatarr": False}


def fail(message):
    raise SystemExit("FAIL: " + message)


def rows_from_lines(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["case"] in rows:
                fail(f"{path.name}: duplicate case {row['case']}")
            rows[row["case"]] = row
    return rows


def browser_doc(path, mutate):
    if mutate == "missing-browser":
        fail("browser result missing (self-test mutation)")
    if not path.exists():
        fail("browser DOM dump missing")
    dom = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, re.S)
    if not match:
        fail("browser DOM has no result element")
    text = html.unescape(match.group(1)).strip()
    if not text.startswith("{"):
        fail(f"browser result not produced: {text[:200]!r}")
    return json.loads(text)


def fnv(values):
    h = 0x811C9DC5
    for v in values:
        h = ((h ^ (v & 0xFFFFFFFF)) * 0x01000193) & 0xFFFFFFFF
    return f"{h:x}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args()
    build = args.build

    native = rows_from_lines(build / "jvm-native.jsonl")
    verbatim = rows_from_lines(build / "jvm-verbatim.jsonl")
    doc = browser_doc(build / "browser-dom.html", args.mutate)
    browser = {}
    for row in doc["cases"]:
        if row["case"] in browser:
            fail(f"duplicate browser case {row['case']}")
        browser[row["case"]] = row
    mutate = args.mutate
    if mutate == "browser-hash":
        browser["cam1-mask0-1280x800"]["fnv1a"] = "deadbeef"
    if mutate == "browser-element":
        browser["cam0-mask0-765x503"]["projX"][40] += 1
    if mutate == "zero-coverage":
        for rows in (native, verbatim, browser):
            for row in rows.values():
                row["covered"] = 0
    if mutate == "counter-stub":
        browser["cam0-mask0-765x503"]["counters"]["method646"] = 1
    if mutate == "counter-adapter":
        verbatim["cam1-mask0-765x503"]["counters"]["adapterEntries"] = 2
    if mutate == "no-backface":
        for rows in (native, verbatim, browser):
            for row in rows.values():
                row["back"] = 0
    if mutate == "culling-equal":
        for rows in (native, verbatim, browser):
            for row in rows.values():
                row["allFacesFnv1a"], row["allFacesDepthFnv1a"] = row["fnv1a"], row["depthFnv1a"]
                row["allFacesCovered"] = row["covered"]
    if mutate == "duplicate-case":
        doc["cases"].append(dict(doc["cases"][0]))
        if len({r["case"] for r in doc["cases"]}) != len(doc["cases"]):
            fail("duplicate browser case (self-test mutation)")
    if mutate == "control-equal":
        for rows in (native, verbatim, browser):
            for size in SIZES:
                rows[f"cam0-mask0-vertex-control-{size}"].update(
                    {k: rows[f"cam0-mask0-{size}"][k] for k in COMPARED if k not in ("control", "variant")})

    for name, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
        if sorted(rows) != sorted(CASE_NAMES):
            fail(f"{name}: unexpected case set {sorted(set(rows) ^ set(CASE_NAMES))}")

    results = []
    for case in CASE_NAMES:
        ref = native[case]
        for name, rows in (("jvm-verbatim", verbatim), ("browser", browser)):
            for field in COMPARED:
                if rows[case][field] != ref[field]:
                    fail(f"{name} {case}: {field} differs from the native jar reference")
        for name, row in (("jvm-native", ref), ("jvm-verbatim", verbatim[case]), ("browser", browser[case])):
            n = row["vertices"]
            if not (len(row["projX"]) == len(row["projY"]) == len(row["projZ"]) == n > 0):
                fail(f"{name} {case}: projected arrays have the wrong length")
            if row["covered"] <= 0:
                fail(f"{name} {case}: zero coverage")
            if row["back"] < 1 or row["front"] < 1 or row["front"] + row["back"] != row["faces"]:
                fail(f"{name} {case}: back-face culling not exercised or counts inconsistent")
            if -5000 in row["projX"]:
                fail(f"{name} {case}: near-plane miss in projection")
            if row["fnv1a"] != row["directFnv1a"] or row["depthFnv1a"] != row["directDepthFnv1a"]:
                fail(f"{name} {case}: pipeline output differs from the direct front-face fill")
            if row["shortCleared"] != EXPECT_SHORT[row["variant"]] or not row["byteCleared"]:
                fail(f"{name} {case}: adapter side effects differ from the native state-2 expectation")
        for name, row in (("jvm-verbatim", verbatim[case]), ("browser", browser[case])):
            c = row["counters"]
            if c is None or c["adapterEntries"] != 1:
                fail(f"{name} {case}: adapter entry count {c and c['adapterEntries']} != 1")
            for key, value in c.items():
                if key != "adapterEntries" and value != 0:
                    fail(f"{name} {case}: counter {key}={value}; illegal adapter state or stub reached")
        if ref["counters"] is not None:
            fail(f"jvm-native {case}: native run unexpectedly reported counters")
        results.append(case)

    # Anti-bypass: culling must visibly matter. At each size at least one canonical case must render differently
    # with every face drawn (no culling) than with front faces only.
    culling = {}
    for size in SIZES:
        differing = [n for n in (f"cam0-mask0-{size}", f"cam1-mask0-{size}")
                     if native[n]["allFacesFnv1a"] != native[n]["fnv1a"] or native[n]["allFacesDepthFnv1a"] != native[n]["depthFnv1a"]]
        if not differing:
            fail(f"{size}: drawing all faces equals the front-only frame; culling is not shown to affect output")
        culling[size] = differing
    controls = {}
    for size in SIZES:
        base, ctl = native[f"cam0-mask0-{size}"], native[f"cam0-mask0-vertex-control-{size}"]
        if base["projX"] == ctl["projX"]:
            fail(f"{size}: the vertex control did not change the native projection")
        changed = [i for i, (a, b) in enumerate(zip(base["projX"], ctl["projX"])) if a != b]
        if changed != [17]:
            fail(f"{size}: control changed vertices {changed}, expected [17]")
        if base["projY"] != ctl["projY"] or base["projZ"] != ctl["projZ"]:
            fail(f"{size}: control changed y or depth")
        if base["fnv1a"] == ctl["fnv1a"] or base["depthFnv1a"] == ctl["depthFnv1a"]:
            fail(f"{size}: vertex control did not change the framebuffer")
        controls[size] = {"vertex": 17, "nativeProjXBefore": base["projX"][17], "nativeProjXAfter": ctl["projX"][17],
                          "colourFnv1aBefore": base["fnv1a"], "colourFnv1aAfter": ctl["fnv1a"],
                          "depthFnv1aBefore": base["depthFnv1a"], "depthFnv1aAfter": ctl["depthFnv1a"]}
        for a, b in (("cam0-mask0", "cam1-mask0"),):
            if native[f"{a}-{size}"]["fnv1a"] == native[f"{b}-{size}"]["fnv1a"]:
                fail(f"{size}: the two cameras produced the same frame")
    present = doc.get("present", {})
    if mutate == "missing-present":
        present = {}
    hexword = re.compile(r"^[0-9a-f]{1,8}$")
    for key in ("presentedFnv1a", "canvasReadbackFnv1a", "frameFnv1a"):
        if not isinstance(present.get(key), str) or not hexword.match(present[key]):
            fail(f"presentation field {key} missing or not a hash: {present.get(key)!r}")
    if present.get("size") != "1280x800":
        fail("presentation size missing or wrong")
    whole = doc.get("wholeMatrixMs")
    if isinstance(whole, bool) or not isinstance(whole, (int, float)) or not math.isfinite(whole) or whole <= 0:
        fail(f"wholeMatrixMs missing or not finite positive: {whole!r}")
    if present.get("presentedFnv1a") != present.get("canvasReadbackFnv1a"):
        fail(f"canvas readback {present.get('canvasReadbackFnv1a')} != presented {present.get('presentedFnv1a')}")
    if present.get("frameFnv1a") != native["cam1-mask0-1280x800"]["fnv1a"]:
        fail("presented frame differs from the native cam1 1280x800 frame")

    meta = json.loads((build / "browser-meta.json").read_text(encoding="utf-8"))
    inputs = json.loads((build / "inputs.json").read_text(encoding="utf-8"))
    toolchain = json.loads((build / "toolchain.json").read_text(encoding="utf-8"))
    summary = []
    for case in CASE_NAMES:
        row = native[case]
        entry = {k: row[k] for k in ("case", "size", "camera", "variant", "control", "vertices", "faces", "front", "back",
                                     "minDepth", "covered", "distinct", "fnv1a", "depthFnv1a", "directFnv1a",
                                     "directDepthFnv1a", "allFacesFnv1a", "allFacesDepthFnv1a", "allFacesCovered", "shortCleared",
                                     "byteCleared")}
        entry.update({"projXFnv1a": fnv(row["projX"]), "projYFnv1a": fnv(row["projY"]), "projZFnv1a": fnv(row["projZ"]),
                      "match": "native-jar == jvm-extracted == wasmgc, projected arrays element for element",
                      "extractedCounters": verbatim[case]["counters"], "wasmCounters": browser[case]["counters"]})
        if case in ("cam0-mask0-765x503", "cam1-mask0-765x503"):
            entry["projX"], entry["projY"], entry["projZ"] = row["projX"], row["projY"], row["projZ"]
        summary.append(entry)
    evidence = {
        "schema": "soloscape.wasm-face.evidence/1",
        "inputsSha256": inputs,
        "toolchain": toolchain,
        "browser": meta,
        "cases": summary,
        "vertexControls": controls,
        "cullingAffectsOutput": culling,
        "presentation": present,
        "wasmWholeMatrixMs": doc.get("wholeMatrixMs"),
    }
    (build / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(results)} cases match across native jar, JVM extracted and WasmGC "
          f"(projected arrays element for element, colour/depth hashes, adapter side effects, counters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
