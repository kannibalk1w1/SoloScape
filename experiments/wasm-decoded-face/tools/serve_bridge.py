#!/usr/bin/env python3
"""Loopback-only server for the decoded-model bridge page. Reuses wasm-face's serve_loopback by path (not edited).
`--probe PORT` checks that this experiment's own page answers 200 with its own marker, not another service."""
import argparse
import importlib.util
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
SERVE = HERE.parent / "wasm-face" / "tools" / "serve_loopback.py"
MARKER = b"SoloScape WASM decoded face probe"


def load_serve():
    spec = importlib.util.spec_from_file_location("serve_loopback", SERVE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    parser.add_argument("--port-file")
    parser.add_argument("--probe", type=int)
    args = parser.parse_args()
    if args.probe is not None:
        with urllib.request.urlopen(f"http://127.0.0.1:{args.probe}/index.html", timeout=5) as response:
            body = response.read()
            if response.status != 200 or MARKER not in body:
                print(f"readiness probe failed on port {args.probe}", file=sys.stderr)
                sys.exit(1)
        return
    load_serve().serve(pathlib.Path(args.root), args.port_file)


if __name__ == "__main__":
    main()
