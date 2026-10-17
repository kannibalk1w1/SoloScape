#!/usr/bin/env python3
"""Records the exact sources, reused tools, inputs, tool versions, closures, fixtures and module sizes of a run.

Writes build/provenance.json and a copy into the private log directory. Reused files are hashed at their source
(read-only) and their copies under build/ must match byte for byte.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
WASM_FACE = HERE.parent / "wasm-face"
DECODE = HERE.parent / "wasm-model-decode"
REUSED_FACE = ["FaceMesh", "FaceRig", "FaceScene", "FaceCounters", "ExtractedRig"]
REUSED_NATIVE = ["ClipScene"]


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def gz(path):
    return len(gzip.compress(pathlib.Path(path).read_bytes(), compresslevel=9, mtime=0))


def tool(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=60)
        text = (result.stdout + result.stderr).strip().splitlines()
        return text[0] if text else ""
    except (OSError, subprocess.SubprocessError) as error:
        return f"unavailable: {error}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=pathlib.Path)
    parser.add_argument("--log", required=True, type=pathlib.Path)
    parser.add_argument("--jdk", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--chromium", required=True)
    args = parser.parse_args()
    build = args.build

    sources = {}
    for folder in ("src/shared/java", "src/jvm/java", "src/browser/java"):
        for path in sorted((HERE / folder).glob("*.java")):
            sources[str(path.relative_to(HERE))] = sha(path)
    for name in ("tools/encode_bridge_fixtures.py", "tools/check_bridge_evidence.py", "tools/serve_bridge.py",
                 "tools/record_bridge_provenance.py", "web/index.html", "build.gradle", "settings.gradle", "run.sh", "README.md", ".gitignore"):
        sources[name] = sha(HERE / name)

    reused = {}
    for name in REUSED_FACE:
        origin = WASM_FACE / "src" / "shared" / "java" / f"{name}.java"
        copy = build / "reused" / f"{name}.java"
        if sha(origin) != sha(copy):
            sys.exit(f"provenance: reused copy {copy} differs from {origin}")
        reused[str(origin.relative_to(HERE.parent))] = sha(origin)
    for name in REUSED_NATIVE:
        origin = WASM_FACE / "src" / "shared" / "java" / f"{name}.java"
        copy = build / "reused-native" / f"{name}.java"
        if sha(origin) != sha(copy):
            sys.exit(f"provenance: reused copy {copy} differs from {origin}")
        reused[str(origin.relative_to(HERE.parent))] = sha(origin)
    origin = WASM_FACE / "src" / "jvm" / "java" / "NativeFace.java"
    if sha(origin) != sha(build / "reused-native" / "NativeFace.java"):
        sys.exit("provenance: NativeFace copy differs from its source")
    reused[str(origin.relative_to(HERE.parent))] = sha(origin)
    for path in (WASM_FACE / "tools" / "extract_face_closure.py", WASM_FACE / "tools" / "browser_probe.mjs",
                 WASM_FACE / "tools" / "serve_loopback.py",
                 HERE.parent / "wasm-triangle" / "tools" / "extract_triangle_closure.py",
                 DECODE / "tools" / "extract_decode_closure.py", DECODE / "tools" / "encode_decode_fixtures.py"):
        reused[str(path.relative_to(HERE.parent))] = sha(path)

    closures = {}
    for part in ("face", "decode"):
        path = build / part / "closure.json"
        closures[part] = {"sha256": sha(path), "report": json.loads(path.read_text(encoding="utf-8"))}

    fixtures = json.loads((build / "fixtures.json").read_text(encoding="utf-8"))
    sizes = {}
    for name in ("bridge.wasm", "bridge.wasm-runtime.js"):
        path = build / "web-out" / name
        sizes[name] = {"raw": path.stat().st_size, "gzip9": gz(path), "sha256": sha(path)}

    report = {
        "sources": sources,
        "reusedTools": reused,
        "inputs": json.loads((build / "inputs.json").read_text(encoding="utf-8")),
        "closures": closures,
        "fixtures": [{"name": f["name"], "bytes": f["bytes"], "sha256": hashlib.sha256(bytes.fromhex(f["hex"])).hexdigest()}
                     for f in fixtures],
        "checker": json.loads((build / "checker-summary.json").read_text(encoding="utf-8")),
        "moduleSizes": sizes,
        "tools": {
            "java": tool([args.jdk + "/bin/java", "-version"]),
            "javac": tool([args.jdk + "/bin/javac", "-version"]),
            "node": tool([args.node, "--version"]),
            "chromium": tool([args.chromium, "--version"]),
            "teavm": "0.16.0 (org.teavm plugin and teavm-jso, offline Gradle cache)",
        },
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    (build / "provenance.json").write_text(text, encoding="utf-8")
    args.log.mkdir(parents=True, exist_ok=True)
    (args.log / "provenance.json").write_text(text, encoding="utf-8")
    shutil.copyfile(build / "checker-summary.json", args.log / "checker-summary.json")
    print(text)


if __name__ == "__main__":
    main()
