#!/usr/bin/env python3
"""Validate one clip-mode run (FACE_CLIP=1) and write build-clip/clip-evidence.json; exits nonzero on any mismatch.

Clip eligibility and the expected method646 output counts are derived HERE, in Python, from the native jar's projected
and camera-space arrays. The native jar has no counters, so these derivations are the reference. Each extracted build
(JVM and WasmGC) must reproduce them, and must agree with the native arrays element for element.

  * eligibility: a face with any behind vertex (projected x == -5000) whose camera-space triple product, computed with
    Java's int semantics, is positive (method643: dot = B . ((A - B) x (C - B)) > 0);
  * outputs: 0 front vertices -> nothing (index 0), 1 -> triangle (index 3), 2 -> quad (index 4);
  * model rejection: method654 skips the projection body when the model bound 2400 + 0.6 * y + radius is <= 50.
"""
import argparse
import html
import json
import math
import pathlib
import re
import sys

SIZES = ["765x503", "1280x800"]
NEAR = 50
ZERO = [0, 0, 0, 0, 0]
# name -> expected clipOut counts (index 0: no output, 3: triangle, 4: quad), whether the model is rejected,
# and whether the frame must show drawn pixels. These are the designed intent; the derived oracle must match them.
EXPECT = {
    "one-behind-quad": {"clip": [0, 0, 0, 0, 1], "rejected": False, "covered": True},
    "one-behind-quad-reversed": {"clip": ZERO, "rejected": False, "covered": False},
    "two-behind-triangle": {"clip": [0, 0, 0, 1, 0], "rejected": False, "covered": True},
    "two-behind-triangle-reversed": {"clip": ZERO, "rejected": False, "covered": False},
    "exact-near-50": {"clip": ZERO, "rejected": False, "covered": True},
    "crossing-49.8-behind": {"clip": [0, 0, 0, 0, 1], "rejected": False, "covered": True},
    "crossing-50.2-front": {"clip": ZERO, "rejected": False, "covered": True},
    "model-all-behind": {"clip": ZERO, "rejected": True, "covered": False},
    "face-all-behind-companion": {"clip": [1, 0, 0, 0, 0], "rejected": False, "covered": True},
}
# Labelled threshold vertices: name -> (vertex index, integer camera depth, behind the near plane).
EXACT_VERTEX = {"exact-near-50": (2, 50, False), "crossing-49.8-behind": (2, 49, True),
                "crossing-50.2-front": (2, 50, False)}
COMPARED = ("vertexCount", "faceCount", "projX", "projY", "projZ", "camX", "camY", "camD", "fnv1a", "depthFnv1a",
            "covered")  # adapter counts are compared through the extracted counters only: the native jar has none
# Designed flat-fill entries (method1018 calls): quad = 2 clip fills, triangle = 1, regular front face = 1, culled or rejected = 0.
FILLS = {"one-behind-quad": 2, "one-behind-quad-reversed": 0, "two-behind-triangle": 1,
         "two-behind-triangle-reversed": 0, "exact-near-50": 1, "crossing-49.8-behind": 2,
         "crossing-50.2-front": 1, "model-all-behind": 0, "face-all-behind-companion": 1}
MUTATIONS = ("clip-count", "clip-visible", "clip-browser-element", "clip-fill-count")
INT_MIN, INT_MAX = -2 ** 31, 2 ** 31 - 1
BACKGROUND = 0xff102030


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


def browser_rows(path, mutate):
    if not path.exists():
        fail("browser DOM dump missing")
    dom = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, re.S)
    if not match:
        fail("browser DOM has no result element")
    text = html.unescape(match.group(1)).strip()
    if not text.startswith("{"):
        fail(f"browser result not produced: {text[:200]!r}")
    doc = json.loads(text)
    rows = {}
    for row in doc["cases"]:
        if row["case"] in rows:
            fail(f"duplicate browser case {row['case']}")
        rows[row["case"]] = row
    return rows


def wrap32(v):
    return ((v + 2 ** 31) % 2 ** 32) - 2 ** 31


def analytic_bound(vertices):
    """method655 / method654 model bound: i637 = max(int(2400 + 0.6 minY), int(2400 + 0.6 maxY)) + radius."""
    ys = [v[1] for v in vertices]
    radius = int(math.sqrt(max(v[0] * v[0] + v[2] * v[2] for v in vertices)) + 0.99)
    i634 = int(2400 + 0.6 * min(ys))
    i635 = int(2400 + 0.6 * max(ys))
    i636 = min(i634, i635) - radius
    i637 = max(i634, i635) + radius
    return i636, i637


def i32(value, what):
    """Java int semantics: every intermediate must already be in range, so no wraparound can differ from exact math."""
    if not INT_MIN <= value <= INT_MAX:
        fail(f"int overflow at {what}: {value} (oracle would not equal Java int arithmetic)")
    return value


def triple_dot(row, a, b, c, name, face):
    """method643 with int semantics, checked at each subtraction, product and sum."""
    cx, cy, cd = row["camX"], row["camY"], row["camD"]
    ux = i32(cx[a] - cx[b], f"{name} face {face} ux"); uy = i32(cy[a] - cy[b], f"{name} face {face} uy")
    ud = i32(cd[a] - cd[b], f"{name} face {face} ud")
    vx = i32(cx[c] - cx[b], f"{name} face {face} vx"); vy = i32(cy[c] - cy[b], f"{name} face {face} vy")
    vd = i32(cd[c] - cd[b], f"{name} face {face} vd")
    p1, p2 = i32(uy * vd, f"{name} face {face} uy*vd"), i32(ud * vy, f"{name} face {face} ud*vy")
    nx = i32(p1 - p2, f"{name} face {face} nx")
    p3, p4 = i32(ud * vx, f"{name} face {face} ud*vx"), i32(ux * vd, f"{name} face {face} ux*vd")
    ny = i32(p3 - p4, f"{name} face {face} ny")
    p5, p6 = i32(ux * vy, f"{name} face {face} ux*vy"), i32(uy * vx, f"{name} face {face} uy*vx")
    nz = i32(p5 - p6, f"{name} face {face} nz")
    t1 = i32(cx[b] * nx, f"{name} face {face} xb*nx")
    t2 = i32(cy[b] * ny, f"{name} face {face} yb*ny")
    t3 = i32(cd[b] * nz, f"{name} face {face} db*nz")
    s12 = i32(t1 + t2, f"{name} face {face} sum12")
    return i32(s12 + t3, f"{name} face {face} dot")


def area2d(row, a, b, c, name, face):
    """method643's flat-path test: (Xa-Xb)*(Yc-Yb) - (Ya-Yb)*(Xc-Xb) > 0, on the projected arrays, with int checks."""
    x, y = row["projX"], row["projY"]
    t1 = i32(i32(x[a] - x[b], f"{name} face {face} area dxab") * i32(y[c] - y[b], f"{name} face {face} area dyc"),
             f"{name} face {face} area p1")
    t2 = i32(i32(y[a] - y[b], f"{name} face {face} area dyab") * i32(x[c] - x[b], f"{name} face {face} area dxc"),
             f"{name} face {face} area p2")
    return i32(t1 - t2, f"{name} face {face} area")


def derive(name, row):
    """Independent oracle: rejection, behind flags, eligibility, clip outputs and flat-fill entries from the native arrays."""
    vertices, faces = row["vertices"], row["faces"]
    n = len(vertices)
    i636, i637 = analytic_bound(vertices)
    rejected = not (i636 < 100000 and i637 > NEAR)
    if rejected:
        return {"rejected": True, "behind": None, "eligible": [], "clip": ZERO, "fills": 0, "normalFills": 0,
                "clipFills": 0, "boundI636": i636, "boundI637": i637}
    # Analytic camera-space check for camera 0 (x = x, y = 0.8 y - 0.6 z, depth = 2400 + 0.6 y + 0.8 z).
    for i, (x, y, z) in enumerate(vertices):
        if row["camX"][i] != x:
            fail(f"{name}: camX[{i}]={row['camX'][i]} != {x}")
        # The integer cast truncates toward zero (error < 1) and float rounding adds about 1e-4 at these magnitudes.
        if abs(row["camY"][i] - (0.8 * y - 0.6 * z)) > 1.001 or abs(row["camD"][i] - (2400 + 0.6 * y + 0.8 * z)) > 1.001:
            fail(f"{name}: camera arrays at vertex {i} deviate from the analytic camera transform")
    behind = [row["camD"][i] < NEAR for i in range(n)]
    for i in range(n):
        if (row["projX"][i] == -5000) != behind[i]:
            fail(f"{name}: vertex {i} projected sentinel disagrees with the integer depth threshold")
    eligible, clip, normal = [], [0] * 5, 0
    for f, (a, b, c) in enumerate(faces):
        if not any(behind[v] for v in (a, b, c)):
            if area2d(row, a, b, c, name, f) > 0:
                normal += 1
            continue
        dot = triple_dot(row, a, b, c, name, f)
        if dot > 0:
            front = sum(1 for v in (a, b, c) if not behind[v])
            index = {0: 0, 1: 3, 2: 4}.get(front)
            if index is None:
                fail(f"{name}: eligible face {f} has three front vertices")
            clip[index] += 1
            eligible.append({"face": f, "frontVertices": front, "dot": dot})
    clip_fills = 2 * clip[4] + clip[3]
    return {"rejected": False, "behind": behind, "eligible": eligible, "clip": clip,
            "fills": normal + clip_fills, "normalFills": normal, "clipFills": clip_fills,
            "boundI636": i636, "boundI637": i637}


def check_row(name, size, native, verbatim, browser):
    """Cross-runtime equality, oracle agreement and the labelled expectation for one case."""
    expect = EXPECT[name]
    oracle = derive(name, native)
    if oracle["fills"] != FILLS[name]:
        fail(f"{name} {size}: derived fill entries {oracle['fills']} != designed {FILLS[name]}")
    if native["flatFillEntries"] is not None:
        fail(f"jvm-native {name} {size}: flat-fill entries reported; the native jar is uninstrumented")
    if name in EXACT_VERTEX:
        index, depth, behind = EXACT_VERTEX[name]
        if native["camD"][index] != depth or (native["projX"][index] == -5000) != behind:
            fail(f"{name} {size}: threshold vertex {index} depth {native['camD'][index]} / "
                 f"behind={native['projX'][index] == -5000}, designed depth {depth} behind={behind}")
    if oracle["clip"] != expect["clip"]:
        fail(f"{name} {size}: derived clip counts {oracle['clip']} != designed {expect['clip']}")
    if oracle["rejected"] != expect["rejected"]:
        fail(f"{name} {size}: model rejected={oracle['rejected']} but designed {expect['rejected']}")
    for label, row in (("jvm-verbatim", verbatim), ("browser", browser)):
        for field in COMPARED:
            if row[field] != native[field]:
                fail(f"{label} {name} {size}: {field} differs from the native jar reference")
        if row["vertices"] != native["vertices"] or row["faces"] != native["faces"]:
            fail(f"{label} {name} {size}: geometry differs")
    for label, row in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
        n = native["vertexCount"]
        if len(native["camX"]) != n or len(native["projX"]) != n or n <= 0:
            fail(f"{label} {name} {size}: wrong array lengths")
        if expect["rejected"]:
            for field in ("projX", "projY", "projZ", "camX", "camY", "camD"):
                if any(row[field]):
                    fail(f"{label} {name} {size}: rejected model wrote {field}")
            if row["covered"] != 0:
                fail(f"{label} {name} {size}: rejected model drew pixels")
        if (row["covered"] > 0) != expect["covered"]:
            fail(f"{label} {name} {size}: covered={row['covered']} but designed covered={expect['covered']}")
    for label, row in (("jvm-verbatim", verbatim), ("browser", browser)):
        c = row["counters"]
        if c is None:
            fail(f"{label} {name} {size}: counters missing")
        expect_adapter = 0 if expect["rejected"] else 1
        if c["adapterEntries"] != expect_adapter or c["adapterIllegal"] != 0:
            fail(f"{label} {name} {size}: adapter entries {c['adapterEntries']} != {expect_adapter}")
        for key, value in c.items():
            if key != "adapterEntries" and value != 0:
                fail(f"{label} {name} {size}: counter {key}={value}; illegal path or stub reached")
        clip_out = row["clipOut"]
        if row["flatFillEntries"] != oracle["fills"]:
            fail(f"{label} {name} {size}: flatFillEntries {row['flatFillEntries']} != derived {oracle['fills']}")
        if clip_out != oracle["clip"]:
            fail(f"{label} {name} {size}: clipOut {clip_out} != derived {oracle['clip']}")
    if native["counters"] is not None or native.get("clipOutNative") is not True:
        fail(f"jvm-native {name} {size}: native reference unexpectedly reported counters")
    return oracle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args()
    build, mutate = args.build, args.mutate

    closure = json.loads((build / "closure.json").read_text(encoding="utf-8"))
    if closure.get("clip_mode") is not True:
        fail("closure.json is not a clip-mode extraction")
    if closure["class64_sub1_verbatim_lines"] > closure["class64_sub1_line_budget"] or closure["class64_sub1_line_budget"] != 580:
        fail("clip closure exceeds the 580-line budget")
    if closure["class64_sub1_native_instance_fields_kept"] > 65:
        fail("clip closure exceeds the 65-field budget")
    if closure.get("class109_non_verbatim_lines") != 1 or closure.get("class64_sub1_non_verbatim_lines") != 1:
        fail("closure metadata must declare exactly one non-verbatim line in Class64_Sub1 and one in Class109")
    if "Class64_Sub1.method646" in closure["stubs"]:
        fail("method646 is still a stub in clip mode")

    native = rows_from_lines(build / "jvm-native.jsonl")
    verbatim = rows_from_lines(build / "jvm-verbatim.jsonl")
    browser = browser_rows(build / "browser-dom.html", mutate)
    expected_keys = {f"{name}-{size}" for name in EXPECT for size in SIZES}
    for label, rows in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
        if set(rows) != expected_keys:
            fail(f"{label}: unexpected case set {sorted(set(rows) ^ expected_keys)}")

    if mutate == "clip-count":
        verbatim["one-behind-quad-765x503"]["clipOut"][4] += 1
    if mutate == "clip-fill-count":
        verbatim["one-behind-quad-765x503"]["flatFillEntries"] += 1
    if mutate == "clip-browser-element":
        browser["two-behind-triangle-1280x800"]["projX"][0] += 1
    if mutate == "clip-visible":
        for rows in (native, verbatim, browser):
            for size in SIZES:
                rows[f"crossing-50.2-front-{size}"]["fnv1a"] = rows[f"crossing-49.8-behind-{size}"]["fnv1a"]

    oracles = {}
    for size in SIZES:
        for name in EXPECT:
            key = f"{name}-{size}"
            oracles[key] = check_row(name, size, native[key], verbatim[key], browser[key])

    # Visible native output must change across the near-plane crossing and when culling removes a clipped face.
    for size in SIZES:
        a, b = native[f"crossing-49.8-behind-{size}"], native[f"crossing-50.2-front-{size}"]
        if a["fnv1a"] == b["fnv1a"] or a["depthFnv1a"] == b["depthFnv1a"]:
            fail(f"{size}: native output does not change across the near-plane crossing (49.8 behind vs 50.2 front)")
        q, r = native[f"one-behind-quad-{size}"], native[f"one-behind-quad-reversed-{size}"]
        if q["fnv1a"] == r["fnv1a"]:
            fail(f"{size}: reversed winding does not change native output; culling is not shown to matter")

    # Positive counters for each intended clipped shape, from the extracted builds.
    totals = [0] * 5
    for size in SIZES:
        for name in EXPECT:
            for i, value in enumerate(verbatim[f"{name}-{size}"]["clipOut"]):
                totals[i] += value
    for index, label in ((4, "one-behind quad (method646 output 4)"), (3, "two-behind triangle (output 3)"),
                         (0, "all-behind face with zero output")):
        if totals[index] <= 0:
            fail(f"no positive counter for {label}")

    if mutate is None:
        evidence = {
            "schema": "soloscape.wasm-face.clip-evidence/1",
            "closure": {k: closure[k] for k in ("class64_sub1_verbatim_lines", "class64_sub1_line_budget",
                                                  "class64_sub1_non_verbatim_lines", "class109_non_verbatim_lines",
                                                  "class64_sub1_native_instance_fields_kept",
                                                  "class64_sub1_field_budget", "stubs")},
            "clipOutTotalsExtracted": {"0": totals[0], "3": totals[3], "4": totals[4]},
            "cases": [{"case": key, "vertices": native[key]["vertices"], "faces": native[key]["faces"],
                       "eligibleFaces": oracles[key]["eligible"], "derivedClipOut": oracles[key]["clip"],
                       "rejected": oracles[key]["rejected"], "boundI636": oracles[key]["boundI636"],
                       "derivedFills": oracles[key]["fills"], "normalFills": oracles[key]["normalFills"],
                       "clipFills": oracles[key]["clipFills"], "flatFillEntriesExtracted": verbatim[key]["flatFillEntries"],
                       "flatFillEntriesWasm": browser[key]["flatFillEntries"], "flatFillEntriesNative": None,
                       "boundI637": oracles[key]["boundI637"], "covered": native[key]["covered"],
                       "fnv1a": native[key]["fnv1a"], "depthFnv1a": native[key]["depthFnv1a"],
                       "projX": native[key]["projX"], "projY": native[key]["projY"], "projZ": native[key]["projZ"],
                       "camX": native[key]["camX"], "camY": native[key]["camY"], "camD": native[key]["camD"],
                       "extractedCounters": verbatim[key]["counters"], "extractedClipOut": verbatim[key]["clipOut"],
                       "wasmCounters": browser[key]["counters"], "wasmClipOut": browser[key]["clipOut"]}
                      for size in SIZES for key in [f"{name}-{size}" for name in EXPECT]],
        }
        (build / "clip-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: {len(expected_keys)} clip cases match across native jar, JVM extracted and WasmGC; "
              f"derived eligibility, clipOut counts, model rejection, stubs and camera arrays agree; "
              f"native output changes across the 49.8/50.2 crossing; extracted clipOut totals {totals}; "
              f"flat-fill entries (JVM and WasmGC) equal the derived fills in all cases, native absent")
    else:
        # Same convention as check_evidence.py: a corrupted input that gets past every check exits 0 here, and the
        # self-test in run.sh then reports the weakened checker.
        print(f"mutation {mutate} was NOT detected by the clip checker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
