"""Bounded fetch, safe extraction and sealing of one managed package (a zip of a version payload).

The archive holds `soloscape-runtime.json` plus exactly the files it lists, at their hierarchical payload
paths. Nothing is extracted or run before the archive's SHA-256 matches. The digest comes from the release's
own asset metadata (or the caller for a local install): it proves the bytes are what that source listed. It
does not authenticate the publisher; GitHub HTTPS for the fixed project is the explicit trust source.

Sealing creates `versions/<manifest sha256>/`, read-only, only after the whole tree validates. A failed or
cancelled run removes its scratch directory and leaves every existing version untouched.
"""
import fcntl
import hashlib
import json
import hmac
import http.client
import os
import re
import shutil
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_manifest  # noqa: E402

MAX_PACKAGE = 768 << 20  # archive bound; a payload may still expand to runtime_manifest's own 2 GiB bound
MAX_RATIO_BYTES = runtime_manifest.TOTAL_MAX_BYTES
CHUNK = 1 << 20
SOCKET_TIMEOUT = 10
DEADLINE_SECONDS = 30 * 60  # whole download + verify + extract job, not a per-read inactivity timeout
REDIRECT_HOSTS = frozenset({'objects.githubusercontent.com', 'release-assets.githubusercontent.com'})
STAGING = 'staging'
LOCK = '.lock'
EXECUTABLE = {'scripts/launcher.sh'}
STAMP = '.runtime/build-stamp.json'  # written by local_dev.prepare in a source folder after a successful local build
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
BUILD_SCRIPT = 'scripts/prepare-build.sh'


class PackageError(Exception):
    """A refusal or unavailability. Its message is shown to the player as-is.

    `code` marks the refusals a player can fix by building locally: 'needs-build' (nothing registered or no build
    record) and 'needs-rebuild' (the registered build is of other source or changed after it was made).
    """

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class Cancelled(PackageError):
    """The player cancelled; scratch files were removed."""


class _ProjectRedirects(urllib.request.HTTPRedirectHandler):
    """GitHub moves release downloads to its object store; follow only those fixed hosts over HTTPS."""
    max_redirections = 3

    def redirect_request(self, request, fp, code, message, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme != 'https' or parts.hostname not in REDIRECT_HOSTS:
            return None
        return super().redirect_request(request, fp, code, message, headers, newurl)


def _open(url):
    request = urllib.request.Request(url, headers={
        'Accept': 'application/octet-stream', 'User-Agent': 'SoloScape-launcher-update-fetch'})
    return urllib.request.build_opener(_ProjectRedirects()).open(request, timeout=SOCKET_TIMEOUT)


class Job:
    """Cancellation, whole-job deadline and progress shared by download and extraction."""

    def __init__(self, cancelled=None, deadline=DEADLINE_SECONDS, progress=None, clock=time.monotonic):
        self.cancelled, self.progress, self.clock = cancelled, progress, clock
        self.limit = clock() + deadline

    def check(self):
        if self.cancelled is not None and self.cancelled.is_set():
            raise Cancelled('Update cancelled. Nothing was installed.')
        if self.clock() > self.limit:
            raise PackageError('The update took too long and was stopped. Nothing was installed. Try again on a better connection.')

    def report(self, stage, done, total):
        if self.progress is not None:
            self.progress(stage, done, total)


def _staging(root):
    path = Path(root) / STAGING
    if path.is_symlink() or not path.is_dir():
        raise PackageError('The install staging folder is missing or unsafe.')
    return path


class _StagingLock:
    def __init__(self, root):
        self.path = _staging(root)
        try:
            self.fd = os.open(self.path / LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        except OSError as exc:
            raise PackageError('The staging guard is unreadable.') from exc
        try:
            if not stat.S_ISREG(os.fstat(self.fd).st_mode):
                raise PackageError('The staging guard is not an ordinary file.')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.fd)
            raise PackageError('Another update download is already running.') from None
        except BaseException:
            os.close(self.fd)
            raise
        for entry in os.scandir(self.path):  # we own the lock: anything else is an interrupted earlier run
            if entry.name.startswith(('.part-', '.extract-')):
                _remove(Path(entry.path))

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        os.close(self.fd)


def _remove(path):
    if path.is_dir() and not path.is_symlink():
        for base, dirs, _ in os.walk(path):
            for name in dirs:
                try:
                    os.chmod(Path(base) / name, 0o755)
                except OSError:
                    pass
        os.chmod(path, 0o755)
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def _validate_package(package):
    import release_updates
    fields = {'tag', 'name', 'url', 'size', 'sha256'}
    if not isinstance(package, dict) or set(package) != fields:
        raise PackageError('The update package metadata is incomplete or unsupported.')
    if (not isinstance(package['tag'], str) or not release_updates.TAG.fullmatch(package['tag'])
            or not isinstance(package['name'], str) or not release_updates.PACKAGE_NAME.fullmatch(package['name'])
            or type(package['size']) is not int or not 1 <= package['size'] <= MAX_PACKAGE
            or not isinstance(package['sha256'], str) or not release_updates.DIGEST.fullmatch('sha256:' + package['sha256'])):
        raise PackageError('The update package metadata is invalid.')
    if package['url'] != release_updates.asset_url(package['tag'], package['name']):
        raise PackageError('The update package is not a file of this project’s release.')


def download(url, size, sha256, destination, job, transport=_open):
    """Stream exactly `size` bytes into `destination`, verified against `sha256`. Raises PackageError."""
    digest, total = hashlib.sha256(), 0
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            job.check()
            source = transport(url)
            try:
                while True:
                    job.check()
                    chunk = source.read(min(CHUNK, size + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > size:
                        raise PackageError('The download is larger than the release says. Nothing was installed.')
                    digest.update(chunk)
                    out.write(chunk)
                    job.report('downloading', total, size)
            finally:
                source.close()
    except urllib.error.HTTPError as exc:
        exc.close()
        raise PackageError('The download is unavailable. You can keep using your installed version.') from exc
    except (OSError, http.client.HTTPException) as exc:
        job.check()  # a cancelled read may surface as a closed-socket error
        raise PackageError('The download was interrupted or is unavailable. You can keep using your installed version.') from exc
    job.check()  # a cancel that raced the end of a blocked read is a cancel, not a short download
    if total != size:
        raise PackageError('The download stopped early. Try again later.')
    if not hmac.compare_digest(digest.hexdigest(), sha256):
        raise PackageError('The download does not match the release digest. Nothing was installed.')


def _members(archive):
    infos = archive.infolist()
    if len({info.filename for info in infos}) != len(infos):
        raise PackageError('The package has a duplicate entry name.')
    for info in infos:
        if info.orig_filename != info.filename or '\0' in info.orig_filename:
            raise PackageError('The package has an altered or NUL entry name.')
        if info.flag_bits & 0x1:
            raise PackageError('The package has an encrypted entry.')
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise PackageError('The package uses an unsupported compression method.')
        if info.is_dir() or not stat.S_ISREG(info.external_attr >> 16):
            raise PackageError('The package holds a directory, link or special file entry: ' + info.filename[:80])
    return {info.filename: info for info in infos}


def _copy(archive, info, size, out, job, stage, counter):
    digest, total = hashlib.sha256(), 0
    with archive.open(info) as source:
        while True:
            job.check()
            chunk = source.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > size:
                raise PackageError('A package file streams more bytes than declared: ' + info.filename[:80])
            digest.update(chunk)
            if out is not None:
                out.write(chunk)
            counter[0] += len(chunk)
            job.report(stage, counter[0], counter[1])
    if total != size or info.file_size != size:
        raise PackageError('A package file size disagrees with its declaration: ' + info.filename[:80])
    return digest.hexdigest()


def _read_manifest(archive):
    """The members and strictly parsed manifest of an open package; nothing is extracted."""
    infos = _members(archive)
    name = runtime_manifest.MANIFEST_NAME
    if name not in infos:
        raise PackageError('The package has no ' + name + '.')
    if infos[name].file_size > runtime_manifest.MANIFEST_MAX_BYTES:
        raise PackageError('The package manifest is too large.')
    raw = bytearray()
    with archive.open(infos[name]) as source:
        raw += source.read(runtime_manifest.MANIFEST_MAX_BYTES + 1)
    raw = bytes(raw)
    if len(raw) > runtime_manifest.MANIFEST_MAX_BYTES or len(raw) != infos[name].file_size:
        raise PackageError('The package manifest is too large or inconsistent.')
    try:
        manifest = runtime_manifest.parse(raw)
    except (ValueError, RecursionError) as exc:
        raise PackageError('The package manifest was refused: ' + str(exc)) from None
    return infos, manifest, raw


def read_manifest(zip_path):
    """Parse only the manifest of a package whose digest the caller has already verified."""
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, NotImplementedError, zlib.error, OSError) as exc:
        raise PackageError('The package is not a readable ZIP file.') from exc
    with archive:
        return _read_manifest(archive)[1]


def _extract(zip_path, scratch, job):
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, NotImplementedError, zlib.error, OSError) as exc:
        raise PackageError('The package is not a readable ZIP file.') from exc
    with archive:
        infos, manifest, raw = _read_manifest(archive)
        name = runtime_manifest.MANIFEST_NAME
        listed = manifest['files']
        files = {path: meta for path, meta in listed.items() if 'size' in meta}
        if set(infos) != set(files) | {name}:
            raise PackageError('The package entries must be exactly the manifest plus its released files.')
        for path in listed:
            parts = path.split('/')
            if any('/'.join(parts[:i]) in listed for i in range(1, len(parts))):
                raise PackageError('A listed file is nested under another listed file.')
        total = sum(meta['size'] for meta in files.values())
        if sum(info.file_size for info in infos.values()) > MAX_RATIO_BYTES + runtime_manifest.MANIFEST_MAX_BYTES:
            raise PackageError('The package expands beyond the allowed size.')
        free = shutil.disk_usage(scratch).free
        if free < total + (64 << 20):
            raise PackageError('Not enough free disk space to unpack this update (' + str(total >> 20) + ' MiB needed).')
        counter = [0, total]
        for path in sorted(files):
            meta, info = files[path], infos[path]
            if info.file_size != meta['size']:
                raise PackageError('A package file size disagrees with the manifest: ' + path)
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as out:
                digest = _copy(archive, info, meta['size'], out, job, 'unpacking', counter)
            if not hmac.compare_digest(digest, meta['sha256']):
                raise PackageError('A package file does not match its manifest digest: ' + path)
        fd = os.open(scratch / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(raw)
    return manifest, raw


def _seal(scratch, manifest):
    for base, dirs, names in os.walk(scratch):
        for item in names:
            rel = (Path(base) / item).relative_to(scratch).as_posix()
            os.chmod(Path(base) / item, 0o555 if rel in EXECUTABLE else 0o444)
    for base, dirs, _ in os.walk(scratch, topdown=False):
        os.chmod(base, 0o555)


def _read_stamp(source):
    try:
        fd = _open_below(source, STAMP.split('/'))
        with os.fdopen(fd, 'rb') as handle:
            stamp = json.loads(handle.read(runtime_manifest.MANIFEST_MAX_BYTES).decode('utf-8'))
    except (OSError, ValueError):
        stamp = None
    jars = stamp.get('jars') if isinstance(stamp, dict) else None
    if (not isinstance(jars, dict) or set(jars) != {'server', 'client'}
            or not all(isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v) for v in jars.values())):
        raise PackageError('The source folder ' + str(source) + ' has no usable build record. Run ' + BUILD_SCRIPT
                           + ' in it, then press Download again, or choose Update Source and Rebuild. Nothing was installed.', 'needs-build')
    return stamp


def _open_below(source, parts):
    """Open a regular file below `source` without following any link on the way."""
    fds = [os.open(source, DIR_FLAGS)]
    try:
        for part in parts[:-1]:
            fds.append(os.open(part, DIR_FLAGS, dir_fd=fds[-1]))
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fds[-1])
    finally:
        for opened in fds:
            os.close(opened)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise OSError('not an ordinary file')
    return fd


def _differences(stamp, manifest):
    """Short, plain list of what differs between a local build record and a release manifest."""
    names = [f'{kind} {key}' for kind in ('pin',) for key in sorted(manifest['pins']) if stamp.get('pins', {}).get(key) != manifest['pins'][key]]
    recorded = stamp.get('patches') if isinstance(stamp.get('patches'), dict) else {}
    names += sorted(key for key in set(manifest['patches']) | set(recorded) if recorded.get(key) != manifest['patches'].get(key))
    shown = ', '.join(names[:3]) + (' and ' + str(len(names) - 3) + ' more' if len(names) > 3 else '')
    return shown or 'the build record'


def _supply(scratch, manifest, roots, job, install=None):
    """Fill the manifest's locally supplied paths from the first registered source folder whose build matches it."""
    local = runtime_manifest.local_paths(manifest)
    if not local:
        return
    if not roots:
        command = 'python3 ' + str(Path(install) / 'bootstrap/managed_install.py') + ' supply-root ' + str(install) + ' <source folder>' if install else 'supply-root'
        raise PackageError('Release ' + manifest['release'] + ' does not include the game programs or game data; they come from a '
                           'build made on this computer. Build SoloScape from source (' + BUILD_SCRIPT + ' in your source folder), '
                           'register that folder with: ' + command + ' and press Download again. Nothing was installed.', 'needs-build')
    refusal = None
    for root in roots:
        source = Path(root)
        try:
            stamp = _read_stamp(source)
            if stamp.get('pins') != manifest['pins'] or stamp.get('patches') != manifest['patches']:
                commit = manifest['source_commit']
                where = '' if set(commit) == {'0'} else ' (source commit ' + commit[:12] + ')'
                raise PackageError('Release ' + manifest['release'] + ' needs a different build than the one in ' + str(source)
                                   + ' (differs: ' + _differences(stamp, manifest) + '). Update that folder to the source of release '
                                   + manifest['release'] + where + ', run ' + BUILD_SCRIPT + ' in it, then press Download again, or choose '
                                   'Update Source and Rebuild to fetch and build the release source automatically. '
                                   'Your installed version keeps working.', 'needs-rebuild')
            return _copy_local(source, scratch, manifest, stamp, local, job)
        except PackageError as exc:
            if isinstance(exc, Cancelled):
                raise
            refusal = refusal or exc
    raise refusal


def _copy_local(source, scratch, manifest, stamp, local, job):
    sizes = {}
    for path in local:
        try:
            fd = _open_below(source, path.split('/'))
        except OSError:
            raise PackageError('The build in ' + str(source) + ' is missing a file this release needs: ' + path + '. Run ' + BUILD_SCRIPT
                               + ' in it again, then press Download, or choose Update Source and Rebuild.', 'needs-rebuild') from None
        with os.fdopen(fd, 'rb') as handle:
            sizes[path] = os.fstat(handle.fileno()).st_size
        if sizes[path] > runtime_manifest.FILE_MAX_BYTES:
            raise PackageError('A local build file is larger than the supported maximum: ' + path)
    total = sum(sizes.values())
    if total + sum(m['size'] for m in manifest['files'].values() if 'size' in m) > runtime_manifest.TOTAL_MAX_BYTES:
        raise PackageError('The local build is larger than the supported maximum.')
    if shutil.disk_usage(scratch).free < total + (64 << 20):
        raise PackageError('Not enough free disk space to copy your local build (' + str(total >> 20) + ' MiB needed).')
    roles = {manifest['roles']['server']: stamp['jars']['server'], manifest['roles']['client']: stamp['jars']['client']}
    record, counter = {}, [0, total]
    for path in local:
        target = scratch / path
        target.parent.mkdir(parents=True, exist_ok=True)
        digest, copied = hashlib.sha256(), 0
        with os.fdopen(_open_below(source, path.split('/')), 'rb') as src:
            out_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(out_fd, 'wb') as out:
                while True:
                    job.check()
                    chunk = src.read(CHUNK)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > sizes[path]:
                        raise PackageError('A local build file changed while it was being copied: ' + path)
                    digest.update(chunk)
                    out.write(chunk)
                    counter[0] += len(chunk)
                    job.report('copying local build', counter[0], counter[1])
        if copied != sizes[path]:
            raise PackageError('A local build file changed while it was being copied: ' + path)
        if path in roles and digest.hexdigest() != roles[path]:
            raise PackageError('The programs in ' + str(source) + ' changed after they were built. Run ' + BUILD_SCRIPT
                               + ' in it again, then press Download, or choose Update Source and Rebuild.', 'needs-rebuild')
        record[path] = {'sha256': digest.hexdigest(), 'size': copied}
    fd = os.open(scratch / runtime_manifest.SUPPLIED_NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write((json.dumps({'format': runtime_manifest.SUPPLIED_FORMAT, 'files': record}, indent=2, sort_keys=True) + '\n').encode())


def install_zip(root, zip_path, sha256, expected_release=None, job=None, supply_roots=()):
    """Verify, unpack and seal a local package as versions/<id>. Returns {id, release, already_present}."""
    with _StagingLock(Path(root)):
        return _install_locked(Path(root), zip_path, sha256, expected_release, job or Job(), supply_roots)


def _install_locked(root, zip_path, sha256, expected_release, job, supply_roots=()):
    """The staging lock is held by the caller."""
    if not isinstance(sha256, str) or not re.fullmatch('[0-9a-f]{64}', sha256):
        raise PackageError('The package digest must be 64 lowercase hex characters.')
    versions = root / 'versions'
    if versions.is_symlink() or not versions.is_dir():
        raise PackageError('The versions folder is missing or unsafe.')
    scratch = Path(tempfile.mkdtemp(prefix='.extract-', dir=_staging(root)))
    try:
        fd = os.open(zip_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        digest = hashlib.sha256()
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise PackageError('The package must be an ordinary file.')
            size = os.fstat(handle.fileno()).st_size
            if size > MAX_PACKAGE:
                raise PackageError('The package is larger than the supported maximum.')
            done = 0
            while chunk := handle.read(CHUNK):
                job.check()
                done += len(chunk)
                if done > MAX_PACKAGE:
                    raise PackageError('The package is larger than the supported maximum.')
                digest.update(chunk)
                job.report('verifying', done, size)
        if not hmac.compare_digest(digest.hexdigest(), sha256):
            raise PackageError('The package does not match the expected digest. Nothing was installed.')
        manifest, raw = _extract(zip_path, scratch, job)
        if expected_release is not None and manifest['release'] != expected_release:
            raise PackageError('The package is release ' + manifest['release'] + ', not the announced ' + expected_release + '.')
        _supply(scratch, manifest, supply_roots, job, root)
        try:
            _, version = runtime_manifest.validate_with_id(scratch)
        except (ValueError, OSError) as exc:
            raise PackageError('The unpacked payload was refused: ' + str(exc)) from None
        target = versions / version
        if os.path.lexists(target):
            _remove(scratch)
            return {'id': version, 'release': manifest['release'], 'already_present': True, 'zip_sha256': sha256}
        os.rename(scratch, target)  # a directory cannot be renamed into place once sealed read-only
        _seal(target, manifest)
        fd = os.open(versions, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return {'id': version, 'release': manifest['release'], 'already_present': False, 'zip_sha256': sha256}
    except BaseException:
        if os.path.lexists(scratch):
            _remove(scratch)
        raise


def fetch_and_install(root, package, job=None, transport=_open, supply_roots=(), rebuild=None):
    """Download the one declared release package (see _validate_package for the metadata), then install it.

    `rebuild(manifest, job)`, when given (an explicit player request), runs after the package is verified and before it
    is installed; it returns extra supply folders (a finished local build of the release's own source). The install
    step then gets a fresh whole-job deadline, since a build can outlast the download's."""
    _validate_package(package)
    job = job or Job()
    root = Path(root)
    with _StagingLock(root):
        part = Path(tempfile.mkdtemp(prefix='.part-', dir=_staging(root)))
        try:
            archive = part / 'package.zip'
            download(package['url'], package['size'], package['sha256'], archive, job, transport)
            if rebuild is not None:
                manifest = read_manifest(archive)
                if manifest['release'] != package['tag']:
                    raise PackageError('The package is release ' + manifest['release'] + ', not the announced ' + package['tag'] + '.')
                extra = rebuild(manifest, job)
                job = Job(cancelled=job.cancelled, progress=job.progress, clock=job.clock)
                supply_roots = list(supply_roots) + list(extra)
            return _install_locked(root, archive, package['sha256'], package['tag'], job, supply_roots)
        finally:
            _remove(part)
