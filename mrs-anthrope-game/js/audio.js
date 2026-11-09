// MRS. ANTHROPE - chiptune synthesizer. Renders music + SFX from the game's event list.
// Pure JS (works in Node and browser). Output: stereo Float32Arrays.
(function (root) {
  'use strict';
  var MA = root.MA = root.MA || {};
  var SR = 44100;

  function mtof(m) { return 440 * Math.pow(2, (m - 69) / 12); }
  function Noise(seed) { var s = seed >>> 0 || 1; return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) / 4294967296) * 2 - 1; }; }

  function Mixer(seconds) {
    this.n = Math.ceil(seconds * SR);
    this.L = new Float32Array(this.n); this.R = new Float32Array(this.n);
  }
  Mixer.prototype.add = function (i, v, pan) {
    if (i < 0 || i >= this.n) return;
    pan = pan || 0;
    this.L[i] += v * (1 - pan) ; this.R[i] += v * (1 + pan);
  };

  // ---------------------------------------------------------- instruments
  // generic voice: fn(t, k) -> sample, env applied by caller
  function render(mx, t0, dur, vol, pan, fn, env) {
    var i0 = Math.floor(t0 * SR), n = Math.floor(dur * SR);
    for (var k = 0; k < n; k++) {
      var t = k / SR;
      var e = env ? env(t, dur) : 1;
      if (e < 0.0005 && t > 0.02) continue;
      mx.add(i0 + k, fn(t, k) * e * vol, pan);
    }
  }
  function adsr(a, d, s, r) {
    return function (t, dur) {
      var e;
      if (t < a) e = t / a;
      else if (t < a + d) e = 1 - (1 - s) * ((t - a) / d);
      else e = s;
      if (t > dur - r) e *= Math.max(0, (dur - t) / r);
      return e;
    };
  }
  function expEnv(tau, release) {
    release = release || 0.01;
    return function (t, dur) { var e = Math.exp(-t / tau); if (t > dur - release) e *= Math.max(0, (dur - t) / release); return e; };
  }
  function pulseFn(freq, duty, vib, slide) {
    var ph = 0;
    return function (t) {
      var f = freq * (slide ? Math.pow(2, slide * t) : 1);
      if (vib && t > 0.12) f *= 1 + Math.sin(t * 2 * Math.PI * 5.5) * vib;
      ph += f / SR; ph -= Math.floor(ph);
      return ph < duty ? 0.5 : -0.5;
    };
  }
  function triFn(freq, slide) {
    var ph = 0;
    return function (t) {
      var f = freq * (slide ? Math.pow(2, slide * t) : 1);
      ph += f / SR; ph -= Math.floor(ph);
      // 4-bit quantised triangle like the NES
      var v = ph < 0.5 ? ph * 4 - 1 : 3 - ph * 4;
      return Math.round(v * 7.5) / 7.5 * 0.5;
    };
  }
  function sawFn(freq, vib, slide) {
    var ph = 0;
    return function (t) {
      var f = freq * (slide ? Math.pow(2, slide * t) : 1);
      if (vib) f *= 1 + Math.sin(t * 2 * Math.PI * 7) * vib;
      ph += f / SR; ph -= Math.floor(ph);
      return ph - 0.5;
    };
  }
  function noiseFn(seed, rate, lp) {
    var nz = Noise(seed), hold = 0, cnt = 0, y = 0;
    var period = Math.max(1, Math.round(SR / (rate || SR)));
    return function () {
      if (cnt-- <= 0) { hold = nz(); cnt = period - 1; }
      if (lp) { y += (hold - y) * lp; return y; }
      return hold;
    };
  }

  function guitar(mx, t0, dur, root, muted, vol, pan) {
    var f = mtof(root);
    var a = pulseFn(f * 1.002, 0.5), b = pulseFn(f * 1.4983, 0.25), c = pulseFn(f * 2.004, 0.5), d = pulseFn(f * 0.998, 0.125);
    var env = muted ? expEnv(0.055, 0.01) : adsr(0.004, 0.25, 0.6, 0.04);
    var lp = 0, cut = muted ? 0.18 : 0.45;
    render(mx, t0, dur, vol, pan, function (t) {
      var s = (a(t) + b(t) * 0.8 + c(t) * 0.5 + d(t) * 0.5) * 2.2;
      s = Math.tanh(s * 1.6);
      lp += (s - lp) * cut;
      return lp * 0.7;
    }, env);
  }
  function bass(mx, t0, dur, root, vol) {
    render(mx, t0, dur, vol, 0, triFn(mtof(root)), adsr(0.002, 0.05, 0.85, 0.02));
  }
  function lead(mx, t0, dur, note, vol, pan, duty) {
    render(mx, t0, dur, vol, pan, pulseFn(mtof(note), duty || 0.25, 0.012), adsr(0.004, 0.08, 0.7, 0.03));
  }
  function kick(mx, t0, vol) {
    var ph = 0;
    render(mx, t0, 0.16, vol, 0, function (t) {
      var f = 50 + 110 * Math.exp(-t / 0.025);
      ph += f / SR; ph -= Math.floor(ph);
      var v = ph < 0.5 ? ph * 4 - 1 : 3 - ph * 4;
      return v * 0.9 + (t < 0.004 ? 0.6 : 0);
    }, expEnv(0.06));
  }
  function snare(mx, t0, vol, seed) {
    var n = noiseFn(seed || 7, 22000), ph = 0;
    render(mx, t0, 0.18, vol, 0, function (t) {
      ph += 190 / SR; ph -= Math.floor(ph);
      return n() * 0.7 + (ph < 0.5 ? 0.25 : -0.25) * Math.exp(-t / 0.03);
    }, expEnv(0.055));
  }
  function hat(mx, t0, vol, open, seed) {
    var n = noiseFn(seed || 3, 44100), prev = 0;
    render(mx, t0, open ? 0.2 : 0.05, vol, 0.25, function () { var x = n(); var y = x - prev; prev = x; return y * 0.5; }, expEnv(open ? 0.07 : 0.014));
  }
  function crash(mx, t0, vol, seed) {
    var n = noiseFn(seed || 11, 30000), prev = 0;
    render(mx, t0, 1.4, vol, -0.2, function () { var x = n(); var y = x - prev * 0.6; prev = x; return y * 0.5; }, expEnv(0.45));
  }

  // ---------------------------------------------------------------- songs
  var E2 = 40, F2 = 41, Fs2 = 42, G2 = 43, A2 = 45, Bb2 = 46, B2 = 47, C3 = 48, D3 = 50;
  var SONGS = {
    title: {
      bpm: 104,
      bars: [[E2], [C3], [D3], [B2]],
      play: function (mx, ctx) { // ctx: bar index, t (bar start), beat (sec), root
        var b = ctx.beat, r = ctx.root, t = ctx.t, i;
        for (i = 0; i < 8; i++) guitar(mx, t + i * b / 2, b / 2, r, i % 4 !== 0, 0.22, -0.3);
        guitar(mx, t, b * 1.9, r + 12, false, 0.09, 0.3);
        for (i = 0; i < 8; i++) bass(mx, t + i * b / 2, b / 2 * 0.9, r + 12, 0.5);
        kick(mx, t, 0.8); kick(mx, t + b * 1.5, 0.7); kick(mx, t + b * 2.5, 0.6);
        snare(mx, t + b * 2, 0.5, ctx.bar);
        for (i = 0; i < 4; i++) hat(mx, t + i * b, 0.25, i === 3);
        if (ctx.bar % 4 === 0) crash(mx, t, 0.3, ctx.bar + 5);
        var mel = [[64, 67, 71, 69], [67, 64, 62, 64], [66, 69, 74, 72], [71, 69, 67, 66]][ctx.bar % 4];
        if (ctx.loop > 0 || ctx.bar >= 0) for (i = 0; i < 4; i++) lead(mx, t + i * b, b * 0.92, mel[i] + 12, 0.11, 0.2, 0.25);
      }
    },
    stage: {
      bpm: 168,
      bars: [[E2], [E2], [C3], [D3], [E2], [E2], [G2], [D3]],
      lead: [
        [71, 0, 71, 69, 67, 0, 64, 0], [67, 69, 71, 0, 74, 0, 71, 0], [72, 0, 71, 69, 67, 0, 69, 0], [66, 0, 67, 69, 66, 0, 62, 0],
        [76, 0, 74, 71, 0, 0, 67, 69], [71, 0, 0, 0, 76, 0, 74, 0], [74, 0, 71, 67, 0, 0, 71, 0], [69, 0, 66, 62, 0, 0, 66, 69]
      ],
      play: function (mx, ctx) {
        var b = ctx.beat, r = ctx.root, t = ctx.t, i;
        var e = b / 2;
        for (i = 0; i < 8; i++) guitar(mx, t + i * e, e, r, !(i === 0 || i === 3 || i === 6), 0.2, -0.35);
        for (i = 0; i < 8; i++) guitar(mx, t + i * e, e, r + 12, i % 2 === 1, 0.07, 0.35);
        for (i = 0; i < 8; i++) bass(mx, t + i * e, e * 0.85, r + 12, 0.48);
        // punk beat
        kick(mx, t, 0.8); kick(mx, t + e * 3, 0.6); kick(mx, t + b * 2, 0.8); kick(mx, t + e * 7, 0.5);
        snare(mx, t + b, 0.48, ctx.bar * 3); snare(mx, t + b * 3, 0.48, ctx.bar * 3 + 1);
        for (i = 0; i < 8; i++) hat(mx, t + i * e, i % 2 ? 0.14 : 0.2, false, i + ctx.bar);
        if (ctx.bar % 8 === 0) crash(mx, t, 0.32, ctx.bar);
        if (ctx.bar % 8 === 7) { snare(mx, t + e * 6, 0.4, 99); snare(mx, t + e * 7, 0.45, 98); }
        var withLead = ctx.full || (Math.floor(ctx.absBar / 8) % 2 === 1);
        if (withLead) {
          var L = SONGS.stage.lead[ctx.bar % 8];
          for (i = 0; i < 8; i++) if (L[i]) {
            var len = 1; while (i + len < 8 && !L[i + len]) len++;
            lead(mx, t + i * e, e * len * 0.95, L[i], 0.12, 0.25, 0.25);
            lead(mx, t + i * e + 0.012, e * len * 0.9, L[i] - 12, 0.05, -0.25, 0.5);
          }
        }
      }
    },
    boss: {
      bpm: 184,
      bars: [[E2, E2, E2, F2], [E2, E2, G2, Fs2], [E2, E2, E2, F2], [Bb2, A2, G2, F2]],
      play: function (mx, ctx) {
        var b = ctx.beat, t = ctx.t, i, roots = ctx.roots;
        for (i = 0; i < 4; i++) {
          var r = roots[i], bt = t + i * b;
          // gallop: 8th + two 16ths
          guitar(mx, bt, b / 2, r, i !== 0, 0.2, -0.35);
          guitar(mx, bt + b / 2, b / 4, r, true, 0.2, -0.35);
          guitar(mx, bt + b * 3 / 4, b / 4, r, true, 0.2, -0.35);
          guitar(mx, bt, b * 0.95, r + 12, true, 0.06, 0.35);
          bass(mx, bt, b / 2 * 0.9, r + 12, 0.45); bass(mx, bt + b / 2, b / 4 * 0.9, r + 12, 0.4); bass(mx, bt + b * 3 / 4, b / 4 * 0.9, r + 12, 0.4);
          kick(mx, bt, 0.7); kick(mx, bt + b / 2, 0.5); kick(mx, bt + b * 3 / 4, 0.5);
          if (i % 2 === 1) snare(mx, bt, 0.5, ctx.bar * 4 + i);
          hat(mx, bt + b / 2, 0.16, false, i);
        }
        if (ctx.bar % 4 === 0) crash(mx, t, 0.3, ctx.bar);
        if (Math.floor(ctx.absBar / 4) % 2 === 1) {
          var mel = [[76, 77, 76, 74], [76, 77, 79, 78], [83, 82, 81, 79], [82, 81, 79, 77]][ctx.bar % 4];
          for (i = 0; i < 4; i++) lead(mx, t + i * b, b * 0.9, mel[i], 0.09, 0.25, 0.125);
        }
      }
    },
    clear: {
      bpm: 150, once: true,
      bars: [[E2], [C3], [D3], [E2]],
      play: function (mx, ctx) {
        var b = ctx.beat, t = ctx.t, r = ctx.root, i;
        if (ctx.bar < 3) {
          guitar(mx, t, b * 1.5, r, false, 0.22, -0.3); guitar(mx, t + b * 1.5, b * 0.5, r, true, 0.2, -0.3);
          guitar(mx, t + b * 2, b * 2, r, false, 0.22, -0.3);
          bass(mx, t, b * 1.5, r + 12, 0.45); bass(mx, t + b * 2, b * 2, r + 12, 0.45);
          kick(mx, t, 0.8); snare(mx, t + b, 0.45, 1); kick(mx, t + b * 2, 0.8); snare(mx, t + b * 3, 0.45, 2);
          var mel = [[64, 67, 71, 76], [72, 71, 72, 76], [74, 76, 78, 81]][ctx.bar];
          for (i = 0; i < 4; i++) lead(mx, t + i * b, b * 0.9, mel[i] + 12, 0.12, 0.2, 0.25);
        } else {
          guitar(mx, t, b * 4, E2, false, 0.24, -0.3); guitar(mx, t, b * 4, E2 + 12 + 4, false, 0.08, 0.3);
          bass(mx, t, b * 3.5, E2 + 12, 0.45);
          lead(mx, t, b * 3.5, 88, 0.12, 0.2, 0.25); lead(mx, t, b * 3.5, 80, 0.07, -0.2, 0.5);
          kick(mx, t, 0.9); crash(mx, t, 0.4, 3);
        }
      }
    }
  };
  SONGS.concert = { bpm: 168, bars: SONGS.stage.bars, full: true, crowd: true, play: SONGS.stage.play };

  function renderSong(mx, name, t0, t1, loopMode) {
    var S = SONGS[name]; if (!S) return;
    var beat = 60 / S.bpm, barLen = beat * 4;
    var nb = S.bars.length;
    for (var k = 0; ; k++) {
      var t = t0 + k * barLen;
      if (t >= t1 - 0.01) break;
      if (S.once && k >= nb) break;
      var roots = S.bars[k % nb];
      // render into a temp mixer so we can cut the song exactly at t1
      S.play(mx, { t: t, beat: beat, bar: k % nb, absBar: k, loop: Math.floor(k / nb), root: roots[0], roots: roots, full: S.full });
    }
    if (S.crowd) crowdNoise(mx, t0, t1 - t0, loopMode);
  }
  function crowdNoise(mx, t0, dur, flat) {
    var n = noiseFn(1234, 44100, 0.08), n2 = noiseFn(77, 44100, 0.02);
    render(mx, t0, dur, 0.5, 0, function (t) {
      var swell = 0.55 + 0.45 * Math.sin(t * 0.9) * Math.sin(t * 0.37 + 1);
      return (n() * 0.6 + n2() * 0.8) * swell;
    }, flat ? null : function (t, d) { return Math.min(1, t / 0.6) * Math.min(1, (d - t) / 1.0); });
  }

  // ------------------------------------------------------------------ SFX
  var sfxSeed = 1;
  function sfx(mx, name, t0) {
    var s = sfxSeed++;
    var n, ph = 0;
    switch (name) {
      case 'hit':
        n = noiseFn(s, 16000);
        render(mx, t0, 0.09, 0.55, 0, function (t) { return n() * 0.7; }, expEnv(0.025));
        render(mx, t0, 0.08, 0.6, 0, triFn(150 + (s % 5) * 12, -6), expEnv(0.03));
        break;
      case 'heavy':
        n = noiseFn(s, 9000);
        render(mx, t0, 0.18, 0.65, 0, function () { return n() * 0.8; }, expEnv(0.05));
        render(mx, t0, 0.16, 0.8, 0, triFn(110, -5), expEnv(0.06));
        break;
      case 'smash':
        guitar(mx, t0, 0.7, E2, false, 0.32, 0);
        guitar(mx, t0, 0.7, E2 + 6, false, 0.16, 0);
        crash(mx, t0, 0.45, s);
        n = noiseFn(s, 7000);
        render(mx, t0, 0.22, 0.6, 0, function () { return n(); }, expEnv(0.06));
        break;
      case 'swing':
        n = noiseFn(s, 44100);
        var y = 0;
        render(mx, t0, 0.13, 0.32, 0, function (t) { var c = 0.04 + t * 3; y += (n() - y) * Math.min(0.9, c); return y; }, adsr(0.03, 0.05, 0.6, 0.05));
        break;
      case 'land':
        render(mx, t0, 0.14, 0.6, 0, triFn(90, -4), expEnv(0.05));
        n = noiseFn(s, 4000);
        render(mx, t0, 0.08, 0.35, 0, function () { return n(); }, expEnv(0.03));
        break;
      case 'thud':
        render(mx, t0, 0.35, 0.9, 0, triFn(70, -3), expEnv(0.1));
        n = noiseFn(s, 3000);
        render(mx, t0, 0.25, 0.55, 0, function () { return n(); }, expEnv(0.07));
        break;
      case 'scream':
        var a = sawFn(233, 0.03, -0.35), b = pulseFn(349, 0.25, 0.02, -0.35), nz = noiseFn(s, 12000), lp = 0;
        render(mx, t0, 0.85, 0.42, 0, function (t) {
          var v = a(t) * 1.4 + b(t) * 0.8 + nz() * 0.35;
          v = Math.tanh(v * 3);
          lp += (v - lp) * 0.35;
          return lp * 0.8;
        }, adsr(0.02, 0.1, 0.85, 0.2));
        break;
      case 'select':
        [76, 83, 88].forEach(function (m, i) { lead(mx, t0 + i * 0.06, 0.06, m, 0.22, 0, 0.5); });
        lead(mx, t0 + 0.18, 0.35, 88, 0.2, 0, 0.25);
        break;
      case 'go':
        lead(mx, t0, 0.07, 81, 0.18, 0, 0.5); lead(mx, t0 + 0.09, 0.14, 86, 0.18, 0, 0.5);
        break;
      case 'card':
        guitar(mx, t0, 1.2, E2, false, 0.3, 0); kick(mx, t0, 0.9); crash(mx, t0, 0.4, s);
        break;
      case 'door':
        n = noiseFn(s, 2500, 0.2);
        render(mx, t0, 0.4, 0.35, 0, function (t) { return n() * (0.6 + 0.4 * Math.sin(t * 90)); }, adsr(0.05, 0.1, 0.7, 0.15));
        render(mx, t0 + 0.3, 0.15, 0.5, 0, triFn(80, -3), expEnv(0.05));
        break;
      case 'ko':
        n = noiseFn(s, 6000, 0.25);
        render(mx, t0, 2.2, 0.9, 0, function () { return n() * 1.4; }, expEnv(0.5));
        render(mx, t0, 1.2, 0.9, 0, triFn(60, -1.5), expEnv(0.3));
        render(mx, t0, 0.6, 0.18, 0, pulseFn(880, 0.5, 0, -3), expEnv(0.2));
        crash(mx, t0, 0.5, s);
        break;
      case 'pickup':
        [72, 76, 79, 84, 88].forEach(function (m, i) { lead(mx, t0 + i * 0.05, 0.07, m, 0.2, 0, 0.5); });
        break;
      case 'tick':
        render(mx, t0, 0.025, 0.12, 0, pulseFn(1760, 0.5), null);
        break;
    }
  }

  // events: [{f, type, name}], fps
  MA.renderAudio = function (events, totalFrames, fps) {
    fps = fps || 60;
    sfxSeed = 1;
    var total = totalFrames / fps + 2.5;
    var music = new Mixer(total), fx = new Mixer(total);
    var musicEv = events.filter(function (e) { return e.type === 'music'; });
    musicEv.forEach(function (e, i) {
      if (!e.name) return;
      var t0 = e.f / fps, t1 = i + 1 < musicEv.length ? musicEv[i + 1].f / fps : total;
      var tmp = new Mixer(total);
      renderSong(tmp, e.name, t0, t1 + 0.6);
      // hard cut at t1 with short fade
      var i0 = Math.floor(t0 * SR), i1 = Math.min(tmp.n, Math.floor(t1 * SR)), fade = Math.floor(0.03 * SR);
      for (var k = i0; k < Math.min(tmp.n, i1 + fade); k++) {
        var g = k < i1 ? 1 : 1 - (k - i1) / fade;
        music.L[k] += tmp.L[k] * g; music.R[k] += tmp.R[k] * g;
      }
    });
    events.forEach(function (e) { if (e.type === 'sfx') sfx(fx, e.name, e.f / fps); });
    var L = new Float32Array(music.n), R = new Float32Array(music.n);
    var lpL = 0, lpR = 0;
    for (var k = 0; k < music.n; k++) {
      var l = music.L[k] * 0.55 + fx.L[k] * 0.7, r = music.R[k] * 0.55 + fx.R[k] * 0.7;
      lpL += (l - lpL) * 0.6; lpR += (r - lpR) * 0.6;
      L[k] = Math.tanh(lpL * 1.7) * 0.9; R[k] = Math.tanh(lpR * 1.7) * 0.9;
    }
    var len = Math.ceil(totalFrames / fps * SR);
    return { sr: SR, L: L.subarray(0, len), R: R.subarray(0, len) };
  };

  // ---------------------------------------------------- realtime helpers (browser game)
  function master(x, gain) { return Math.tanh(x * gain) * 0.9; }
  MA.SFX_NAMES = ['hit', 'heavy', 'smash', 'swing', 'land', 'thud', 'scream', 'select', 'go', 'card', 'door', 'ko', 'tick', 'pickup'];
  MA.renderSfxClip = function (name) {
    var mx = new Mixer(2.6);
    sfx(mx, name, 0.005);
    var end = mx.n;
    while (end > 1000 && Math.abs(mx.L[end - 1]) < 1e-4 && Math.abs(mx.R[end - 1]) < 1e-4) end--;
    var L = new Float32Array(end), R = new Float32Array(end);
    for (var k = 0; k < end; k++) { L[k] = master(mx.L[k], 1.2); R[k] = master(mx.R[k], 1.2); }
    return { sr: SR, L: L, R: R };
  };
  var LOOP_BARS = { title: 8, stage: 16, boss: 8, concert: 8, clear: 4 };
  // returns a seamlessly looping buffer (tails wrap around to the start); 'clear' plays once
  MA.renderSongLoop = function (name) {
    var S = SONGS[name], beat = 60 / S.bpm, len = LOOP_BARS[name] * beat * 4;
    var mx = new Mixer(len + 3);
    renderSong(mx, name, 0, len - 0.001, !S.once);
    var n = S.once ? mx.n : Math.round(len * SR);
    var L = new Float32Array(n), R = new Float32Array(n);
    for (var k = 0; k < mx.n; k++) {
      var j = S.once ? k : k % n;
      if (j >= n) continue;
      L[j] += mx.L[k]; R[j] += mx.R[k];
    }
    for (k = 0; k < n; k++) { L[k] = master(L[k], 0.95); R[k] = master(R[k], 0.95); }
    return { sr: SR, L: L, R: R, loop: !S.once };
  };

  MA.encodeWav = function (a) {
    var n = a.L.length, buf = new ArrayBuffer(44 + n * 4), v = new DataView(buf);
    function str(o, s) { for (var i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); }
    str(0, 'RIFF'); v.setUint32(4, 36 + n * 4, true); str(8, 'WAVE'); str(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true);
    v.setUint32(24, a.sr, true); v.setUint32(28, a.sr * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 16, true);
    str(36, 'data'); v.setUint32(40, n * 4, true);
    for (var i = 0, o = 44; i < n; i++, o += 4) {
      v.setInt16(o, Math.max(-1, Math.min(1, a.L[i])) * 32767, true);
      v.setInt16(o + 2, Math.max(-1, Math.min(1, a.R[i])) * 32767, true);
    }
    return buf;
  };
})(typeof window !== 'undefined' ? window : globalThis);
