#!/usr/bin/env python3
"""One-command SoloScape installer (Linux x86_64, Python 3 standard library only).

It downloads nothing from SoloScape except the fixed project source. Every other input is fetched by the player's own computer from the publisher named in installer_inputs.json: the JDKs,
7-Zip and the upstream sources are checked against hashes and commit ids pinned there; Gradle dependencies are not hash-pinned. The game cache is the one input the player supplies: the installer
finds it, or explains where it is published, then verifies every file against a pinned list before using it.

    sh soloscape-installer.sh --release r1 --commit <40 hex>   # shows the plan, asks, installs
    python3 installer.py --plan                                # shows the plan only
    python3 installer.py --cache ~/Downloads/2026-08-02-void-634-cache.7z --yes

Every stage can be repeated: verified downloads, the source folder, a finished build and an existing install are
reused, so an interrupted run resumes where it stopped. The game is installed into the managed layout, so the
launcher's Update dialog keeps it up to date from then on.
"""
import argparse
import copy
import fcntl
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent  # the folder, or the .pyz file when run as a zipapp
PROJECT_ORIGIN = 'https://github.com/kannibalk1w1/SoloScape.git'
MIN_FREE_BYTES = 8 << 30
BUILD_DEADLINE = 90 * 60
MAX_UNPACKED = 2 << 30
NET_TIMEOUT = 60
GIT_TIMEOUT = 15 * 60
EXTRACT_TIMEOUT = 15 * 60
CACHE_FILES = ('main_file_cache.dat2', 'main_file_cache.idx255')
STORAGE_VERSIONS = (0, 1)
HEX40 = set('0123456789abcdef')


class InstallerError(Exception):
    """A refusal or failure with a plain message. `code` 3 means the player must supply the game cache."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def resource(name):
    """A file shipped beside the installer, which may be running from a zipapp (a single .pyz file)."""
    if HERE.is_file():
        import zipfile
        with zipfile.ZipFile(HERE) as archive:
            return archive.read(name).decode()
    path = HERE / name
    return path.read_text() if path.is_file() else None


def load_inputs(path=None):
    return json.loads(Path(path).read_text() if path else resource('installer_inputs.json'))


class _HttpsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise InstallerError('A download redirected to a non-HTTPS address and was refused.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def default_opener():
    return urllib.request.build_opener(_HttpsOnly()).open  # called as opener(request, timeout=...)


class Installer:
    def __init__(self, data, release, commit, inputs=None, opener=None, say=print, origin=PROJECT_ORIGIN, run=subprocess.run):
        self.data = Path(data).expanduser().absolute()
        self.release, self.commit = release, commit
        self.inputs = inputs or load_inputs()
        self.opener = opener or default_opener()
        self.say = say
        self.origin = origin
        self.protocols = 'https'
        self.run = run
        self.downloads = self.data / 'downloads'
        self.source = self.data / 'source'
        self.cache = self.data / 'cache'
        self.jdks = self.data / 'jdks'
        self.tools = self.data / 'tools'
        self.install = self.data / 'install'
        self.profiles = self.data / 'profiles'
        self.launcher = self.data / 'launcher'
        self.logs = self.data / 'logs'

    # ---- checks -------------------------------------------------------------------------------------------------

    def validate_identity(self):
        if not (isinstance(self.release, str) and self.release and len(self.release) <= 64 and self.release.isprintable()
                and '/' not in self.release):
            raise InstallerError('The release name is missing or invalid.')
        if not (isinstance(self.commit, str) and len(self.commit) == 40 and set(self.commit) <= HEX40):
            raise InstallerError('The release commit must be 40 lowercase hex characters.')

    def preflight(self):
        platform_ = self.inputs['platform']
        import platform
        if platform.system() != platform_['system'] or platform.machine() != platform_['machine']:
            raise InstallerError('This installer supports Linux x86_64 (including Steam Deck) only.')
        missing = [tool for tool in ('git', 'bash', 'flock') if shutil.which(tool) is None]
        if missing:
            raise InstallerError('These programs are needed and were not found: ' + ', '.join(missing)
                                 + '. Run the installer with `sh soloscape-installer.sh`, which sets up Python and git itself when the computer has none.')
        probe = self.data
        while not probe.exists():
            probe = probe.parent
        free = shutil.disk_usage(probe).free
        if free < MIN_FREE_BYTES:
            raise InstallerError('At least %d GB of free space is needed in %s; %.1f GB is free.'
                                 % (MIN_FREE_BYTES >> 30, probe, free / 2**30))

    def plan(self):
        lines = ['SoloScape installer plan (release %s, commit %s)' % (self.release, self.commit[:12]),
                 'Everything is installed under ' + str(self.data) + ' and nothing else on this computer is changed.', '',
                 'Downloaded to this computer from the original publishers, each checked against a pinned hash:']
        for key in ('21', '8'):
            lines.append('  - ' + self.inputs['jdks'][key]['publisher'])
        lines.append('  - ' + self.inputs['sevenzip']['publisher'] + ' (only to unpack the game cache archive)')
        lines += ['  - the SoloScape source at the release commit, from ' + self.origin,
                  '  - the three upstream game projects at their pinned commits, from github.com/2011Scape',
                  '  - the build dependencies (Maven Central, Gradle, repo.runelite.net), several hundred MB',
                  '', 'Supplied by you (not downloaded by this installer):',
                  '  - the game cache %s (%.0f MB unpacked). Published by the 2011Scape/Void maintainers at:' % (
                      self.inputs['cache']['archive'], sum(f['size'] for f in self.inputs['cache']['files'].values()) / 1e6),
                  '    ' + self.inputs['cache']['where'],
                  '    Download it yourself, then give this installer the .7z file (or the unpacked folder) with --cache.',
                  '', 'Then the installer builds the game on this computer (about 10 to 40 minutes the first time),',
                  'installs it into the managed layout, and the launcher updates it from then on.']
        return '\n'.join(lines)

    # ---- downloads ----------------------------------------------------------------------------------------------

    def fetch(self, url, destination, sha256, max_bytes, label):
        """Download over HTTPS to `destination` and keep it only if its SHA-256 matches. A verified file is reused."""
        destination = Path(destination)
        if destination.is_file() and sha256_file(destination) == sha256:
            return destination
        if urllib.parse.urlsplit(url).scheme != 'https':
            raise InstallerError('Refusing a download that is not HTTPS: ' + url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_name(destination.name + '.part')
        digest = hashlib.sha256()
        size = 0
        self.say('Downloading ' + label + ' ...')
        try:
            with self.opener(urllib.request.Request(url, headers={'User-Agent': 'soloscape-installer'}), timeout=NET_TIMEOUT) as response, open(part, 'wb') as out:
                total = int(response.headers.get('Content-Length') or 0)
                if total > max_bytes:
                    raise InstallerError(label + ' is larger than expected; it was not downloaded.')
                step = 0
                while True:
                    block = response.read(1 << 20)
                    if not block:
                        break
                    size += len(block)
                    if size > max_bytes:
                        raise InstallerError(label + ' is larger than expected; the download was stopped.')
                    digest.update(block)
                    out.write(block)
                    if total and size * 10 // total > step:
                        step = size * 10 // total
                        self.say('  %s: %d%%' % (label, step * 10))
        except InstallerError:
            part.unlink(missing_ok=True)
            raise
        except OSError as exc:
            part.unlink(missing_ok=True)
            raise InstallerError('Could not download %s (%s). Check the connection and run the installer again; finished '
                                 'downloads are kept.' % (label, exc)) from exc
        if digest.hexdigest() != sha256:
            part.unlink(missing_ok=True)
            raise InstallerError(label + ' did not match its pinned hash and was discarded. Nothing was installed from it.')
        os.replace(part, destination)
        return destination

    def unpack_tar(self, archive, destination, strip=1, only=None):
        """Unpack a verified tar archive into a new `destination`: files, folders and links that stay inside it only."""
        destination = Path(destination)
        staging = destination.with_name('.' + destination.name + '.tmp')
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        total = 0

        root = os.path.realpath(staging)

        def inside(path):
            real = os.path.realpath(path)
            return real == root or real.startswith(root + os.sep)

        def members(tar):
            nonlocal total
            for member in tar:
                parts = [p for p in member.name.split('/') if p not in ('', '.')]
                if '..' in parts or member.name.startswith('/'):
                    raise InstallerError('An archive entry points outside its folder; nothing was unpacked.')
                parts = parts[strip:]
                if not parts:
                    continue
                if only is not None and parts != [only]:
                    continue
                if not (member.isreg() or member.isdir() or member.issym()):
                    raise InstallerError('An archive holds a special file or hard link; nothing was unpacked.')
                target = os.path.join(staging, *parts)
                if not inside(os.path.dirname(target)):  # an earlier link in the archive would redirect this entry
                    raise InstallerError('An archive entry would be written outside its folder; nothing was unpacked.')
                if member.issym() and (os.path.isabs(member.linkname) or not inside(os.path.join(os.path.dirname(target), member.linkname))):
                    raise InstallerError('An archive link points outside its folder; nothing was unpacked.')
                total += member.size
                if total > MAX_UNPACKED:
                    raise InstallerError('An archive unpacks to more than expected; nothing was unpacked.')
                clone = copy.copy(member)
                clone.name = '/'.join(parts)
                clone.mode = member.mode & 0o755 | 0o200
                yield clone
        try:
            with tarfile.open(archive) as tar:
                for member in members(tar):
                    tar.extract(member, staging) if sys.version_info < (3, 12) else tar.extract(member, staging, filter='data')
            for base, dirs, files in os.walk(staging):
                for name in dirs + files:
                    if os.path.islink(os.path.join(base, name)) and not inside(os.path.join(base, name)):
                        raise InstallerError('An archive link points outside its folder; nothing was unpacked.')
            if destination.exists():
                shutil.rmtree(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.rename(staging, destination)
        except (tarfile.TarError, EOFError, OSError) as exc:
            raise InstallerError('Could not unpack ' + Path(archive).name + ': ' + str(exc)) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    # ---- toolchains ---------------------------------------------------------------------------------------------

    def java_ok(self, home, major):
        java = Path(home) / 'bin/java'
        if not (java.is_file() and (Path(home) / 'bin/javac').is_file()):
            return False
        result = self.run([str(java), '-version'], capture_output=True, text=True, timeout=60)
        text = result.stderr + result.stdout
        return result.returncode == 0 and ('version "%d' % major in text or ('version "1.%d' % major in text))

    def toolchains(self):
        paths = {}
        for key in ('21', '8'):
            spec = self.inputs['jdks'][key]
            home = self.jdks / ('jdk' + key)
            if not self.java_ok(home, int(key)):
                archive = self.fetch(spec['url'], self.downloads / Path(urllib.parse.urlsplit(spec['url']).path).name,
                                     spec['sha256'], spec['max_bytes'], 'JDK ' + key)
                self.say('Unpacking JDK ' + key + ' ...')
                self.unpack_tar(archive, home)
                if not self.java_ok(home, int(key)):
                    shutil.rmtree(home, ignore_errors=True)
                    raise InstallerError('JDK %s did not run after unpacking. Nothing was installed from it.' % key)
            paths[key] = home
        return paths

    def sevenzip(self):
        spec = self.inputs['sevenzip']
        tool = self.tools / spec['member']
        if tool.is_file() and not tool.is_symlink() and os.access(tool, os.X_OK) and sha256_file(tool) == spec['member_sha256']:
            return tool
        archive = self.fetch(spec['url'], self.downloads / Path(urllib.parse.urlsplit(spec['url']).path).name,
                             spec['sha256'], spec['max_bytes'], '7-Zip')
        staging = self.tools / '.unpack'
        self.unpack_tar(archive, staging, strip=0, only=spec['member'])
        self.tools.mkdir(parents=True, exist_ok=True)
        if sha256_file(staging / spec['member']) != spec['member_sha256']:
            shutil.rmtree(staging, ignore_errors=True)
            raise InstallerError('The 7-Zip program inside its archive is not the pinned one. Nothing was installed from it.')
        os.chmod(staging / spec['member'], 0o755)
        if tool.is_symlink():
            tool.unlink()
        os.replace(staging / spec['member'], tool)
        shutil.rmtree(staging, ignore_errors=True)
        return tool

    # ---- the game cache -----------------------------------------------------------------------------------------

    def _verify_cache(self, folder):
        """Return a list of problems with `folder` against the pinned per-file list; empty means it is the cache."""
        expected = self.inputs['cache']['files']
        problems = []
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return ['the folder cannot be read']
        for name in names:
            path = Path(folder) / name
            if path.is_symlink() or not path.is_file():
                problems.append('unexpected entry ' + name)
            elif name not in expected:
                problems.append('unexpected file ' + name)
        for name, spec in sorted(expected.items()):
            path = Path(folder) / name
            if path.is_symlink() or not path.is_file():
                problems.append('missing ' + name)
            elif path.stat().st_size != spec['size'] or sha256_file(path) != spec['sha256']:
                problems.append('different content in ' + name)
        return problems

    def cache_ready(self):
        return self.cache.is_dir() and not self._verify_cache(self.cache)

    def _cache_root(self, folder):
        """The folder holding the cache files: `folder` itself or its single wrapping subfolder."""
        folder = Path(folder)
        if (folder / CACHE_FILES[0]).exists():
            return folder
        children = [c for c in folder.iterdir() if c.is_dir() and not c.is_symlink()] if folder.is_dir() else []
        if len(children) == 1 and (children[0] / CACHE_FILES[0]).exists():
            return children[0]
        return folder

    def candidates(self, given):
        found = []
        if given:
            found.append(Path(given).expanduser())
        else:
            home = Path.home()
            for place in (home / 'Downloads', home / 'Desktop', Path.cwd()):
                found.append(place / self.inputs['cache']['archive'])
        return [c for c in found if c.exists()]

    def provide_cache(self, given=None, prompt=None):
        if self.cache_ready():
            self.say('The game cache is already in place and verified.')
            return
        candidates = self.candidates(given)
        if not candidates and prompt is not None:
            answer = prompt('Path to the game cache (.7z file or unpacked folder, empty to stop): ').strip()
            if answer:
                candidates = [Path(answer).expanduser()]
        if not candidates:
            raise InstallerError(self.cache_help(), 3)
        source = candidates[0]
        staging = self.data / '.cache.tmp'
        shutil.rmtree(staging, ignore_errors=True)
        try:
            if source.is_dir():
                folder = self._cache_root(source)
                problems = self._verify_cache(folder)
                if problems:
                    raise InstallerError('That folder is not the verified game cache (%s).' % '; '.join(problems[:3]) + self.cache_help(), 3)
                self.say('Copying the verified game cache ...')
                staging.mkdir(parents=True)
                for name in self.inputs['cache']['files']:
                    shutil.copyfile(folder / name, staging / name)
            else:
                self.say('Checking the cache archive ...')
                if sha256_file(source) != self.inputs['cache']['archive_sha256']:
                    raise InstallerError('That file is not the archive this installer was verified with (%s). Download that exact '
                                         'file, or unpack another archive yourself and give the installer the unpacked folder, '
                                         'whose files are checked one by one.' % self.inputs['cache']['archive'] + self.cache_help(), 3)
                tool = self.sevenzip()
                staging.mkdir(parents=True)
                result = self.run([str(tool), 'x', '-y', '-bso0', '-bsp0', '-o' + str(staging), str(source)], capture_output=True, text=True, timeout=EXTRACT_TIMEOUT)
                if result.returncode:
                    raise InstallerError('The cache archive could not be unpacked (%s).' % (result.stderr or result.stdout).strip()[:200], 3)
                folder = self._cache_root(staging)
                problems = self._verify_cache(folder)
                if problems:
                    raise InstallerError('The archive is not the verified game cache (%s).' % '; '.join(problems[:3]) + self.cache_help(), 3)
                if folder != staging:
                    final = self.data / '.cache.verified'
                    shutil.rmtree(final, ignore_errors=True)
                    os.rename(folder, final)
                    shutil.rmtree(staging, ignore_errors=True)
                    staging = final
            problems = self._verify_cache(staging)  # the bytes about to be used, not the ones that were checked earlier
            if problems:
                raise InstallerError('The copied game cache changed while it was being copied (%s). Nothing was installed.' % '; '.join(problems[:3]), 3)
            old = self.data / '.cache.old'
            shutil.rmtree(old, ignore_errors=True)
            if self.cache.exists():
                os.rename(self.cache, old)
            os.rename(staging, self.cache)
            shutil.rmtree(old, ignore_errors=True)
            self.say('The game cache is verified and in place.')
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def cache_help(self):
        info = self.inputs['cache']
        return ('\nThe game cache is not included and is not downloaded by this installer. Download %s from the '
                'maintainers\' published folder:\n  %s\nThen run the installer again with --cache <that .7z file or the '
                'unpacked folder>. See %s for details.' % (info['archive'], info['where'], info['guide']))

    # ---- source, build, registration ----------------------------------------------------------------------------

    def _git_env(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ALLOW_PROTOCOL=self.protocols,
                   GIT_OPTIONAL_LOCKS='0', LC_ALL='C')
        return env

    def _git(self, args, cwd):
        return self.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'protocol.version=2'] + args, cwd=cwd, env=self._git_env(),
                        capture_output=True, text=True, timeout=GIT_TIMEOUT)

    def fetch_source(self):
        head = self._git(['rev-parse', 'HEAD'], self.source) if (self.source / '.git').is_dir() else None
        if head is not None and head.returncode == 0 and head.stdout.strip() == self.commit:
            self.restore_tracked()
            self.say('The SoloScape source is already at the release commit.')
            return
        fresh = not (self.source / '.git').is_dir()  # an older checkout is moved forward in place, keeping its upstream clones and Gradle cache
        if fresh:
            shutil.rmtree(self.source, ignore_errors=True)
        self.source.mkdir(parents=True, exist_ok=True)
        self.say('Fetching the SoloScape source (commit %s) ...' % self.commit[:12])
        if self._git(['init', '-q'], self.source).returncode:
            raise InstallerError('Could not prepare the source folder.')
        result = self._git(['fetch', '--quiet', '--depth=1', '--no-tags', '--no-recurse-submodules', self.origin, self.commit], self.source)
        if result.returncode:
            raise InstallerError('Could not fetch the release source: ' + result.stderr.strip()[-200:])
        fetched = self._git(['rev-parse', 'FETCH_HEAD^{commit}'], self.source).stdout.strip()
        if fetched != self.commit:
            raise InstallerError('The project returned a different commit than the release names. Nothing was built.')
        listing = self.run(['git', 'ls-tree', '-r', '-z', 'FETCH_HEAD'], cwd=self.source, env=self._git_env(), capture_output=True)
        for entry in listing.stdout.split(b'\0'):
            if entry and entry.split(b' ', 1)[0] not in (b'100644', b'100755'):
                raise InstallerError('The fetched source contains a link or submodule, which is never built.')
        if self._git(['checkout', '--quiet', '--force', '--detach', 'FETCH_HEAD'], self.source).returncode:
            raise InstallerError('Could not check out the release source.')
        self.restore_tracked()

    def restore_tracked(self):
        """A resumed source folder is ours, but its code is imported and run, so make it exactly the commit again:
        tracked files restored, and nothing untracked left where Python would import it from."""
        if self._git(['checkout', '--quiet', '--force', 'HEAD', '--', '.'], self.source).returncode:
            raise InstallerError('Could not restore the source folder to the release commit.')
        for place in ('scripts', 'patches', 'experiments'):
            if (self.source / place).is_dir():
                self._git(['clean', '-qfdx', '--', place], self.source)

    def load_project(self):
        sys.path.insert(0, str(self.source / 'scripts'))
        import local_dev
        import managed_install
        import package_builder
        import source_build
        import update_package
        return local_dev, managed_install, package_builder, source_build, update_package

    def write_environment(self, jdks):
        config = self.source / 'config'
        config.mkdir(exist_ok=True)
        (config / 'local.env').write_text(
            'SERVER_JAVA=' + shlex.quote(str(jdks['21'] / 'bin/java')) + '\n'
            'CLIENT_JAVA=' + shlex.quote(str(jdks['8'] / 'bin/java')) + '\n'
            'SOLOSCAPE_CACHE_HOME=' + shlex.quote(str(self.cache)) + '\n')

    def package(self, package_builder, destination):
        try:
            return package_builder.checkout_package(self.source, self.release, STORAGE_VERSIONS, destination, source=self.source)
        except (ValueError, OSError, KeyError):
            return None

    def build(self, jdks, cancelled=None):
        local_dev, managed_install, package_builder, source_build, update_package = self.load_project()
        self.say('Fetching the upstream projects at their pinned commits ...')
        job = update_package.Job(cancelled=cancelled, deadline=BUILD_DEADLINE)
        runner = source_build.Runner(job)
        source_build.provision_upstream(self.source, {'pins': dict(local_dev.PINNED)}, [], runner)
        self.write_environment(jdks)
        scratch = self.data / 'package.zip'
        if self.package(package_builder, scratch) is not None:
            self.say('A finished build for this release is already present.')
            return scratch
        self.logs.mkdir(parents=True, exist_ok=True)
        log = open(self.logs / 'build.log', 'w')
        seen = [0]

        def line(text):
            if text.startswith('> Task') and seen[0] % 8 == 0:
                self.say('  building: ' + text[7:80])
            seen[0] += 1 if text.startswith('> Task') else 0
        runner.on_line = line
        env = {k: v for k, v in os.environ.items() if not k.startswith('SOLOSCAPE_')}
        env.update(SERVER_JAVA=str(jdks['21'] / 'bin/java'), CLIENT_JAVA=str(jdks['8'] / 'bin/java'), SOLOSCAPE_CACHE_HOME=str(self.cache))
        self.say('Building SoloScape (first build downloads dependencies; this takes a while) ...')
        try:
            code = runner.run(['bash', str(self.source / 'scripts/prepare-build.sh')], cwd=self.source, env=env, log=log)
        finally:
            log.close()
        if code != 0:
            last = [t for t in runner.tail if t.strip()][-3:]
            raise InstallerError('The build did not finish (exit %s): %s. The full log is %s. Run the installer again to retry; '
                                 'finished steps are kept.' % (code, ' | '.join(t[:120] for t in last), self.logs / 'build.log'))
        digest = self.package(package_builder, scratch)
        if digest is None:
            raise InstallerError('The finished build does not match the release source. Nothing was installed.')
        return scratch

    def register(self, jdks, cancelled=None):
        local_dev, managed_install, package_builder, source_build, update_package = self.load_project()
        if self.install_complete(managed_install):
            try:
                # Hold the guard across build, staging and activation. A launcher/world must not
                # open between the version check and the pointer switch; the old version stays intact.
                with managed_install.acquire(self.install, 'exclusive') as lease:
                    current = managed_install.verify_version(self.install, lease.current())
                    if current['release'] == self.release and current['source_commit'] == self.commit:
                        self.say('SoloScape release %s is already installed in %s.' % (self.release, self.install))
                        return None
                    self.say('Updating SoloScape from %s to %s; saves and backups stay in place.' % (current['release'], self.release))
                    package = self.build(jdks, cancelled)
                    digest = sha256_file(package)
                    found = update_package.install_zip(self.install, package, digest, expected_release=self.release,
                                                       supply_roots=[str(self.source)], job=update_package.Job(cancelled=cancelled))
                    version = managed_install.activate(self.install, found['id'], lease=lease)
                    package.unlink(missing_ok=True)
                    return version
            except update_package.Cancelled as exc:
                raise InstallerError(str(exc), 130) from None
            except (managed_install.InstallError, update_package.PackageError) as exc:
                raise InstallerError(str(exc)) from None
        if self.install.exists():  # an earlier run stopped before the install was complete; it holds nothing of the player's
            self.remove_tree(self.install)
        package = self.build(jdks, cancelled)
        digest = sha256_file(package)
        self.say('Installing ...')
        version = managed_install.install_first(self.install, package, digest, str(self.profiles), str(self.cache), str(self.launcher),
                                                release=self.release, supply_roots=[str(self.source)],
                                                server_java=str(jdks['21'] / 'bin/java'), client_java=str(jdks['8'] / 'bin/java'))
        package.unlink(missing_ok=True)
        return version

    def install_complete(self, managed_install):
        """True only for an install whose configuration, guard, pointer and current version are all present and sound."""
        root = self.install
        try:
            if not (root / managed_install.CONFIG).is_file() or not (root / managed_install.GUARD).is_file():
                return False
            pointer = managed_install.read_pointer(root)
            managed_install.verify_version(root, pointer['current'])
            return (root / managed_install.BOOTSTRAP / 'managed_install.py').is_file()
        except Exception:  # any damage means this install is not usable and is rebuilt from the verified package
            return False

    @staticmethod
    def remove_tree(path):
        for base, dirs, _ in os.walk(path):
            for name in dirs:
                try:
                    os.chmod(os.path.join(base, name), 0o755)
                except OSError:
                    pass
        shutil.rmtree(path, ignore_errors=True)

    def keep_copy(self):
        """Keep the installer itself so a later repair (for example a lost cache) is one command: it is idempotent."""
        if HERE.is_file():
            target = self.data / 'soloscape-installer.sh'
            shutil.copyfile(HERE, target)
            os.chmod(target, 0o755)
            return target
        return None

    def launcher_script(self):
        script = self.data / 'soloscape'
        tools = self.tools / 'env/bin'
        path = ('PATH=%s:"$PATH"\nexport PATH\n' % shlex.quote(str(tools))) if (tools / 'python3').is_file() else ''
        script.write_text('#!/bin/sh\n%sexec python3 %s run %s "$@"\n' % (
            path, shlex.quote(str(self.install / 'bootstrap/managed_install.py')), shlex.quote(str(self.install))))
        os.chmod(script, 0o755)
        return script

    def shortcut(self, script):
        applications = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'applications'
        applications.mkdir(parents=True, exist_ok=True)
        entry = applications / 'soloscape.desktop'
        entry.write_text('[Desktop Entry]\nType=Application\nName=SoloScape\nComment=Offline 2011 RuneScape on your own computer\n'
                         'Exec=%s\nTerminal=false\nCategories=Game;\n' % desktop_quote(script))
        return entry

    # ---- run ----------------------------------------------------------------------------------------------------

    def run_all(self, cache=None, prompt=None, shortcut=True, cancelled=None):
        self.validate_identity()
        self.preflight()
        self.data.mkdir(parents=True, exist_ok=True)
        with open(self.data / '.installer.lock', 'a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise InstallerError('Another SoloScape installer is already running.') from None
            self.say('[1/5] Java')
            jdks = self.toolchains()
            self.say('[2/5] Game cache')
            self.provide_cache(cache, prompt)
            self.say('[3/5] Source')
            self.fetch_source()
            self.say('[4/5] Build')
            version = self.register(jdks, cancelled)
            self.say('[5/5] Launcher')
            script = self.launcher_script()
            kept = self.keep_copy()
            entry = self.shortcut(script) if shortcut else None
        self.say('')
        self.say('SoloScape is installed' + (' (version %s).' % version[:12] if version else '.'))
        self.say('Start it with: ' + str(script) + (' or from the application menu (%s).' % entry.name if entry else '.'))
        if kept:
            self.say('To repair or re-supply the game cache later, run: sh %s --cache <file or folder> --yes' % kept)
        self.say('Your saves, login and settings live in ' + str(self.profiles) + ' and ' + str(self.launcher) + ' and are kept across updates.')
        return 0


def desktop_quote(path):
    """One Desktop Entry Exec argument: double-quoted, with the characters the specification reserves escaped."""
    text = str(path).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    return '"' + text + '"'


def default_data():
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'soloscape'


def read_release(args):
    if args.release and args.commit:
        return args.release, args.commit
    text = resource('release.json')
    if text:
        record = json.loads(text)
        return record['release'], record['commit']
    raise InstallerError('Name the release with --release and --commit, or keep release.json next to the installer.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Install SoloScape: Java, source, game cache, build and the managed launcher.')
    parser.add_argument('--data', help='install location (default ~/.local/share/soloscape)')
    parser.add_argument('--release')
    parser.add_argument('--commit')
    parser.add_argument('--cache', help='the game cache .7z file or unpacked folder you downloaded')
    parser.add_argument('--plan', action='store_true', help='show what would be downloaded and installed, then stop')
    parser.add_argument('--yes', action='store_true', help='do not ask for confirmation')
    parser.add_argument('--no-shortcut', action='store_true', help='do not add an application menu entry')
    args = parser.parse_args(argv)
    try:
        release, commit = read_release(args)
        installer = Installer(args.data or default_data(), release, commit)
        installer.validate_identity()
        print(installer.plan())
        if args.plan:
            return 0
        interactive = sys.stdin.isatty()
        if not args.yes:
            if not interactive:
                raise InstallerError('Run with --yes to confirm the plan above (no terminal to ask).')
            if input('\nContinue? [y/N] ').strip().lower() not in ('y', 'yes'):
                print('Nothing was changed.')
                return 0
        print()
        return installer.run_all(cache=args.cache, prompt=input if interactive else None, shortcut=not args.no_shortcut)
    except InstallerError as exc:
        print('\nSoloScape installer: ' + str(exc), file=sys.stderr)
        return exc.code
    except (OSError, subprocess.SubprocessError) as exc:
        print('\nSoloScape installer: %s: %s. Finished steps are kept; run the installer again to retry.' % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('\nStopped. Finished steps are kept; run the installer again to continue.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
