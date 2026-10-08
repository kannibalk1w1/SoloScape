"""Private world/character profiles and verified generation-based save recovery.

Content/cache are shared read-only inputs. A profile owns every mutable storage path.
Backups/restores require an exclusive profile lock; restoring switches one atomic
manifest pointer and retains the old generation rather than rewriting live files.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import tempfile
import tomllib
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / '.runtime/profiles'
FORMAT = 1
MAX_FILE = 32 * 1024 * 1024
MAX_BACKUP = 512 * 1024 * 1024
MAX_FILES = 10000
SAFE_ID = re.compile(r'[a-f0-9]{32}\Z')
ACCOUNT = re.compile(r'[A-Za-z0-9 _]{1,12}\Z')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def identifier(value):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError('Invalid profile or save-generation identifier.')
    return value


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def private_directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('Profile storage cannot be a symbolic link.')
    path.chmod(0o700)


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def validate_save(data, expected_account=None):
    """Validate native PlayerSave's structural fields; preserve bytes, never rewrite it."""
    if len(data) > MAX_FILE:
        raise ValueError('Character save is too large.')
    try:
        save = tomllib.loads(data.decode('utf-8'))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError('Character save is not valid TOML.') from exc
    name = save.get('accountName')
    if not isinstance(name, str) or not ACCOUNT.fullmatch(name) or not name.strip():
        raise ValueError('Character save has an invalid account name.')
    if expected_account and name.casefold() != expected_account.casefold():
        raise ValueError('Character save belongs to a different account.')
    if not isinstance(save.get('passwordHash'), str):
        raise ValueError('Character save is missing its authentication hash.')
    for key, length in [('experience', 25), ('levels', 25), ('looks', 7), ('colours', 5)]:
        values = save.get(key)
        if not isinstance(values, list) or len(values) != length or any(type(n) is not int or n < 0 for n in values):
            raise ValueError(f'Character save has invalid {key}.')
    tile = save.get('tile')
    if not isinstance(tile, dict) or any(type(tile.get(k)) is not int or not 0 <= tile[k] <= 16383 for k in ('x', 'y')):
        raise ValueError('Character save has an invalid location.')
    if type(tile.get('level', 0)) is not int or not 0 <= tile.get('level', 0) <= 3:
        raise ValueError('Character save has an invalid plane.')
    inventories = save.get('inventories', {})
    if not isinstance(inventories, dict):
        raise ValueError('Character inventories are invalid.')
    for items in inventories.values():
        if not isinstance(items, list) or len(items) > 10000:
            raise ValueError('Character inventory size is invalid.')
        for item in items:
            if not isinstance(item, dict) or (item and (not isinstance(item.get('id'), str) or type(item.get('amount', 1)) is not int or not 1 <= item.get('amount', 1) <= 2147483647)):
                raise ValueError('Character inventory item is invalid.')
    return save


class Profile:
    def __init__(self, directory):
        self.directory = Path(directory)
        if self.directory.is_symlink():
            raise ValueError('Profile storage cannot be a symbolic link.')
        self.reload()

    def reload(self):
        path = self.directory / 'profile.json'
        if path.is_symlink():
            raise ValueError('Profile manifest cannot be a symbolic link.')
        self.manifest = json.loads(path.read_text())
        if not isinstance(self.manifest, dict):
            raise ValueError('Profile manifest is corrupt; preserve it for recovery.')
        if (self.directory / 'states').is_symlink():
            raise ValueError('Profile generations cannot be symbolic links.')
        if self.manifest.get('format') != FORMAT:
            raise ValueError('Unsupported profile format; preserve it and use a compatible launcher.')
        if identifier(self.manifest.get('id')) != self.directory.name:
            raise ValueError('Profile identity does not match its directory.')
        identifier(self.manifest.get('generation'))
        if not ACCOUNT.fullmatch(self.manifest.get('account', '')):
            raise ValueError('Invalid profile account.')
        if not self.state.is_dir() or self.state.is_symlink():
            raise ValueError('Profile state generation is missing or unsafe. Restore a verified backup.')

    @property
    def state(self):
        return self.directory / 'states' / identifier(self.manifest['generation'])

    @contextmanager
    def lock(self, reload=True):
        path = self.directory / 'profile.lock'
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('This character/world is running or another save operation is active.') from exc
            if reload:
                self.reload()
            yield self

    def metadata(self):
        result = {k: self.manifest[k] for k in ('id', 'label', 'account', 'created', 'last_played')}
        save_path = self.state / 'saves' / (self.manifest['account'].lower() + '.toml')
        result.update(saved=False, location=None, saved_at=None, error=None)
        result['storage_bytes'] = sum(p.stat().st_size for p in self.directory.rglob('*') if p.is_file() and not p.is_symlink())
        result['backup_count'] = len(list((self.directory / 'backups').glob('*.zip')))
        result['retention'] = 'Backups and previous generations are kept until explicitly removed.'
        if save_path.exists():
            try:
                if save_path.is_symlink():
                    raise ValueError('Character save cannot be a symbolic link.')
                save = validate_save(save_path.read_bytes(), self.manifest['account'])
                result.update(saved=True, location=save['tile'], saved_at=datetime.fromtimestamp(save_path.stat().st_mtime, timezone.utc).isoformat(timespec='seconds'))
            except (OSError, ValueError) as exc:
                result['error'] = str(exc)
        return result

    def environment(self, port=43594):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('Choose a game port between 1 and 65535.')
        for name in ('saves','errors','logs','temp'):
            if (self.state/name).is_symlink():
                raise ValueError('Mutable profile directories cannot be symbolic links.')
        state = self.state.resolve()
        paths = {'storage.players.path': state / 'saves', 'storage.players.logs': state / 'logs',
                 'storage.players.errors': state / 'errors', 'storage.data.modified': state / 'temp/modified.dat',
                 'storage.wildcards': state / 'temp/wildcards.txt', 'storage.caching.path': state / 'temp'}
        env = {key: str(value) + ('/' if key.endswith('.path') and key != 'storage.data.modified' else '') for key, value in paths.items()}
        env.update({'network.bind': '127.0.0.1', 'network.port': str(port), 'storage.type': 'files',
                    'development.admin.name': '', 'development.accountCreation': 'true',
                    'world.start.tutorial': str(self.manifest.get('tutorial', False)).lower(),
                    'world.start.creation': 'false', 'web.server.enabled': 'false', 'bots.count': '0',
                    'soloscape.profile.account': self.manifest['account'],
                    'SOLOSCAPE_AUTH_FILE': str(self.directory / 'login.json')})
        # Exchange/report paths are relative to FileStorage's already isolated saves.
        return env

    def mark_played(self):
        self.manifest['last_played'] = now()
        atomic_json(self.directory / 'profile.json', self.manifest)

    def _files(self):
        files = []
        for path in self.state.rglob('*'):
            if path.is_symlink():
                raise ValueError('World state contains a symbolic link; backup refused.')
            if path.name.startswith('.save-') and path.name.endswith('.tmp'):
                continue
            if path.is_file() and path.relative_to(self.state).parts[0] in ('saves', 'errors'):
                if path.stat().st_size > MAX_FILE:
                    raise ValueError('A world-state file is too large for this backup format.')
                files.append(path)
        if len(files) > MAX_FILES or sum(p.stat().st_size for p in files) > MAX_BACKUP:
            raise ValueError('World state exceeds the backup size limit.')
        return sorted(files)

    def backup(self, reason='manual'):
        with self.lock():
            return self._backup(reason)

    def _backup(self, reason):
        backup_dir = self.directory / 'backups'
        private_directory(backup_dir)
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.zip'
        target = backup_dir / name
        temporary = backup_dir / ('.' + name + '.tmp')
        contents = {}
        files = self._files()
        for path in files:
            relative = path.relative_to(self.state).as_posix()
            data = path.read_bytes()
            if relative.startswith('saves/') and relative.endswith('.toml') and '/' not in relative[6:]:
                validate_save(data)
            contents[relative] = data
        manifest = {'format': FORMAT, 'profile': self.manifest['id'], 'account': self.manifest['account'],
                    'metadata': {k: self.manifest[k] for k in ('label', 'created', 'last_played', 'tutorial')},
                    'created': now(), 'reason': reason, 'files': {name: {'sha256': hash_bytes(data), 'size': len(data)} for name, data in contents.items()}}
        try:
            with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('backup.json', json.dumps(manifest))
                for member, data in contents.items():
                    archive.writestr('state/' + member, data)
            temporary.chmod(0o600)
            self.validate_backup(temporary)
            with temporary.open('rb') as source:
                os.fsync(source.fileno())
            temporary.replace(target)
            fsync_directory(backup_dir)
            return target
        finally:
            temporary.unlink(missing_ok=True)

    def validate_backup(self, path):
        try:
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                names = [info.filename for info in infos]
                if len(names) != len(set(names)) or len(names) > MAX_FILES + 1:
                    raise ValueError('Backup has duplicate or too many entries.')
                if sum(i.file_size for i in infos) > MAX_BACKUP or any(i.file_size > MAX_FILE for i in infos):
                    raise ValueError('Backup is too large.')
                if 'backup.json' not in names:
                    raise ValueError('Backup manifest is missing.')
                manifest = json.loads(archive.read('backup.json'))
                if not isinstance(manifest, dict):
                    raise ValueError('Backup manifest is invalid.')
                if manifest.get('format') != FORMAT or manifest.get('profile') != self.manifest['id'] or manifest.get('account') != self.manifest['account']:
                    raise ValueError('Backup belongs to a different profile or format.')
                records = manifest.get('files')
                if not isinstance(records, dict) or set(names) != {'backup.json'} | {'state/' + n for n in records}:
                    raise ValueError('Backup manifest and entries do not match.')
                result = {}
                for relative, record in records.items():
                    if not isinstance(record, dict):
                        raise ValueError('Backup file record is invalid.')
                    p = PurePosixPath(relative)
                    if not relative or p.is_absolute() or '..' in p.parts or '\\' in relative or str(p) != relative:
                        raise ValueError('Backup has an unsafe path.')
                    member = archive.getinfo('state/' + relative)
                    if member.is_dir() or member.external_attr >> 16 & 0o170000 == 0o120000:
                        raise ValueError('Backup contains an unsupported link/directory.')
                    data = archive.read(member)
                    if len(data) != record['size'] or hash_bytes(data) != record['sha256']:
                        raise ValueError('Backup checksum does not match.')
                    if relative.startswith('saves/') and relative.endswith('.toml') and '/' not in relative[6:]:
                        validate_save(data)
                    result[relative] = data
                return manifest, result
        except (zipfile.BadZipFile, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError('Backup is corrupt or has an invalid manifest.') from exc

    def restore(self, backup_name, recovery=False):
        if Path(backup_name).name != backup_name or not re.fullmatch(r'[A-Za-z0-9_-]+\.zip', backup_name):
            raise ValueError('Select a backup from this profile.')
        with self.lock(reload=not recovery):
            if recovery:
                recovered_metadata = self.manifest
                try:
                    self.reload()
                except (ValueError, OSError, KeyError):
                    self.manifest = recovered_metadata
                else:
                    raise RuntimeError('This profile was recovered meanwhile. Select its backup again.')
            backup = self.directory / 'backups' / backup_name
            if backup.is_symlink():
                raise ValueError('Backup cannot be a symbolic link.')
            manifest, contents = self.validate_backup(backup)
            generation = uuid.uuid4().hex
            target = self.directory / 'states' / generation
            private_directory(target)
            try:
                for directory in ('saves', 'logs', 'errors', 'temp'):
                    private_directory(target / directory)
                for relative, data in contents.items():
                    path = target / relative
                    private_directory(path.parent)
                    with path.open('xb') as out:
                        os.fchmod(out.fileno(), 0o600)
                        out.write(data)
                        out.flush()
                        os.fsync(out.fileno())
                for directory in sorted((p for p in target.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                    fsync_directory(directory)
                fsync_directory(target)
                fsync_directory(target.parent)
                changed = dict(self.manifest)
                changed['generation'] = generation
                changed['restored_at'] = now()
                changed['restored_from'] = backup_name
                # Old generation remains available even if original saves were corrupt.
                changed['previous_generations'] = self.manifest.get('previous_generations', []) + [self.manifest['generation']]
                if recovery:
                    damaged = self.directory / 'profile.json'
                    if damaged.exists():
                        if damaged.is_symlink():
                            raise ValueError('Profile manifest cannot be a symbolic link.')
                        preserved = self.directory / ('damaged-manifest-' + uuid.uuid4().hex + '.json')
                        shutil.copyfile(damaged, preserved)
                        preserved.chmod(0o600)
                        with preserved.open('rb') as source:
                            os.fsync(source.fileno())
                        fsync_directory(self.directory)
                atomic_json(self.directory / 'profile.json', changed)
                self.reload()
                return {'generation': generation, 'restored_from': backup_name, 'files': len(contents)}
            except BaseException:
                # After a successful atomic switch this is the active world; never remove it.
                try:
                    disk = json.loads((self.directory / 'profile.json').read_text())
                except (OSError, ValueError):
                    disk = {}
                if disk.get('generation') != generation:
                    shutil.rmtree(target)
                raise


def create(label, account, password=None, tutorial=False):
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 48:
        raise ValueError('Character label must be 1–48 characters.')
    if not isinstance(account, str) or not ACCOUNT.fullmatch(account) or not account.strip():
        raise ValueError('Account name must be 1–12 letters, numbers, spaces or underscores.')
    private_directory(PROFILES)
    uid, generation = uuid.uuid4().hex, uuid.uuid4().hex
    directory = PROFILES / uid
    private_directory(directory)
    private_directory(directory / 'states')
    state = directory / 'states' / generation
    private_directory(state)
    for name in ('saves', 'logs', 'errors', 'temp'):
        private_directory(state / name)
    manifest = {'format': FORMAT, 'id': uid, 'label': label.strip(), 'account': account.strip(),
                'created': now(), 'last_played': None, 'generation': generation, 'tutorial': bool(tutorial)}
    atomic_json(directory / 'profile.json', manifest)
    atomic_json(directory / 'login.json', {'account': manifest['account'], 'password': password if password is not None else secrets.token_hex(8)})
    return Profile(directory)


def load(uid):
    return Profile(PROFILES / identifier(uid))


def list_profiles():
    if not PROFILES.exists():
        return []
    result = []
    for directory in sorted(PROFILES.iterdir()):
        if not SAFE_ID.fullmatch(directory.name):
            continue
        try:
            result.append(Profile(directory).metadata())
        except (OSError, ValueError, KeyError) as exc:
            result.append({'id': directory.name, 'label': 'Profile needs recovery', 'error': str(exc), 'saved': False})
    return result


def import_character(source, label):
    source = Path(source)
    if source.is_symlink() or not source.is_file():
        raise ValueError('Choose a regular native character save file.')
    data = source.read_bytes()
    save = validate_save(data)
    profile = create(label, save['accountName'], password='')
    try:
        with profile.lock():
            target = profile.state / 'saves' / (save['accountName'].lower() + '.toml')
            target.write_bytes(data)
            target.chmod(0o600)
            profile._backup('imported-copy')
        return profile
    except BaseException:
        shutil.rmtree(profile.directory)
        raise


def recovery_profile(uid, backup_name):
    """Construct recovery metadata only; never launch a damaged profile through this path."""
    directory = PROFILES / identifier(uid)
    if directory.is_symlink() or (directory / 'states').is_symlink():
        raise ValueError('Profile recovery storage cannot be a symbolic link.')
    if not isinstance(backup_name, str) or Path(backup_name).name != backup_name or not re.fullmatch(r'[A-Za-z0-9_-]+\.zip', backup_name):
        raise ValueError('Select a backup from this profile.')
    backup = directory / 'backups' / backup_name
    if (directory / 'backups').is_symlink() or backup.is_symlink():
        raise ValueError('Recovery backup cannot be a symbolic link.')
    try:
        with zipfile.ZipFile(backup) as archive:
            info = archive.getinfo('backup.json')
            if info.file_size > MAX_FILE:
                raise ValueError('Backup metadata is too large.')
            header = json.loads(archive.read(info))
        if not isinstance(header, dict) or header.get('profile') != uid:
            raise ValueError('Backup belongs to a different profile.')
        account = header.get('account')
        if not isinstance(account, str) or not ACCOUNT.fullmatch(account) or not account.strip():
            raise ValueError('Recovery backup account is invalid.')
        metadata = header.get('metadata', {})
        if not isinstance(metadata, dict):
            raise ValueError('Recovery metadata is invalid.')
        profile = object.__new__(Profile)
        profile.directory = directory
        profile.manifest = {'format': FORMAT, 'id': uid, 'account': account,
            'label': str(metadata.get('label', 'Recovered character'))[:48],
            'created': header.get('created', now()), 'last_played': None,
            'tutorial': bool(metadata.get('tutorial', False)), 'generation': uuid.uuid4().hex}
        profile.validate_backup(backup)
        return profile
    except (zipfile.BadZipFile, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Recovery backup metadata is corrupt.') from exc


def list_backups(uid):
    directory = PROFILES / identifier(uid)
    if directory.is_symlink() or (directory / 'backups').is_symlink():
        raise ValueError('Backup storage cannot be a symbolic link.')
    result = []
    for path in sorted((directory / 'backups').glob('*.zip'), reverse=True):
        try:
            profile = recovery_profile(uid, path.name)
            manifest, _ = profile.validate_backup(path)
            result.append({'name': path.name, 'created': manifest['created'], 'reason': manifest.get('reason', ''), 'valid': True})
        except (ValueError, OSError, KeyError) as exc:
            result.append({'name': path.name, 'valid': False, 'error': str(exc)})
    return result


def restore_profile(uid, backup_name):
    try:
        profile = load(uid)
    except (ValueError, OSError, KeyError):
        profile = recovery_profile(uid, backup_name)
        return profile.restore(backup_name, recovery=True)
    return profile.restore(backup_name)
