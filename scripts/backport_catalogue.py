#!/usr/bin/env python3
"""Inspect supplied 634 definition slots read-only. This does not allocate safe IDs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
NAMESPACES = {'item': (19, 8), 'npc': (18, 7), 'object': (16, 8), 'sequence': (20, 7)}
SOURCE_FILES = (
    'CacheLoader.kt', 'FileCache.kt', 'ReadOnlyCache.kt', 'Index.kt',
    'definition/decoder/ItemDecoder.kt', 'definition/decoder/NPCDecoder.kt',
    'definition/decoder/ObjectDecoder.kt', 'definition/decoder/AnimationDecoder.kt',
)


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def fingerprint(cache):
    if cache.is_symlink() or not cache.is_dir():
        raise ValueError('Supply a real cache directory, not a symbolic link.')
    paths = sorted(p for p in cache.iterdir() if re.fullmatch(r'main_file_cache\.(dat2|idx[0-9]+)', p.name))
    required = {'main_file_cache.dat2', 'main_file_cache.idx255'} | {
        f'main_file_cache.idx{index}' for index, _ in NAMESPACES.values()}
    if not required.issubset({p.name for p in paths}):
        raise ValueError('The supplied cache is missing required 634 index files.')
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('Cache files must be regular files, not links.')
    return {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in paths}


def validate_slots(raw):
    if not isinstance(raw, dict) or type(raw.get('schema_version')) is not int or raw['schema_version'] != 1 or not isinstance(raw.get('namespaces'), list):
        raise ValueError('Invalid catalogue schema.')
    result = {}
    for row in raw['namespaces']:
        if not isinstance(row, dict) or not isinstance(row.get('kind'), str):
            raise ValueError('Invalid namespace record.')
        kind = row['kind']
        if kind not in NAMESPACES or kind in result:
            raise ValueError('Unknown or duplicate namespace.')
        index, shift = NAMESPACES[kind]
        if type(row.get('index')) is not int or type(row.get('archive_shift')) is not int or (row['index'], row['archive_shift']) != (index, shift):
            raise ValueError('Namespace does not match the inspected native codec.')
        ids = row.get('occupied_ids')
        if not isinstance(ids, list) or not ids or any(type(n) is not int or not 0 <= n <= 2147483647 for n in ids):
            raise ValueError('Invalid occupied ID list.')
        if ids != sorted(set(ids)):
            raise ValueError('Occupied IDs must be unique and sorted.')
        result[kind] = dict(row, count=len(ids), highest_occupied_id=ids[-1])
    if set(result) != set(NAMESPACES):
        raise ValueError('Missing definition namespace.')
    return result


def inspect(cache, jar, source, java_home, output):
    # Resolve only after rejecting direct symlinks, so input bytes remain explicit.
    if jar.is_symlink() or not jar.is_file():
        raise ValueError('Supply a built native server jar, not a symbolic link.')
    before = fingerprint(cache)
    cache = cache.resolve()
    jar = jar.resolve()
    private = ROOT / '.runtime/backport-lab'
    private.mkdir(parents=True, exist_ok=True)
    # Outputs are deliberately confined to the ignored lab and outside every input.
    output = output.absolute()
    resolved = output.resolve()
    if not resolved.is_relative_to(private.resolve()) or resolved.is_relative_to(cache) or cache.is_relative_to(resolved.parent):
        raise ValueError('Write the report inside .runtime/backport-lab, outside the cache.')
    if output.exists() or output.is_symlink():
        raise ValueError('Report already exists; choose a new output.')
    source_root = source / 'cache/src/main/kotlin/world/gregs/voidps/cache'
    provenance = {name: digest(source_root / name) for name in SOURCE_FILES}
    jar_hash = digest(jar)
    tool = ROOT / 'backport/tooling/CacheSlots.java'
    tool_hash = digest(tool)
    inspector_hash = digest(Path(__file__))
    with tempfile.TemporaryDirectory(prefix='inspect-', dir=private) as temporary:
        build = Path(temporary)
        raw_path = build / 'slots.json'
        subprocess.run([str(java_home / 'bin/javac'), '-cp', str(jar), '-d', str(build), str(tool)], check=True)
        subprocess.run([str(java_home / 'bin/java'), '-cp', os.pathsep.join((str(build), str(jar))),
                        'CacheSlots', str(cache), str(raw_path)], check=True)
        slots = validate_slots(json.loads(raw_path.read_text()))
    if (fingerprint(cache) != before or digest(jar) != jar_hash
            or provenance != {name: digest(source_root / name) for name in SOURCE_FILES}
            or digest(tool) != tool_hash or digest(Path(__file__)) != inspector_hash):
        raise ValueError('An input changed during inspection; report withheld.')
    report = {'schema_version': 1, 'mode': 'read-only-reference-table-occupancy',
              'supplied_revision_contract': 634, 'revision_detected': False, 'cache_files': before,
              'cache_fingerprint_sha256': hashlib.sha256(canonical(before)).hexdigest(),
              'server_jar_sha256': jar_hash, 'native_source_sha256': provenance,
              'tool_sha256': tool_hash, 'inspector_sha256': inspector_hash, 'namespaces': slots,
              'allocation_allowed': False,
              'limits': ['Metadata occupancy only; no definition/asset decoding or cache integrity certification.',
                         'No ID allocation. Server semantic definitions, client overrides, consumer limits and saved IDs still need audit.',
                         'A missing slot is not a safe target. Cache revision compatibility is supplied, not auto-detected.',
                         'Source digests are recorded separately; this does not prove an arbitrary jar was built from those sources.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as out:
        json.dump(report, out, indent=2, sort_keys=True)
        out.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--server-jar', type=Path, required=True)
    parser.add_argument('--server-source', type=Path, default=ROOT / 'upstream/game-server')
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / f'.runtime/backport-lab/catalogue-{time.time_ns()}.json')
    args = parser.parse_args()
    report = inspect(args.cache, args.server_jar, args.server_source, args.java_home, args.output)
    print(json.dumps({'output': str(args.output), 'cache_fingerprint_sha256': report['cache_fingerprint_sha256'],
                      'counts': {kind: row['count'] for kind, row in report['namespaces'].items()}, 'allocation_allowed': False}, indent=2))


if __name__ == '__main__':
    main()
