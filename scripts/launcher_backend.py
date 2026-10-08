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

MAX_REQUEST = 16384


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
        if action == 'list':
            return {'profiles': profiles.list_profiles(), 'session': self.current()}
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
        if action == 'backups':
            return profiles.list_backups(request.get('profile'))
        if action == 'restore':
            return profiles.restore_profile(request.get('profile'), request.get('backup', ''))
        if action in ('backup', 'start'):
            profile = profiles.load(request.get('profile'))
            if action == 'backup':
                return {'name': profile.backup().name}
            if self.worker is not None and self.worker.is_alive():
                raise RuntimeError('A world is already running in this launcher. Save & Quit before switching characters.')
            port = self.port(request)
            self.cancelled = threading.Event()
            with self.mutex:
                self.status = {'stage': 'starting', 'message': 'Checking your local installation…', 'profile': profile.manifest['id'], 'error': None}
            self.worker = threading.Thread(target=self.play, args=(profile, port), name='owned-world', daemon=False)
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
    serve()
