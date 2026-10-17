#!/usr/bin/env python3
"""Fixture-only proof: one bounded, versioned grave/pile snapshot through native PlayerSave variables.

Writer and reader are separate JVMs. The reader decodes strictly and prints the canonical snapshot; this runner compares it
with an independent literal. Process-level only: no SaveQueue, Player.copy, timer simulation or production layout claim.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name('GraveCodecHelper.java')
REFUSED = 2
TIMEOUT = 120
CARRIER = Path('saves/gravelab.toml')
SENTINEL = b'unrelated sentinel, must survive refusal\n'
LITERAL = {
    'version': 1,
    'graves': [
        {'id': 'g1', 'account': 'alpha', 'kind': 'memorial_plaque', 'x': 3235, 'y': 3220, 'level': 0, 'remaining_seconds': 300, 'blessed': False},
        {'id': 'g2', 'account': 'alpha', 'kind': 'memorial_plaque', 'x': 3235, 'y': 3220, 'level': 0, 'remaining_seconds': 180, 'blessed': True},
        {'id': 'g3', 'account': 'beta', 'kind': 'memorial_plaque', 'x': 3240, 'y': 3220, 'level': 0, 'remaining_seconds': 120, 'blessed': False},
    ],
    'piles': [
        {'id': 'p1', 'source_account': 'alpha', 'visible_owner': 'alpha', 'item': 'coins', 'amount': 125, 'charges': 0, 'x': 3235, 'y': 3220, 'level': 0, 'reveal_ticks': 300, 'disappear_ticks': 60},
        {'id': 'p2', 'source_account': 'alpha', 'visible_owner': 'alpha', 'item': 'chaotic_rapier', 'amount': 1, 'charges': 12345, 'x': 3235, 'y': 3220, 'level': 0, 'reveal_ticks': 250, 'disappear_ticks': 60},
        {'id': 'p3', 'source_account': 'beta', 'visible_owner': '', 'item': 'logs', 'amount': 2, 'charges': 0, 'x': 3240, 'y': 3220, 'level': 0, 'reveal_ticks': 0, 'disappear_ticks': 40},
    ],
    'latest': {'alpha': 'g2', 'beta': 'g3'},
}
EXPECTED = {name: 'ACCEPTED_EQUAL' for name in ['valid_fixture_decodes_equal']}
EXPECTED.update({name: 'ACCEPTED' for name in ['amount_int_max_accepted', 'item_with_digits_accepted',
                                               'kind_with_digits_accepted', 'private_reveal_minus_one_accepted']})
EXPECTED.update({name: 'UNCHANGED' for name in ['caller_input_mutation_after_decode_unchanged',
                                                'caller_record_list_mutation_after_construct_unchanged',
                                                'replacement_snapshot_leaves_checkpoint_unchanged']})
EXPECTED.update({name: 'IMMUTABLE_REFUSED' for name in ['decoded_graves_add_immutable', 'encoded_grave_list_add_immutable',
                                                        'encoded_grave_map_put_immutable', 'encoded_latest_put_immutable',
                                                        'encoded_root_put_immutable']})
EXPECTED.update({name: 'REFUSED' for name in [
    'amount_overflow_refused', 'amount_zero_refused', 'bool_as_number_refused', 'counter_below_minus_one_refused',
    'double_number_refused', 'duplicate_grave_id_refused', 'duplicate_pile_id_refused', 'encode_null_refused',
    'graves_map_container_refused', 'graves_oversize_refused', 'latest_missing_grave_refused', 'latest_null_value_refused',
    'latest_uppercase_account_refused', 'latest_wrong_owner_refused', 'level_out_of_range_refused', 'missing_latest_refused',
    'latest_oversize_refused', 'missing_pile_field_refused', 'negative_charges_refused',
    'negative_grave_seconds_refused', 'negative_tile_refused', 'non_map_root_refused',
    'null_inside_piles_refused', 'null_snapshot_refused', 'null_visible_owner_refused', 'oversize_grave_id_refused',
    'piles_oversize_refused', 'piles_string_container_refused', 'private_owner_mismatch_refused',
    'private_reveal_zero_refused', 'public_with_reveal_refused', 'string_number_refused', 'tile_x_out_of_range_refused',
    'unknown_grave_field_refused', 'unknown_root_key_refused', 'unsafe_item_refused', 'unsafe_kind_refused',
    'unsupported_version_refused', 'uppercase_grave_id_refused', 'version_string_refused']})
# Each corruption edits only the fresh fixture file (exact single match) and must be refused without any rewrite.
CORRUPTIONS = {
    'schema_version_two': ('grave_lab_state = {version = 1,', 'grave_lab_state = {version = 2,'),
    'unknown_grave_field': ('blessed = false}, {id = "g2"', 'blessed = false, extra = 1}, {id = "g2"'),
    'missing_latest': (', latest = {alpha = "g2", beta = "g3"}}', '}'),
    'bool_as_number': ('blessed = true}', 'blessed = 1}'),
}


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def refuse_links(path):
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise SystemExit(f'Refuse a symlinked path component: {part}')


def tree(root):
    entries = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(directory) / name
            mode = p.lstat().st_mode
            key = p.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                entries[key] = {'link': os.readlink(p)}
            elif stat.S_ISREG(mode):
                entries[key] = {'sha256': sha_file(p)}
            else:
                entries[key] = {'kind': stat.S_IFMT(mode)}
    return entries


def jvm(java, cp, case_dir, label, args):
    out, err = case_dir / f'{label}.stdout', case_dir / f'{label}.stderr'
    code, timed_out = None, False
    with out.open('w') as stdout, err.open('w') as stderr:
        try:
            code = subprocess.run([str(java), '-cp', cp, 'GraveCodecHelper', *args], stdout=stdout, stderr=stderr,
                                  timeout=TIMEOUT).returncode
        except subprocess.TimeoutExpired:
            timed_out = True  # no retry: a duplicate native process would contaminate the fixture
    text = err.read_text()
    pid = re.search(r'^PROBE_PID ([0-9]+)$', text, re.MULTILINE)
    return {'label': label, 'exit': code, 'timed_out': timed_out, 'pid': int(pid.group(1)) if pid else None,
            'stdout': out.read_text(), 'stderr': text, 'logs': [rel(out), rel(err)]}


def run_case(run, java, cp, name, corrupt=None, guard=None, charge_control=False):
    case_dir = run / 'cases' / name
    case_dir.mkdir(parents=True)
    root = case_dir / 'root'
    failures, procs, snapshot = [], [], None
    writer = jvm(java, cp, case_dir, 'writer', ['write', str(root)])
    procs.append(writer)
    if writer['exit'] != 0 or writer['timed_out'] or writer['pid'] is None:
        failures.append(f'writer exit {writer["exit"]} timed_out {writer["timed_out"]}')
        return finish(name, 'FAILED', procs, failures, snapshot, root)
    (root / 'sentinel.txt').write_bytes(SENTINEL)
    carrier = root / CARRIER
    if guard == 'linked-member':
        carrier.rename(root / 'carrier-original.toml')
        carrier.symlink_to('../carrier-original.toml')
    elif guard == 'linked-ancestor':
        (root / 'saves').rename(root / 'saves-original')
        (root / 'saves').symlink_to('saves-original', target_is_directory=True)
    elif guard == 'oversize-member':
        with carrier.open('ab') as output:
            output.write(b'# padding\n' * 131073)
        assert carrier.stat().st_size > 1 << 20
    elif guard == 'fifo-member':
        carrier.unlink()
        os.mkfifo(carrier, 0o600)
    elif guard is not None:
        raise ValueError('Unknown file guard control')
    if corrupt:
        carrier = root / CARRIER
        text = carrier.read_text()
        old, new = CORRUPTIONS[corrupt]
        if text.count(old) != 1:
            raise RuntimeError(f'{corrupt}: expected one match in the native fixture, found {text.count(old)}')
        carrier.write_text(text.replace(old, new))
    if charge_control:
        text = carrier.read_text()
        assert text.count('charges = 12345') == 1
        carrier.write_text(text.replace('charges = 12345', 'charges = 0'))
    before = tree(root)
    reader = jvm(java, cp, case_dir, 'reader', ['read', str(root)])
    procs.append(reader)
    if tree(root) != before:
        failures.append('reader changed fixture bytes')
    if (root / 'sentinel.txt').read_bytes() != SENTINEL:
        failures.append('unrelated sentinel changed')
    if reader['timed_out'] or reader['pid'] is None:
        failures.append(f'reader timed_out {reader["timed_out"]} pid {reader["pid"]}')
    if corrupt or guard:
        if reader['exit'] != REFUSED or reader['stdout'].strip():
            failures.append(f'reader not refused: exit {reader["exit"]}')
    elif reader['exit'] != 0:
        failures.append(f'reader exit {reader["exit"]}: {reader["stderr"].strip()[-300:]}')
    else:
        snapshot = json.loads(reader['stdout'])
        if snapshot.get('native_loaded_accounts') != 1 or snapshot.get('inventories_empty') is not True:
            failures.append('reader did not load one native file with empty inventories')
        expected = json.loads(json.dumps(LITERAL))
        if charge_control:
            expected['piles'][1]['charges'] = 0
        if snapshot.get('snapshot') != expected:
            failures.append('decoded snapshot differs from the literal fixture')
        if charge_control and snapshot.get('snapshot') == LITERAL:
            failures.append('independent oracle did not observe the deliberately lost charge')
    return finish(name, 'FAILED' if failures else 'PASSED', procs, failures, snapshot, root)


def finish(name, outcome, procs, failures, snapshot, root):
    pids = [p['pid'] for p in procs]
    if len(set(pids)) != len(pids) or None in pids:
        failures.append(f'native processes not fresh and identified: {pids}')
        outcome = 'FAILED'
    return {'case': name, 'outcome': outcome, 'exit_codes': {p['label']: p['exit'] for p in procs},
            'timed_out': {p['label']: p['timed_out'] for p in procs}, 'pids': {p['label']: p['pid'] for p in procs},
            'logs': [log for p in procs for log in p['logs']], 'snapshot': snapshot, 'failures': failures,
            'fixture': rel(root) if root.exists() else None}


def run_checks(run, java, cp):
    case_dir = run / 'cases' / 'checks'
    case_dir.mkdir(parents=True)
    result = jvm(java, cp, case_dir, 'checks', ['checks'])
    failures = []
    if result['exit'] != 0 or result['timed_out'] or result['pid'] is None:
        failures.append(f'checks exit {result["exit"]} timed_out {result["timed_out"]}')
        outcomes = {}
    else:
        outcomes = json.loads(result['stdout'])['outcomes']
        failures += [f'{name}: got {outcomes.get(name)} expected {want}' for name, want in EXPECTED.items()
                     if outcomes.get(name) != want]
        failures += [f'unexpected check {name}' for name in outcomes if name not in EXPECTED]
    return {'case': 'checks', 'outcome': 'FAILED' if failures else 'PASSED', 'exit_codes': {'checks': result['exit']},
            'pids': {'checks': result['pid']}, 'logs': result['logs'], 'outcomes': outcomes, 'failures': failures}


def run_write_existing(run, java, cp, prior):
    case_dir = run / 'cases' / 'write-existing-refused'
    case_dir.mkdir(parents=True)
    root = run / 'cases' / prior / 'root'
    before = tree(root)
    result = jvm(java, cp, case_dir, 'writer', ['write', str(root)])
    failures = []
    if result['exit'] != REFUSED or result['stdout'].strip() or result['timed_out'] or result['pid'] is None:
        failures.append(f'writer over an existing root not refused: exit {result["exit"]} timed_out {result["timed_out"]}')
    if tree(root) != before:
        failures.append('refused writer changed the existing fixture')
    return {'case': 'write-existing-refused', 'outcome': 'FAILED' if failures else 'PASSED',
            'exit_codes': {'writer': result['exit']}, 'pids': {'writer': result['pid']}, 'logs': result['logs'],
            'failures': failures}


def freeze(run, jar_arg, sha, lock):
    refuse_links(lock)
    jar = jar_arg.resolve(strict=True)
    with open(lock, 'rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        frozen_jar = run / 'frozen' / 'void-server-dev.jar'
        frozen_jar.parent.mkdir()
        shutil.copyfile(jar, frozen_jar)
        src = run / 'src' / HELPER.name
        src.parent.mkdir()
        shutil.copyfile(HELPER, src)
        fcntl.flock(handle, fcntl.LOCK_UN)
    if sha_file(frozen_jar) != sha:
        raise SystemExit('frozen jar copy does not match the expected digest')
    return jar, frozen_jar, src


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-jar', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--java', required=True, type=Path)
    parser.add_argument('--javac', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256):
        parser.error('Expected a lowercase SHA-256 for the frozen server jar.')
    refuse_links(args.server_jar.absolute())
    original_jar = args.server_jar.resolve(strict=True)
    if sha_file(original_jar) != args.sha256:
        parser.error('Server jar does not match its expected digest.')
    runtime, lab = ROOT / '.runtime', ROOT / '.runtime' / 'native-grave-codec'
    lock = ROOT / '.runtime' / 'build.lock'
    refuse_links(runtime)
    refuse_links(lock)
    lab.mkdir(parents=True, exist_ok=True)
    refuse_links(lab)
    run = lab / str(time.time_ns())
    run.mkdir()  # refuses an existing run
    java, javac = args.java.resolve(strict=True), args.javac.resolve(strict=True)
    originals = {'jar': sha_file(original_jar), 'helper': sha_file(HELPER), 'runner': sha_file(Path(__file__))}
    jar, frozen_jar, src = freeze(run, args.server_jar, args.sha256, lock)
    if sha_file(src) != originals['helper']:
        raise SystemExit('Frozen helper does not match the captured source digest')
    classes = run / 'classes'
    classes.mkdir()
    with (run / 'compile.log').open('w') as log:
        subprocess.run([str(javac), '-cp', str(frozen_jar), '-d', str(classes), str(src)], stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=TIMEOUT)
    cp = f'{classes}{os.pathsep}{frozen_jar}'
    cases = [run_case(run, java, cp, 'valid-cold-roundtrip')]
    cases.append(run_checks(run, java, cp))
    cases.append(run_write_existing(run, java, cp, 'valid-cold-roundtrip'))
    cases += [run_case(run, java, cp, f'corrupt-{name}', corrupt=name) for name in CORRUPTIONS]
    cases += [run_case(run, java, cp, f'guard-{name}', guard=name) for name in
              ('linked-member', 'linked-ancestor', 'oversize-member', 'fifo-member')]
    cases.append(run_case(run, java, cp, 'control-charge-loss-detected', charge_control=True))
    failures = [f'{c["case"]}: {f}' for c in cases for f in c['failures']]
    pids = [pid for c in cases for pid in c.get('pids', {}).values()]
    if None in pids or len(set(pids)) != len(pids):
        failures.append(f'native PIDs not all non-null and unique across the run: {pids}')
    unchanged = {'jar': sha_file(original_jar) == originals['jar'] == args.sha256,
                 'helper': sha_file(HELPER) == originals['helper'], 'runner': sha_file(Path(__file__)) == originals['runner']}
    failures += [f'{k} changed during the run' for k, ok in unchanged.items() if not ok]
    summary = {'mode': 'native-grave-codec-v1-fixture', 'run': rel(run), 'all_passed': not failures and all(
        c['outcome'] == 'PASSED' for c in cases), 'failures': failures,
        'cases_run': len(cases), 'cases_passed': sum(c['outcome'] == 'PASSED' for c in cases),
        'server_jar_sha256': args.sha256, 'frozen_jar_sha256': sha_file(frozen_jar), 'originals_unchanged': unchanged,
        'tool_sha256': {'java': sha_file(java), 'javac': sha_file(javac)},
        'source_sha256': {'helper_before': originals['helper'], 'helper_after': sha_file(HELPER),
                          'runner_before': originals['runner'], 'runner_after': sha_file(Path(__file__))},
        'cases': cases}
    (run / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'summary': rel(run / 'summary.json'), 'all_passed': summary['all_passed'],
                      'cases_run': len(cases), 'cases_passed': summary['cases_passed'], 'failures': failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
