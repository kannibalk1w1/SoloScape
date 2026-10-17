#!/usr/bin/env python3
"""Disposable live-server/client proof for the original definition-only Lab token.

Requires a NEW private deck_export snapshot and a successful backport_lab_token run.
Never targets the owner install. Experimental cache/semantic overlay is private and
explicitly supersedes the snapshot's cache entries; it is not a playable release.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE_SHA = 'a4293ba42198ed092f8db93f2b9c2dc8e755db1d6c16bdd91f4dcf0ad68c43fd'
CANDIDATE_SHA = 'f6ed21f471bfda634e3bc87b6c93026711d0b1ead71def4557482eb4b35f56b3'


def require(value, message):
    if not value:
        raise ValueError(message)


def ordinary(path):
    require(path.is_absolute() and '..' not in path.parts, 'absolute ordinary path required')
    for part in [path, *path.parents]:
        require(not part.is_symlink(), 'linked path refused: '+str(part))
    return path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def native_json(text):
    # Native logging prefixes output with ANSI resets; require one actual JSON record.
    plain = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    records = [json.loads(line) for line in plain.splitlines() if line.startswith('{')]
    require(len(records) == 1, 'native helper must emit exactly one JSON record')
    return records[0]


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    args = parser.parse_args()
    snapshot, candidate = ordinary(args.snapshot), ordinary(args.candidate)
    require(snapshot.is_relative_to(ROOT/'.runtime/deck-exports') and snapshot.is_dir(), 'new private export required')
    require(candidate.is_relative_to(ROOT/'.runtime/backport-lab') and candidate.name == 'cache-copy', 'lab cache-copy required')
    require(not (snapshot/'.runtime/lab-token-overlay.json').exists(), 'snapshot already used by this lab')
    sources = [HERE/'LabTokenHelper.java', HERE/'LabTokenClientProbe.java', Path(__file__)]
    require(all(p.is_file() and not p.is_symlink() for p in sources), 'lab source inputs missing')
    inputs_before = {p.name: sha(p) for p in sources}
    # Import session/build contracts from the copied, matched snapshot, never mutate root modules.
    sys.path.insert(0, str(snapshot/'scripts'))
    import local_dev, profiles, profile_session
    from backport_catalogue import canonical, fingerprint
    baseline = ROOT/'upstream/game-server/data/cache'
    source_before, candidate_before = fingerprint(baseline), fingerprint(candidate)
    require(hashlib.sha256(canonical(source_before)).hexdigest() == BASELINE_SHA, 'baseline cache identity differs')
    require(hashlib.sha256(canonical(candidate_before)).hexdigest() == CANDIDATE_SHA, 'candidate cache identity differs')
    cache = snapshot/'upstream/game-server/data/cache'
    require(fingerprint(cache) == source_before, 'snapshot is not the original baseline cache')
    manifest = json.loads((snapshot/'deck-manifest.json').read_text())
    overlay_name = 'upstream/game-server/data/entity/lab_token.items.toml'
    mapping = snapshot/overlay_name
    require(not mapping.exists(), 'mapping occupied')
    cache_prefix = 'upstream/game-server/data/cache/'
    # Verify every source-listed entry, with exactly the cache overlay excluded after installation.
    def verify_snapshot(overlaid):
        for name, entry in manifest['files'].items():
            if overlaid and name.startswith(cache_prefix):
                continue
            path = snapshot/name
            if 'link' in entry:
                require(path.is_symlink() and os.readlink(path) == entry['link'], 'snapshot link differs: '+name)
            else:
                require(path.is_file() and not path.is_symlink() and sha(path) == entry['sha256'], 'snapshot file differs: '+name)
    verify_snapshot(False)
    output = ROOT/'.runtime/native-lab-token'/str(time.time_ns())
    output.mkdir(parents=True, mode=0o700)
    (output/'.lab-token-fixture').write_text('Original Lab token only; no owner data.\n')
    print('OUTPUT '+str(output), flush=True)
    overlay = {'purpose': 'disposable native Lab token proof; not a release',
               'source_commit': manifest['source_commit'], 'original_manifest_sha256': sha(snapshot/'deck-manifest.json'),
               'baseline': source_before, 'candidate': candidate_before, 'mapping': overlay_name,
               'cache_generation_summary_sha256': sha(candidate.parent.parent/'summary.json')}
    for name in candidate_before:
        shutil.copyfile(candidate/name, cache/name)
    mapping.write_text('[lab_token]\nid = 20179\n')
    overlay['mapping_sha256'] = sha(mapping)
    write_json(snapshot/'.runtime/lab-token-overlay.json', overlay)
    write_json(output/'overlay.json', overlay)
    require(fingerprint(cache) == candidate_before, 'overlay copy differs')
    classes = output/'classes'
    classes.mkdir()
    server = local_dev.jar(local_dev.SERVER/'game', 'void-server-*.jar')
    client = local_dev.jar(local_dev.CLIENT/'client', 'void-client-*.jar')
    j21 = snapshot/'.runtime/jdks/jdk21/bin/java'
    j8 = snapshot/'.runtime/jdks/jdk8/bin/java'
    for source, javac, jar in [('LabTokenHelper.java', j21.with_name('javac'), server),
                               ('LabTokenClientProbe.java', j8.with_name('javac'), client)]:
        subprocess.run([str(javac), '-encoding', 'UTF-8', '-cp', str(jar), '-d', str(classes), str(HERE/source)], check=True, timeout=60)
    os.environ.update(SERVER_JAVA=str(j21), CLIENT_JAVA=str(j8), LIBGL_ALWAYS_SOFTWARE='1')
    home = output/'home'
    home.mkdir()
    os.environ['HOME'] = str(home)
    alsa = output/'empty-alsa.conf'
    alsa.write_text('')
    os.environ['ALSA_CONFIG_PATH'] = str(alsa)
    os.environ.pop('_JAVA_OPTIONS', None)
    os.environ.pop(local_dev.CACHE_HOME_ENV, None)
    profiles.PROFILES = output/'profiles'
    profile = profiles.create('Original Lab token fixture', 'AlphaTest')
    marker = output/'client.json'
    save = profile.state/'saves/alphatest.toml'
    original_popen = subprocess.Popen
    read_fd, write_fd = os.pipe()
    display = original_popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                             pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(write_fd)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(read_fd, selectors.EVENT_READ)
            require(bool(selector.select(10)), 'owned Xvfb handshake timed out')
        number = os.read(read_fd, 128).decode().strip()
        require(number.isdigit() and display.poll() is None, 'owned display unavailable')
        os.environ['DISPLAY'] = ':'+number
        results = []
        def session(label, expected):
            marker.unlink(missing_ok=True)
            def popen(argv, **kwargs):
                if '-jar' in argv and str(client) in argv:
                    i = argv.index('-jar')
                    argv = argv[:i]+['-cp', os.pathsep.join([str(classes), str(client)]), 'LabTokenClientProbe', str(marker), '43595', str(expected)]
                return original_popen(argv, **kwargs)
            started = time.monotonic()
            with patch.object(subprocess, 'Popen', side_effect=popen):
                code = profile_session.run(profile, threading.Event(), lambda stage, message: print(label, stage, flush=True), port=43595)
            require(code == 0 and marker.is_file() and profile.metadata()['saved'], 'native session failed: '+label)
            require(not (profile.directory/'session.json').exists(), 'session ownership did not close')
            row = json.loads(marker.read_text())
            require(row['quantity'] == expected, 'client quantity mismatch')
            row.update(label=label, session_seconds=time.monotonic()-started)
            write_json(output/(label+'.json'), row)
            shutil.copyfile(save, output/(label+'.toml'))
            results.append(row)
            return tomllib.loads(save.read_text())
        initial = session('new', 0)
        def helper(mode, cache_input):
            with profile.lock():
                result = subprocess.run([str(j21), '-cp', os.pathsep.join([str(classes), str(server)]),
                                         'LabTokenHelper', mode, str(cache_input), str(save)], cwd=ROOT, capture_output=True, text=True, timeout=90)
            (output/(mode+('-baseline' if cache_input == baseline else '')+'.log')).write_text(result.stdout+result.stderr)
            return result
        injected = helper('inject', cache)
        require(injected.returncode == 0, 'native helper inject failed; inspect log')
        native_inject = native_json(injected.stdout)
        require(native_inject['id'] == 20179 and native_inject['tokenquantity'] == 2
                and native_inject['nativearraycount'] == 28 and native_inject['itemarraycount'] > 20179
                and all(native_inject['transactioncheckflags'].values()), 'native transaction evidence differs')
        after = tomllib.loads(save.read_text())
        require({k:v for k,v in initial.items() if k != 'inventories'} == {k:v for k,v in after.items() if k != 'inventories'}, 'injection changed non-inventory fields')
        require({k:v for k,v in initial['inventories'].items() if k != 'inventory'} == {k:v for k,v in after['inventories'].items() if k != 'inventory'}, 'other inventories changed during injection')
        def without_token(slots):
            return [v for v in slots if v and v.get('id') != 'lab_token']
        require(without_token(initial['inventories']['inventory']) == without_token(after['inventories']['inventory']), 'starter inventory changed during injection')
        require(len(initial['inventories']['inventory']) == len(after['inventories']['inventory']) == 28, 'inventory capacity changed')
        require(all(not item or item == after['inventories']['inventory'][i] for i, item in enumerate(initial['inventories']['inventory'])), 'starter slots moved during injection')
        before_refusal = save.read_bytes()
        refused = helper('read', baseline)
        require(refused.returncode != 0 and save.read_bytes() == before_refusal, 'baseline cache mismatch did not refuse unchanged')
        first = session('continue-one', 2)
        second = session('continue-two', 2)
        for state in (first, second):
            require(without_token(state['inventories']['inventory']) == without_token(initial['inventories']['inventory']), 'starter save items changed')
            tokens = [v for v in state['inventories']['inventory'] if v.get('id') == 'lab_token']
            require(len(tokens) == 1 and tokens[0]['amount'] == 2, 'token native save mismatch')
        for row in results[1:]:
            require([s for s in row['slots'] if s[0] != 20179] == results[0]['slots'], 'client starter items differ')
        cold = helper('read', cache)
        require(cold.returncode == 0, 'native cold-read failed')
        native_cold = native_json(cold.stdout)
        require(native_cold['quantity'] == 2 and native_cold['nativearraycount'] == 28, 'cold native quantity differs')
        require(fingerprint(baseline) == source_before and fingerprint(candidate) == candidate_before
                and fingerprint(cache) == candidate_before, 'cache input bytes changed')
        verify_snapshot(True)
        require(sha(mapping) == overlay['mapping_sha256'], 'semantic overlay changed')
        backups = profiles.list_backups(profile.manifest['id'])
        require(len(backups) >= 6 and all(b['valid'] for b in backups), 'verified backup generations missing')
        for backup in backups:
            profile.validate_backup(profile.directory/'backups'/backup['name'])
        require(inputs_before == {p.name: sha(p) for p in sources}, 'lab source changed during run')
        summary = {'scope': 'original definition-only token; real native server/client, fixture inventory injection',
                   'appearance_proof': False, 'production_uninstall_proof': False,
                   'source_commit': manifest['source_commit'], 'server_sha256': sha(server), 'client_sha256': sha(client),
                   'helper_sha256': sha(HERE/'LabTokenHelper.java'), 'probe_sha256': sha(HERE/'LabTokenClientProbe.java'),
                   'runner_sha256': sha(Path(__file__)), 'source_inputs_sha256': inputs_before, 'baseline_unchanged': True, 'candidate_unchanged': True,
                   'snapshot_other_listed_files_unchanged': True, 'baseline_missing_definition_refused_unchanged': True,
                   'sessions': results, 'backups_verified': len(backups), 'native_inject': native_inject,
                   'native_cold_read': native_cold}
        write_json(output/'summary.json', summary)
        print(json.dumps({'summary': str(output/'summary.json'), 'sessions': len(results), 'backups_verified': len(backups)}), flush=True)
    finally:
        os.close(read_fd)
        if display.poll() is None:
            display.terminate()
            display.wait(10)


if __name__ == '__main__':
    # Freeze root matched inputs while a lab may read lazily; sessions also lock the copy.
    with (ROOT/'.runtime/build.lock').open('a+') as guard:
        fcntl.flock(guard, fcntl.LOCK_SH)
        run()
