"""Original-fixture proof for experiments/update-staging/stage.py: dummy bytes only, no downloads or installs."""
import contextlib
import fcntl
import os
import hashlib
import importlib.util
import io
import json
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    'update_staging_stage', Path(__file__).resolve().parent.parent / 'experiments' / 'update-staging' / 'stage.py')
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)

SOURCE = 'ab' * 20
LAUNCH = 'app/launcher/launch.sh'
CLIENT = 'app/client/client.jar'
SERVER = 'app/server/server.jar'
ROLES = {'launcher': LAUNCH, 'client': CLIENT, 'server': SERVER}
ORIGINAL = {
    LAUNCH: b'#!/bin/sh\necho original launcher\n',
    CLIENT: b'ORIGINAL-CLIENT-DUMMY-BYTES\n',
    SERVER: b'ORIGINAL-SERVER-DUMMY-BYTES\n',
}
REG = 0o100000
DEFLATED = zipfile.ZIP_DEFLATED


def manifest_doc(files=ORIGINAL):
    entries = {path: {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
                      'mode': '0755' if path == LAUNCH else '0644'} for path, data in files.items()}
    return {'format': 1, 'repository': 'kannibalk1w1/SoloScape', 'source_commit40': SOURCE,
            'platform': 'linux-x86_64', 'cache_revision': 634, 'roles': dict(ROLES), 'files': entries}


def dump(doc):
    return json.dumps(doc, sort_keys=True).encode()


def make_zip(path, members):
    """members: (name, bytes, unix_mode_with_type, compress_type) in archive order."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)  # duplicate-name fixtures are deliberate
        with zipfile.ZipFile(path, 'w') as zf:
            for name, data, mode, compress in members:
                info = zipfile.ZipInfo(name, (2026, 10, 17, 0, 0, 0))
                info.external_attr = mode << 16
                info.compress_type = compress
                zf.writestr(info, data)
    return path


def nul_bundle(path, listed='app/x/a.txt', note=b'listed-note\n'):
    """A real ZIP whose entry is named 'app/x/a.txt.zz', byte-patched in place (same length) to 'app/x/a.txt' + NULs.

    ZipInfo would silently truncate the patched name at the first NUL to the listed path, so only the
    orig_filename check can see it. Both the local header and the central directory are patched.
    """
    files = {**ORIGINAL, listed: note}
    doc = manifest_doc(files)
    make_zip(path, [('manifest.json', dump(doc), REG | 0o644, DEFLATED)]
             + [(name, data, REG | 0o644, DEFLATED) for name, data in ORIGINAL.items()]
             + [(listed + '.zz', note, REG | 0o644, DEFLATED)])
    raw = path.read_bytes()
    original_name, patched = (listed + '.zz').encode(), listed.encode() + b'\0\0\0'
    assert len(original_name) == len(patched) and raw.count(original_name) == 2
    path.write_bytes(raw.replace(original_name, patched))
    return path


def bundle(path, doc=None, raw_manifest=None, files=ORIGINAL, modes=None, extra=(), skip=()):
    manifest = raw_manifest if raw_manifest is not None else dump(doc if doc is not None else manifest_doc(files))
    members = [('manifest.json', manifest, REG | 0o644, DEFLATED)]
    members += [(name, data, (modes or {}).get(name, REG | 0o644), DEFLATED)
                for name, data in files.items() if name not in skip]
    return make_zip(path, members + list(extra))


class StageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.lab = self.root / 'lab'
        self.lab.mkdir()
        (self.lab / stage.LOCK_NAME).touch()
        (self.lab / 'sentinel.txt').write_bytes(b'unrelated sentinel')
        self.bundle_path = self.root / 'bundle.zip'

    def sha_of(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def listing(self):
        return sorted(p.name for p in self.lab.iterdir())

    def refuse(self, message='', bundle_path=None, sha=None):
        target = bundle_path or self.bundle_path
        expected = sha or self.sha_of(target)
        before = (self.listing(), (self.lab / 'sentinel.txt').read_bytes(), target.read_bytes())
        with self.assertRaisesRegex(stage.StageError, message):
            stage.stage(target, expected, self.lab)
        self.assertEqual((self.listing(), (self.lab / 'sentinel.txt').read_bytes(), target.read_bytes()), before)

    def test_original_bundle_stages_exact_bytes_modes_and_report(self):
        # Archive setuid and executable bits must not leak into the staged files.
        bundle(self.bundle_path, modes={LAUNCH: REG | 0o4755, CLIENT: REG | 0o755})
        digest = self.sha_of(self.bundle_path)
        report = stage.stage(self.bundle_path, digest, self.lab)
        candidate = self.lab / digest
        self.assertEqual(report['candidate'], str(candidate))
        for path, data in ORIGINAL.items():
            self.assertEqual((candidate / path).read_bytes(), data)
        self.assertEqual(stat.S_IMODE((candidate / LAUNCH).stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((candidate / CLIENT).stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE((candidate / SERVER).stat().st_mode), 0o644)
        written = json.loads((candidate / 'report.json').read_text())
        self.assertEqual(written['result'], 'staged')
        self.assertEqual(written['archive_sha256'], digest)
        self.assertEqual(written['manifest_sha256'], hashlib.sha256((candidate / 'manifest.json').read_bytes()).hexdigest())
        self.assertEqual(written['declared']['source_commit40'], SOURCE)
        self.assertEqual(written['declared']['cache_revision'], 634)
        self.assertFalse(written['declared']['cache_revision_detected'])
        self.assertEqual(written['roles'], ROLES)
        self.assertEqual(written['files'][LAUNCH]['sha256'], hashlib.sha256(ORIGINAL[LAUNCH]).hexdigest())
        self.assertEqual(written['files'][LAUNCH]['mode'], '0755')
        self.assertNotIn('original launcher', (candidate / 'report.json').read_text())
        self.assertEqual(self.listing(), sorted([stage.LOCK_NAME, 'sentinel.txt', digest]))

    def test_wrong_or_malformed_archive_digest_refuses_before_staging(self):
        bundle(self.bundle_path)
        self.refuse('does not match the expected digest', sha='0' * 64)
        for bad in ['A' * 64, 'a' * 63, 'g' * 64]:
            with self.subTest(bad=bad):
                self.refuse('64 lowercase hex', sha=bad)

    def test_bundle_changed_while_being_read_is_refused(self):
        bundle(self.bundle_path)
        digest = self.sha_of(self.bundle_path)
        real_read, grown = stage.os.read, []

        def grow_once(fd, n):
            chunk = real_read(fd, n)
            if not grown:
                grown.append(True)
                with open(self.bundle_path, 'ab') as handle:
                    handle.write(b'tail')
            return chunk

        with mock.patch.object(stage.os, 'read', side_effect=grow_once):
            with self.assertRaisesRegex(stage.StageError, 'changed while'):
                stage.stage(self.bundle_path, digest, self.lab)
        self.assertEqual(self.listing(), sorted([stage.LOCK_NAME, 'sentinel.txt']))

    def test_mismatched_file_hash_and_size_are_refused_and_leave_nothing(self):
        # Same length as the original, different bytes: the streamed SHA-256 check must catch it.
        tampered = {**ORIGINAL, LAUNCH: b'#!/bin/sh\necho tampered launcher\n'}
        bundle(self.bundle_path, doc=manifest_doc(tampered))
        self.refuse('sha256 for app/launcher/launch.sh does not match')
        doc = manifest_doc()
        doc['files'][CLIENT]['size'] += 1
        bundle(self.bundle_path, doc=doc)
        self.refuse('disagrees with the manifest')

    def test_unsafe_and_private_payload_paths_are_refused(self):
        bad_paths = ['app/../escape.txt', 'app/./x', '/app/x', 'app//x', 'app/a\\b', 'app/a:b', 'app/x\x00y',
                     'app/.hidden', 'other/x', 'app/.runtime/state', 'app/profiles/p.json',
                     'app/caches/cache/c', 'app/saves/s.dat', 'app/backups/b', 'app/credentials/c',
                     'app/config/local.env', 'app/.git/HEAD']
        for bad in bad_paths:
            with self.subTest(path=bad):
                files = {**ORIGINAL, bad: b'x'}
                bundle(self.bundle_path, doc=manifest_doc(files), files=files)
                self.refuse('unsafe payload path|mutable or private path')

    def test_duplicate_zip_entry_names_are_refused(self):
        bundle(self.bundle_path, extra=[(LAUNCH, ORIGINAL[LAUNCH], REG | 0o755, DEFLATED)])
        self.refuse('duplicate entry name')

    def test_duplicate_json_keys_are_refused(self):
        raw = dump(manifest_doc()).replace(b'{', b'{"format": 1, ', 1)
        bundle(self.bundle_path, raw_manifest=raw)
        self.refuse('duplicate JSON key')

    def test_symlink_and_special_entries_are_refused(self):
        cases = {'symlink': ('app/launcher/alias', b'launch.sh', 0o120777),
                 'fifo': ('app/launcher/pipe', b'', 0o010644)}
        for label, (name, data, mode) in cases.items():
            with self.subTest(label):
                bundle(self.bundle_path, extra=[(name, data, mode, DEFLATED)])
                self.refuse('not a regular file')

    def test_encrypted_header_and_unsupported_compression_are_refused(self):
        for field, value, message in [('flags', 1, 'encrypted ZIP entry'),
                                       ('compression', 99, 'unsupported compression')]:
            with self.subTest(field=field):
                bundle(self.bundle_path)
                raw = bytearray(self.bundle_path.read_bytes())
                local = raw.index(b'PK\x03\x04')
                central = raw.index(b'PK\x01\x02')
                offsets = (6, 8) if field == 'flags' else (8, 10)
                struct.pack_into('<H', raw, local + offsets[0], value)
                struct.pack_into('<H', raw, central + offsets[1], value)
                self.bundle_path.write_bytes(raw)
                self.refuse(message)

    def test_corrupt_deflate_after_earlier_files_are_written_discards_only_partial_candidate(self):
        bundle(self.bundle_path)
        with zipfile.ZipFile(self.bundle_path) as zf:
            info = zf.getinfo(SERVER)  # Last sorted payload, after the client and launcher.
        raw = bytearray(self.bundle_path.read_bytes())
        name_size, extra_size = struct.unpack_from('<HH', raw, info.header_offset + 26)
        start = info.header_offset + 30 + name_size + extra_size
        raw[start] = 7  # Final DEFLATE block with reserved block type3.
        self.bundle_path.write_bytes(raw)
        self.refuse('not a readable ZIP')

    def test_unlisted_and_missing_zip_members_are_refused(self):
        bundle(self.bundle_path, extra=[('app/extra/unlisted.txt', b'x', REG | 0o644, DEFLATED)])
        self.refuse('exactly manifest.json plus the listed files')
        bundle(self.bundle_path, skip=(SERVER,))
        self.refuse('exactly manifest.json plus the listed files')

    def test_oversized_manifest_is_refused(self):
        bundle(self.bundle_path, raw_manifest=dump(manifest_doc()) + b' ' * stage.MAX_MANIFEST)
        self.refuse('exceeds 64 KiB')

    def test_oversized_file_and_total_output_are_refused(self):
        bundle(self.bundle_path, files={**ORIGINAL, 'app/data/huge.bin': b'\0' * ((4 << 20) + 1)})
        self.refuse('size for app/data/huge.bin must be')
        parts = {f'app/data/part{i}.bin': b'\0' * (4 << 20) for i in range(5)}
        bundle(self.bundle_path, files={**ORIGINAL, **parts})
        self.refuse('declared output exceeds 16 MiB')

    def test_too_many_files_and_oversized_archive_are_refused(self):
        many = {**ORIGINAL, **{f'app/many/f{i:03d}.txt': b'x' for i in range(98)}}
        bundle(self.bundle_path, files=many)
        self.refuse('entries')
        self.bundle_path.write_bytes(b'\0' * ((8 << 20) + 1))
        self.refuse('regular file of at most 8 MiB')

    def test_invalid_manifest_schema_values_are_refused(self):
        edits = {
            'format true': lambda d: d.update(format=True),
            'format 2': lambda d: d.update(format=2),
            'repository': lambda d: d.update(repository='someone/else'),
            'platform': lambda d: d.update(platform='windows-x86_64'),
            'commit uppercase': lambda d: d.update(source_commit40=SOURCE.upper()),
            'commit short': lambda d: d.update(source_commit40='ab' * 19),
            'cache bool': lambda d: d.update(cache_revision=True),
            'cache other': lambda d: d.update(cache_revision=633),
            'extra top key': lambda d: d.update(detected=True),
            'missing top key': lambda d: d.pop('platform'),
            'roles missing': lambda d: d['roles'].pop('server'),
            'roles extra': lambda d: d['roles'].update(updater=LAUNCH),
            'roles duplicate file': lambda d: d['roles'].update(client=LAUNCH),
            'roles unlisted': lambda d: d['roles'].update(server='app/server/missing.jar'),
            'roles non-string': lambda d: d['roles'].update(server=['x']),
            'mode 0777': lambda d: d['files'][LAUNCH].update(mode='0777'),
            'mode integer': lambda d: d['files'][LAUNCH].update(mode=493),
            'size bool': lambda d: d['files'][CLIENT].update(size=True),
            'size negative': lambda d: d['files'][CLIENT].update(size=-1),
            'sha uppercase': lambda d: d['files'][CLIENT].update(sha256=d['files'][CLIENT]['sha256'].upper()),
            'file extra key': lambda d: d['files'][CLIENT].update(owner='root'),
        }
        for label, edit in edits.items():
            with self.subTest(label):
                doc = manifest_doc()
                edit(doc)
                bundle(self.bundle_path, doc=doc)
                self.refuse()

    def test_existing_candidate_is_refused_and_untouched(self):
        bundle(self.bundle_path)
        digest = self.sha_of(self.bundle_path)
        candidate = self.lab / digest
        candidate.mkdir()
        (candidate / 'keep.txt').write_bytes(b'prior')
        self.refuse('candidate already exists', sha=digest)
        self.assertEqual((candidate / 'keep.txt').read_bytes(), b'prior')

    def test_linked_lab_root_is_refused(self):
        bundle(self.bundle_path)
        link = self.root / 'linked-lab'
        link.symlink_to(self.lab, target_is_directory=True)
        with self.assertRaisesRegex(stage.StageError, 'symlink'):
            stage.stage(self.bundle_path, self.sha_of(self.bundle_path), link)
        self.assertEqual(self.listing(), sorted([stage.LOCK_NAME, 'sentinel.txt']))

    def test_concurrent_cooperating_run_is_refused(self):
        bundle(self.bundle_path)
        with open(self.lab / stage.LOCK_NAME, 'rb') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            self.refuse('locked by another staging run')

    def test_cli_lab_is_confined_to_runtime_update_lab(self):
        repo = self.root / 'repo'
        repo.mkdir()
        bundle(self.bundle_path)
        digest = self.sha_of(self.bundle_path)
        (repo / '.runtime').mkdir()
        (repo / '.runtime' / 'update-lab').symlink_to(self.lab, target_is_directory=True)
        with mock.patch.object(stage, 'ROOT', repo), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(stage.main([str(self.bundle_path), digest]), 1)
        self.assertIn('must not be symlinks', err.getvalue())
        self.assertEqual(self.listing(), sorted([stage.LOCK_NAME, 'sentinel.txt']))

    def test_cli_stages_under_runtime_lab_and_refuses_bad_digest(self):
        repo = self.root / 'repo'
        repo.mkdir()
        bundle(self.bundle_path)
        digest = self.sha_of(self.bundle_path)
        with mock.patch.object(stage, 'ROOT', repo):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(stage.main([str(self.bundle_path), digest]), 0)
            self.assertTrue((repo / '.runtime' / 'update-lab' / digest / CLIENT).is_file())
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(stage.main([str(self.bundle_path), '0' * 64]), 1)
        self.assertIn('stage refused', err.getvalue())

    def test_nul_embedded_zip_name_is_refused_before_mapping(self):
        nul_bundle(self.bundle_path)
        with zipfile.ZipFile(self.bundle_path) as zf:  # what ZipInfo.filename alone would show
            self.assertEqual([i.filename for i in zf.infolist()].count('app/x/a.txt'), 1)
            self.assertIn('\0', [i.orig_filename for i in zf.infolist()][-1])
        self.refuse('altered or contains NUL')

    def copied_code_root(self):
        code = self.root / 'code'
        (code / 'experiments' / 'update-staging').mkdir(parents=True)
        shutil.copy(SPEC.origin, code / 'experiments' / 'update-staging' / 'stage.py')
        return code

    def run_cli(self, code, *args):
        script = code / 'experiments' / 'update-staging' / 'stage.py'
        return subprocess.run([sys.executable, '-I', str(script), *args], capture_output=True, text=True,
                              cwd=self.root, timeout=60)

    def tree(self):
        return sorted(os.path.join(dp, name) for dp, dns, fns in os.walk(self.root) for name in dns + fns)

    def test_subprocess_cli_rejects_root_flag_and_creates_nothing(self):
        code = self.copied_code_root()
        other = self.root / 'other-install'
        other.mkdir()
        bundle(self.bundle_path)
        before = self.tree()
        result = self.run_cli(code, '--root', str(other), str(self.bundle_path), self.sha_of(self.bundle_path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unrecognized arguments: --root', result.stderr)
        self.assertEqual(self.tree(), before)  # nothing created anywhere, including outside the copied code root
        self.assertFalse((code / '.runtime').exists())

    def test_subprocess_cli_refused_bundle_exits_nonzero_without_candidate(self):
        code = self.copied_code_root()
        bundle(self.bundle_path)
        result = self.run_cli(code, str(self.bundle_path), '0' * 64)
        self.assertEqual(result.returncode, 1)
        self.assertIn('stage refused', result.stderr)
        self.assertEqual(list((code / '.runtime' / 'update-lab').iterdir()), [])

    def test_subprocess_cli_stages_only_under_copied_code_root(self):
        code = self.copied_code_root()
        bundle(self.bundle_path)
        digest = self.sha_of(self.bundle_path)
        result = self.run_cli(code, str(self.bundle_path), digest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['archive_sha256'], digest)
        self.assertTrue((code / '.runtime' / 'update-lab' / digest / CLIENT).is_file())


if __name__ == '__main__':
    unittest.main()
