"""Read-only validation of native death-loot world files and committed account batches.

Python never replays a pending batch. It proves that the batch journal and the logical
post-replay state are coherent, so backup, restore and import can preserve bytes verbatim.
This module imports nothing from profiles; callers pass their native save validator in.
"""
import base64
import hashlib
import re
import tomllib

WORLD_FILE = '.soloscape-death-loot.v1'
JOURNAL = 'saves/.soloscape-account-save'
BATCH_HEADER = 'SOLOSCAPE_ACCOUNT_BATCH_V1\n'
MAX_WORLD = 32 * 1024 * 1024
MAX_MANIFEST = 512 * 1024
MAX_MEMBER = 32 * 1024 * 1024
MAX_BATCH = 512 * 1024 * 1024
MAX_MEMBERS = 2049
MAX_GRAVES = 2048
MAX_PILES = 16384
MAX_SOURCES = 2048
INT_MAX = 2147483647
TILE_MAX = 1073741823

UUID_TEXT = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
ACCOUNT = re.compile(r'[a-z0-9 _-]{1,64}')
KIND = re.compile(r'[a-z0-9_]{1,128}')
DIGEST = re.compile(r'[0-9a-f]{64}')
MEMBER_ROW = re.compile(r'([a-z0-9 _-]{1,64}\.toml|' + re.escape(WORLD_FILE) + r')\t([1-9][0-9]{0,8})\t([0-9a-f]{64})')
GRAVE_KEYS = {'id', 'account', 'name', 'male', 'kind', 'tile', 'direction', 'remaining', 'blessed', 'latest'}
PILE_KEYS = {'id', 'item', 'amount', 'charges', 'tile', 'owner', 'sources', 'reveal', 'disappear'}


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _text(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _printable(value, minimum):
    return isinstance(value, str) and minimum <= len(value) <= 64 and value.isprintable()


def _exact(record, keys, label):
    if not isinstance(record, dict) or set(record) != keys:
        raise ValueError(label + ' has missing or unexpected fields.')


def validate_world(data):
    """Return the parsed payload of a native death-loot world envelope, or raise ValueError."""
    if not isinstance(data, bytes) or len(data) > MAX_WORLD:
        raise ValueError('Death-loot world file is missing or too large.')
    try:
        envelope = tomllib.loads(data.decode('utf-8'))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError('Death-loot world file is not valid TOML.') from exc
    _exact(envelope, {'format', 'payload', 'sha256'}, 'Death-loot world envelope')
    if type(envelope['format']) is not int or envelope['format'] != 1:
        raise ValueError('Death-loot world format is unsupported.')
    if not _text(envelope['sha256'], DIGEST) or not isinstance(envelope['payload'], str):
        raise ValueError('Death-loot world envelope is malformed.')
    try:
        payload = base64.b64decode(envelope['payload'], validate=True)
    except ValueError as exc:
        raise ValueError('Death-loot world payload is not strict base64.') from exc
    if base64.b64encode(payload).decode('ascii') != envelope['payload']:
        raise ValueError('Death-loot world payload is not canonical base64.')
    if hashlib.sha256(payload).hexdigest() != envelope['sha256']:
        raise ValueError('Death-loot world checksum does not match.')
    try:
        body = tomllib.loads(payload.decode('utf-8'))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError('Death-loot world payload is not valid TOML.') from exc
    _exact(body, {'graves', 'piles'}, 'Death-loot world payload')
    grave_ids = _graves(body['graves'])
    pile_ids = _piles(body['piles'])
    if grave_ids & pile_ids:
        raise ValueError('A grave and a pile cannot share an identifier.')
    return body


def _graves(records):
    if not isinstance(records, list) or len(records) > MAX_GRAVES:
        raise ValueError('Death-loot graves are invalid.')
    ids, latest_accounts = set(), set()
    for grave in records:
        _exact(grave, GRAVE_KEYS, 'Grave')
        if not _text(grave['id'], UUID_TEXT) or grave['id'] in ids:
            raise ValueError('Grave identifiers must be unique canonical UUIDs.')
        ids.add(grave['id'])
        if not _text(grave['account'], ACCOUNT) or not _printable(grave['name'], 1) or not _text(grave['kind'], KIND):
            raise ValueError('Grave account, name or kind is invalid.')
        if not all(type(grave[key]) is bool for key in ('male', 'blessed', 'latest')):
            raise ValueError('Grave flags must be booleans.')
        if not _int(grave['tile'], 0, TILE_MAX) or not _int(grave['direction'], 0, 8) or not _int(grave['remaining'], 1, INT_MAX):
            raise ValueError('Grave tile, direction or remaining value is out of range.')
        if grave['latest']:
            if grave['account'] in latest_accounts:
                raise ValueError('An account can have at most one latest grave.')
            latest_accounts.add(grave['account'])
    return ids


def _piles(records):
    if not isinstance(records, list) or len(records) > MAX_PILES:
        raise ValueError('Death-loot piles are invalid.')
    ids = set()
    for pile in records:
        _exact(pile, PILE_KEYS, 'Pile')
        if not _text(pile['id'], UUID_TEXT) or pile['id'] in ids:
            raise ValueError('Pile identifiers must be unique canonical UUIDs.')
        ids.add(pile['id'])
        if not (isinstance(pile['item'], str) and 1 <= len(pile['item']) <= 256 and pile['item'].isprintable()) or not _int(pile['amount'], 1, INT_MAX) or not _int(pile['charges'], 0, INT_MAX):
            raise ValueError('Pile item, amount or charges are invalid.')
        if not _int(pile['tile'], 0, TILE_MAX) or not _printable(pile['owner'], 0):
            raise ValueError('Pile tile or owner is invalid.')
        sources = pile['sources']
        if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCES :
            raise ValueError('Pile sources must be a nonempty unique account list.')
        if not all(_text(source, ACCOUNT) for source in sources) or len(set(sources)) != len(sources):
            raise ValueError('Pile sources must name canonical accounts.')
        if not _int(pile['reveal'], -1, INT_MAX) or not _int(pile['disappear'], -1, INT_MAX):
            raise ValueError('Pile reveal or disappear time is out of range.')
        if pile['owner'] and pile['reveal'] == 0:
            raise ValueError('An owned pile must be reveal -1 or later.')
        if not pile['owner'] and pile['reveal'] > 0:
            raise ValueError('A public pile cannot have a later reveal time.')
    return ids


def _storage_version(save):
    version = save.get('storage_version', 0)
    return type(version) is int and version == 1


def _batch(files, validate_save):
    """Validate a pending batch's exact members; return its (accounts, world bytes)."""
    if 'manifest.tsv' not in files:
        raise ValueError('Pending account batch has no manifest.')
    manifest = files['manifest.tsv']
    if len(manifest) > MAX_MANIFEST or not manifest.startswith(BATCH_HEADER.encode('ascii')):
        raise ValueError('Pending account batch manifest header is invalid.')
    try:
        text = manifest.decode('ascii')
    except UnicodeError as exc:
        raise ValueError('Pending account batch manifest must be ASCII.') from exc
    body = text[len(BATCH_HEADER):]
    if not body.endswith('\n'):
        raise ValueError('Pending account batch manifest must end with a newline.')
    rows = body[:-1].split('\n')
    if not 1 <= len(rows) <= MAX_MEMBERS:
        raise ValueError('Pending account batch member count is invalid.')
    members, previous, total = {}, None, 0
    for row in rows:
        match = MEMBER_ROW.fullmatch(row)
        if not match:
            raise ValueError('Pending account batch manifest row is invalid.')
        name, size, digest = match.groups()
        if previous is not None and name <= previous:
            raise ValueError('Pending account batch rows must be sorted and unique.')
        previous = name
        size = int(size)
        if not 1 <= size <= MAX_MEMBER:
            raise ValueError('Pending account batch member size is out of range.')
        total += size
        if total > MAX_BATCH:
            raise ValueError('Pending account batch is too large.')
        members[name] = (size, digest)
    if set(files) != set(members) | {'manifest.tsv'}:
        raise ValueError('Pending account batch has unlisted or missing files.')
    for name, (size, digest) in members.items():
        data = files[name]
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Pending account batch member checksum does not match.')
    accounts, world = {}, None
    for name in members:
        if name == WORLD_FILE:
            world = files[name]
        else:
            accounts[name[:-len('.toml')]] = validate_save(files[name], name[:-len('.toml')])
    if any(_storage_version(save) for save in accounts.values()) and world is None:
        raise ValueError('Pending account batch with storage version 1 accounts must include its world file.')
    return accounts, world


def validate_state(contents, validate_save):
    """Validate a state-relative file map and its logical post-replay accounts.

    contents maps paths such as 'saves/tester.toml' to bytes. validate_save(data, expected_account)
    must return the parsed native save or raise ValueError. Returns the logical accounts (journal
    members override same-named canonical files) and the parsed world payload, or None.
    """
    accounts, root_world, pending = {}, None, {}
    for path, data in contents.items():
        parts = path.split('/')
        if parts[:2] == ['saves', '.soloscape-account-save'] and len(parts) > 2:
            pending['/'.join(parts[2:])] = data
        elif path == JOURNAL:
            raise ValueError('Pending account batch must be a directory.')
        elif len(parts) == 2 and parts[0] == 'saves' and parts[1] == WORLD_FILE:
            root_world = data
        elif len(parts) == 2 and parts[0] == 'saves' and parts[1].endswith('.toml'):
            accounts[parts[1][:-len('.toml')]] = validate_save(data, None)
    world = root_world
    if pending:
        batch_accounts, batch_world = _batch(pending, validate_save)
        accounts.update(batch_accounts)
        if batch_world is not None:
            world = batch_world
    payload = validate_world(world) if world is not None else None
    if any(_storage_version(save) for save in accounts.values()) and payload is None:
        raise ValueError('Storage version 1 accounts require a validated death-loot world file.')
    return {'accounts': accounts, 'world': payload}


def validate_journal_layout(saves):
    """Reject unrepresentable pending filesystem state before collecting backup bytes."""
    pending = saves / '.soloscape-account-save'
    if pending.is_symlink():
        raise ValueError('Pending account batch cannot be a symbolic link.')
    if not pending.exists():
        return
    if not pending.is_dir():
        raise ValueError('Pending account batch must be a directory.')
    manifest = pending / 'manifest.tsv'
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('Pending account batch manifest is missing or invalid.')
    for child in pending.iterdir():
        if child.is_symlink() or not child.is_file():
            raise ValueError('Pending account batch contains an unsupported member.')
