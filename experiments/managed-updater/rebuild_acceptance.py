#!/usr/bin/env python3
"""PRIVATE native acceptance of the launcher-driven Java-changing update and the user-triggered rollback.

Disposable state only; never run against an owner install. Sequence, driven through the real graphical launcher with
mapped controller input on an owned Xvfb display, the real bootstrap, real native server/client and REAL
scripts/prepare-build.sh builds:

  play a world -> Check -> Download is refused (the release changes Java) -> Update Source and Rebuild -> cancel it
  mid-build (owned processes gone, nothing left, source folder untouched) -> rebuild again -> staged -> Install and
  Restart -> Continue -> Roll Back (declined with B, then confirmed) -> Continue

The "project" is a disposable local git repository (fixed-origin validation is unchanged in production; only this
process's fake_github shim points the fixed origin at it). It holds this checkout's tracked sources plus one inert
server patch, so the release changes Java. A disposable maintainer folder builds that commit with the real prepare
flow to produce the code-only package, exactly as a maintainer would. Evidence goes to <run>/acceptance.json.
"""
import argparse
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))
import acceptance as base  # noqa: E402
import managed_install as mi  # noqa: E402
import package_builder  # noqa: E402
import profiles  # noqa: E402
import real_checkout  # noqa: E402
import release_updates  # noqa: E402
import runtime_manifest  # noqa: E402
import source_build  # noqa: E402

fields, logical_account, wait_for, load = base.fields, base.logical_account, base.wait_for, base.load


def tree(path):
    """Byte-exact picture of a directory (symbolic links recorded, never followed)."""
    result = {}
    for folder, dirs, names in os.walk(path):
        for name in dirs + names:
            full = Path(folder) / name
            rel = full.relative_to(path).as_posix()
            if full.is_symlink():
                result[rel] = ('link', os.readlink(full))
            elif full.is_file():
                result[rel] = (oct(full.stat().st_mode & 0o7777), hashlib.sha256(full.read_bytes()).hexdigest())
    return result


def git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    return subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=acceptance', '-c', 'user.email=acceptance@example.invalid', *args],
                          check=True, capture_output=True, text=True, env=env).stdout.strip()


def make_origin(destination):
    """A disposable stand-in for the project repository: this checkout's source files plus the inert server patch."""
    files = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                           capture_output=True, check=True).stdout.split(b'\0')
    for raw in files:
        if not raw:
            continue
        name = raw.decode()
        source = ROOT / name
        if source.is_file() and not source.is_symlink():
            target = Path(destination) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    git(destination, 'init', '-q')
    real_checkout.add_inert_patch_to(destination, ROOT)
    git(destination, 'add', '-A')
    git(destination, 'commit', '-q', '-m', 'acceptance source')
    return git(destination, 'rev-parse', 'HEAD')


def owned_processes(marker):
    """Process ids whose command line mentions `marker` (the install's build folder), excluding this process."""
    found = []
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit() and int(entry.name) != os.getpid():
            try:
                if marker.encode() in (entry / 'cmdline').read_bytes() or str(marker) in os.readlink(entry / 'cwd'):
                    found.append(int(entry.name))
            except OSError:
                pass
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True, help='authorized cache to copy (read only)')
    parser.add_argument('--server-java', type=Path, required=True)
    parser.add_argument('--client-java', type=Path, required=True)
    parser.add_argument('--reuse', type=Path, help='an earlier run whose real player/maintainer builds, origin and packages are copied (saves two builds while iterating on the launcher steps)')
    options = parser.parse_args()
    cache_source = options.cache.resolve(strict=True)
    run = ROOT / '.runtime/managed-acceptance' / str(time.time_ns())
    for name in ('packages', 'profiles', 'launcher', 'probe', 'temp', 'home', 'shim', 'classes'):
        (run / name).mkdir(parents=True, mode=0o700)
    (run / 'alsa.conf').write_text('')
    result = {'passed': False, 'checks': {}, 'scope': 'Private disposable native acceptance with mapped AWT Robot input on owned Xvfb; '
              'real prepare-build.sh builds in disposable folders; a disposable local git repository stands in for the fixed project '
              'repository and fake_github.py for GitHub metadata at the backend seams; no SDL, hardware, audio or owner install.'}
    checks = result['checks']
    support = load(ROOT / 'experiments/native-prebuilt-server/run.py', 'acceptance_support')
    display = bootstrap = None
    try:
        shutil.copytree(cache_source, run / 'cache')
        cache_before = support.tree(run / 'cache')
        # ---- player folder: the first real build, and the installed release a ---------------------------------------------
        a_zip = run / 'packages/soloscape-package-private-test-a.zip'
        if options.reuse:
            previous = options.reuse.resolve(strict=True)
            for name in ('player', 'maintainer', 'origin'):
                shutil.copytree(previous / name, run / name, symlinks=True)
            for name in ('soloscape-package-private-test-a.zip', 'soloscape-package-private-test-j.zip'):
                shutil.copy2(previous / 'packages' / name, run / 'packages' / name)
            player = run / 'player'
            checks['player_built_by_real_prepare'] = True
            result['reused_builds_from'] = previous.name
            a_digest = hashlib.sha256(a_zip.read_bytes()).hexdigest()
        else:
            player = real_checkout.copy_source(ROOT, run / 'player')
            checks['player_built_by_real_prepare'] = real_checkout.prepare(player, run / 'cache', run / 'prepare-player.log') == 0
            if not checks['player_built_by_real_prepare']:
                raise RuntimeError('prepare-build.sh failed in the player folder; see prepare-player.log')
            a_digest = package_builder.checkout_package(player, 'private-test-a', (0, 1), a_zip, source=player)
        stamp_one = json.loads((player / '.runtime/build-stamp.json').read_text())
        root = run / 'install'
        a = mi.install_first(root, a_zip, a_digest, run / 'profiles', run / 'cache', run / 'launcher', release='private-test-a',
                             supply_roots=[player], server_java=str(options.server_java), client_java=str(options.client_java))
        checks['install_a_sealed'] = mi.read_pointer(root) == {'current': a, 'previous': None}
        # ---- the project repository, the maintainer build and the Java-changing release ----------------------------------
        origin = run / 'origin'
        maintainer = run / 'maintainer'
        j_zip = run / 'packages/soloscape-package-private-test-j.zip'
        if options.reuse:
            commit = git(origin, 'rev-parse', 'HEAD')
            checks['maintainer_built_by_real_prepare'] = True
            j_digest = hashlib.sha256(j_zip.read_bytes()).hexdigest()
        else:
            commit = make_origin(origin)
            git(origin, 'clone', '-q', str(origin), str(maintainer))
            for name in real_checkout.UPSTREAM:
                shutil.copytree(player / 'upstream' / name, maintainer / 'upstream' / name, symlinks=True,
                                ignore=shutil.ignore_patterns('build', '.gradle'))
            (maintainer / '.gradle').symlink_to(ROOT / '.gradle')
            (maintainer / 'config').mkdir(exist_ok=True)  # untracked local configuration, as on any developer machine
            (maintainer / 'config/local.env').write_text('SERVER_JAVA=%s\nCLIENT_JAVA=%s\n' % (options.server_java, options.client_java))
            checks['maintainer_built_by_real_prepare'] = real_checkout.prepare(maintainer, run / 'cache', run / 'prepare-maintainer.log') == 0
            if not checks['maintainer_built_by_real_prepare']:
                raise RuntimeError('prepare-build.sh failed in the maintainer folder; see prepare-maintainer.log')
            j_digest = package_builder.checkout_package(maintainer, 'private-test-j', (0, 1), j_zip, source=maintainer)
        result['source_commit'] = commit
        with zipfile.ZipFile(j_zip) as archive:
            declared = json.loads(archive.read(runtime_manifest.MANIFEST_NAME))
        checks['release_declares_the_exact_source_commit'] = declared['source_commit'] == commit
        checks['release_package_is_scripts_only'] = j_zip.stat().st_size < 1 << 20
        result['package_bytes'] = {'a': a_zip.stat().st_size, 'j': j_zip.stat().st_size}
        fake = run / 'fake.json'
        fake.write_text(json.dumps({'mode': 'serve', 'tag': 'private-test-j', 'name': j_zip.name, 'size': j_zip.stat().st_size,
                                    'sha256': j_digest, 'path': str(j_zip), 'rate': 1 << 20}))
        origins = {'SoloScape': str(origin), **{name: str(player / 'upstream' / name) for name in real_checkout.UPSTREAM}}
        player_before = tree(player)
        # ---- wrappers, display, fixture character ---------------------------------------------------------------------------
        sessions = load(ROOT / 'experiments/native-prebuilt-session/run.py', 'acceptance_sessions')
        harness = run / 'harness'
        harness.mkdir()
        client_jar = root / 'versions' / a / 'upstream/runelite-client/client/build/libs/void-client-0.2.0_a2.jar'
        javac = options.client_java.with_name('javac')
        subprocess.run([str(javac), '-encoding', 'UTF-8', '-cp', str(client_jar), '-d', str(harness),
                        str(ROOT / 'scripts/harness/NativeManagedRebuildProbe.java')] +
                       [str(ROOT / 'scripts/harness' / (name + '.java')) for name in sessions.HARNESS], check=True)
        shim = run / 'shim/python3'
        shim.write_text('#!/bin/sh\ncase "$1" in\n  */launcher_backend.py) exec %s -B %s "$@";;\n  *) exec %s "$@";;\nesac\n'
                        % (sys.executable, HERE / 'fake_github.py', sys.executable))
        shim.chmod(0o700)
        wrappers = {}
        for role, java in (('server', options.server_java), ('client', options.client_java)):
            wrapper = run / (role + '-java')
            code = '''import os,sys
from pathlib import Path
java=JAVA
args=['-Djava.io.tmpdir='+TEMP]+sys.argv[1:]
LAUNCHER='net.runelite.client.soloscape.launcher.SoloScapeLauncher'
if ROLE=='client' and '-jar' in args:
 i=args.index('-jar'); jar=args[i+1]
 count_file=Path(COUNTER)
 count=int(count_file.read_text())+1 if count_file.exists() else 1
 count_file.write_text(str(count))
 port=args[args.index('--port')+1]
 args=args[:i]+['-cp',jar+os.pathsep+HARNESS,'NativeSessionSmoke',MARKER+str(count),port]
elif ROLE=='client' and LAUNCHER in args:
 i=args.index(LAUNCHER); cp=args[args.index('-cp')+1]
 args=['-Dsoloscape.launcher.steamKeyboard=true','-cp',cp+os.pathsep+HARNESS,'net.runelite.client.soloscape.launcher.NativeManagedRebuildProbe',args[i+1],PROBE]
os.execv(java,[java]+args)
'''
            for name, value in {'JAVA': str(java), 'TEMP': str(run / 'temp'), 'ROLE': role, 'COUNTER': str(run / 'client-launches'),
                                'HARNESS': str(harness), 'MARKER': str(run / 'native-'), 'PROBE': str(run / 'probe')}.items():
                code = code.replace(name, repr(value))
            wrapper.write_text('#!' + sys.executable + '\n' + code)
            wrapper.chmod(0o700)
            wrappers[role] = wrapper
        env = {'PATH': str(run / 'shim') + ':/usr/bin:/bin', 'HOME': str(run / 'home'), 'TMPDIR': str(run / 'temp'), 'LANG': 'C.UTF-8',
               'PYTHONDONTWRITEBYTECODE': '1', 'ALSA_CONFIG_PATH': str(run / 'alsa.conf'), 'SERVER_JAVA': str(wrappers['server']),
               'CLIENT_JAVA': str(wrappers['client']), 'SOLOSCAPE_FAKE_GITHUB': str(fake), 'SOLOSCAPE_FAKE_ORIGINS': json.dumps(origins)}
        read_fd, write_fd = os.pipe()
        display = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'], env=env,
                                   pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.close(write_fd)
        with selectors.DefaultSelector() as selector:
            selector.register(read_fd, selectors.EVENT_READ)
            if not selector.select(10):
                raise RuntimeError('Private Xvfb handshake timed out.')
            env['DISPLAY'] = ':' + os.read(read_fd, 64).decode().strip()
        os.close(read_fd)
        import socket
        with socket.socket() as probe_port:
            probe_port.bind(('127.0.0.1', 0))
            port = probe_port.getsockname()[1]
        backend_env = mi.child_environment(root, mi.load_config(root), env)
        requests = [dict(id=1, action='settings', save=True, port=port), dict(id=2, action='create', label='Managed updater fixture', account='BundleProbe')]
        setup = subprocess.run([sys.executable, '-B', str(root / 'versions' / a / 'scripts/launcher_backend.py')],
                               input=''.join(json.dumps(r) + '\n' for r in requests), env=backend_env, cwd=root / 'versions' / a,
                               text=True, capture_output=True, timeout=120)
        replies = [json.loads(line) for line in setup.stdout.splitlines()]
        if setup.returncode or len(replies) != 2 or not all(r.get('ok') for r in replies):
            raise RuntimeError('Fixture setup failed: ' + setup.stdout[:600] + setup.stderr[-600:])
        profile_dir = run / 'profiles' / replies[1]['result']['id']
        login_before = (profile_dir / 'login.json').read_bytes()
        password = json.loads(login_before)['password']
        # ---- the launcher-driven sequence ---------------------------------------------------------------------------------------
        probe = run / 'probe'
        log = (run / 'bootstrap.log').open('w')
        bootstrap = subprocess.Popen([sys.executable, '-B', str(root / 'bootstrap/managed_install.py'), 'run', str(root)], env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        wait_for(probe / 'round0.json', 400, bootstrap, 'round 0')
        before_update = fields(logical_account(profile_dir))
        checks['round0_account_storage_version'] = before_update['storage_version']
        (probe / 'round0.ack').write_text('verified\n')
        wait_for(probe / 'building.flag', 900, bootstrap, 'the build stage of the first rebuild')
        builds = root / 'builds'
        checks['rebuild_runs_in_an_isolated_workspace_inside_the_install'] = any(n.startswith('.work-') for n in os.listdir(builds))
        checks['rebuild_started_owned_build_processes'] = bool(owned_processes(str(builds)))
        wait_for(probe / 'cancelled.flag', 300, bootstrap, 'the cancelled rebuild')
        time.sleep(2)
        checks['cancel_ended_every_owned_build_process'] = not owned_processes(str(builds))
        checks['cancel_left_no_workspace_or_version'] = (not any(n.startswith('.work-') for n in os.listdir(builds))
                                                          and os.listdir(root / 'versions') == [a] and not source_build.built_workspaces(root))
        checks['cancel_kept_the_private_dependency_cache'] = (builds / source_build.GRADLE_HOME).is_dir()
        checks['launcher_still_running_after_cancel'] = bootstrap.poll() is None
        wait_for(root / mi.CANDIDATE, 3000, bootstrap, 'the staged rebuilt release')
        candidate = mi.read_candidate(root)
        checks['rebuilt_release_staged_and_verified'] = candidate is not None and candidate['release'] == 'private-test-j'
        workspaces = source_build.built_workspaces(root)
        checks['workspace_is_the_declared_commit'] = len(workspaces) == 1 and git(workspaces[0], 'rev-parse', 'HEAD') == commit
        workspace_stamp = json.loads((workspaces[0] / '.runtime/build-stamp.json').read_text())
        checks['workspace_build_record_matches_the_release'] = (workspace_stamp['pins'] == declared['pins']
                                                                 and workspace_stamp['patches'] == declared['patches'])
        checks['staged_version_carries_the_new_jars'] = (
            hashlib.sha256((root / 'versions' / candidate['id'] / package_builder.SERVER_ROLE).read_bytes()).hexdigest() == workspace_stamp['jars']['server']
            and hashlib.sha256((root / 'versions' / candidate['id'] / package_builder.CLIENT_ROLE).read_bytes()).hexdigest() == workspace_stamp['jars']['client']
            and workspace_stamp['jars']['server'] != stamp_one['jars']['server'])
        checks['player_folder_byte_identical_after_rebuild_and_cancel'] = tree(player) == player_before
        try:
            mi.activate(root, candidate['id'])
            checks['activation_refused_while_launcher_runs'] = False
        except mi.Busy:
            checks['activation_refused_while_launcher_runs'] = True
        wait_for(probe / 'round1.json', 600, bootstrap, 'round 1 (Continue after the Java-changing update)')
        checks['pointer_after_update'] = mi.read_pointer(root) == {'current': candidate['id'], 'previous': a}
        after_update = fields(logical_account(profile_dir))
        checks['continue_after_update_fields_equal'] = after_update == before_update
        checks['native_session_after_update_verified'] = 'serverCapabilities=verified' in (run / 'native-2').read_text()
        saves_after_update = tree(profile_dir / 'states')
        (probe / 'round1.ack').write_text('verified\n')
        wait_for(probe / 'launch3.started', 600, bootstrap, 'launch 3')
        checks['pointer_after_rollback'] = mi.read_pointer(root) == {'current': a, 'previous': candidate['id']}
        checks['rollback_kept_current_progress_byte_identical'] = tree(profile_dir / 'states') == saves_after_update
        wait_for(probe / 'round2.json', 600, bootstrap, 'round 2 (Continue after the rollback)')
        checks['continue_after_rollback_fields_equal'] = fields(logical_account(profile_dir)) == before_update
        checks['native_session_after_rollback_verified'] = 'serverCapabilities=verified' in (run / 'native-3').read_text()
        (probe / 'round2.ack').write_text('verified\n')
        checks['bootstrap_exit_clean'] = bootstrap.wait(timeout=300) == 0 and (probe / 'passed3').exists()
        checks['results_shown_once_then_cleared'] = mi.read_result(root) is None
        # ---- state preservation ----------------------------------------------------------------------------------------------
        checks['login_json_byte_identical_throughout'] = (profile_dir / 'login.json').read_bytes() == login_before
        leaked = []
        for folder in (root, run / 'launcher', probe):
            for where, _, names in os.walk(folder):
                for name in names:
                    if password.encode() in (Path(where) / name).read_bytes():
                        leaked.append(str(Path(where) / name))
        if password.encode() in (run / 'bootstrap.log').read_bytes():
            leaked.append('bootstrap.log')
        checks['password_never_in_install_launcher_probe_build_log_or_bootstrap_log'] = not leaked
        checks['launcher_ran_without_optional_artwork'] = mi.status(root)['launcher_art'] == {'brazier.jpg': False, 'brazier-flames.png': False}
        with base.profiles_home(run / 'profiles'):
            backups = profiles.list_backups(profile_dir.name)
        checks['backups_all_valid'] = bool(backups) and all(row['valid'] for row in backups)
        result['backup_count'] = len(backups)
        checks['cache_unchanged'] = support.tree(run / 'cache') == cache_before
        checks['both_versions_verify_and_are_the_only_ones_kept'] = (sorted(os.listdir(root / 'versions')) == sorted([a, candidate['id']])
                                                                       and all(mi.verify_version(root, v) for v in (a, candidate['id'])))
        checks['one_version_context_per_launched_version'] = len(list((run / 'launcher/version-contexts').iterdir())) == 2
        checks['no_staging_leftovers'] = [n for n in os.listdir(root / 'staging') if n != '.lock'] == []
        checks['no_work_folders_left'] = not any(n.startswith('.work-') for n in os.listdir(builds))
        result['jar_hashes'] = {'player_first_build': {k: v[:16] for k, v in stamp_one['jars'].items()},
                                'maintainer': {k: v[:16] for k, v in json.loads((maintainer / '.runtime/build-stamp.json').read_text())['jars'].items()},
                                'launcher_rebuild': {k: v[:16] for k, v in workspace_stamp['jars'].items()}}
        result['probe_log'] = (probe / 'probe.log').read_text().splitlines()
        result['failed_checks'] = [k for k, v in checks.items() if v is False]
        result['passed'] = not result['failed_checks']
    except BaseException as exc:
        result['failure'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        if bootstrap is not None and bootstrap.poll() is None:
            os.killpg(bootstrap.pid, signal.SIGTERM)
            try:
                bootstrap.wait(timeout=180)
            except subprocess.TimeoutExpired:
                result['shutdown_unverified'] = True
        if display is not None and not result.get('shutdown_unverified'):
            display.terminate()
            try:
                display.wait(timeout=5)
            except subprocess.TimeoutExpired:
                display.kill()
                display.wait(timeout=5)
        (run / 'acceptance.json').write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + '\n')
        print('Evidence:', (run / 'acceptance.json').relative_to(ROOT), 'passed=' + str(result['passed']), flush=True)


if __name__ == '__main__':
    main()
