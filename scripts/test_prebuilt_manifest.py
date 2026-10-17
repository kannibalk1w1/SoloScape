"""Original dummy payloads for the private prebuilt manifest validator."""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

CONTRACT = Path(__file__).resolve().parents[1] / 'experiments' / 'prebuilt-runtime-contract' / 'manifest.py'
spec = importlib.util.spec_from_file_location('prebuilt_contract_manifest', CONTRACT)
manifest_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest_module)
validate = manifest_module.validate

SCRIPTS = manifest_module.RUNTIME_SCRIPTS
SERVER = 'upstream/game-server/game/build/libs/void-server-1.0.jar'
CLIENT = 'upstream/runelite-client/client/build/libs/void-client-1.0.jar'
DATA = 'upstream/game-server/data/world/settings.toml'
MANIFEST_MAX = manifest_module.MANIFEST_MAX_BYTES


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PayloadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.sentinel = self.base / 'sentinel.txt'
        self.sentinel.write_bytes(b'owner sentinel, not part of any payload\n')
        self.root = self.base / 'payload'
        self.root.mkdir()
        self.contents = {}
        for name in SCRIPTS:
            self.write(f'scripts/{name}', f'# original fixture {name}\n'.encode())
        self.write('scripts/launcher.sh', b'#!/bin/sh\n# original fixture launcher\n')
        self.write(SERVER, b'original fixture server jar bytes\n')
        self.write(CLIENT, b'original fixture client jar bytes\n')
        self.write(DATA, b'name = "fixture"\n')
        self.write('upstream/game-server/data/world/empty.txt', b'')
        self.manifest = self.make_manifest()
        self.write_manifest(self.manifest)

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.contents[rel] = data

    def make_manifest(self):
        files = {rel: {'sha256': sha(data), 'size': len(data)} for rel, data in self.contents.items()}
        return {
            'format': 1,
            'source_commit': 'a' * 40,
            'platform': 'linux-x86_64',
            'cache_revision': 634,
            'pins': {'game-server': '1' * 40, '634-client': '2' * 40, 'runelite-client': '3' * 40},
            'patches': {'patches/client/0001-fixture.patch': 'c' * 64, 'patches/server/0001-fixture.patch': 'd' * 64},
            'roles': {'server': SERVER, 'client': CLIENT, 'launcher': 'scripts/launcher.sh'},
            'files': files,
        }

    def write_manifest(self, value):
        text = value if isinstance(value, (str, bytes)) else json.dumps(value)
        data = text.encode('utf-8') if isinstance(text, str) else text
        (self.root / manifest_module.MANIFEST_NAME).write_bytes(data)

    def snapshot(self, directory):
        state = {}
        for path in sorted(directory.rglob('*')):
            mode = os.lstat(path).st_mode
            key = str(path.relative_to(directory))
            if stat.S_ISLNK(mode):
                state[key] = ('link', os.readlink(path))
            elif stat.S_ISDIR(mode):
                state[key] = ('dir',)
            elif stat.S_ISREG(mode):
                state[key] = ('file', path.read_bytes())
            else:
                state[key] = ('other', stat.S_IFMT(mode))
        return state

    def assertRefused(self, pattern, root=None):
        before = self.snapshot(self.base)
        with self.assertRaisesRegex(ValueError, pattern):
            validate(root or self.root)
        self.assertEqual(self.snapshot(self.base), before)
        self.assertEqual(self.sentinel.read_bytes(), b'owner sentinel, not part of any payload\n')

    def edited(self, edit):
        value = json.loads(json.dumps(self.manifest))
        edit(value)
        self.write_manifest(value)

    def remove_listing(self, path):
        def edit(value):
            del value['files'][path]
        self.edited(edit)


class AcceptanceTests(PayloadTests):
    def test_accepts_minimal_payload_and_writes_nothing(self):
        before = self.snapshot(self.base)
        self.assertEqual(validate(self.root), self.manifest)
        self.assertEqual(self.snapshot(self.base), before)

    def test_accepts_optional_toml_and_txt_data_and_exact_4mib_manifest(self):
        self.write('upstream/game-server/data/world/notes.txt', b'fixture notes\n')
        self.write('upstream/game-server/data/rules/base.toml', b'[rules]\n')
        self.manifest = self.make_manifest()
        text = json.dumps(self.manifest)
        self.write_manifest(text + ' ' * (MANIFEST_MAX - len(text.encode('utf-8'))))
        self.assertEqual(len((self.root / 'soloscape-runtime.json').read_bytes()), MANIFEST_MAX)
        self.assertEqual(validate(self.root), self.manifest)


class ManifestTextTests(PayloadTests):
    def test_refuses_duplicate_keys_and_non_json_text(self):
        good = json.dumps(self.manifest)
        cases = {
            'top-level duplicate': good.replace('"platform"', '"platform": "linux-x86_64", "platform"', 1),
            'nested duplicate': good.replace('"pins": {', '"pins": {"game-server": "' + '1' * 40 + '", ', 1),
            'NaN number': good.replace('634', 'NaN', 1),
            'truncated JSON': good[:-1],
            'top-level array': '[]',
            'invalid UTF-8': b'\xff\xfe{}',
            'byte order mark': '﻿' + good,
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.write_manifest(text)
                self.assertRefused(r'duplicate JSON key|non-finite|Expecting|Unexpected|UTF-8|object')

    def test_refuses_manifest_over_4mib_and_symlinked_manifest(self):
        text = json.dumps(self.manifest)
        self.write_manifest(text + ' ' * (MANIFEST_MAX + 1 - len(text.encode('utf-8'))))
        self.assertRefused('4 MiB')
        manifest_path = self.root / 'soloscape-runtime.json'
        target = self.base / 'elsewhere.json'
        target.write_bytes(manifest_path.read_bytes())
        manifest_path.unlink()
        manifest_path.symlink_to(target)
        self.assertRefused('symbolic link')


class SchemaTests(PayloadTests):
    def assertSchemaRefused(self, edit, pattern):
        self.edited(edit)
        self.assertRefused(pattern)

    def test_top_level_and_scalar_boundaries(self):
        cases = [
            ('format zero', lambda v: v.update(format=0), 'format'),
            ('format two', lambda v: v.update(format=2), 'format'),
            ('format boolean', lambda v: v.update(format=True), 'format'),
            ('format string', lambda v: v.update(format='1'), 'format'),
            ('commit uppercase', lambda v: v.update(source_commit='A' * 40), 'source_commit'),
            ('commit 39 chars', lambda v: v.update(source_commit='a' * 39), 'source_commit'),
            ('commit 41 chars', lambda v: v.update(source_commit='a' * 41), 'source_commit'),
            ('platform other', lambda v: v.update(platform='linux-aarch64'), 'platform'),
            ('cache 633', lambda v: v.update(cache_revision=633), 'cache_revision'),
            ('cache 635', lambda v: v.update(cache_revision=635), 'cache_revision'),
            ('cache boolean', lambda v: v.update(cache_revision=True), 'cache_revision'),
            ('cache float', lambda v: v.update(cache_revision=634.0), 'cache_revision'),
            ('cache string', lambda v: v.update(cache_revision='634'), 'cache_revision'),
            ('extra top field', lambda v: v.update(extra=1), 'fields must be exactly'),
            ('missing top field', lambda v: v.pop('roles'), 'fields must be exactly'),
        ]
        for label, edit, pattern in cases:
            with self.subTest(label):
                self.assertSchemaRefused(edit, pattern)
                self.setUp()

    def test_pin_boundaries(self):
        cases = {
            'missing pin': lambda p: p.pop('runelite-client'),
            'extra pin': lambda p: p.update({'extra': '4' * 40}),
            '39 hex': lambda p: p.update({'game-server': '1' * 39}),
            '41 hex': lambda p: p.update({'game-server': '1' * 41}),
            'uppercase hex': lambda p: p.update({'game-server': 'A' * 40}),
        }
        for label, edit in cases.items():
            with self.subTest(label):
                self.assertSchemaRefused(lambda v, e=edit: e(v['pins']), 'pins')
                self.setUp()

    def test_patch_boundaries(self):
        cases = {
            'empty': lambda p: p.clear(),
            'client only': lambda p: p.pop('patches/server/0001-fixture.patch'),
            'server only': lambda p: p.pop('patches/client/0001-fixture.patch'),
            'short digest': lambda p: p.update({'patches/client/0001-fixture.patch': 'c' * 63}),
            'flat legacy name': lambda p: p.update({'patches/client-0001.patch': 'c' * 64}),
            'three-digit number': lambda p: p.update({'patches/client/001-fixture.patch': 'c' * 64}),
            'uppercase name': lambda p: p.update({'patches/client/0001-Fixture.patch': 'c' * 64}),
            'leading dash name': lambda p: p.update({'patches/client/0001--fixture.patch': 'c' * 64}),
            'unknown side': lambda p: p.update({'patches/other/0001-fixture.patch': 'c' * 64}),
            'traversal key': lambda p: p.update({'patches/client/../0001-fixture.patch': 'c' * 64}),
        }
        for label, edit in cases.items():
            with self.subTest(label):
                self.assertSchemaRefused(lambda v, e=edit: e(v['patches']), 'patch|patches')
                self.setUp()

    def test_role_boundaries(self):
        cases = {
            'duplicate role paths': lambda r: r.update(client=SERVER),
            'launcher elsewhere': lambda r: r.update(launcher='scripts/other.sh'),
            'server wrong directory': lambda r: r.update(server='upstream/game-server/void-server-1.0.jar'),
            'server empty version': lambda r: r.update(server='upstream/game-server/game/build/libs/void-server-.jar'),
            'client wrong extension': lambda r: r.update(client=CLIENT[:-4] + '.zip'),
            'missing role': lambda r: r.pop('launcher'),
            'extra role': lambda r: r.update(extra='scripts/launcher.sh'),
        }
        for label, edit in cases.items():
            with self.subTest(label):
                self.assertSchemaRefused(lambda v, e=edit: e(v['roles']), 'role|roles')
                self.setUp()

    def test_file_entry_boundaries(self):
        size_cap = manifest_module.FILE_MAX_BYTES
        cases = {
            'boolean size': lambda e: e.update(size=True),
            'negative size': lambda e: e.update(size=-1),
            'float size': lambda e: e.update(size=1.0),
            'size over per-file cap': lambda e: e.update(size=size_cap + 1),
            'uppercase sha': lambda e: e.update(sha256='A' * 64),
            'extra entry field': lambda e: e.update(mode='0644'),
        }
        for label, edit in cases.items():
            with self.subTest(label):
                self.assertSchemaRefused(lambda v, e=edit: e(v['files'][SCRIPTS_PATH]),
                                         'size|sha256|fields must be exactly')
                self.setUp()

    def test_declared_size_one_byte_off_is_refused(self):
        self.edited(lambda v: v['files'][DATA].update(size=len(self.contents[DATA]) + 1))
        self.assertRefused('declared size')
        self.edited(lambda v: v['files'][DATA].update(size=len(self.contents[DATA]) - 1))
        self.assertRefused('declared size')

    def test_total_and_count_caps(self):
        cap = manifest_module.FILE_MAX_BYTES
        headroom = manifest_module.TOTAL_MAX_BYTES - sum(entry['size'] for entry in self.manifest['files'].values())

        def add_bulk(last_size):
            def edit(value):
                for index in range(3):
                    value['files'][f'upstream/game-server/data/bulk/{index}.txt'] = {'sha256': '0' * 64, 'size': cap}
                value['files']['upstream/game-server/data/bulk/3.txt'] = {'sha256': '0' * 64, 'size': last_size}
            return edit

        # Exactly 2 GiB declared passes the schema and only fails later for the missing entries.
        self.edited(add_bulk(headroom - 3 * cap + 1))
        self.assertRefused('2 GiB cap')
        self.edited(add_bulk(headroom - 3 * cap))
        self.assertRefused('missing from the payload')

        def too_many(value):
            for index in range(manifest_module.FILE_MAX_COUNT + 1):
                value['files'][f'upstream/game-server/data/bulk/{index}.txt'] = {'sha256': '0' * 64, 'size': 0}
        self.edited(too_many)
        self.assertRefused('cap is')


SCRIPTS_PATH = 'scripts/local_dev.py'


class FilesystemTests(PayloadTests):
    def test_mutated_files_are_refused(self):
        target = self.root / SCRIPTS_PATH
        original = target.read_bytes()
        target.write_bytes(original.replace(b'fixture', b'fixturX'))
        self.assertRefused('sha256 mismatch')
        target.write_bytes(original + b'extra\n')
        self.assertRefused('declared size')
        target.write_bytes(original[:-1])
        self.assertRefused('declared size')

    def test_missing_unlisted_and_unallowed_files_are_refused(self):
        (self.root / SCRIPTS_PATH).unlink()
        self.assertRefused('missing from the payload')
        self.write(SCRIPTS_PATH, self.contents.get(SCRIPTS_PATH, b'# restored\n'))
        self.write('scripts/stray.py', b'# not listed\n')
        self.assertRefused('unlisted file')
        (self.root / 'scripts/stray.py').unlink()
        self.write('upstream/game-server/data/world/notes.md', b'not allowed\n')
        self.assertRefused('unlisted file')
        self.write('scripts/smoke_profile.py', b'# real script, not part of the contract\n')
        self.edited(lambda v: v['files'].update({'scripts/smoke_profile.py': {'sha256': sha(b'# real script, not part of the contract\n'), 'size': 41}}))
        self.assertRefused('allowlist')

    def test_required_entries_and_manifest_self_listing(self):
        self.remove_listing('scripts/deck_awake.py')
        self.assertRefused('missing required')
        self.edited(lambda v: v['files'].update({'soloscape-runtime.json': {'sha256': '0' * 64, 'size': 0}}))
        self.assertRefused('allowlist')

    def test_symlink_leaf_and_intermediate_are_refused(self):
        target = self.root / SCRIPTS_PATH
        target.unlink()
        target.symlink_to(self.sentinel)
        self.assertRefused('symbolic link')
        target.unlink()
        self.write(SCRIPTS_PATH, self.contents[SCRIPTS_PATH])
        data_dir = self.root / 'upstream/game-server/data'
        moved = self.base / 'moved-data'
        data_dir.rename(moved)
        data_dir.symlink_to(moved)
        self.assertRefused('symbolic link')

    def test_symlink_in_root_path_is_refused(self):
        link = self.base / 'root-link'
        link.symlink_to(self.root)
        self.assertRefused('symbolic link', root=link)
        real = self.base / 'real'
        self.root.rename(real)
        parent_link = self.base / 'parent-link'
        parent_link.symlink_to(real)
        self.assertRefused('symbolic link', root=parent_link / 'payload')

    def test_special_file_is_refused_without_opening_it(self):
        os.mkfifo(self.root / 'scripts' / 'pipe.fifo')
        self.assertRefused('special file')

    def test_root_traversal_is_refused(self):
        self.assertRefused(r'"\.\." components', root=self.base / 'x' / '..' / 'payload')


class ForbiddenPathTests(PayloadTests):
    def test_unsafe_manifest_paths_are_refused(self):
        bad_paths = [
            '../escape.txt', 'scripts/../local_dev.py', '/abs/path.py', 'scripts//local_dev.py',
            './scripts/local_dev.py', 'scripts/', 'scripts\\local_dev.py', 'scripts/local\0dev.py',
        ]
        for path in bad_paths:
            with self.subTest(path=path):
                self.edited(lambda v, p=path: v['files'].update({p: {'sha256': '0' * 64, 'size': 0}}))
                self.assertRefused('unsafe|must be relative|must be a non-empty|not valid UTF-8')

    def test_forbidden_asset_state_and_source_paths_are_refused(self):
        forbidden = [
            '.git/config', '.gradle/cache.bin', '.runtime/owner.json', 'upstream/game-server/data/saves/world.toml',
            'upstream/game-server/data/cache/rev.txt', 'upstream/game-server/data/logs/run.txt',
            'upstream/game-server/data/exchange/offer.toml', 'upstream/game-server/data/.temp/x.toml',
            'scripts/native.c', 'upstream/game-server/native/patch.h', 'build.gradle.kts', 'settings.gradle',
            'upstream/game-server/data/world/gradle.properties',
        ]
        for path in forbidden:
            with self.subTest(path=path):
                self.edited(lambda v, p=path: v['files'].update({p: {'sha256': '0' * 64, 'size': 0}}))
                self.assertRefused('forbidden|native|Gradle')

    def test_forbidden_directories_on_disk_are_refused(self):
        for directory in ('.git', '.gradle', '.runtime'):
            with self.subTest(directory=directory):
                (self.root / directory).mkdir()
                (self.root / directory / 'state.txt').write_bytes(b'owner state\n')
                self.assertRefused('forbidden payload path')
                (self.root / directory / 'state.txt').unlink()
                (self.root / directory).rmdir()


if __name__ == '__main__':
    unittest.main()
