"""Use real pidfds, inherited flocks and disposable simulated JVMs."""
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import threading
import unittest
import zipfile
from unittest.mock import patch
import local_dev
import launcher_backend
import profiles
import session_recovery
from test_launcher_backend import LauncherTests
from test_profiles import native_save


class RecoveryTests(LauncherTests):
    # Reuse only fixture setup/helpers, not the inherited launcher's test methods.
    def test_fixture_cleanup_waits_for_slow_owned_children_to_exit(self):
        self.java.write_text(self.java.read_text().replace(
            'def stop(*args):', 'def stop(*args):\n    time.sleep(0.2)'))
        record = self.orphan()
        descriptors = [os.pidfd_open(child['pid']) for child in record['children'].values()]
        try:
            self.assertTrue(self.doCleanups())
            for descriptor in descriptors:
                self.assertTrue(select.select([descriptor], [], [], 0)[0],
                                'Fixture cleanup returned before an owned child exited')
            self.assertFalse(self.root.exists())
        finally:
            for descriptor in descriptors:
                # Also settle the intentionally slow children when demonstrating the old failure.
                select.select([descriptor], [], [], 5)
                os.close(descriptor)

    def orphan(self):
        (self.profile.state/'saves/tester.toml').write_bytes(native_save())
        harness = '''
import sys, threading
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import local_dev, profiles, profile_session
root=Path(sys.argv[2]);local_dev.ROOT=root;local_dev.RUNTIME=root/'.runtime'
local_dev.SERVER=root/'upstream/game-server';local_dev.CLIENT=root/'upstream/runelite-client'
profiles.PROFILES=root/'profiles'
profile_session.run(profiles.Profile(Path(sys.argv[3])),threading.Event(),lambda *args:None,checked=False)
'''
        launcher=subprocess.Popen([sys.executable,'-c',harness,str(Path(__file__).parent),str(self.root),str(self.profile.directory)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                  env=dict(os.environ, SOLOSCAPE_PROFILE_HOME=str(profiles.PROFILES)))
        children = []
        def remember_children():
            record = session_recovery.read(self.profile)
            if record is None:
                return
            for role, process in session_recovery.candidates(self.profile, record).items():
                try:
                    descriptor = os.pidfd_open(process['pid'])
                except ProcessLookupError:
                    continue
                if session_recovery.verified(self.profile, record, process, role):
                    children.append(descriptor)
                else:
                    os.close(descriptor)
        def cleanup():
            try:
                # Capture partial startup too, before removing the parent and its guards.
                if not children and launcher.poll() is None:
                    remember_children()
                if launcher.poll() is None:launcher.kill();launcher.wait(timeout=5)
                for descriptor in children:
                    try:
                        signal.pidfd_send_signal(descriptor, signal.SIGCONT)
                        signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                for descriptor in children:
                    self.assertTrue(select.select([descriptor], [], [], 5)[0],
                                    'Owned fixture child did not exit before directory cleanup')
            finally:
                for descriptor in children:
                    os.close(descriptor)
        self.addCleanup(cleanup)
        self.wait_for(lambda:(self.root/'client.args').exists() or launcher.poll() is not None)
        self.assertIsNone(launcher.poll())
        # Both records must be durable before taking out the parent.
        self.wait_for(lambda:len(session_recovery.read(self.profile)['children'])==2)
        remember_children()
        self.assertEqual(len(children), 2)
        launcher.kill();launcher.wait(timeout=5)
        return session_recovery.read(self.profile)

    def test_malformed_record_does_not_hide_other_profiles_or_authorize_recovery(self):
        healthy = profiles.create('Healthy', 'Healthy')
        healthy_manifest = (healthy.directory / 'profile.json').read_bytes()
        with local_dev.build_lock(shared=True), self.profile.lock():
            record = session_recovery.begin(self.profile, 43594, '/fixture/server.jar', '/fixture/client.jar')
        path = self.profile.directory / session_recovery.RECORD
        malformed = [
            dict(record, children=[]),
            dict(record, children=None),
            dict(record, children={'server': []}),
            dict(record, children={'other': record['owner']}),
            dict(record, owner=[]),
            dict(record, owner=dict(record['owner'], pid=True)),
            dict(record, owner=dict(record['owner'], start='unknown')),
            dict(record, session=12345678901234567890123456789012),
            dict(record, jars={'server': 42, 'client': '/fixture/client.jar'}),
            dict(record, locks=[]),
            dict(record, locks={'profile': ['bad', 1], 'build': [1, 2]}),
        ]
        backend = launcher_backend.Backend()
        self.addCleanup(backend.close)
        for index, invalid in enumerate(malformed):
            with self.subTest(index=index):
                session_recovery.write(self.profile, invalid)
                before = path.read_bytes()
                rows = {row['id']: row for row in backend.dispatch({'action': 'list'})['profiles']}
                self.assertFalse(rows[self.profile.manifest['id']]['recovery']['recoverable'])
                self.assertIsNone(rows[healthy.manifest['id']]['recovery'])
                with patch.object(signal, 'pidfd_send_signal') as send_signal:
                    with self.assertRaises(ValueError):
                        session_recovery.recover(self.profile, threading.Event(), lambda *args: None)
                    with self.assertRaises(ValueError):
                        session_recovery.archive_ended(self.profile)
                    send_signal.assert_not_called()
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual((healthy.directory / 'profile.json').read_bytes(), healthy_manifest)
                self.assertEqual(list((self.profile.directory / 'backups').glob('*.zip')), [])

    def test_orphan_recovery_checks_ownership_and_preserves_uncertain_backup_truth(self):
        self.orphan()
        status=session_recovery.inspect(self.profile)
        self.assertTrue(status['recoverable']);self.assertCountEqual(status['active'],['client','server'])
        events=[]
        self.assertEqual(session_recovery.recover(self.profile,threading.Event(),lambda *args:events.append(args)),0)
        self.assertIsNone(session_recovery.read(self.profile))
        self.assertIn('Clean shutdown is unconfirmed',events[-1][1])
        for role in ('client','server'):self.assertEqual((self.root/(role+'.stopped')).read_text(),'graceful')
        reasons=[]
        for p in (self.profile.directory/'backups').glob('*.zip'):
            with zipfile.ZipFile(p) as z:reasons.append(json.loads(z.read('backup.json'))['reason'])
        self.assertCountEqual(reasons,['before-launch','after-recovered-shutdown'])
        with self.profile.lock():pass
        with local_dev.build_lock():pass

    def test_backend_recover_worker_refuses_overlap_and_finishes_the_recorded_world(self):
        record=self.orphan()
        record['owner']=session_recovery.identity(os.getpid())
        session_recovery.write(self.profile,record)
        backend=launcher_backend.Backend()
        class ActiveWorker:
            def is_alive(self):return True
        backend.worker=ActiveWorker()
        with self.assertRaisesRegex(RuntimeError,'already running'):
            backend.dispatch({'action':'recover','profile':self.profile.manifest['id']})
        self.assertFalse((self.root/'server.stopped').exists())
        backend.worker=None
        try:
            backend.dispatch({'action':'recover','profile':self.profile.manifest['id']})
            backend.worker.join(5)
            status=backend.current()
            self.assertFalse(status['running'])
            self.assertIsNone(status['error'])
            self.assertEqual(status['stage'],'stopped')
            self.assertIn('Clean shutdown is unconfirmed',status['message'])
            self.assertIsNone(session_recovery.read(self.profile))
        finally:backend.close()

    def test_wrong_process_environment_refuses_before_any_signal(self):
        record=self.orphan()
        record['session']='f'*32;session_recovery.write(self.profile,record)
        with self.assertRaisesRegex(RuntimeError,'identity changed'):
            session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertFalse((self.root/'client.stopped').exists());self.assertFalse((self.root/'server.stopped').exists())

    def test_wrong_jar_or_replaced_guard_refuses_without_partial_stop(self):
        record=self.orphan()
        record['jars']['server']='/unrelated/void-server.jar'
        session_recovery.write(self.profile,record)
        with self.assertRaisesRegex(RuntimeError,'identity changed'):
            session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertFalse((self.root/'client.stopped').exists())
        record['jars']['server']=str(local_dev.jar(local_dev.SERVER/'game','void-server-*.jar'))
        session_recovery.write(self.profile,record)
        lock=self.profile.directory/'profile.lock'
        lock.rename(self.profile.directory/'held-profile.lock')
        lock.touch()
        with self.assertRaisesRegex(RuntimeError,'identity changed'):
            session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertFalse((self.root/'client.stopped').exists())
        self.assertFalse((self.root/'server.stopped').exists())

    def test_recovery_without_native_confirmation_keeps_record_and_previous_backup(self):
        os.environ['TEST_CASE'] = 'no-save-receipt'
        self.orphan()
        before = set((self.profile.directory / 'backups').glob('*.zip'))
        with self.assertRaisesRegex(RuntimeError, 'confirm'):
            session_recovery.recover(self.profile, threading.Event(), lambda *args: None)
        self.assertIsNotNone(session_recovery.read(self.profile))
        self.assertEqual(set((self.profile.directory / 'backups').glob('*.zip')), before)
        for role in ('server', 'client'):
            self.assertEqual((self.root / (role + '.stopped')).read_text(), 'graceful')

    def test_dirty_recovered_save_retains_record_and_previous_backup(self):
        self.orphan()
        (self.profile.state/'saves/.save-incomplete.tmp').write_text('unfinished')
        before=set((self.profile.directory/'backups').glob('*.zip'))
        with self.assertRaisesRegex(RuntimeError,'save errors/temporary files'):
            session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertIsNotNone(session_recovery.read(self.profile))
        self.assertEqual(set((self.profile.directory/'backups').glob('*.zip')),before)
        for role in ('client','server'):
            self.assertEqual((self.root/(role+'.stopped')).read_text(),'graceful')

    def test_live_original_launcher_is_not_adopted(self):
        record=self.orphan();record['owner']=session_recovery.identity(os.getpid());session_recovery.write(self.profile,record)
        self.assertFalse(session_recovery.inspect(self.profile)['recoverable'])
        with self.assertRaisesRegex(RuntimeError,'original launcher is still active'):
            session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertFalse((self.root/'client.stopped').exists())

    def test_suspended_owned_process_is_not_forced_or_partially_stopped(self):
        record=self.orphan();pid=record['children']['server']['pid'];os.kill(pid,signal.SIGSTOP)
        self.wait_for(lambda:session_recovery.identity(pid)['state']=='T')
        with self.assertRaisesRegex(RuntimeError,'suspended'):
            session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertFalse((self.root/'client.stopped').exists());self.assertFalse((self.root/'server.stopped').exists())

    def test_missing_pid_record_discovers_only_exact_session_and_inherited_guards(self):
        record=self.orphan();record['children']={};session_recovery.write(self.profile,record)
        self.assertTrue(session_recovery.inspect(self.profile)['recoverable'])
        session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        self.assertIsNone(session_recovery.read(self.profile))

    def test_cancel_before_signal_keeps_live_world_and_record(self):
        self.orphan();cancelled=threading.Event();cancelled.set()
        session_recovery.recover(self.profile,cancelled,lambda *args:None)
        self.assertIsNotNone(session_recovery.read(self.profile));self.assertFalse((self.root/'client.stopped').exists())

    def test_parallel_recovery_lock_and_symlink_record_are_rejected(self):
        self.orphan()
        with session_recovery.recovery_lock(self.profile):
            with self.assertRaisesRegex(RuntimeError,'Another launcher'):
                session_recovery.recover(self.profile,threading.Event(),lambda *args:None)
        (self.profile.directory/session_recovery.RECORD).unlink()
        (self.profile.directory/session_recovery.RECORD).symlink_to(self.root/'unrelated')
        with self.assertRaisesRegex(ValueError,'unsafe'):
            session_recovery.read(self.profile)

    def test_another_code_root_cannot_recover_or_archive_the_live_earlier_world(self):
        self.orphan()
        record_path = self.profile.directory / session_recovery.RECORD
        before = record_path.read_bytes()
        other_runtime = self.root / 'other-version/.runtime'
        other_runtime.mkdir(parents=True)
        with patch.object(local_dev, 'RUNTIME', other_runtime):
            with local_dev.build_lock(shared=True):
                pass
            self.assertFalse(session_recovery.inspect(self.profile)['recoverable'])
            with patch.object(signal, 'pidfd_send_signal') as send_signal:
                with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                    session_recovery.recover(self.profile, threading.Event(), lambda *args: None)
                with self.assertRaises(RuntimeError):
                    session_recovery.archive_ended(self.profile)
                send_signal.assert_not_called()
            self.assertEqual(record_path.read_bytes(), before)
            for role in ('client', 'server'):
                self.assertFalse((self.root / (role + '.stopped')).exists())
        # Returning to the original build context retains a usable recovery route.
        session_recovery.recover(self.profile, threading.Event(), lambda *args: None)
        self.assertIsNone(session_recovery.read(self.profile))

    def test_stale_record_from_finished_worker_in_this_backend_is_recoverable(self):
        record=self.orphan();record['owner']=session_recovery.identity(os.getpid());session_recovery.write(self.profile,record)
        self.assertTrue(session_recovery.inspect(self.profile,owner_active=lambda:False)['recoverable'])
        session_recovery.recover(self.profile,threading.Event(),lambda *args:None,owner_active=lambda:False)
        self.assertIsNone(session_recovery.read(self.profile))

    def test_listing_a_stale_self_owned_profile_does_not_confuse_another_active_world(self):
        record=self.orphan()
        for child in record['children'].values():os.kill(child['pid'],signal.SIGTERM)
        self.wait_for(lambda:all(not session_recovery.same_process(child) for child in record['children'].values()))
        record['owner']=session_recovery.identity(os.getpid())
        session_recovery.write(self.profile,record)
        other=profiles.create('Other world','Other')
        backend=launcher_backend.Backend()
        with patch.object(backend,'current',return_value={'running':True,'profile':other.manifest['id']}):
            rows=backend.dispatch({'action':'list'})['profiles']
        prior=next(row for row in rows if row['id']==self.profile.manifest['id'])
        active=next(row for row in rows if row['id']==other.manifest['id'])
        self.assertTrue(prior['recovery']['recoverable'])
        self.assertIsNone(active['recovery'])

    def test_restore_refuses_a_record_before_switching_generation(self):
        record=self.orphan()
        self.wait_for(lambda:len(list((self.profile.directory/'backups').glob('*.zip')))==1)
        for role in ('client','server'):os.kill(record['children'][role]['pid'],signal.SIGTERM)
        self.wait_for(lambda:all((self.root/(role+'.stopped')).exists() for role in ('client','server')))
        self.wait_for(lambda:all(not session_recovery.same_process(child) for child in record['children'].values()))
        original=self.profile.manifest['generation']
        backup=next((self.profile.directory/'backups').glob('*.zip'))
        with self.assertRaisesRegex(RuntimeError,'Recover the earlier session'):
            self.profile.restore(backup.name)
        self.assertEqual(self.profile.manifest['generation'],original)

    def test_backend_SIGTERM_runs_owned_save_and_cleanup_instead_of_orphaning(self):
        harness="""
import sys,runpy
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import local_dev,profiles
root=Path(sys.argv[2]);local_dev.ROOT=root;local_dev.RUNTIME=root/'.runtime'
local_dev.SERVER=root/'upstream/game-server';local_dev.CLIENT=root/'upstream/runelite-client'
profiles.PROFILES=root/'profiles';local_dev.doctor=lambda **kwargs:True
runpy.run_path(str(Path(sys.argv[1])/'launcher_backend.py'),run_name='__main__')
"""
        backend=subprocess.Popen([sys.executable,'-c',harness,str(Path(__file__).parent),str(self.root)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,
                                 env=dict(os.environ, SOLOSCAPE_PROFILE_HOME=str(profiles.PROFILES)))
        try:
            backend.stdin.write(json.dumps({'id':1,'action':'start','profile':self.profile.manifest['id']})+'\n');backend.stdin.flush()
            self.assertTrue(json.loads(backend.stdout.readline())['ok'])
            self.wait_for(lambda:(self.root/'client.args').exists())
            backend.terminate();self.assertEqual(backend.wait(timeout=5),0)
            self.assertIsNone(session_recovery.read(self.profile))
            for role in ('client','server'):self.assertEqual((self.root/(role+'.stopped')).read_text(),'graceful')
        finally:
            if backend.poll() is None:backend.kill();backend.wait(timeout=5)
            backend.stdin.close();backend.stdout.close()

    def test_archive_ended_record_preserves_evidence_and_allows_damaged_world_restore(self):
        record=self.orphan();backup=next((self.profile.directory/'backups').glob('*.zip'))
        with self.assertRaises(RuntimeError):session_recovery.archive_ended(self.profile)
        for role in ('client','server'):os.kill(record['children'][role]['pid'],signal.SIGTERM)
        self.wait_for(lambda:all((self.root/(role+'.stopped')).exists() for role in ('client','server')))
        self.wait_for(lambda:all(not session_recovery.same_process(child) for child in record['children'].values()))
        (self.profile.state/'saves/tester.toml').write_text('damaged')
        session_recovery.archive_ended(self.profile)
        self.assertIsNone(session_recovery.read(self.profile))
        self.assertTrue((self.profile.directory/('session.'+record['session']+'.unverified.json')).exists())
        self.profile.restore(backup.name)
        self.assertIsNone(self.profile.metadata()['error'])


# The shared fixture class has its own tests in its original module; don't duplicate counts.
for name in dir(LauncherTests):
    if name.startswith('test_'):
        setattr(RecoveryTests,name,None)
del LauncherTests
