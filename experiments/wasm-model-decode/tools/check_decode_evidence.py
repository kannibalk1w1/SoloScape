#!/usr/bin/env python3
"""Checker for the decode-only equality proof.

Compares, for every original fixture, the native jar's real Class124(byte[]) (reflection), the extracted JVM closure
and the extracted TeaVM WasmGC closure against the INDEPENDENT design in build/fixtures.json. Colour and index
arrays are compared as the stored Java types: the native colour field is a signed short, so the design's unsigned
16-bit colour is converted explicitly (v - 65536 when v >= 32768) before comparison.

Perturbation effects are measured on the NATIVE decoded arrays: the vertex perturbation must change exactly one
vertex coordinate, and the colour/index perturbation must change exactly one colour and one face index.

`--mutate NAME` corrupts one collected runtime's evidence in memory before validation. Every mutation must fail
inside the checker (nonzero exit, a FAIL: line). Exit 1 is a checker failure; argparse errors exit 2 and are never
counted as a control.
"""
import argparse
import html
import json
import pathlib
import re
import sys

MUTATIONS = {
    "native-design": ("native-jar", "triangle", "x", 0),
    "extracted-vertex": ("extracted-jvm", "strip_types_1_4", "y", 1),
    "browser-face": ("teavm-0.16.0-wasmgc", "signed_smart_boundaries", "a", 0),
    "browser-colour": ("teavm-0.16.0-wasmgc", "strip_types_1_4", "colour", 0),
}
ARRAYS = ["x", "y", "z", "a", "b", "c", "colour"]
SCALARS = ["vertexCount", "faceCount", "maxVertexPlusOne"]
FAILS = []


def fail(message):
    FAILS.append(message)
    print("FAIL: " + message)


def signed_colour(value):
    return value - 65536 if value >= 32768 else value


def load_jsonl(path):
    if not path.exists():
        fail(f"missing runtime output {path.name}")
        return []
    cases = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as error:
            fail(f"{path.name} line {number} is not JSON: {error}")
    return cases


def load_browser(path):
    if not path.exists():
        fail("missing browser DOM")
        return []
    dom = path.read_text(encoding="utf-8")
    match = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, re.S)
    if not match:
        fail("browser DOM has no result element")
        return []
    text = html.unescape(match.group(1)).strip()
    if text.startswith("FAIL:"):
        fail("browser probe reported " + text[:200])
        return []
    try:
        return json.loads(text)["cases"]
    except (json.JSONDecodeError, KeyError) as error:
        fail(f"browser result is not the expected JSON: {error}")
        return []


def expected_value(expected, field):
    if field == "colour":
        return [signed_colour(v) for v in expected["colour"]]
    return expected[field]


def validate(runtime, cases, fixtures, stub_expected):
    by_name = {}
    expected_names = {fixture["name"] for fixture in fixtures}
    if len(cases) != len(fixtures) or {case.get("name") for case in cases} != expected_names:
        fail(f"{runtime}: runtime case set does not exactly match the original fixtures")
    for case in cases:
        by_name.setdefault(case.get("name"), []).append(case)
    for fixture in fixtures:
        name = fixture["name"]
        expected = fixture["expected"]
        matches = by_name.get(name, [])
        if len(matches) != 1:
            fail(f"{runtime} {name}: expected exactly one case, found {len(matches)}")
            continue
        case = matches[0]
        if case.get("runtime") != runtime:
            fail(f"{runtime} {name}: runtime label {case.get('runtime')!r}")
        if not case.get("ok"):
            fail(f"{runtime} {name}: decode failed: {case.get('error')}")
            continue
        if stub_expected and case.get("stubCalls") != 0:
            fail(f"{runtime} {name}: adapter stub calls {case.get('stubCalls')} (must be 0)")
        for field in SCALARS:
            if case.get(field) != expected[field]:
                fail(f"{runtime} {name}: {field} {case.get(field)} != design {expected[field]}")
        for field in ARRAYS:
            if case.get(field) != expected_value(expected, field):
                got = case.get(field)
                first = next((i for i, (g, e) in enumerate(zip(got or [], expected_value(expected, field)))
                              if g != e), None)
                fail(f"{runtime} {name}: {field} differs from the design at index {first}: "
                     f"{None if got is None or first is None else got[first]} != "
                     f"{None if first is None else expected_value(expected, field)[first]}")
    return by_name


def differences(first, second, arrays):
    found = []
    for field in arrays:
        for index, (a, b) in enumerate(zip(first[field], second[field])):
            if a != b:
                found.append((field, index))
        if len(first[field]) != len(second[field]):
            found.append((field, "length"))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True)
    parser.add_argument("--mutate", choices=sorted(MUTATIONS))
    args = parser.parse_args()
    build = pathlib.Path(args.build)
    fixtures = json.loads((build / "fixtures.json").read_text(encoding="utf-8"))

    native = load_jsonl(build / "jvm-native.jsonl")
    extracted = load_jsonl(build / "jvm-extracted.jsonl")
    browser = load_browser(build / "browser-dom.html")
    runs = {"native-jar": native, "extracted-jvm": extracted, "teavm-0.16.0-wasmgc": browser}

    if args.mutate:
        runtime, name, field, index = MUTATIONS[args.mutate]
        for case in runs[runtime]:
            if case.get("name") == name and isinstance(case.get(field), list):
                case[field][index] = case[field][index] + 1
                print(f"mutation {args.mutate}: {runtime} {name} {field}[{index}] changed in memory")
                break
        else:
            fail(f"mutation {args.mutate} target not found")

    for runtime, cases in runs.items():
        validate(runtime, cases, fixtures, stub_expected=runtime != "native-jar")

    if not FAILS:
        native_by = {c["name"]: c for c in native if c.get("ok")}
        extracted_by = {c["name"]: c for c in extracted if c.get("ok")}
        vertex_effect = differences(native_by["triangle"], native_by["vertex_perturbed"], ["x", "y", "z"])
        if vertex_effect != [("y", 2)]:
            fail(f"vertex perturbation changed {vertex_effect}, expected exactly [('y', 2)] on native")
        colour_effect = differences(native_by["strip_types_1_4"], native_by["colour_index_perturbed"],
                                    ["colour", "a", "b", "c"])
        if colour_effect != [("colour", 2), ("c", 4)]:
            fail(f"colour/index perturbation changed {colour_effect}, expected [('colour', 2), ('c', 4)]")
        if differences(native_by["triangle"], extracted_by["triangle"], ARRAYS):
            fail("native and extracted triangle arrays differ")
        for name, case in native_by.items():
            if not any(case["x"]) and not any(case["y"]) and not any(case["z"]):
                fail(f"{name}: all coordinates are zero, no meaningful geometry")
            if len(case["colour"]) >= 2 and len(set(case["colour"])) < 2:
                fail(f"{name}: colours are not distinct, no colour effect can be seen")

    evidence = {
        "fixtures": [f["name"] for f in fixtures],
        "runtimes": sorted(runs),
        "failures": FAILS,
        "mutation": args.mutate,
    }
    if not args.mutate:
        (build / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if FAILS:
        print(f"decode checker: {len(FAILS)} failure(s)")
        return 1
    print(f"PASS: {len(fixtures)} original fixtures agree across native jar, extracted JVM and WasmGC "
          f"with the design; perturbation effects match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
