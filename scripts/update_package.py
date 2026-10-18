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


class PackageError(Exception):
    """A refusal or unavailability. Its message is shown to the player as-is."""


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


def _extract(zip_path, scratch, job):
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, NotImplementedError, zlib.error, OSError) as exc:
        raise PackageError('The package is not a readable ZIP file.') from exc
    with archive:
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
        files = manifest['files']
        if set(infos) != set(files) | {name}:
            raise PackageError('The package entries must be exactly the manifest plus its listed files.')
        for path in files:
            parts = path.split('/')
            if any('/'.join(parts[:i]) in files for i in range(1, len(parts))):
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


def install_zip(root, zip_path, sha256, expected_release=None, job=None):
    """Verify, unpack and seal a local package as versions/<id>. Returns {id, release, already_present}."""
    with _StagingLock(Path(root)):
        return _install_locked(Path(root), zip_path, sha256, expected_release, job or Job())


def _install_locked(root, zip_path, sha256, expected_release, job):
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


def fetch_and_install(root, package, job=None, transport=_open):
    """Download the one declared release package (see _validate_package for the metadata), then install it."""
    _validate_package(package)
    job = job or Job()
    root = Path(root)
    with _StagingLock(root):
        part = Path(tempfile.mkdtemp(prefix='.part-', dir=_staging(root)))
        try:
            archive = part / 'package.zip'
            download(package['url'], package['size'], package['sha256'], archive, job, transport)
            return _install_locked(root, archive, package['sha256'], package['tag'], job)
        finally:
            _remove(part)
