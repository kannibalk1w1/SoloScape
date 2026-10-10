#!/usr/bin/env python3
"""Real Swing controller-entry adapter and backend, fully disposable and private."""
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import time
import local_dev


def main():
    root=local_dev.ROOT/'.runtime/launcher-tests'/str(time.time_ns())
    (root/'scripts').mkdir(parents=True)
    for source in (local_dev.ROOT/'scripts').glob('*.py'):
        shutil.copyfile(source,root/'scripts'/source.name)
    java=Path(os.environ.get('CLIENT_JAVA','java')).resolve()
    javac=java.with_name('javac')
    classes=root/'classes';classes.mkdir()
    jar=local_dev.jar(local_dev.CLIENT/'client','void-client-*.jar')
    with local_dev.build_lock(shared=True) as guard:
        subprocess.run([str(javac),'-cp',str(jar),'-d',str(classes),str(local_dev.ROOT/'scripts/harness/NativeLauncherProbe.java')],check=True)
        read_fd,write_fd=os.pipe()
        display=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x800x24','-nolisten','tcp'],pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        os.close(write_fd)
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(read_fd,selectors.EVENT_READ)
                if not ready.select(10):raise RuntimeError('Owned display was not ready.')
                number=os.read(read_fd,64).decode().strip()
            if not number.isdigit() or display.poll() is not None:raise RuntimeError('No owned display; refusing fallback.')
            environment=dict(os.environ,DISPLAY=':'+number)
            subprocess.run([str(java),'-Duser.home='+str(root/'home'),'-cp',str(jar)+':'+str(classes),'net.runelite.client.soloscape.launcher.NativeLauncherProbe',str(root)],env=environment,pass_fds=(guard.fileno(),),check=True,timeout=90)
            print('Private launcher evidence:',root)
        finally:
            os.close(read_fd)
            display.terminate()
            try:display.wait(timeout=5)
            except subprocess.TimeoutExpired:
                display.kill();display.wait(timeout=5)  # Only our owned display, no game/save process.


if __name__=='__main__':main()
