// Real-clock Chromium probe. CDP pipe avoids virtual time, external npm dependencies
// and a remotely reachable debugging port. Only original synthetic geometry is captured.
import {spawn, execFileSync} from 'node:child_process';
import {mkdtempSync, openSync, closeSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const [browser, url, output] = process.argv.slice(2);
if (!browser || !url || !output) throw new Error('browser_probe.mjs CHROMIUM LOOPBACK_URL OUTPUT');
const address = new URL(url);
if (address.hostname !== '127.0.0.1' || address.protocol !== 'http:') throw new Error('Loopback HTTP only');
const profile = mkdtempSync(join(tmpdir(), 'soloscape-material-'));
const log = openSync(join(output, 'chromium.log'), 'w');
const child = spawn(browser, ['--headless=new', '--disable-gpu', '--no-first-run',
    '--remote-debugging-pipe', '--user-data-dir=' + profile],
    {stdio: ['ignore', log, log, 'pipe', 'pipe']});
const pending = new Map();
let sequence = 0, buffer = '';
const deadline = setTimeout(() => { child.kill(); }, 150000);
process.on('SIGTERM', () => child.kill());
child.on('error', error => { for (const p of pending.values()) p.reject(error); });
const exited = new Promise(resolve => child.once('close', code => {
    for (const p of pending.values()) p.reject(new Error('Chromium exited: ' + code));
    resolve();
}));
child.stdio[4].on('data', bytes => {
    buffer += bytes.toString();
    for (let end; (end = buffer.indexOf('\0')) >= 0;) {
        const raw = buffer.slice(0, end); buffer = buffer.slice(end + 1);
        if (!raw) continue;
        const message = JSON.parse(raw), request = pending.get(message.id);
        if (!request) continue;
        pending.delete(message.id);
        if (message.error) request.reject(new Error(JSON.stringify(message.error)));
        else request.resolve(message.result);
    }
});
function command(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
        const id = ++sequence;
        pending.set(id, {resolve, reject});
        child.stdio[3].write(JSON.stringify({id, method, params, sessionId}) + '\0');
    });
}
try {
    const {targetId} = await command('Target.createTarget', {url: 'about:blank'});
    const {sessionId} = await command('Target.attachToTarget', {targetId, flatten: true});
    await command('Page.enable', {}, sessionId);
    await command('Emulation.setDeviceMetricsOverride', {width: 1320, height: 1000, deviceScaleFactor: 1, mobile: false}, sessionId);
    await command('Page.navigate', {url}, sessionId);
    const result = await command('Runtime.evaluate', {
        expression: `new Promise((resolve, reject) => {
            const end = performance.now() + 120000;
            function check() {
                const text = document.getElementById('result')?.textContent;
                if (text && text !== 'WAIT') { resolve(text); return; }
                if (performance.now() > end) { reject(new Error('Material result timeout')); return; }
                setTimeout(check, 50);
            }
            check();
        })`, awaitPromise: true, returnByValue: true,
    }, sessionId);
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    const data = JSON.parse(result.result.value);
    if (!data.raster?.length) throw new Error('Missing material results');
    const dom = await command('Runtime.evaluate', {expression: 'document.documentElement.outerHTML', returnByValue: true}, sessionId);
    writeFileSync(join(output, 'browser-dom.html'), dom.result.value);
    writeFileSync(join(output, 'browser-meta.json'), JSON.stringify({
        clock: 'performance.now with real time; no virtual-time budget',
        browser: execFileSync(browser, ['--version'], {encoding: 'utf8'}).trim(),
        node: process.version, presentation: 'headless Chromium software Canvas; host only',
    }, null, 2));
    const screenshot = await command('Page.captureScreenshot', {format: 'png'}, sessionId);
    writeFileSync(join(output, 'synthetic-material.png'), Buffer.from(screenshot.data, 'base64'));
    console.log('Real-clock browser result captured');
} finally {
    clearTimeout(deadline);
    child.kill();
    await exited;
    closeSync(log);
    rmSync(profile, {recursive: true, force: true});
}
