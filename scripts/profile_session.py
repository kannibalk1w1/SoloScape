"""Owned profile session lifecycle, usable from a launcher worker or isolated harness.

The profile lock remains held through save hooks and the verified post-stop backup.
Cancellation never kills a save in progress. Existing game processes are not touched.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import local_dev
import profiles


def owned_environment(profile, port):
    # Dotted properties inherited from another launcher must not change ownership.
    environment = {key: value for key, value in os.environ.items() if '.' not in key}
    environment.update(profile.environment(port))
    return environment


def run(profile, cancelled, notify, port=43594, client_enabled=True, checked=True):
    with local_dev.build_lock(shared=True):
        return _run(profile, cancelled, notify, port, client_enabled, checked)


def _run(profile, cancelled, notify, port=43594, client_enabled=True, checked=True):
    """Blocking worker. notify(stage, message), cancelled is a threading.Event."""
    if checked:
        if not local_dev.doctor(port=port, require_display=client_enabled, output=lambda *args, **kw: print(*args, file=sys.stderr, **kw)):
            raise RuntimeError('Setup checks failed. Open Diagnostics for missing files or runtime requirements.')
    server_jar = local_dev.jar(local_dev.SERVER / 'game', 'void-server-*.jar')
    client_jar = local_dev.jar(local_dev.CLIENT / 'client', 'void-client-*.jar')
    local_dev.verify_build_stamp(server_jar, client_jar)
    with profile.lock():
        metadata = profile.metadata()
        if metadata['error']:
            raise ValueError('Character save needs recovery: ' + metadata['error'])
        notify('backup', 'Verifying a backup before starting this world…')
        profile._backup('before-launch')
        log_dir = profile.directory / 'session-logs'
        profiles.private_directory(log_dir)
        for name in ('server', 'client'):
            current = log_dir / (name + '.log')
            if current.is_symlink():
                raise ValueError('Session logs cannot be symbolic links.')
            if current.exists():
                current.replace(log_dir / (name + '.previous.log'))
        client_home = profile.directory / 'client-home'
        profiles.private_directory(client_home)
        environment = owned_environment(profile, port)
        server = client = None
        ready = False
        failed = None
        def shutdown_output(*args, **kw):
            print(*args, file=sys.stderr, **kw)
            if args and 'Still waiting' in str(args[0]):
                notify('saving', f'Still saving; waiting for owned server shutdown. Logs: {log_dir}')

        with (log_dir / 'server.log').open('w') as server_log, (log_dir / 'client.log').open('w') as client_log:
            try:
                notify('starting', 'Loading this character’s local world…')
                if cancelled.is_set():
                    return 0
                server = subprocess.Popen([os.environ.get('SERVER_JAVA', 'java'), '-jar', str(server_jar)],
                                          cwd=local_dev.SERVER, env=environment, stdout=server_log,
                                          stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + local_dev.READY_TIMEOUT
                while not cancelled.is_set():
                    if server.poll() is not None:
                        raise RuntimeError('World exited during startup. See this profile’s server log.')
                    output = (log_dir / 'server.log').read_text(errors='replace')
                    if re.search(r'Void loaded in \d+ms', output):
                        ready = True
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError('World loading timed out. See this profile’s server log.')
                    cancelled.wait(0.1)
                if not ready:
                    return 0
                profile.mark_played()
                if client_enabled and not cancelled.is_set():
                    notify('connecting', 'Opening the game on localhost…')
                    client = subprocess.Popen([os.environ.get('CLIENT_JAVA', 'java'), '-Duser.home=' + str(client_home),
                                               '-Dsoloscape.cache.root=' + str(client_home / 'native-cache'),
                                               '-jar', str(client_jar), '--address', '127.0.0.1', '--port', str(port)],
                                              cwd=local_dev.CLIENT, env=environment, stdout=client_log,
                                              stderr=subprocess.STDOUT, start_new_session=True)
                notify('playing', 'World ready. Save & Quit waits for normal save hooks.')
                while not cancelled.is_set():
                    if server.poll() is not None:
                        raise RuntimeError('World stopped unexpectedly. Inspect its logs and verified backups.')
                    if client is not None and client.poll() is not None:
                        return client.returncode
                    cancelled.wait(0.1)
                return 0
            except BaseException as exc:
                failed = exc
                raise
            finally:
                notify('saving', 'Saving and closing your local world…')
                local_dev.stop(client, output=shutdown_output)
                local_dev.stop(server, output=shutdown_output)
                # An unexpected process failure must not be represented as a clean save.
                if ready and server is not None and server.returncode in (0, 143, -15) and failed is None:
                    notify('backup', 'Verifying the saved-world backup…')
                    profile._backup('after-clean-shutdown')
                    notify('stopped', 'World saved and verified. You can continue later.')
                elif server is None:
                    notify('stopped', 'Startup cancelled. Your world was not started.')
                else:
                    notify('stopped', 'World closed. Previous verified backup retained; check logs after an error.')
