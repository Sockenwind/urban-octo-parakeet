// MRS. ANTHROPE - STAGE 1 "ROAD TO THE GIG"
// Deterministic 8-bit beat 'em up simulation + renderer (runs in browser and Node).
(function (root) {
  'use strict';
  var MA = root.MA;
  var C = MA.C, W = MA.W, H = MA.H;
  var RAD = Math.PI / 180;
  var K = C.K;

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function sgn(v) { return v < 0 ? -1 : 1; }
  function lerp(a, b, t) { return a + (b - a) * t; }

  // ================================================================ HEADS
  // facing right; anchor = (ax, last row)
  var HEADS = {
    vox: [
      '....hHHHh....',
      '..hHHHHHHHh..',
      '.hHHHHHHHHHh.',
      'hHHHHHHHHHHHh',
      'hHHHHHHHHSHHh',
      'hHHHHHHSSSSS.',
      'hHHHHsSSSKSS.',
      'hhHHHsSSSKSSs',
      '.hHHsSSSSSSSs',
      '.hhBBSSSSSSS.',
      '..hBBBBSBBBB.',
      '...BBBBrrrB..',
      '....BBBBBB...',
      '.....BBBB....'
    ],
    voxOpen: [
      '....hHHHh....',
      '..hHHHHHHHh..',
      '.hHHHHHHHHHh.',
      'hHHHHHHHHHHHh',
      'hHHHHHHHHSHHh',
      'hHHHHHHSSSSS.',
      'hHHHHsSSSKSS.',
      'hhHHHsSSSKSSs',
      '.hHHsSSSSSSSs',
      '.hhBBSSSSSSS.',
      '..hBBBBSKKKK.',
      '...BBBBKRRK..',
      '....BBBKKK...',
      '.....BBBB....'
    ],
    axe: [
      '....nNNNNn...',
      '..nNNNNNNNNn.',
      '.nNNNNNNNNNNn',
      '.nNNNNNNNNNNn',
      '.mnnnnnnnnnnn',
      '.bbbSSSSSSSS.',
      '.bbsSSSSSKSS.',
      '.bbsSSSSSKSSs',
      '.bbSSSSSSSSSs',
      '..bBSSSSSSSS.',
      '..BBBBBSBBBB.',
      '..BBBBBrrrB..',
      '...BBBBBBBB..',
      '....BBBBBB...'
    ],
    cap: [
      '....nNNNNn.....',
      '..nNNNNNNNNn...',
      '.nNNNNNNNNNNn..',
      '.nNNNNNNNNNNNNN',
      '.bbbSSSSSSSS...',
      '.bbsSSSSSKSS...',
      '.bbsSSSSSKSSs..',
      '.bbSSSSSSSSSs..',
      '..bSSSSSSSSS...',
      '..BBSSSSSrrS...',
      '...BBBBBBBB....',
      '....BBBBBB.....'
    ],
    drum: [
      '....bbbbb....',
      '..bbbbbbbbb..',
      '.bbbbbbbbbbb.',
      '.bRRRRRRRRRR.',
      '.bbbbSSSSSSS.',
      'bbbbsSSSSKSS.',
      'bbbbsSSSSKSSs',
      'bbbbSSSSSSSSs',
      'bbbbSSSSSSSS.',
      'bbb.SSSSSrrS.',
      'bb...SSSSSS..',
      'b.....SSSS...'
    ],
    punk: [
      '.....PPP.....',
      '....PPPPP....',
      '...PPPPPPp...',
      '...PPPPPPp...',
      '..sPPPPPPs...',
      '.sSSSSSSSSS..',
      '.sSSSSSSKKS..',
      '.ssSSSSSSKSs.',
      '.YsSSSSSSSSs.',
      '.ssSSSSSSSS..',
      '..sSSSSSrrr..',
      '...sSSSSSS...',
      '....sSSSS....'
    ],
    suit: [
      '...kkkkkkk...',
      '..kkkkkkkkkk.',
      '.kkkkkkkkkkkk',
      '.kkkkkkkkkkk.',
      '.kkkSSSSSSSS.',
      '.kksSSKKKKKKK',
      '.kksSSKKKKKSs',
      '.kksSSSSSSSSs',
      '..sSSSSSSSSS.',
      '..sSSSSSrrrS.',
      '...sSSSSSSS..',
      '....sSSSSS...'
    ],
    bouncer: [
      '....SSSSS....',
      '..SSSSSSSSS..',
      '.sSSSSSSSSSS.',
      '.sSSSSSSSSSS.',
      '.sSSSSSSSSSS.',
      '.sSSSSSSkkkS.',
      '.ssSSSSSSKSS.',
      '.ssSSSSSSKSSs',
      '.ssSSSSSSSSSs',
      '.ssSSSSSSSSS.',
      '..sSSSSbbbbS.',
      '...sSSSbrrb..',
      '....sSSbbb...'
    ],
    boss: [
      '....LLLLLL.....',
      '..LLLLLLLLLL...',
      '.LLLLLLLLLLLL..',
      'LLLLLLLLLLLLL..',
      'LLLLSSSSSSSSS..',
      'LLLsSSSSSSSSS..',
      'LLLsSSKKKKKKKK.',
      '.LLsSSSKKKKKSs.',
      '.LsSSSSSSSSSSs.',
      '..sSSSSSSSSSS..',
      '..sSSSSSSSkWWWO',
      '..ssSSSSSSS....',
      '...ssSSSSSS....',
      '....sSSSSS.....'
    ]
  };
  function recolor(rows, map) {
    return rows.map(function (r) { return r.replace(/./g, function (ch) { return map[ch] || ch; }); });
  }
  HEADS.punk2 = recolor(HEADS.punk, { P: 'O', p: 'A' });
  HEADS.punk3 = recolor(HEADS.punk, { P: 'C', p: 'c' });
  var HS = {};
  Object.keys(HEADS).forEach(function (k) { HS[k] = MA.spr(HEADS[k]); });

  // ================================================================ LOOKS
  var DIMS = {
    std: { thigh: 12, shin: 12, torso: 17, upper: 8, fore: 8, legW: 5, armW: 4, sw: 13, ww: 10, fist: 5 },
    big: { thigh: 13, shin: 13, torso: 19, upper: 9, fore: 9, legW: 6, armW: 5, sw: 16, ww: 12, fist: 6 },
    boss: { thigh: 14, shin: 14, torso: 23, upper: 10, fore: 10, legW: 7, armW: 6, sw: 22, ww: 17, fist: 7 }
  };
  var LOOKS = {
    vox: { head: 'vox', open: 'voxOpen', dims: 'std', skin: 'S', shirt: 'd', hi: 'E', pants: 'd', shin: 'd', shoe: 'W', tattoo: true, print: true, name: 'VOX' },
    axe: { head: 'axe', dims: 'std', skin: 'S', shirt: 'd', hi: 'E', sleeve: 'd', pants: 'd', shin: 'S', sock: 'W', shoe: 'W', guitar: { body: 'W', edge: 'L', neck: 'B', pick: 'K' }, name: 'AXE' },
    cap: { head: 'cap', dims: 'std', skin: 'S', shirt: 'd', hi: 'n', sleeve: 'd', pants: 'd', shin: 'd', shoe: 'W', guitar: { body: 'k', edge: 'N', neck: 'B', pick: 'N' }, name: 'RIFF' },
    drum: { head: 'drum', dims: 'std', skin: 'S', shirt: 'd', hi: 'E', sleeve: 'd', pants: 'd', shin: 'd', shoe: 'W', name: 'BEAT' },
    punk: { head: 'punk', dims: 'std', skin: 'S', shirt: 'E', hi: 'G', sleeve: 'E', full: true, pants: 'U', shin: 'U', shoe: 'k', studs: true, name: 'POSER' },
    punk2: { head: 'punk2', dims: 'std', skin: 'S', shirt: 'p', hi: 'P', sleeve: 'p', pants: 'u', shin: 'u', shoe: 'k', name: 'SNOT' },
    punk3: { head: 'punk3', dims: 'std', skin: 'S', shirt: 'E', hi: 'G', sleeve: 'E', full: true, pants: 'k', shin: 'k', shoe: 'r', studs: true, name: 'SID' },
    suit: { head: 'suit', dims: 'std', skin: 'S', shirt: 'G', hi: 'L', sleeve: 'G', full: true, pants: 'G', shin: 'G', shoe: 'k', tie: 'R', name: 'A AND R MAN' },
    bouncer: { head: 'bouncer', dims: 'big', skin: 'S', shirt: 'r', hi: 'R', sleeve: 'r', pants: 'k', shin: 'k', shoe: 'k', name: 'BOUNCER' },
    boss: { head: 'boss', dims: 'boss', skin: 'S', shirt: 'W', hi: 'w', sleeve: 'W', full: true, pants: 'W', shin: 'W', shoe: 'X', chain: true, name: 'THE PROMOTER' }
  };
  var SHADE = { S: 's', d: 'k', E: 'D', G: 'E', L: 'G', W: 'L', w: 'W', U: 'u', u: 'D', r: 'q', R: 'r', P: 'p', p: 'q', N: 'n', n: 'm', B: 'b', H: 'h', k: 'K', X: 'x', T: 'S' };
  function cc(ch, shade) { return C[shade ? (SHADE[ch] || ch) : ch]; }

  // ================================================================ POSES
  // angles (deg): 0 = down, 90 = forward, 180 = up. [upper, lower]
  var POSES = {
    stand: { lean: 2, bA: [8, 14], fA: [14, 22], bL: [-7, -3], fL: [8, 3] },
    stand2: { lean: 3, bA: [10, 16], fA: [16, 24], bL: [-8, -2], fL: [9, 2] },
    guard0: { lean: 6, bA: [22, 150], fA: [42, 140], bL: [-18, -8], fL: [22, 6] },
    guard1: { lean: 7, bA: [24, 146], fA: [44, 136], bL: [-21, -6], fL: [25, 4] },
    walk0: { lean: 7, bA: [22, 150], fA: [40, 140], bL: [-26, -18], fL: [26, 10] },
    walk1: { lean: 7, bA: [24, 146], fA: [38, 144], bL: [14, -32], fL: [-2, 0] },
    walk2: { lean: 7, bA: [22, 150], fA: [40, 140], bL: [26, 10], fL: [-26, -18] },
    walk3: { lean: 7, bA: [24, 146], fA: [38, 144], bL: [-2, 0], fL: [14, -32] },
    cwalk0: { lean: 3, bA: [-18, -10], fA: [18, 26], bL: [-24, -16], fL: [24, 8] },
    cwalk1: { lean: 3, bA: [-4, 4], fA: [4, 12], bL: [12, -30], fL: [-2, 0] },
    cwalk2: { lean: 3, bA: [18, 26], fA: [-18, -10], bL: [24, 8], fL: [-24, -16] },
    cwalk3: { lean: 3, bA: [4, 12], fA: [-4, 4], bL: [-2, 0], fL: [12, -30] },
    jabW: { lean: 2, bA: [22, 150], fA: [24, 162], bL: [-20, -8], fL: [24, 6] },
    jab: { lean: 14, bA: [26, 155], fA: [86, 90], bL: [-27, -14], fL: [27, 8] },
    cross: { lean: 20, bA: [84, 90], fA: [30, 160], bL: [-31, -18], fL: [25, 10] },
    kickW: { lean: -6, bA: [10, 140], fA: [45, 150], bL: [-6, -3], fL: [72, -12] },
    kick: { lean: -20, bA: [-40, 10], fA: [50, 132], bL: [-12, -6], fL: [92, 92] },
    hurt: { lean: -20, hx: -1, bA: [-35, -15], fA: [-15, 25], bL: [-15, -6], fL: [18, 4] },
    hurt2: { lean: -11, hx: -1, bA: [-20, 0], fA: [0, 40], bL: [-15, -6], fL: [18, 4] },
    fly: { lean: 0, bA: [-120, -150], fA: [-95, -125], bL: [25, 45], fL: [-5, 15] },
    lie: { lean: 0, bA: [-168, -172], fA: [-150, -160], bL: [2, 2], fL: [-5, -3], hipH: 4, rot: -90 },
    kneel: { lean: 22, bA: [30, 60], fA: [60, 95], bL: [-10, -95], fL: [85, 0] },
    victory: { lean: 0, bA: [-14, 8], fA: [165, 178], bL: [-13, -6], fL: [13, 6] },
    victory2: { lean: -3, bA: [-18, 4], fA: [150, 172], bL: [-14, -6], fL: [14, 6] },
    screamW: { lean: -12, hx: -1, bA: [-15, 20], fA: [40, 168], bL: [-18, -8], fL: [22, 6], mic: true },
    scream: { lean: 18, hx: 2, mouth: 1, bA: [-62, -40], fA: [56, 166], bL: [-33, -20], fL: [33, 12], mic: true },
    gsw0: { lean: -14, bA: [185, 200], fA: [195, 210], bL: [-18, -8], fL: [22, 6], guitar: 'hands' },
    gsw1: { lean: 8, bA: [140, 150], fA: [150, 155], bL: [-22, -10], fL: [26, 8], guitar: 'hands' },
    gsw2: { lean: 24, bA: [90, 90], fA: [96, 94], bL: [-33, -22], fL: [37, 22], guitar: 'hands' },
    gsw3: { lean: 28, bA: [55, 40], fA: [60, 45], bL: [-33, -22], fL: [37, 22], guitar: 'hands' },
    epunchW: { lean: -6, bA: [20, 150], fA: [-12, 140], bL: [-18, -8], fL: [22, 6] },
    epunch: { lean: 16, bA: [10, 150], fA: [88, 90], bL: [-27, -14], fL: [27, 8] },
    slamW: { lean: -16, bA: [170, 185], fA: [175, 190], bL: [-18, -8], fL: [22, 6] },
    slam: { lean: 28, bA: [65, 35], fA: [70, 40], bL: [-31, -20], fL: [31, 15] },
    taunt: { lean: -4, bA: [12, 24], fA: [60, 172], bL: [-12, -5], fL: [12, 5] },
    leap: { lean: 10, bA: [120, 150], fA: [140, 170], bL: [40, -30], fL: [70, 0] },
    play0: { lean: 6, bA: [62, 98], fA: [28, 100], bL: [-25, -14], fL: [25, 10], guitar: 'play' },
    play1: { lean: 8, bA: [62, 98], fA: [24, 140], bL: [-25, -14], fL: [25, 10], guitar: 'play', hy: 1 },
    sing0: { lean: 8, mouth: 1, bA: [-45, -15], fA: [52, 166], bL: [-28, -16], fL: [30, 12], mic: true },
    sing1: { lean: 12, mouth: 1, hy: 1, bA: [150, 172], fA: [52, 166], bL: [-30, -18], fL: [32, 14], mic: true },
    jump: { lean: 6, bA: [40, 150], fA: [60, 140], bL: [70, -25], fL: [95, 5] },
    jkick: { lean: -16, bA: [-45, 5], fA: [60, 130], bL: [55, -45], fL: [96, 96] },
    drum0: { lean: 4, bA: [45, 110], fA: [55, 120], bL: [92, 0], fL: [84, 0], hipH: 15 },
    drum1: { lean: 6, hy: 1, bA: [70, 160], fA: [40, 95], bL: [92, 0], fL: [84, 0], hipH: 15 }
  };

  // ================================================================ RIG
  function limb(s, a, l1, l2) {
    var a1 = a[0] * RAD, a2 = a[1] * RAD;
    var e = [s[0] + Math.sin(a1) * l1, s[1] + Math.cos(a1) * l1];
    return [s, e, [e[0] + Math.sin(a2) * l2, e[1] + Math.cos(a2) * l2]];
  }
  function rig(D, pose) {
    var L = (pose.lean || 0) * RAD;
    var ux = Math.sin(L), uy = -Math.cos(L), fx = Math.cos(L), fy = Math.sin(L);
    var r = { ux: ux, uy: uy, fx: fx, fy: fy };
    r.neck = [ux * D.torso, uy * D.torso];
    var so = D.sw / 2 - D.armW / 2 - 0.5;
    r.shF = [r.neck[0] + fx * so - ux * 2, r.neck[1] + fy * so - uy * 2];
    r.shB = [r.neck[0] - fx * so - ux * 2, r.neck[1] - fy * so - uy * 2];
    var ho = (D.ww / 2 - D.legW / 2) * 0.6;
    r.armB = limb(r.shB, pose.bA, D.upper, D.fore);
    r.armF = limb(r.shF, pose.fA, D.upper, D.fore);
    r.legB = limb([-ho, 0], pose.bL, D.thigh, D.shin);
    r.legF = limb([ho, 0], pose.fL, D.thigh, D.shin);
    var hw = D.ww / 2, hs = D.sw / 2;
    r.torso = [[-hw, 1.5], [hw, 1.5],
      [r.neck[0] + fx * hs, r.neck[1] + fy * hs], [r.neck[0] - fx * hs, r.neck[1] - fy * hs]];
    r.ext = Math.max(r.legB[2][1], r.legF[2][1]);
    return r;
  }

  function drawGuitar(buf, P, n, g) {
    var bx = P[0], by = P[1];
    var hx = bx + n[0] * 17, hy = by + n[1] * 17;
    var lb = [bx - n[0] * 1.5, by - n[1] * 1.5], ub = [bx + n[0] * 3.5, by + n[1] * 3.5];
    buf.thick(bx + n[0] * 4, by + n[1] * 4, hx, hy, 4, K);
    buf.circle(lb[0], lb[1], 5.4, K); buf.circle(ub[0], ub[1], 4.3, K);
    buf.thick(bx + n[0] * 4, by + n[1] * 4, hx, hy, 2, C[g.neck]);
    buf.stamp(hx, hy, 3, C.k);
    buf.circle(lb[0], lb[1], 4.3, C[g.body]); buf.circle(ub[0], ub[1], 3.3, C[g.body]);
    if (g.edge) { buf.ring(lb[0], lb[1], 4.2, C[g.edge]); }
    buf.circle(lb[0], lb[1], 4.3 - 2.6, C[g.body]);
    buf.stamp(bx + n[0] * 1, by + n[1] * 1, 2, C[g.pick]);
    buf.pset(Math.round(lb[0] - n[0] * 2), Math.round(lb[1] - n[1] * 2), C.k);
  }

  // draw an actor at screen root (sx, sy) [sy = ground y - z]
  function drawPuppet(buf, a, sx, sy) {
    var look = a.look, D = DIMS[look.dims], pose = a.pose, dir = a.dir;
    var R = rig(D, pose);
    var rotDeg = pose.rot !== undefined ? pose.rot : (a.rot || 0);
    var rot = rotDeg * RAD;
    var hipH = pose.hipH !== undefined ? pose.hipH : (rotDeg ? 5 : R.ext + 1);
    var hx = sx, hy = sy - hipH;
    var cr = Math.cos(rot), sr = Math.sin(rot);
    function T(p) { var x = p[0] * cr - p[1] * sr, y = p[0] * sr + p[1] * cr; return [hx + dir * x, hy + y]; }
    function V(v) { var x = v[0] * cr - v[1] * sr, y = v[0] * sr + v[1] * cr; return [dir * x, y]; }

    function arm(A, shade, front) {
      var p = A.map(T), w = D.armW;
      buf.thick(p[0][0], p[0][1], p[1][0], p[1][1], w + 2, K);
      buf.thick(p[1][0], p[1][1], p[2][0], p[2][1], w + 2, K);
      buf.stamp(p[2][0], p[2][1], D.fist + 2, K);
      var up = look.full ? look.sleeve : look.skin;
      var fo = look.full ? look.sleeve : look.skin;
      buf.thick(p[0][0], p[0][1], p[1][0], p[1][1], w, cc(up, shade));
      buf.thick(p[1][0], p[1][1], p[2][0], p[2][1], w, cc(fo, shade));
      if (look.sleeve && !look.full) {
        buf.thick(p[0][0], p[0][1], lerp(p[0][0], p[1][0], 0.55), lerp(p[0][1], p[1][1], 0.55), w, cc(look.sleeve, shade));
      }
      if (look.full) buf.stamp(lerp(p[1][0], p[2][0], 0.92), lerp(p[1][1], p[2][1], 0.92), w, cc(look.hi, shade));
      buf.stamp(p[2][0], p[2][1], D.fist, cc(look.skin, shade));
      if (look.tattoo && front) {
        buf.pset(Math.round(lerp(p[0][0], p[1][0], 0.5)), Math.round(lerp(p[0][1], p[1][1], 0.5)), C.m);
        buf.pset(Math.round(lerp(p[0][0], p[1][0], 0.7)), Math.round(lerp(p[0][1], p[1][1], 0.7)) + 1, C.u);
        buf.pset(Math.round(lerp(p[1][0], p[2][0], 0.4)), Math.round(lerp(p[1][1], p[2][1], 0.4)), C.m);
      }
      return p;
    }
    function leg(Lg, shade) {
      var p = Lg.map(T), w = D.legW;
      var sv = [p[2][0] - p[1][0], p[2][1] - p[1][1]], sl = Math.hypot(sv[0], sv[1]) || 1;
      var f = [sv[1] / sl * dir, -sv[0] / sl * dir];
      // foot direction must point forward in facing space: compute in local space instead
      var lsv = [Lg[2][0] - Lg[1][0], Lg[2][1] - Lg[1][1]], ll = Math.hypot(lsv[0], lsv[1]) || 1;
      f = V([lsv[1] / ll, -lsv[0] / ll]);
      var a0 = [p[2][0] - f[0] * 1, p[2][1] - f[1] * 1], a1 = [p[2][0] + f[0] * 3, p[2][1] + f[1] * 3];
      buf.thick(p[0][0], p[0][1], p[1][0], p[1][1], w + 2, K);
      buf.thick(p[1][0], p[1][1], p[2][0], p[2][1], w + 2, K);
      buf.thick(a0[0], a0[1], a1[0], a1[1], 5, K);
      buf.thick(p[0][0], p[0][1], p[1][0], p[1][1], w, cc(look.pants, shade));
      buf.thick(p[1][0], p[1][1], p[2][0], p[2][1], look.shin === look.skin ? w - 1 : w, cc(look.shin, shade));
      if (look.sock) buf.stamp(lerp(p[1][0], p[2][0], 0.85), lerp(p[1][1], p[2][1], 0.85), w - 1, cc(look.sock, shade));
      buf.thick(a0[0], a0[1], a1[0], a1[1], 3, cc(look.shoe, shade));
    }
    function guitar(mode, front) {
      var g = look.guitar; if (!g) return;
      var P, n;
      if (mode === 'hands') {
        var p = R.armF;
        var fd = [p[2][0] - p[1][0], p[2][1] - p[1][1]], fl = Math.hypot(fd[0], fd[1]) || 1;
        fd = [fd[0] / fl, fd[1] / fl];
        P = T([p[2][0] + fd[0] * 14, p[2][1] + fd[1] * 14]);
        n = V([-fd[0], -fd[1]]);
      } else if (mode === 'play') {
        P = T([3, -3]);
        n = V([Math.sin(112 * RAD), Math.cos(112 * RAD)]);
      } else { // on back
        P = T([-6, -7]);
        n = V([Math.sin(196 * RAD), Math.cos(196 * RAD)]);
      }
      drawGuitar(buf, P, n, g);
    }

    var gmode = pose.guitar || (look.guitar ? 'back' : null);
    if (gmode === 'back') guitar('back');
    arm(R.armB, true, false);
    leg(R.legB, true);
    leg(R.legF, false);
    // torso
    var tp = [];
    R.torso.forEach(function (p) { var q = T(p); tp.push(q[0], q[1]); });
    function shifted(dx, dy) { var o = []; for (var i = 0; i < tp.length; i += 2) o.push(tp[i] + dx, tp[i + 1] + dy); return o; }
    buf.poly(shifted(-1, 0), K); buf.poly(shifted(1, 0), K); buf.poly(shifted(0, -1), K); buf.poly(shifted(0, 1), K);
    buf.poly(tp, C[look.shirt]);
    // front edge highlight
    var wf = T([D.ww / 2 - 1, 0]), sf = T([R.neck[0] + R.fx * (D.sw / 2 - 1), R.neck[1] + R.fy * (D.sw / 2 - 1) + 1]);
    buf.line(wf[0], wf[1], sf[0], sf[1], C[look.hi]);
    var mid = T([R.ux * D.torso * 0.55 + R.fx * 1, R.uy * D.torso * 0.55 + R.fy * 1]);
    if (look.print) {
      buf.rect(Math.round(mid[0]) - 2, Math.round(mid[1]) - 2, 4, 4, C.L);
      buf.pset(Math.round(mid[0]), Math.round(mid[1]) - 1, C.R);
      buf.pset(Math.round(mid[0]) - 1, Math.round(mid[1]), C.R);
    }
    if (look.studs) {
      buf.pset(Math.round(mid[0]) - 2, Math.round(mid[1]) - 3, C.L);
      buf.pset(Math.round(mid[0]) + 1, Math.round(mid[1]) + 2, C.L);
    }
    var nk = T(R.neck);
    if (look.tie) {
      var t2 = T([R.neck[0] - R.ux * 8 + R.fx * 1, R.neck[1] - R.uy * 8 + R.fy * 1]);
      buf.thick(nk[0] + dir, nk[1] + 1, t2[0], t2[1], 2, C.R);
      buf.pset(Math.round(nk[0]), Math.round(nk[1]) + 1, C.w);
    }
    if (look.chain) {
      var c1 = T([R.neck[0] - R.ux * 6, R.neck[1] - R.uy * 6]);
      buf.poly([nk[0] - 3, nk[1], nk[0] + 4, nk[1], c1[0], c1[1] + 1], C.k);
      buf.line(nk[0] - 3, nk[1] + 1, c1[0], c1[1], C.Y);
      buf.line(nk[0] + 4, nk[1] + 1, c1[0], c1[1], C.Y);
    }
    // neck + head
    var nTop = T([R.neck[0] + R.ux * 2, R.neck[1] + R.uy * 2]);
    buf.thick(nk[0], nk[1], nTop[0], nTop[1], 6, K);
    buf.thick(nk[0], nk[1], nTop[0], nTop[1], 4, C[look.skin]);
    var hs = HS[(pose.mouth && look.open) ? look.open : look.head];
    var hp = T([R.neck[0] + R.ux * 2 + (pose.hx || 0), R.neck[1] + R.uy * 2 + (pose.hy || 0)]);
    var hang = Math.round(rotDeg / 45) * 45 * RAD;
    buf.spriteOutlined(hs, hp[0], hp[1], 5, hs.h - 1, dir < 0, dir < 0 ? -hang : hang, K);

    if (gmode === 'play' || gmode === 'hands') guitar(gmode);
    var pf = arm(R.armF, false, true);
    if (pose.mic) {
      // mic pointing from fist towards mouth
      var m0 = pf[2], m1 = T([R.neck[0] + R.ux * 6 + R.fx * 5, R.neck[1] + R.uy * 6 + R.fy * 5]);
      var mv = [m1[0] - m0[0], m1[1] - m0[1]], ml = Math.hypot(mv[0], mv[1]) || 1;
      var tip = [m0[0] + mv[0] / ml * 4, m0[1] + mv[1] / ml * 4];
      buf.thick(m0[0], m0[1], tip[0], tip[1], 2, C.k);
      buf.stamp(tip[0], tip[1], 3, C.G);
      buf.pset(Math.round(tip[0]), Math.round(tip[1]), C.L);
    }
  }
  MA.drawPuppet = drawPuppet;

  // ================================================================ ATTACKS
  var ATK = {
    jab: { dur: 15, keys: [[0, 'jabW'], [3, 'jab'], [10, 'guard0']], act: [3, 6], reach: 25, dmg: 4, hitZ: 40, sfx: 'hit', stop: 4, score: 100 },
    cross: { dur: 18, keys: [[0, 'jabW'], [4, 'cross'], [12, 'guard0']], act: [4, 7], reach: 26, dmg: 5, hitZ: 37, sfx: 'hit', stop: 5, score: 150 },
    kick: { dur: 30, keys: [[0, 'kickW'], [7, 'kick'], [19, 'kickW'], [25, 'guard0']], act: [7, 11], reach: 32, dmg: 8, knock: 1, hitZ: 29, sfx: 'heavy', stop: 7, lunge: [5, 11, 0.9], score: 300 },
    gsmash: { dur: 58, keys: [[0, 'gsw0'], [16, 'gsw1'], [20, 'gsw2'], [30, 'gsw3'], [48, 'guard0']], act: [20, 26], reach: 48, dmg: 22, knock: 1.25, multi: true, hitZ: 31, sfx: 'smash', stop: 10, shake: 10, special: true, swing: 14, score: 500 },
    scream: { dur: 66, keys: [[0, 'screamW'], [14, 'scream'], [54, 'guard0']], proj: 16, special: true, score: 500 },
    jkick: { reach: 32, dmg: 9, knock: 1, hitZ: 36, sfx: 'heavy', stop: 6, score: 300 },
    wave: { dmg: 16, knock: 1.15, hitZ: 36, sfx: 'heavy', stop: 6, score: 500 },
    epunch: { dur: 26, keys: [[0, 'epunchW'], [12, 'epunch'], [19, 'guard0']], act: [12, 15], reach: 24, dmg: 6, hitZ: 37, sfx: 'hit', stop: 4, swing: 10 },
    ekick: { dur: 32, keys: [[0, 'kickW'], [10, 'kick'], [22, 'kickW'], [27, 'guard0']], act: [10, 13], reach: 30, dmg: 7, hitZ: 29, sfx: 'hit', stop: 5 },
    bpunch: { dur: 32, keys: [[0, 'epunchW'], [15, 'epunch'], [25, 'guard0']], act: [15, 18], reach: 32, dmg: 9, hitZ: 46, sfx: 'heavy', stop: 6, lunge: [12, 17, 1.2] },
    slam: { dur: 46, keys: [[0, 'slamW'], [22, 'slam'], [38, 'guard0']], act: [22, 26], reach: 37, dmg: 13, knock: 1.1, hitZ: 36, sfx: 'smash', stop: 8, shake: 8, swing: 18 }
  };

  // ================================================================ ACTOR
  var nextId = 1;
  function Actor(g, kind, o) {
    this.id = nextId++;
    this.kind = kind; this.look = LOOKS[kind];
    this.name = o.name || this.look.name;
    this.team = o.team || 'enemy';
    this.x = o.x; this.y = o.y; this.z = o.z || 0;
    this.vx = 0; this.vy = 0; this.vz = 0; this.mx = 0; this.my = 0;
    this.dir = o.dir || (this.team === 'player' ? 1 : -1);
    this.hp = this.maxHp = o.hp || 22;
    this.state = 'idle'; this.t = 0; this.walkT = 0;
    this.freeze = 0; this.flash = 0; this.invuln = 0;
    this.pose = POSES.guard0; this.rot = 0;
    this.scale = this.look.dims === 'boss' ? 1.35 : this.look.dims === 'big' ? 1.15 : 1;
    this.speed = o.speed || (this.team === 'player' ? 1.15 : 0.78);
    this.boss = !!o.boss;
    this.human = !!o.human;
    this.calm = !!o.calm;
    this.ai = { cool: o.cool || 30, combo: 0, comboT: 0, spCool: o.spCool || 200, target: o.target || null, engaged: false, wait: o.wait || 0, slot: o.slot || 0, yoff: o.yoff || 0 };
    this.goal = o.goal || null;
    this.hits = 0; this.hitSet = [];
    this.removed = false;
    this.score = 0; this.lives = 3;
    this.phase = (this.id * 7) % 30;
    this.anim = null;
  }
  MA.Actor = Actor;
  var AP = Actor.prototype;
  AP.canAct = function () { return (this.state === 'idle' || this.state === 'walk') && this.freeze <= 0; };
  AP.hittable = function () {
    return !this.removed && this.invuln <= 0 && this.state !== 'knock' && this.state !== 'down' &&
      this.state !== 'getup' && this.state !== 'dead' && this.state !== 'leap' && this.state !== 'script' &&
      this.state !== 'jump' && !(this.human && this.state === 'hurt');
  };
  AP.busy = function () { return this.state === 'knock' || this.state === 'down' || this.state === 'getup' || this.state === 'dead'; };
  AP.attack = function (g, name) {
    this.state = 'attack'; this.t = 0; this.atk = ATK[name]; this.atkName = name; this.hitSet = [];
    if (this.atk.swing !== undefined) g.sfxAt('swing', this.atk.swing);
    if (name === 'scream') g.sfxAt('scream', 13);
    if (name === 'gsmash') g.sfx('swing');
  };
  AP.hurt = function (dir) { this.state = 'hurt'; this.t = 0; this.vx = dir * 1.1; this.atk = null; };
  AP.knock = function (g, dir, p) {
    this.state = 'knock'; this.t = 0; this.atk = null; this.bounced = false;
    var s = this.boss ? 0.5 : 1;
    this.vx = dir * 1.7 * p * s;
    if (this.boss) { var land = this.x + this.vx * 34; if (land < g.cam + 70 || land > g.cam + W - 70) this.vx *= 0.15; } this.vz = 2.6 * Math.sqrt(p) * s; this.z = Math.max(this.z, 0.5);
    this.hits = 0;
  };

  AP.update = function (g) {
    if (this.freeze > 0) { this.freeze--; return; }
    this.t++;
    if (this.flash > 0) this.flash--;
    if (this.invuln > 0) this.invuln--;
    var st = this.state;
    if (st === 'idle' || st === 'walk') {
      if (this.mx || this.my) {
        this.state = 'walk';
        this.x += this.mx * this.speed; this.y += this.my * this.speed * 0.62;
        this.walkT += Math.max(Math.abs(this.mx), Math.abs(this.my) * 0.8);
        var wf = Math.floor(this.walkT / 7) % 4;
        this.pose = POSES[(this.calm ? 'cwalk' : 'walk') + wf];
      } else {
        this.state = 'idle';
        if (this.calm) this.pose = POSES[(Math.floor((this.t + this.phase) / 40) % 2) ? 'stand2' : 'stand'];
        else this.pose = POSES[(Math.floor((g.frame + this.phase) / 26) % 2) ? 'guard1' : 'guard0'];
      }
      if (this.anim) this.pose = POSES[this.anim(g, this)] || this.pose;
    } else if (st === 'attack') {
      var A = this.atk, i, k = A.keys[0][1];
      for (i = 0; i < A.keys.length; i++) if (this.t >= A.keys[i][0]) k = A.keys[i][1];
      this.pose = POSES[k];
      if (A.lunge && this.t >= A.lunge[0] && this.t <= A.lunge[1]) this.x += this.dir * A.lunge[2];
      if (A.act && this.t >= A.act[0] && this.t <= A.act[1]) g.resolveHits(this, A);
      if (A.proj && this.t === A.proj) g.spawnWave(this);
      if (A.shake && this.t === A.act[0]) g.shake = Math.max(g.shake, 4);
      if (this.t >= A.dur) {
        this.state = 'idle'; this.t = 0;
        this.ai.cool = this.team === 'player' ? (this.atkName === 'kick' || A.special ? 22 : g.rng.int(2, 7)) + (this.ai.partner ? 16 : 0) : this.ai.cool;
        if (this.atkName === 'kick' || A.special) this.ai.combo = 0;
        this.atk = null;
      }
    } else if (st === 'hurt') {
      this.pose = this.t < 7 ? POSES.hurt : POSES.hurt2;
      this.x += this.vx; this.vx *= 0.82;
      if (this.t >= 20) { this.state = 'idle'; this.t = 0; }
    } else if (st === 'knock') {
      this.pose = POSES.fly;
      this.x += this.vx; this.z += this.vz; this.vz -= 0.17;
      this.rot = -Math.min(90, this.t * (this.bounced ? 2 : 4.5));
      if (this.bounced) this.rot = -90;
      if (this.z <= 0 && this.t > 2) {
        this.z = 0;
        if (!this.bounced) {
          this.bounced = true; this.vz = 1.1; this.vx *= 0.45; this.z = 0.1;
          g.sfx(this.boss ? 'thud' : 'land'); g.dust(this.x, this.y); g.shake = Math.max(g.shake, this.boss ? 8 : 3);
        } else {
          this.state = 'down'; this.t = 0; this.vx = 0; this.rot = -90;
        }
      }
    } else if (st === 'down') {
      this.pose = POSES.lie;
      var dt = this.team === 'player' ? 40 : this.boss ? 48 : 30;
      if (this.t >= dt) {
        if (this.hp <= 0 && this.team !== 'player') { this.state = 'dead'; this.t = 0; g.onDefeat(this); }
        else if (this.human && this.hp <= 0) { if (this.t === dt) g.onHumanDeath(this); }
        else { this.state = 'getup'; this.t = 0; }
      }
    } else if (st === 'getup') {
      this.pose = POSES.kneel; this.rot = 0;
      if (this.t >= 16) { this.state = 'idle'; this.t = 0; this.invuln = this.team === 'player' ? 50 : 10; this.ai.cool = 25; }
    } else if (st === 'dead') {
      this.pose = POSES.lie;
      if (this.t >= 40) this.removed = true;
    } else if (st === 'jump') {
      this.x += this.vx; this.z += this.vz; this.vz -= 0.19;
      this.pose = this.jkick ? POSES.jkick : POSES.jump;
      if (this.jkick) g.resolveHits(this, ATK.jkick);
      if (this.z <= 0 && this.t > 2) { this.z = 0; this.state = 'idle'; this.t = 0; this.jkick = false; g.sfx('land'); }
    } else if (st === 'leap') {
      // scripted jump from (sx,sy) to (tx,ty) over dur frames
      var L = this.leap, u = Math.min(1, this.t / L.dur);
      this.x = lerp(L.sx, L.tx, u); this.y = lerp(L.sy, L.ty, u);
      this.z = Math.sin(u * Math.PI) * L.h + (1 - u) * (L.sz || 0);
      this.pose = u < 0.15 ? POSES.kneel : POSES.leap;
      if (u >= 1) {
        this.z = 0; this.state = 'idle'; this.t = 0; this.pose = POSES.kneel;
        g.sfx('thud'); g.dust(this.x, this.y); g.dust(this.x - 8, this.y); g.shake = 14;
        if (L.done) L.done();
      }
    } else if (st === 'script') {
      if (this.anim) this.pose = POSES[this.anim(g, this)] || this.pose;
    }
  };

  // ================================================================ GAME
  function Game(opts) {
    opts = opts || {};
    this.mode = opts.mode || 'demo';
    this.input = {}; this.prevIn = {}; this.pressed = {};
    this.items = [];
    this.frame = 0;
    this.rng = new MA.RNG(20261108);
    this.actors = []; this.fx = []; this.events = [];
    this.scene = 'black'; this.sceneT = 0; this.cam = 0; this.shake = 0; this.fade = 0;
    this.hud = false; this.time = 99; this.timeT = 0;
    this.banners = [];
    this.slowmo = 0;
    this.hudTarget = {};
    this.done = false;
    this.players = [];
    this.musicStart = 0; this.musicName = null;
    nextId = 1;
    this.script = this.mode === 'play' ? playDirector(this) : director(this);
  }
  MA.Game = Game;
  var GP = Game.prototype;

  GP.sfx = function (name, opt) { this.events.push({ f: this.frame, type: 'sfx', name: name, opt: opt }); };
  GP.sfxAt = function (name, delay) { this.events.push({ f: this.frame + delay, type: 'sfx', name: name }); };
  GP.music = function (name) {
    this.events.push({ f: this.frame, type: 'music', name: name });
    this.musicName = name; this.musicStart = this.frame;
  };
  GP.spawn = function (kind, o) { var a = new Actor(this, kind, o); this.actors.push(a); if (a.team === 'player') this.players.push(a); return a; };
  GP.enemies = function () { return this.actors.filter(function (a) { return a.team === 'enemy' && !a.removed; }); };
  GP.banner = function (text, dur, o) { this.banners.push({ text: text, t: 0, dur: dur, o: o || {} }); };
  GP.dust = function (x, y) { this.fx.push({ type: 'dust', x: x, y: y, t: 0, life: 16 }); };
  GP.popup = function (x, y, z, text) {
    this.fx.forEach(function (f) { if (f.type === 'pop' && f.t < 14 && Math.abs(f.x - x) < 24) z += 9; });
    this.fx.push({ type: 'pop', x: x, y: y, z: z, t: 0, life: 40, text: text });
  };

  GP.resolveHits = function (a, A) {
    var list = this.actors;
    for (var i = 0; i < list.length; i++) {
      var e = list[i];
      if (e.team === a.team || e.removed || !e.hittable()) continue;
      if (a.hitSet.indexOf(e) >= 0) continue;
      if (!A.multi && a.hitSet.length) return;
      var rel = (e.x - a.x) * a.dir, dy = Math.abs(e.y - a.y);
      if (rel > -5 && rel < A.reach * a.scale + (e.scale - 1) * 10 && dy < 7 + (e.scale - 1) * 10) {
        a.hitSet.push(e);
        this.hit(a, e, A);
      }
    }
  };
  GP.hit = function (a, e, A) {
    e.hp -= A.dmg;
    e.dir = -a.dir;
    if (e.team === 'player' && !e.human) e.hp = Math.max(e.hp, 14);
    if (e.human && e.hp <= 0) e.hp = 0;
    e.hits++;
    var heavy = A.knock;
    var knock = A.knock || (e.hp <= 0) || (e.team === 'enemy' && !e.boss && e.hits >= 4) || (e.boss && e.hits >= 7);
    a.freeze = A.stop; e.freeze = A.stop; e.flash = 5;
    var sx = e.x - a.dir * 4 * e.scale;
    this.fx.push({ type: 'spark', x: sx, y: e.y + 1, z: A.hitZ * e.scale, t: 0, life: 12, big: !!heavy || A.special });
    this.sfx(A.sfx || 'hit');
    if (A.shake) this.shake = Math.max(this.shake, A.shake);
    if (knock) e.knock(this, a.dir, A.knock || 0.9); else e.hurt(a.dir);
    if (a.team === 'player') {
      a.score += A.score || 100;
      this.hudTarget[a.id] = { actor: e, t: 160 };
      if (A.special || A.knock) this.popup(e.x, e.y, 56 * e.scale, String(A.score || 100));
    }
    if (e.boss && e.hp <= 0 && !this.koDone) this.startKO(a, e);
  };
  GP.spawnWave = function (a) {
    this.fx.push({ type: 'wave', owner: a, x: a.x + a.dir * 14, y: a.y, z: 46, dir: a.dir, t: 0, life: 34, hitSet: [] });
  };
  GP.onDefeat = function (e) {
    var last = null, self = this;
    this.players.forEach(function (p) { if (self.hudTarget[p.id] && self.hudTarget[p.id].actor === e) last = p; });
    (last || this.players[0]).score += e.boss ? 10000 : 500;
    if (this.mode === 'play' && e.drop) this.items.push({ x: e.x, y: e.y, kind: e.drop, t: 0 });
  };

  GP.updateFx = function () {
    var self = this;
    this.fx.forEach(function (f) {
      f.t++;
      if (f.type === 'wave') {
        f.x += f.dir * 3.3;
        self.actors.forEach(function (e) {
          if (e.team !== 'enemy' || !e.hittable() || f.hitSet.indexOf(e) >= 0) return;
          if (Math.abs(e.y - f.y) < 12 + (e.scale - 1) * 10 && Math.abs(e.x - f.x) < 9 * e.scale) {
            f.hitSet.push(e); self.hit(f.owner, e, ATK.wave);
          }
        });
      }
    });
    this.fx = this.fx.filter(function (f) { return f.t < f.life; });
  };

  // ---------------------------------------------------------------- AI
  GP.playerAI = function (p) {
    if (!p.canAct()) return;
    p.mx = 0; p.my = 0;
    if (p.ai.cool > 0) p.ai.cool--;
    if (p.ai.spCool > 0) p.ai.spCool--;
    if (p.ai.comboT++ > 70) p.ai.combo = 0;
    if (p.goal) { this.moveTo(p, p.goal.x, p.goal.y); if (p.goal && p.goal.face) p.dir = p.goal.face; return; }
    if (this.peace) return;
    var es = this.actors.filter(function (e) { return e.team === 'enemy' && !e.removed && e.state !== 'dead' && e.state !== 'leap' && e.state !== 'script'; });
    if (!es.length) {
      var hu = this.human;
      if (hu && p !== hu) {
        var fdx = hu.x - 30 - p.x, fdy = (p.ai.lane || p.y) - p.y;
        if (Math.abs(fdx) > 10 || Math.abs(fdy) > 3) { p.mx = clamp(fdx * 0.2, -1, 1); p.my = clamp(fdy * 0.3, -1, 1); p.dir = sgn(fdx); }
      }
      return;
    }
    var best = null, bd = 1e9, self = this;
    es.forEach(function (e) {
      var d = Math.abs(e.x - p.x) + Math.abs(e.y - p.y) * 2;
      if (e.busy()) d += 80;
      if (e.targetedBy && e.targetedBy !== p && e.targetedBy.ai.target === e && !e.boss) d += 45;
      if (e.x < self.cam - 10 || e.x > self.cam + W + 10) d += 200;
      if (d < bd) { bd = d; best = e; }
    });
    var t = best; p.ai.target = t; t.targetedBy = p;
    var side = p.x < t.x ? -1 : 1;
    if (t.boss) side = p.ai.bossSide || side;
    var dist = t.busy() ? 42 : 19 + (t.scale - 1) * 26;
    if (t.x + side * dist < this.cam + 16 || t.x + side * dist > this.cam + W - 16) side = -side;
    if (t.boss && t.x < this.cam + 110) side = 1; else if (t.boss && t.x > this.cam + W - 110) side = -1;
    var lane = p.ai.lane || t.y;
    var ty = t.busy() ? lane : clamp(t.y, lane - 20, lane + 20);
    var dx = t.x + side * dist - p.x, dy = ty - p.y;
    p.dir = t.x > p.x ? 1 : -1;
    if (Math.abs(dx) > 2.5 || Math.abs(dy) > 1.6) {
      p.mx = clamp(dx * 0.3, -1, 1); p.my = clamp(dy * 0.35, -1, 1);
      if (Math.abs(dx) < 1.5) p.mx = 0;
      if (Math.abs(dy) < 1) p.my = 0;
      return;
    }
    if (p.ai.cool > 0 || t.busy()) return;
    var front = 0;
    es.forEach(function (e) {
      var rel = (e.x - p.x) * p.dir;
      if (rel > -4 && rel < 56 && Math.abs(e.y - p.y) < 12 && !e.busy()) front++;
    });
    var wantSp = p.ai.spCool <= 0 && (front >= 2 || this.forceSpecial || this.rng.next() < (t.boss ? 0.3 : 0.12));
    if (wantSp) {
      p.attack(this, p.kind === 'vox' ? 'scream' : 'gsmash');
      p.ai.spCool = this.forceSpecial ? 90 : (p.ai.partner ? 480 : 260);
      return;
    }
    var seq = ['jab', 'cross', 'kick'];
    if (p.kind === 'axe') seq = ['jab', 'jab', 'kick'];
    p.attack(this, seq[p.ai.combo % 3]);
    p.ai.combo++; p.ai.comboT = 0;
  };

  GP.moveTo = function (a, x, y) {
    var dx = x - a.x, dy = y - a.y;
    if (Math.abs(dx) < 1.2 && Math.abs(dy) < 1.2) {
      a.mx = 0; a.my = 0;
      if (a.goal && a.goal.done) { var d = a.goal.done; a.goal = null; d(); } else a.goal = null;
      return true;
    }
    a.mx = clamp(dx * 0.5, -1, 1); a.my = clamp(dy * 0.6, -1, 1);
    if (Math.abs(dx) > 0.5) a.dir = a.goal && a.goal.face ? a.goal.face : sgn(dx);
    return false;
  };

  GP.enemyAI = function (e) {
    if (!e.canAct()) return;
    e.mx = 0; e.my = 0;
    if (e.ai.cool > 0) e.ai.cool--;
    if (e.ai.wait > 0) e.ai.wait--;
    if (e.goal) { this.moveTo(e, e.goal.x, e.goal.y); return; }
    if (this.peace) return;
    var ps = this.players.filter(function (p) { return !p.busy(); });
    if (!ps.length) ps = this.players;
    var t = e.ai.target;
    if (!t || t.busy()) {
      var best = null, bd = 1e9;
      ps.forEach(function (p) { var d = Math.abs(p.x - e.x) + Math.abs(p.y - e.y); if (d < bd) { bd = d; best = p; } });
      t = best; e.ai.target = t;
    }
    if (!t) return;
    var self = this;
    if (!e.ai.engaged && e.ai.wait <= 0) {
      var eng = this.actors.filter(function (o) { return o !== e && o.team === 'enemy' && !o.removed && o.ai.engaged && o.ai.target === t; }).length;
      if (eng < (e.boss ? 9 : 1) || e.boss) e.ai.engaged = true;
    }
    var side = e.x >= t.x ? 1 : -1;
    var dist = e.ai.engaged ? 20 * e.scale + (t.scale - 1) * 12 : 60 + e.ai.slot * 16;
    var tx = t.x + side * dist;
    if (e.ai.engaged && (tx < this.cam + 16 || tx > this.cam + W - 16)) tx = t.x - side * dist;
    tx = e.boss ? clamp(tx, this.cam + 80, this.cam + W - 80) : clamp(tx, this.cam + 14, this.cam + W - 14);
    var ty = e.ai.engaged ? t.y : clamp(t.y + e.ai.yoff, this.floor[0], this.floor[1]);
    var dx = tx - e.x, dy = ty - e.y;
    e.dir = t.x > e.x ? 1 : -1;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 1.6) {
      e.mx = clamp(dx * 0.3, -1, 1); e.my = clamp(dy * 0.35, -1, 1);
      if (Math.abs(dx) < 2) e.mx = 0;
      if (Math.abs(dy) < 1.2) e.my = 0;
      if (!e.ai.engaged) { e.mx *= 0.6; e.my *= 0.6; }
      return;
    }
    if (!e.ai.engaged || e.ai.cool > 0 || t.busy() || t.invuln > 0) return;
    if (e.boss) {
      e.attack(this, this.rng.next() < 0.45 ? 'slam' : 'bpunch');
      e.ai.cool = this.rng.int(40, 80);
    } else {
      e.attack(this, this.rng.next() < 0.25 ? 'ekick' : 'epunch');
      e.ai.cool = this.rng.int(70, 130);
      if (this.rng.next() < 0.35) { e.ai.engaged = false; e.ai.wait = this.rng.int(60, 140); }
    }
  };

  // ---------------------------------------------------------------- step
  GP.step = function () {
    if (this.done) return;
    var I = this.input, PI = this.prevIn, pr = {};
    ['attack', 'jump', 'special', 'start', 'tap', 'left', 'right', 'up', 'down'].forEach(function (k) { pr[k] = !!I[k] && !PI[k]; PI[k] = !!I[k]; });
    this.pressed = pr;
    if (this.mode === 'play' && this.playOverlay()) { this.frame++; return; }
    var r = this.script.next();
    if (r.done) this.done = true;
    var slow = this.slowmo > 0 && (this.slowmo-- % 4 !== 0);
    if (!slow) {
      var self = this;
      this.actors.forEach(function (a) {
        if (a.human) self.humanControl(a); else if (a.team === 'player') self.playerAI(a); else self.enemyAI(a);
      });
      this.actors.forEach(function (a) { a.update(self); });
      this.separate();
      this.updateFx();
      this.updateItems();
      if (this.floor) this.actors.forEach(function (a) {
        if (a.state !== 'leap' && a.state !== 'script' && !a.noClamp) a.y = clamp(a.y, self.floor[0], self.floor[1]);
        if (self.lockCam && a.x > self.cam + 10 && a.x < self.cam + W - 10) a.entered = true;
        if (self.lockCam && (a.team === 'player' || a.entered)) a.x = clamp(a.x, self.cam + 10, self.cam + W - 10);
      });
      this.actors = this.actors.filter(function (a) { return !a.removed; });
      for (var id in this.hudTarget) if (--this.hudTarget[id].t <= 0) delete this.hudTarget[id];
      if (this.shake > 0) this.shake--;
      if (this.hud && this.timerRun) {
        if (++this.timeT >= (this.mode === 'play' ? 60 : 72)) {
          this.timeT = 0; this.time = Math.max(0, this.time - 1);
          if (this.mode === 'play' && this.time === 0) this.timeOver();
        }
      }
    }
    if (this.showTags > 0) this.showTags--;
    if (this.koFlash > 0) this.koFlash--;
    this.banners.forEach(function (b) { b.t++; });
    this.banners = this.banners.filter(function (b) { return b.t < b.dur; });
    this.frame++;
  };
  GP.separate = function () {
    var A = this.actors;
    for (var i = 0; i < A.length; i++) for (var j = i + 1; j < A.length; j++) {
      var a = A[i], b = A[j];
      if (a.busy() || b.busy() || a.z > 0 || b.z > 0 || a.state === 'script' || b.state === 'script') continue;
      var dx = b.x - a.x, dy = b.y - a.y;
      var minx = a.team === b.team ? 18 : 13 + (a.scale + b.scale - 2) * 10;
      if (a.team === b.team && Math.abs(dx) < minx && Math.abs(dy) < 10) {
        var py = (dy > 0 || (dy === 0 && a.id < b.id) ? 1 : -1) * 0.45;
        b.y += py; a.y -= py;
        var px2 = (dx >= 0 ? 1 : -1) * 0.25;
        if (b.state !== 'attack') b.x += px2;
        if (a.state !== 'attack') a.x -= px2;
      } else if (Math.abs(dx) < minx && Math.abs(dy) < 5) {
        {
          var px = (dx >= 0 ? 1 : -1) * 0.4;
          if (b.state !== 'attack') b.x += px;
          if (a.state !== 'attack') a.x -= px;
        }
      }
    }
  };

  // ================================================================ DIRECTOR
  function wait(n) { return (function* () { for (var i = 0; i < n; i++) yield; })(); }
  function* fadeIn(g, n) { n = n || 24; for (var i = 0; i < n; i++) { g.fade = 4 - Math.floor(i / (n / 4)); yield; } g.fade = 0; }
  function* fadeOut(g, n) { n = n || 24; for (var i = 0; i < n; i++) { g.fade = 1 + Math.floor(i / (n / 4)); yield; } g.fade = 4; }
  function* untilClear(g, max) {
    for (var i = 0; i < max; i++) {
      if (!g.enemies().length) return;
      yield;
    }
    g.enemies().forEach(function (e) { if (e.hittable()) { e.hp = 0; e.knock(g, -e.dir, 1); } });
    while (g.enemies().length) yield;
  }
  function* advance(g, camTarget) {
    g.peace = true; g.goT = 0;
    yield* wait(30);
    g.sfx('go');
    g.showGo = true;
    var ps = g.players;
    ps.forEach(function (p) { p.speed = 1.6; });
    while (g.cam < camTarget) {
      var avg = (ps[0].x + ps[1].x) / 2;
      ps.forEach(function (p, i) { if (p.canAct() || p.goal) p.goal = { x: i ? ps[0].x - 28 : g.cam + 200, y: p.ai.lane || p.y }; });
      var want = Math.min(camTarget, Math.max(g.cam, avg - 150));
      g.cam = want;
      if (g.frame % 50 === 0) g.sfx('go');
      yield;
    }
    g.cam = camTarget;
    ps.forEach(function (p) { p.goal = null; p.mx = p.my = 0; p.speed = 1.15; });
    g.showGo = false; g.peace = false;
  }

  function* director(g) {
    var i;
    // ------------------------------------------------ TITLE SCREEN
    g.scene = 'title';
    g.music('title');
    for (i = 0; i < 360; i++) {
      g.sceneT = i;
      if (i === 200) { g.sfx('select'); g.music(null); g.titleSel = true; }
      g.fade = i < 16 ? 4 - Math.floor(i / 4) : i >= 330 ? Math.min(4, 1 + Math.floor((i - 330) / 6)) : 0;
      yield;
    }
    // ------------------------------------------------ STAGE CARD
    g.scene = 'card'; g.sceneT = 0;
    g.sfx('card');
    for (i = 0; i < 170; i++) {
      g.sceneT = i;
      g.fade = i < 16 ? 4 - Math.floor(i / 4) : i >= 146 ? Math.min(4, 1 + Math.floor((i - 146) / 6)) : 0;
      yield;
    }
    // ------------------------------------------------ STREET
    g.scene = 'street'; g.sceneT = 0; g.cam = 0; g.hud = true; g.floor = [124, 172]; g.lockCam = false;
    g.music('stage');
    var vox = g.spawn('vox', { x: -20, y: 142, team: 'player', hp: 100 });
    var axe = g.spawn('axe', { x: -46, y: 162, team: 'player', hp: 100 });
    vox.goal = { x: 92, y: 140 }; axe.goal = { x: 66, y: 162 };
    vox.ai.lane = 138; axe.ai.lane = 160;
    vox.ai.bossSide = -1; axe.ai.bossSide = 1;
    g.showTags = 200;
    yield* fadeIn(g, 20);
    yield* wait(40);
    g.banner('GO!', 80, { scale: 4, col: 'Y', y: 62 });
    g.sfx('go');
    g.lockCam = true; g.timerRun = true;
    yield* wait(30);
    // wave 1
    g.spawn('punk', { x: g.cam + 345, y: 136, target: vox, cool: 50 });
    g.spawn('punk2', { x: g.cam + 360, y: 162, target: axe, cool: 70, slot: 1, yoff: 8 });
    yield* wait(110);
    g.spawn('punk3', { x: g.cam - 26, y: 150, target: axe, cool: 60, slot: 0, yoff: -6 });
    yield* untilClear(g, 1500);
    yield* wait(40);
    yield* advance(g, 380);
    // wave 2
    g.spawn('suit', { x: g.cam + 350, y: 140, target: vox, cool: 50 });
    g.spawn('punk', { x: g.cam + 340, y: 166, target: axe, cool: 70, slot: 1, yoff: 10 });
    g.spawn('punk2', { x: g.cam - 24, y: 134, target: vox, cool: 80, slot: 1, yoff: -10 });
    yield* wait(150);
    g.spawn('bouncer', { x: g.cam + 350, y: 152, target: axe, cool: 60, slot: 2, hp: 36, speed: 0.7 });
    yield* untilClear(g, 1900);
    yield* wait(40);
    yield* advance(g, 940);
    // walk to the club door
    g.peace = true; g.lockCam = false;
    var doorX = 1072;
    vox.calm = true; axe.calm = true;
    vox.goal = { x: doorX + 8, y: 125 }; axe.goal = { x: doorX - 14, y: 127 };
    for (i = 0; i < 200 && (vox.goal || axe.goal); i++) yield;
    vox.dir = -1; axe.dir = 1;
    yield* wait(20);
    g.sfx('door'); g.doorOpen = true;
    yield* wait(24);
    vox.goal = { x: doorX, y: 121 }; axe.goal = { x: doorX - 4, y: 121 };
    g.floor = [116, 172];
    yield* wait(14);
    yield* fadeOut(g, 28);
    g.music(null);
    yield* wait(20);

    // ------------------------------------------------ VENUE / BOSS
    g.scene = 'venue'; g.sceneT = 0; g.cam = 0; g.floor = [128, 172]; g.doorOpen = false;
    g.actors = g.actors.filter(function (a) { return a.team === 'player'; });
    vox.calm = false; axe.calm = false; vox.x = -20; vox.y = 144; axe.x = -44; axe.y = 162;
    vox.goal = { x: 84, y: 142 }; axe.goal = { x: 62, y: 162 };
    var boss = g.spawn('boss', { x: 230, y: 112, hp: 120, boss: true, cool: 40, speed: 0.62 });
    boss.state = 'script'; boss.anim = function (gg, b) { return (Math.floor(gg.frame / 30) % 2) ? 'taunt' : 'stand'; };
    boss.dir = -1; boss.noClamp = true;
    g.music('boss');
    yield* fadeIn(g, 20);
    for (i = 0; i < 70; i++) yield;
    g.bossCard = 0; g.sfx('card');
    for (i = 0; i < 120; i++) { g.bossCard = i; yield; }
    g.bossCard = -1;
    // boss jumps off the stage
    boss.anim = null; boss.state = 'leap'; boss.t = 0;
    boss.leap = { sx: 230, sy: 112, sz: 0, tx: 206, ty: 150, h: 26, dur: 42, done: function () { boss.noClamp = false; } };
    g.sfx('swing');
    for (i = 0; i < 60; i++) yield;
    g.banner('FIGHT!', 70, { scale: 4, col: 'R', y: 64 });
    g.sfx('go');
    g.bossBar = true; g.lockCam = true; g.peace = false;
    while (!g.koDone) {
      if (boss.hp <= 50) g.forceSpecial = true;
      yield;
    }
    // KO sequence (startKO set slowmo)
    while (g.slowmo > 0) yield;
    g.forceSpecial = false; g.peace = true;
    while (boss.state !== 'dead' && boss.state !== 'down') yield;
    yield* wait(20);
    vox.goal = { x: 136, y: 146, face: 1 }; axe.goal = { x: 180, y: 150, face: -1 };
    for (i = 0; i < 150 && (vox.goal || axe.goal); i++) yield;
    vox.dir = 1; axe.dir = -1;
    g.music('clear');
    g.players.forEach(function (p) {
      p.state = 'script'; p.t = 0;
      p.anim = function (gg, a) { return (Math.floor((gg.frame + a.phase) / 14) % 2) ? 'victory' : 'victory2'; };
    });
    g.banner('STAGE CLEAR!', 260, { scale: 3, col: 'Y', y: 56, outline: 'r', band: true });
    g.tally = 0;
    for (i = 0; i < 260; i++) {
      if (i > 70) g.tally = Math.min(g.time * 100, (i - 70) * 60);
      if (i > 70 && i % 4 === 0 && g.tally < g.time * 100) g.sfx('tick');
      yield;
    }
    g.players.forEach(function (p) { p.score += Math.floor(g.time * 50); });
    yield* fadeOut(g, 28);
    g.tally = null;
    // ------------------------------------------------ CONCERT
    g.scene = 'concert'; g.sceneT = 0; g.hud = false; g.bossBar = false; g.floor = null;
    g.actors = [];
    var cb = g.spawn('axe', { x: 66, y: 142, team: 'band', dir: 1 });
    var cv = g.spawn('vox', { x: 152, y: 144, team: 'band', dir: 1 });
    var cd = g.spawn('drum', { x: 212, y: 124, team: 'band', dir: -1 });
    var cr = g.spawn('cap', { x: 270, y: 142, team: 'band', dir: -1 });
    var beat = 3600 / 168;
    [cb, cv, cd, cr].forEach(function (a, k) {
      a.state = 'script';
      a.anim = function (gg) {
        var b = Math.floor((gg.frame - gg.musicStart) / (beat / 2));
        if (a === cv) return (Math.floor(b / 2) % 2) ? 'sing1' : 'sing0';
        if (a === cd) return (b % 2) ? 'drum1' : 'drum0';
        return ((b + k) % 2) ? 'play1' : 'play0';
      };
    });
    g.music('concert');
    yield* fadeIn(g, 24);
    for (i = 0; i < 520; i++) { g.sceneT = i + 24; yield; }
    yield* fadeOut(g, 40);
    g.music(null);
    yield* wait(30);
  }

  GP.startKO = function (a, boss) {
    this.koDone = true;
    this.slowmo = 120;
    this.koFlash = 10;
    this.sfx('ko');
    this.music(null);
    this.banner('K.O.', 150, { scale: 6, col: 'R', y: 52, outline: 'W', band: true });
    boss.hp = 0;
  };

  // ================================================================ PLAY MODE
  GP.humanControl = function (p) {
    var I = this.input, pr = this.pressed;
    if (p.ai.spCool > 0) p.ai.spCool--;
    p.ai.comboT++;
    if (p.goal) {
      if (p.canAct()) { p.mx = p.my = 0; this.moveTo(p, p.goal.x, p.goal.y); if (p.goal && p.goal.face) p.dir = p.goal.face; }
      return;
    }
    if (this.lockInput) { if (p.canAct()) { p.mx = p.my = 0; } return; }
    if (p.state === 'jump') {
      if (pr.attack && !p.jkick && p.z > 1) { p.jkick = true; p.hitSet = []; this.sfx('swing'); }
      return;
    }
    if (p.state === 'attack') {
      if (pr.attack && p.atk && !p.atk.special) p.queued = true;
      return;
    }
    if (!p.canAct()) { p.mx = p.my = 0; p.queued = false; return; }
    var mx = (I.right ? 1 : 0) - (I.left ? 1 : 0), my = (I.down ? 1 : 0) - (I.up ? 1 : 0);
    p.mx = mx; p.my = my;
    if (mx) p.dir = mx;
    if (pr.special && p.ai.spCool <= 0) {
      p.mx = p.my = 0; p.ai.combo = 0;
      p.attack(this, p.kind === 'vox' ? 'scream' : 'gsmash');
      p.ai.spCool = 240;
      return;
    }
    if (pr.jump) {
      p.state = 'jump'; p.t = 0; p.vz = 3.3; p.vx = mx * 1.5; p.jkick = false; p.hitSet = []; p.mx = p.my = 0;
      this.sfx('swing');
      return;
    }
    if (pr.attack || p.queued) {
      p.queued = false;
      if (p.ai.comboT > 40) p.ai.combo = 0;
      var seq = p.kind === 'axe' ? ['jab', 'jab', 'kick'] : ['jab', 'cross', 'kick'];
      p.mx = p.my = 0;
      p.attack(this, seq[p.ai.combo % 3]);
      p.ai.combo = (p.ai.combo + 1) % 3; p.ai.comboT = 0;
    }
  };

  GP.onHumanDeath = function (p) {
    if (p.lives > 1) {
      p.lives--; p.hp = p.maxHp; p.state = 'idle'; p.t = 0; p.rot = 0; p.invuln = 150;
      this.sfx('select');
    } else {
      p.lives = 0; this.contT = 600; this.sfx('card');
    }
  };
  GP.revive = function () {
    var p = this.human;
    p.lives = 3; p.hp = p.maxHp; p.state = 'idle'; p.t = 0; p.rot = 0; p.z = 0; p.invuln = 150;
    this.contT = 0; this.sfx('select');
  };
  GP.timeOver = function () {
    var h = this.human;
    this.time = 99;
    if (!h || h.busy() || h.state === 'script') return;
    this.banner('TIME OVER', 100, { scale: 3, col: 'R', y: 62, band: true });
    h.hp = 0; h.knock(this, -h.dir, 0.8);
  };
  // returns true when the world is frozen (pause / continue / game over)
  GP.playOverlay = function () {
    var pr = this.pressed;
    if (this.contT > 0) {
      this.contT--;
      if (pr.start || pr.attack || pr.tap) this.revive();
      else if (this.contT === 0) { this.overT = 220; this.music(null); this.sfx('ko'); }
      return true;
    }
    if (this.overT > 0) { if (--this.overT === 0) this.restart = true; return true; }
    if (this.restart) return true;
    if (this.canPause && pr.start) { this.paused = !this.paused; this.sfx('tick'); }
    return !!this.paused;
  };
  GP.updateItems = function () {
    var h = this.human, self = this;
    if (!h || !this.items.length) return;
    this.items = this.items.filter(function (it) {
      it.t++;
      if (h.canAct() && h.z === 0 && Math.abs(h.x - it.x) < 13 && Math.abs(h.y - it.y) < 8) {
        h.hp = Math.min(h.maxHp, h.hp + 45); h.score += 1000;
        self.sfx('pickup'); self.popup(it.x, it.y, 24, 'YUM!');
        return false;
      }
      return true;
    });
  };

  function* untilClearP(g) { while (g.enemies().length) yield; }
  function* scrollTo(g, target) {
    yield* wait(30);
    g.showGo = true; g.sfx('go');
    var h = g.human;
    while (g.cam < target) {
      g.cam = Math.min(target, Math.max(g.cam, h.x - 150));
      if (g.frame % 60 === 0) g.sfx('go');
      yield;
    }
    g.cam = target; g.showGo = false;
    g.time = 99;
  }
  function anyPress(g) { var p = g.pressed; return p.start || p.attack || p.tap || p.jump || p.special; }

  function* playDirector(g) {
    var i;
    // ------------------------------------------------ TITLE
    g.scene = 'title'; g.sceneT = 0;
    g.music('title');
    yield* fadeIn(g, 16);
    for (i = 0; ; i++) { g.sceneT = i; if (i > 10 && anyPress(g)) break; yield; }
    g.titleSel = true; g.music(null); g.sfx('select');
    for (i = 0; i < 45; i++) { g.sceneT++; yield; }
    yield* fadeOut(g, 20);
    // ------------------------------------------------ CHARACTER SELECT
    g.scene = 'select'; g.selIdx = 0; g.selDone = false; g.sceneT = 0;
    g.music('boss');
    yield* fadeIn(g, 12);
    for (i = 0; ; i++) {
      g.sceneT = i;
      var pr = g.pressed;
      if (pr.left && g.selIdx !== 0) { g.selIdx = 0; g.sfx('tick'); }
      if (pr.right && g.selIdx !== 1) { g.selIdx = 1; g.sfx('tick'); }
      if (pr.tap && g.tapX !== undefined) {
        var k = g.tapX < W / 2 ? 0 : 1;
        if (k === g.selIdx && i > 10) break;
        g.selIdx = k; g.sfx('tick');
      } else if (i > 10 && (pr.attack || pr.start)) break;
      yield;
    }
    g.sfx('select'); g.selDone = true; g.music(null);
    for (i = 0; i < 45; i++) { g.sceneT++; yield; }
    yield* fadeOut(g, 20);
    var kind = g.selIdx === 0 ? 'vox' : 'axe', other = kind === 'vox' ? 'axe' : 'vox';
    // ------------------------------------------------ STAGE CARD
    g.scene = 'card'; g.sceneT = 0;
    g.sfx('card');
    for (i = 0; i < 150; i++) {
      g.sceneT = i;
      g.fade = i < 16 ? 4 - Math.floor(i / 4) : i >= 126 ? Math.min(4, 1 + Math.floor((i - 126) / 6)) : 0;
      yield;
    }
    // ------------------------------------------------ STREET
    g.scene = 'street'; g.sceneT = 0; g.cam = 0; g.hud = true; g.floor = [124, 172]; g.lockCam = false;
    g.music('stage');
    var h = g.spawn(kind, { x: -20, y: 142, team: 'player', hp: 100, human: true });
    var c = g.spawn(other, { x: -46, y: 162, team: 'player', hp: 100 });
    g.human = h; h.lives = 3; h.speed = 1.25;
    h.ai.lane = 140; c.ai.lane = 160; c.ai.partner = true;
    c.ai.bossSide = 1;
    g.lockInput = true;
    h.goal = { x: 92, y: 140 }; c.goal = { x: 62, y: 162 };
    g.showTags = 200;
    yield* fadeIn(g, 20);
    for (i = 0; i < 90 && (h.goal || c.goal); i++) yield;
    h.goal = null; c.goal = null;
    g.lockInput = false; g.lockCam = true; g.canPause = true; g.timerRun = true; g.time = 99;
    g.banner('GO!', 80, { scale: 4, col: 'Y', y: 62 });
    g.sfx('go');
    yield* wait(50);
    // wave 1
    g.spawn('punk', { x: g.cam + 345, y: 136, target: h, cool: 60 });
    g.spawn('punk2', { x: g.cam + 360, y: 162, target: c, cool: 80, slot: 1, yoff: 8 });
    yield* wait(160);
    g.spawn('punk3', { x: g.cam - 26, y: 150, target: h, cool: 70, yoff: -6 });
    yield* untilClearP(g);
    yield* scrollTo(g, 380);
    // wave 2
    g.spawn('suit', { x: g.cam + 350, y: 140, target: h, cool: 60 });
    g.spawn('punk', { x: g.cam + 340, y: 166, target: c, cool: 80, slot: 1, yoff: 10 });
    g.spawn('punk2', { x: g.cam - 24, y: 134, target: h, cool: 90, slot: 1, yoff: -10 });
    yield* wait(170);
    g.spawn('bouncer', { x: g.cam + 350, y: 152, target: h, cool: 70, slot: 2, hp: 36, speed: 0.7 }).drop = 'pizza';
    yield* untilClearP(g);
    yield* scrollTo(g, 680);
    // wave 3
    g.spawn('punk3', { x: g.cam + 345, y: 132, target: h, cool: 50 });
    g.spawn('suit', { x: g.cam - 26, y: 160, target: c, cool: 70, slot: 1 });
    g.spawn('punk2', { x: g.cam + 360, y: 156, target: h, cool: 90, slot: 2, yoff: 12 });
    yield* wait(150);
    g.spawn('bouncer', { x: g.cam - 30, y: 140, target: h, cool: 80, slot: 2, hp: 36, speed: 0.7 }).drop = 'pizza';
    g.spawn('punk', { x: g.cam + 350, y: 146, target: c, cool: 100, slot: 3, yoff: -12 });
    yield* untilClearP(g);
    yield* scrollTo(g, 940);
    // the club door
    var doorX = 1072;
    g.doorHint = true;
    while (!(Math.abs(h.x - doorX) < 26 && h.y < 138 && h.canAct())) yield;
    g.doorHint = false; g.lockInput = true; g.timerRun = false; g.canPause = false;
    h.calm = true; c.calm = true;
    h.goal = { x: doorX + 8, y: 125 }; c.goal = { x: doorX - 14, y: 127 };
    for (i = 0; i < 160 && (h.goal || c.goal); i++) yield;
    h.dir = -1; c.dir = 1;
    g.sfx('door'); g.doorOpen = true;
    yield* wait(24);
    g.floor = [116, 172]; g.lockCam = false;
    h.goal = { x: doorX, y: 121 }; c.goal = { x: doorX - 4, y: 121 };
    yield* wait(14);
    yield* fadeOut(g, 28);
    g.music(null);
    yield* wait(16);
    // ------------------------------------------------ VENUE / BOSS
    g.scene = 'venue'; g.sceneT = 0; g.cam = 0; g.floor = [128, 172]; g.doorOpen = false;
    g.actors = g.actors.filter(function (a) { return a.team === 'player'; });
    g.items = [];
    h.calm = false; c.calm = false; h.x = -20; h.y = 144; c.x = -44; c.y = 162; h.dir = c.dir = 1;
    h.goal = { x: 84, y: 142 }; c.goal = { x: 62, y: 162 };
    if (h.hp < 70) g.items.push({ x: 34, y: 152, kind: 'pizza', t: 0 });
    var boss = g.spawn('boss', { x: 230, y: 112, hp: 140, boss: true, cool: 50, speed: 0.62, target: h });
    boss.state = 'script'; boss.anim = function (gg) { return (Math.floor(gg.frame / 30) % 2) ? 'taunt' : 'stand'; };
    boss.dir = -1; boss.noClamp = true;
    g.music('boss');
    yield* fadeIn(g, 20);
    for (i = 0; i < 70; i++) yield;
    g.bossCard = 0; g.sfx('card');
    for (i = 0; i < 120; i++) { g.bossCard = i; if (i > 30 && i < 100 && anyPress(g)) i = 100; yield; }
    g.bossCard = -1;
    boss.anim = null; boss.state = 'leap'; boss.t = 0;
    boss.leap = { sx: 230, sy: 112, sz: 0, tx: 206, ty: 150, h: 26, dur: 42, done: function () { boss.noClamp = false; } };
    g.sfx('swing');
    for (i = 0; i < 56; i++) yield;
    h.goal = null; c.goal = null;
    g.banner('FIGHT!', 70, { scale: 4, col: 'R', y: 64 });
    g.sfx('go');
    g.bossBar = true; g.lockCam = true; g.lockInput = false; g.canPause = true; g.timerRun = true; g.time = 99;
    while (!g.koDone) {
      if (boss.hp <= 50) g.forceSpecial = true;
      yield;
    }
    while (g.slowmo > 0) yield;
    g.forceSpecial = false; g.peace = true; g.lockInput = true; g.timerRun = false; g.canPause = false;
    while (boss.state !== 'dead' && boss.state !== 'down') yield;
    yield* wait(20);
    h.goal = { x: 136, y: 146, face: 1 }; c.goal = { x: 180, y: 150, face: -1 };
    for (i = 0; i < 150 && (h.goal || c.goal); i++) yield;
    h.dir = 1; c.dir = -1;
    g.music('clear');
    g.players.forEach(function (p) {
      p.state = 'script'; p.t = 0;
      p.anim = function (gg, a) { return (Math.floor((gg.frame + a.phase) / 14) % 2) ? 'victory' : 'victory2'; };
    });
    g.banner('STAGE CLEAR!', 250, { scale: 3, col: 'Y', y: 56, outline: 'r', band: true });
    g.tally = 0;
    for (i = 0; i < 250; i++) {
      if (i > 70) g.tally = Math.min(g.time * 100, (i - 70) * 60);
      if (i > 70 && i % 4 === 0 && g.tally < g.time * 100) g.sfx('tick');
      yield;
    }
    h.score += g.time * 100;
    yield* fadeOut(g, 28);
    g.tally = null;
    // ------------------------------------------------ CONCERT + END
    g.scene = 'concert'; g.sceneT = 0; g.hud = false; g.bossBar = false; g.floor = null; g.lockCam = false;
    g.actors = [];
    var cb = g.spawn('axe', { x: 66, y: 142, team: 'band', dir: 1 });
    var cv = g.spawn('vox', { x: 152, y: 144, team: 'band', dir: 1 });
    var cd = g.spawn('drum', { x: 212, y: 124, team: 'band', dir: -1 });
    var cr = g.spawn('cap', { x: 270, y: 142, team: 'band', dir: -1 });
    var beat = 3600 / 168;
    [cb, cv, cd, cr].forEach(function (a, k) {
      a.state = 'script';
      a.anim = function (gg) {
        var b = Math.floor((gg.frame - gg.musicStart) / (beat / 2));
        if (a === cv) return (Math.floor(b / 2) % 2) ? 'sing1' : 'sing0';
        if (a === cd) return (b % 2) ? 'drum1' : 'drum0';
        return ((b + k) % 2) ? 'play1' : 'play0';
      };
    });
    g.music('concert');
    yield* fadeIn(g, 24);
    for (i = 0; i < 240; i++) { g.sceneT = i + 24; yield; }
    g.endScreen = true;
    for (i = 0; ; i++) { g.sceneT++; if (i > 60 && anyPress(g)) break; yield; }
    g.sfx('select');
    yield* fadeOut(g, 30);
    g.music(null);
    g.restart = true;
    for (;;) yield;
  }

  function bigSprite(buf, s, x, y, k) {
    var i, j, c;
    for (j = 0; j < s.h; j++) for (i = 0; i < s.w; i++) if (s.px[j * s.w + i] !== MA.TR) buf.rect(x + i * k - 2, y + j * k - 2, k + 4, k + 4, K);
    for (j = 0; j < s.h; j++) for (i = 0; i < s.w; i++) { c = s.px[j * s.w + i]; if (c !== MA.TR) buf.rect(x + i * k, y + j * k, k, k, c); }
  }
  function drawSelect(buf, g) {
    buf.clear(K);
    var t = g.sceneT;
    for (var y = 0; y < H; y += 2) buf.rect(0, y, W, 1, ((y >> 1) + (t >> 2)) % 6 === 0 ? C.q : K);
    buf.title(22, 0, 196, 68, 62, -6, true);
    buf.textC('SELECT YOUR ROCKER', W / 2, 62, C.W, { scale: 1, outline: C.r });
    var chars = [
      { head: 'vox', name: 'VOX', role: 'VOCALS', sp: 'SCREAM WAVE' },
      { head: 'axe', name: 'AXE', role: 'GUITAR', sp: 'GUITAR SMASH' }
    ];
    chars.forEach(function (ch, k) {
      var px = k ? 170 : 54, py = 76, pw = 96, ph = 82;
      var sel = g.selIdx === k;
      var blink = g.selDone ? (t >> 2) % 2 : (t >> 4) % 2;
      buf.rect(px - 2, py - 2, pw + 4, ph + 4, sel ? (blink ? C.Y : C.R) : C.E);
      buf.rect(px, py, pw, ph, sel ? C.q : C.Q);
      if (sel) buf.drect(px, py, pw, ph, C.r, 3);
      var hs = HS[ch.head];
      bigSprite(buf, hs, px + Math.round((pw - hs.w * 3) / 2), py + 4, 3);
      buf.textC(ch.name, px + pw / 2, py + 48, sel ? C.Y : C.W, { scale: 2, outline: K });
      buf.textC(ch.role, px + pw / 2, py + 63, C.L);
      buf.textC(ch.sp, px + pw / 2, py + 72, sel ? C.N : C.G);
    });
    var other = g.selIdx === 0 ? 'AXE' : 'VOX';
    buf.textC('PARTNER: ' + other + ' (CPU)', W / 2, 162, C.L);
    if ((t >> 4) % 2 === 0 && !g.selDone) buf.textC('< >  CHOOSE     HIT = OK', W / 2, 172, C.W);
  }
  function drawPizza(buf, x, y, t) {
    buf.ellipse(x, y, 8, 3, K);
    buf.ellipse(x, y - 1, 7, 2.6, C.O);
    buf.ellipse(x, y - 1, 5.5, 1.8, C.Y);
    buf.pset(x - 3, y - 1, C.R); buf.pset(x + 2, y - 2, C.R); buf.pset(x + 1, y, C.R); buf.pset(x - 1, y - 2, C.n);
    if ((t >> 3) % 2) buf.pset(x + 4, y - 4, C.w);
  }
  function drawPlayOverlay(buf, g) {
    if (g.doorHint && (g.frame >> 4) % 2 === 0) {
      var dx = 1072 - Math.round(g.cam);
      buf.textC('ENTER', dx, 90, C.Y, { outline: K });
      buf.poly([dx - 5, 99, dx + 5, 99, dx, 105], K); buf.poly([dx - 3, 100, dx + 3, 100, dx, 104], C.Y);
    }
    if (g.paused) {
      buf.rect(0, 74, W, 30, K);
      if ((g.frame >> 4) % 2 === 0) buf.textC('PAUSE', W / 2, 78, C.Y, { scale: 3, outline: C.r, bold: true });
      buf.textC('START = WEITER', W / 2, 100 - 4, C.L);
    }
    if (g.contT > 0) {
      buf.rect(0, 58, W, 62, K); buf.rect(0, 59, W, 1, C.r); buf.rect(0, 118, W, 1, C.r);
      buf.textC('CONTINUE?', W / 2, 64, C.W, { scale: 3, outline: C.r, bold: true });
      buf.textC(String(Math.ceil(g.contT / 60) - 1 < 0 ? 0 : Math.ceil(g.contT / 60) - 1), W / 2, 88, C.Y, { scale: 3, outline: K, bold: true });
      if ((g.frame >> 4) % 2 === 0) buf.textC('PRESS START', W / 2, 110, C.W);
    }
    if (g.overT > 0) {
      buf.rect(0, 66, W, 44, K);
      buf.textC('GAME OVER', W / 2, 76, C.R, { scale: 4, outline: C.W, bold: true });
    }
    if (g.endScreen) {
      buf.rect(0, 70, W, 46, K); buf.rect(0, 71, W, 1, C.r); buf.rect(0, 114, W, 1, C.r);
      buf.textC('THANK YOU FOR PLAYING!', W / 2, 76, C.Y, { scale: 2, outline: C.r });
      buf.textC('SCORE ' + pad(g.human ? g.human.score : 0, 7), W / 2, 94, C.W);
      if ((g.frame >> 4) % 2 === 0) buf.textC('PRESS START', W / 2, 104, C.N);
    }
  }

  // ================================================================ BACKGROUNDS
  var hash = MA.hash;

  function drawSky(buf, cam, t) {
    var y;
    for (y = 0; y < 100; y++) {
      var c, lv = 0, c2;
      if (y < 16) { c = C.v; }
      else if (y < 40) { c = C.v; c2 = C.V; lv = Math.floor((y - 16) / 24 * 16); }
      else if (y < 70) { c = C.V; c2 = C.p; lv = Math.floor((y - 40) / 30 * 6); }
      else { c = C.V; c2 = C.p; lv = 6; }
      buf.rect(0, y, W, 1, c);
      if (lv) for (var x = 0; x < W; x++) if (MA.BAYER[((y & 3) << 2) | (x & 3)] < lv) buf.pset(x, y, c2);
    }
    // stars
    for (var i = 0; i < 60; i++) {
      var sx = Math.floor(hash(i * 3 + 1) * 700 - cam * 0.05) % 340, sy = Math.floor(hash(i * 3 + 2) * 50);
      if (sx < 0) sx += 340;
      var tw = (Math.floor(t / 20) + i) % 7 === 0;
      buf.pset(sx, sy, tw ? C.L : (i % 3 ? C.G : C.W));
    }
  }
  function drawSkyline(buf, cam, t, par, colB, winCols, seed, base) {
    for (var i = 0; i < 60; i++) {
      var bw = 22 + Math.floor(hash(seed + i * 5) * 26), bh = 26 + Math.floor(hash(seed + i * 5 + 1) * 46);
      var bx = Math.round(i * 34 - cam * par) - 20;
      if (bx > W || bx + bw < 0) continue;
      var top = base - bh;
      buf.rect(bx, top, bw, base - top + 30, colB);
      if (hash(seed + i * 5 + 3) < 0.3) { buf.rect(bx + 4, top - 6, 2, 6, colB); buf.pset(bx + 4, top - 7, (t >> 5) % 2 ? C.R : colB); }
      if (hash(seed + i * 5 + 4) < 0.25) { buf.rect(bx + bw - 10, top - 8, 7, 6, colB); buf.rect(bx + bw - 9, top - 2, 1, 2, colB); buf.rect(bx + bw - 5, top - 2, 1, 2, colB); }
      for (var wy = top + 4; wy < base + 20; wy += 5) for (var wx = bx + 3; wx < bx + bw - 3; wx += 4) {
        var h = hash(seed * 7 + i * 1000 + wx * 3 + wy * 17);
        if (h < 0.22) buf.rect(wx, wy, 2, 2, winCols[Math.floor(h * 100) % winCols.length]);
      }
    }
  }

  // street facade segments (world x)
  var STREET = [
    { x: -40, w: 220, type: 'brick', top: 36 },
    { x: 180, w: 130, type: 'bar', top: 44 },
    { x: 310, w: 44, type: 'alley' },
    { x: 354, w: 210, type: 'brick2', top: 30 },
    { x: 564, w: 150, type: 'vinyl', top: 40 },
    { x: 714, w: 50, type: 'alley' },
    { x: 764, w: 220, type: 'brick', top: 34, posters2: true },
    { x: 984, w: 300, type: 'club', top: 26 }
  ];
  var LAMPS = [120, 470, 830];

  function brickWall(buf, x0, w, top, base, cA, cB, offs) {
    buf.rect(x0, top, w, base - top, cA);
    var row = 0;
    for (var y = top + 6; y < base; y += 4, row++) {
      buf.rect(x0, y, w, 1, cB);
      var o = ((row + offs) & 1) * 4;
      for (var x = x0 + o; x < x0 + w; x += 8) buf.rect(x, y + 1, 1, 3, cB);
    }
    buf.rect(x0, top, w, 4, C.x); buf.rect(x0, top + 4, w, 2, C.q);
  }
  function windowsRow(buf, x0, w, y, seed, t) {
    for (var x = x0 + 10; x + 14 < x0 + w; x += 30) {
      buf.rect(x - 1, y - 1, 14, 18, C.x);
      var lit = hash(seed + x) < 0.45;
      buf.rect(x, y, 12, 16, lit ? C.O : C.k);
      if (lit) { buf.rect(x, y, 12, 6, C.Y); buf.rect(x + 2, y + 9, 3, 7, C.A); }
      else { buf.line(x + 2, y + 13, x + 8, y + 3, C.D); }
      buf.rect(x + 5, y, 1, 16, C.x); buf.rect(x, y + 8, 12, 1, C.x);
      buf.rect(x - 2, y + 16, 16, 2, C.G);
    }
  }
  function poster(buf, x, y, kind) {
    if (kind === 0) {
      buf.rect(x - 1, y - 1, 53, 38, C.K);
      buf.rect(x, y, 51, 36, C.k);
      for (var i = 0; i < 51; i += 3) buf.rect(x + i, y, 2, 2 + Math.floor(hash(i + 7) * 5), C.R);
      buf.text('MRS.', x + 2, y + 6, C.W);
      buf.text('ANTHROPE', x + 2, y + 14, C.W);
      buf.text('LIVE!', x + 11, y + 25, C.R);
      buf.rect(x + 44, y + 30, 2, 2, C.N);
    } else {
      var cols = [C.Y, C.N, C.W, C.C, C.P];
      var c = cols[kind % cols.length];
      buf.rect(x - 1, y - 1, 20, 26, C.K);
      buf.rect(x, y, 18, 24, c);
      buf.rect(x + 3, y + 3, 12, 8, C.k);
      buf.rect(x + 3, y + 14, 12, 2, C.k); buf.rect(x + 3, y + 18, 8, 2, C.k);
      buf.pset(x + 17, y + 23, C.L);
    }
  }
  function drawLamp(buf, sx, t) {
    buf.rect(sx - 1, 46, 3, 72, C.D); buf.rect(sx - 2, 112, 5, 6, C.E);
    buf.rect(sx, 44, 12, 2, C.D);
    buf.rect(sx + 9, 46, 6, 3, C.E); buf.rect(sx + 10, 49, 4, 1, C.F);
    var on = !((t % 97 > 90) && (t % 7 < 3));
    if (on) {
      buf.poly([sx + 10, 50, sx + 14, 50, sx + 30, 120, sx - 6, 120], C.F, 2);
      buf.ellipse(sx + 12, 124, 20, 5, C.F, 3);
    }
  }
  function drawSegment(buf, s, sx, t) {
    var base = 118, i;
    if (s.type === 'brick' || s.type === 'brick2') {
      brickWall(buf, sx, s.w, s.top, base, s.type === 'brick' ? C.X : C.x, s.type === 'brick' ? C.x : C.q, s.x);
      windowsRow(buf, sx, s.w, s.top + 10, s.x, t);
      buf.rect(sx, base - 4, s.w, 4, C.q);
      if (s.type === 'brick') {
        poster(buf, sx + 20, 70, 0);
        poster(buf, sx + 84, 74, s.posters2 ? 3 : 1);
        poster(buf, sx + 108, 78, 2);
        poster(buf, sx + 150, 70, s.posters2 ? 0 : 4);
        if (!s.posters2) { buf.rect(sx + 190, 82, 22, 36, C.k); buf.rect(sx + 191, 83, 20, 35, C.q); buf.rect(sx + 207, 99, 2, 2, C.Y); }
      } else {
        // graffiti
        buf.text('PUNX', sx + 18, 66, C.N, { scale: 3, outline: C.m, bold: true });
        for (i = 0; i < 8; i++) buf.rect(sx + 22 + i * 9, 87, 1, 2 + Math.floor(hash(i + 31) * 8), C.N);
        buf.text('MRS.A', sx + 110, 92, C.W, { scale: 2, outline: C.r });
        buf.text('NO FUTURE?', sx + 108, 74, C.Y, { shadow: C.K });
        poster(buf, sx + 176, 76, 1);
      }
    } else if (s.type === 'bar') {
      buf.rect(sx, s.top, s.w, base - s.top, C.E);
      for (var y = s.top + 4; y < base; y += 6) buf.rect(sx, y, s.w, 1, C.D);
      buf.rect(sx, s.top, s.w, 4, C.D);
      windowsRow(buf, sx, s.w, s.top + 8, s.x + 5, t);
      // storefront
      buf.rect(sx + 6, 76, s.w - 12, 42, C.K);
      buf.rect(sx + 8, 78, 70, 38, C.k);
      buf.line(sx + 14, 112, sx + 40, 80, C.D); buf.line(sx + 20, 112, sx + 46, 80, C.D);
      // patrons silhouettes
      buf.circle(sx + 30, 100, 4, C.Q); buf.rect(sx + 25, 104, 10, 12, C.Q);
      buf.circle(sx + 55, 98, 4, C.Q); buf.rect(sx + 50, 102, 10, 14, C.Q);
      buf.rect(sx + 84, 82, 36, 36, C.r); buf.rect(sx + 86, 84, 32, 34, C.q); buf.rect(sx + 112, 100, 2, 3, C.Y);
      var flick = (t % 140) > 128 && (t % 5 < 2);
      buf.rect(sx + 18, 56, 64, 16, C.K);
      buf.text('BAR', sx + 33, 58, flick ? C.q : C.R, { scale: 2, outline: flick ? C.K : C.r });
      buf.text('OPEN', sx + 92, 70, (t >> 4) % 2 ? C.N : C.n);
    } else if (s.type === 'alley') {
      buf.rect(sx, 52, s.w, base - 52, C.Q);
      for (var fy = 56; fy < 108; fy += 18) {
        buf.rect(sx + 2, fy, s.w - 4, 2, C.D);
        for (var fx = sx + 2; fx < sx + s.w - 2; fx += 4) buf.rect(fx, fy - 6, 1, 6, C.D);
      }
      buf.rect(sx + 6, 96, s.w - 12, 22, C.n); buf.rect(sx + 6, 96, s.w - 12, 3, C.m);
      buf.rect(sx + 8, 101, s.w - 16, 1, C.m);
    } else if (s.type === 'vinyl') {
      buf.rect(sx, s.top, s.w, base - s.top, C.D);
      buf.rect(sx, s.top, s.w, 4, C.k);
      windowsRow(buf, sx, s.w, s.top + 8, s.x + 9, t);
      buf.rect(sx + 8, 76, 96, 40, C.K); buf.rect(sx + 10, 78, 92, 36, C.u);
      for (i = 0; i < 4; i++) {
        var rx = sx + 22 + i * 22;
        buf.circle(rx, 98, 8, C.K); buf.ring(rx, 98, 6, C.k); buf.circle(rx, 98, 2.5, [C.R, C.N, C.Y, C.W][i]);
      }
      buf.rect(sx + 110, 80, 32, 38, C.k); buf.rect(sx + 112, 82, 28, 36, C.E); buf.rect(sx + 134, 98, 2, 3, C.Y);
      var on = (t % 90) < 80;
      buf.text('VINYL', sx + 22, 58, on ? C.N : C.m, { scale: 2, outline: on ? C.m : C.K });
    } else if (s.type === 'club') {
      buf.rect(sx, s.top, s.w, base - s.top, C.k);
      for (var by = s.top + 3; by < base; by += 8) buf.rect(sx, by, s.w, 1, C.Q);
      // marquee
      var mx = sx + 30, mw = 196;
      buf.rect(mx, 34, mw, 30, C.q); buf.rect(mx + 3, 37, mw - 6, 24, C.K);
      for (i = 0; i < mw; i += 6) {
        var on2 = ((i / 6 + Math.floor(t / 8)) % 2) === 0;
        buf.rect(mx + i, 34, 2, 2, on2 ? C.Y : C.O); buf.rect(mx + i, 62, 2, 2, on2 ? C.O : C.Y);
      }
      buf.textC('THE PIT', mx + mw / 2, 40, C.Y, { scale: 2, outline: C.r });
      buf.textC('LIVE MUSIC CLUB', mx + mw / 2, 54, C.W);
      buf.rect(mx + 20, 66, mw - 40, 11, C.r); buf.rect(mx + 21, 67, mw - 42, 9, C.R);
      buf.textC('TONITE: MRS. ANTHROPE', mx + mw / 2, 68, C.W);
      // door
      var dx = sx + 1072 - s.x - 20;
      buf.rect(dx - 3, 80, 46, 38, C.Y); buf.rect(dx - 1, 82, 42, 36, C.K);
      if (!MA._doorOpen) {
        buf.rect(dx, 83, 19, 35, C.r); buf.rect(dx + 21, 83, 19, 35, C.r);
        buf.circle(dx + 9, 94, 3, C.k); buf.circle(dx + 30, 94, 3, C.k);
        buf.rect(dx + 17, 100, 2, 4, C.Y); buf.rect(dx + 21, 100, 2, 4, C.Y);
      } else {
        buf.rect(dx, 83, 40, 35, C.R); buf.rect(dx, 83, 40, 35, C.O);
        buf.drect(dx, 83, 40, 35, C.Y, 6);
        buf.rect(dx, 83, 6, 35, C.r); buf.rect(dx + 34, 83, 6, 35, C.r);
      }
      // posters next to door
      poster(buf, dx - 62, 78, 0); poster(buf, dx + 50, 82, 2);
      // carpet + rope
      buf.rect(dx + 2, 118, 36, 10, C.r);
      buf.rect(dx - 14, 108, 3, 14, C.Y); buf.rect(dx + 51, 108, 3, 14, C.Y);
      buf.line(dx - 12, 110, dx - 4, 114, C.R);
      buf.line(dx + 44, 114, dx + 52, 110, C.R);
    }
  }

  function drawStreet(buf, g) {
    var cam = Math.round(g.cam), t = g.frame;
    drawSky(buf, cam, t);
    drawSkyline(buf, cam, t, 0.25, C.Q, [C.O, C.Y, C.F, C.c], 11, 70);
    drawSkyline(buf, cam, t, 0.45, C.k, [C.O, C.Y, C.R], 77, 84);
    MA._doorOpen = g.doorOpen;
    STREET.forEach(function (s) {
      var sx = s.x - cam;
      if (sx > W || sx + s.w < 0) return;
      drawSegment(buf, s, sx, t);
    });
    // sidewalk
    buf.rect(0, 118, W, 26, C.I);
    buf.rect(0, 118, W, 1, C.L);
    buf.rect(0, 127, W, 1, C.i); buf.rect(0, 136, W, 1, C.i);
    for (var y = 119; y < 144; y++) {
      var off = Math.floor((y - 118) * 0.6);
      for (var x = -((cam - off) % 32 + 32) % 32; x < W; x += 32) buf.pset(x, y, C.i);
    }
    // curb + street
    buf.rect(0, 144, W, 2, C.L); buf.rect(0, 146, W, 2, C.G);
    buf.rect(0, 148, W, 32, C.Z);
    buf.drect(0, 148, W, 32, C.z, 3);
    for (var lx = -((cam * 1) % 48 + 48) % 48; lx < W; lx += 48) buf.rect(lx, 168, 22, 2, C.L);
    buf.rect(0, 148, W, 1, C.z);
    LAMPS.forEach(function (lx2) { var s = lx2 - cam; if (s > -40 && s < W + 40) drawLamp(buf, s, t + lx2); });
    // props: hydrant / trash cans
    [60, 300, 610, 900].forEach(function (px, i) {
      var s = px - cam; if (s < -20 || s > W + 20) return;
      if (i % 2 === 0) {
        buf.rect(s - 1, 110, 10, 14, C.K); buf.rect(s, 111, 8, 12, C.G); buf.rect(s, 111, 8, 2, C.L); buf.rect(s + 2, 115, 1, 7, C.E); buf.rect(s + 5, 115, 1, 7, C.E);
      } else {
        buf.rect(s, 112, 6, 10, C.K); buf.rect(s + 1, 113, 4, 9, C.R); buf.rect(s - 1, 115, 8, 2, C.r); buf.rect(s + 1, 111, 4, 2, C.r);
      }
    });
  }

  function truss(buf, x, y0, y1, t, lamps, beatOn) {
    buf.rect(x, y0, 2, y1 - y0, C.E); buf.rect(x + 12, y0, 2, y1 - y0, C.E);
    for (var y = y0; y < y1; y += 12) { buf.line(x + 2, y, x + 11, y + 6, C.D); buf.line(x + 11, y + 6, x + 2, y + 12, C.D); buf.rect(x, y, 14, 1, C.D); }
    lamps.forEach(function (ly, i) {
      var on = ((i + beatOn) % 2) === 0;
      buf.circle(x + 7, ly, 3.2, C.K);
      buf.circle(x + 7, ly, 2.4, on ? (i % 2 ? C.N : C.R) : (i % 2 ? C.m : C.q));
      if (on) buf.pset(x + 6, ly - 1, C.w);
    });
  }
  function beam(buf, x0, y0, ang, len, spread, col, level) {
    var a1 = ang - spread, a2 = ang + spread;
    buf.poly([x0, y0, x0 + Math.sin(a1) * len, y0 + Math.cos(a1) * len, x0 + Math.sin(a2) * len, y0 + Math.cos(a2) * len], col, level);
  }
  function drawAmp(buf, x, y) {
    // stack of two cabinets + head, bottom at y
    for (var k = 0; k < 2; k++) {
      var cy = y - 16 * (k + 1);
      buf.rect(x, cy, 32, 16, C.K); buf.rect(x + 1, cy + 1, 30, 14, C.k);
      buf.drect(x + 3, cy + 3, 26, 10, C.E, 6);
    }
    buf.rect(x, y - 41, 32, 9, C.K); buf.rect(x + 1, y - 40, 30, 7, C.r);
    buf.rect(x + 3, y - 38, 26, 3, C.k);
    for (var i = 0; i < 6; i++) buf.pset(x + 5 + i * 4, y - 37, C.Y);
  }
  function drawKit(buf, cx, by) {
    // stands
    buf.line(cx - 22, by, cx - 20, by - 28, C.L); buf.line(cx + 22, by, cx + 20, by - 30, C.L);
    buf.line(cx - 26, by, cx - 24, by - 20, C.L);
    buf.ellipse(cx - 20, by - 29, 7, 1.5, C.N); buf.ellipse(cx + 20, by - 31, 8, 1.5, C.N);
    buf.ellipse(cx - 24, by - 21, 5, 1.2, C.Y);
    // toms
    buf.ellipse(cx - 8, by - 20, 5, 4, C.K); buf.ellipse(cx - 8, by - 20, 4, 3, C.R); buf.rect(cx - 12, by - 23, 8, 1, C.W);
    buf.ellipse(cx + 8, by - 20, 5, 4, C.K); buf.ellipse(cx + 8, by - 20, 4, 3, C.R); buf.rect(cx + 4, by - 23, 8, 1, C.W);
    buf.ellipse(cx + 18, by - 8, 6, 7, C.K); buf.ellipse(cx + 18, by - 8, 5, 6, C.R);
    // kick
    buf.circle(cx, by - 10, 10.5, C.K); buf.circle(cx, by - 10, 9.5, C.R); buf.circle(cx, by - 10, 8, C.W);
    buf.circle(cx, by - 10, 2.5, C.K);
    buf.rect(cx - 6, by - 2, 2, 2, C.L); buf.rect(cx + 4, by - 2, 2, 2, C.L);
  }

  function drawVenueBase(buf, g, opts) {
    var t = g.frame;
    var beatF = 3600 / (g.musicName === 'boss' ? 184 : 168);
    var beatOn = Math.floor((t - g.musicStart) / beatF);
    buf.clear(K);
    var top = opts.top;
    // back curtain
    for (var x = 0; x < W; x++) {
      var ph = (x + 3) % 12;
      buf.rect(x, top, 1, opts.stageY - top, ph < 2 ? C.x : ph < 7 ? C.q : C.K);
    }
    buf.drect(0, top, W, 10, K, 10);
    // beams
    var sw = Math.sin(t / 50), sw2 = Math.sin(t / 37 + 1);
    beam(buf, 18, top + 8, 0.55 + sw * 0.35, 210, 0.13, C.N, 5);
    beam(buf, 302, top + 8, -0.55 - sw2 * 0.35, 210, 0.13, (beatOn >> 2) % 2 ? C.R : C.N, 5);
    beam(buf, 120, top - 6, 0.25 * sw2, 170, 0.1, C.R, 4);
    beam(buf, 200, top - 6, -0.25 * sw, 170, 0.1, C.N, 4);
    // logo backdrop
    buf.title(22, 0, 196, 68, 62, opts.logoY, true);
    // amps
    drawAmp(buf, 30, opts.stageY); drawAmp(buf, 258, opts.stageY);
    // stage
    var sy = opts.stageY;
    buf.rect(0, sy, W, opts.stageH, C.R);
    for (var px = 0; px < W; px += 16) buf.rect(px, sy, 1, opts.stageH, C.r);
    buf.rect(0, sy, W, 1, C.O);
    buf.rect(0, sy + opts.stageH, W, 8, C.r); buf.rect(0, sy + opts.stageH, W, 1, C.K);
    buf.drect(0, sy + opts.stageH + 1, W, 7, C.q, 8);
    // trusses
    truss(buf, 4, 0, sy + opts.stageH, t, opts.lamps, beatOn);
    truss(buf, 302, 0, sy + opts.stageH, t, opts.lamps, beatOn + 1);
    return beatOn;
  }

  function drawVenue(buf, g) {
    var beatOn = drawVenueBase(buf, g, { top: 26, logoY: 26, stageY: 98, stageH: 14, lamps: [40, 58, 76, 94] });
    drawKit(buf, 160, 98);
    // mic stand
    buf.line(130, 98, 130, 76, C.L); buf.rect(129, 74, 3, 3, C.G);
    // monitors
    [96, 196].forEach(function (mx) { buf.poly([mx, 98, mx + 22, 98, mx + 18, 90, mx + 4, 92], C.k); buf.drect(mx + 5, 93, 12, 4, C.E, 6); });
    // floor
    var fy = 120;
    buf.rect(0, fy, W, H - fy, C.Q);
    for (var y = fy; y < H; y += 7) buf.rect(0, y, W, 1, C.k);
    for (var x = -8; x < W; x += 24) buf.line(x + (fy - 120), fy, x - 30, H, C.k);
    // light pools
    var sw = Math.sin(g.frame / 50);
    buf.ellipse(90 + sw * 70, 150, 34, 9, C.m, 4);
    buf.ellipse(230 - sw * 60, 158, 34, 9, (beatOn >> 2) % 2 ? C.q : C.m, 4);
  }

  function crowdPerson(buf, x, y, up, outline, seed) {
    var arm = up ? -15 : -9;
    var h = hash(seed);
    // body + shoulders (only the top contour is outlined, like the title art)
    buf.poly([x - 10, y + 24, x - 10, y - 1, x - 6, y - 5, x + 6, y - 5, x + 10, y - 1, x + 10, y + 24], K);
    buf.line(x - 10, y - 1, x - 6, y - 5, outline); buf.line(x + 6, y - 5, x + 10, y - 1, outline);
    buf.line(x - 6, y - 5, x - 3, y - 5, outline); buf.line(x + 3, y - 5, x + 6, y - 5, outline);
    buf.circle(x, y - 11, 5, K);
    buf.ring(x, y - 11, 5, outline);
    if (h < 0.65) { // right arm raised
      buf.thick(x + 8, y - 2, x + 11, y + arm, 4, K);
      buf.line(x + 6, y - 2, x + 9, y + arm, outline); buf.line(x + 10, y - 1, x + 13, y + arm, outline);
      buf.line(x + 9, y + arm, x + 13, y + arm, outline);
      if (h < 0.3) { buf.pset(x + 9, y + arm - 1, outline); buf.pset(x + 13, y + arm - 1, outline); }
    }
    if (h > 0.45) { // left arm raised
      buf.thick(x - 8, y - 2, x - 11, y + arm + 2, 4, K);
      buf.line(x - 6, y - 2, x - 9, y + arm + 2, outline); buf.line(x - 10, y - 1, x - 13, y + arm + 2, outline);
      buf.line(x - 13, y + arm + 2, x - 9, y + arm + 2, outline);
    }
  }

  function drawConcert(buf, g, layer) {
    var beatF = 3600 / 168, t = g.frame;
    var b = Math.floor((t - g.musicStart) / beatF);
    if (layer === 'back') {
      drawVenueBase(buf, g, { top: 0, logoY: 2, stageY: 112, stageH: 30, lamps: [20, 40, 60, 80, 100] });
      // drum riser
      buf.rect(178, 106, 70, 8, C.r); buf.rect(178, 106, 70, 1, C.O);
      return;
    }
    if (layer === 'kit') { drawKit(buf, 212, 128); return; }
    // pyro on beat accents
    var ph = (t - g.musicStart) % (beatF * 8);
    if (ph < beatF * 2 && g.sceneT > 100) {
      [24, 296].forEach(function (px) {
        for (var i = 0; i < 18; i++) {
          var fy = 140 - (ph * 2.5 + i * 3) % 60, fx = px + Math.sin(i * 1.7 + t * 0.4) * (3 + i * 0.3);
          var c = i < 5 ? C.w : i < 9 ? C.Y : i < 13 ? C.O : C.R;
          buf.circle(fx, fy, 3 - i * 0.12, c);
        }
      });
    }
    // crowd
    var rows = [{ y: 158, n: 16, out: C.n, off: 9 }, { y: 172, n: 15, out: C.N, off: 0 }];
    rows.forEach(function (r, ri) {
      for (var i = 0; i < r.n; i++) {
        var x = r.off + i * 21 + Math.floor(hash(i * 13 + ri) * 8);
        var jump = ((b + i + ri) % 2 === 0) ? -3 : 0;
        if (hash(i * 7 + ri * 3) < 0.35) jump = ((b + i) % 4 === 0) ? -5 : 0;
        crowdPerson(buf, x, r.y + jump, (b + i) % 2 === 0, r.out, i * 31 + ri * 7);
      }
    });
  }

  function drawTitle(buf, g) {
    buf.clear(K);
    buf.title(0, 0, 240, 180, 40, 0, false);
    var t = g.sceneT;
    // lamps blink
    var lys = [55, 69, 79, 92];
    lys.forEach(function (ly, i) {
      var on = ((Math.floor(t / 15) + i) % 2) === 0;
      [48.5, 271].forEach(function (lx, j) {
        buf.circle(lx, ly, 2.2, on ? ((i + j) % 2 ? C.N : C.R) : C.k);
        if (on) buf.pset(Math.round(lx) - 1, ly - 1, C.w);
      });
    });
    // extra truss on the side bars to fill 16:9
    truss(buf, 14, 30, 140, t, [], 0);
    truss(buf, 292, 30, 140, t, [], 0);
    for (var y = 120; y < 140; y++) { buf.rect(0, y, 40, 1, (y % 3) ? C.k : C.D); buf.rect(280, y, 40, 1, (y % 3) ? C.k : C.D); }
    buf.drect(0, 140, 40, 4, C.R, 8); buf.drect(280, 140, 40, 4, C.R, 8);
    // PRESS START blink
    var blinkOff = g.titleSel ? (Math.floor(t / 3) % 2 === 0) : (t % 64) >= 44;
    if (blinkOff) buf.rect(40 + 91, 153, 64, 9, K);
    // credit line
    buf.text('CREDIT 2', 254, 172, C.W);
    buf.text('1P', 8, 172, C.N); buf.text('2P', 22, 172, C.R);
  }

  function drawCard(buf, g) {
    buf.clear(K);
    var t = g.sceneT;
    buf.textC('STAGE 1', W / 2, 52, C.W, { scale: 4, outline: C.r, bold: true });
    if (t > 30) buf.textC('ROAD TO THE GIG', W / 2, 104, C.R, { scale: 2 });
    if (t > 60) buf.textC('DOWNTOWN - 11:58 PM', W / 2, 128, C.L);
    // blood-red bar with drips under the title
    var bw = Math.min(170, t * 6);
    buf.rect(W / 2 - bw / 2, 86, bw, 3, C.R);
    for (var i = 0; i < 17; i++) {
      var x = 77 + i * 10 + Math.floor(hash(i) * 5), len = Math.min(2 + Math.floor(hash(i + 50) * 9), Math.max(0, Math.floor((t - 20) / 4)));
      if (x < W / 2 - bw / 2 || x > W / 2 + bw / 2 - 2) continue;
      buf.rect(x, 89, 2, len, C.R); if (len > 3) buf.rect(x, 89 + len, 2, 1, C.r);
    }
  }

  // ================================================================ FX + HUD
  function drawFx(buf, g, f) {
    var sx = Math.round(f.x - g.cam), sy = Math.round(f.y - (f.z || 0));
    if (f.type === 'spark') {
      var r = f.t < 3 ? (f.big ? 10 : 7) : f.t < 6 ? (f.big ? 7 : 5) : 3;
      var c1 = f.t < 3 ? C.w : f.t < 6 ? C.Y : C.O;
      var c2 = f.t < 3 ? C.Y : f.t < 6 ? C.O : C.R;
      buf.thick(sx - r, sy, sx + r, sy, 3, c2); buf.thick(sx, sy - r, sx, sy + r, 3, c2);
      buf.thick(sx - r * 0.6, sy - r * 0.6, sx + r * 0.6, sy + r * 0.6, 2, c2); buf.thick(sx - r * 0.6, sy + r * 0.6, sx + r * 0.6, sy - r * 0.6, 2, c2);
      buf.line(sx - r, sy, sx + r, sy, c1); buf.line(sx, sy - r, sx, sy + r, c1);
      buf.circle(sx, sy, f.t < 3 ? 3 : 2, c1);
      if (f.big && f.t < 4) buf.ring(sx, sy, r + 3, C.W);
    } else if (f.type === 'dust') {
      var d = f.t * 0.8;
      buf.circle(sx - 6 - d, sy - 2 - f.t * 0.2, 3 - f.t * 0.15, C.L);
      buf.circle(sx + 6 + d, sy - 2 - f.t * 0.2, 3 - f.t * 0.15, C.L);
    } else if (f.type === 'wave') {
      for (var k = 0; k < 4; k++) {
        var rr = 6 + k * 3 + (f.t % 4) * 1.5, wx = sx - f.dir * k * 8;
        var col = k === 0 ? C.w : k === 1 ? C.N : k === 2 ? C.n : C.m;
        for (var a = -64; a <= 64; a += 5) {
          var ang = a * RAD;
          buf.stamp(wx + f.dir * Math.cos(ang) * rr - f.dir * rr * 0.6, sy + Math.sin(ang) * rr * 1.5, k ? 2 : 3, col);
        }
      }
      if (f.t < 26) buf.text('AAARGH!', sx - 20 - f.dir * 10, sy - 26, C.Y, { outline: C.K });
    } else if (f.type === 'pop') {
      buf.textC(f.text, sx, sy - f.t * 0.5, C.W, { outline: C.K });
    }
  }

  function bar(buf, x, y, w, frac, colFill, colBack) {
    buf.rect(x - 1, y - 1, w + 2, 7, K);
    buf.rect(x, y, w, 5, colBack);
    var fw = Math.round(w * clamp(frac, 0, 1));
    buf.rect(x, y, fw, 5, colFill);
    buf.rect(x, y, fw, 1, C.w === colFill ? C.w : C.F);
    for (var i = 4; i < w; i += 5) buf.rect(x + i, y + 1, 1, 4, K);
  }
  function pad(n, l) { var s = String(Math.floor(n)); while (s.length < l) s = '0' + s; return s; }

  function drawHUD(buf, g) {
    var ps = g.players;
    var o = { outline: K };
    ps.forEach(function (p, i) {
      var left = i === 0;
      var x = left ? 6 : W - 6 - 96;
      var lab = left ? '1P' : (g.mode === 'play' ? 'CPU' : '2P');
      buf.text(lab, x, 3, left ? C.N : C.R, o);
      buf.text(p.name, x + MA.textWidth(lab) + 4, 3, C.W, o);
      buf.text(pad(p.score, 7), x + 54, 3, C.W, o);
      var fr = p.hp / p.maxHp;
      bar(buf, x, 13, 80, fr, fr > 0.5 ? C.Y : fr > 0.25 ? C.O : C.R, C.q);
      if (!(g.mode === 'play' && !left)) buf.text('x' + p.lives, x + 84, 12, C.W, o);
      if (p.human) {
        var sp = 1 - p.ai.spCool / 240;
        buf.rect(x - 1, 19, 82, 3, K);
        buf.rect(x, 20, Math.round(80 * sp), 1, sp >= 1 ? ((g.frame >> 3) % 2 ? C.N : C.w) : C.n);
      }
      var ht = g.hudTarget[p.id];
      if (ht && !ht.actor.boss && ht.t % 1 === 0) {
        buf.text(ht.actor.name, x, 22, C.L, o);
        bar(buf, x + 1, 31, 46, Math.max(0, ht.actor.hp) / ht.actor.maxHp, C.P, C.q);
      }
    });
    buf.textC('TIME', W / 2, 2, C.R, o);
    buf.textC(pad(g.time, 2), W / 2, 11, C.W, { scale: 2, outline: K });
    if (g.bossBar) {
      var b = g.actors.filter(function (a) { return a.boss; })[0];
      if (b) {
        buf.rect(70, 168, 180, 11, K);
        buf.text('BOSS', 74, 170, C.R);
        buf.text(b.name, 102, 170, C.W);
        bar(buf, 178, 170, 68, Math.max(0, b.hp) / b.maxHp, C.R, C.q);
      }
    }
  }

  function drawBanners(buf, g) {
    g.banners.forEach(function (b) {
      var o = b.o, sc = o.scale || 2;
      if (o.blink && (b.t >> 3) % 2) return;
      var y = o.y || 70;
      if (o.band) {
        var bh = 7 * sc + 14, by = y - 7;
        buf.rect(0, by, W, bh, K); buf.rect(0, by + 1, W, 1, C.r); buf.rect(0, by + bh - 2, W, 1, C.r);
        if (g.tally !== null && g.tally !== undefined && b.text !== 'K.O.') buf.rect(0, by + bh, W, 14, K);
      }
      if (b.text === 'K.O.') {
        var s2 = b.t < 6 ? 8 - b.t / 3 : sc;
        buf.textC('K.O.', W / 2, y - (s2 - sc) * 3, (b.t >> 2) % 2 ? C.R : C.Y, { scale: Math.round(s2), outline: K, bold: true });
        return;
      }
      buf.textC(b.text, W / 2, y, C[o.col || 'W'], { scale: sc, outline: C[o.outline || 'K'], bold: true });
    });
    if (g.showGo && (g.frame >> 4) % 2 === 0) {
      buf.text('GO', 262, 66, C.Y, { scale: 3, outline: K, bold: true });
      buf.poly([300, 62, 312, 74, 300, 86], K); buf.poly([301, 66, 309, 74, 301, 82], C.Y);
    }
    if (g.bossCard >= 0 && g.bossCard !== undefined && g.bossCard !== null) {
      var k = g.bossCard, slide = Math.min(1, k / 14), x0 = Math.round(lerp(-W, 0, slide));
      if (k > 104) x0 = Math.round(lerp(0, W, (k - 104) / 16));
      buf.rect(x0, 60, W, 38, K); buf.rect(x0, 61, W, 1, C.R); buf.rect(x0, 96, W, 1, C.R);
      buf.text('BOSS', x0 + 40, 66, C.R, { scale: 1 });
      buf.text('THE PROMOTER', x0 + 40, 76, C.W, { scale: 2, outline: C.r, bold: true });
      buf.text('"YOU PLAY FOR EXPOSURE!"', x0 + 40, 90 - 2, C.Y);
    }
    if (g.tally !== null && g.tally !== undefined) {
      buf.textC('TIME BONUS  ' + pad(g.tally, 5), W / 2, 92, C.W, { outline: K });
    }
    if (g.showTags > 0) {
      g.players.forEach(function (p, i) {
        if ((g.frame >> 3) % 2) return;
        var sx = Math.round(p.x - g.cam), sy = Math.round(p.y - 74);
        buf.text(i ? '2P' : '1P', sx - 5, sy, i ? C.R : C.N, { outline: K });
        buf.poly([sx - 2, sy + 9, sx + 4, sy + 9, sx + 1, sy + 12], i ? C.R : C.N);
      });
    }
  }

  // ================================================================ RENDER
  GP.render = function (buf) {
    var g = this;
    buf.remap = null; buf.ox = 0; buf.oy = 0;
    if (g.scene === 'title') { drawTitle(buf, g); return; }
    if (g.scene === 'card') { drawCard(buf, g); return; }
    if (g.scene === 'select') { drawSelect(buf, g); return; }
    if (g.scene === 'black') { buf.clear(K); return; }
    var shx = g.shake > 0 ? ((g.shake >> 1) % 2 ? 2 : -2) : 0;
    var shy = g.shake > 0 ? ((g.shake >> 2) % 2 ? 1 : -1) : 0;
    buf.ox = shx; buf.oy = shy;
    if (g.scene === 'street') drawStreet(buf, g);
    else if (g.scene === 'venue') drawVenue(buf, g);
    else if (g.scene === 'concert') drawConcert(buf, g, 'back');
    // actors sorted by depth
    g.items.forEach(function (it) { drawPizza(buf, Math.round(it.x - g.cam), Math.round(it.y), it.t); });
    var list = g.actors.slice().sort(function (a, b) { return a.y - b.y || a.id - b.id; });
    // shadows
    list.forEach(function (a) {
      if (g.scene === 'concert') return;
      var sx = Math.round(a.x - g.cam), r = (a.busy() && a.state !== 'getup' ? 18 : 11) * a.scale - Math.min(5, a.z * 0.1);
      buf.ellipse(sx + (a.state === 'down' || a.state === 'dead' ? -a.dir * 8 * a.scale : 0), Math.round(a.y), r, 2.6, K, 11);
    });
    list.forEach(function (a) {
      if (a.state === 'dead' && (a.t >> 2) % 2) return;
      if (a.invuln > 0 && a.team === 'player' && (a.invuln >> 2) % 2) return;
      if (a.flash > 0 && (a.flash % 2)) {
        var m = new Uint8Array(256).fill(C.w); m[K] = K; buf.remap = m;
      }
      drawPuppet(buf, a, Math.round(a.x - g.cam), Math.round(a.y - a.z));
      buf.remap = null;
      if (g.scene === 'concert' && a.kind === 'drum') drawConcert(buf, g, 'kit');
    });
    g.fx.forEach(function (f) { drawFx(buf, g, f); });
    if (g.scene === 'concert') drawConcert(buf, g, 'front');
    buf.ox = 0; buf.oy = 0;
    if (g.hud) drawHUD(buf, g);
    drawBanners(buf, g);
    if (g.mode === 'play') drawPlayOverlay(buf, g);
    if (g.scene === 'concert' && g.mode !== 'play') {
      if (g.sceneT > 330 && (g.frame >> 4) % 4 !== 3) buf.textC('TO BE CONTINUED...', W / 2, 92, C.W, { scale: 1, outline: K });
    }
  };
  GP.fadeLevel = function () {
    if (this.koFlash > 0) return -Math.min(4, Math.ceil(this.koFlash / 2.5));
    return this.fade;
  };
})(typeof window !== 'undefined' ? window : globalThis);
