// Dev helper: render selected frames into a contact sheet PNG.
// node tools/snap.js out.png 100,200,300 [scale]
const path = require('path');
const { spawnSync } = require('child_process');
const root = path.join(__dirname, '..', 'js');
['assets.js', 'engine.js', 'game.js'].forEach((f) => require(path.join(root, f)));
const MA = globalThis.MA;
MA.loadTitle();
const out = process.argv[2] || 'snap.png';
let frames = (process.argv[3] || '100').split(',').map(Number);
const sc = Number(process.argv[4] || 2);
const cols = Math.min(frames.length, Number(process.argv[5] || 3));
const rows = Math.ceil(frames.length / cols);
const W = 320, H = 180;
const sheet = new Uint8Array(W * cols * H * rows * 4);
const g = new MA.Game();
const buf = new MA.Buf(W, H);
const rgba = new Uint8Array(W * H * 4);
const want = new Map(frames.map((f, i) => [f, i]));
const maxF = Math.max(...frames);
let f = 0;
while (f <= maxF && !g.done) {
  g.step();
  if (want.has(f)) {
    g.render(buf);
    MA.toRGBA(buf, rgba, g.fadeLevel());
    const i = want.get(f), cx = (i % cols) * W, cy = Math.floor(i / cols) * H;
    for (let y = 0; y < H; y++) sheet.set(rgba.subarray(y * W * 4, (y + 1) * W * 4), ((cy + y) * W * cols + cx) * 4);
    console.error('frame', f, 'scene', g.scene, 'cam', Math.round(g.cam), 'actors', g.actors.map((a) => a.kind + ':' + a.state + ':' + Math.round(a.x) + ',' + Math.round(a.y) + ' hp' + a.hp).join(' '));
  }
  f++;
}
if (g.done) console.error('sim done at frame', g.frame);
const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W * cols}x${H * rows}`, '-i', '-',
  '-vf', `scale=${W * cols * sc}:${H * rows * sc}:flags=neighbor`, out], { input: Buffer.from(sheet) });
if (r.status) console.error(String(r.stderr));
