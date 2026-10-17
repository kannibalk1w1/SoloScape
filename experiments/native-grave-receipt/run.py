#!/usr/bin/env python3
"""Fixture-only process-exit proof: whole-pile receipts inside per-account PlayerSave variables.

Each case uses a fresh root and separate native JVMs for baseline, every mutating step, dump and recover.
Failures and refusals are retained. Process-exit cuts only: no power-loss, live-world, SaveQueue or production claim.
The conservation oracle lives here in Python and reads the native dump; the Java helper never checks the total.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(__file__).with_name('GraveReceiptHelper.java')
HALTED, REFUSED = 75, 2
TOTAL = 10       # independent conservation target, derived from the task oracle
PILE_BASE = 2    # the pile base is immutable in this fixture
SENTINEL = b'unrelated sentinel, must survive refusal and recovery\n'
REFUSE = 'refuse'


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


def invoke(java, cp, case_dir, label, args):
    out, err = case_dir / f'{label}.stdout', case_dir / f'{label}.stderr'
    with out.open('w') as stdout, err.open('w') as stderr:
        code = subprocess.run([str(java), '-cp', cp, 'GraveReceiptHelper', *args],
                              stdout=stdout, stderr=stderr, timeout=120).returncode
    error = err.read_text()
    pid = re.search(r'^PROBE_PID ([0-9]+)$', error, re.MULTILINE)
    if pid is None:
        raise RuntimeError(f'{label} did not identify its native process; evidence retained in {case_dir}')
    return {'label': label, 'exit': code, 'pid': int(pid.group(1)), 'stdout': out.read_text(), 'stderr': error,
            'logs': [rel(out), rel(err)]}


def state(owner, guest, consumed, floor, piles, receipts):
    return {'owner': owner, 'guest': guest, 'consumed': consumed, 'floor': floor, 'piles': piles, 'receipts': receipts}


PRE = state(10, 0, 0, 0, 0, 0)          # alpha 10, no pile, beta 0
COMMITTED = state(8, 0, 0, 2, 1, 0)     # owner death saved, pile base 2, no receipt
CLAIMED = state(8, 2, 0, 0, 1, 1)       # guest inventory+receipt saved, pile fully claimed
CONSUMED = state(8, 0, 2, 0, 1, 1)      # claimed coins consumed into the fixture sink
RETIRED_KEPT = state(8, 2, 0, 0, 0, 1)  # owner pile retired, extra receipt not yet GC'd
FINAL = state(8, 2, 0, 0, 0, 0)         # pile retired and receipt GC'd
BAD_ERASED = state(8, 0, 2, 2, 1, 0)    # control: receipt erased after consumption, base 2 still live


def jvm(mode, halt='none', exit=None, unchanged=False):
    expected = exit if exit is not None else (HALTED if halt != 'none' else 0)
    return {'mode': mode, 'halt': halt, 'exit': expected, 'unchanged': unchanged}


def py(action):
    return {'python': action}


def case(name, steps, expect, dump_exit=0, extra=None, statuses=None, control=None, raw_total=None, fallback=False):
    return {'name': name, 'steps': steps, 'expect': expect, 'dump_exit': dump_exit, 'extra': extra or {},
            'statuses': statuses, 'control': control, 'raw_total': raw_total, 'fallback': fallback}


DEATH, PICKUP = jvm('death'), jvm('pickup')
CASES = [
    case('1a-death-before-save', [jvm('death', 'death-before-save')], PRE),
    case('1b-death-after-save', [jvm('death', 'death-after-save')], COMMITTED),
    case('2a-pickup-before-save', [DEATH, jvm('pickup', 'pickup-before-save')], COMMITTED),
    case('2b-pickup-after-save', [DEATH, jvm('pickup', 'pickup-after-save')], CLAIMED),
    case('2c-barrier-refuses-pickup-before-death', [jvm('pickup', exit=REFUSED, unchanged=True)], PRE),
    case('2d-repeated-pickup-refuses-without-mutation', [DEATH, PICKUP, jvm('pickup', exit=REFUSED, unchanged=True)], CLAIMED),
    case('3-owner-resave-keeps-base-applies-once', [DEATH, PICKUP, jvm('resave')], CLAIMED,
         extra={('alpha', 'save_generation'): 3}),
    case('4a-claimed-coins-banked', [DEATH, PICKUP, jvm('bank')], CLAIMED,
         extra={('beta', 'inventory'): 0, ('beta', 'bank'): 2}),
    case('4b-claimed-coins-consumed-sink', [DEATH, PICKUP, jvm('consume')], CONSUMED,
         extra={('beta', 'inventory'): 0, ('beta', 'consumed_coins'): 2}),
    case('5a-halt-after-owner-retirement', [DEATH, PICKUP, jvm('gc', 'retire-after-save')], RETIRED_KEPT,
         statuses=['retired']),
    case('5b-halt-after-receipt-gc', [DEATH, PICKUP, jvm('gc', 'gc-after-save')], FINAL),
    case('5c-gc-no-fault-control', [DEATH, PICKUP, jvm('gc')], FINAL),
    case('5d-repeat-gc-is-idempotent', [DEATH, PICKUP, jvm('gc'), jvm('gc', unchanged=True)], FINAL),
    case('5e-halt-before-receipt-gc', [DEATH, PICKUP, jvm('gc', 'gc-before-save')], RETIRED_KEPT, statuses=['retired']),
    case('6-stale-backup-owner-refused', [DEATH, PICKUP, py('restore-pre-death-owner'),
                                          jvm('gc', exit=REFUSED, unchanged=True)],
         REFUSE, raw_total=12),
    case('7-fallback-file-not-promoted', [DEATH, jvm('fallback-pickup')], COMMITTED, fallback=True),
    case('8a-control-bypass-source-barrier', [jvm('bypass-pickup')], REFUSE, control=12),
    case('8b-control-erased-receipt-after-consume', [DEATH, PICKUP, jvm('consume'), jvm('erase-receipt')],
         BAD_ERASED, control=12),
    case('9a-symlinked-guest-refused', [DEATH, PICKUP, py('symlink-guest')], REFUSE, dump_exit=REFUSED),
    case('9b-traversal-receipt-owner-refused', [DEATH, PICKUP, py('traversal-owner-id')], REFUSE, dump_exit=REFUSED),
]
EXPECTED_CASES = 20


def python_action(action, root, case_dir):
    saves = root / 'saves'
    if action == 'restore-pre-death-owner':
        shutil.copyfile(case_dir / 'alpha-pre-death-backup.toml', saves / 'alpha.toml')
    elif action == 'symlink-guest':
        (saves / 'beta.toml').unlink()
        os.symlink('../sentinel.txt', saves / 'beta.toml')
    elif action == 'traversal-owner-id':
        text = (saves / 'beta.toml').read_text()
        if text.count('owner = "alpha"') != 1:
            raise RuntimeError('receipt owner field is not present exactly once in the native file')
        (saves / 'beta.toml').write_text(text.replace('owner = "alpha"', 'owner = "../alpha"'))
    else:
        raise RuntimeError(f'unknown python action {action}')
    return {'python_action': action}


def oracle(dump):
    """Independent conservation tuple computed from the native dump, not from Java's protocol output."""
    owner, guest = dump['alpha'], dump['beta']
    floor = 0
    for pile in owner['piles']:
        if pile['base'] != PILE_BASE:
            raise AssertionError(f'pile base changed to {pile["base"]}')
        claimed = sum(r['quantity'] for r in guest['receipts']
                      if r['pile_id'] == pile['id'] and r['source_seq'] == pile['source_seq'])
        floor += pile['base'] - claimed
    consumed = owner['consumed_coins'] + guest['consumed_coins']
    owner_coins = owner['inventory'] + owner['bank']
    guest_coins = guest['inventory'] + guest['bank']
    if floor < 0:
        raise AssertionError(f'negative floor {floor}')
    return {'tuple': state(owner_coins, guest_coins, consumed, floor, len(owner['piles']), len(guest['receipts'])),
            'total': owner_coins + guest_coins + consumed + floor}


def java_state(rec):
    return state(rec['owner']['inventory'] + rec['owner']['bank'],
                 rec['guest']['inventory'] + rec['guest']['bank'],
                 rec['guest']['consumed_coins'], rec['floor'],
                 len(rec['live_piles']), len(rec['receipts']))


def run_case(run, java, cp, spec):
    case_dir = run / 'cases' / spec['name']
    case_dir.mkdir(parents=True)
    root = case_dir / 'root'
    failures, actions, jvms = [], [], []
    baseline = invoke(java, cp, case_dir, 'baseline', ['baseline', str(root)])
    jvms.append(baseline)
    if baseline['exit'] != 0:
        failures.append(f'baseline exit {baseline["exit"]}')
    (root / 'sentinel.txt').write_bytes(SENTINEL)
    shutil.copyfile(root / 'saves' / 'alpha.toml', case_dir / 'alpha-pre-death-backup.toml')

    for index, item in enumerate(spec['steps'], 1):
        if 'python' in item:
            actions.append(python_action(item['python'], root, case_dir))
            continue
        if item['halt'] != 'none' and index != len(spec['steps']):
            raise RuntimeError('a halting step must be the last step of its case')
        before = snapshot(root) if item['unchanged'] else None
        args = ['gc', str(root), item['halt']] if item['mode'] == 'gc' else ['step', str(root), item['mode'], item['halt']]
        result = invoke(java, cp, case_dir, f'step-{index}-{item["mode"]}', args)
        jvms.append(result)
        if result['exit'] != item['exit']:
            failures.append(f'{item["mode"]} exit {result["exit"]} expected {item["exit"]}: {result["stderr"].strip()[-300:]}')
        if item['halt'] != 'none' and f'HALT {item["halt"]}' not in result['stdout']:
            failures.append(f'halt {item["halt"]} not reached')
        if item['unchanged'] and snapshot(root) != before:
            failures.append(f'refused {item["mode"]} changed account files')

    before_recovery = snapshot(root)
    dump = invoke(java, cp, case_dir, 'dump', ['dump', str(root)])
    recover = invoke(java, cp, case_dir, 'recover', ['recover', str(root)])
    jvms += [dump, recover]
    if snapshot(root) != before_recovery:
        failures.append('dump or recover changed files')
    if len({j['pid'] for j in jvms}) != len(jvms):
        failures.append('native processes were not distinct')
    if dump['exit'] != spec['dump_exit']:
        failures.append(f'dump exit {dump["exit"]} expected {spec["dump_exit"]}')
    if (root / 'sentinel.txt').read_bytes() != SENTINEL:
        failures.append('unrelated sentinel changed')
    if spec['fallback']:
        fallback = root / 'errors' / 'beta.toml'
        if not fallback.is_file() or b'claim-1' not in fallback.read_bytes():
            failures.append('fallback error file does not hold the receipt')

    measured, measured_total, java_result = None, None, None
    if dump['exit'] == 0:
        dumped = json.loads(dump['stdout'])
        if dumped['native_loaded_accounts'] != 2:
            failures.append('dump did not load exactly two native accounts')
        for (account, key), wanted in spec['extra'].items():
            if dumped[account][key] != wanted:
                failures.append(f'{account}.{key}={dumped[account][key]} expected {wanted}')
        seen = oracle(dumped)
        measured, measured_total = seen['tuple'], seen['total']
    if recover['exit'] == 0:
        java_result = json.loads(recover['stdout'])
        if java_result['native_loaded_accounts'] != 2:
            failures.append('recover did not load exactly two native accounts')
        if spec['statuses'] is not None and [r['status'] for r in java_result['receipts']] != spec['statuses']:
            failures.append('receipt statuses differ')

    expect = spec['expect']
    if expect == REFUSE:
        if recover['exit'] != REFUSED or recover['stdout'].strip():
            failures.append(f'recover was not refused (exit {recover["exit"]})')
        if spec['raw_total'] is not None and measured_total != spec['raw_total']:
            failures.append(f'raw total {measured_total} expected {spec["raw_total"]}')
    elif recover['exit'] != 0:
        failures.append(f'recover exit {recover["exit"]}')
    else:
        if measured != expect:
            failures.append(f'native dump tuple {measured} expected {expect}')
        if java_state(java_result) != expect:
            failures.append(f'recover tuple {java_state(java_result)} expected {expect}')

    if spec['control'] is not None:
        # A control passes only when the independent oracle sees the expected bad total and the controlled breach is not 10.
        outcome = 'EXPECTED_BAD_STATE_DETECTED' if measured_total == spec['control'] and measured_total != TOTAL else 'NOT_DETECTED'
        if outcome != 'EXPECTED_BAD_STATE_DETECTED':
            failures.append(f'control total {measured_total} expected bad total {spec["control"]}')
    else:
        outcome = 'PASSED' if not failures else 'FAILED'
        if measured_total is not None and expect != REFUSE and measured_total != TOTAL:
            failures.append(f'conservation total {measured_total} expected {TOTAL}')
            outcome = 'FAILED'
        if failures:
            outcome = 'FAILED'

    return {'case': spec['name'], 'control': spec['control'] is not None, 'outcome': outcome,
            'expected': 'refuse' if expect == REFUSE else expect,
            'native_dump': json.loads(dump['stdout']) if dump['exit'] == 0 else None,
            'recover': java_result, 'recover_refusal': recover['stderr'].strip() if recover['exit'] == REFUSED else None,
            'measured_total': measured_total, 'actions': actions,
            'exit_codes': {j['label']: j['exit'] for j in jvms},
            'pids': {j['label']: j['pid'] for j in jvms},
            'logs': [log for j in jvms for log in j['logs']], 'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-jar', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--java', required=True, type=Path)
    parser.add_argument('--javac', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256):
        parser.error('Expected a lowercase SHA-256 for the frozen server jar.')
    jar = args.server_jar.resolve(strict=True)
    if sha_file(jar) != args.sha256:
        parser.error('Server jar does not match its expected digest.')
    runtime = ROOT / '.runtime'
    lab = runtime / 'native-grave-receipt'
    for ancestor in (runtime, lab):
        if ancestor.is_symlink():
            parser.error(f'Refuse a symlinked lab ancestor: {ancestor}')
    lab.mkdir(parents=True, exist_ok=True)
    run = lab / str(time.time_ns())
    run.mkdir()  # refuses an existing run
    (run / 'cases').mkdir()
    classes = run / 'classes'
    classes.mkdir()
    runner_before = sha_file(Path(__file__))
    helper_before = sha_file(HELPER)
    java = args.java.resolve(strict=True)
    with (run / 'compile.log').open('w') as log:
        subprocess.run([str(args.javac.resolve(strict=True)), '-cp', str(jar), '-d', str(classes), str(HELPER)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    cp = f'{classes}{os.pathsep}{jar}'

    cases = [run_case(run, java, cp, spec) for spec in CASES]
    failures = [f'{c["case"]}: {failure}' for c in cases for failure in c['failures']]
    if len(cases) != EXPECTED_CASES:
        failures.append(f'expected {EXPECTED_CASES} cases, ran {len(cases)}')
    jar_unchanged = sha_file(jar) == args.sha256
    if not jar_unchanged:
        failures.append('server jar changed during the run')
    if sha_file(HELPER) != helper_before or sha_file(Path(__file__)) != runner_before:
        failures.append('helper or runner changed during the run')
    protocol = [c for c in cases if not c['control']]
    controls = [c for c in cases if c['control']]
    summary = {
        'mode': 'native-grave-receipt-whole-pile-restricted-model',
        'scope': 'Fixture-only process-exit cuts over original TOML-sourced PlayerSave files. Not power loss, not live world, '
                 'not SaveQueue, not production storage, not a save-format decision.',
        'run': rel(run),
        'all_passed': not failures,
        'failures': failures,
        'cases_run': len(cases),
        'protocol_cases': len(protocol),
        'protocol_passed': sum(c['outcome'] == 'PASSED' for c in protocol),
        'controls': len(controls),
        'controls_detected': sum(c['outcome'] == 'EXPECTED_BAD_STATE_DETECTED' for c in controls),
        'server_jar_sha256': args.sha256,
        'server_jar_unchanged_after_run': jar_unchanged,
        'helper_source_sha256': {'before': helper_before, 'after': sha_file(HELPER)},
        'runner_sha256': {'before': runner_before, 'after': sha_file(Path(__file__))},
        'cases': cases,
    }
    (run / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'summary': rel(run / 'summary.json'), 'all_passed': summary['all_passed'],
                      'cases_run': len(cases), 'protocol_passed': summary['protocol_passed'],
                      'controls_detected': summary['controls_detected'], 'failures': failures}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
