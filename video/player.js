// Clear House explainer: plays STORYBOARD on a 1920x1080 canvas. Every frame is a pure function of t (seconds),
// so the video can be scrubbed, screen-recorded or exported frame-perfect. Injected by build_video.py:
//   STORYBOARD (scenes), TIMINGS ({total, scenes:[{start,end,cues:[{text,start,end}]}]}), CHAPTERS, HAS_VOICE.
(() => {
  const W = 1920, H = 1080;
  const C = {  // Clear House UI + Google colors
    bg1: '#f3f7ff', bg2: '#e4edfd', ink: '#14203f', muted: '#56657f', line: '#d4def2', navy: '#23408f',
    accent: '#1a73e8', blue: '#4285f4', red: '#ea4335', yellow: '#fbbc04', green: '#34a853',
    good: '#188038', goodFill: '#e6f4ea', bad: '#c5221f', badFill: '#fce8e6', ping: '#ff8a1f', white: '#ffffff', glass: 'rgba(255,255,255,0.86)',
  };
  const FONT = "'Google Sans', 'Inter', system-ui, sans-serif", MONO = FONT;  // Google Sans everywhere
  const cv = document.getElementById('stage'), ctx = cv.getContext('2d');

  // ---------- helpers ----------
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const ease = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const out = x => 1 - Math.pow(1 - clamp(x), 3);
  const prog = (t, a, d = .6) => out((t - a) / d);               // 0→1 starting at a, over d seconds
  const lerp = (a, b, k) => a + (b - a) * k;
  function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
  function fillRR(x, y, w, h, r, fill, stroke, lw = 2) { rr(x, y, w, h, r); if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); } }
  function text(s, x, y, { size = 32, weight = 400, color = C.ink, font = FONT, align = 'left', base = 'alphabetic', spacing = 0, alpha = 1 } = {}) {
    ctx.save(); ctx.globalAlpha *= alpha; ctx.font = `${weight} ${size}px ${font}`; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = base;
    if (spacing) ctx.letterSpacing = spacing + 'px';
    ctx.fillText(s, x, y); ctx.restore();
  }
  function wrap(s, maxW, size, weight = 400, font = FONT) {
    ctx.font = `${weight} ${size}px ${font}`; const words = String(s).split(/\s+/), lines = []; let cur = '';
    for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = w; } else cur = t; }
    if (cur) lines.push(cur); return lines;
  }
  function para(s, x, y, maxW, { size = 32, lh = 1.4, weight = 400, color = C.ink, alpha = 1, align = 'left' } = {}) {
    const lines = wrap(s, maxW, size, weight); lines.forEach((l, i) => text(l, x, y + i * size * lh, { size, weight, color, alpha, align })); return lines.length * size * lh;
  }
  function circle(x, y, r, fill, stroke, lw = 3) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); } }
  function shadow(blur = 30, y = 12, color = 'rgba(35,64,143,0.16)') { ctx.shadowColor = color; ctx.shadowBlur = blur; ctx.shadowOffsetY = y; }
  function noShadow() { ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0; }
  const colorOf = k => ({ good: C.good, bad: C.bad, accent: C.accent }[k] || C.accent);
  function house(x, y, s, wall = C.white, roof = C.navy, door = C.navy) {  // simple flat house, bottom-center at x,y
    ctx.fillStyle = wall; ctx.beginPath(); ctx.moveTo(x - s * .5, y); ctx.lineTo(x - s * .5, y - s * .55); ctx.lineTo(x, y - s * .95); ctx.lineTo(x + s * .5, y - s * .55); ctx.lineTo(x + s * .5, y); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = roof; ctx.lineWidth = s * .09; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath(); ctx.moveTo(x - s * .62, y - s * .48); ctx.lineTo(x, y - s * .98); ctx.lineTo(x + s * .62, y - s * .48); ctx.stroke();
    fillRR(x - s * .1, y - s * .32, s * .2, s * .32, [s * .1, s * .1, 0, 0], door);
  }
  function pin(x, y, s, color = C.accent) {  // map pin pointing at x,y
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y - s, s * .62, Math.PI, 0); ctx.lineTo(x, y); ctx.closePath(); ctx.fill(); circle(x, y - s, s * .26, C.white);
  }
  function face(x, y, r, mood, t) {  // flat character with dot eyes
    const bob = Math.sin(t * 2.2) * 6; y += bob;
    shadow(24, 10); circle(x, y, r, C.blue); noShadow();
    circle(x - r * .32, y - r * .12, r * .1, C.ink); circle(x + r * .32, y - r * .12, r * .1, C.ink);
    const blink = (t % 3.6) < .12; if (blink) { fillRR(x - r * .45, y - r * .16, r * .26, r * .08, 4, C.blue); fillRR(x + r * .19, y - r * .16, r * .26, r * .08, 4, C.blue); ctx.fillStyle = C.ink; }
    ctx.strokeStyle = C.ink; ctx.lineWidth = r * .07; ctx.lineCap = 'round'; ctx.beginPath();
    if (mood === 'happy') ctx.arc(x, y + r * .12, r * .3, .15 * Math.PI, .85 * Math.PI);
    else if (mood === 'worried') { ctx.moveTo(x - r * .25, y + r * .38); ctx.quadraticCurveTo(x, y + r * .22, x + r * .25, y + r * .38); }
    else if (mood === 'surprised') { ctx.arc(x, y + r * .32, r * .11, 0, Math.PI * 2); }
    else { ctx.moveTo(x - r * .22, y + r * .34); ctx.lineTo(x + r * .2, y + r * .28); }
    ctx.stroke(); circle(x + r * .58, y - r * .55, r * .14, C.ping); // orange ping, like the logo
    return y;
  }
  function icon(name, x, y, s) {
    ctx.save(); ctx.lineWidth = s * .08; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = C.navy; ctx.fillStyle = C.navy;
    if (name === 'phone') { fillRR(x - s * .28, y - s * .48, s * .56, s * .96, s * .1, C.white, C.navy, s * .07); circle(x, y + s * .36, s * .05, C.navy); }
    else if (name === 'door') { fillRR(x - s * .3, y - s * .5, s * .6, s, [s * .3, s * .3, 4, 4], C.white, C.navy, s * .07); circle(x + s * .14, y + s * .05, s * .05, C.navy); }
    else if (name === 'clock') { circle(x, y, s * .45, C.white, C.navy, s * .07); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - s * .28); ctx.moveTo(x, y); ctx.lineTo(x + s * .2, y); ctx.stroke(); }
    else if (name === 'shield') { ctx.beginPath(); ctx.moveTo(x, y - s * .5); ctx.lineTo(x + s * .42, y - s * .32); ctx.lineTo(x + s * .36, y + s * .2); ctx.quadraticCurveTo(x, y + s * .52, x, y + s * .52); ctx.quadraticCurveTo(x, y + s * .52, x - s * .36, y + s * .2); ctx.lineTo(x - s * .42, y - s * .32); ctx.closePath(); ctx.fillStyle = C.goodFill; ctx.fill(); ctx.strokeStyle = C.good; ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - s * .16, y); ctx.lineTo(x - s * .02, y + s * .14); ctx.lineTo(x + s * .2, y - s * .14); ctx.stroke(); }
    else if (name === '911' || name === '211') { fillRR(x - s * .5, y - s * .32, s, s * .64, s * .32, name === '911' ? C.badFill : '#e8f0fe', name === '911' ? C.bad : C.accent, s * .06); text(name, x, y + s * .02, { size: s * .36, weight: 700, color: name === '911' ? C.bad : C.accent, align: 'center', base: 'middle' }); }
    else if (name === 'moon') { circle(x, y, s * .45, '#fff4cf'); circle(x + s * .2, y - s * .12, s * .38, '#1b2a55'); }
    ctx.restore();
  }

  // ---------- shared layout: story-cartoon style (full-bleed scene, Sam, board, big caption) ----------
  const ART = { x: 0, y: 0, w: 1000, h: 800 };           // scene art is drawn in this virtual box...
  const BOARD = { x: 790, y: 200, s: .76 };                // ...then placed on the board at this spot and scale
  const HEAD = FONT;  // headlines too: heavy Google Sans
  const ACCENTS = [C.red, C.blue, C.yellow, C.green, C.accent];
  function chapterOf(i) { let c = 0; CHAPTERS.forEach((ch, k) => { if (i >= ch.scene) c = k; }); return c; }
  function light(x, y, r, color, a) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, color.replace('A', a)); g.addColorStop(1, color.replace('A', 0)); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2); }
  function backdrop(t, i) {
    const ch = chapterOf(i), sway = Math.sin(t * .4) * 12;
    const skies = [['#0f1a3d', '#2a3f7a'], ['#0f1a3d', '#2a3f7a'], ['#3b2a22', '#6b4b36'], ['#2a2448', '#c0646e'], ['#0b1020', '#16203d'], ['#bcd3f5', '#f3f7ff'], ['#bcd3f5', '#f3f7ff']];
    const [a, b] = skies[Math.min(ch, skies.length - 1)]; const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, a); g.addColorStop(1, b); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    if (ch <= 1) {  // night street: houses with glowing windows and a street lamp
      for (let k = 0; k < 60; k++) circle((k * 331) % W, (k * 97) % 420, 1.5 + (k % 3), `rgba(255,255,255,${.25 + .35 * Math.abs(Math.sin(t + k))})`);
      circle(1700, 150, 70, '#fff4cf'); circle(1730, 130, 62, a);
      for (let k = 0; k < 8; k++) { const x = 120 + k * 250; house(x, 980, 300, '#1d2c5a', '#33478a', (k + Math.floor(t / 5)) % 3 ? '#ffcf6b' : '#1d2c5a'); light(x, 830, 160, 'rgba(255,190,90,A)', .18); }
      fillRR(0, 960, W, 140, 0, '#151f44'); fillRR(560, 520, 14, 460, 4, '#0b1230'); light(567, 520, 360, 'rgba(255,200,110,A)', .35); circle(567, 520, 20, '#ffe2a1');
    } else if (ch === 2) {  // warm office with shelves
      for (let k = 0; k < 4; k++) { fillRR(60, 180 + k * 180, 600, 20, 6, '#4a3326'); for (let j = 0; j < 9; j++) fillRR(80 + j * 62, 120 + k * 180, 44, 60, 4, ACCENTS[(j + k) % 4] + '99'); }
      fillRR(0, 900, W, 200, 0, '#2c1f18'); light(1450, 120, 520, 'rgba(255,214,150,A)', .35);
    } else if (ch === 3) {  // dusk city skyline
      for (let k = 0; k < 14; k++) { const h = 220 + (k * 137) % 360, x = k * 150 - 40; fillRR(x, 900 - h, 120, h + 200, 8, '#1f1b3a');
        for (let r = 0; r < h / 60; r++) for (let c = 0; c < 3; c++) if ((k + r + c) % 3) fillRR(x + 16 + c * 34, 920 - h + r * 60, 18, 24, 3, `rgba(255,220,140,${.35 + .3 * Math.sin(t + k + r)})`); }
      fillRR(0, 900, W, 200, 0, '#15122b'); light(300, 700, 500, 'rgba(234,67,53,A)', .25);
    } else if (ch === 4) {  // server room: racks with Google-colored lights
      for (let k = 0; k < 9; k++) { const x = 40 + k * 215; fillRR(x, 120, 170, 860, 14, '#141c33', '#202b4a');
        for (let r = 0; r < 14; r++) { fillRR(x + 18, 150 + r * 58, 134, 40, 6, '#1b2442'); circle(x + 40, 170 + r * 58, 6, ACCENTS[(k + r) % 4]); fillRR(x + 60, 166 + r * 58, 70 * (.4 + .6 * Math.abs(Math.sin(t * 2 + k + r))), 6, 3, '#2f3d66'); } }
      light(960, 540, 900, 'rgba(66,133,244,A)', .25);
    } else {  // morning: soft sky, clouds, a home
      for (let k = 0; k < 5; k++) { const x = ((k * 420 + t * 14) % (W + 400)) - 200; fillRR(x, 120 + (k % 2) * 90, 260, 60, 30, '#ffffffcc'); }
      circle(1720, 170, 90, '#ffe9a8'); fillRR(0, 930, W, 160, 0, '#cfe3c9'); for (let k = 0; k < 3; k++) house(1640 + k * 120, 950, 110, C.white, '#9fb4e6', '#9fb4e6');
    }
    const v = ctx.createRadialGradient(W / 2, H * .45, H * .35, W / 2, H * .5, H * .95); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,.55)'); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);  // vignette
    light(W / 2 + sway, 0, 900, 'rgba(255,240,210,A)', .08);  // soft top light
  }
  function sam(x, y, mood, t) {  // the narrator character: round face, dot eyes, a navy cap with the orange ping
    const bob = Math.sin(t * 1.8) * 6; y += bob;
    shadow(30, 14, 'rgba(0,0,0,.35)'); fillRR(x - 120, y + 150, 240, 300, [110, 110, 30, 30], C.blue); noShadow();  // hoodie
    fillRR(x - 40, y + 150, 80, 40, 20, '#3367d6');
    circle(x, y, 150, '#f6dcc8');  // face
    ctx.fillStyle = C.navy; ctx.beginPath(); ctx.ellipse(x, y - 72, 158, 92, 0, Math.PI, 0); ctx.fill(); fillRR(x - 10, y - 86, 220, 30, 15, C.navy);  // cap + brim
    circle(x + 40, y - 120, 12, C.ping);
    const blink = (t % 4.2) < .14, ey = y + 10;
    if (blink) { fillRR(x - 70, ey - 3, 36, 7, 3, C.ink); fillRR(x + 34, ey - 3, 36, 7, 3, C.ink); }
    else if (mood === 'worried') { circle(x - 52, ey, 11, C.ink); circle(x + 52, ey, 11, C.ink); ctx.strokeStyle = C.ink; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x - 75, ey - 30); ctx.lineTo(x - 32, ey - 42); ctx.moveTo(x + 75, ey - 30); ctx.lineTo(x + 32, ey - 42); ctx.stroke(); }
    else { circle(x - 52, ey, 11, C.ink); circle(x + 52, ey, 11, C.ink); }
    ctx.strokeStyle = C.ink; ctx.lineWidth = 8; ctx.lineCap = 'round'; ctx.beginPath();
    if (mood === 'happy') ctx.arc(x, y + 50, 36, .15 * Math.PI, .85 * Math.PI);
    else if (mood === 'worried') { ctx.moveTo(x - 28, y + 82); ctx.quadraticCurveTo(x, y + 66, x + 28, y + 82); }
    else if (mood === 'surprised') ctx.arc(x, y + 76, 14, 0, Math.PI * 2);
    else { ctx.moveTo(x - 26, y + 76); ctx.lineTo(x + 24, y + 70); }
    ctx.stroke();
  }
  function moodFor(s) { return { hook: 'worried', versus: 'thinking', quiz: 'thinking', recap: 'happy', bignumber: 'surprised', bars: 'surprised' }[s.draw] || (s.mood || 'happy'); }
  function strokeText(s, x, y, size, color, align = 'center', spacing = 0, font = HEAD) {
    ctx.save(); ctx.font = `800 ${size}px ${font}`; ctx.textAlign = align; ctx.textBaseline = 'alphabetic'; if (spacing) ctx.letterSpacing = spacing + 'px';
    ctx.lineJoin = 'round'; ctx.lineWidth = size * .14; ctx.strokeStyle = 'rgba(10,14,30,.9)'; ctx.strokeText(s, x, y); shadow(0, size * .06, 'rgba(0,0,0,.5)'); ctx.fillStyle = color; ctx.fillText(s, x, y); ctx.restore();
  }
  function caption(s, i, lt) {  // big heavy caption, the last word in a Google color, like the reference
    const words = s.headline.toUpperCase().split(' '), last = words.pop(), a = prog(lt, .15, .45), y = 905 - (1 - a) * 30;
    ctx.font = `800 88px ${HEAD}`; const size = Math.min(88, 88 * 1700 / ctx.measureText(s.headline.toUpperCase()).width);
    ctx.save(); ctx.globalAlpha *= a; ctx.font = `800 ${size}px ${HEAD}`; const first = words.join(' '), w1 = first ? ctx.measureText(first + ' ').width : 0, w2 = ctx.measureText(last).width, x0 = W / 2 - (w1 + w2) / 2;
    if (first) strokeText(first + ' ', x0, y, size, C.white, 'left'); strokeText(last, x0 + w1, y, size, ACCENTS[chapterOf(i) % ACCENTS.length], 'left'); ctx.restore();
  }
  function subtitle(cue, lt) {
    if (!cue) return; const ca = clamp((lt - cue.lt0) / .3) * clamp((cue.lt1 + .35 - lt) / .3 + 1); if (ca <= 0) return;
    const lines = wrap(cue.text, 1500, 34, 500); const h = lines.length * 46 + 30, y = 1040 - h;
    ctx.save(); ctx.globalAlpha *= ca; fillRR(W / 2 - 800, y, 1600, h, 20, 'rgba(10,14,30,.72)');
    lines.forEach((l, k) => text(l, W / 2, y + 48 + k * 46, { size: 34, weight: 500, color: C.white, align: 'center' })); ctx.restore();
  }
  function topBar(s, i, lt) {
    const ch = CHAPTERS[chapterOf(i)], title = `CLEAR HOUSE · ${ch.title.toUpperCase()}`;
    ctx.save(); ctx.font = `800 34px ${HEAD}`; ctx.letterSpacing = '2px'; const w = ctx.measureText(title).width + 60;
    shadow(20, 8, 'rgba(0,0,0,.4)'); fillRR(W / 2 - w / 2, 28, w, 64, 10, C.red); noShadow(); strokeText(title, W / 2, 73, 34, C.white, 'center', 2); ctx.restore();
    const k = s.kicker; ctx.save(); ctx.globalAlpha *= prog(lt, .1); ctx.font = `700 28px ${HEAD}`; ctx.letterSpacing = '2px'; const pw = ctx.measureText(k).width + 100;
    fillRR(W / 2 - pw / 2, 116, pw, 58, 29, 'rgba(10,14,30,.78)', C.yellow, 3); circle(W / 2 - pw / 2 + 36, 145, 13, null, C.yellow, 3);
    ctx.strokeStyle = C.yellow; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(W / 2 - pw / 2 + 36, 145); ctx.lineTo(W / 2 - pw / 2 + 36, 137); ctx.moveTo(W / 2 - pw / 2 + 36, 145); ctx.lineTo(W / 2 - pw / 2 + 43, 145); ctx.stroke();
    text(k, W / 2 + 18, 155, { size: 28, weight: 700, font: HEAD, color: C.white, align: 'center', spacing: 2 }); ctx.restore();
  }
  function infoCard(card, lt) {
    if (!card) return; const a = prog(lt, .5, .6), x = ART.x + ART.w - 420, y = ART.y + 26 - (1 - a) * 20;
    ctx.save(); ctx.globalAlpha *= a; shadow(); fillRR(x, y, 394, 150, 22, C.white); noShadow(); fillRR(x, y, 394, 6, [22, 22, 0, 0], C.accent);
    text(card[0], x + 26, y + 46, { size: 17, font: MONO, color: C.muted, spacing: 3 });
    text(card[1], x + 26, y + 98, { size: 44, weight: 800 }); text(card[2], x + 26, y + 132, { size: 21, weight: 600, color: C.accent }); ctx.restore();
  }
  function statCard(stat, pill, lt) {
    const a = prog(lt, .7, .6); ctx.save(); ctx.globalAlpha *= a;
    if (stat) { shadow(); fillRR(ART.x + 26, ART.y + 26, 300, 126, 22, C.white); noShadow(); text(stat[0], ART.x + 50, ART.y + 66, { size: 16, font: MONO, color: C.muted, spacing: 3 }); text(stat[1], ART.x + 50, ART.y + 122, { size: 46, weight: 800, color: colorOf(stat[2]) }); }
    if (pill) { ctx.font = `700 20px ${MONO}`; const w = ctx.measureText(pill).width + 44; fillRR(ART.x + 26, ART.y + (stat ? 170 : 26), w, 46, 23, '#fff4e5', C.ping); text(pill, ART.x + 48, ART.y + (stat ? 200 : 56), { size: 20, weight: 700, font: MONO, color: '#9a4b00', spacing: 2 }); }
    ctx.restore();
  }
  function chapterBar(t) {
    const y = H - 10, total = TIMINGS.total; fillRR(0, y - 4, W, 8, 0, 'rgba(255,255,255,.18)'); fillRR(0, y - 4, W * clamp(t / total), 8, 0, C.ping);
    CHAPTERS.forEach(ch => circle(W * (TIMINGS.scenes[ch.scene].start / total), y, 6, t >= TIMINGS.scenes[ch.scene].start ? C.ping : 'rgba(255,255,255,.5)'));
  }

  // ---------- scene art (one function per "draw" type), each gets local time lt and scene duration d ----------
  const A = ART, cx = A.x + A.w / 2, cy = A.y + A.h / 2 + 30;  // in board units
  const cueStart = (sc, i) => (sc.cues[i] ? sc.cues[i].start - sc.start : 999);
  const DRAW = {
    hook(s, lt) {
      fillRR(A.x, A.y, A.w, A.h, 34, '#1b2a55'); for (let i = 0; i < 40; i++) { const x = A.x + 40 + (i * 241) % (A.w - 80), y = A.y + 40 + (i * 137) % 360; circle(x, y, 2 + (i % 3), `rgba(255,255,255,${.35 + .4 * Math.abs(Math.sin(lt * 1.3 + i))})`); }
      icon('moon', A.x + 170, A.y + 150, 120);
      for (let i = 0; i < 6; i++) { const lit = (i % 2 === 0) || (lt > 2 + i); house(A.x + 120 + i * 155, A.y + A.h - 60, 120, '#2c3f78', '#4a62a8', lit ? C.yellow : '#2c3f78'); }
      fillRR(A.x, A.y + A.h - 60, A.w, 60, [0, 0, 34, 34], '#24366c');
      const a = prog(lt, .3, .8); text(s.big, cx, A.y + 400, { size: 132, weight: 800, color: C.white, align: 'center', alpha: a });
      text(s.sub, cx, A.y + 470, { size: 26, font: MONO, color: C.yellow, align: 'center', spacing: 5, alpha: prog(lt, .9) });
      const r = 14 + 8 * (Math.sin(lt * 4) * .5 + .5); circle(cx + 330, A.y + 300, r + 10, 'rgba(255,138,31,.25)'); circle(cx + 330, A.y + 300, 14, C.ping);
    },
    agenda(s, lt) {
      text(s.title, A.x + 40, A.y + 110, { size: 40, weight: 700, color: C.navy, alpha: prog(lt, .2) });
      s.items.forEach((it, i) => { const a = prog(lt, .6 + i * .45), y = A.y + 190 + i * 118; ctx.save(); ctx.globalAlpha = a; shadow(18, 8);
        fillRR(A.x + 40 - (1 - a) * 40, y, A.w - 80, 92, 22, C.white); noShadow(); const col = [C.blue, C.red, C.yellow, C.green, C.accent][i % 5];
        circle(A.x + 100, y + 46, 30, col); text(String(i + 1), A.x + 100, y + 47, { size: 30, weight: 800, color: C.white, align: 'center', base: 'middle' });
        text(it, A.x + 154, y + 58, { size: 36, weight: 600 }); ctx.restore(); });
    },
    definition(s, lt, d) {
      const pct = (s.meaning.match(/(\d+(?:\.\d+)?)\s*percent/) || [])[1], ex = (s.example || '').match(/(\d+(?:\.\d+)?) percent/);
      shadow(); fillRR(A.x + 40, A.y + 190, A.w - 80, 250, 28, C.white); noShadow();
      text(s.term, A.x + 90, A.y + 290, { size: 66, weight: 800, color: C.navy, alpha: prog(lt, .2) });
      para(s.meaning, A.x + 90, A.y + 350, A.w - 180, { size: 30, color: C.muted, alpha: prog(lt, .6) });
      if (pct) {  // donut: the threshold, then the worked example
        const k1 = ease((lt - 1) / 1.4), k2 = ease((lt - cueStart(s._t, 1)) / 1.4), x = cx, y = A.y + 640, r = 120;
        circle(x, y, r, null, '#e3e9f6', 46); ctx.lineWidth = 46; ctx.lineCap = 'butt';
        ctx.strokeStyle = C.accent; ctx.beginPath(); ctx.arc(x, y, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (pct / 100) * k1); ctx.stroke();
        if (ex && k2 > 0) { ctx.strokeStyle = C.red; ctx.lineWidth = 18; ctx.beginPath(); ctx.arc(x, y, r + 46, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * (ex[1] / 100) * k2); ctx.stroke(); }
        text(pct + '%', x, y + 14, { size: 54, weight: 800, align: 'center' }); text('THRESHOLD', x, y + 50, { size: 16, font: MONO, color: C.muted, align: 'center', spacing: 3 });
        if (ex) text(s.example, cx, A.y + A.h - 22, { size: 26, weight: 600, color: C.red, align: 'center', alpha: k2 });
      } else {  // grounding: records flow into the model, nothing comes from outside
        const recs = 6; for (let i = 0; i < recs; i++) { const a = prog(lt, .8 + i * .2), x = A.x + 120 + i * 140, y = A.y + 560;
          ctx.save(); ctx.globalAlpha = a; fillRR(x, y, 110, 140, 14, C.white, C.line); for (let j = 0; j < 4; j++) fillRR(x + 16, y + 26 + j * 24, 78 - (j % 2) * 24, 8, 4, j ? '#dbe4f5' : C.accent); ctx.restore();
          const k = clamp((lt - 2.2 - i * .15) / 1.2); circle(lerp(x + 55, cx, k), lerp(y + 150, A.y + A.h - 50, k), 7, C.green); }
        fillRR(cx - 140, A.y + A.h - 92, 280, 80, 40, C.navy); text('Gemma 4', cx, A.y + A.h - 42, { size: 32, weight: 700, color: C.white, align: 'center' });
        if (s.example) text(s.example, cx, A.y + 500, { size: 24, color: C.muted, align: 'center', alpha: prog(lt, cueStart(s._t, 1)) });
      }
    },
    versus(s, lt, d) {
      const colW = (A.w - 100) / 2;
      [s.left, s.right].forEach((side, k) => { const x = A.x + 30 + k * (colW + 40), col = side.color === 'good' ? C.good : C.bad, fill = side.color === 'good' ? C.goodFill : C.badFill;
        const a = prog(lt, .2 + k * (d * .33)); ctx.save(); ctx.globalAlpha = a; shadow(); fillRR(x, A.y + 210, colW, 520, 28, C.white); noShadow();
        fillRR(x, A.y + 210, colW, 90, [28, 28, 0, 0], fill); text(side.title, x + 36, A.y + 268, { size: 36, weight: 800, color: col });
        side.points.forEach((p, i) => { const pa = prog(lt, .5 + k * (d * .33) + i * .45); ctx.globalAlpha = a * pa;
          const y = A.y + 360 + i * 110; circle(x + 54, y - 10, 18, fill); text(side.color === 'good' ? '✓' : '✕', x + 54, y - 9, { size: 24, weight: 800, color: col, align: 'center', base: 'middle' });
          para(p, x + 90, y, colW - 120, { size: 28, weight: 600 }); });
        ctx.restore(); });
      if (s.winner !== 'none') { const k = prog(lt, d * .72, .5), x = A.x + 30 + (s.winner === 'right' ? colW + 40 : 0);
        ctx.save(); ctx.globalAlpha = k; ctx.lineWidth = 6; ctx.strokeStyle = C.green; rr(x - 6, A.y + 204, colW + 12, 532, 32); ctx.stroke();
        fillRR(x + colW - 170, A.y + 750, 170, 52, 26, C.green); text('BETTER', x + colW - 85, A.y + 785, { size: 22, weight: 800, font: MONO, color: C.white, align: 'center', spacing: 3 }); ctx.restore(); }
    },
    character(s, lt) {
      const y = A.y + 470 + Math.sin(lt * 2.2) * 6; ctx.save(); ctx.translate(cx - 80, y); ctx.scale(.85, .85); sam(0, -40, s.mood, lt); ctx.restore();
      const props = s.props || []; props.forEach((p, i) => { const a = prog(lt, .8 + i * .5), ang = -Math.PI * .85 + i * (Math.PI * .7 / Math.max(1, props.length - 1));
        ctx.save(); ctx.globalAlpha = a; icon(p, cx - 80 + Math.cos(ang) * 300, A.y + 470 + Math.sin(ang) * 230 + Math.sin(lt * 1.6 + i) * 6, 110); ctx.restore(); });
      const bub = s.say || s.line; if (bub) { const a = prog(lt, 1.4), bx = cx + 40, maxW = A.x + A.w - bx - 30, ls = wrap(bub, maxW - 60, 32, 700), bh = 40 + ls.length * 40;
        ctx.save(); ctx.globalAlpha *= a; shadow(); fillRR(bx, A.y + 150, maxW, bh, 26, C.white, C.line); noShadow(); ctx.fillStyle = C.white; ctx.beginPath(); ctx.moveTo(bx + 40, A.y + 150 + bh - 2); ctx.lineTo(bx - 10, A.y + 150 + bh + 50); ctx.lineTo(bx + 110, A.y + 150 + bh - 2); ctx.fill();
        ls.forEach((l, k) => text(l, bx + 30, A.y + 200 + k * 40, { size: 32, weight: 700, color: C.navy })); ctx.restore(); }
      if (s.say && s.line) text(s.line, cx - 80, A.y + A.h - 40, { size: 30, weight: 600, color: C.muted, align: 'center', alpha: prog(lt, 2) });
    },
    bignumber(s, lt) {
      const k = ease((lt - .3) / 1.8), v = Math.round(s.value * k);
      text(v.toLocaleString(), cx, A.y + 400, { size: 220, weight: 800, color: C.accent, align: 'center' });
      text(s.unit, cx, A.y + 470, { size: 40, weight: 600, color: C.navy, align: 'center', alpha: prog(lt, 1) });
      text(s.label, cx, A.y + 240, { size: 22, font: MONO, color: C.muted, align: 'center', spacing: 5, alpha: prog(lt, .4) });
      (s.compare || []).forEach(([name, n], i) => { const a = prog(lt, cueStart(s._t, 1) + i * .4), y = A.y + 560 + i * 74, max = s.value, w = (A.w - 420) * (n / max) * ease((lt - cueStart(s._t, 1) - i * .4) / 1);
        ctx.save(); ctx.globalAlpha = a; text(name, A.x + 60, y + 30, { size: 26, weight: 600 }); fillRR(A.x + 380, y + 6, A.w - 460, 34, 17, '#e3e9f6'); fillRR(A.x + 380, y + 6, Math.max(34, w), 34, 17, [C.blue, C.red, C.green][i % 3]);
        text(String(n), A.x + 380 + Math.max(34, w) + 14, y + 32, { size: 26, weight: 800 }); ctx.restore(); });
    },
    steps(s, lt, d) {
      const n = s.items.length, gap = Math.min(128, 620 / n); ctx.strokeStyle = '#cbd8f2'; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(A.x + 110, A.y + 180); ctx.lineTo(A.x + 110, A.y + 180 + gap * (n - 1)); ctx.stroke();
      s.items.forEach((it, i) => { const at = .4 + i * ((d - 2) / n), a = prog(lt, at), y = A.y + 180 + i * gap, col = [C.blue, C.red, C.yellow, C.green, C.accent, C.navy][i % 6];
        ctx.save(); ctx.globalAlpha = .25 + .75 * a; circle(A.x + 110, y, 36, a > .5 ? col : C.white, col, 5); text(String(i + 1), A.x + 110, y + 1, { size: 30, weight: 800, color: a > .5 ? C.white : col, align: 'center', base: 'middle' });
        shadow(16, 6); fillRR(A.x + 170 + (1 - a) * 30, y - 42, A.w - 220, 84, 20, C.white); noShadow(); para(it, A.x + 200 + (1 - a) * 30, y + 11, A.w - 280, { size: 30, weight: 600 }); ctx.restore(); });
    },
    timeline(s, lt, d) {
      const n = s.events.length, x0 = A.x + 90, x1 = A.x + A.w - 90, y = A.y + 440, k = ease((lt - .3) / (d * .6));
      fillRR(x0, y - 5, x1 - x0, 10, 5, '#d4def2'); fillRR(x0, y - 5, (x1 - x0) * k, 10, 5, C.accent);
      s.events.forEach(([when, what], i) => { const x = lerp(x0, x1, n === 1 ? 0 : i / (n - 1)), a = clamp((k * (n - 1) - i) * 2 + 1), up = i % 2 === 0;
        ctx.save(); ctx.globalAlpha = a; circle(x, y, 20, i === n - 1 ? C.green : C.accent, C.white, 6);
        text(when, x, up ? y - 70 : y + 92, { size: 30, weight: 800, color: C.navy, align: 'center' });
        const lines = wrap(what, 230, 24, 500); lines.forEach((l, j) => text(l, x, (up ? y - 150 - (lines.length - 1 - j) * 32 : y + 132 + j * 32), { size: 24, color: C.muted, align: 'center' })); ctx.restore(); });
    },
    quiz(s, lt) {
      const reveal = cueStart(s._t, 2), shown = lt >= reveal;
      para(s.question, A.x + 60, A.y + 150, A.w - 120, { size: 38, weight: 700, color: C.navy, alpha: prog(lt, .2) });
      s.choices.forEach((ch, i) => { const a = prog(lt, .8 + i * .3), y = A.y + 330 + i * 140, right = i === s.answer, col = shown ? (right ? C.good : '#9aa7bf') : C.navy;
        ctx.save(); ctx.globalAlpha = a * (shown && !right ? .55 : 1); shadow(16, 6); fillRR(A.x + 60, y, A.w - 120, 110, 24, shown && right ? C.goodFill : C.white, shown && right ? C.good : C.line, shown && right ? 5 : 2); noShadow();
        circle(A.x + 130, y + 55, 30, shown && right ? C.good : '#e8f0fe'); text('ABC'[i], A.x + 130, y + 56, { size: 28, weight: 800, color: shown && right ? C.white : C.accent, align: 'center', base: 'middle' });
        text(ch, A.x + 190, y + 66, { size: 32, weight: 600, color: col }); ctx.restore(); });
      const think = cueStart(s._t, 1); if (lt > think && !shown) { const r = 40 + 6 * Math.sin(lt * 5); circle(A.x + A.w - 120, A.y + 150, r, '#fff4e5', C.ping, 4); text('?', A.x + A.w - 120, A.y + 152, { size: 44, weight: 800, color: C.ping, align: 'center', base: 'middle' }); }
    },
    image(s, lt) {
      if (/city/i.test(s.image_prompt) && s.ring) {  // a city map with homes, an office and the route
        fillRR(A.x, A.y + 120, A.w, A.h - 120, 30, '#e8f1e4'); ctx.save(); rr(A.x, A.y + 120, A.w, A.h - 120, 30); ctx.clip();
        ctx.strokeStyle = C.white; ctx.lineWidth = 22; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(A.x, A.y + 200 + i * 120); ctx.lineTo(A.x + A.w, A.y + 170 + i * 120); ctx.stroke(); ctx.beginPath(); ctx.moveTo(A.x + 80 + i * 180, A.y + 120); ctx.lineTo(A.x + 140 + i * 180, A.y + A.h); ctx.stroke(); }
        fillRR(A.x + 640, A.y + 600, 260, 120, 60, '#cfe3f7'); ctx.restore();
        const ox = A.x + A.w * s.ring[0], oy = A.y + A.h * s.ring[1] + 60; fillRR(ox - 40, oy - 110, 80, 110, 8, C.navy); for (let r = 0; r < 4; r++) for (let c = 0; c < 2; c++) fillRR(ox - 26 + c * 30, oy - 96 + r * 24, 22, 14, 3, C.yellow);
        const homes = [[.32, .46], [.46, .7], [.72, .64], [.8, .3], [.25, .78]]; homes.forEach(([hx, hy], i) => { const a = prog(lt, .6 + i * .3); const x = A.x + A.w * hx, y = A.y + A.h * hy + 60;
          const k = clamp((lt - 2.5 - i * .25) / 1); if (k > 0) { ctx.save(); ctx.globalAlpha = .8; ctx.setLineDash([14, 12]); ctx.strokeStyle = C.accent; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(ox, oy - 40); ctx.lineTo(lerp(ox, x, k), lerp(oy - 40, y - 30, k)); ctx.stroke(); ctx.restore(); }
          ctx.save(); ctx.globalAlpha = a; house(x, y, 70); ctx.restore(); });
        const pr = 70 + 8 * Math.sin(lt * 3); ctx.save(); ctx.globalAlpha = prog(lt, .4); ctx.lineWidth = 6; ctx.strokeStyle = C.ping; circle(ox, oy - 55, pr, null, C.ping, 6); ctx.restore();
        if (s.caption) { ctx.font = `700 28px ${FONT}`; const w = ctx.measureText(s.caption).width + 60; shadow(); fillRR(cx - w / 2, A.y + 150, w, 62, 31, C.white); noShadow(); text(s.caption, cx, A.y + 191, { size: 28, weight: 700, color: C.navy, align: 'center' }); }
      } else {  // the Google stack: five blocks feeding one home
        const blocks = s.caption.split('·').map(b => b.trim()), cols = [C.blue, C.green, C.red, C.yellow, C.navy];
        house(cx, A.y + A.h - 60, 180, C.white, C.navy, C.navy);
        blocks.forEach((b, i) => { const a = prog(lt, .4 + i * .45), x = A.x + 40 + i * ((A.w - 80) / blocks.length), w = (A.w - 80) / blocks.length - 20, y = A.y + 230 + (i % 2) * 120;
          ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = cols[i]; ctx.lineWidth = 5; ctx.setLineDash([10, 10]); ctx.lineDashOffset = -lt * 30; ctx.beginPath(); ctx.moveTo(x + w / 2, y + 110); ctx.lineTo(cx, A.y + A.h - 160); ctx.stroke(); ctx.setLineDash([]);
          shadow(18, 8); fillRR(x, y, w, 110, 22, C.white); noShadow(); fillRR(x, y, w, 10, [22, 22, 0, 0], cols[i]);
          const ls = wrap(b, w - 30, 25, 700); ls.forEach((l, j) => text(l, x + w / 2, y + 58 + j * 30 - (ls.length - 1) * 15, { size: 25, weight: 700, align: 'center' })); ctx.restore(); });
      }
    },
    flow(s, lt, d) {
      const n = s.nodes.length, w = (A.w - 60) / n - 30, y = A.y + 360;
      s.nodes.forEach((nd, i) => { const x = A.x + 30 + i * (w + 30 + 60 / Math.max(1, n - 1) * 0), a = prog(lt, .3 + i * (d * .5 / n)), col = [C.blue, C.red, C.yellow, C.green, C.accent][i % 5];
        ctx.save(); ctx.globalAlpha = a; shadow(18, 8); fillRR(x, y, w, 170, 24, C.white); noShadow(); fillRR(x, y, w, 12, [24, 24, 0, 0], col);
        const ls = wrap(nd, w - 30, 30, 700); ls.forEach((l, j) => text(l, x + w / 2, y + 96 + j * 36 - (ls.length - 1) * 18, { size: 30, weight: 700, align: 'center' }));
        if (i < n - 1) { const ax = x + w + 2, bx = x + w + 28; ctx.strokeStyle = C.navy; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(ax, y + 85); ctx.lineTo(bx, y + 85); ctx.stroke(); ctx.beginPath(); ctx.moveTo(bx - 10, y + 75); ctx.lineTo(bx, y + 85); ctx.lineTo(bx - 10, y + 95); ctx.stroke();
          if (s.labels && s.labels[i]) text(s.labels[i], x + w + 15, y + 230 + (i % 2) * 40, { size: 20, font: MONO, color: C.muted, align: 'center' });
          const k = ((lt * .6 - i * .3) % 1 + 1) % 1; if (a > .9) circle(lerp(ax, bx, k), y + 85, 6, C.ping); }
        ctx.restore(); });
      if (s.labels && s.labels.length >= n) text(s.labels[n - 1], A.x + 30 + (n - 1) * (w + 30) + w / 2, y + 230, { size: 20, font: MONO, color: C.muted, align: 'center', alpha: prog(lt, d * .5) });
    },
    bars(s, lt, d) {
      const max = Math.max(...s.bars.map(b => b[1])), n = s.bars.length, rowH = Math.min(120, 560 / n);
      text(s.title, A.x + 50, A.y + 240, { size: 30, weight: 700, color: C.navy, alpha: prog(lt, .2) });
      s.bars.forEach(([label, v], i) => { const k = ease((lt - .6 - i * .35) / 1.2), y = A.y + 300 + i * rowH, maxW = A.w - 600, col = n === 2 ? (i ? C.green : C.red) : [C.blue, C.red, C.yellow, C.green, C.accent][i % 5];
        ctx.save(); ctx.globalAlpha = clamp(k * 2); para(label, A.x + 50, y + rowH * .42, 300, { size: 24, weight: 600 }); fillRR(A.x + 370, y + rowH * .2, maxW, rowH * .42, 14, '#e3e9f6'); fillRR(A.x + 370, y + rowH * .2, Math.max(28, maxW * v / max * k), rowH * .42, 14, col);
        text(`${(v * k).toFixed(v % 1 ? 1 : 0)} ${s.unit}`, A.x + 370 + Math.max(28, maxW * v / max * k) + 14, y + rowH * .5, { size: 26, weight: 800, base: 'middle' }); ctx.restore(); });
    },
    analogy(s, lt) {
      const a1 = prog(lt, .3), a2 = prog(lt, 1.1), y = A.y + 230, w = 430;
      ctx.save(); ctx.globalAlpha = a1; shadow(); fillRR(A.x + 40, y, w, 300, 28, C.white); noShadow(); pin(A.x + 40 + w / 2, y + 170, 80); text(s.a, A.x + 40 + w / 2, y + 250, { size: 30, weight: 700, align: 'center' }); ctx.restore();
      text('is like', cx, y + 160, { size: 30, weight: 600, font: MONO, color: C.ping, align: 'center', alpha: a2 });
      ctx.save(); ctx.globalAlpha = a2; shadow(); fillRR(A.x + A.w - 40 - w, y, w, 300, 28, C.white); noShadow(); const fx = A.x + A.w - 40 - w / 2;
      face(fx - 60, y + 130, 52, 'happy', lt); ctx.strokeStyle = C.navy; ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(fx - 12, y + 140 + Math.sin(lt * 2.2) * 6); ctx.lineTo(fx + 80, y + 100 + Math.sin(lt * 3) * 8); ctx.stroke(); house(fx + 120, y + 175, 60);
      ((l) => l.forEach((x, j) => text(x, fx, y + 238 + j * 32, { size: 26, weight: 700, align: 'center' })))(wrap(s.b, w - 40, 26, 700)); ctx.restore();
      para(s.mapping, A.x + 60, y + 400, A.w - 120, { size: 30, color: C.muted, alpha: prog(lt, cueStart(s._t, 1)) });
    },
    recap(s, lt, d) {
      s.items.forEach((it, i) => { const at = .5 + i * ((d * .62) / s.items.length), a = prog(lt, at), y = A.y + 140 + i * 128;
        ctx.save(); ctx.globalAlpha = .25 + .75 * a; shadow(16, 6); fillRR(A.x + 40, y, A.w - 80, 100, 24, C.white); noShadow();
        circle(A.x + 100, y + 50, 28, a > .6 ? C.green : '#e6f4ea'); if (a > .6) { ctx.strokeStyle = C.white; ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(A.x + 88, y + 50); ctx.lineTo(A.x + 98, y + 61); ctx.lineTo(A.x + 115, y + 39); ctx.stroke(); }
        text(it, A.x + 150, y + 62, { size: 30, weight: 600 }); ctx.restore(); });
      const fa = prog(lt, cueStart(s._t, s.cues.length - 1)); ctx.save(); ctx.globalAlpha = fa; fillRR(A.x + 40, A.y + A.h - 170, A.w - 80, 130, 30, C.navy);
      text(s.final, cx, A.y + A.h - 88, { size: 42, weight: 800, color: C.white, align: 'center' }); circle(A.x + A.w - 90, A.y + A.h - 140, 12, C.ping); ctx.restore();
    },
  };

  // ---------- frame ----------
  function sceneAt(t) { let i = TIMINGS.scenes.findIndex(s => t < s.end); if (i < 0) i = TIMINGS.scenes.length - 1; return i; }
  function render(t) {
    t = clamp(t, 0, TIMINGS.total);
    const i = sceneAt(t), tm = TIMINGS.scenes[i], s = STORYBOARD[i], lt = t - tm.start, d = tm.end - tm.start;
    s._t = tm; backdrop(t, i);
    const ci = tm.cues.findIndex(c => t < c.end + .45), c = tm.cues[ci < 0 ? tm.cues.length - 1 : ci];
    const fadeIn = clamp(lt / .5), fadeOut = i === STORYBOARD.length - 1 ? 1 : clamp((tm.end - t) / .45);
    ctx.save(); ctx.globalAlpha = Math.min(fadeIn, fadeOut);
    if (s.draw !== 'character') sam(360, 470, moodFor(s), t);
    ctx.save(); ctx.translate(BOARD.x, BOARD.y + (1 - prog(lt, 0, .6)) * 30); ctx.scale(BOARD.s, BOARD.s);
    shadow(50, 24, 'rgba(0,0,0,.45)'); fillRR(-24, -24, ART.w + 48, ART.h + 48, 40, 'rgba(255,255,255,.93)'); noShadow();
    (DRAW[s.draw] || (() => {}))(s, lt, d); infoCard(s.card, lt); statCard(s.stat, s.pill, lt); ctx.restore();
    topBar(s, i, lt); caption(s, i, lt); subtitle(c && { text: c.text, lt0: c.start - tm.start, lt1: c.end - tm.start }, lt);
    ctx.restore(); chapterBar(t);
  }

  // ---------- playback: the voice track is the clock when there is one ----------
  const btn = document.getElementById('play'), audio = document.getElementById('voice');
  let playing = false, t0 = 0, startedAt = 0;
  const now = () => HAS_VOICE ? audio.currentTime : (playing ? (performance.now() - startedAt) / 1000 : t0);
  function loop() { const t = now(); render(t); if (playing && t >= TIMINGS.total) { playing = false; btn.textContent = 'Restart'; window.dispatchEvent(new Event('videoend')); } if (playing) requestAnimationFrame(loop); }
  function play(from = 0) { playing = true; btn.textContent = 'Restart'; if (HAS_VOICE) { audio.currentTime = from; audio.play(); } else { startedAt = performance.now() - from * 1000; } requestAnimationFrame(loop); }
  btn.addEventListener('click', () => play(0));
  window.clearHouseVideo = { render, play, total: TIMINGS.total };
  const seek = new URLSearchParams(location.search).get('t');
  Promise.all([document.fonts.load(`800 60px 'Google Sans'`), document.fonts.load(`400 30px 'Google Sans'`)]).then(() => { render(seek ? +seek : 0); window.videoReady = true; if (new URLSearchParams(location.search).get('autoexport')) { document.body.classList.add('recording'); document.getElementById('export').click(); } });

  // ---------- export: record the canvas (and voice) to a video file ----------
  document.getElementById('export')?.addEventListener('click', async () => {
    const stream = cv.captureStream(30);
    if (HAS_VOICE) { const ac = new AudioContext(), src = ac.createMediaElementSource(audio), dest = ac.createMediaStreamDestination(); src.connect(dest); src.connect(ac.destination); dest.stream.getAudioTracks().forEach(tr => stream.addTrack(tr)); }
    const type = ['video/mp4;codecs=avc1,mp4a.40.2', 'video/mp4', 'video/webm;codecs=vp9,opus', 'video/webm'].find(m => MediaRecorder.isTypeSupported(m));
    const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 8e6 }), parts = [];
    rec.ondataavailable = e => e.data.size && parts.push(e.data);
    rec.onstop = async () => { const blob = new Blob(parts, { type }), name = `clear-house-explainer${HAS_VOICE ? '' : '-silent'}.${type.includes('mp4') ? 'mp4' : 'webm'}`;
      if (window.UPLOAD_URL) await fetch(window.UPLOAD_URL + '?name=' + name, { method: 'POST', body: blob });
      else { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); } };
    window.addEventListener('videoend', () => setTimeout(() => rec.stop(), 400), { once: true });
    rec.start(1000); play(0);
  });
})();
