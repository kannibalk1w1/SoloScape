#!/usr/bin/env python3
"""Run the existing decoded-model WasmGC proof in an ephemeral WebKitGTK view.

Engine compatibility only: no Tauri binary, timing comparison, native game or owner display.
Requires the separately built wasm-decoded-face experiment, PyGObject/WebKit2 4.1 and Xvfb.
"""
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT/'experiments/wasm-decoded-face'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def view(url):
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import GLib, Gtk, WebKit2
    manager = WebKit2.UserContentManager()
    manager.register_script_message_handler('probe')
    result = []

    def received(_manager, message):
        result.append(json.loads(message.get_js_value().to_string()))
        Gtk.main_quit()

    manager.connect('script-message-received::probe', received)
    script = '''const timer = setInterval(() => {
      const r = document.getElementById('result');
      if (r && r.textContent !== 'WAIT') {
        clearInterval(timer);
        window.webkit.messageHandlers.probe.postMessage(JSON.stringify({
          html: document.documentElement.outerHTML, userAgent: navigator.userAgent
        }));
      }
    }, 50);'''
    manager.add_script(WebKit2.UserScript.new(script, WebKit2.UserContentInjectedFrames.TOP_FRAME,
                                             WebKit2.UserScriptInjectionTime.END, None, None))
    data = WebKit2.WebsiteDataManager.new_ephemeral()
    context = WebKit2.WebContext.new_with_website_data_manager(data)
    web = WebKit2.WebView(web_context=context, user_content_manager=manager)
    window = Gtk.Window()
    window.set_default_size(1280, 800)
    window.add(web)
    window.show_all()
    web.load_uri(url)
    GLib.timeout_add_seconds(45, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    window.destroy()
    if not result:
        raise RuntimeError('WebKit did not report a completed proof within 45 seconds')
    doc = result[0]
    doc['webkit'] = '.'.join(str(f()) for f in (WebKit2.get_major_version,
                                               WebKit2.get_minor_version, WebKit2.get_micro_version))
    print(json.dumps(doc))


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path not in ('/index.html', '/bridge.wasm', '/bridge.wasm-runtime.js'):
            self.send_error(404)
            return
        super().do_GET()


def run():
    original = BRIDGE/'build'
    files = [original/'web-out'/n for n in ('index.html', 'bridge.wasm', 'bridge.wasm-runtime.js')]
    files += [original/n for n in ('fixtures.json', 'native.json', 'extracted-jvm.json', 'provenance.json')]
    before = {str(p.relative_to(BRIDGE)): digest(p) for p in files}
    private = ROOT/'.runtime/wasm-webkit'
    private.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='run-', dir=private))
    for name in ('fixtures.json', 'native.json', 'extracted-jvm.json'):
        shutil.copyfile(original/name, output/name)
    (output/'browser').mkdir()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
               functools.partial(Handler, directory=str(original/'web-out')))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    display = None
    read_fd, write_fd = os.pipe()
    try:
        with (output/'xvfb.log').open('w') as log:
            display = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0',
                                        '1280x800x24', '-nolisten', 'tcp'], pass_fds=(write_fd,),
                                       stdout=log, stderr=log)
        os.close(write_fd)
        write_fd = None
        with selectors.DefaultSelector() as selector:
            selector.register(read_fd, selectors.EVENT_READ)
            if not selector.select(10):
                raise RuntimeError('owned Xvfb handshake timed out')
        number = os.read(read_fd, 128).decode().strip()
        if not number.isdigit() or display.poll() is not None:
            raise RuntimeError('owned Xvfb failed')
        env = dict(os.environ, DISPLAY=':'+number, GDK_BACKEND='x11', LIBGL_ALWAYS_SOFTWARE='1')
        with (output/'webkit.stderr').open('w') as log:
            child = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), '--view',
                                   f'http://127.0.0.1:{server.server_port}/index.html'], env=env,
                                   stdout=subprocess.PIPE, stderr=log, text=True, timeout=60, check=True)
        record = json.loads(child.stdout)
        (output/'browser/browser-dom.html').write_text(record.pop('html'))
        checker = BRIDGE/'tools/check_bridge_evidence.py'
        checks = {}
        for mutation in (None, 'decoded-array', 'browser-projected', 'browser-frame', 'palette'):
            args = [sys.executable, '-I', str(checker), '--build', str(output)]
            if mutation:
                args += ['--mutate', mutation]
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            (output/((mutation or 'positive')+'.log')).write_text(result.stdout+result.stderr)
            expected = 1 if mutation else 0
            if result.returncode != expected or (mutation and not result.stdout.startswith('FAIL:')):
                raise RuntimeError('unexpected checker outcome: '+str(mutation))
            checks[mutation or 'positive'] = result.returncode
        if before != {str(p.relative_to(BRIDGE)): digest(p) for p in files}:
            raise RuntimeError('bridge input changed; withholding compatibility report')
        record.update(scope='WebKitGTK engine compatibility only; not Tauri or a performance benchmark',
                      inputs_sha256=before, checker_sha256=digest(checker), probe_sha256=digest(Path(__file__)),
                      checker_outcomes=checks, environment='owned Xvfb, X11, forced software GL',
                      proof=json.loads((output/'checker-summary.json').read_text()))
        (output/'summary.json').write_text(json.dumps(record, indent=2)+'\n')
        print(output)
    finally:
        if write_fd is not None:
            os.close(write_fd)
        os.close(read_fd)
        server.shutdown()
        server.server_close()
        thread.join(5)
        if display is not None and display.poll() is None:
            display.terminate()  # this helper's own Xvfb only; view child already returned
            display.wait(10)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--view':
        view(sys.argv[2])
    elif len(sys.argv) == 1:
        run()
    else:
        raise SystemExit('Usage: python3 experiments/wasm-webkit/probe.py')
