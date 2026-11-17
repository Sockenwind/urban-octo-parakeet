#!/usr/bin/env node
// Renders the MRS. ANTHROPE stage-1 "gameplay recording" to an MP4 file.
//   node render.js                       -> out/mrs-anthrope-stage1.mp4 (1920x1080, 60 fps, with audio)
//   node render.js --scale 4 --out x.mp4 -> 1280x720
//   node render.js --wav                 -> only write out/soundtrack.wav
// Requires ffmpeg on PATH.
'use strict';
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

['assets.js', 'engine.js', 'game.js', 'audio.js'].forEach((f) => require(path.join(__dirname, 'js', f)));
const MA = globalThis.MA;
MA.loadTitle();

const args = process.argv.slice(2);
function opt(name, def) { const i = args.indexOf('--' + name); return i >= 0 ? args[i + 1] : def; }
const scale = Number(opt('scale', 6));
const fps = 60;
const crf = opt('crf', '18');
const outDir = path.join(__dirname, 'out');
const out = path.resolve(opt('out', path.join(outDir, 'mrs-anthrope-stage1.mp4')));
const wavPath = path.join(outDir, 'soundtrack.wav');
fs.mkdirSync(outDir, { recursive: true });

// ---- pass 1: simulate to collect the sound events
let t = Date.now();
const sim = new MA.Game();
while (!sim.done) sim.step();
const total = sim.frame;
console.log(`simulated ${total} frames (${(total / fps).toFixed(1)} s) in ${Date.now() - t} ms`);

t = Date.now();
const audio = MA.renderAudio(sim.events, total, fps);
fs.writeFileSync(wavPath, Buffer.from(MA.encodeWav(audio)));
console.log(`audio rendered in ${Date.now() - t} ms -> ${wavPath}`);
if (args.includes('--wav')) process.exit(0);

// ---- pass 2: render frames and pipe them to ffmpeg
const W = MA.W, H = MA.H;
const ff = spawn('ffmpeg', [
  '-y', '-loglevel', 'error',
  '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(fps), '-i', '-',
  '-i', wavPath,
  '-vf', `scale=${W * scale}:${H * scale}:flags=neighbor`,
  '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', crf, '-pix_fmt', 'yuv420p',
  '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out
], { stdio: ['pipe', 'inherit', 'inherit'] });

const g = new MA.Game();
const buf = new MA.Buf(W, H);
const rgba = new Uint8Array(W * H * 4);
t = Date.now();

function pump() {
  while (!g.done) {
    g.step();
    g.render(buf);
    MA.toRGBA(buf, rgba, g.fadeLevel());
    if (g.frame % 600 === 0) process.stdout.write(`  frame ${g.frame}/${total}\n`);
    const ok = ff.stdin.write(Buffer.from(rgba));
    if (!ok) { ff.stdin.once('drain', pump); return; }
  }
  ff.stdin.end();
}
ff.on('close', (code) => {
  console.log(`\nffmpeg exited with ${code}; ${g.frame} frames in ${((Date.now() - t) / 1000).toFixed(1)} s -> ${out}`);
  process.exit(code);
});
pump();
