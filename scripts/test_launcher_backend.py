"""Launcher protocol/session tests use fake JVMs and entirely disposable worlds."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import launcher_backend
import local_dev
import profile_session
import profiles
from test_local_dev import FAKE_JAVA


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='soloscape-launcher-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patches = []
        for key, value in [('ROOT', self.root), ('SERVER', self.root/'upstream/game-server'),
                           ('CLIENT', self.root/'upstream/runelite-client'), ('RUNTIME', self.root/'.runtime'), ('READY_TIMEOUT', 1)]:
            self.patches.append(patch.object(local_dev, key, value))
        self.patches.append(patch.object(profiles, 'PROFILES', self.root/'profiles'))
        for item in self.patches:
            item.start();self.addCleanup(item.stop)
        for directory, name in [(local_dev.SERVER/'game','void-server-test.jar'), (local_dev.CLIENT/'client','void-client-test.jar')]:
            (directory/'build/libs').mkdir(parents=True)
            (directory/'build/libs'/name).touch()
        self.java = self.root/'java'
        self.java.write_text(FAKE_JAVA.replace('"void-server" in sys.argv[2]', 'any("void-server" in arg for arg in sys.argv)'))
        self.java.chmod(0o755)
        self.env = patch.dict(os.environ, {'SERVER_JAVA': str(self.java), 'CLIENT_JAVA': str(self.java),
                                           'TEST_ROOT': str(self.root), 'TEST_CASE': 'interrupt',
                                           'storage.players.path': '/unsafe/inherited/world'})
        self.env.start();self.addCleanup(self.env.stop)
        local_dev.write_build_stamp(local_dev.jar(local_dev.SERVER/'game','void-server-*.jar'), local_dev.jar(local_dev.CLIENT/'client','void-client-*.jar'))
        self.profile = profiles.create('Disposable', 'Tester')

    def wait_for(self, predicate):
        deadline=time.monotonic()+4
        while not predicate():
            if time.monotonic()>deadline:self.fail('Simulated session did not reach the expected state')
            time.sleep(.01)

    def test_session_waits_for_readiness_and_holds_lock_until_verified_shutdown(self):
        cancelled=threading.Event();events=[];errors=[]
        def target():
            try:profile_session.run(self.profile,cancelled,lambda *args:events.append(args),checked=False,port=43595)
            except Exception as exc:errors.append(exc)
        worker=threading.Thread(target=target)
        worker.start()
        try:
            self.wait_for(lambda:(self.root/'client.args').exists())
            with self.assertRaises(RuntimeError):self.profile.backup()
            args=(self.root/'client.args').read_text()
            self.assertIn('--address 127.0.0.1 --port 43595',args)
            self.assertIn('-Duser.home='+str(self.profile.directory/'client-home'),args)
        finally:
            cancelled.set();worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assertEqual(events[-1][0],'stopped')
        self.assertIn('saved and verified',events[-1][1])
        self.assertEqual(len(list((self.profile.directory/'backups').glob('*.zip'))),2)
        for role in ('server','client'):
            self.assertEqual((self.root/(role+'.stopped')).read_text(),'graceful')
            with self.assertRaises(ProcessLookupError):os.kill(int((self.root/(role+'.pid')).read_text()),0)
        self.profile.backup()  # exclusive lock was released only after cleanup

    def test_profile_environment_overrides_inherited_dotted_settings(self):
        env=profile_session.owned_environment(self.profile,43595)
        self.assertEqual(env['storage.players.path'],str(self.profile.state/'saves')+'/')
        self.assertEqual(env['bots.count'],'0')
        self.assertEqual(env['TEST_ROOT'],str(self.root))

    def test_stdio_returns_exactly_one_json_response_per_request_and_hides_secrets(self):
        source=io.StringIO('not-json\n'+json.dumps({'id':1,'action':'list'})+'\n'+json.dumps({'id':2,'action':'create','label':'Other','account':'Other'})+'\n')
        destination=io.StringIO();launcher_backend.serve(source,destination)
        rows=[json.loads(line) for line in destination.getvalue().splitlines()]
        self.assertEqual(len(rows),3);self.assertFalse(rows[0]['ok'])
        self.assertEqual(rows[1]['id'],1);self.assertTrue(rows[2]['ok'])
        self.assertNotIn('password',destination.getvalue())

    def test_backend_refuses_switch_while_worker_running_and_eof_waits_for_stop(self):
        backend=launcher_backend.Backend();self.addCleanup(backend.close)
        actual_run=profile_session.run
        with patch.object(profile_session,'run',side_effect=lambda *a,**kw:actual_run(*a,**kw,checked=False)):
            backend.dispatch({'action':'start','profile':self.profile.manifest['id'],'port':43595})
            self.wait_for(lambda:(self.root/'client.args').exists())
            with self.assertRaises(RuntimeError):backend.dispatch({'action':'start','profile':self.profile.manifest['id']})
            backend.close()
        self.assertFalse(backend.current()['running']);self.assertEqual(backend.current()['stage'],'stopped')

    def test_oversized_request_is_drained_without_desynchronizing_the_next_reply(self):
        source=io.StringIO('x'*(launcher_backend.MAX_REQUEST*3)+'\n'+json.dumps({'id':7,'action':'status'})+'\n')
        destination=io.StringIO();launcher_backend.serve(source,destination)
        rows=[json.loads(line) for line in destination.getvalue().splitlines()]
        self.assertEqual(len(rows),2);self.assertFalse(rows[0]['ok'])
        self.assertTrue(rows[1]['ok']);self.assertEqual(rows[1]['id'],7)

    def test_invalid_port_or_profile_never_starts_processes(self):
        backend=launcher_backend.Backend()
        with self.assertRaises(ValueError):backend.dispatch({'action':'start','profile':self.profile.manifest['id'],'port':True})
        with self.assertRaises(ValueError):backend.dispatch({'action':'backup','profile':'../../other'})
        self.assertFalse((self.root/'server.pid').exists())
