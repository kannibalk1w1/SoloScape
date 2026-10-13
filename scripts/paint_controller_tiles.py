#!/usr/bin/env python3
"""Generate a local coordinate-grid painter for optional controller avoidance tiles."""
import argparse
from pathlib import Path

HTML = '''<!doctype html><meta charset="utf-8"><title>SoloScape controller tile painter</title>
<style>body{font:16px system-ui;background:#222;color:#eee;margin:24px}canvas{border:1px solid #aaa;touch-action:none}button,input{font:inherit;margin:6px}p{max-width:800px}</style>
<h1>Controller tile painter</h1><p>Paint awkward floor tiles red to exclude them from direct controller movement. Native collision still applies. Use coordinates from the in-game debug guide; this grid does not show game geometry. Restart the world after changing the avoidance file.</p>
<label>West X <input id="x" type="number" value="3200" min="0" max="16352"></label>
<label>South Y <input id="y" type="number" value="3200" min="0" max="16352"></label>
<label>Plane <input id="z" type="number" value="0" min="0" max="3"></label>
<button id="view">Move grid</button><label>Import <input id="file" type="file" accept=".txt"></label><button id="save">Export tiles</button>
<p id="status">Drag to paint; start on a red tile to erase. North is up.</p><canvas id="grid" width="768" height="768"></canvas>
<script>
const canvas=document.getElementById('grid'),ctx=canvas.getContext('2d'),tiles=new Set();let west=3200,south=3200,plane=0,drag=false,erase=false;
const key=(x,y,z)=>`${x},${y},${z}`;
function draw(){ctx.clearRect(0,0,768,768);for(let row=0;row<32;row++)for(let col=0;col<32;col++){ctx.fillStyle=tiles.has(key(west+col,south+31-row,plane))?'#c55342':(row+col)%2?'#444':'#393939';ctx.fillRect(col*24,row*24,23,23)}document.getElementById('status').textContent=`${tiles.size} marked tiles · X ${west}–${west+31}, Y ${south}–${south+31}, plane ${plane}. Drag to paint/erase.`}
function cell(e){const rect=canvas.getBoundingClientRect();let col=Math.floor((e.clientX-rect.left)*768/rect.width/24),row=Math.floor((e.clientY-rect.top)*768/rect.height/24);return col>=0&&col<32&&row>=0&&row<32?key(west+col,south+31-row,plane):null}
function paint(e){let tile=cell(e);if(!tile)return;if(erase)tiles.delete(tile);else if(tiles.size<4096)tiles.add(tile);draw()}
canvas.onpointerdown=e=>{const tile=cell(e);if(!tile)return;drag=true;erase=tiles.has(tile);canvas.setPointerCapture(e.pointerId);paint(e)};canvas.onpointermove=e=>{if(drag)paint(e)};canvas.onpointerup=canvas.onpointercancel=()=>drag=false;
document.getElementById('view').onclick=()=>{let a=Number(document.getElementById('x').value),b=Number(document.getElementById('y').value),c=Number(document.getElementById('z').value);if(!Number.isInteger(a)||!Number.isInteger(b)||!Number.isInteger(c)||a<0||a>16352||b<0||b>16352||c<0||c>3)return alert('Enter valid coordinates.');west=a;south=b;plane=c;draw()};
document.getElementById('save').onclick=()=>{const url=URL.createObjectURL(new Blob(['# SoloScape controller avoidance: x,y,plane\\n'+[...tiles].sort().join('\\n')+'\\n'],{type:'text/plain'}));const a=document.createElement('a');a.href=url;a.download='controller-avoid-tiles.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
document.getElementById('file').onchange=async e=>{const file=e.target.files[0];if(!file)return;if(file.size>262144)return alert('File too large.');const lines=(await file.text()).split(/\\r?\\n/).map(s=>s.trim()).filter(s=>s&&!s.startsWith('#'));if(lines.length>4096||lines.some(s=>{const v=s.split(',').map(Number);return v.length!==3||v.some(n=>!Number.isInteger(n))||v[0]<0||v[0]>16383||v[1]<0||v[1]>16383||v[2]<0||v[2]>3}))return alert('Invalid avoidance file.');tiles.clear();for(const line of lines)tiles.add(line.split(',').map(Number).join(','));draw()};draw();
</script>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.runtime/controller-tile-painter.html'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(HTML)
    print(args.output.resolve())


if __name__ == '__main__':
    main()
