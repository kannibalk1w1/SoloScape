#!/usr/bin/env python3
"""Add one original Lab token to two fresh disposable cache copies and compare them. Not a safe allocator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from backport_catalogue import ROOT, canonical, digest, fingerprint
import local_dev

MANIFEST = ROOT / 'backport/manifests/lab-token.json'
TOOL = ROOT / 'backport/tooling/LabTokenCache.java'
BASELINE = ROOT / 'upstream/game-server/data/cache'
GRADLE = ROOT / '.gradle/caches/modules-2/files-2.1'
# Documented in docs/BACKPORT_CATALOGUE_20261017.md for the exact authorized baseline.
EXPECTED_BASELINE_FINGERPRINT = 'a4293ba42198ed092f8db93f2b9c2dc8e755db1d6c16bdd91f4dcf0ad68c43fd'
TARGET = 20179
ARCHIVE = 78
FILE = 211
CEILING = 32768
SOURCE_DIRS = ('upstream/game-server/game/src', 'upstream/game-server/engine/src', 'upstream/game-server/network/src',
               'upstream/game-server/cache/src', 'upstream/runelite-client/client/src')
DATA_DIR = ROOT / 'upstream/game-server/data'
# Pinned by the Displee 7.1.7 pom and already present in the local Gradle cache.
DEPENDENCIES = {
    'rs-cache-library': 'com.displee/rs-cache-library/7.1.7',
    'disio': 'com.displee/disio/2.2',
    'ant': 'org.apache.ant/ant/1.10.14',
    'lzma-java': 'com.github.jponge/lzma-java/1.3',
}
MUTABLE_DATA_DIRS = {'saves', 'errors', '.temp', 'cache', 'exchange'}
OCCUPIED = re.compile(r'(?<![0-9-])%d(?![0-9])' % TARGET)


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load_manifest(path=MANIFEST):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate manifest key: '+key)
            result[key] = value
        return result

    def reject_constant(_):
        raise ValueError('Non-finite manifest number.')

    data = path.read_bytes()
    if len(data) > 16384:
        raise ValueError('Manifest exceeds the fixed proof bound.')
    return validate_manifest(json.loads(data, object_pairs_hook=pairs, parse_constant=reject_constant))


def validate_manifest(raw):
    """Bind the manifest to this single fixed original definition, not a generic converter."""
    keys = {'schema_version', 'status', 'semantic_key', 'origin', 'target', 'definition',
            'dependencies', 'appearance_proof', 'enabled_in_production', 'production_toml_entry', 'limits'}
    if not isinstance(raw, dict) or set(raw) != keys:
        raise ValueError('Unexpected manifest shape.')
    if type(raw['schema_version']) is not int or raw['schema_version'] != 1:
        raise ValueError('Unexpected manifest schema.')
    if raw['semantic_key'] != 'lab_token' or raw['status'] != 'disposable-cache-format-proof':
        raise ValueError('Unexpected manifest identity.')
    target = {'kind': 'item', 'index': 19, 'archive': ARCHIVE, 'file': FILE,
              'id': TARGET, 'ceiling_exclusive': CEILING}
    definition = {'name': 'SoloScape Lab token', 'cost': 37, 'stackable': 1,
                  'opcodes': [2, 11, 12, 0], 'note_link': None, 'lend_link': None,
                  'stack_variants': None, 'wearable': False, 'animations': None,
                  'model': 'model0 numeric default; no model is loaded or claimed'}
    # Canonical JSON distinguishes bool/int as well as refusing missing or extra fields.
    if canonical(raw['target']) != canonical(target) or canonical(raw['definition']) != canonical(definition):
        raise ValueError('Manifest differs from the fixed encoded token.')
    if ARCHIVE * 256 + FILE != TARGET or not 0 <= TARGET < CEILING:
        raise ValueError('Candidate arithmetic or ceiling is invalid.')
    if raw['dependencies'] != [] or raw['enabled_in_production'] is not False:
        raise ValueError('Manifest must not enable production or add dependencies.')
    if raw['production_toml_entry'] is not None or raw['appearance_proof'] is not False:
        raise ValueError('Manifest must not claim production or appearance.')
    if not isinstance(raw['origin'], str) or not 1 <= len(raw['origin']) <= 512:
        raise ValueError('Bounded original provenance is required.')
    if not isinstance(raw['limits'], list) or not 1 <= len(raw['limits']) <= 8 or any(
            not isinstance(x, str) or not 1 <= len(x) <= 512 for x in raw['limits']):
        raise ValueError('Bounded limitations are required.')
    return raw


def guard_copy(path, lab):
    """Accepts only a real cache-copy directory below the lab; symlinks and outside paths are refused."""
    path, lab = path.absolute(), lab.absolute()
    if path.resolve() != path or lab.resolve() != lab:
        raise ValueError('Linked ancestors are refused.')
    if path.name != 'cache-copy' or path.is_symlink() or not path.is_dir():
        raise ValueError('Writes require a real directory named cache-copy.')
    if not path.resolve().is_relative_to(lab.resolve()):
        raise ValueError('Writes must stay inside .runtime/backport-lab.')


def check_candidate(occupied_ids):
    """Refuses any occupied or out-of-range candidate; the token ID must be absent from the baseline item namespace."""
    if not 0 <= TARGET < CEILING or TARGET in occupied_ids:
        raise ValueError('Candidate ID is occupied or outside the ceiling.')


def display(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def scan_reservations(data_dir, source_roots):
    """Finds literal candidate uses. A reservation in an item TOML blocks the proof; other hits are reported."""
    item_hits, other_hits, scanned = [], [], {}
    paths = []
    # Prune installation state before traversal, not after discovering its files.
    for current, directories, files in os.walk(data_dir, followlinks=False):
        current = Path(current)
        if current == data_dir:
            directories[:] = [name for name in directories if name not in MUTABLE_DATA_DIRS]
        for name in directories:
            if (current/name).is_symlink():
                raise ValueError('Linked source directory refused.')
        paths.extend(current/name for name in files if name.endswith('.toml'))
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError('Linked source input refused.')
        text = path.read_text(errors='replace')
        scanned[display(path)] = sha256_text(text)
        for number, line in enumerate(text.splitlines(), 1):
            if OCCUPIED.search(line):
                row = {'file': display(path), 'line': number, 'commented': line.lstrip().startswith('#')}
                (item_hits if path.name.endswith('.items.toml') else other_hits).append(row)
    source_hits = []
    for root in source_roots:
        for path in sorted(root.rglob('*')):
            if path.suffix not in ('.kt', '.java') or not path.is_file():
                continue
            if path.is_symlink():
                raise ValueError('Linked source input refused.')
            text = path.read_text(errors='replace')
            scanned[display(path)] = sha256_text(text)
            for number, line in enumerate(text.splitlines(), 1):
                if OCCUPIED.search(line):
                    source_hits.append({'file': display(path), 'line': number})
    if item_hits or source_hits:
        raise ValueError('Candidate ID is reserved by item data or source: ' + json.dumps(item_hits + source_hits))
    return {'item_toml_reservations': 0, 'other_toml_occurrences': other_hits,
            'source_literal_occurrences': 0, 'inspected_files': len(scanned),
            'inspected_files_sha256': hashlib.sha256(canonical(scanned)).hexdigest()}


def resolve_dependency(coordinate):
    """Finds exactly one pinned jar under its bounded Gradle coordinate directory."""
    directory = GRADLE / coordinate
    if not directory.is_dir():
        raise ValueError('Missing pinned dependency directory: ' + coordinate)
    output = subprocess.run(['rg', '--files', '--glob', '*.jar', str(directory)], check=True, capture_output=True, text=True).stdout
    jars = [Path(line) for line in output.splitlines() if line]
    if len(jars) != 1 or jars[0].is_symlink():
        raise ValueError('Expected exactly one regular jar for ' + coordinate)
    return jars[0]


def copy_baseline(destination):
    """Copies only the regular files of the authorized baseline into a new private directory."""
    destination = destination.absolute()
    if destination.resolve() != destination or destination.is_relative_to(BASELINE.resolve()):
        raise ValueError('Copy destination must not be linked or inside the baseline.')
    before = fingerprint(BASELINE)
    if BASELINE.resolve() != BASELINE.absolute():
        raise ValueError('Linked baseline ancestors refused.')
    entries = list(BASELINE.iterdir())
    if {p.name for p in entries} != set(before):
        raise ValueError('Unexpected file in baseline cache.')
    if any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError('Baseline cache must contain only regular files.')
    destination.mkdir(parents=True, exist_ok=False)
    for entry in entries:
        shutil.copyfile(entry, destination / entry.name)
    if fingerprint(destination) != before:
        raise ValueError('Cache copy differs from its baseline.')


def run_once(run_dir, classes, classpath, java, lab):
    cache = run_dir / 'cache-copy'
    copy_baseline(cache)
    guard_copy(cache, lab)
    report = run_dir / 'report.json'
    result = subprocess.run([str(java), '-Djava.awt.headless=true', '-cp', os.pathsep.join((str(classes), classpath)),
                             'LabTokenCache', str(cache), str(report), str(lab)], cwd=ROOT, capture_output=True, text=True)
    (run_dir/'helper.stdout').write_text(result.stdout)
    (run_dir/'helper.stderr').write_text(result.stderr)
    result.check_returncode()
    return json.loads(report.read_text()), result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-jar', type=Path, default=ROOT / 'upstream/game-server/cache/build/libs/cache-dev.jar')
    parser.add_argument('--server-jar', type=Path, default=ROOT / 'upstream/game-server/game/build/libs/void-server-dev.jar')
    parser.add_argument('--client-jar', type=Path, default=ROOT / 'upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar')
    parser.add_argument('--java-home', type=Path, default=ROOT / '.runtime/jdks/jdk21')
    args = parser.parse_args()
    with local_dev.build_lock(shared=True):
        perform(args)


def perform(args):
    manifest = load_manifest()
    manifest_hash = digest(MANIFEST)
    if BASELINE.is_symlink() or not BASELINE.is_dir():
        raise ValueError('The authorized baseline must be a real directory.')
    baseline_before = fingerprint(BASELINE)
    fingerprint_sha = hashlib.sha256(canonical(baseline_before)).hexdigest()
    if fingerprint_sha != EXPECTED_BASELINE_FINGERPRINT:
        raise ValueError('Baseline fingerprint differs from the documented authorized cache.')

    jars = {'cache': args.cache_jar, 'server': args.server_jar, 'client': args.client_jar}
    if any(p.is_symlink() or not p.is_file() for p in jars.values()):
        raise ValueError('Supply regular locally built native jars.')
    deps = {name: resolve_dependency(coord) for name, coord in DEPENDENCIES.items()}
    jar_before = {name: digest(p) for name, p in {**jars, **deps}.items()}
    tool_hash = digest(TOOL)
    wrapper_hash = digest(Path(__file__))
    reservations = scan_reservations(DATA_DIR, [ROOT / s for s in SOURCE_DIRS])

    lab = ROOT / '.runtime/backport-lab'
    lab.mkdir(parents=True, exist_ok=True)
    if lab.resolve() != lab.absolute():
        raise ValueError('Linked lab ancestors refused before copying.')
    stamp = 'lab-token-' + str(time.time_ns())
    run_root = lab / stamp
    run_root.mkdir(exist_ok=False)
    classes = run_root / 'classes'
    classes.mkdir()
    frozen = run_root / 'inputs'
    frozen.mkdir()
    input_copies = []
    for name, path in {**jars, **deps}.items():
        copy = frozen / (name+'.jar')
        shutil.copyfile(path, copy)
        if digest(copy) != jar_before[name]:
            raise ValueError('Jar changed while freezing input: '+name)
        input_copies.append(copy)
    classpath = os.pathsep.join(map(str, input_copies))
    java_bin = args.java_home / 'bin/java'
    subprocess.run([str(args.java_home / 'bin/javac'), '-cp', classpath, '-d', str(classes), str(TOOL)], check=True)

    reports = {}
    summaries = {}
    for label in ('run-a', 'run-b'):
        run_dir = run_root / label
        run_dir.mkdir()
        reports[label], summaries[label] = run_once(run_dir, classes, classpath, java_bin, lab)

    # Original negative controls operate only on our candidate/copies, never on owner data.
    control = run_root / 'control-corrupt'
    control.mkdir()
    corrupt = control / 'cache-copy'
    shutil.copytree(run_root/'run-a'/'cache-copy', corrupt)
    guard_copy(corrupt, lab)
    with (corrupt/'main_file_cache.idx19').open('rb') as handle:
        handle.seek(ARCHIVE*6)
        entry = handle.read(6)
    if len(entry) != 6:
        raise ValueError('Control has no target archive pointer.')
    length, sector = int.from_bytes(entry[:3], 'big'), int.from_bytes(entry[3:], 'big')
    with (corrupt/'main_file_cache.dat2').open('r+b') as handle:
        handle.seek(sector*520)
        header = handle.read(8)
        if len(header) != 8 or int.from_bytes(header[:2], 'big') != ARCHIVE or header[2:4] != b'\0\0' or header[7] != 19 or length < 128:
            raise ValueError('Control target is not an intact archive78 first sector.')
        offset = sector*520+8+64
        handle.seek(offset)
        old = handle.read(1)
        handle.seek(offset)
        handle.write(bytes([old[0] ^ 0xff]))
    verify_report = control/'refusal.json'
    command = [str(java_bin), '-Djava.awt.headless=true', '-cp', os.pathsep.join((str(classes), classpath)),
               'LabTokenCache', '--verify', str(corrupt), str(verify_report), str(lab)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (control/'helper.stdout').write_text(result.stdout)
    (control/'helper.stderr').write_text(result.stderr)
    refusal = json.loads(verify_report.read_text())
    if result.returncode == 0 or refusal.get('refused_at') != 'crc-gate' or refusal['gate']['crc_ok'] is not False or refusal['gate']['footer_ok'] is not True:
        raise ValueError('Corrupt-payload control did not reach the actual CRC refusal.')
    candidate = run_root/'run-a'/'cache-copy'
    candidate_before = fingerprint(candidate)
    occupied = subprocess.run([str(java_bin), '-Djava.awt.headless=true', '-cp',
                   os.pathsep.join((str(classes), classpath)), 'LabTokenCache', str(candidate),
                   str(run_root/'occupied-report.json'), str(lab)], cwd=ROOT, capture_output=True, text=True)
    (run_root/'occupied-refusal.log').write_text(occupied.stdout+occupied.stderr)
    if occupied.returncode == 0 or 'Candidate item slot is already occupied' not in occupied.stderr or fingerprint(candidate) != candidate_before:
        raise ValueError('Occupied-candidate refusal did not preserve its cache.')
    controls = {'corrupt_payload': {'exit': result.returncode, 'changed_offset': offset,
                 'old_byte': old[0], 'new_byte': old[0] ^ 0xff, 'refusal': refusal},
                'occupied_candidate': {'exit': occupied.returncode, 'cache_unchanged': True}}

    baseline_after = fingerprint(BASELINE)
    if (baseline_after != baseline_before or {name: digest(p) for name, p in {**jars, **deps}.items()} != jar_before
            or digest(TOOL) != tool_hash or digest(Path(__file__)) != wrapper_hash
            or digest(MANIFEST) != manifest_hash
            or scan_reservations(DATA_DIR, [ROOT / s for s in SOURCE_DIRS]) != reservations):
        raise ValueError('An input or tool changed during the proof; report withheld.')

    a, b = reports['run-a'], reports['run-b']
    deterministic = {key: a[key] == b[key] for key in ('new_entry_sha256', 'item_namespace_after_sha256', 'encoded_bytes', 'opcodes')}
    if not all(deterministic.values()):
        raise ValueError('Two fresh builds disagree: ' + json.dumps(deterministic))

    summary = {
        'schema_version': 1,
        'semantic_key': manifest['semantic_key'],
        'target': manifest['target'],
        'manifest_sha256': manifest_hash,
        'baseline_fingerprint_sha256': fingerprint_sha,
        'baseline_is_authorized_reference': True,
        'input_sha256': jar_before,
        'tool_sha256': {'LabTokenCache.java': tool_hash, 'backport_lab_token.py': wrapper_hash},
        'candidate_absent_from_baseline_and_toml': reservations,
        'builds': {'run-a': a, 'run-b': b},
        'controls': controls,
        'deterministic_equal': deterministic,
        'limits': ['One original definition in disposable copies only; the authorized baseline is never written.',
                   'Model0 numeric default; no appearance, packet, controller, render or save claim.',
                   'Byte determinism is claimed only for the new entry and decoded namespace, not for the container.',
                   'Source consumer audit is partial: client item lookup is id-keyed and server array size follows the cache, but full growth/packet audits remain open.'],
    }
    (run_root / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'summary': str(run_root / 'summary.json'), 'deterministic_equal': deterministic,
                      'new_entry_sha256': a['new_entry_sha256'], 'item_entries_after': a['item_entries_after']}, indent=2))


if __name__ == '__main__':
    main()
