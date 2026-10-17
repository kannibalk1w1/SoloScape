#!/usr/bin/env python3
"""Fixture-only process-exit proof for an immutable-generation account checkpoint.

Every case uses a fresh baseline root and separate JVMs for baseline, attempt, and recovery. Failures are retained.
This is process-exit ordering evidence only; fsync calls are not power-loss or live-world acceptance.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name('GraveCheckpointHelper.java')
POINTS = ['alpha-write', 'beta-write', 'ledger-write', 'manifest-write',
          'generation-rename', 'pointer-temp-fsync', 'pointer-replace', 'parent-fsync']
AFTER_POINTS = {'pointer-replace', 'parent-fsync'}
HALTED, REFUSED = 75, 2
BASELINE_STATE = {'generation': 'gen-000001', 'state': 'BASELINE', 'alpha_coins': 10, 'alpha_version': 1,
                  'beta_coins': 0, 'beta_version': 1, 'ledger_pile_coins': 2, 'ledger_remaining_ticks': 1000,
                  'ledger_version': 1, 'total_coins': 12, 'native_loaded_accounts': 2}
AFTER_STATE = {'generation': 'gen-000002', 'state': 'AFTER', 'alpha_coins': 10, 'alpha_version': 2,
               'beta_coins': 2, 'beta_version': 2, 'ledger_pile_coins': 0, 'ledger_remaining_ticks': 0,
               'ledger_version': 2, 'total_coins': 12, 'native_loaded_accounts': 2}
SENTINEL = b'unrelated sentinel, must survive refusal\n'
EXPECTED_CASES = len(POINTS) + 1 + 5


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def snapshot(root):
    entries = {}
    for path in sorted(root.rglob('*')):
        key = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[key] = {'symlink_to': os.readlink(path)}
        elif path.is_file():
            entries[key] = {'bytes': path.stat().st_size, 'sha256': sha_file(path)}
        else:
            entries[key] = {'dir': True}
    return entries


def helper(java, cp, case, name, mode, *args):
    out, err = case / f'{name}.stdout', case / f'{name}.stderr'
    with out.open('w') as stdout, err.open('w') as stderr:
        code = subprocess.run([str(java), '-cp', cp, 'GraveCheckpointHelper', mode, *args],
                              stdout=stdout, stderr=stderr, timeout=120).returncode
    error = err.read_text()
    pid = re.search(r'^PROBE_PID ([0-9]+)$', error, re.MULTILINE)
    if pid is None:
        raise RuntimeError(f'{mode} did not identify its native process; evidence retained in {case}')
    return {'step': name, 'exit': code, 'pid': int(pid.group(1)), 'stdout': out.read_text(), 'stderr': error,
            'logs': [rel(out), rel(err)]}


def positive_case(run, java, cp, name, point):
    case = run / 'cases' / name
    case.mkdir(parents=True)
    root = case / 'root'
    baseline = helper(java, cp, case, 'baseline', 'baseline', str(root))
    attempt = helper(java, cp, case, 'attempt', 'attempt', str(root), point or 'none')
    tree = snapshot(root)
    recover = helper(java, cp, case, 'recover', 'recover', str(root))
    expected = AFTER_STATE if point is None or point in AFTER_POINTS else BASELINE_STATE
    failures = []
    if len({baseline['pid'], attempt['pid'], recover['pid']}) != 3:
        failures.append('baseline/attempt/recovery did not identify three distinct native processes')
    if baseline['exit'] != 0:
        failures.append('baseline did not complete')
    if point and (attempt['exit'] != HALTED or f'HALT {point}' not in attempt['stdout']):
        failures.append(f'halt at {point} not reached (exit {attempt["exit"]})')
    if not point and attempt['exit'] != 0:
        failures.append('no-fault attempt did not complete')
    recovered = None
    if recover['exit'] != 0:
        failures.append(f'recovery exit {recover["exit"]}')
    else:
        recovered = json.loads(recover['stdout'])
        for key, wanted in expected.items():
            if recovered.get(key) != wanted:
                failures.append(f'recovered {key}={recovered.get(key)} expected {wanted}')
    return {'case': name, 'halt_point': point, 'expected': expected, 'recovered': recovered,
            'exit_codes': {'baseline': baseline['exit'], 'attempt': attempt['exit'], 'recover': recover['exit']},
            'pids': {'baseline': baseline['pid'], 'attempt': attempt['pid'], 'recover': recover['pid']},
            'logs': baseline['logs'] + attempt['logs'] + recover['logs'], 'tree_after_attempt': tree,
            'failures': failures}


def corruption_case(run, java, cp, name, mutate):
    case = run / 'cases' / name
    case.mkdir(parents=True)
    root = case / 'root'
    baseline = helper(java, cp, case, 'baseline', 'baseline', str(root))
    # Halting at generation-rename leaves a complete orphan gen-000002 while CURRENT still names the baseline.
    attempt = helper(java, cp, case, 'attempt', 'attempt', str(root), 'generation-rename')
    sentinel = root / 'sentinel.txt'
    sentinel.write_bytes(SENTINEL)
    mutate(root)
    recover = helper(java, cp, case, 'recover', 'recover', str(root))
    failures = []
    if len({baseline['pid'], attempt['pid'], recover['pid']}) != 3:
        failures.append('baseline/attempt/recovery did not identify three distinct native processes')
    if baseline['exit'] != 0:
        failures.append('baseline did not complete')
    if attempt['exit'] != HALTED or 'HALT generation-rename' not in attempt['stdout']:
        failures.append('orphan preparation halt not reached')
    if recover['exit'] != REFUSED:
        failures.append(f'corrupted state was not refused (exit {recover["exit"]})')
    if recover['stdout'].strip():
        failures.append('corrupted state printed a recovered state')
    if sentinel.read_bytes() != SENTINEL:
        failures.append('unrelated sentinel changed')
    return {'case': name, 'exit_codes': {'baseline': baseline['exit'], 'attempt': attempt['exit'], 'recover': recover['exit']},
            'pids': {'baseline': baseline['pid'], 'attempt': attempt['pid'], 'recover': recover['pid']},
            'refusal': recover['stderr'].strip(), 'logs': baseline['logs'] + attempt['logs'] + recover['logs'],
            'failures': failures}


def mutate_account(root):
    with (root / 'state/generations/gen-000001/alpha.toml').open('ab') as account:
        account.write(b'# tampered\n')


def mutate_manifest_pointer(root):
    current = root / 'state/CURRENT'
    text = current.read_text()
    digest = re.search(r'manifest_sha256 = ([0-9a-f]{64})', text).group(1)
    flipped = ('1' if digest[0] == '0' else '0') + digest[1:]
    current.write_text(text.replace(digest, flipped))


def mutate_symlink_member(root):
    member = root / 'state/generations/gen-000001/beta.toml'
    member.unlink()
    os.symlink('../../../sentinel.txt', member)


def mutate_traversal_pointer(root):
    current = root / 'state/CURRENT'
    current.write_text(re.sub(r'generation = gen-[0-9]{6}', 'generation = ../partials', current.read_text()))


def mutate_ancestor_link(root):
    # Leaf and members are real; only the generations ancestor is a symlink to the same bytes.
    generations = root / 'state/generations'
    generations.rename(root / 'state/real-generations')
    os.symlink('real-generations', generations)


CORRUPTIONS = [
    ('corrupt-changed-account-bytes', mutate_account),
    ('corrupt-altered-manifest-pointer', mutate_manifest_pointer),
    ('corrupt-symlink-member', mutate_symlink_member),
    ('corrupt-traversal-pointer', mutate_traversal_pointer),
    ('corrupt-linked-generations-ancestor', mutate_ancestor_link),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-jar', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--java', required=True, type=Path)
    parser.add_argument('--javac', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256):
        parser.error('Expected a lowercase SHA-256 for the trusted locally built server jar.')
    jar = args.server_jar.resolve(strict=True)
    if sha_file(jar) != args.sha256:
        parser.error('Server jar does not match its expected digest.')
    runtime = ROOT / '.runtime'
    lab = runtime / 'native-grave-checkpoint'
    for ancestor in (runtime, lab):
        if ancestor.is_symlink():
            parser.error(f'Refuse a symlinked lab ancestor: {ancestor}')
    lab.mkdir(parents=True, exist_ok=True)
    run = lab / str(time.time_ns())
    run.mkdir()  # refuses an existing run
    (run / 'cases').mkdir()
    classes = run / 'classes'
    classes.mkdir()
    java = args.java.resolve(strict=True)
    with (run / 'compile.log').open('w') as log:
        subprocess.run([str(args.javac.resolve(strict=True)), '-cp', str(jar), '-d', str(classes), str(HELPER)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    cp = f'{classes}{os.pathsep}{jar}'

    cases = [positive_case(run, java, cp, f'halt-{index}-{point}', point) for index, point in enumerate(POINTS, 1)]
    cases.append(positive_case(run, java, cp, 'control-no-fault', None))
    cases += [corruption_case(run, java, cp, name, mutate) for name, mutate in CORRUPTIONS]

    failures = [f'{case["case"]}: {failure}' for case in cases for failure in case['failures']]
    if len(cases) != EXPECTED_CASES:
        failures.append(f'expected {EXPECTED_CASES} cases, ran {len(cases)}')
    jar_unchanged = sha_file(jar) == args.sha256
    if not jar_unchanged:
        failures.append('server jar changed during the run')
    summary = {
        'mode': 'native-grave-checkpoint-process-exit-proof',
        'scope': 'Fixture-only process-exit ordering. Not power-loss durability, not live world, not production storage.',
        'run': rel(run),
        'all_passed': not failures,
        'failures': failures,
        'cases_run': len(cases),
        'server_jar_sha256': args.sha256,
        'server_jar_unchanged_after_run': jar_unchanged,
        'helper_source_sha256': sha_file(HELPER),
        'runner_sha256': sha_file(Path(__file__)),
        'cases': cases,
    }
    (run / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'summary': rel(run / 'summary.json'), 'all_passed': summary['all_passed'],
                      'cases_run': len(cases), 'failures': failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
