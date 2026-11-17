// Dev helper: run the whole simulation and print scene changes / waves
const path = require('path');
['assets.js', 'engine.js', 'game.js'].forEach((f) => require(path.join(__dirname, '..', 'js', f)));
const MA = globalThis.MA; MA.loadTitle();
const g = new MA.Game();
let last = '', lastN = -1;
while (!g.done && g.frame < 20000) {
  g.step();
  const n = g.enemies().length;
  const key = g.scene + ' cam' + Math.round(g.cam);
  if (g.scene !== last.split(' ')[0] || n !== lastN) {
    console.log(String(g.frame).padStart(5), (g.frame / 60).toFixed(1).padStart(6) + 's', g.scene.padEnd(8), 'cam', Math.round(g.cam), 'enemies', n,
      g.players.map((p) => p.kind + ' hp' + p.hp + ' y' + Math.round(p.y)).join(' '));
    last = key; lastN = n;
  }
}
console.log('END frame', g.frame, (g.frame / 60).toFixed(1) + 's', 'events', g.events.length);
