// Dev helper: plays the game with a simple bot to check that the stage can be completed.
// node tools/playtest.js [sheet.png] [frames,to,snap] [seed]
const path = require('path');
const { spawnSync } = require('child_process');
['assets.js', 'engine.js', 'game.js'].forEach((f) => require(path.join(__dirname, '..', 'js', f)));
const MA = globalThis.MA; MA.loadTitle();
const out = process.argv[2];
const snaps = (process.argv[3] || '').split(',').filter(Boolean).map(Number);
const g = new MA.Game({ mode: 'play' });
const W = 320, H = 180, cols = 3, rows = Math.max(1, Math.ceil(snaps.length / cols));
const sheet = new Uint8Array(W * cols * H * rows * 4), buf = new MA.Buf(W, H), rgba = new Uint8Array(W * H * 4);
let deaths = 0, lastLives = 3, lastScene = '';
for (let f = 0; f < 30000 && !g.restart; f++) {
  const I = g.input; for (const k in I) I[k] = false;
  const h = g.human;
  if (g.scene !== 'street' && g.scene !== 'venue') { if (f % 40 === 0) I.attack = true; }
  else if (h) {
    if (g.contT > 0) { if (f % 30 === 0) I.start = true; }
    const es = g.enemies().filter((e) => !e.busy() && e.state !== 'leap' && e.state !== 'script');
    let tx = null, ty = null;
    if (g.doorHint) { tx = 1072; ty = 124; }
    else if (es.length) {
      es.sort((a, b) => Math.abs(a.x - h.x) - Math.abs(b.x - h.x));
      const e = es[0]; const side = h.x < e.x ? -1 : 1; tx = e.x + side * (18 + (e.scale - 1) * 24); ty = e.y;
      if (Math.abs(h.x - tx) < 4 && Math.abs(h.y - ty) < 3) {
        I.left = e.x < h.x && h.dir > 0; I.right = e.x > h.x && h.dir < 0;
        if (f % 6 < 3) I.attack = true;
        if (h.ai.spCool <= 0 && f % 50 === 0) I.special = true;
        if (f % 200 === 7) I.jump = true;
        tx = null;
      }
    } else if (g.showGo) { tx = h.x + 40; ty = 140; }
    if (tx !== null) { I.left = tx < h.x - 2; I.right = tx > h.x + 2; I.up = ty < h.y - 2; I.down = ty > h.y + 2; }
    if (h.state === 'jump' && h.z > 8) I.attack = true;
    if (h.lives < lastLives) deaths++;
    lastLives = h.lives;
  }
  g.step();
  if (g.scene !== lastScene) { console.log(String(g.frame).padStart(6), (g.frame / 60).toFixed(1).padStart(6) + 's', g.scene, h ? `hp${h.hp} lives${h.lives} score${h.score}` : ''); lastScene = g.scene; }
  const si = snaps.indexOf(g.frame);
  if (si >= 0) {
    g.render(buf); MA.toRGBA(buf, rgba, g.fadeLevel());
    const cx = (si % cols) * W, cy = Math.floor(si / cols) * H;
    for (let y = 0; y < H; y++) sheet.set(rgba.subarray(y * W * 4, (y + 1) * W * 4), ((cy + y) * W * cols + cx) * 4);
  }
}
const h = g.human;
console.log('END frame', g.frame, (g.frame / 60).toFixed(1) + 's', 'restart', !!g.restart, 'scene', g.scene, h ? `hp${h.hp} lives${h.lives} score${h.score} deaths${deaths}` : '');
if (out && snaps.length) spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W * cols}x${H * rows}`, '-i', '-', '-vf', `scale=${W * cols * 2}:${H * rows * 2}:flags=neighbor`, out], { input: Buffer.from(sheet) });
