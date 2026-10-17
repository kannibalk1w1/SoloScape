#!/usr/bin/env python3
"""Checks decoded-model bridge evidence from the native jar, the extracted JVM and TeaVM WasmGC.

Inputs (build/): fixtures.json (the original designs and their expected arrays, written by the encoder), native.json,
extracted-jvm.json and browser/browser-dom.html (the JSON result inside the page). Nothing is taken from one runtime
to check another, except the cross-runtime equality the bridge is meant to prove.

Checks, in order: exact fixture/size/camera case sets; decoded arrays and counts against the original design;
front/back culling recomputed from the projected coordinates; counters (zero adapter/stub/decode-stub calls on the
extracted and browser runs, absent on the native jar); element-wise projected XYZ and colour/depth hashes across the
three runtimes; the palette against the independently computed original synthetic palette; the perturbations visibly
changing output; the direct re-render and the all-faces bypass; and the presented frame (native == extracted == browser
readback).

--mutate NAME corrupts one collected value before the checks, so the checker must exit 1 with a FAIL: line:
decoded-array | browser-projected | browser-frame | palette.
Exit 0 on a full pass, 1 on any failed check, 2 on bad arguments (argparse) which are not counted as rejections.
"""
import argparse
import html
import json
import pathlib
import re
import sys

FIXTURES = ["tetra", "tetra_vertex", "tetra_colour"]
SIZES = ["765x503", "1280x800"]
CAMERAS = [0, 1]
NEAR = 50
NATIVE, EXTRACTED, BROWSER = "native-jar", "extracted-jvm", "teavm-0.16.0-wasmgc"
RUNTIMES = (NATIVE, EXTRACTED, BROWSER)
MUTATIONS = ("decoded-array", "browser-projected", "browser-frame", "palette")
MASK32 = 0xFFFFFFFF
BACKGROUND = 0xFF102030
COUNTER_KEYS = ("adapterEntries", "adapterIllegal", "method646", "method658", "method3720", "method3645",
                "method1022", "method1024")


def fail(message):
    print("FAIL: " + message)
    sys.exit(1)


def fnv(values):
    h = 0x811C9DC5
    for value in values:
        h = ((h ^ (value & MASK32)) * 0x01000193) & MASK32
    return f"{h:x}"


def original_palette_fnv():
    # The original synthetic palette (FaceMesh.palette), recomputed here from its published formula.
    values = []
    for i in range(65536):
        x = (i * 0x9E3779B1) & MASK32
        x ^= x >> 15
        x = (x * 0x85EBCA6B) & MASK32
        x ^= x >> 13
        p = 0xFF000000 | (x & 0xFFFFFF)
        if p == BACKGROUND:
            p ^= 1
        values.append(p)
    return fnv(values)


def signed_short(value):
    return value - 65536 if value >= 32768 else value


def load_browser(path):
    dom = path.read_text(encoding="utf-8")
    match = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, re.S)
    if not match:
        fail("browser DOM has no result element")
    text = html.unescape(match.group(1)).strip()
    if text.startswith("FAIL:"):
        fail("browser run reported: " + text[:300])
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        fail(f"browser result is not the expected JSON: {error}")


def mutate(docs, name):
    if name == "decoded-array":
        docs[NATIVE]["cases"][0]["decoded"]["y"][0] += 1
    elif name == "browser-projected":
        docs[BROWSER]["cases"][0]["projX"][0] += 1
    elif name == "browser-frame":
        value = int(docs[BROWSER]["cases"][0]["fnv1a"], 16) ^ 1
        docs[BROWSER]["cases"][0]["fnv1a"] = f"{value:x}"
    elif name == "palette":
        value = int(docs[BROWSER]["palette"]["fnv1a"], 16) ^ 1
        docs[BROWSER]["palette"]["fnv1a"] = f"{value:x}"


def expected_case_names():
    return [f"{fixture}-cam{camera}-{size}" for fixture in FIXTURES for camera in CAMERAS for size in SIZES]


def check_design(name, record, case):
    # Decoded arrays and counts against the declared design (never against another runtime).
    exp = record["expected"]
    d = case["decoded"]
    if d["vertexCount"] != exp["vertexCount"] or d["faceCount"] != exp["faceCount"]:
        fail(f"{name}: decoded counts {d['vertexCount']}/{d['faceCount']} differ from the design")
    if d["maxVertexPlusOne"] != exp["maxVertexPlusOne"]:
        fail(f"{name}: maxVertexPlusOne {d['maxVertexPlusOne']} differs from the design")
    for key in ("x", "y", "z", "a", "b", "c"):
        if d[key] != exp[key]:
            fail(f"{name}: decoded {key} {d[key]} differs from the design {exp[key]}")
    if d["colour"] != [signed_short(v) for v in exp["colour"]]:
        fail(f"{name}: decoded colour shorts differ from the design")
    if [v & 0xFFFF for v in d["colourIndex"]] != exp["colour"]:
        fail(f"{name}: colourIndex (decoded short & 0xffff) differs from the design colours")


def check_projection(name, record, case):
    # Front/back classification recomputed from the projected coordinates with the scene's own formula.
    x, y, z = case["projX"], case["projY"], case["projZ"]
    vertices = record["expected"]["vertexCount"]
    if len(x) != vertices or len(y) != vertices or len(z) != vertices:
        fail(f"{name}: projected arrays are not {vertices} long")
    if case["vertices"] != vertices or case["faces"] != record["expected"]["faceCount"]:
        fail(f"{name}: scene counts differ from the design")
    if min(z) != case["minDepth"] or min(z) < NEAR:
        fail(f"{name}: minDepth {case['minDepth']} (projected minimum {min(z)}) is not a valid near-plane depth")
    front = 0
    for _, a, b, k in record["design"]["faces"]:
        area = (x[a] - x[b]) * (y[k] - y[b]) - (y[a] - y[b]) * (x[k] - x[b])
        if area > 0:
            front += 1
    if case["front"] != front or case["back"] != len(record["design"]["faces"]) - front:
        fail(f"{name}: front/back {case['front']}/{case['back']} differ from the recomputed {front}")
    if front < 1 or case["back"] < 1:
        fail(f"{name}: back-face culling not exercised (front {front}, back {case['back']})")
    if case["covered"] <= 0:
        fail(f"{name}: zero coverage")
    if case["directFnv1a"] != case["fnv1a"] or case["directDepthFnv1a"] != case["depthFnv1a"]:
        fail(f"{name}: direct front-face re-render differs from the pipeline")
    if not case["shortCleared"] or not case["byteCleared"]:
        fail(f"{name}: adapter side effects missing")


def check_counters(runtime, name, case):
    if runtime == NATIVE:
        if case["counters"] is not None or case["decodeStubCalls"] is not None:
            fail(f"{name}: native run reports counters (must be absent)")
        return
    counters = case["counters"]
    if counters is None:
        fail(f"{name}: {runtime} run reports no counters")
    if counters["adapterEntries"] != 1:
        fail(f"{name}: adapter entries {counters['adapterEntries']} (expected exactly 1)")
    for key in COUNTER_KEYS[1:]:
        if counters[key] != 0:
            fail(f"{name}: {runtime} {key} = {counters[key]} (expected 0)")
    if case["decodeStubCalls"] != 0:
        fail(f"{name}: {runtime} decode stub calls {case['decodeStubCalls']} (expected 0)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args()
    build = args.build

    records = {r["name"]: r for r in json.loads((build / "fixtures.json").read_text(encoding="utf-8"))}
    if sorted(records) != sorted(FIXTURES):
        fail(f"fixture set {sorted(records)} differs from {sorted(FIXTURES)}")
    docs = {
        NATIVE: json.loads((build / "native.json").read_text(encoding="utf-8")),
        EXTRACTED: json.loads((build / "extracted-jvm.json").read_text(encoding="utf-8")),
        BROWSER: load_browser(build / "browser" / "browser-dom.html"),
    }
    if args.mutate:
        mutate(docs, args.mutate)

    expected_names = expected_case_names()
    by_runtime = {}
    for runtime in RUNTIMES:
        doc = docs[runtime]
        if doc.get("runtime") != runtime:
            fail(f"{runtime}: wrong runtime label {doc.get('runtime')!r}")
        if doc["palette"]["fnv1a"] != original_palette_fnv():
            fail(f"{runtime}: palette {doc['palette']['fnv1a']} is not the original synthetic palette")
        names = [case["name"] for case in doc["cases"]]
        if sorted(names) != sorted(expected_names) or len(names) != len(set(names)):
            fail(f"{runtime}: case set {sorted(names)} differs from the expected {sorted(expected_names)}")
        by_runtime[runtime] = {case["name"]: case for case in doc["cases"]}

    for name in expected_names:
        fixture = name.split("-cam")[0]
        record = records[fixture]
        for runtime in RUNTIMES:
            case = by_runtime[runtime][name]
            expected_camera = int(name.split("-cam", 1)[1].split("-", 1)[0])
            expected_size = name.rsplit("-", 1)[1]
            if case["camera"] != expected_camera or case["size"] != expected_size:
                fail(f"{name}: recorded camera/size do not match the declared case")
            if case["fixture"] != fixture or case["variant"] != "mask0":
                fail(f"{name}: {runtime} recorded fixture/variant {case['fixture']}/{case['variant']}")
            check_design(f"{runtime} {name}", record, case)
            check_projection(f"{runtime} {name}", record, case)
            check_counters(runtime, f"{runtime} {name}", case)

        reference = by_runtime[NATIVE][name]
        for runtime in (EXTRACTED, BROWSER):
            other = by_runtime[runtime][name]
            for key in ("decoded", "projX", "projY", "projZ", "front", "back", "minDepth", "covered", "distinct",
                        "fnv1a", "depthFnv1a", "directFnv1a", "directDepthFnv1a", "allFacesFnv1a",
                        "allFacesDepthFnv1a", "allFacesCovered"):
                if other[key] != reference[key]:
                    fail(f"{name}: {runtime} {key} differs from the native jar")

    # Presented frame: the same RGBA frame on all three, and the browser canvas readback equals its frame hash.
    presented = {runtime: docs[runtime]["presented"] for runtime in RUNTIMES}
    for runtime in RUNTIMES:
        shown = presented[runtime]
        if (shown.get("fixture"), shown.get("size"), shown.get("camera")) != ("tetra", "1280x800", 1):
            fail(f"{runtime}: presented frame does not identify the intended canonical case")
        if shown["frameFnv1a"] != by_runtime[runtime]["tetra-cam1-1280x800"]["fnv1a"]:
            fail(f"{runtime}: presented frame is not the canonical pipeline output")
        if presented[runtime]["rgbaFnv1a"] != presented[NATIVE]["rgbaFnv1a"]:
            fail(f"presented RGBA frame of {runtime} differs from the native jar")
        if presented[runtime]["frameFnv1a"] != presented[NATIVE]["frameFnv1a"]:
            fail(f"presented ARGB frame of {runtime} differs from the native jar")
    if presented[BROWSER]["canvasReadbackFnv1a"] != presented[BROWSER]["rgbaFnv1a"]:
        fail("browser canvas readback differs from the presented frame")

    # Perturbations must visibly change native output. Camera branches must be observably distinct.
    for size in SIZES:
        first = by_runtime[NATIVE][f"tetra-cam0-{size}"]
        second = by_runtime[NATIVE][f"tetra-cam1-{size}"]
        if (first["projX"], first["projY"], first["projZ"]) == (second["projX"], second["projY"], second["projZ"]):
            fail(f"native camera branches produce identical projected arrays at {size}")
    for camera in CAMERAS:
        for size in SIZES:
            base = by_runtime[NATIVE][f"tetra-cam{camera}-{size}"]
            vertex = by_runtime[NATIVE][f"tetra_vertex-cam{camera}-{size}"]
            colour = by_runtime[NATIVE][f"tetra_colour-cam{camera}-{size}"]
            if vertex["projX"] == base["projX"] or vertex["fnv1a"] == base["fnv1a"]:
                fail(f"vertex perturbation does not change native output (cam{camera} {size})")
            if colour["fnv1a"] == base["fnv1a"]:
                fail(f"colour perturbation does not change native output (cam{camera} {size})")
    # The bypass must visibly differ on canonical cases: at least one tetra case per size. The camera-1 cases have a
    # single back face that the depth test already hides, so their bypass equals the culled frame; that is recorded,
    # not hidden, and is listed in the summary.
    bypass_differs, bypass_equal = [], []
    for size in SIZES:
        for camera in CAMERAS:
            case = by_runtime[NATIVE][f"tetra-cam{camera}-{size}"]
            (bypass_equal if case["allFacesFnv1a"] == case["fnv1a"] else bypass_differs).append(f"cam{camera}-{size}")
        if not any(name.endswith(size) for name in bypass_differs):
            fail(f"all-faces bypass equals the front-only frame in every canonical case at {size}")

    summary = {
        "cases": len(expected_names),
        "runtimes": list(RUNTIMES),
        "palette": docs[NATIVE]["palette"]["fnv1a"],
        "presentedRgbaFnv1a": presented[NATIVE]["rgbaFnv1a"],
        "canvasReadbackFnv1a": presented[BROWSER]["canvasReadbackFnv1a"],
        "bypassDiffersFromCulledFrame": bypass_differs,
        "bypassEqualToCulledFrame": bypass_equal,
        "mutation": args.mutate or "none",
    }
    if not args.mutate:
        (build / "checker-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("PASS: " + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
