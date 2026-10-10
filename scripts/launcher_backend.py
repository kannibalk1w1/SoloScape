"""Local graphical launcher's stdio JSON API. No listening web service or shell commands.

One request per line, one response per line with matching id. The owned worker keeps
running until Save & Quit, game exit, or stdin closes; then waits for normal save hooks.
"""
import io
import json
import sys
import threading
import traceback
import local_dev
import profile_session
import profiles
import session_recovery
import signal

MAX_REQUEST = 16384
SETTINGS = local_dev.ROOT / ".runtime/launcher-settings.json"


class Backend:
    def __init__(self):
        self.worker = None
        self.cancelled = threading.Event()
        self.mutex = threading.Lock()
        self.status = {'stage': 'idle', 'message': 'Choose a character or create a new one.', 'profile': None, 'error': None}

    def notify(self, stage, message):
        with self.mutex:
            self.status.update(stage=stage, message=message)

    def current(self):
        with self.mutex:
            result = dict(self.status)
        result['running'] = self.worker is not None and self.worker.is_alive()
        return result

    def dispatch(self, request):
        action = request.get('action')
        if action == 'settings':
            if request.get('save', False):
                port = self.port(request)
                profiles.private_directory(SETTINGS.parent)
                profiles.atomic_json(SETTINGS, {'format': 1, 'port': port})
                return {'port': port}
            if SETTINGS.is_symlink():
                raise ValueError('Launcher settings cannot be a symbolic link.')
            if not SETTINGS.exists():
                return {'port': 43594}
            if SETTINGS.stat().st_size > MAX_REQUEST:
                raise ValueError('Launcher settings are damaged; preserve the file and reset its port.')
            settings = json.loads(SETTINGS.read_text())
            if not isinstance(settings, dict) or settings.get('format') != 1:
                raise ValueError('Launcher settings format is unsupported.')
            return {'port': self.port(settings)}
        if action == 'list':
            rows = profiles.list_profiles()
            current = self.current()
            for row in rows:
                try:
                    row['recovery'] = None if current['running'] and row['id'] == current['profile'] else session_recovery.inspect(
                        profiles.load(row['id']), owner_active=lambda: current['running'] and current['profile'] == row['id'])
                except (ValueError, OSError, KeyError):
                    row['recovery'] = None
            return {'profiles': rows, 'session': current}
        if action == 'status':
            return self.current()
        if action == 'create':
            return profiles.create(request.get('label'), request.get('account'), tutorial=bool(request.get('tutorial', False))).metadata()
        if action == 'diagnostics':
            out = io.StringIO()
            ok = local_dev.doctor(port=self.port(request), output=lambda *args, **kw: print(*args, file=out, **kw))
            return {'ok': ok, 'text': out.getvalue()}
        if action == 'stop':
            self.cancelled.set()
            return self.current()
        if action == 'retention_preview':
            return profiles.preview_retention(request.get('profile'), request.get('keep', 10))
        if action == 'retention_apply':
            return profiles.apply_retention(request.get('profile'), request.get('keep', 10), request.get('token'))
        if action == 'backups':
            return profiles.list_backups(request.get('profile'))
        if action == 'restore':
            return profiles.restore_profile(request.get('profile'), request.get('backup', ''))
        if action == 'archive_session':
            if self.current()['running']:
                raise RuntimeError('Save & Quit before archiving an earlier session record.')
            return session_recovery.archive_ended(profiles.load(request.get('profile')), owner_active=lambda: False)
        if action in ('backup', 'start', 'recover'):
            profile = profiles.load(request.get('profile'))
            if action == 'backup':
                return {'name': profile.backup().name}
            if self.worker is not None and self.worker.is_alive():
                raise RuntimeError('A world is already running in this launcher. Save & Quit before switching characters.')
            port = self.port(request)
            self.cancelled = threading.Event()
            with self.mutex:
                self.status = {'stage': 'starting', 'message': 'Checking your local installation…', 'profile': profile.manifest['id'], 'error': None}
            self.worker = threading.Thread(target=self.recover if action == 'recover' else self.play,
                                           args=(profile, port), name='owned-world', daemon=False)
            self.worker.start()
            return self.current()
        raise ValueError('Unknown launcher action.')

    @staticmethod
    def port(request):
        port = request.get('port', 43594)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('Choose a local game port between 1 and 65535.')
        return port

    def play(self, profile, port):
        try:
            code = profile_session.run(profile, self.cancelled, self.notify, port=port)
            if code:
                self.notify('error', 'Game exited with an error. Check this profile’s client log.')
        except Exception as exc:
            with self.mutex:
                self.status.update(stage='error', message=str(exc), error=str(exc))
            traceback.print_exc(file=sys.stderr)

    def recover(self, profile, port):
        try:
            # A stale record can belong to this backend's earlier, finished worker.
            session_recovery.recover(profile, self.cancelled, self.notify, owner_active=lambda: False)
        except Exception as exc:
            with self.mutex:
                self.status.update(stage='error', message=str(exc), error=str(exc))

    def close(self):
        self.cancelled.set()
        if self.worker is not None:
            self.worker.join()  # no forced kill while save hooks are running


def serve(source=sys.stdin, destination=sys.stdout):
    backend = Backend()
    try:
        while True:
            line = source.readline(MAX_REQUEST + 1)
            if not line:
                break
            response = {'id': None}
            try:
                if len(line) > MAX_REQUEST or not line.endswith('\n'):
                    while line and not line.endswith('\n'):
                        line = source.readline(MAX_REQUEST + 1)
                    raise ValueError('Launcher request is too large or incomplete.')
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError('Launcher request must be an object.')
                response['id'] = request.get('id')
                response.update(ok=True, result=backend.dispatch(request))
            except Exception as exc:
                if not isinstance(exc, (ValueError, RuntimeError, OSError, KeyError, TypeError)):
                    traceback.print_exc(file=sys.stderr)
                response.update(ok=False, error=str(exc))
            destination.write(json.dumps(response) + '\n')
            destination.flush()
    finally:
        backend.close()


if __name__ == '__main__':
    # Raising exits a blocking stdin read through serve's finally and joins save hooks.
    def graceful_exit(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, graceful_exit)
    signal.signal(signal.SIGHUP, graceful_exit)
    serve()
