#!/usr/bin/env python3
"""Serve one directory on an ephemeral 127.0.0.1 port and write the bound port to a file.

Only the directory given with --root is reachable. `--probe PORT` checks positive readiness: the
expected page must answer 200 with its marker, so an unrelated service on a port is not accepted.
"""
import argparse
import functools
import http.server
import pathlib
import sys
import urllib.request

MARKER = b"SoloScape WASM material probe"


def serve(root, port_file):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    pathlib.Path(port_file).write_text(str(server.server_address[1]), encoding="utf-8")
    server.serve_forever()


def probe(port):
    url = f"http://127.0.0.1:{port}/index.html"
    with urllib.request.urlopen(url, timeout=5) as response:
        body = response.read()
        if response.status != 200 or MARKER not in body:
            raise SystemExit(f"readiness probe failed on port {port}")
    print(f"ready on 127.0.0.1:{port}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path)
    parser.add_argument("--port-file", type=pathlib.Path)
    parser.add_argument("--probe", type=int)
    args = parser.parse_args()
    if args.probe is not None:
        probe(args.probe)
        return 0
    serve(args.root, args.port_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
