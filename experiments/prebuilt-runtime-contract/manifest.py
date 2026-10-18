"""Read-only validator for the private prebuilt-payload manifest experiment.

The manifest sits at <root>/soloscape-runtime.json and describes one fixed
linux-x86_64 payload. Validation only opens and reads: it never writes, chmods,
creates, copies, extracts, touches the network, or runs a subprocess. Pins,
patch hashes and the cache revision are checked for shape only; nothing here
authenticates them against a source checkout, a cache or a licence record.
"""
import hashlib
import json
import os
import re
import stat
from pathlib import Path

MANIFEST_NAME = 'soloscape-runtime.json'
MANIFEST_MAX_BYTES = 4 * 1024 * 1024
FILE_MAX_BYTES = 512 * 1024 * 1024
TOTAL_MAX_BYTES = 2 * 1024 * 1024 * 1024
FILE_MAX_COUNT = 10000
DIR_MAX_COUNT = 10000
DEPTH_MAX = 32
READ_CHUNK = 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

FORMAT = 1
PLATFORM = 'linux-x86_64'
CACHE_REVISION = 634
TOP_FIELDS = {'format', 'source_commit', 'platform', 'cache_revision', 'pins', 'patches', 'roles', 'files'}
PIN_FIELDS = {'game-server', '634-client', 'runelite-client'}
ROLE_FIELDS = {'server', 'client', 'launcher'}
RUNTIME_SCRIPTS = (
    'local_dev.py', 'profiles.py', 'death_loot_state.py', 'profile_session.py', 'session_recovery.py', 'launcher_backend.py',
    'release_updates.py', 'deck_awake.py', 'prebuilt_bootstrap.py', 'owned_launcher_backend.py',
    'prebuilt_manifest.py',
)
RUNTIME_SCRIPT_PATHS = frozenset(f'scripts/{name}' for name in RUNTIME_SCRIPTS)
LAUNCHER = 'scripts/launcher.sh'
SERVER_JAR = re.compile(r'upstream/game-server/game/build/libs/void-server-[^/]+\.jar')
CLIENT_JAR = re.compile(r'upstream/runelite-client/client/build/libs/void-client-[^/]+\.jar')
DATA_PREFIX = 'upstream/game-server/data/'
DATA_SUFFIXES = ('.toml', '.txt')
# Match the tracked-data selector: mutable state/cache lives directly under data/.
# Nested social/trade/exchange contains immutable interface/content definitions.
STATE_PARTS = frozenset({'cache', 'saves', 'errors', 'logs', 'temp', '.temp', 'exchange'})
FORBIDDEN_PARTS = frozenset({'.git', '.gradle', '.runtime', 'gradle', 'native'})
FORBIDDEN_NAMES = frozenset({'gradle.properties', 'gradlew', 'gradlew.bat'})
FORBIDDEN_SUFFIXES = ('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.m', '.mm', '.rs', '.gradle', '.gradle.kts')
PATCH_PATH = re.compile(r'patches/(client|server)/[0-9]{4}-[a-z0-9][a-z0-9-]*\.patch')


def validate(root):
    """Return the manifest for the payload at root, or raise ValueError/OSError. Writes nothing."""
    root_fd = _open_root(Path(root))
    try:
        manifest = _parse(_read_manifest(root_fd))
        _check_schema(manifest)
        files = manifest['files']
        walk = _Walk(set(files))
        walk.scan(root_fd, '', 0)
        missing = sorted(set(files) - walk.seen)
        if missing:
            raise ValueError(f'listed file is missing from the payload: {missing[0]!r}')
        for path, entry in files.items():
            _verify(root_fd, path, entry)
    finally:
        os.close(root_fd)
    return manifest


def _open_root(root):
    path = root.absolute()
    if '..' in path.parts:
        raise ValueError(f'payload root must not contain ".." components: {str(root)!r}')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        _require_dir(current)
    return os.open(path, DIR_FLAGS)


def _require_dir(path):
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        raise ValueError(f'symbolic link is not allowed in the payload root path: {str(path)!r}')
    if not stat.S_ISDIR(mode):
        raise ValueError(f'payload root path component is not a directory: {str(path)!r}')


def _read_manifest(root_fd):
    mode = os.stat(MANIFEST_NAME, dir_fd=root_fd, follow_symlinks=False).st_mode
    if stat.S_ISLNK(mode):
        raise ValueError(f'{MANIFEST_NAME} must not be a symbolic link')
    fd = os.open(MANIFEST_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
    try:
        _require_regular(os.fstat(fd), MANIFEST_NAME)
        data = bytearray()
        while len(data) <= MANIFEST_MAX_BYTES:
            chunk = os.read(fd, MANIFEST_MAX_BYTES + 1 - len(data))
            if not chunk:
                break
            data += chunk
    finally:
        os.close(fd)
    if len(data) > MANIFEST_MAX_BYTES:
        raise ValueError(f'{MANIFEST_NAME} exceeds the 4 MiB limit')
    return bytes(data)


def _parse(data):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError(f'{MANIFEST_NAME} is not valid UTF-8') from error
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_refuse_constant)
    except RecursionError as error:
        raise ValueError(f'{MANIFEST_NAME} is nested too deeply') from error
    if not isinstance(value, dict):
        raise ValueError(f'{MANIFEST_NAME} must contain a JSON object')
    return value


def _no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'duplicate JSON key: {key!r}')
        value[key] = item
    return value


def _refuse_constant(name):
    raise ValueError(f'non-finite JSON number is not allowed: {name}')


def _check_schema(manifest):
    _exact(manifest, TOP_FIELDS, 'manifest')
    _int_equal(manifest['format'], FORMAT, 'format')
    _check_hex(manifest['source_commit'], 40, 'source_commit')
    if manifest['platform'] != PLATFORM:
        raise ValueError(f'platform must be {PLATFORM!r}')
    _int_equal(manifest['cache_revision'], CACHE_REVISION, 'cache_revision')
    _check_pins(manifest['pins'])
    _check_patches(manifest['patches'])
    roles = _check_roles(manifest['roles'])
    files = _check_files(manifest['files'])
    for path in roles.values():
        if path not in files:
            raise ValueError(f'role path is not listed in files: {path!r}')
    required = RUNTIME_SCRIPT_PATHS | {LAUNCHER, roles['server'], roles['client']}
    for path in files:
        if path not in required and not _is_data_path(path):
            raise ValueError(f'file is not on the payload allowlist: {path!r}')
    missing = sorted(required - set(files))
    if missing:
        raise ValueError(f'files is missing required payload entries: {missing!r}')


def _check_pins(pins):
    _exact(pins, PIN_FIELDS, 'pins')
    for key in sorted(PIN_FIELDS):
        _check_hex(pins[key], 40, f'pins[{key!r}]')


def _check_patches(patches):
    if not isinstance(patches, dict) or not patches:
        raise ValueError('patches must be a non-empty object')
    sides = set()
    for path, digest in patches.items():
        match = PATCH_PATH.fullmatch(path) if isinstance(path, str) else None
        if match is None:
            raise ValueError(f'patch path must match patches/(client|server)/NNNN-name.patch: {path!r}')
        _check_hex(digest, 64, f'patches[{path!r}]')
        sides.add(match.group(1))
    if sides != {'client', 'server'}:
        raise ValueError('patches must include both client and server patches')


def _check_roles(roles):
    _exact(roles, ROLE_FIELDS, 'roles')
    for key in sorted(ROLE_FIELDS):
        if not isinstance(roles[key], str):
            raise ValueError(f'roles[{key!r}] must be a string')
    server, client, launcher = roles['server'], roles['client'], roles['launcher']
    if not SERVER_JAR.fullmatch(server):
        raise ValueError('roles.server must match upstream/game-server/game/build/libs/void-server-*.jar')
    if not CLIENT_JAR.fullmatch(client):
        raise ValueError('roles.client must match upstream/runelite-client/client/build/libs/void-client-*.jar')
    if launcher != LAUNCHER:
        raise ValueError(f'roles.launcher must be exactly {LAUNCHER!r}')
    if len({server, client, launcher}) != 3:
        raise ValueError('roles must name three distinct paths')
    for path in (server, client, launcher):
        _check_relative(path, 'role path')
    return roles


def _check_files(files):
    if not isinstance(files, dict) or not files:
        raise ValueError('files must be a non-empty object')
    if len(files) > FILE_MAX_COUNT:
        raise ValueError(f'files lists {len(files)} entries; the cap is {FILE_MAX_COUNT}')
    total = 0
    for path, entry in files.items():
        _check_relative(path, 'file path')
        _exact(entry, {'sha256', 'size'}, f'files[{path!r}]')
        _check_hex(entry['sha256'], 64, f'files[{path!r}].sha256')
        size = entry['size']
        if type(size) is not int or size < 0:
            raise ValueError(f'files[{path!r}].size must be a non-negative integer')
        if size > FILE_MAX_BYTES:
            raise ValueError(f'files[{path!r}].size exceeds the 512 MiB per-file cap')
        total += size
    if total > TOTAL_MAX_BYTES:
        raise ValueError(f'declared total of {total} bytes exceeds the 2 GiB cap')
    return files


def _is_data_path(path):
    return path.startswith(DATA_PREFIX) and path.endswith(DATA_SUFFIXES)


def _check_relative(path, label):
    if not isinstance(path, str) or not path:
        raise ValueError(f'{label} must be a non-empty string')
    if path.startswith('/'):
        raise ValueError(f'{label} must be relative: {path!r}')
    for part in path.split('/'):
        _check_name(part, path)
    return path


def _check_name(name, path):
    if name in ('', '.', '..') or '\\' in name or '\0' in name:
        raise ValueError(f'unsafe path component in {path!r}')
    try:
        name.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError(f'path is not valid UTF-8: {path!r}') from error
    if path.startswith(DATA_PREFIX) and path[len(DATA_PREFIX):].split('/')[0] in STATE_PARTS:
        raise ValueError(f'forbidden top-level cache/state path in {path!r}')
    if name in FORBIDDEN_PARTS:
        raise ValueError(f'forbidden payload path component {name!r} in {path!r}')
    if name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_SUFFIXES):
        raise ValueError(f'native source or Gradle file is not allowed in the payload: {path!r}')


def _exact(value, fields, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    if set(value) != fields:
        missing = sorted(fields - set(value))
        extra = sorted(set(value) - fields)
        raise ValueError(f'{label} fields must be exactly {sorted(fields)}; missing {missing}, extra {extra}')


def _int_equal(value, expected, label):
    if type(value) is not int or value != expected:
        raise ValueError(f'{label} must be the integer {expected}')


def _check_hex(value, length, label):
    if not isinstance(value, str) or re.fullmatch(f'[0-9a-f]{{{length}}}', value) is None:
        raise ValueError(f'{label} must be {length} lowercase hex characters')


class _Walk:
    """Scan the payload with directory fds so nothing outside the supplied root is followed."""

    def __init__(self, listed):
        self.listed = listed
        self.seen = set()
        self.dirs = 0

    def scan(self, dir_fd, rel, depth):
        if depth > DEPTH_MAX:
            raise ValueError(f'payload is nested deeper than {DEPTH_MAX} levels')
        for name in sorted(os.listdir(dir_fd)):
            child = f'{rel}/{name}' if rel else name
            _check_name(name, child)
            mode = os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f'symbolic link is not allowed in the payload: {child!r}')
            if stat.S_ISDIR(mode):
                self.dirs += 1
                if self.dirs > DIR_MAX_COUNT:
                    raise ValueError(f'payload has more than {DIR_MAX_COUNT} directories')
                fd = os.open(name, DIR_FLAGS, dir_fd=dir_fd)
                try:
                    self.scan(fd, child, depth + 1)
                finally:
                    os.close(fd)
            elif not stat.S_ISREG(mode):
                raise ValueError(f'special file is not allowed in the payload: {child!r}')
            elif not rel and name == MANIFEST_NAME:
                continue
            elif child in self.listed:
                self.seen.add(child)
            else:
                raise ValueError(f'unlisted file in the payload: {child!r}')


def _verify(root_fd, path, entry):
    fd = _open_leaf(root_fd, path)
    try:
        before = os.fstat(fd)
        _require_regular(before, path)
        digest = hashlib.sha256()
        total = 0
        expected = entry['size']
        while total <= expected:
            chunk = os.read(fd, min(READ_CHUNK, expected + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if _identity(before) != _identity(after):
        raise ValueError(f'file changed while it was being validated: {path!r}')
    if total != expected:
        raise ValueError(f'declared size {expected} does not match actual size of {path!r}')
    if digest.hexdigest() != entry['sha256']:
        raise ValueError(f'sha256 mismatch for {path!r}')


def _open_leaf(root_fd, path):
    *parents, leaf = path.split('/')
    opened = []
    current = root_fd
    try:
        for part in parents:
            current = os.open(part, DIR_FLAGS, dir_fd=current)
            opened.append(current)
        return os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
    finally:
        for fd in opened:
            os.close(fd)


def _require_regular(st, label):
    if not stat.S_ISREG(st.st_mode):
        raise ValueError(f'not a regular file: {label!r}')


def _identity(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
