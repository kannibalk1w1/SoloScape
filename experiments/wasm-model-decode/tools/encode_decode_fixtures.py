#!/usr/bin/env python3
"""Encode original synthetic old-format Class124 model bytes from independently declared designs.

The expected arrays are the DESIGN (vertices, faces, colours), not decoder output. The encoder writes the
old-format layout that the native method1103 reads (18-byte footer, texture count 0, every optional flag 0):

  [0, V)                 vertex flags (bit0 X delta, bit1 Y delta, bit2 Z delta)
  [V, V+F)               face types (1-4)
  [V+F, V+F+L)           face index deltas (the Packet stream), L = footer i65
  [.., +2F)              face colours, unsigned 16-bit big-endian
  [.., +X) [.., +Y) [.., +Z)  vertex X, Y, Z delta streams (signedSmart), lengths in the footer
  last 18 bytes          footer: u16 V, u16 F, u8 T=0, u8 flags i57..i61 = 0, u16 X, Y, Z, index lengths

signedSmart: -64..63 is one byte (value+64); -16384..16383 is two bytes big-endian (value+49152).
Face types, as read by the face loop of native method1103: 1 = three new indices, 2 = (A, C, new),
3 = (C, B, new), 4 = (B, A, new), with the running state (A, B, C) and the cursor equal to C.

Writes build/fixtures.json (designs, expected arrays, hex bytes) and build/generated-src/DecodeFixtures.java.
Fails (nonzero) on any design the stream cannot express, on bounds, on a fixture above 1 KiB, or on a missing
delta class. It never reads native source and never uses decoder output as expected data.
"""
import argparse
import json
import pathlib
import struct
import sys

MAX_FIXTURE_BYTES = 1024
MAX_VERTICES = 65535
ONE_BYTE = range(-64, 64)
TWO_BYTE = range(-16384, 16384)


def die(message):
    print("encode_decode_fixtures: " + message, file=sys.stderr)
    sys.exit(1)


def smart(value):
    if value in ONE_BYTE:
        return bytes([value + 64])
    if value in TWO_BYTE:
        return struct.pack(">H", value + 49152)
    die(f"delta {value} is outside signedSmart")


def design_triangle():
    return {
        "name": "triangle",
        "vertices": [(0, 0, 0), (100, 0, 0), (0, 100, 0)],
        "faces": [(1, 0, 1, 2)],
        "colours": [0xF00D],
        "zeroBits": {},
    }


def design_strip():
    return {
        "name": "strip_types_1_4",
        "vertices": [(0, 0, 0), (10, 0, 0), (0, 10, 0), (10, 10, 0), (0, 20, 0), (10, 20, 0)],
        "faces": [(1, 0, 1, 2), (2, 0, 2, 3), (3, 3, 2, 4), (4, 2, 3, 5), (1, 5, 4, 1)],
        "colours": [0x0102, 0x7FFF, 0x8000, 0xFFFF, 0x0000],
        "zeroBits": {},
    }


def design_boundaries():
    # Vertices 0-7 carry the signedSmart edges on their coordinate deltas; the rest are zero deltas.
    x = [0, 63, 127, 62, -2, 16381, -3, -3] + [0] * 192
    y = [0, 63, -1, -1, -65, -1, -66, -66] + [0] * 192
    z = [0, 64, 0, -65, 0, 63, 63, 63] + [0] * 192
    faces = [
        (1, 0, 1, 2),
        (1, 66, 130, 131),
        (2, 66, 131, 67),
        (3, 67, 131, 2),
        (4, 131, 67, 129),
        (1, 5, 6, 7),
        (2, 5, 7, 70),
    ]
    return {
        "name": "signed_smart_boundaries",
        "vertices": list(zip(x, y, z)),
        "faces": faces,
        "colours": [0x1000, 0x2000, 0x3000, 0x4000, 0x8000, 0xFFFF, 0x7FFF],
        # Explicit zero deltas: the bit is set, the stream carries a zero value.
        "zeroBits": {7: "x", 3: "y"},
    }


def design_vertex_perturbed():
    base = design_triangle()
    base["name"] = "vertex_perturbed"
    base["vertices"] = [(0, 0, 0), (100, 0, 0), (0, 101, 0)]
    return base


def design_colour_index_perturbed():
    base = design_strip()
    base["name"] = "colour_index_perturbed"
    base["colours"] = [0x0102, 0x7FFF, 0x8001, 0xFFFF, 0x0000]
    base["faces"] = base["faces"][:4] + [(1, 5, 4, 0)]
    return base


DESIGNS = [design_triangle(), design_strip(), design_boundaries(),
           design_vertex_perturbed(), design_colour_index_perturbed()]


def encode(design):
    name = design["name"]
    vertices = design["vertices"]
    faces = design["faces"]
    colours = design["colours"]
    count_v, count_f = len(vertices), len(faces)
    if not 3 <= count_v <= MAX_VERTICES or not 1 <= count_f <= MAX_VERTICES:
        die(f"{name}: vertex or face count out of bounds")
    if len(colours) != count_f:
        die(f"{name}: one colour per face is required")
    if any(not 0 <= c <= 0xFFFF for c in colours):
        die(f"{name}: colours must be unsigned 16-bit")
    if faces[0][0] != 1:
        die(f"{name}: the first face must be type 1 (the expected max+1 relies on it)")
    for _, a, b, c in faces:
        for index in (a, b, c):
            if not 0 <= index < count_v:
                die(f"{name}: face index {index} outside 0..{count_v - 1}")

    flags = bytearray()
    streams = {"x": bytearray(), "y": bytearray(), "z": bytearray()}
    deltas = {"x": [], "y": [], "z": []}
    previous = [0, 0, 0]
    for index, vertex in enumerate(vertices):
        bits = 0
        for axis, axis_name in enumerate("xyz"):
            delta = vertex[axis] - previous[axis]
            explicit = axis_name in design["zeroBits"].get(index, "")
            if delta != 0 or explicit:
                if delta == 0 and not explicit:
                    die(f"{name}: zero delta needs an explicit bit")
                bits |= 1 << axis
                streams[axis_name] += smart(delta)
                deltas[axis_name].append(delta)
        flags.append(bits)
        previous = list(vertex)

    types = bytearray()
    index_stream = bytearray()
    index_deltas = []
    state_a, state_b, state_c = 0, 0, 0
    for face_type, a, b, c in faces:
        types.append(face_type)
        if face_type == 1:
            steps = [a - state_c, b - a, c - b]
            for step in steps:
                index_stream += smart(step)
                index_deltas.append(step)
            state_a, state_b, state_c = a, b, c
        elif face_type == 2:
            if (a, b) != (state_a, state_c):
                die(f"{name}: type-2 face {(a, b, c)} does not continue (A, C)")
            step = c - state_c
            index_stream += smart(step)
            index_deltas.append(step)
            state_a, state_b, state_c = state_a, state_c, c
        elif face_type == 3:
            if (a, b) != (state_c, state_b):
                die(f"{name}: type-3 face {(a, b, c)} does not continue (C, B)")
            step = c - state_c
            index_stream += smart(step)
            index_deltas.append(step)
            state_a, state_b, state_c = state_c, state_b, c
        elif face_type == 4:
            if (a, b) != (state_b, state_a):
                die(f"{name}: type-4 face {(a, b, c)} does not continue (B, A)")
            step = c - state_c
            index_stream += smart(step)
            index_deltas.append(step)
            state_a, state_b, state_c = state_b, state_a, c
        else:
            die(f"{name}: face type {face_type} is not 1-4")

    colour_stream = b"".join(struct.pack(">H", c) for c in colours)
    # u16 V, u16 F, u8 texture count, u8 flags i57..i61 (all 0), u16 X, Y, Z and index stream lengths.
    footer = struct.pack(">HHBBBBBBHHHH", count_v, count_f, 0, 0, 0, 0, 0, 0,
                         len(streams["x"]), len(streams["y"]), len(streams["z"]), len(index_stream))
    if len(footer) != 18:
        die(f"{name}: footer is {len(footer)} bytes, expected 18")
    if footer[-2:] == b"\xff\xff":
        die(f"{name}: footer would route to the new format")
    data = bytes(flags) + bytes(types) + bytes(index_stream) + colour_stream \
        + bytes(streams["x"]) + bytes(streams["y"]) + bytes(streams["z"]) + footer
    if len(data) > MAX_FIXTURE_BYTES:
        die(f"{name}: {len(data)} bytes exceeds {MAX_FIXTURE_BYTES}")

    return data, {"x": deltas["x"], "y": deltas["y"], "z": deltas["z"], "index": index_deltas}


def expected_arrays(design):
    vertices, faces = design["vertices"], design["faces"]
    max_index = max(max(a, b, c) for _, a, b, c in faces)
    return {
        "vertexCount": len(vertices),
        "faceCount": len(faces),
        "maxVertexPlusOne": max_index + 1,
        "x": [v[0] for v in vertices],
        "y": [v[1] for v in vertices],
        "z": [v[2] for v in vertices],
        "a": [f[1] for f in faces],
        "b": [f[2] for f in faces],
        "c": [f[3] for f in faces],
        "colour": design["colours"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    (out / "generated-src").mkdir(parents=True, exist_ok=True)

    records = []
    coverage = {}
    for design in DESIGNS:
        data, deltas = encode(design)
        coverage[design["name"]] = deltas
        records.append({
            "name": design["name"],
            "bytes": len(data),
            "hex": data.hex(),
            "expected": expected_arrays(design),
        })

    boundary = coverage["signed_smart_boundaries"]
    for axis in "xyz":
        needed = {63, 64, -64, -65, 16383, -16384} if axis == "x" else {63, 64, -64, -65}
        missing = needed - set(boundary[axis])
        if missing:
            die(f"boundary fixture misses {sorted(missing)} on {axis}")
    if not {63, 64, -64, -65, 0} <= set(boundary["index"]):
        die("boundary fixture misses index deltas 63, 64, -64, -65 or 0")
    if 0 not in boundary["x"] or 0 not in boundary["y"]:
        die("boundary fixture misses an explicit zero coordinate delta")

    (out / "fixtures.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    lines = ["/* GENERATED by tools/encode_decode_fixtures.py. Original synthetic designs only. */",
             "final class DecodeFixtures {",
             "    static final String[] NAMES = {"]
    lines += [f"        \"{r['name']}\"," for r in records]
    lines += ["    };", "    static final String[] HEX = {"]
    lines += [f"        \"{r['hex']}\"," for r in records]
    lines += ["    };", "}"]
    (out / "generated-src" / "DecodeFixtures.java").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for r in records:
        print(f"fixture {r['name']}: {r['bytes']} bytes")


if __name__ == "__main__":
    main()
