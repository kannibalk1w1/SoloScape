"""Run actual shell entrypoints with disposable config and inert Python/Java stand-ins."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

WRAPPERS = ('launcher.sh', 'doctor.sh', 'dev-run.sh', 'prepare-build.sh',
            'smoke-profile.sh', 'smoke-coop.sh', 'test-content-coverage.sh')
SELECTORS = ('SOLOSCAPE_PROFILE_HOME', 'SOLOSCAPE_CACHE_HOME')
DUMP = 'import json,os\nprint(json.dumps({k:os.environ.get(k) for k in '+repr(SELECTORS)+'}))\n'


class ConfigExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        scripts = self.root/'scripts'
        scripts.mkdir()
        (self.root/'config').mkdir()
        for name in WRAPPERS:
            shutil.copy2(Path(__file__).with_name(name), scripts/name)
        for name in ('smoke_profile.py','smoke_coop.py','content_coverage.py'):
            (scripts/name).write_text(DUMP)
        (scripts/'local_dev.py').write_text(
            'from pathlib import Path\nCLIENT=Path("unused-client")\n'
            'def jar(*args): return Path("inert-client.jar")\n'
            'if __name__ == "__main__":\n'+''.join('    '+line+'\n' for line in DUMP.splitlines()))
        self.java = self.root/'fake-java'
        self.java.write_text('#!/usr/bin/env python3\n'+DUMP)
        self.java.chmod(0o755)

    def run_wrappers(self, config='', inherited=None):
        (self.root/'config/local.env').write_text(config+'\nCLIENT_JAVA='+str(self.java)+'\n')
        env = {k:v for k,v in os.environ.items() if k not in SELECTORS}
        env.update(inherited or {})
        results=[]
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                result=subprocess.run(['bash',str(self.root/'scripts'/name)],env=env,
                                      cwd=self.root,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)
                results.append(json.loads(result.stdout))
        return results

    def test_plain_local_config_assignments_reach_every_child(self):
        expected={key:str(self.root/('external '+key)) for key in SELECTORS}
        config='\n'.join(key+'="'+value+'"' for key,value in expected.items())
        for result in self.run_wrappers(config): self.assertEqual(result,expected)

    def test_unset_stays_unset_so_existing_defaults_apply(self):
        for result in self.run_wrappers(): self.assertEqual(result,dict.fromkeys(SELECTORS))

    def test_explicit_empty_is_preserved_for_native_validation(self):
        for result in self.run_wrappers('\n'.join(key+'=' for key in SELECTORS)):
            self.assertEqual(result,{key:'' for key in SELECTORS})

    def test_exported_invocation_environment_remains_supported(self):
        expected={key:str(self.root/key) for key in SELECTORS}
        for result in self.run_wrappers(inherited=expected): self.assertEqual(result,expected)
