"""Binds a version payload started by the managed installer to its immutable code root and external state.

Production adaptation of experiments/prebuilt-runtime-contract/prebuilt_bootstrap.py. It only acts when the
bootstrap exported SOLOSCAPE_MANAGED_ROOT; a source checkout never imports it. The version's mutable
build/recovery context is keyed by its code-root identity and manifest hash, so a later version cannot
inherit or recover this version's session records.
"""
import fcntl
import hashlib
import os
import platform
import stat
import sys
from pathlib import Path

import local_dev
import profiles
import runtime_manifest

MANAGED_ROOT_ENV = 'SOLOSCAPE_MANAGED_ROOT'


def install_root():
    value = os.environ.get(MANAGED_ROOT_ENV)
    return Path(value) if value else None


def open_guard():
    """A fresh shared flock description on install.guard, for children that may outlive the launcher.

    Inherited by owned game JVMs so an orphaned world keeps blocking activation after its launcher dies.
    Returns an open file or None when not managed; raises when the guard cannot be taken.
    """
    root = install_root()
    if root is None:
        return None
    fd = os.open(root / 'install.guard', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise RuntimeError('The install guard is not an ordinary file.')
    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    return os.fdopen(fd, 'rb')


def configure():
    """Validate this payload and bind lifecycle code to its own version context. No-op when unmanaged."""
    managed = install_root()
    if managed is None:
        return None
    root = local_dev.ROOT.resolve()
    manifest, version = runtime_manifest.validate_with_id(root)
    if manifest['pins'] != local_dev.PINNED:
        raise ValueError('Package pins do not match its runtime code.')
    selected = {}
    for name, helper in ((profiles.PROFILE_HOME_ENV, profiles.configured_profile_home),
                         (local_dev.CACHE_HOME_ENV, local_dev.cache_directory),
                         (local_dev.LAUNCHER_HOME_ENV, local_dev.launcher_directory)):
        if name not in os.environ:
            raise ValueError('The managed runtime requires explicit ' + name + '.')
        value = helper().resolve()
        if value == root or value.is_relative_to(root) or root.is_relative_to(value):
            raise ValueError('Shared state/cache must be outside the immutable package.')
        selected[name] = value
    values = list(selected.values())
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
           for index, a in enumerate(values) for b in values[index + 1:]):
        raise ValueError('Choose distinct, non-nested profile, cache and launcher directories.')
    key = hashlib.sha256((str(root) + '\0' + version).encode()).hexdigest()
    contexts = selected[local_dev.LAUNCHER_HOME_ENV] / 'version-contexts'
    profiles.private_directory(contexts)
    runtime = contexts / key
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise ValueError('The version runtime context must be an ordinary directory.')
    local_dev.RUNTIME = runtime
    profiles.PROFILES = selected[profiles.PROFILE_HOME_ENV]

    def verify(server_jar, client_jar):
        current, found = runtime_manifest.validate_with_id(root)
        if current != manifest or found != version:
            raise RuntimeError('The package manifest changed after startup.')
        for role, path in (('server', server_jar), ('client', client_jar)):
            if Path(path) != root / manifest['roles'][role]:
                raise RuntimeError('Runtime jar selection differs from its package manifest.')
        return current

    def doctor(port=local_dev.PORT, require_display=True, output=print, check_port=True):
        errors = []
        try:
            verify(root / manifest['roles']['server'], root / manifest['roles']['client'])
        except (ValueError, RuntimeError, OSError) as exc:
            errors.append(str(exc))
        if sys.platform != 'linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
            errors.append('This runtime requires Linux x86_64.')
        for variable, required in (('SERVER_JAVA', 21), ('CLIENT_JAVA', 8)):
            try:
                found = local_dev.java_version(os.environ.get(variable, 'java'))
                if not (found >= 21 if required == 21 else found == 8):
                    errors.append(variable + ' has an unsupported Java version.')
            except (OSError, ValueError) as exc:
                errors.append(variable + ': ' + str(exc))
        cache = selected[local_dev.CACHE_HOME_ENV]
        for name in ('main_file_cache.dat2', 'main_file_cache.idx255'):
            path = cache / name
            if not path.is_file() or path.stat().st_size == 0:
                errors.append('Supply the authorized compatible cache: missing/empty ' + str(path))
        if require_display and not os.environ.get('DISPLAY'):
            errors.append('Java8 needs an X11/XWayland DISPLAY.')
        if check_port:
            try:
                local_dev.probe_port(port)
            except OSError as exc:
                errors.append('Game port is unavailable: ' + str(exc))
        for error in errors:
            output('ERROR:', error)
        output('Managed preflight:', len(errors), 'error(s); cache revision is declared, not detected.')
        return not errors

    def no_build(*args, **kwargs):
        raise RuntimeError('This is an installed package; rebuild in the source checkout.')

    local_dev.verify_build_stamp = verify
    local_dev.doctor = doctor
    local_dev.prepare = no_build
    local_dev.build = no_build
    return {'version': version, 'release': manifest['release'], 'storage_versions': manifest['storage_versions'],
            'code_root': str(root), 'runtime_context': str(runtime)}
