#!/usr/bin/env python3
"""Observe a grave boundary in two native test JVMs; never alter an owner world."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import local_dev


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    java_home = Path(os.environ.get('JAVA_HOME', str(ROOT / '.runtime/jdks/jdk21'))).resolve()
    if not (java_home / 'bin/java').is_file():
        raise ValueError('Supply the native JDK21 JAVA_HOME.')
    output = ROOT / '.runtime/grave-boundary' / str(time.time_ns())
    output.mkdir(parents=True, mode=0o700)
    source = Path(__file__).with_name('TransientWorldSaveProbe.kt')
    destination = local_dev.SERVER / 'game/src/test/kotlin/content/soloscape/TransientWorldSaveProbe.kt'
    source_hash = digest(source)
    suite = 'content.soloscape.TransientWorldSaveProbe'
    report = local_dev.SERVER / 'game/build/test-results/test' / ('TEST-' + suite + '.xml')
    phases = []
    storage_inputs = []
    cache_files = sorted((local_dev.SERVER / 'data/cache').glob('main_file_cache.*'))
    if not cache_files:
        raise RuntimeError('Supply the authorized native cache before this probe.')
    cache_before = {p.name: digest(p) for p in cache_files}
    with local_dev.build_lock():
        subprocess.run([sys.executable, str(ROOT / 'scripts/verify_patches.py'), 'server'], check=True)
        if destination.exists() or destination.is_symlink():
            raise RuntimeError('Refusing to overwrite an existing native test source.')
        staged = output / 'injected-source.kt'
        staged.write_bytes(source.read_bytes())
        if digest(staged) != source_hash:
            raise RuntimeError('Probe source changed before injection.')
        os.link(staged, destination)  # Atomic no-overwrite publication of a complete source file.
        try:
            for phase in ('before', 'after'):
                isolated = output / 'world'
                isolated.mkdir(exist_ok=phase == 'after')
                if phase == 'after':
                    (isolated / 'saves').mkdir()
                    shutil.copyfile(output / 'saved/grave_probe.toml', isolated / 'saves/grave_probe.toml')
                inherited = {}
                for directory in (isolated, output / 'exchange'):
                    for path in sorted(directory.rglob('*')):
                        if path.is_symlink():
                            raise RuntimeError('Unexpected link in disposable storage.')
                        if path.is_file():
                            inherited[str(path.relative_to(output))] = digest(path)
                storage_inputs.append({'phase': phase, 'root': str(isolated.relative_to(output)), 'files_sha256': inherited})
                env = dict(os.environ, JAVA_HOME=str(java_home), GRADLE_USER_HOME=str(ROOT / '.gradle'),
                           SOLOSCAPE_TEST_ROOT=str(isolated), SOLOSCAPE_GRAVE_OUTPUT=str(output),
                           SOLOSCAPE_GRAVE_PHASE=phase)
                report.unlink(missing_ok=True)
                command = ['bash', 'gradlew', '--offline', '--no-daemon', ':game:test', '--tests', suite,
                           '-Dorg.gradle.java.installations.paths=' + str(java_home)]
                with (output / (phase + '.log')).open('x') as log:
                    result = subprocess.run(command, cwd=local_dev.SERVER, env=env, stdout=log, stderr=subprocess.STDOUT)
                if report.is_file():
                    shutil.copyfile(report, output / (phase + '.xml'))
                if result.returncode:
                    raise RuntimeError('Native phase failed; inspect ' + str(output))
                xml = ET.parse(output / (phase + '.xml')).getroot()
                if any(int(xml.attrib[k]) for k in ('errors', 'failures', 'skipped')) or int(xml.attrib['tests']) != 1:
                    raise RuntimeError('Expected exactly one fresh, passing native diagnostic.')
                phases.append(json.loads((output / (phase + '.json')).read_text()))
        finally:
            if digest(destination) != source_hash:
                raise RuntimeError('Injected source changed; preserved for inspection: ' + str(destination))
            destination.unlink()
    if {p.name: digest(p) for p in cache_files} != cache_before:
        raise RuntimeError('Native cache inputs changed; summary withheld.')
    before, after = phases
    if before['pid'] == after['pid'] or before['clock_seconds'] != after['clock_seconds']:
        raise RuntimeError('Cold JVM/unchanged-clock evidence is invalid.')
    if before['grave_expires_seconds'] <= after['clock_seconds']:
        raise RuntimeError('Grave was already expired; cannot attribute loss to persistence.')
    observed_gap = (before['death_floor_count'] == before['grave_npc_count'] == 1
                    and before['live_grave_variables'] and after['death_floor_count'] == after['grave_npc_count'] == 0
                    and not after['live_grave_variables']
                    and before['grave_map_markers'] == 1 and after['grave_map_markers'] == 0)
    summary = dict(mode='native-world-test-cold-jvm-diagnostic', phases=phases, observed_gap=observed_gap,
                   harness_sha256=source_hash, runner_sha256=digest(Path(__file__)),
                   source_pin=local_dev.PINNED['game-server'],
                   server_patches_sha256={p.name: digest(p) for p in sorted((ROOT / 'patches/server').glob('*.patch'))},
                   same_private_storage_root=storage_inputs[0]['root'] == storage_inputs[1]['root'],
                   inherited_private_storage=storage_inputs,
                   cache_files_sha256=cache_before, cache_inputs_unchanged=True,
                   saved_account_sha256=digest(output / 'saved/grave_probe.toml'),
                   limits=['Native WorldTest boot, damage API, real World.shutdown/AutoSave/FileStorage writes; cold PlayerSave.load plus AccountManager spawn, not a network login.',
                           'Supplied items and API death; no network Main, client, physical controller or owner world.',
                           'Reported loss is an open lifecycle gap, never a persistence acceptance.'])
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(output / 'summary.json')


if __name__ == '__main__':
    main()
