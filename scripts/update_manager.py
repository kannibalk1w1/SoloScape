"""Launcher-side update flow: check, bounded download into staging, then request a stopped restart.

Runs inside a managed version's backend. It never touches profiles, saves, backups or the cache, never
activates anything itself and never runs candidate code. Activation belongs to the outer bootstrap
(managed_install), which repeats every safety check under the install lease after this launcher exits.
Download work runs on its own thread so Save & Quit and backend shutdown are never queued behind the network.
"""
import os
import sys
import threading
import time
import traceback
from pathlib import Path

import release_updates
import update_package

NOT_MANAGED = ('This is a source or development copy, so it cannot install updates. '
               'Updates install only into a managed package install.')


class UpdateManager:
    def __init__(self, managed, transport=update_package._open, check=None,
                 deadline=update_package.DEADLINE_SECONDS, clock=time.monotonic):
        self.managed = managed
        self.root = Path(os.environ['SOLOSCAPE_MANAGED_ROOT']) if managed else None
        self.transport, self.deadline, self.clock = transport, deadline, clock
        self.check_fn = check or (lambda: release_updates.check())  # late-bound so tests can patch discovery
        self.mutex = threading.Lock()
        self.cancel_event = threading.Event()
        self.worker = None
        self.release = None
        self.state = {'stage': 'idle', 'message': '', 'done': 0, 'total': 0, 'needs_build': None}
        self.reported_result = False
        if managed:
            import managed_install
            self.install = managed_install
        else:
            self.install = None

    # ---- helpers ---------------------------------------------------------------------------------------
    def _set(self, **fields):
        with self.mutex:
            self.state.update(fields)

    def _installed(self):
        if not self.managed:
            return {'release': None, 'id': None}
        return {'release': self.managed['release'], 'id': self.managed['version']}

    def _candidate(self):
        """The staged candidate recorded on disk, if its version folder still exists and differs from the installed one."""
        if not self.managed:
            return None
        record = self.install.read_candidate(self.root)
        if record is None:
            return None
        if record['id'] == self.managed['version'] or not (self.root / 'versions' / record['id']).is_dir():
            return None
        return {'id': record['id'], 'release': record['release'], 'zip_sha256': record['zip_sha256']}

    def _progress(self, stage, done, total):
        self._set(stage=stage, done=done, total=total)

    # ---- actions ---------------------------------------------------------------------------------------------
    def check(self):
        result = self.check_fn()
        result = dict(result, managed=bool(self.managed), installed=self._installed())
        package = result.get('package')
        if result.get('state') == 'release_available':
            with self.mutex:
                self.release = result if package else None
            if not self.managed:
                result['message'] += ' ' + NOT_MANAGED
            elif package and package['tag'] == self.managed['release']:
                result['message'] = 'You already have release ' + package['tag'] + '.'
                result['up_to_date'] = True
        return result

    def download(self):
        if not self.managed:
            raise RuntimeError(NOT_MANAGED)
        with self.mutex:
            if self.worker is not None and self.worker.is_alive():
                return dict(self.state)
            release = self.release
        if release is None or not release.get('package'):
            raise RuntimeError('Check for updates first; the latest release has no installable package.')
        package = release['package']
        if package['tag'] == self.managed['release']:
            raise RuntimeError('You already have release ' + package['tag'] + '.')
        staged = self._candidate()
        if staged and staged['zip_sha256'] == package['sha256']:
            self._set(stage='staged', message='Release ' + staged['release'] + ' is downloaded and verified.', done=0, total=0)
            return dict(self.state)
        self.cancel_event = threading.Event()
        self._set(stage='downloading', message='Downloading release ' + package['tag'] + '…', done=0, total=package['size'], needs_build=None)
        self.worker = threading.Thread(target=self._download, args=(package, self.cancel_event), name='update-download', daemon=True)
        self.worker.start()
        return dict(self.state)

    def _download(self, package, cancelled):
        job = update_package.Job(cancelled=cancelled, deadline=self.deadline, progress=self._progress, clock=self.clock)
        try:
            roots = self.install.load_config(self.root).get('supply_roots', [])
            found = update_package.fetch_and_install(self.root, package, job=job, transport=self.transport, supply_roots=roots)
            self.install.write_candidate(self.root, found['id'], found['release'], found['zip_sha256'])
            self._set(stage='staged', message='Release ' + found['release'] + ' is downloaded and verified. '
                      'Choose Install and Restart when you are ready.', done=0, total=0)
        except update_package.Cancelled as exc:
            self._set(stage='cancelled', message=str(exc), done=0, total=0)
        except update_package.PackageError as exc:
            self._set(stage='error', message=str(exc), done=0, total=0, needs_build=exc.code)
        except Exception as exc:  # never leave the dialog waiting on a dead worker
            traceback.print_exc(file=sys.stderr)
            self._set(stage='error', message='The update could not be prepared: ' + type(exc).__name__, done=0, total=0)

    def cancel(self):
        self.cancel_event.set()
        with self.mutex:
            active = self.worker is not None and self.worker.is_alive()
        if active:
            self._set(message='Cancelling…')
        return self.status()

    def apply(self, world_running):
        if not self.managed:
            raise RuntimeError(NOT_MANAGED)
        if world_running:
            raise RuntimeError('Save & Quit before installing an update.')
        with self.mutex:
            if self.worker is not None and self.worker.is_alive():
                raise RuntimeError('Wait for the download to finish or cancel it first.')
        candidate = self._candidate()
        if candidate is None:
            raise RuntimeError('Download an update first.')
        try:
            reasons = self.install.preflight(self.root, candidate['id'])
        except self.install.InstallError as exc:
            raise RuntimeError(str(exc)) from None
        if reasons:
            raise RuntimeError(' '.join(reasons))
        self.install.request_activation(self.root, candidate['id'])
        return {'restart': True, 'candidate': candidate,
                'message': 'Restarting to install release ' + candidate['release'] + '. Your characters and backups stay in place.'}

    def status(self, world_running=False):
        with self.mutex:
            state = dict(self.state)
            active = self.worker is not None and self.worker.is_alive()
            release = self.release
        candidate = self._candidate()
        result = {'managed': bool(self.managed), 'installed': self._installed(), 'candidate': candidate,
                  'stage': state['stage'], 'message': state['message'] or ('' if self.managed else NOT_MANAGED),
                  'done': state['done'], 'total': state['total'], 'needs_build': state['needs_build'],
                  'release': None if release is None else {'tag': release['tag'], 'title': release['title']},
                  'can_download': bool(self.managed and not active and not world_running and release is not None
                                       and release.get('package') and release['package']['tag'] != self.managed['release']
                                       and not (candidate and candidate['zip_sha256'] == release['package']['sha256'])),
                  'can_cancel': active,
                  'can_apply': bool(self.managed and not active and not world_running and candidate is not None),
                  'last_result': None}
        if self.managed and not self.reported_result:
            self.reported_result = True
            result['last_result'] = self.install.read_result(self.root)
            self.install.clear_result(self.root)
        return result

    def close(self, timeout=20):
        """Backend shutdown: stop any download promptly; the socket read timeout bounds the wait."""
        self.cancel_event.set()
        worker = self.worker
        if worker is not None:
            worker.join(timeout)
