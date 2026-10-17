#!/usr/bin/env python3
"""Prepare a private immutable runtime experiment. Never publish its binary/data outputs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'experiments/native-prebuilt-server'))
import local_dev
from runtime_inputs import collect_data

spec = importlib.util.spec_from_file_location('private_payload_helpers', ROOT/'experiments/native-prebuilt-server/run.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def prepare(cache):
    cache = cache.absolute()
    if cache.is_symlink() or not cache.is_dir():
        raise ValueError('Supply a real authorized compatible cache directory.')
    parent = ROOT/'.runtime/prebuilt-runtime'
    for directory in (ROOT/'.runtime',parent):
        if directory.is_symlink():
            raise ValueError('The private experiment root cannot be a link.')
        directory.mkdir(exist_ok=True)
    run = parent/str(time.time_ns())
    run.mkdir(mode=0o700)
    result = {'passed':False,'scope':'Private runtime preparation only; no public package or activation.'}
    try:
        with local_dev.build_lock(shared=True):
            native = {'server':local_dev.jar(local_dev.SERVER/'game','void-server-*.jar'),
                      'client':local_dev.jar(local_dev.CLIENT/'client','void-client-*.jar')}
            local_dev.verify_build_stamp(native['server'],native['client'])
            for role in ('client','server'):
                subprocess.run([sys.executable,str(ROOT/'scripts/verify_patches.py'),role],check=True)
            stamp = json.loads((local_dev.RUNTIME/'build-stamp.json').read_text())
            commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            committed_preparer = subprocess.check_output(['git','show',commit+':experiments/prebuilt-runtime-contract/prepare.py'],cwd=ROOT)
            if Path(__file__).read_bytes() != committed_preparer:
                raise RuntimeError('Commit the exact private preparer before running it.')
            payload = run/'payload'
            roles = {'server':'upstream/game-server/game/build/libs/'+native['server'].name,
                     'client':'upstream/runelite-client/client/build/libs/'+native['client'].name,
                     'launcher':'scripts/launcher.sh'}
            payload.mkdir()
            for role, source in native.items():
                destination = payload/roles[role]
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,destination)
                if support.digest(destination) != stamp['jars'][role]:
                    raise RuntimeError('Copied jar differs from its matched build: '+role)
            inputs = collect_data(local_dev.SERVER,sorted((ROOT/'patches/server').glob('*.patch')))
            for item in inputs:
                destination = payload/'upstream/game-server'/item['path']
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(local_dev.SERVER/item['path'],destination)
                if support.digest(destination) != item['sha256']:
                    raise RuntimeError('Data changed during copying: '+item['path'])
            source_map = {name:'scripts/'+name for name in
                          ('local_dev.py','profiles.py','profile_session.py','session_recovery.py',
                           'release_updates.py','deck_awake.py','launcher.sh')}
            source_map.update({'owned_launcher_backend.py':'scripts/launcher_backend.py',
                               'prebuilt_bootstrap.py':'experiments/prebuilt-runtime-contract/prebuilt_bootstrap.py',
                               'prebuilt_manifest.py':'experiments/prebuilt-runtime-contract/manifest.py'})
            (payload/'scripts').mkdir()
            for destination, source_name in source_map.items():
                source = ROOT/source_name
                committed = subprocess.check_output(['git','show',commit+':'+source_name],cwd=ROOT)
                if source.read_bytes() != committed:
                    raise RuntimeError('Commit the exact runtime input before preparing: '+source_name)
                (payload/'scripts'/destination).write_bytes(committed)
            (payload/'scripts/launcher_backend.py').write_text('from prebuilt_bootstrap import main\nmain()\n')
            files = {p.relative_to(payload).as_posix():{'size':p.stat().st_size,'sha256':support.digest(p)}
                     for p in sorted(payload.rglob('*')) if p.is_file()}
            manifest = {'format':1,'source_commit':commit,'platform':'linux-x86_64','cache_revision':634,
                        'pins':stamp['pins'],'patches':stamp['patches'],'roles':roles,'files':files}
            (payload/'soloscape-runtime.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
            source_inventory = support.tree(cache)
            external_cache = run/'cache'
            shutil.copytree(cache,external_cache)
            if support.tree(external_cache) != source_inventory:
                raise RuntimeError('The private copied cache differs from its input.')
            for path in payload.rglob('*'):
                path.chmod(0o555 if path.is_dir() or path.name=='launcher.sh' else 0o444)
            payload.chmod(0o555)
            # Import the supplied read-only validator without writing bytecode into the payload.
            validator_spec = importlib.util.spec_from_file_location('prepared_manifest',ROOT/'experiments/prebuilt-runtime-contract/manifest.py')
            validator = importlib.util.module_from_spec(validator_spec)
            validator_spec.loader.exec_module(validator)
            if validator.validate(payload) != manifest:
                raise RuntimeError('Prepared manifest validation differs.')
            state = run/'state'
            for name in ('home','temp','launcher','profiles'):
                (state/name).mkdir(parents=True,mode=0o700)
            (state/'alsa.conf').write_text('')
            result.update(passed=True,source_commit=commit,payload=str(payload),cache=str(external_cache),
                          state=str(state),manifest_sha256=support.digest(payload/'soloscape-runtime.json'),
                          payload_tree_sha256=support.tree_digest(support.tree(payload)),
                          cache_tree_sha256=support.tree_digest(source_inventory),files=len(files),
                          jars=stamp['jars'],data_files=len(inputs),data_bytes=sum(i['size'] for i in inputs),
                          source_cache_unchanged=support.tree(cache)==source_inventory,
                          roles=roles,cache_revision_detected=False,public_distribution_approved=False)
            if not result['source_cache_unchanged']:
                raise RuntimeError('The supplied input cache changed.')
    except BaseException as exc:
        result.update(passed=False,failure=type(exc).__name__+': '+str(exc))
        raise
    finally:
        result['preparer_sha256']=support.digest(Path(__file__))
        (run/'preparation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print('Evidence:',run.relative_to(ROOT)/'preparation.json',flush=True)
    return run


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    prepare(parser.parse_args().cache)
