#!/usr/bin/env python3
"""Validate one clip-mode run (FACE_CLIP=1) and write build-clip/clip-evidence.json; exits nonzero on any mismatch.

Every camera-space and projected array is derived HERE, in Python, from each row's RECORDED model and view matrices
and its vertices. The derivation re-implements method654's expression order with Java float32 semantics (each
operation rounds to binary32; (int) truncates toward zero). The native jar has no counters, so these derivations are
the reference. Each extracted build (JVM and WasmGC) must reproduce them, and must agree with the native arrays.

  * matrices: each row's recorded model and view matrices must equal the designed matrices of the row's REQUESTED
    camera. Camera 0 takes the fast path (model = 16384 I); camera 1 takes the general composition (model = 16384 x
    rotation with 0.8/0.6, view rows 12/13 and 5/13 scaled by 1/16384, depth offset 2400);
  * screen and bound rejection: method654 returns before writing anything when the model bound (100000, 50) or a
    screen bound fails; the derived bound uses the minimum and maximum model Y and the model radius;
  * eligibility: a face with a behind vertex (camera depth < 50) whose camera-space triple product, computed with
    Java's int semantics, is positive (method643: dot = B . ((A - B) x (C - B)) > 0);
  * outputs: 0 front vertices -> nothing (index 0), 1 -> triangle (index 3), 2 -> quad (index 4);
  * adapter state: the requested variant mask0 clears aShortArray5311 in method657 state 2; maskbit (anInt5316 bit
    0x1000) and floatarr (aFloatArrayArray5314 non-null) keep it. Byte array clearing is required for every variant.
"""
import argparse
import html
import json
import math
import pathlib
import re
import struct
import sys

SIZES = ["765x503", "1280x800"]
NEAR = 50
FAR_BOUND = 100000
ZERO = [0, 0, 0, 0, 0]
# name -> requested camera, requested variant, expected clipOut counts (index 0: no output, 3: triangle, 4: quad),
# whether the model is rejected, and whether the frame must show drawn pixels. These are the designed intent; the
# derived oracle must match them.
EXPECT = {
    "one-behind-quad": {"camera": 0, "variant": "mask0", "clip": [0, 0, 0, 0, 1], "rejected": False, "covered": True},
    "one-behind-quad-reversed": {"camera": 0, "variant": "mask0", "clip": ZERO, "rejected": False, "covered": False},
    "two-behind-triangle": {"camera": 0, "variant": "mask0", "clip": [0, 0, 0, 1, 0], "rejected": False, "covered": True},
    "two-behind-triangle-reversed": {"camera": 0, "variant": "mask0", "clip": ZERO, "rejected": False, "covered": False},
    "exact-near-50": {"camera": 0, "variant": "mask0", "clip": ZERO, "rejected": False, "covered": True},
    "crossing-49.8-behind": {"camera": 0, "variant": "mask0", "clip": [0, 0, 0, 0, 1], "rejected": False, "covered": True},
    "crossing-50.2-front": {"camera": 0, "variant": "mask0", "clip": ZERO, "rejected": False, "covered": True},
    "model-all-behind": {"camera": 0, "variant": "mask0", "clip": ZERO, "rejected": True, "covered": False},
    "face-all-behind-companion": {"camera": 0, "variant": "mask0", "clip": [1, 0, 0, 0, 0], "rejected": False, "covered": True},
    "cam1-one-behind-quad": {"camera": 1, "variant": "mask0", "clip": [0, 0, 0, 0, 1], "rejected": False, "covered": True},
    "cam1-one-behind-quad-reversed": {"camera": 1, "variant": "mask0", "clip": ZERO, "rejected": False, "covered": False},
    "cam1-two-behind-triangle": {"camera": 1, "variant": "mask0", "clip": [0, 0, 0, 1, 0], "rejected": False, "covered": True},
    "cam1-maskbit-one-behind-quad": {"camera": 1, "variant": "maskbit", "clip": [0, 0, 0, 0, 1], "rejected": False, "covered": True},
    "cam1-floatarr-two-behind-triangle": {"camera": 1, "variant": "floatarr", "clip": [0, 0, 0, 1, 0], "rejected": False, "covered": True},
}
# Labelled threshold vertices: name -> (vertex index, integer camera depth, behind the near plane).
EXACT_VERTEX = {"exact-near-50": (2, 50, False), "crossing-49.8-behind": (2, 49, True),
                "crossing-50.2-front": (2, 50, False)}
COMPARED = ("vertexCount", "faceCount", "projX", "projY", "projZ", "camX", "camY", "camD", "fnv1a", "depthFnv1a",
            "covered", "camera", "variant", "modelBits", "viewBits", "shortCleared", "byteCleared")
# Designed flat-fill entries (method1018 calls): quad = 2 clip fills, triangle = 1, regular front face = 1, culled or rejected = 0.
FILLS = {"one-behind-quad": 2, "one-behind-quad-reversed": 0, "two-behind-triangle": 1,
         "two-behind-triangle-reversed": 0, "exact-near-50": 1, "crossing-49.8-behind": 2,
         "crossing-50.2-front": 1, "model-all-behind": 0, "face-all-behind-companion": 1,
         "cam1-one-behind-quad": 2, "cam1-one-behind-quad-reversed": 0, "cam1-two-behind-triangle": 1,
         "cam1-maskbit-one-behind-quad": 2, "cam1-floatarr-two-behind-triangle": 1}
MUTATIONS = ("clip-count", "clip-visible", "clip-browser-element", "clip-fill-count", "clip-camera1-projection",
             "clip-variant-state")
INT_MIN, INT_MAX = -2 ** 31, 2 ** 31 - 1
BACKGROUND = 0xff102030


def fail(message):
    raise SystemExit("FAIL: " + message)


def f32(value):
    """Round a double to the nearest binary32 (Java float)."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def decode_matrices(row):
    """Exact float32 values of the recorded matrices (raw IEEE bit patterns, so no decimal rounding can intervene)."""
    def decode(bits):
        return [struct.unpack("<f", struct.pack("<i", b))[0] for b in bits]
    return decode(row["modelBits"]), decode(row["viewBits"])


def fmul(a, b):
    return f32(a * b)


def fadd(a, b):
    return f32(a + b)


def fdiv(a, b):
    return f32(a / b)


def trunc(value):
    """Finite, in-range fixture float to Java int: truncate toward zero."""
    return int(value)


def designed_matrices(camera):
    """The matrices FaceMesh.model/view must record for a camera, written from the design constants."""
    if camera == 0:
        model = [16384.0, 0.0, 0.0, 0.0, 16384.0, 0.0, 0.0, 0.0, 16384.0, 0.0, 0.0, 0.0]
        view = [1.0, 0.0, 0.0, 0.0, f32(4.0 / 5.0), -f32(3.0 / 5.0), 0.0, f32(3.0 / 5.0), f32(4.0 / 5.0), 0.0, 0.0, 2400.0]
    elif camera == 1:
        c, s = f32(4.0 / 5.0 * 16384.0), f32(3.0 / 5.0 * 16384.0)
        model = [c, 0.0, s, 0.0, 16384.0, 0.0, -s, 0.0, c, 0.0, 0.0, 0.0]
        k, cv, sv = f32(1.0 / 16384.0), f32(12.0 / 13.0 / 16384.0), f32(5.0 / 13.0 / 16384.0)
        view = [k, 0.0, 0.0, 0.0, cv, -sv, 0.0, sv, cv, 0.0, 0.0, 2400.0]
    else:
        raise SystemExit(f"FAIL: no designed matrices for camera {camera}")
    return model, view


def oracle(row):
    """method654 for one row, from its recorded matrices, vertices and size. Returns the arrays it writes."""
    width, height = (int(v) for v in row["size"].split("x"))
    cx, cy = width // 2, height // 2
    model, view = decode_matrices(row)
    vertices = row["vertices"]
    vr = [view[0:3], view[3:6], view[6:9]]
    vt = view[9:12]
    mr = [model[0:3], model[3:6], model[6:9]]
    mt = model[9:12]
    fast = model[:9] == [16384.0, 0.0, 0.0, 0.0, 16384.0, 0.0, 0.0, 0.0, 16384.0]
    # Translation base per output row (f, f_638, f_644): view translation plus view row times model translation.
    t = []
    for r in range(3):
        acc = vt[r]
        for j in range(3):
            acc = fadd(acc, fmul(vr[r][j], mt[j]))
        t.append(acc)
    # Composed 3x3 (f_650..f_655 and f_633, f_639, f_645): the fast path uses the view rows alone.
    comp = [[0.0] * 3 for _ in range(3)]
    for r in range(3):
        for c in range(3):
            if fast:
                comp[r][c] = vr[r][c]
            else:
                acc = fmul(vr[r][0], mr[0][c])
                acc = fadd(acc, fmul(vr[r][1], mr[1][c]))
                comp[r][c] = fadd(acc, fmul(vr[r][2], mr[2][c]))
    ys = [v[1] for v in vertices]
    radius = trunc(math.sqrt(max(v[0] * v[0] + v[2] * v[2] for v in vertices)) + 0.99)
    i634 = trunc(fadd(t[2], fmul(float(min(ys)), comp[2][1])))
    i635 = trunc(fadd(t[2], fmul(float(max(ys)), comp[2][1])))
    i636, i637 = min(i634, i635) - radius, max(i634, i635) + radius
    result = {"i636": i636, "i637": i637, "rejected": False, "written": False, "screenRejected": False,
              "camX": [0] * len(vertices), "camY": [0] * len(vertices), "camD": [0] * len(vertices),
              "projX": [0] * len(vertices), "projY": [0] * len(vertices), "projZ": [0] * len(vertices)}
    if not (i636 < FAR_BOUND and i637 > NEAR):
        result["rejected"] = True
        return result
    # Screen-bound rejection in x and y (method654, i == -1): integer division truncates toward zero.
    x_lo_hi = [trunc(fadd(t[0], fmul(float(v), comp[0][1]))) for v in (min(ys), max(ys))]
    y_lo_hi = [trunc(fadd(t[1], fmul(float(v), comp[1][1]))) for v in (min(ys), max(ys))]
    lo_x, hi_x = min(x_lo_hi), max(x_lo_hi)
    lo_y, hi_y = min(y_lo_hi), max(y_lo_hi)
    x0, x1 = (lo_x - radius) * height, (hi_x + radius) * height
    y0, y1 = (lo_y - radius) * height, (hi_y + radius) * height

    def div(a, b):
        q = abs(a) // abs(b)
        return q if (a >= 0) == (b >= 0) else -q
    if div(x0, i637) >= width - cx or div(x1, i637) <= -cx or div(y0, i637) >= height - cy or div(y1, i637) <= -cy:
        result["screenRejected"] = True
        return result
    for i, (x, y, z) in enumerate(vertices):
        cam = []
        for r in range(3):
            acc = t[r]
            acc = fadd(acc, fmul(comp[r][0], float(x)))
            acc = fadd(acc, fmul(comp[r][1], float(y)))
            acc = fadd(acc, fmul(comp[r][2], float(z)))
            cam.append(acc)
        result["camX"][i], result["camY"][i], result["camD"][i] = trunc(cam[0]), trunc(cam[1]), trunc(cam[2])
        result["projZ"][i] = trunc(cam[2])
        if cam[2] >= float(NEAR):
            result["projX"][i] = cx + trunc(fdiv(fmul(cam[0], float(height)), cam[2]))
            result["projY"][i] = cy + trunc(fdiv(fmul(cam[1], float(height)), cam[2]))
        else:
            result["projX"][i] = -5000
    # Both native auxiliary model arrays are null in this asset-free harness.
    # Under that constraint bool_658 equals the near-bound flag bool_657.
    result["written"] = i636 <= NEAR
    if not result["written"]:
        for key in ("camX", "camY", "camD"):
            result[key] = [0] * len(vertices)
    return result


def check_matrices(name, key, row):
    """The recorded matrices must be the designed ones for the row's requested camera (the camera state itself)."""
    model, view = designed_matrices(EXPECT[name]["camera"])
    if row["camera"] != EXPECT[name]["camera"]:
        fail(f"{key}: row records camera {row['camera']}, requested {EXPECT[name]['camera']}")
    if row["variant"] != EXPECT[name]["variant"]:
        fail(f"{key}: row records variant {row['variant']}, requested {EXPECT[name]['variant']}")
    recorded_model, recorded_view = decode_matrices(row)
    if recorded_model != model:
        fail(f"{key}: recorded model matrix {recorded_model} is not the camera {EXPECT[name]['camera']} design")
    if recorded_view != view:
        fail(f"{key}: recorded view matrix {recorded_view} is not the camera {EXPECT[name]['camera']} design")


def rows_from_lines(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["case"] in rows:
                fail(f"{path.name}: duplicate case {row['case']}")
            rows[row["case"]] = row
    return rows


def browser_rows(path):
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


def derive(name, row, expected):
    """Clip eligibility, clip outputs and flat-fill entries, from the native arrays and the oracle's bound state."""
    vertices, faces = row["vertices"], row["faces"]
    n = len(vertices)
    if expected["rejected"] or expected["screenRejected"]:
        return {"rejected": expected["rejected"], "eligible": [], "clip": ZERO, "fills": 0, "normalFills": 0,
                "clipFills": 0, "boundI636": expected["i636"], "boundI637": expected["i637"]}
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
    return {"rejected": False, "eligible": eligible, "clip": clip,
            "fills": normal + clip_fills, "normalFills": normal, "clipFills": clip_fills,
            "boundI636": expected["i636"], "boundI637": expected["i637"]}


def check_row(name, size, native, verbatim, browser):
    """Cross-runtime equality, oracle agreement and the labelled expectation for one case."""
    key = f"{name}-{size}"
    expect = EXPECT[name]
    for label, row in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
        check_matrices(name, f"{label} {key}", row)
    exp = oracle(native)
    if exp["rejected"] != expect["rejected"]:
        fail(f"{key}: model rejected={exp['rejected']} but designed {expect['rejected']}")
    oracle_row = derive(name, dict(native, camX=exp["camX"], camY=exp["camY"], camD=exp["camD"],
                                   projX=exp["projX"], projY=exp["projY"]), exp)
    if oracle_row["fills"] != FILLS[name]:
        fail(f"{key}: derived fill entries {oracle_row['fills']} != designed {FILLS[name]}")
    if native["flatFillEntries"] is not None:
        fail(f"jvm-native {key}: flat-fill entries reported; the native jar is uninstrumented")
    if name in EXACT_VERTEX:
        index, depth, behind = EXACT_VERTEX[name]
        if native["camD"][index] != depth or (native["projX"][index] == -5000) != behind:
            fail(f"{key}: threshold vertex {index} depth {native['camD'][index]} / "
                 f"behind={native['projX'][index] == -5000}, designed depth {depth} behind={behind}")
    if oracle_row["clip"] != expect["clip"]:
        fail(f"{key}: derived clip counts {oracle_row['clip']} != designed {expect['clip']}")
    if oracle_row["rejected"] != expect["rejected"]:
        fail(f"{key}: model rejected={oracle_row['rejected']} but designed {expect['rejected']}")
    if expect["camera"] == 0 and exp["written"]:
        # Camera 0 identity (fast path): camera x is exactly the model x, so the view row is a unit row.
        for i, (x, _, _) in enumerate(native["vertices"]):
            if native["camX"][i] != x:
                fail(f"{key}: camX[{i}]={native['camX'][i]} != {x} (camera 0 fast path)")
    for label, row in (("jvm-verbatim", verbatim), ("browser", browser)):
        for field in COMPARED:
            if row[field] != native[field]:
                fail(f"{label} {key}: {field} differs from the native jar reference")
        if row["vertices"] != native["vertices"] or row["faces"] != native["faces"]:
            fail(f"{label} {key}: geometry differs")
    for label, row in (("jvm-native", native), ("jvm-verbatim", verbatim), ("browser", browser)):
        n = native["vertexCount"]
        if len(native["camX"]) != n or len(native["projX"]) != n or n <= 0:
            fail(f"{label} {key}: wrong array lengths")
        # Every runtime must reproduce the oracle's arrays for this row, element for element.
        for field in ("projX", "projY", "projZ", "camX", "camY", "camD"):
            if row[field] != exp[field]:
                fail(f"{label} {key}: {field} {row[field]} != derived {exp[field]} (camera {expect['camera']} oracle)")
        if expect["rejected"]:
            if row["covered"] != 0:
                fail(f"{label} {key}: rejected model drew pixels")
        if (row["covered"] > 0) != expect["covered"]:
            fail(f"{label} {key}: covered={row['covered']} but designed covered={expect['covered']}")
        if not expect["rejected"]:
            want_short = expect["variant"] == "mask0"
            if row["shortCleared"] != want_short:
                fail(f"{label} {key}: shortCleared={row['shortCleared']} for variant {expect['variant']}; "
                     f"designed {want_short} (method657 state 2)")
            if row["byteCleared"] is not True:
                fail(f"{label} {key}: aByteArray5386 not cleared")
    for label, row in (("jvm-verbatim", verbatim), ("browser", browser)):
        c = row["counters"]
        if c is None:
            fail(f"{label} {key}: counters missing")
        expect_adapter = 0 if expect["rejected"] else 1
        if c["adapterEntries"] != expect_adapter or c["adapterIllegal"] != 0:
            fail(f"{label} {key}: adapter entries {c['adapterEntries']} != {expect_adapter}")
        for counter, value in c.items():
            if counter != "adapterEntries" and value != 0:
                fail(f"{label} {key}: counter {counter}={value}; illegal path or stub reached")
        if row["flatFillEntries"] != oracle_row["fills"]:
            fail(f"{label} {key}: flatFillEntries {row['flatFillEntries']} != derived {oracle_row['fills']}")
        if row["clipOut"] != oracle_row["clip"]:
            fail(f"{label} {key}: clipOut {row['clipOut']} != derived {oracle_row['clip']}")
    if native["counters"] is not None or native.get("clipOutNative") is not True:
        fail(f"jvm-native {key}: native reference unexpectedly reported counters")
    return oracle_row, exp


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
    browser = browser_rows(build / "browser-dom.html")
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
    if mutate == "clip-camera1-projection":
        browser["cam1-one-behind-quad-1280x800"]["projY"][0] += 1
    if mutate == "clip-variant-state":
        verbatim["cam1-maskbit-one-behind-quad-765x503"]["shortCleared"] = True
    if mutate == "clip-visible":
        for rows in (native, verbatim, browser):
            for size in SIZES:
                rows[f"crossing-50.2-front-{size}"]["fnv1a"] = rows[f"crossing-49.8-behind-{size}"]["fnv1a"]

    oracles = {}
    for size in SIZES:
        for name in EXPECT:
            key = f"{name}-{size}"
            oracles[key], _ = check_row(name, size, native[key], verbatim[key], browser[key])

    # Visible native output must change across the near-plane crossing and when culling removes a clipped face.
    for size in SIZES:
        a, b = native[f"crossing-49.8-behind-{size}"], native[f"crossing-50.2-front-{size}"]
        if a["fnv1a"] == b["fnv1a"] or a["depthFnv1a"] == b["depthFnv1a"]:
            fail(f"{size}: native output does not change across the near-plane crossing (49.8 behind vs 50.2 front)")
        q, r = native[f"one-behind-quad-{size}"], native[f"one-behind-quad-reversed-{size}"]
        if q["fnv1a"] == r["fnv1a"]:
            fail(f"{size}: reversed winding does not change native output; culling is not shown to matter")
        # Camera 1 (general transform): the clipped quad must change native framebuffer and depth vs the culled reverse.
        q1, r1 = native[f"cam1-one-behind-quad-{size}"], native[f"cam1-one-behind-quad-reversed-{size}"]
        if q1["fnv1a"] == r1["fnv1a"] or q1["depthFnv1a"] == r1["depthFnv1a"]:
            fail(f"{size}: camera 1 clipped quad does not change native framebuffer/depth vs its culled reverse")

    # Positive counters for each intended clipped shape, from the extracted builds.
    totals = [0] * 5
    camera1 = [0] * 5
    camera1_fills = 0
    for size in SIZES:
        for name in EXPECT:
            for i, value in enumerate(verbatim[f"{name}-{size}"]["clipOut"]):
                totals[i] += value
                if EXPECT[name]["camera"] == 1:
                    camera1[i] += value
            if EXPECT[name]["camera"] == 1:
                camera1_fills += verbatim[f"{name}-{size}"]["flatFillEntries"]
    for index, label in ((4, "one-behind quad (method646 output 4)"), (3, "two-behind triangle (output 3)"),
                         (0, "all-behind face with zero output")):
        if totals[index] <= 0:
            fail(f"no positive counter for {label}")
    for index, label in ((4, "camera 1 one-behind quad"), (3, "camera 1 two-behind triangle")):
        if camera1[index] <= 0:
            fail(f"no positive camera-1 counter for {label}")
    if camera1_fills <= 0:
        fail("no positive camera-1 flat-fill entries")

    if mutate is None:
        evidence = {
            "schema": "soloscape.wasm-face.clip-evidence/2",
            "closure": {k: closure[k] for k in ("class64_sub1_verbatim_lines", "class64_sub1_line_budget",
                                                  "class64_sub1_non_verbatim_lines", "class109_non_verbatim_lines",
                                                  "class64_sub1_native_instance_fields_kept",
                                                  "class64_sub1_field_budget", "stubs")},
            "clipOutTotalsExtracted": {"0": totals[0], "3": totals[3], "4": totals[4]},
            "camera1ClipOutExtracted": {"0": camera1[0], "3": camera1[3], "4": camera1[4]},
            "camera1FillEntriesExtracted": camera1_fills,
            "cases": [{"case": key, "camera": EXPECT[name]["camera"], "variant": EXPECT[name]["variant"],
                       "vertices": native[key]["vertices"], "faces": native[key]["faces"],
                       "modelMatrix": decode_matrices(native[key])[0], "viewMatrix": decode_matrices(native[key])[1],
                       "shortCleared": native[key]["shortCleared"], "byteCleared": native[key]["byteCleared"],
                       "derivedClipOut": oracles[key]["clip"], "rejected": oracles[key]["rejected"],
                       "boundI636": oracles[key]["boundI636"], "boundI637": oracles[key]["boundI637"],
                       "derivedFills": oracles[key]["fills"], "normalFills": oracles[key]["normalFills"],
                       "clipFills": oracles[key]["clipFills"], "flatFillEntriesExtracted": verbatim[key]["flatFillEntries"],
                       "flatFillEntriesWasm": browser[key]["flatFillEntries"], "flatFillEntriesNative": None,
                       "covered": native[key]["covered"],
                       "fnv1a": native[key]["fnv1a"], "depthFnv1a": native[key]["depthFnv1a"],
                       "projX": native[key]["projX"], "projY": native[key]["projY"], "projZ": native[key]["projZ"],
                       "camX": native[key]["camX"], "camY": native[key]["camY"], "camD": native[key]["camD"],
                       "extractedCounters": verbatim[key]["counters"], "extractedClipOut": verbatim[key]["clipOut"],
                       "wasmCounters": browser[key]["counters"], "wasmClipOut": browser[key]["clipOut"]}
                      for size in SIZES for name in EXPECT for key in [f"{name}-{size}"]],
        }
        (build / "clip-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: {len(expected_keys)} clip cases match across native jar, JVM extracted and WasmGC; "
              f"recorded camera/variant state, matrices, camera and projected arrays agree with the float32 oracle; "
              f"derived eligibility, clipOut counts, model rejection and adapter state agree; "
              f"native output changes across the 49.8/50.2 crossing and camera-1 reversal; "
              f"extracted clipOut totals {totals}, camera-1 clipOut {camera1}, camera-1 flat-fill entries {camera1_fills}; "
              f"flat-fill entries (JVM and WasmGC) equal the derived fills in all cases, native absent")
    else:
        # Same convention as check_evidence.py: a corrupted input that gets past every check exits 0 here, and the
        # self-test in run.sh then reports the weakened checker.
        print(f"mutation {mutate} was NOT detected by the clip checker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
