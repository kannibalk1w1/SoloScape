"""Experimental asset-free update-bundle staging: verify, then stage a candidate. See README.md."""
import argparse
import fcntl
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

FORMAT = 1
REPOSITORY = 'kannibalk1w1/SoloScape'
PLATFORM = 'linux-x86_64'
CACHE_REVISION = 634  # declared only; never detected from the payload
ROLES = ('launcher', 'client', 'server')
MODES = {'0644': 0o644, '0755': 0o755}
MAX_ARCHIVE = 8 << 20
MAX_MANIFEST = 64 << 10
MAX_FILE = 4 << 20
MAX_OUTPUT = 16 << 20
MAX_FILES = 100
CHUNK = 64 << 10
LOCK_NAME = '.update-staging.lock'
PATH_RE = re.compile(r'app(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)+')
PRIVATE_SEGMENTS = {'.runtime', '.git', 'profiles', 'caches', 'cache', 'saves', 'backups', 'credentials'}
HEX64 = re.compile(r'[0-9a-f]{64}')
HEX40 = re.compile(r'[0-9a-f]{40}')
ROOT = Path(__file__).resolve().parents[2]  # the CLI lab is always ROOT/.runtime/update-lab


class StageError(Exception):
    """A refusal: the bundle or request is not stageable."""


def _freeze(bundle_path, expected_sha256):
    """Read the bundle once with a hard bound, refuse if it changed while read, then check its digest."""
    fd = os.open(bundle_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ARCHIVE:
            raise StageError('bundle must be a regular file of at most 8 MiB')
        chunks, total = [], 0
        while chunk := os.read(fd, CHUNK):
            total += len(chunk)
            if total > MAX_ARCHIVE:
                raise StageError('bundle grows past the 8 MiB archive limit')
            chunks.append(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or total != before.st_size:
        raise StageError('bundle changed while it was being read')
    data = b''.join(chunks)
    digest = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(digest, expected_sha256):
        raise StageError('archive sha256 does not match the expected digest')
    return data, digest


def _parse_manifest(raw):
    def no_duplicates(pairs):
        if len({key for key, _ in pairs}) != len(pairs):
            raise StageError('manifest has a duplicate JSON key')
        return dict(pairs)

    def refuse_constant(name):
        raise StageError(f'manifest uses non-JSON constant {name}')
    try:  # ValueError includes UnicodeDecodeError and JSONDecodeError
        return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicates, parse_constant=refuse_constant)
    except ValueError as exc:
        raise StageError(f'manifest is not strict UTF-8 JSON: {exc}') from None


def _check_path(path):
    if not (isinstance(path, str) and PATH_RE.fullmatch(path)):
        raise StageError(f'unsafe payload path {path!r}')
    segments = path.split('/')
    if PRIVATE_SEGMENTS & set(segments) or ['config', 'local.env'] in [segments[i:i + 2] for i in range(len(segments))]:
        raise StageError(f'mutable or private path {path!r}')


def _validate_manifest(doc):
    if not (isinstance(doc, dict) and set(doc) == {'format', 'repository', 'source_commit40', 'platform', 'cache_revision', 'roles', 'files'}):
        raise StageError('manifest keys must be exactly the v1 set')
    if type(doc['format']) is not int or doc['format'] != FORMAT:
        raise StageError('manifest format must be the integer 1')
    if doc['repository'] != REPOSITORY or doc['platform'] != PLATFORM:
        raise StageError('manifest repository or platform is not accepted')
    if not (isinstance(doc['source_commit40'], str) and HEX40.fullmatch(doc['source_commit40'])):
        raise StageError('source_commit40 must be 40 lowercase hex digits')
    if type(doc['cache_revision']) is not int or doc['cache_revision'] != CACHE_REVISION:
        raise StageError(f'cache_revision must be the integer {CACHE_REVISION}')
    roles, files = doc['roles'], doc['files']
    if not (isinstance(roles, dict) and set(roles) == set(ROLES)):
        raise StageError('roles must be exactly launcher, client and server')
    if not (isinstance(files, dict) and 0 < len(files) <= MAX_FILES):
        raise StageError(f'files must hold 1..{MAX_FILES} entries')
    for path, meta in files.items():
        _check_path(path)
        if not (isinstance(meta, dict) and set(meta) == {'sha256', 'size', 'mode'}):
            raise StageError(f'file entry for {path} must be exactly sha256, size, mode')
        if not (isinstance(meta['sha256'], str) and HEX64.fullmatch(meta['sha256'])):
            raise StageError(f'sha256 for {path} must be 64 lowercase hex digits')
        if type(meta['size']) is not int or not 0 <= meta['size'] <= MAX_FILE:
            raise StageError(f'size for {path} must be an integer in 0..4 MiB')
        if not (isinstance(meta['mode'], str) and meta['mode'] in MODES):
            raise StageError(f'mode for {path} must be "0644" or "0755"')
    targets = [roles[role] for role in ROLES]
    if not all(isinstance(t, str) and t in files for t in targets) or len(set(targets)) != len(ROLES):
        raise StageError('roles must name three distinct listed files')
    return doc


def _members(zf):
    infos = zf.infolist()
    if len({info.filename for info in infos}) != len(infos):
        raise StageError('ZIP has a duplicate entry name')
    for info in infos:  # ZipInfo truncates at NUL and rewrites separators; refuse before mapping names
        if info.orig_filename != info.filename or '\0' in info.orig_filename:
            raise StageError(f'ZIP entry name {info.orig_filename!r} is altered or contains NUL')
        if info.flag_bits & 0x1:
            raise StageError(f'encrypted ZIP entry {info.filename!r}')
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise StageError(f'unsupported compression for {info.filename!r}')
        if info.is_dir() or not stat.S_ISREG(info.external_attr >> 16):
            raise StageError(f'ZIP entry {info.filename!r} is not a regular file')
    return {info.filename: info for info in infos}


def _stream(zf, info, size, out=None):
    """Copy one member through a bounded loop; return its SHA-256 and reject any size drift."""
    digest, total = hashlib.sha256(), 0
    with zf.open(info) as src:
        while chunk := src.read(CHUNK):
            total += len(chunk)
            if total > size:
                raise StageError(f'{info.filename!r} streams more bytes than declared')
            digest.update(chunk)
            if out:
                out.write(chunk)
    if total != size or info.file_size != size:
        raise StageError(f'{info.filename!r} size disagrees with its declared size')
    return digest.hexdigest()


def _stage_members(zf, archive_sha, partial):
    infos = _members(zf)
    if 'manifest.json' not in infos:
        raise StageError('bundle has no manifest.json')
    minfo = infos['manifest.json']
    if minfo.file_size > MAX_MANIFEST:
        raise StageError('manifest exceeds 64 KiB')
    buf = io.BytesIO()
    _stream(zf, minfo, minfo.file_size, buf)
    raw = buf.getvalue()
    doc = _validate_manifest(_parse_manifest(raw))
    files = doc['files']
    if set(infos) != set(files) | {'manifest.json'}:
        raise StageError('ZIP entries must be exactly manifest.json plus the listed files')
    if sum(meta['size'] for meta in files.values()) > MAX_OUTPUT:
        raise StageError('declared output exceeds 16 MiB')
    for path in files:  # no listed file may also be a directory for another listed file
        parts = path.split('/')
        if any('/'.join(parts[:i]) in files for i in range(2, len(parts))):
            raise StageError(f'{path!r} is nested under a listed file')
    for path in sorted(files):
        meta, info = files[path], infos[path]
        if info.file_size != meta['size']:
            raise StageError(f'ZIP size for {path} disagrees with the manifest')
        target = partial / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as out:
            digest = _stream(zf, info, meta['size'], out)
        if not hmac.compare_digest(digest, meta['sha256']):
            raise StageError(f'sha256 for {path} does not match the manifest')
        os.chmod(target, MODES[meta['mode']])  # only the declared mode, never the archive's
    (partial / 'manifest.json').write_bytes(raw)
    declared = {'format': FORMAT, 'repository': REPOSITORY, 'platform': PLATFORM, 'cache_revision_detected': False,
                'source_commit40': doc['source_commit40'], 'cache_revision': doc['cache_revision']}
    limits = {'archive_bytes': MAX_ARCHIVE, 'manifest_bytes': MAX_MANIFEST, 'file_bytes': MAX_FILE,
              'output_bytes': MAX_OUTPUT, 'files': MAX_FILES}
    report = {'result': 'staged', 'provisional': True, 'archive_sha256': archive_sha, 'declared': declared,
              'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'roles': doc['roles'], 'limits': limits,
              'files': {path: files[path] for path in sorted(files)}}
    (partial / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report


def stage(bundle_path, expected_archive_sha256, lab_root):
    """Stage a verified bundle into a new candidate named by its archive digest; return the report."""
    if not (isinstance(expected_archive_sha256, str) and HEX64.fullmatch(expected_archive_sha256)):
        raise StageError('expected archive sha256 must be 64 lowercase hex digits')
    lab = Path(lab_root)
    if lab.is_symlink() or not lab.is_dir():
        raise StageError('lab root must be an existing real directory, not a symlink')
    data, archive_sha = _freeze(bundle_path, expected_archive_sha256)
    candidate = lab / archive_sha
    try:
        lock = os.open(lab / LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except OSError as exc:
        raise StageError('staging guard must be a readable regular file') from exc
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode):
            raise StageError('staging guard must be a regular file')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StageError('update lab is locked by another staging run') from None
        if os.path.lexists(candidate):
            raise StageError('candidate already exists for this archive')
        partial = Path(tempfile.mkdtemp(prefix='.partial-', dir=lab))
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                report = _stage_members(zf, archive_sha, partial)
            os.rename(partial, candidate)  # the only success signal: no pointer is written
        except BaseException as exc:
            shutil.rmtree(partial, ignore_errors=True)  # removes only this run's partial directory
            if isinstance(exc, (zipfile.BadZipFile, NotImplementedError, zlib.error)):
                raise StageError(f'bundle is not a readable ZIP: {exc}') from None
            raise
        return dict(report, candidate=str(candidate))
    finally:
        os.close(lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Stage an update bundle into the ignored update lab.')
    parser.add_argument('bundle')
    parser.add_argument('sha256')
    args = parser.parse_args(argv)
    runtime = ROOT / '.runtime'
    lab = runtime / 'update-lab'
    try:
        if runtime.is_symlink() or lab.is_symlink():
            raise StageError('.runtime and update-lab must not be symlinks')
        runtime.mkdir(exist_ok=True)
        lab.mkdir(exist_ok=True)
        report = stage(args.bundle, args.sha256, lab)
    except (StageError, OSError) as exc:
        print(f'stage refused: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
