#!/usr/bin/env python3
"""Real Swing controller-entry adapter and backend, fully disposable and private."""
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time
import local_dev
import argparse


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop',action='store_true',help='Use the authorized current DISPLAY; never terminate it.')
    parser.add_argument('--updates', action='store_true', help='Test release discovery dialogs with private deterministic metadata, no downloads.')
    options=parser.parse_args()
    root=local_dev.ROOT/'.runtime/launcher-tests'/str(time.time_ns())
    (root/'scripts').mkdir(parents=True)
    for source in (local_dev.ROOT/'scripts').glob('*.py'):
        shutil.copyfile(source,root/'scripts'/source.name)
    for name in ('brazier.jpg', 'brazier-flames.png'):
        artwork=local_dev.ROOT/'.runtime/launcher-art'/name
        if artwork.is_file():
            (root/'.runtime/launcher-art').mkdir(parents=True,exist_ok=True)
            shutil.copyfile(artwork,root/'.runtime/launcher-art'/name)
    if options.updates:
        with (root/'scripts/release_updates.py').open('a') as fixture:
            fixture.write('\n# Private metadata fixture only; real backend and GUI remain unchanged.\n'
                          'def check():\n    import time\n    from pathlib import Path\n'
                          '    data=json.loads((Path(__file__).parent.parent/"update-response.json").read_text())\n'
                          '    time.sleep(data.pop("delay") / 1000)\n    return data\n')
    probe = 'NativeLauncherUpdateProbe' if options.updates else 'NativeLauncherProbe'
    java=Path(os.environ.get('CLIENT_JAVA','java')).resolve()
    javac=java.with_name('javac')
    classes=root/'classes';classes.mkdir()
    jar=local_dev.jar(local_dev.CLIENT/'client','void-client-*.jar')
    with local_dev.build_lock(shared=True) as guard:
        subprocess.run([str(javac),'-encoding','UTF-8','-cp',str(jar),'-d',str(classes),str(local_dev.ROOT/'scripts/harness'/(probe+'.java'))],check=True)
        display=None
        if options.desktop:
            if not os.environ.get('DISPLAY'):raise RuntimeError('--desktop requires an explicit authorized DISPLAY.')
            environment=dict(os.environ)
        else:
            read_fd,write_fd=os.pipe()
            display=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x800x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            os.close(write_fd)
        try:
            if display is not None:
                with selectors.DefaultSelector() as ready:
                    ready.register(read_fd,selectors.EVENT_READ)
                    if not ready.select(10):raise RuntimeError('Owned display was not ready.')
                number=os.read(read_fd,64).decode().strip()
                if not number.isdigit() or display.poll() is not None:raise RuntimeError('No owned display; refusing fallback.')
                environment=dict(os.environ,DISPLAY=':'+number)
            environment['SOLOSCAPE_PROFILE_HOME'] = str(root/'.runtime/profiles')
            subprocess.run([str(java),'-Duser.home='+str(root/'home'),'-cp',str(jar)+':'+str(classes),'net.runelite.client.soloscape.launcher.'+probe,str(root)],env=environment,pass_fds=(guard.fileno(),),check=True,timeout=90)
            print('Private launcher evidence:',root)
        finally:
            if display is not None:
                os.close(read_fd)
                display.terminate()
                try:display.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    display.kill();display.wait(timeout=5)  # Only our owned display, no game/save process.


if __name__=='__main__':main()
