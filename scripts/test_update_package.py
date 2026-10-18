import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import threading
import unittest
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import Mock

import managed_fixture as fx
import package_builder
import release_updates
import runtime_manifest
import update_package as up

TAG = 'r2'


def regular(name):
    info = zipfile.ZipInfo(name)
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


class PackageCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='pkg-'))
        self.addCleanup(self.cleanup)
        self.root = self.tmp / 'install'
        for name in ('versions', 'staging'):
            (self.root / name).mkdir(parents=True)

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assert_nothing_left(self):
        self.assertEqual(os.listdir(self.root / 'versions'), [])
        self.assertEqual([n for n in os.listdir(self.root / 'staging') if n != up.LOCK], [])

    def raw_zip(self, entries, manifest=None, name='raw.zip'):
        """entries: list of (ZipInfo-or-name, bytes). Builds an arbitrary archive for hostile-input tests."""
        path = self.tmp / name
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as archive:
            for entry, data in entries:
                if isinstance(entry, str):  # writestr(str) records no file-type bits; set an ordinary file
                    entry = regular(entry)
                archive.writestr(entry, data)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def package_with(self, mutate):
        files = fx.payload_files(TAG)
        manifest = json.loads(package_builder.build_manifest(files, TAG, (0, 1), 'c' * 40, fx.PINS, fx.PATCHES))
        entries = dict(files)
        mutate(manifest, entries)
        entries_list = [(runtime_manifest.MANIFEST_NAME, json.dumps(manifest).encode())]
        for name, data in entries.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            entries_list.append((info, data))
        return self.raw_zip(entries_list)


class Install(PackageCase):
    def test_hierarchical_payload_is_sealed_under_its_manifest_hash(self):
        path, digest, files = fx.make_package(self.tmp, TAG)
        steps = []
        found = up.install_zip(self.root, path, digest, expected_release=TAG, job=up.Job(progress=lambda *a: steps.append(a)))
        self.assertEqual(found['id'], fx.version_id(files, TAG))
        directory = self.root / 'versions' / found['id']
        for name, data in files.items():
            self.assertEqual((directory / name).read_bytes(), data)
        self.assertEqual(stat.S_IMODE((directory / 'scripts/launcher.sh').stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE((directory / fx.SERVER).stat().st_mode), 0o444)
        self.assertEqual(stat.S_IMODE((directory / 'upstream').stat().st_mode), 0o555)
        self.assertTrue(any(stage == 'unpacking' for stage, *_ in steps) and any(stage == 'verifying' for stage, *_ in steps))
        self.assertEqual([n for n in os.listdir(self.root / 'staging') if n != up.LOCK], [])
        again = up.install_zip(self.root, path, digest, expected_release=TAG)
        self.assertTrue(again['already_present'])

    def test_real_sized_jars_install_within_the_production_bounds(self):
        server = os.urandom(1 << 20) * 60  # 60 MiB, far above the old 4 MiB lab file bound
        path, digest, files = fx.make_package(self.tmp, TAG, server=server)
        found = up.install_zip(self.root, path, digest, expected_release=TAG)
        self.assertEqual((self.root / 'versions' / found['id'] / fx.SERVER).stat().st_size, len(server))
        self.assertGreater(path.stat().st_size, 8 << 20)

    def test_wrong_digest_or_release_label_installs_nothing(self):
        path, digest, _ = fx.make_package(self.tmp, TAG)
        with self.assertRaisesRegex(up.PackageError, 'digest'):
            up.install_zip(self.root, path, '0' * 64)
        with self.assertRaisesRegex(up.PackageError, 'not the announced'):
            up.install_zip(self.root, path, digest, expected_release='r9')
        with self.assertRaises(up.PackageError):
            up.install_zip(self.root, path, 'ABC')
        self.assert_nothing_left()

    def test_hostile_archives_are_refused_without_a_trace(self):
        def traversal(m, e):
            e['../evil'] = b'x'
            m['files']['../evil'] = {'size': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}

        def unlisted(m, e):
            e['upstream/extra.toml'] = b'x = 1\n'

        def missing(m, e):
            del e['upstream/game-server/data/test/items.toml']

        def lie_size(m, e):
            m['files'][fx.CLIENT]['size'] += 1

        def lie_digest(m, e):
            m['files'][fx.SERVER]['sha256'] = '0' * 64

        def cache_path(m, e):
            e['upstream/game-server/data/cache/main_file_cache.dat2'] = b'x'
            m['files']['upstream/game-server/data/cache/main_file_cache.dat2'] = {
                'size': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}

        def git_path(m, e):
            e['upstream/.git/config'] = b'x'
            m['files']['upstream/.git/config'] = {'size': 1, 'sha256': hashlib.sha256(b'x').hexdigest()}

        def huge(m, e):
            m['files'][fx.SERVER]['size'] = runtime_manifest.FILE_MAX_BYTES + 1

        def old_format(m, e):
            m['format'] = 1

        for mutate in (traversal, unlisted, missing, lie_size, lie_digest, cache_path, git_path, huge, old_format):
            with self.subTest(mutate=mutate.__name__):
                path, digest = self.package_with(mutate)
                with self.assertRaises(up.PackageError):
                    up.install_zip(self.root, path, digest)
                self.assert_nothing_left()

    def test_links_special_files_directories_duplicates_and_encryption_are_refused(self):
        files = fx.payload_files(TAG)
        manifest = package_builder.build_manifest(files, TAG, (0, 1), 'c' * 40, fx.PINS, fx.PATCHES)

        def info(name, mode):
            i = zipfile.ZipInfo(name)
            i.external_attr = mode << 16
            return i
        base = [(info(n, stat.S_IFREG | 0o644), d) for n, d in files.items()]
        cases = {
            'symlink': [(info(fx.SERVER, stat.S_IFLNK | 0o777), b'/etc/passwd')] + [e for e in base if e[0].filename != fx.SERVER],
            'fifo': [(info(fx.SERVER, stat.S_IFIFO | 0o644), b'')] + [e for e in base if e[0].filename != fx.SERVER],
            'directory': base + [(zipfile.ZipInfo('upstream/'), b'')],
            'duplicate': base + [base[0]],
        }
        for label, entries in cases.items():
            with self.subTest(label):
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    path, digest = self.raw_zip([(runtime_manifest.MANIFEST_NAME, manifest)] + entries)
                with self.assertRaises(up.PackageError):
                    up.install_zip(self.root, path, digest)
                self.assert_nothing_left()
        path, digest = self.raw_zip([(runtime_manifest.MANIFEST_NAME, manifest)] + base)
        data = bytearray(path.read_bytes())
        data[data.find(b'PK\x03\x04') + 6] |= 1  # encrypted flag on the first local header
        central = data.find(b'PK\x01\x02')
        data[central + 8] |= 1
        path.write_bytes(bytes(data))
        with self.assertRaises(up.PackageError):
            up.install_zip(self.root, path, hashlib.sha256(bytes(data)).hexdigest())
        self.assert_nothing_left()

    def test_a_named_pipe_or_link_as_the_archive_does_not_hang_or_install(self):
        fifo = self.tmp / 'pipe.zip'
        os.mkfifo(fifo)
        with self.assertRaises(up.PackageError):
            up.install_zip(self.root, fifo, '0' * 64)
        path, digest, _ = fx.make_package(self.tmp, TAG)
        link = self.tmp / 'link.zip'
        link.symlink_to(path)
        with self.assertRaises(OSError):
            up.install_zip(self.root, link, digest)
        self.assert_nothing_left()

    def test_a_decompression_bomb_beyond_the_declared_size_is_stopped(self):
        files = fx.payload_files(TAG)
        manifest = json.loads(package_builder.build_manifest(files, TAG, (0, 1), 'c' * 40, fx.PINS, fx.PATCHES))
        path = self.tmp / 'bomb.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(regular(runtime_manifest.MANIFEST_NAME), json.dumps(manifest))
            for name, data in files.items():
                archive.writestr(regular(name), b'\0' * (50 << 20) if name == fx.SERVER else data)
        # The manifest declares the small honest server jar; the entry inflates to 50 MiB of zeros.
        with self.assertRaisesRegex(up.PackageError, 'disagrees|more bytes'):
            up.install_zip(self.root, path, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assert_nothing_left()

    def test_cancellation_and_the_whole_job_deadline_stop_extraction(self):
        path, digest, _ = fx.make_package(self.tmp, TAG, server=os.urandom(1 << 20) * 8)
        flag = threading.Event()
        flag.set()
        with self.assertRaises(up.Cancelled):
            up.install_zip(self.root, path, digest, job=up.Job(cancelled=flag))
        now = [0.0]
        job = up.Job(deadline=5, clock=lambda: now[0], progress=lambda *a: now.__setitem__(0, now[0] + 10))
        with self.assertRaisesRegex(up.PackageError, 'too long'):
            up.install_zip(self.root, path, digest, job=job)
        self.assert_nothing_left()

    def test_a_second_staging_run_is_refused_while_the_first_holds_the_lock(self):
        path, digest, _ = fx.make_package(self.tmp, TAG)
        with up._StagingLock(self.root):
            with self.assertRaisesRegex(up.PackageError, 'already running'):
                up.install_zip(self.root, path, digest)

    def test_interrupted_leftovers_are_cleared_by_the_next_run_and_symlinked_staging_is_refused(self):
        path, digest, _ = fx.make_package(self.tmp, TAG)
        leftover = self.root / 'staging' / '.extract-old'
        leftover.mkdir()
        (leftover / 'junk').write_text('x')
        up.install_zip(self.root, path, digest)
        self.assertFalse(leftover.exists())
        shutil.rmtree(self.root / 'staging')
        (self.root / 'staging').symlink_to(self.tmp)
        with self.assertRaises(up.PackageError):
            up.install_zip(self.root, path, digest)


class Fetch(PackageCase):
    def package(self, payload=None, **override):
        path, digest, files = fx.make_package(self.tmp, TAG)
        payload = path.read_bytes() if payload is None else payload
        meta = dict(tag=TAG, name='soloscape-package-test.zip', size=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                    url=release_updates.asset_url(TAG, 'soloscape-package-test.zip'))
        meta.update(override)
        return meta, payload, files

    @staticmethod
    def transport(payload, error=None):
        def open_(url):
            return io.BytesIO(payload)
        return open_

    def test_fetch_downloads_then_installs_and_reports_progress(self):
        meta, payload, files = self.package()
        seen = []
        found = up.fetch_and_install(self.root, meta, job=up.Job(progress=lambda *a: seen.append(a)), transport=self.transport(payload))
        self.assertEqual(found['id'], fx.version_id(files, TAG))
        self.assertEqual(seen[0][0], 'downloading')
        self.assertEqual([n for n in os.listdir(self.root / 'staging') if n != up.LOCK], [])

    def test_download_failures_leave_no_candidate_or_partial_file(self):
        meta, payload, _ = self.package()
        cases = {'wrong digest': (dict(sha256='0' * 64), payload), 'truncated': ({}, payload[:-5]),
                 'oversized': ({}, payload + b'x'), 'empty': ({}, b'')}
        for label, (override, body) in cases.items():
            with self.subTest(label):
                with self.assertRaises(up.PackageError):
                    up.fetch_and_install(self.root, dict(meta, **override), transport=self.transport(body))
                self.assert_nothing_left()

        def broken(url):
            class Source:
                def read(self, n):
                    raise OSError('connection reset')
                close = Mock()
            return Source()
        with self.assertRaisesRegex(up.PackageError, 'interrupted'):
            up.fetch_and_install(self.root, meta, transport=broken)

        def http_error(url):
            raise urllib.error.HTTPError(url, 503, 'down', {}, io.BytesIO(b'x'))
        with self.assertRaisesRegex(up.PackageError, 'unavailable'):
            up.fetch_and_install(self.root, meta, transport=http_error)
        self.assert_nothing_left()

    def test_metadata_is_validated_before_any_request_or_file(self):
        meta, payload, _ = self.package()
        calls = []
        bad = [dict(url='https://evil.invalid/x.zip'), dict(size=0), dict(size=up.MAX_PACKAGE + 1), dict(name='soloscape-update-x.zip'),
               dict(tag='../x'), dict(sha256='ABC'), dict(size=True)]
        for override in bad:
            with self.subTest(override=override):
                with self.assertRaises(up.PackageError):
                    up.fetch_and_install(self.root, dict(meta, **override), transport=lambda u: calls.append(u))
        with self.assertRaises(up.PackageError):
            up.fetch_and_install(self.root, {'tag': TAG}, transport=lambda u: calls.append(u))
        self.assertEqual(calls, [])
        self.assert_nothing_left()

    def test_release_label_must_match_the_announced_tag(self):
        meta, payload, _ = self.package(tag='r3', url=release_updates.asset_url('r3', 'soloscape-package-test.zip'))
        with self.assertRaisesRegex(up.PackageError, 'not the announced'):
            up.fetch_and_install(self.root, meta, transport=self.transport(payload))
        self.assert_nothing_left()

    def test_cancel_during_a_blocked_read_and_a_trickling_server_hit_the_deadline(self):
        meta, payload, _ = self.package()
        flag = threading.Event()

        class Slow:
            def __init__(self):
                self.sent = False

            def read(self, n):
                if self.sent:
                    flag.set()  # the player cancels while the next read would block
                    return b'x'
                self.sent = True
                return payload[:10]
            close = Mock()
        with self.assertRaises(up.Cancelled):
            up.fetch_and_install(self.root, meta, job=up.Job(cancelled=flag), transport=lambda u: Slow())
        self.assert_nothing_left()
        now = [0.0]

        class Trickle:
            def read(self, n):
                now[0] += 6
                return b'x'
            close = Mock()
        with self.assertRaisesRegex(up.PackageError, 'too long'):
            up.fetch_and_install(self.root, meta, job=up.Job(deadline=30, clock=lambda: now[0]), transport=lambda u: Trickle())
        self.assert_nothing_left()

    def test_redirects_leave_the_github_object_hosts_only_over_https(self):
        handler = up._ProjectRedirects()
        request = Mock()
        for url in ('https://evil.invalid/x', 'http://objects.githubusercontent.com/x', 'file:///etc/passwd'):
            self.assertIsNone(handler.redirect_request(request, None, 302, 'Found', {}, url))


if __name__ == '__main__':
    unittest.main()
