import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

import installer as ins

COMMIT = 'a' * 40


def tar_bytes(entries, mode='w:gz'):
    """entries: (name, data|None for dir, linkname|None, type) tuples -> archive bytes."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode=mode) as tar:
        for name, data, link, kind in entries:
            info = tarfile.TarInfo(name)
            if kind == 'dir':
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            elif kind in ('sym', 'hard'):
                info.type = tarfile.SYMTYPE if kind == 'sym' else tarfile.LNKTYPE
                info.linkname = link
                tar.addfile(info)
            else:
                info.size = len(data)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class Response(io.BytesIO):
    def __init__(self, data, length=True):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data))} if length else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeNet:
    """Serves bytes by URL and records requests; unknown URLs fail like a dead connection."""

    def __init__(self, pages):
        self.pages, self.requests = dict(pages), []

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.requests.append(url)
        if url not in self.pages:
            raise OSError('no route to ' + url)
        return Response(self.pages[url])


def make_inputs(jdk21, jdk8, seven, cache_files):
    def entry(url, data, **extra):
        return dict(url=url, sha256=hashlib.sha256(data).hexdigest(), max_bytes=len(data) + 1000, publisher='test ' + url, **extra)
    return {'format': 1, 'platform': {'system': 'Linux', 'machine': 'x86_64'},
            'jdks': {'21': entry('https://example.invalid/jdk21.tar.gz', jdk21), '8': entry('https://example.invalid/jdk8.tar.gz', jdk8)},
            'sevenzip': entry('https://example.invalid/7z.tar.xz', seven, member='7zzs',
                              member_sha256=hashlib.sha256(b'#!/bin/sh\nexit 0\n').hexdigest()),
            'cache': {'archive': 'cache.7z', 'archive_sha256': '0' * 64, 'where': 'https://example.invalid/cache', 'guide': 'docs/CACHE_SETUP.md',
                      'files': {n: {'sha256': hashlib.sha256(d).hexdigest(), 'size': len(d)} for n, d in cache_files.items()}}}


CACHE = {'main_file_cache.dat2': b'dat2-synthetic', 'main_file_cache.idx255': b'idx255-synthetic', 'main_file_cache.idx0': b'idx0-synthetic'}


def fake_jdk(version):
    script = '#!/bin/sh\necho \'openjdk version "%s"\' >&2\n' % version
    return tar_bytes([('jdk-top', None, None, 'dir'), ('jdk-top/bin', None, None, 'dir'), ('jdk-top/bin/java', script.encode(), None, 'file'),
                      ('jdk-top/bin/javac', b'#!/bin/sh\nexit 0\n', None, 'file')])


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='installer-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.jdk21, self.jdk8 = fake_jdk('21.0.12'), fake_jdk('1.8.0_504')
        self.seven = tar_bytes([('7zzs', b'#!/bin/sh\nexit 0\n', None, 'file')], 'w:xz')
        self.inputs = make_inputs(self.jdk21, self.jdk8, self.seven, CACHE)
        self.net = FakeNet({'https://example.invalid/jdk21.tar.gz': self.jdk21, 'https://example.invalid/jdk8.tar.gz': self.jdk8,
                            'https://example.invalid/7z.tar.xz': self.seven})
        self.lines = []
        self.inst = ins.Installer(self.tmp / 'data', 'r1', COMMIT, inputs=self.inputs, opener=self.net, say=self.lines.append)

    def say_text(self):
        return '\n'.join(self.lines)


class Identity(Case):
    def test_identity_is_validated(self):
        self.inst.validate_identity()
        for release, commit in (('', COMMIT), ('r/1', COMMIT), ('r1', 'A' * 40), ('r1', 'a' * 39), ('r1', 'g' * 40)):
            with self.assertRaises(ins.InstallerError):
                ins.Installer(self.tmp / 'd', release, commit, inputs=self.inputs).validate_identity()

    def test_plan_names_every_source_and_the_player_supplied_cache(self):
        text = self.inst.plan()
        for needle in ('test https://example.invalid/jdk21', 'https://example.invalid/cache', 'cache.7z', COMMIT[:12], 'Supplied by you'):
            self.assertIn(needle, text)

    def test_real_inputs_are_complete_and_https_only(self):
        inputs = ins.load_inputs()
        for spec in list(inputs['jdks'].values()) + [inputs['sevenzip']]:
            self.assertTrue(spec['url'].startswith('https://'))
            self.assertRegex(spec['sha256'], '^[0-9a-f]{64}$')
        self.assertIn('main_file_cache.dat2', inputs['cache']['files'])
        self.assertIn('main_file_cache.idx255', inputs['cache']['files'])
        self.assertEqual(len(inputs['cache']['files']), 39)


class Downloads(Case):
    def test_verified_download_is_kept_and_reused(self):
        spec = self.inputs['jdks']['21']
        dest = self.tmp / 'd/jdk.tgz'
        self.inst.fetch(spec['url'], dest, spec['sha256'], spec['max_bytes'], 'JDK')
        self.assertEqual(dest.read_bytes(), self.jdk21)
        self.inst.fetch(spec['url'], dest, spec['sha256'], spec['max_bytes'], 'JDK')
        self.assertEqual(self.net.requests.count(spec['url']), 1)

    def test_wrong_hash_is_discarded(self):
        spec = self.inputs['jdks']['21']
        self.net.pages[spec['url']] = b'tampered'
        dest = self.tmp / 'd/jdk.tgz'
        with self.assertRaisesRegex(ins.InstallerError, 'pinned hash'):
            self.inst.fetch(spec['url'], dest, spec['sha256'], spec['max_bytes'], 'JDK')
        self.assertFalse(dest.exists())
        self.assertFalse(dest.with_name('jdk.tgz.part').exists())

    def test_http_oversize_and_dead_network_are_refused(self):
        with self.assertRaisesRegex(ins.InstallerError, 'not HTTPS'):
            self.inst.fetch('http://example.invalid/x', self.tmp / 'x', '0' * 64, 10, 'x')
        spec = self.inputs['jdks']['21']
        with self.assertRaisesRegex(ins.InstallerError, 'larger than expected'):
            self.inst.fetch(spec['url'], self.tmp / 'big', spec['sha256'], 10, 'JDK')
        self.assertFalse((self.tmp / 'big.part').exists())
        with self.assertRaisesRegex(ins.InstallerError, 'Could not download'):
            self.inst.fetch('https://example.invalid/none', self.tmp / 'n', '0' * 64, 10, 'n')

    def test_oversize_without_declared_length_is_stopped(self):
        self.net.pages['https://example.invalid/stream'] = b'x' * 5000
        original = self.net.__call__

        def no_length(request, timeout=None):
            response = original(request)
            response.headers = {}
            return response
        self.inst.opener = no_length
        with self.assertRaisesRegex(ins.InstallerError, 'larger than expected'):
            self.inst.fetch('https://example.invalid/stream', self.tmp / 's', '0' * 64, 100, 's')


class Unpack(Case):
    def unpack(self, entries, **kw):
        archive = self.tmp / 'a.tgz'
        archive.write_bytes(tar_bytes(entries))
        self.inst.unpack_tar(archive, self.tmp / 'out', **kw)

    def test_strips_one_level_and_keeps_executables(self):
        self.unpack([('top', None, None, 'dir'), ('top/bin', None, None, 'dir'), ('top/bin/tool', b'x', None, 'file')])
        self.assertTrue(os.access(self.tmp / 'out/bin/tool', os.X_OK))

    def test_refuses_traversal_absolute_links_and_special_entries(self):
        for entries in ([('top/../../evil', b'x', None, 'file')], [('/abs', b'x', None, 'file')],
                        [('top/l', None, '/etc/passwd', 'sym')], [('top/l', None, '../../x', 'sym')],
                        [('top/h', None, 'top/x', 'hard')]):
            with self.assertRaises(ins.InstallerError, msg=entries):
                self.unpack(entries)
            self.assertFalse((self.tmp / 'out').exists())
        self.assertFalse((self.tmp / 'evil').exists())

    def test_relative_link_inside_the_tree_is_kept(self):
        self.unpack([('top/a', b'1', None, 'file'), ('top/l', None, 'a', 'sym')])
        self.assertTrue((self.tmp / 'out/l').is_symlink())

    def test_a_chain_of_links_cannot_redirect_a_later_entry_outside(self):
        for entries in ([('top/a', None, '.', 'sym'), ('top/b', None, 'a/..', 'sym'), ('top/b/evil', b'x', None, 'file')],
                        [('top/a', None, '..', 'sym'), ('top/a/evil', b'x', None, 'file')]):
            with self.assertRaises(ins.InstallerError, msg=entries):
                self.unpack(entries)
            self.assertFalse((self.tmp / 'evil').exists())
            self.assertFalse((self.tmp / 'out').exists())

    def test_only_picks_one_member(self):
        archive = self.tmp / 'o.tar.xz'
        archive.write_bytes(self.seven)
        self.inst.unpack_tar(archive, self.tmp / 'one', strip=0, only='7zzs')
        self.assertEqual(os.listdir(self.tmp / 'one'), ['7zzs'])


class Toolchains(Case):
    def test_downloads_unpacks_and_reuses(self):
        paths = self.inst.toolchains()
        self.assertTrue(self.inst.java_ok(paths['21'], 21))
        self.assertTrue(self.inst.java_ok(paths['8'], 8))
        count = len(self.net.requests)
        self.inst.toolchains()
        self.assertEqual(len(self.net.requests), count)

    def test_wrong_java_version_is_rejected(self):
        self.net.pages['https://example.invalid/jdk21.tar.gz'] = fake_jdk('17.0.1')
        self.inputs['jdks']['21']['sha256'] = hashlib.sha256(self.net.pages['https://example.invalid/jdk21.tar.gz']).hexdigest()
        with self.assertRaisesRegex(ins.InstallerError, 'did not run'):
            self.inst.toolchains()
        self.assertFalse((self.inst.jdks / 'jdk21').exists())

    def test_a_swapped_sevenzip_program_is_replaced_not_run(self):
        tool = self.inst.sevenzip()
        tool.write_bytes(b'#!/bin/sh\necho evil\n')
        os.chmod(tool, 0o755)
        again = self.inst.sevenzip()
        self.assertEqual(again.read_bytes(), b'#!/bin/sh\nexit 0\n')
        self.assertEqual(self.net.requests.count('https://example.invalid/7z.tar.xz'), 1)  # the verified download is reused

    def test_a_7zip_archive_with_the_wrong_program_is_refused(self):
        bad = tar_bytes([('7zzs', b'#!/bin/sh\necho evil\n', None, 'file')], 'w:xz')
        self.inputs['sevenzip']['sha256'] = hashlib.sha256(bad).hexdigest()
        self.net.pages[self.inputs['sevenzip']['url']] = bad
        with self.assertRaisesRegex(ins.InstallerError, 'not the pinned one'):
            self.inst.sevenzip()
        self.assertFalse((self.inst.tools / '7zzs').exists())

    def test_sevenzip_is_fetched_once(self):
        tool = self.inst.sevenzip()
        self.assertTrue(os.access(tool, os.X_OK))
        self.inst.sevenzip()
        self.assertEqual(self.net.requests.count('https://example.invalid/7z.tar.xz'), 1)


class CacheCase(Case):
    def folder(self, name='given', **changes):
        path = self.tmp / name
        path.mkdir()
        files = dict(CACHE)
        files.update(changes)
        for key, data in files.items():
            if data is not None:
                (path / key).write_bytes(data)
        return path

    def test_good_folder_is_copied_and_verified(self):
        given = self.folder()
        self.inst.provide_cache(given)
        self.assertTrue(self.inst.cache_ready())
        self.assertTrue((given / 'main_file_cache.dat2').exists())  # the player's folder is only read

    def test_wrapping_folder_is_accepted(self):
        outer = self.tmp / 'outer'
        outer.mkdir()
        inner = self.folder('x')
        shutil.move(str(inner), str(outer / 'cache'))
        self.inst.provide_cache(outer)
        self.assertTrue(self.inst.cache_ready())

    def test_bad_folders_are_refused_with_the_download_help(self):
        for changes, word in (({'main_file_cache.idx0': b'changed'}, 'different content'), ({'main_file_cache.idx0': None}, 'missing'),
                              ({'extra.bin': b'x'}, 'unexpected file')):
            given = self.folder('g' + word.replace(' ', ''), **changes)
            with self.assertRaises(ins.InstallerError) as raised:
                self.inst.provide_cache(given)
            self.assertEqual(raised.exception.code, 3)
            self.assertIn(word, str(raised.exception))
            self.assertIn('example.invalid/cache', str(raised.exception))
        self.assertFalse(self.inst.cache.exists())
        self.assertFalse((self.inst.data / '.cache.tmp').exists())

    def test_symlink_in_the_given_folder_is_refused(self):
        given = self.folder()
        (given / 'main_file_cache.idx0').unlink()
        (given / 'main_file_cache.idx0').symlink_to(given / 'main_file_cache.dat2')
        with self.assertRaises(ins.InstallerError):
            self.inst.provide_cache(given)

    def test_nothing_given_explains_where_to_get_it(self):
        self.inst.candidates = lambda given: []
        with self.assertRaises(ins.InstallerError) as raised:
            self.inst.provide_cache(None)
        self.assertEqual(raised.exception.code, 3)
        self.assertIn('is not included and is not downloaded', str(raised.exception))

    def test_prompt_is_used_when_nothing_is_found(self):
        given = self.folder()
        self.inst.candidates = lambda given_: []
        self.inst.provide_cache(None, prompt=lambda text: str(given))
        self.assertTrue(self.inst.cache_ready())

    @unittest.skipUnless(shutil.which('7zz') or shutil.which('7z') or shutil.which('7za'), 'no 7-Zip available')
    def test_archive_is_unpacked_with_the_tool_and_verified(self):
        seven = shutil.which('7zz') or shutil.which('7z') or shutil.which('7za')
        given = self.folder()
        archive = self.tmp / 'cache.7z'
        subprocess.run([seven, 'a', '-bso0', '-bsp0', str(archive), '.'], cwd=given, check=True)
        self.inst.sevenzip = lambda: Path(seven)
        self.inputs['cache']['archive_sha256'] = ins.sha256_file(archive)
        self.inst.provide_cache(archive)
        self.assertTrue(self.inst.cache_ready())
        bad = self.folder('bad', **{'main_file_cache.idx0': b'nope'})
        archive2 = self.tmp / 'bad.7z'
        subprocess.run([seven, 'a', '-bso0', '-bsp0', str(archive2), '.'], cwd=bad, check=True)
        self.inputs['cache']['archive_sha256'] = ins.sha256_file(archive2)
        shutil.rmtree(self.inst.cache)
        with self.assertRaises(ins.InstallerError):
            self.inst.provide_cache(archive2)
        self.assertFalse(self.inst.cache.exists())

    @unittest.skipUnless(shutil.which('7z') or shutil.which('7za') or shutil.which('7zz'), 'no 7-Zip available')
    def test_an_archive_other_than_the_verified_one_is_refused_before_unpacking(self):
        seven = shutil.which('7zz') or shutil.which('7z') or shutil.which('7za')
        given = self.folder()
        archive = self.tmp / 'other.7z'
        subprocess.run([seven, 'a', '-bso0', '-bsp0', str(archive), '.'], cwd=given, check=True)
        self.inst.sevenzip = lambda: self.fail('must not be unpacked')
        with self.assertRaises(ins.InstallerError) as raised:
            self.inst.provide_cache(archive)
        self.assertEqual(raised.exception.code, 3)
        self.assertIn('not the archive', str(raised.exception))

    def test_bytes_changed_during_the_copy_are_caught(self):
        given = self.folder()
        original = shutil.copyfile

        def tamper(src, dst, *a, **k):
            out = original(src, dst, *a, **k)
            if str(dst).endswith('idx0'):
                Path(dst).write_bytes(b'swapped')
            return out
        shutil.copyfile = tamper
        self.addCleanup(setattr, shutil, 'copyfile', original)
        with self.assertRaisesRegex(ins.InstallerError, 'changed while'):
            self.inst.provide_cache(given)
        self.assertFalse(self.inst.cache.exists())

    def test_existing_verified_cache_is_not_touched(self):
        self.inst.provide_cache(self.folder())
        stamp = (self.inst.cache / 'main_file_cache.dat2').stat().st_mtime_ns
        self.inst.provide_cache(None)
        self.assertEqual((self.inst.cache / 'main_file_cache.dat2').stat().st_mtime_ns, stamp)


class Source(Case):
    def origin(self):
        repo = self.tmp / 'origin'
        repo.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        git = lambda *a: subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *a],
                                        check=True, capture_output=True, text=True, env=env).stdout.strip()
        git('init', '-q')
        (repo / 'a.txt').write_text('one\n')
        git('add', '-A')
        git('commit', '-q', '-m', 'one')
        return repo, git('rev-parse', 'HEAD'), git

    def test_fetches_exactly_the_named_commit_and_reuses_it(self):
        repo, commit, git = self.origin()
        (repo / 'a.txt').write_text('two\n')
        git('commit', '-qam', 'two')
        inst = ins.Installer(self.tmp / 'data', 'r1', commit, inputs=self.inputs, say=self.lines.append, origin=str(repo))
        inst.protocols = 'file'
        inst.fetch_source()
        self.assertEqual((inst.source / 'a.txt').read_text(), 'one\n')
        (inst.source / 'keep').mkdir()
        (inst.source / 'keep/cache').write_text('upstream clone or gradle cache\n')
        inst.fetch_source()
        self.assertIn('already at the release commit', self.say_text())

    def test_a_resumed_source_is_restored_to_exactly_the_commit(self):
        repo, commit, _ = self.origin()
        inst = ins.Installer(self.tmp / 'data', 'r1', commit, inputs=self.inputs, say=self.lines.append, origin=str(repo))
        inst.protocols = 'file'
        inst.fetch_source()
        (inst.source / 'a.txt').write_text('edited\n')
        (inst.source / 'scripts').mkdir()
        (inst.source / 'scripts/json.py').write_text('raise SystemExit("planted")\n')
        inst.fetch_source()
        self.assertEqual((inst.source / 'a.txt').read_text(), 'one\n')
        self.assertFalse((inst.source / 'scripts/json.py').exists())

    def test_a_newer_release_moves_the_source_forward_and_keeps_untracked_work(self):
        repo, first, git = self.origin()
        inst = ins.Installer(self.tmp / 'data', 'r1', first, inputs=self.inputs, say=self.lines.append, origin=str(repo))
        inst.protocols = 'file'
        inst.fetch_source()
        (inst.source / 'upstream').mkdir()
        (inst.source / 'upstream/clone').write_text('kept\n')
        (repo / 'a.txt').write_text('two\n')
        git('commit', '-qam', 'two')
        inst.commit = git('rev-parse', 'HEAD')
        inst.fetch_source()
        self.assertEqual((inst.source / 'a.txt').read_text(), 'two\n')
        self.assertEqual((inst.source / 'upstream/clone').read_text(), 'kept\n')

    def test_unknown_commit_is_refused_and_leaves_nothing(self):
        repo, _, _ = self.origin()
        inst = ins.Installer(self.tmp / 'data', 'r1', 'b' * 40, inputs=self.inputs, say=self.lines.append, origin=str(repo))
        inst.protocols = 'file'
        with self.assertRaisesRegex(ins.InstallerError, 'Could not fetch'):
            inst.fetch_source()

    def test_protocol_other_than_https_is_refused_by_default(self):
        repo, commit, _ = self.origin()
        inst = ins.Installer(self.tmp / 'data', 'r1', commit, inputs=self.inputs, say=self.lines.append, origin=str(repo))
        with self.assertRaises(ins.InstallerError):
            inst.fetch_source()

    def test_a_link_in_the_source_is_refused(self):
        repo, _, git = self.origin()
        (repo / 'link').symlink_to('a.txt')
        git('add', '-A')
        git('commit', '-qm', 'link')
        commit = git('rev-parse', 'HEAD')
        inst = ins.Installer(self.tmp / 'data', 'r1', commit, inputs=self.inputs, say=self.lines.append, origin=str(repo))
        inst.protocols = 'file'
        with self.assertRaisesRegex(ins.InstallerError, 'link or submodule'):
            inst.fetch_source()
        self.assertFalse((inst.source / 'a.txt').exists())  # nothing from the refused commit was checked out


class Environment(Case):
    def test_local_env_is_quoted_data_for_the_build(self):
        (self.inst.source).mkdir(parents=True)
        jdks = {'21': Path("/opt/jdk 21'x"), '8': Path('/opt/jdk8')}
        self.inst.write_environment(jdks)
        text = (self.inst.source / 'config/local.env').read_text()
        out = subprocess.run(['bash', '-c', 'set -e; source "$1"; printf "%s\\n%s\\n%s" "$SERVER_JAVA" "$CLIENT_JAVA" "$SOLOSCAPE_CACHE_HOME"',
                              'x', str(self.inst.source / 'config/local.env')], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.split('\n'), ["/opt/jdk 21'x/bin/java", '/opt/jdk8/bin/java', str(self.inst.cache)])
        self.assertNotIn('$(', text)

    def test_desktop_exec_is_escaped_for_the_specification(self):
        self.assertEqual(ins.desktop_quote('/a b/it\'s$x`y"z%'), '"/a b/it\'s\\$x\\`y\\"z%%"')

    def test_relative_data_path_becomes_absolute(self):
        self.assertTrue(ins.Installer('rel/dir', 'r1', COMMIT, inputs=self.inputs).data.is_absolute())

    def test_interrupted_installation_is_not_mistaken_for_a_finished_one(self):
        import managed_install
        self.assertFalse(self.inst.install_complete(managed_install))
        self.inst.install.mkdir(parents=True)
        (self.inst.install / managed_install.CONFIG).write_text('{}')  # configuration published, guard and pointer not yet
        self.assertFalse(self.inst.install_complete(managed_install))
        (self.inst.install / 'versions').mkdir()
        (self.inst.install / 'versions/x').mkdir(mode=0o500)
        self.inst.remove_tree(self.inst.install)
        self.assertFalse(self.inst.install.exists())

    def test_launcher_script_and_desktop_entry(self):
        self.inst.install.mkdir(parents=True)
        script = self.inst.launcher_script()
        self.assertTrue(os.access(script, os.X_OK))
        self.assertIn('bootstrap/managed_install.py', script.read_text())
        os.environ['XDG_DATA_HOME'] = str(self.tmp / 'xdg')
        self.addCleanup(os.environ.pop, 'XDG_DATA_HOME', None)
        entry = self.inst.shortcut(script)
        self.assertIn('Name=SoloScape', entry.read_text())
        self.assertTrue(str(entry).startswith(str(self.tmp / 'xdg')))

    def test_second_installer_is_refused_while_one_runs(self):
        import fcntl
        self.inst.preflight = lambda: None
        self.inst.data.mkdir(parents=True)
        with open(self.inst.data / '.installer.lock', 'a+') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            with self.assertRaisesRegex(ins.InstallerError, 'already running'):
                self.inst.run_all()

    def test_preflight_passes_here_and_refuses_too_little_space(self):
        self.inst.preflight()
        original = ins.MIN_FREE_BYTES
        ins.MIN_FREE_BYTES = 1 << 60
        self.addCleanup(setattr, ins, 'MIN_FREE_BYTES', original)
        with self.assertRaisesRegex(ins.InstallerError, 'free space'):
            self.inst.preflight()

    def test_unsupported_platform_and_missing_tools(self):
        self.inputs['platform'] = {'system': 'Plan9', 'machine': 'x86_64'}
        with self.assertRaisesRegex(ins.InstallerError, 'Linux x86_64'):
            self.inst.preflight()

    def test_main_needs_confirmation_without_a_terminal(self):
        import contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = ins.main(['--data', str(self.tmp / 'd'), '--release', 'r1', '--commit', COMMIT])
        self.assertEqual(code, 2)
        self.assertIn('--yes', err.getvalue())
        self.assertFalse((self.tmp / 'd').exists())

    def test_plan_changes_nothing(self):
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ins.main(['--plan', '--data', str(self.tmp / 'd'), '--release', 'r1', '--commit', COMMIT]), 0)
        self.assertFalse((self.tmp / 'd').exists())


class Zipapp(Case):
    def build(self, name='i.sh'):
        import build_installer
        return build_installer.build('r9', 'c' * 40, self.tmp / name)

    def test_single_file_installer_runs_as_a_script_and_carries_its_release(self):
        sh = self.build()
        out = subprocess.run(['sh', str(sh), '--plan', '--data', str(self.tmp / 'd')], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('release r9, commit cccccccccccc', out.stdout)
        self.assertIn('Supplied by you', out.stdout)
        with zipfile.ZipFile(sh) as archive:
            self.assertEqual(sorted(archive.namelist()), ['__main__.py', 'installer.py', 'installer_inputs.json', 'release.json'])
        self.assertFalse((self.tmp / 'd').exists())

    def test_the_header_is_valid_shell_with_every_pin_filled_in(self):
        import build_installer
        text = build_installer.header(ins.load_inputs()).decode()
        self.assertNotIn('@@', text)
        subprocess.run(['sh', '-n', '-c', text], check=True)
        tools = ins.load_inputs()['tools']
        self.assertIn(tools['micromamba']['sha256'], text)
        for package in tools['packages']:
            self.assertIn(package['sha256'] + ' ' + package['url'], text)
        self.assertEqual(len(tools['packages']), len(set(p['sha256'] for p in tools['packages'])))

    def test_real_tool_pins_are_https_conda_forge_with_hashes(self):
        tools = ins.load_inputs()['tools']
        self.assertTrue(tools['micromamba']['url'].startswith('https://github.com/mamba-org/'))
        names = {p['name'] for p in tools['packages']}
        self.assertTrue({'python', 'git', '7zip'} <= names)
        for package in tools['packages']:
            self.assertRegex(package['sha256'], '^[0-9a-f]{64}$')
            self.assertTrue(package['url'].startswith('https://conda.anaconda.org/conda-forge/'))

    def stripped_path(self):
        """A PATH like a stock SteamOS: the basic tools, curl and sha256sum, but no python3 and no git."""
        bin_dir = self.tmp / 'bin'
        bin_dir.mkdir()
        for name in ('sh', 'bash', 'uname', 'cat', 'cut', 'dirname', 'basename', 'mkdir', 'rm', 'mv', 'chmod', 'echo', 'printf', 'curl',
                     'sha256sum', 'read', 'test', 'env', 'id', 'tr', 'head', 'sleep'):
            found = shutil.which(name)
            if found:
                (bin_dir / name).symlink_to(found)
        return str(bin_dir)

    def test_a_computer_without_python_and_git_is_offered_the_tool_setup_first(self):
        sh = self.build()
        env = {'PATH': self.stripped_path(), 'HOME': str(self.tmp)}
        out = subprocess.run(['/bin/sh', str(sh), '--plan', '--data', str(self.tmp / 'd')], capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('no usable Python 3 and git', out.stdout)
        self.assertIn('conda-forge', out.stdout)
        self.assertFalse((self.tmp / 'd').exists())

    def test_that_setup_needs_confirmation_and_curl(self):
        sh = self.build()
        env = {'PATH': self.stripped_path(), 'HOME': str(self.tmp)}
        out = subprocess.run(['/bin/sh', str(sh), '--data', str(self.tmp / 'd')], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        self.assertEqual(out.returncode, 2)
        self.assertIn('--yes', out.stderr)
        self.assertFalse((self.tmp / 'd').exists())
        (self.tmp / 'bin/curl').unlink()
        out = subprocess.run(['/bin/sh', str(sh), '--plan'], capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 2)
        self.assertIn("'curl' is needed", out.stderr)

    def test_bad_identity_is_refused(self):
        import build_installer
        for release, commit in (('r1', 'x' * 40), ('', 'a' * 40), ('r/1', 'a' * 40)):
            with self.assertRaises(ValueError):
                build_installer.build(release, commit, self.tmp / 'bad.sh')

    def test_the_launcher_script_puts_the_private_python_first_when_there_is_one(self):
        self.inst.install.mkdir(parents=True)
        self.assertNotIn('PATH=', self.inst.launcher_script().read_text())
        (self.inst.tools / 'env/bin').mkdir(parents=True)
        (self.inst.tools / 'env/bin/python3').write_text('')
        text = self.inst.launcher_script().read_text()
        self.assertIn('PATH=' + str(self.inst.tools / 'env/bin') + ':"$PATH"', text)


if __name__ == '__main__':
    unittest.main()
