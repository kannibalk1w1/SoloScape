"""Experimental package adapter; importing it never changes source launch behavior."""
import hashlib
import os
from pathlib import Path
import platform
import signal
import sys

import local_dev
import profiles
from prebuilt_manifest import validate


def configure():
    """Validate a private payload, then bind lifecycle code to its own version context."""
    root = local_dev.ROOT.resolve()
    manifest = validate(root)
    if manifest['pins'] != local_dev.PINNED:
        raise ValueError('Package pins do not match its runtime code.')
    selected = {}
    for name, helper in ((profiles.PROFILE_HOME_ENV, profiles.configured_profile_home),
                         (local_dev.CACHE_HOME_ENV, local_dev.cache_directory),
                         (local_dev.LAUNCHER_HOME_ENV, local_dev.launcher_directory)):
        if name not in os.environ:
            raise ValueError('The experimental prebuilt runtime requires explicit '+name+'.')
        value = helper().resolve()
        if value == root or value.is_relative_to(root) or root.is_relative_to(value):
            raise ValueError('Shared state/cache must be outside the immutable package.')
        selected[name] = value
    values = list(selected.values())
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
           for index, a in enumerate(values) for b in values[index+1:]):
        raise ValueError('Choose distinct, non-nested profile, cache and launcher directories.')
    # Include the code-root identity: another install of identical bytes cannot
    # take over this version's build lock or recover its recorded processes.
    manifest_sha = local_dev.file_hash(root/'soloscape-runtime.json')
    key = hashlib.sha256((str(root)+'\0'+manifest_sha).encode()).hexdigest()
    contexts = selected[local_dev.LAUNCHER_HOME_ENV]/'version-contexts'
    profiles.private_directory(contexts)
    runtime = contexts/key
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise ValueError('The version runtime context must be an ordinary directory.')
    local_dev.RUNTIME = runtime
    profiles.PROFILES = selected[profiles.PROFILE_HOME_ENV]

    def verify(server_jar, client_jar):
        current = validate(root)
        if current != manifest or local_dev.file_hash(root/'soloscape-runtime.json') != manifest_sha:
            raise RuntimeError('The package manifest changed after startup.')
        for role, path in (('server', server_jar), ('client', client_jar)):
            if Path(path) != root/manifest['roles'][role]:
                raise RuntimeError('Runtime jar selection differs from its package manifest.')
        return current

    def doctor(port=local_dev.PORT, require_display=True, output=print, check_port=True):
        errors = []
        try:
            verify(root/manifest['roles']['server'], root/manifest['roles']['client'])
        except (ValueError, RuntimeError, OSError) as exc:
            errors.append(str(exc))
        if sys.platform != 'linux' or platform.machine().lower() not in ('x86_64','amd64'):
            errors.append('This private runtime requires Linux x86_64.')
        for variable, required in (('SERVER_JAVA',21),('CLIENT_JAVA',8)):
            try:
                version = local_dev.java_version(os.environ.get(variable,'java'))
                supported = version >= 21 if required == 21 else version == 8
                if not supported:
                    errors.append(variable+' has an unsupported Java version.')
            except (OSError,ValueError) as exc:
                errors.append(variable+': '+str(exc))
        cache = selected[local_dev.CACHE_HOME_ENV]
        for name in ('main_file_cache.dat2','main_file_cache.idx255'):
            path = cache/name
            if not path.is_file() or path.stat().st_size == 0:
                errors.append('Supply the authorized compatible cache: missing/empty '+str(path))
        if require_display and not os.environ.get('DISPLAY'):
            errors.append('Java8 needs an X11/XWayland DISPLAY.')
        if check_port:
            try:
                local_dev.probe_port(port)
            except OSError as exc:
                errors.append('Game port is unavailable: '+str(exc))
        for error in errors:
            output('ERROR:',error)
        output('Private prebuilt preflight:',len(errors),'error(s); cache revision is declared, not detected.')
        return not errors

    def no_build(*args, **kwargs):
        raise RuntimeError('This is a prebuilt runtime; rebuild in the original source checkout.')

    local_dev.verify_build_stamp = verify
    local_dev.doctor = doctor
    local_dev.prepare = no_build
    local_dev.build = no_build
    return {'format':1,'manifest_sha256':manifest_sha,'code_root':str(root),
            'runtime_context':str(local_dev.RUNTIME),'context_key':key}


def main():
    configure()
    # SETTINGS is fixed at import time, so import after configuring the paths.
    import owned_launcher_backend
    def stop(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGHUP,stop)
    owned_launcher_backend.serve()


if __name__ == '__main__':
    main()
