// MRS. ANTHROPE - 8-bit engine: indexed framebuffer, palette, primitives, pixel font.
// Runs both in the browser and in Node (no DOM needed).
(function (root) {
  'use strict';
  var MA = root.MA = root.MA || {};

  var W = 320, H = 180, TR = 255;
  MA.W = W; MA.H = H; MA.TR = TR;

  // ---------------------------------------------------------------- palette
  var COLORS = [
    ['K', '#000000'], ['k', '#15131e'], ['d', '#2b2b3d'], ['D', '#252940'],
    ['E', '#40445f'], ['G', '#646982'], ['L', '#a5a9bf'], ['W', '#f6ecd6'],
    ['w', '#ffffff'], ['R', '#e3241b'], ['r', '#921712'], ['q', '#4c0d0b'],
    ['N', '#38d63c'], ['n', '#178c22'], ['m', '#0b4514'], ['S', '#f0b385'],
    ['s', '#c47c55'], ['H', '#d0461e'], ['h', '#8c2a10'], ['B', '#6b3b1d'],
    ['b', '#3d2312'], ['Y', '#fadc3c'], ['O', '#f2862a'], ['U', '#3657a8'],
    ['u', '#1d2d66'], ['P', '#e03c96'], ['p', '#7c1a52'], ['V', '#2c1c46'],
    ['v', '#170f28'], ['X', '#6e2c22'], ['x', '#4a1c17'], ['Z', '#34323e'],
    ['z', '#24222d'], ['I', '#5f5d70'], ['i', '#4b495a'], ['C', '#46d0ee'],
    ['c', '#1f6f8c'], ['T', '#ffcf9e'], ['A', '#9a5a2a'], ['F', '#ffe9a8'],
    ['M', '#1c3a22'], ['Q', '#10101a']
  ];
  var PAL = new Uint8Array(256 * 3);
  var C = {};
  COLORS.forEach(function (e, i) {
    C[e[0]] = i;
    PAL[i * 3] = parseInt(e[1].slice(1, 3), 16);
    PAL[i * 3 + 1] = parseInt(e[1].slice(3, 5), 16);
    PAL[i * 3 + 2] = parseInt(e[1].slice(5, 7), 16);
  });
  MA.C = C; MA.PAL = PAL;
  var TITLE_BASE = 64; // title artwork colours live at 64..95
  MA.TITLE_BASE = TITLE_BASE;
  var TITLE_DARK = new Uint8Array(256); // 1 = treat as transparent when used as overlay

  function loadTitle() {
    var t = MA.ASSETS && MA.ASSETS.title;
    if (!t || t.px) return;
    t.pal.forEach(function (hex, i) {
      var r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
      var j = TITLE_BASE + i;
      PAL[j * 3] = r; PAL[j * 3 + 1] = g; PAL[j * 3 + 2] = b;
      TITLE_DARK[j] = (r + g + b < 110) ? 1 : 0;
    });
    var raw;
    if (typeof Buffer !== 'undefined') raw = Buffer.from(t.data, 'base64');
    else {
      var s = atob(t.data); raw = new Uint8Array(s.length);
      for (var i = 0; i < s.length; i++) raw[i] = s.charCodeAt(i);
    }
    t.px = new Uint8Array(raw.length);
    for (var k = 0; k < raw.length; k++) t.px[k] = raw[k] + TITLE_BASE;
  }
  MA.loadTitle = loadTitle;

  // ------------------------------------------------------------------- rng
  function RNG(seed) { this.s = seed >>> 0; }
  RNG.prototype.next = function () {
    var t = (this.s += 0x6D2B79F5) >>> 0;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  RNG.prototype.range = function (a, b) { return a + (b - a) * this.next(); };
  RNG.prototype.int = function (a, b) { return Math.floor(this.range(a, b + 1)); };
  RNG.prototype.pick = function (arr) { return arr[Math.floor(this.next() * arr.length)]; };
  MA.RNG = RNG;
  // stateless hash for static decoration
  MA.hash = function (n) {
    n = (n ^ 61) ^ (n >>> 16); n = n + (n << 3); n = n ^ (n >>> 4);
    n = Math.imul(n, 0x27d4eb2d); n = n ^ (n >>> 15);
    return (n >>> 0) / 4294967296;
  };

  var BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
  MA.BAYER = BAYER;

  // ------------------------------------------------------------- framebuffer
  function Buf(w, h) {
    this.w = w; this.h = h;
    this.px = new Uint8Array(w * h);
    this.remap = null;   // optional Uint8Array(256) colour remap
    this.ox = 0; this.oy = 0;
  }
  MA.Buf = Buf;
  var B = Buf.prototype;

  B.clear = function (c) { this.px.fill(c); };
  B.pset = function (x, y, c) {
    x = (x + this.ox) | 0; y = (y + this.oy) | 0;
    if (x < 0 || y < 0 || x >= this.w || y >= this.h || c === TR) return;
    if (this.remap) c = this.remap[c];
    this.px[y * this.w + x] = c;
  };
  B.get = function (x, y) {
    x = (x + this.ox) | 0; y = (y + this.oy) | 0;
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return TR;
    return this.px[y * this.w + x];
  };
  B.rect = function (x, y, w, h, c) {
    x = Math.round(x); y = Math.round(y);
    var x0 = Math.max(0, x + this.ox), y0 = Math.max(0, y + this.oy);
    var x1 = Math.min(this.w, x + this.ox + w), y1 = Math.min(this.h, y + this.oy + h);
    if (this.remap) c = this.remap[c];
    for (var yy = y0; yy < y1; yy++) {
      var o = yy * this.w;
      for (var xx = x0; xx < x1; xx++) this.px[o + xx] = c;
    }
  };
  // dithered rect: level 0..16
  B.drect = function (x, y, w, h, c, level) {
    x = Math.round(x); y = Math.round(y);
    for (var yy = y; yy < y + h; yy++)
      for (var xx = x; xx < x + w; xx++) {
        var sx = xx + this.ox, sy = yy + this.oy;
        if (BAYER[((sy & 3) << 2) | (sx & 3)] < level) this.pset(xx, yy, c);
      }
  };
  B.hline = function (x0, x1, y, c) { if (x1 < x0) { var t = x0; x0 = x1; x1 = t; } this.rect(x0, y, x1 - x0 + 1, 1, c); };
  B.vline = function (x, y0, y1, c) { if (y1 < y0) { var t = y0; y0 = y1; y1 = t; } this.rect(x, y0, 1, y1 - y0 + 1, c); };

  // thin line
  B.line = function (x0, y0, x1, y1, c) {
    x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
    var dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1, err = dx + dy;
    for (;;) {
      this.pset(x0, y0, c);
      if (x0 === x1 && y0 === y1) break;
      var e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  };

  // disc stamps for thick lines
  var DISCS = {};
  function disc(d) {
    if (DISCS[d]) return DISCS[d];
    var pts = [], c = (d - 1) / 2, r2 = (d / 2) * (d / 2) + 0.3;
    for (var j = 0; j < d; j++) for (var i = 0; i < d; i++)
      if ((i - c) * (i - c) + (j - c) * (j - c) <= r2) pts.push(i, j);
    return (DISCS[d] = { d: d, pts: pts });
  }
  B.stamp = function (cx, cy, d, c) {
    var D = disc(d), x0 = Math.round(cx - (d - 1) / 2), y0 = Math.round(cy - (d - 1) / 2);
    for (var k = 0; k < D.pts.length; k += 2) this.pset(x0 + D.pts[k], y0 + D.pts[k + 1], c);
  };
  B.thick = function (x0, y0, x1, y1, d, c) {
    var n = Math.max(1, Math.ceil(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))));
    for (var i = 0; i <= n; i++) this.stamp(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, d, c);
  };

  B.circle = function (cx, cy, r, c) {
    var r2 = r * r + r * 0.6;
    for (var y = -Math.ceil(r); y <= Math.ceil(r); y++)
      for (var x = -Math.ceil(r); x <= Math.ceil(r); x++)
        if (x * x + y * y <= r2) this.pset(Math.round(cx) + x, Math.round(cy) + y, c);
  };
  B.ring = function (cx, cy, r, c) {
    var n = Math.max(8, Math.ceil(r * 7));
    for (var i = 0; i < n; i++) {
      var a = i / n * Math.PI * 2;
      this.pset(Math.round(cx + Math.cos(a) * r), Math.round(cy + Math.sin(a) * r), c);
    }
  };
  B.ellipse = function (cx, cy, rx, ry, c, level) {
    for (var y = -Math.ceil(ry); y <= Math.ceil(ry); y++)
      for (var x = -Math.ceil(rx); x <= Math.ceil(rx); x++) {
        if ((x * x) / (rx * rx) + (y * y) / (ry * ry) > 1) continue;
        var px = Math.round(cx) + x, py = Math.round(cy) + y;
        if (level !== undefined && BAYER[(((py + this.oy) & 3) << 2) | ((px + this.ox) & 3)] >= level) continue;
        this.pset(px, py, c);
      }
  };

  // scanline polygon fill (pixel centres); optional dither level
  B.poly = function (pts, c, level) {
    var miny = Infinity, maxy = -Infinity, i;
    for (i = 1; i < pts.length; i += 2) { miny = Math.min(miny, pts[i]); maxy = Math.max(maxy, pts[i]); }
    var n = pts.length / 2;
    for (var y = Math.ceil(miny - 0.5); y <= Math.floor(maxy - 0.5); y++) {
      var yc = y + 0.5, xs = [];
      for (i = 0; i < n; i++) {
        var ax = pts[i * 2], ay = pts[i * 2 + 1], bx = pts[((i + 1) % n) * 2], by = pts[((i + 1) % n) * 2 + 1];
        if ((ay <= yc && by > yc) || (by <= yc && ay > yc)) xs.push(ax + (yc - ay) / (by - ay) * (bx - ax));
      }
      xs.sort(function (a, b) { return a - b; });
      for (var k = 0; k + 1 < xs.length; k += 2) {
        var xa = Math.ceil(xs[k] - 0.5), xb = Math.floor(xs[k + 1] - 0.5);
        for (var x = xa; x <= xb; x++) {
          if (level !== undefined && BAYER[(((y + this.oy) & 3) << 2) | ((x + this.ox) & 3)] >= level) continue;
          this.pset(x, y, c);
        }
      }
    }
  };

  // ----------------------------------------------------------------- sprites
  // rows: array of strings using palette letters, '.' = transparent
  function spr(rows) {
    var h = rows.length, w = 0, i, j;
    for (i = 0; i < h; i++) w = Math.max(w, rows[i].length);
    var px = new Uint8Array(w * h).fill(TR);
    for (j = 0; j < h; j++) for (i = 0; i < rows[j].length; i++) {
      var ch = rows[j][i];
      if (ch !== '.' && ch !== ' ') {
        if (C[ch] === undefined) throw new Error('bad sprite colour ' + ch);
        px[j * w + i] = C[ch];
      }
    }
    return { w: w, h: h, px: px };
  }
  MA.spr = spr;

  // draw sprite with anchor (ax,ay) placed at (x,y); flip mirrors around anchor; angle in radians
  // mode: undefined = normal, 'sil' = draw silhouette with colour col
  B.sprite = function (s, x, y, ax, ay, flip, angle, mode, col) {
    var i, j, c;
    if (!angle) {
      for (j = 0; j < s.h; j++) for (i = 0; i < s.w; i++) {
        c = s.px[j * s.w + i]; if (c === TR) continue;
        var px = flip ? Math.round(x + (ax - i)) : Math.round(x + (i - ax));
        this.pset(px, Math.round(y + (j - ay)), mode === 'sil' ? col : c);
      }
      return;
    }
    var ca = Math.cos(angle), sa = Math.sin(angle);
    var R = Math.ceil(Math.sqrt(s.w * s.w + s.h * s.h)) + 1;
    for (var oy = -R; oy <= R; oy++) for (var ox = -R; ox <= R; ox++) {
      // inverse rotate
      var lx = ox * ca + oy * sa, ly = -ox * sa + oy * ca;
      if (flip) lx = -lx;
      var si = Math.round(ax + lx), sj = Math.round(ay + ly);
      if (si < 0 || sj < 0 || si >= s.w || sj >= s.h) continue;
      c = s.px[sj * s.w + si]; if (c === TR) continue;
      this.pset(Math.round(x) + ox, Math.round(y) + oy, mode === 'sil' ? col : c);
    }
  };
  B.spriteOutlined = function (s, x, y, ax, ay, flip, angle, oc) {
    this.sprite(s, x - 1, y, ax, ay, flip, angle, 'sil', oc);
    this.sprite(s, x + 1, y, ax, ay, flip, angle, 'sil', oc);
    this.sprite(s, x, y - 1, ax, ay, flip, angle, 'sil', oc);
    this.sprite(s, x, y + 1, ax, ay, flip, angle, 'sil', oc);
    this.sprite(s, x, y, ax, ay, flip, angle);
  };

  // draw region of the title artwork; skipDark makes near-black transparent
  B.title = function (sx, sy, sw, sh, dx, dy, skipDark, level) {
    var t = MA.ASSETS.title;
    for (var j = 0; j < sh; j++) for (var i = 0; i < sw; i++) {
      var c = t.px[(sy + j) * t.w + sx + i];
      if (skipDark && TITLE_DARK[c]) continue;
      if (level !== undefined && BAYER[(((dy + j) & 3) << 2) | ((dx + i) & 3)] >= level) continue;
      this.pset(dx + i, dy + j, c);
    }
  };

  // -------------------------------------------------------------------- font
  var FONT_SRC = {
    'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'B': ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
    'C': ['.###.', '#...#', '#....', '#....', '#....', '#...#', '.###.'],
    'D': ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'F': ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
    'G': ['.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.####'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'I': ['.###.', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'],
    'J': ['..###', '...#.', '...#.', '...#.', '#..#.', '#..#.', '.##..'],
    'K': ['#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'M': ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'],
    'N': ['#...#', '#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'P': ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
    'Q': ['.###.', '#...#', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'U': ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'V': ['#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'],
    'W': ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '#.#.#', '.#.#.'],
    'X': ['#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'],
    'Y': ['#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'],
    'Z': ['#####', '....#', '...#.', '..#..', '.#...', '#....', '#####'],
    '0': ['.###.', '#...#', '#..##', '#.#.#', '##..#', '#...#', '.###.'],
    '1': ['..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'],
    '2': ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
    '3': ['#####', '...#.', '..#..', '...#.', '....#', '#...#', '.###.'],
    '4': ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
    '5': ['#####', '#....', '####.', '....#', '....#', '#...#', '.###.'],
    '6': ['..##.', '.#...', '#....', '####.', '#...#', '#...#', '.###.'],
    '7': ['#####', '....#', '...#.', '..#..', '.#...', '.#...', '.#...'],
    '8': ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
    '9': ['.###.', '#...#', '#...#', '.####', '....#', '...#.', '.##..'],
    '!': ['..#..', '..#..', '..#..', '..#..', '..#..', '.....', '..#..'],
    '?': ['.###.', '#...#', '....#', '...#.', '..#..', '.....', '..#..'],
    '.': ['.....', '.....', '.....', '.....', '.....', '.##..', '.##..'],
    ',': ['.....', '.....', '.....', '.....', '.##..', '..#..', '.#...'],
    ':': ['.....', '.##..', '.##..', '.....', '.##..', '.##..', '.....'],
    '-': ['.....', '.....', '.....', '#####', '.....', '.....', '.....'],
    '+': ['.....', '..#..', '..#..', '#####', '..#..', '..#..', '.....'],
    '>': ['.#...', '..#..', '...#.', '....#', '...#.', '..#..', '.#...'],
    '<': ['...#.', '..#..', '.#...', '#....', '.#...', '..#..', '...#.'],
    '*': ['.....', '#.#.#', '.###.', '#####', '.###.', '#.#.#', '.....'],
    '"': ['.#.#.', '.#.#.', '.#.#.', '.....', '.....', '.....', '.....'],
    "'": ['..#..', '..#..', '.#...', '.....', '.....', '.....', '.....'],
    '(': ['...#.', '..#..', '.#...', '.#...', '.#...', '..#..', '...#.'],
    ')': ['.#...', '..#..', '...#.', '...#.', '...#.', '..#..', '.#...'],
    '/': ['....#', '....#', '...#.', '..#..', '.#...', '#....', '#....'],
    '=': ['.....', '.....', '#####', '.....', '#####', '.....', '.....'],
    '%': ['##..#', '##..#', '...#.', '..#..', '.#...', '#..##', '#..##'],
    'x': ['.....', '.....', '#...#', '.#.#.', '..#..', '.#.#.', '#...#'],
    ' ': ['.....', '.....', '.....', '.....', '.....', '.....', '.....']
  };
  var FONT = {};
  Object.keys(FONT_SRC).forEach(function (k) {
    var rows = FONT_SRC[k], bits = [];
    for (var y = 0; y < 7; y++) for (var x = 0; x < 5; x++) if (rows[y][x] === '#') bits.push(x, y);
    FONT[k] = bits;
  });

  MA.textWidth = function (str, scale, spacing) {
    scale = scale || 1; spacing = spacing === undefined ? 1 : spacing;
    return str.length * (5 + spacing) * scale - spacing * scale;
  };
  // opts: scale, shadow (colour), outline (colour), bold
  B.text = function (str, x, y, c, opts) {
    opts = opts || {};
    var sc = opts.scale || 1, sp = opts.spacing === undefined ? 1 : opts.spacing;
    var self = this;
    function draw(ox, oy, col) {
      var cx = x + ox;
      for (var n = 0; n < str.length; n++) {
        var g = FONT[str[n]] || FONT['?'];
        for (var k = 0; k < g.length; k += 2) {
          self.rect(cx + g[k] * sc, y + oy + g[k + 1] * sc, sc + (opts.bold ? 1 : 0), sc, col);
        }
        cx += (5 + sp) * sc;
      }
    }
    if (opts.outline !== undefined) {
      draw(-1, 0, opts.outline); draw(1, 0, opts.outline); draw(0, -1, opts.outline); draw(0, 1, opts.outline);
      draw(-1, -1, opts.outline); draw(1, 1, opts.outline); draw(1, -1, opts.outline); draw(-1, 1, opts.outline);
      if (opts.bold) { draw(2, 0, opts.outline); draw(2, 1, opts.outline); draw(2, -1, opts.outline); }
    }
    if (opts.shadow !== undefined) draw(1, 1, opts.shadow);
    draw(0, 0, c);
  };
  B.textC = function (str, cx, y, c, opts) {
    opts = opts || {};
    var w = MA.textWidth(str, opts.scale || 1, opts.spacing);
    this.text(str, Math.round(cx - w / 2), y, c, opts);
  };

  // ----------------------------------------------------------- RGB output
  // fade: 0 = normal, 1..4 darker, -1..-4 brighter (towards white)
  MA.toRGBA = function (buf, out, fade) {
    var px = buf.px, n = px.length, f = fade || 0;
    var mul = f > 0 ? [1, 0.7, 0.45, 0.22, 0][Math.min(4, f)] : 1;
    var add = f < 0 ? [0, 0.3, 0.55, 0.8, 1][Math.min(4, -f)] : 0;
    for (var i = 0; i < n; i++) {
      var c = px[i] * 3, o = i * 4;
      var r = PAL[c], g = PAL[c + 1], b = PAL[c + 2];
      if (mul !== 1) { r *= mul; g *= mul; b *= mul; }
      if (add) { r += (255 - r) * add; g += (255 - g) * add; b += (255 - b) * add; }
      out[o] = r; out[o + 1] = g; out[o + 2] = b; out[o + 3] = 255;
    }
  };
})(typeof window !== 'undefined' ? window : globalThis);
