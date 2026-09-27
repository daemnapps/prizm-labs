/* page.js — the making-of half of daemn.co/carousel/ (first published as /ai-slop/).

   1. One focus at a time: only the clip most in view plays (muted); clips
      load nothing until they are near.
   2. The stem map: draws the 38.7-second loop from m/sound.json as one SVG —
      12 bars, the kick hits, the bass notes as a piano roll, the four stem
      lanes as loudness, and the remix moves over the bars they change. While
      the piece (or the remix excerpt) plays, a playhead runs across it.
   No colours here: every mark carries a class that goja-theme.css paints.
*/
(() => {
  const CALM = matchMedia('(prefers-reduced-motion:reduce)').matches;

  /* ── 1. one focus at a time ─────────────────────────────────────────
     Like a social feed: only the one thing most in view plays. Every clip
     (video[data-clip]), the piece (#piece) and anything marked [data-focus]
     (a drawn post cover, a 3D object tile) is watched; the one that fills the
     most of the screen, nearest the centre, is the focus. A focused clip plays
     muted; every other clip is paused on its still. A focused cover or 3D tile
     gets .is-focus, which is what lets it move. Clips load nothing until they
     are near. Playing a player by hand (the edit's video, a stem) pauses the
     focus until it stops. */
  const clips = [...document.querySelectorAll('video[data-clip]')];
  const piece = document.getElementById('piece');
  const watched = [...new Set([piece, ...clips, ...document.querySelectorAll('[data-focus]')])].filter(Boolean);
  const isClip = el => el.tagName === 'VIDEO';
  // phones only autoplay a clip that is muted and inline as properties, set before the source loads
  const prime = v => {
    if (!isClip(v)) return;
    if (!v.poster && v.dataset.poster) v.poster = v.dataset.poster;
    if (v.dataset.clip && !v.src) { v.muted = true; v.defaultMuted = true; v.playsInline = true; v.setAttribute('playsinline', ''); v.src = v.dataset.clip; v.load(); }
  };
  if ('IntersectionObserver' in window) {
    // a clip's still arrives a screen ahead; its video only once it is close
    const still = new IntersectionObserver(es => es.forEach(e => { const v = e.target; if (e.isIntersecting && !v.poster && v.dataset.poster) { v.poster = v.dataset.poster; still.unobserve(v); } }), {rootMargin: '100% 0px'});
    const near = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) prime(e.target); }), {rootMargin: '200px 0px'});
    clips.forEach(v => { still.observe(v); near.observe(v); });

    const seen = new Map();
    let focus = null, manual = null, blocked = false, ours = false;
    const TH = Array.from({length: 21}, (_, i) => i / 20);
    const io = new IntersectionObserver(es => {
      const vw = innerWidth, vh = innerHeight;
      es.forEach(e => {
        if (!e.isIntersecting) { seen.delete(e.target); return; }
        const r = e.intersectionRect, b = e.boundingClientRect;
        const full = Math.min(b.width * b.height, vw * vh) || 1;
        seen.set(e.target, {s: (r.width * r.height) / full, d: Math.hypot(r.left + r.width / 2 - vw / 2, r.top + r.height / 2 - vh / 2)});
      });
      pick();
    }, {threshold: TH});
    watched.forEach(el => io.observe(el));

    function pick() {
      let best = null, bm = null;
      seen.forEach((m, el) => {
        if (m.s < .5) return;
        if (!bm || m.s > bm.s + .08 || (Math.abs(m.s - bm.s) <= .08 && m.d < bm.d)) { best = el; bm = m; }
      });
      focusOn(best);
    }
    const pause = v => { if (!v.paused) { ours = true; v.pause(); ours = false; } };
    function tryPlay(v) { const p = v.play(); p && p.catch && p.catch(() => { blocked = true; }); }
    function focusOn(el) {
      if (el !== focus) {
        if (focus) { focus.classList.remove('is-focus'); if (isClip(focus)) { pause(focus); focus.held = false; } }
        focus = el;
        if (el) {
          el.classList.add('is-focus');
          // in a swipe row, get the next item's clip ready so it is there when the thumb gets there
          const slide = el.closest('.gj-snap > *');
          if (slide) [slide.nextElementSibling, slide.previousElementSibling].forEach(s => s && s.querySelectorAll('video[data-clip]').forEach(prime));
        }
        document.dispatchEvent(new CustomEvent('gj-focus', {detail: el}));
      }
      if (focus && isClip(focus)) {
        if (manual || focus.held) pause(focus);
        else if (focus.paused) { prime(focus); tryPlay(focus); }
      }
    }
    // a clip paused by hand stays paused while it is the focus
    watched.filter(isClip).forEach(v => {
      v.addEventListener('pause', () => { if (!ours && v === focus && !v.ended) v.held = true; });
      v.addEventListener('play', () => { v.held = false; if (v !== focus) pause(v); });
    });
    // a player played by hand takes over; the focus waits until it stops
    document.addEventListener('play', e => {
      const m = e.target;
      if (watched.includes(m)) return;
      manual = m; if (focus && isClip(focus)) pause(focus);
    }, true);
    const release = e => { if (e.target === manual) { manual = null; focusOn(focus); } };
    document.addEventListener('pause', release, true); document.addEventListener('ended', release, true);
    // if the phone still refuses to autoplay (Low Power Mode), the first touch anywhere starts the focus
    const wake = () => { if (!blocked) return; blocked = false; if (focus && isClip(focus) && !manual) tryPlay(focus); };
    addEventListener('touchstart', wake, {passive: true}); addEventListener('click', wake);
  } else clips.forEach(v => { if (v.dataset.poster) v.poster = v.dataset.poster; v.src = v.dataset.clip; });

  /* ── 2. the stem map ──────────────────────────────────────────────── */
  const box = document.getElementById('stem-map');
  if (!box) return;
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent, text) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text !== undefined) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const f = n => Math.round(n * 10) / 10;

  function draw(d) {
    const W = 1200, X0 = 112, X1 = 1186, L = d.loop;
    const x = t => X0 + (t / L) * (X1 - X0);
    const LANES = [['drums', 'Drums'], ['bass', 'Bass'], ['vocals', 'Vocals'], ['other', 'Other']];
    const top = {bars: 16, moves: 38, kick: 52, roll: 100, lanes: 208}, KH = 36, RH = 92, LH = 58;
    const H = top.lanes + LANES.length * LH + 8;
    const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': 'The 38.7-second loop: 12 bars. Kick hits, the bass line as notes, and the four stems as loudness, with the remix moves on bars 5 to 10.'});

    // the remix moves: a band over each bar they change
    const barX = i => x(d.bars[i]), barW = i => x(d.bars[i + 1]) - x(d.bars[i]);
    const byBar = {};
    d.moves.forEach(m => { (byBar[m.bar] = byBar[m.bar] || []).push(m); });
    Object.entries(byBar).forEach(([b, ms]) => {
      const i = b - 1, drums = ms[0].lane === 'drums';
      el('rect', {class: 'band' + (drums ? ' drums' : ''), x: f(barX(i)), y: top.moves - 12, width: f(barW(i)), height: H - top.moves + 4}, svg);
      el('text', {class: 't-move', x: f(barX(i) + barW(i) / 2), y: top.moves, 'text-anchor': 'middle'}, svg, ms[0].what);
    });
    // bar lines and numbers
    d.bars.forEach((t, i) => {
      el('line', {class: 'grid' + (i % 4 === 0 ? ' bar1' : ''), x1: f(x(t)), x2: f(x(t)), y1: top.moves + 6, y2: H - 4}, svg);
      if (i < 12) el('text', {class: 't-bar', x: f(x(t) + 5), y: top.bars}, svg, String(i + 1));
    });
    const lane = (y, name) => el('text', {class: 't-lane', x: 12, y: y}, svg, name);

    // the kicks
    lane(top.kick + KH / 2 + 4, 'Kick');
    d.kicks.forEach(t => el('line', {class: 'kick', x1: f(x(t)), x2: f(x(t)), y1: top.kick + 6, y2: top.kick + KH - 6}, svg));

    // the bass line, as a piano roll
    lane(top.roll + 14, 'Bass');
    el('text', {x: 12, y: top.roll + 30}, svg, 'notes');
    const ms = d.bass.map(n => n.m), lo = Math.floor(Math.min(...ms)) - 1, hi = Math.ceil(Math.max(...ms)) + 1;
    const ny = m => top.roll + RH - ((m - lo) / (hi - lo)) * RH;
    [28, 33, 40, 45].filter(m => m > lo && m < hi).forEach(m => {
      el('line', {class: 'keyline', x1: X0, x2: X1, y1: f(ny(m)), y2: f(ny(m))}, svg);
      el('text', {x: X0 - 8, y: f(ny(m) + 4), 'text-anchor': 'end'}, svg, {28: 'E1', 33: 'A1', 40: 'E2', 45: 'A2'}[m]);
    });
    d.bass.forEach(n => el('rect', {class: 'note', x: f(x(n.t)), y: f(ny(n.m) - 3), width: f(Math.max(2, x(n.t + n.d) - x(n.t) - 1)),
      height: 6, rx: 2, opacity: (.45 + n.l * .55).toFixed(2)}, svg));

    // the four stems, as loudness (what the loop actually plays, remix moves included)
    LANES.forEach(([k, name], li) => {
      const y0 = top.lanes + li * LH, mid = y0 + LH / 2, amp = LH / 2 - 5, pts = [], low = [];
      lane(mid + 4, name);
      d.lanes[k].forEach((row, b) => row.forEach((v, j) => {
        const t = d.bars[b] + (d.bars[b + 1] - d.bars[b]) * (j + .5) / row.length, px = f(x(t));
        pts.push(`${px},${f(mid - v * amp)}`); low.unshift(`${px},${f(mid + v * amp)}`);
      }));
      el('polygon', {class: 'env ' + k, points: pts.concat(low).join(' ')}, svg);
    });

    const head = el('line', {class: 'head', x1: X0, x2: X0, y1: top.moves - 12, y2: H - 4}, svg);
    box.replaceChildren(svg);
    return {head, x, L, remixAt: d.bars[5]};   // the remix excerpt starts on bar 6 (build_assets.py)
  }

  function follow(m) {
    const piece = document.getElementById('piece'), remix = document.getElementById('remix'), loop = document.getElementById('loop');
    let seen = false, raf = 0;
    const tick = () => {
      raf = 0;
      let t = null;
      if (loop && !loop.paused) t = loop.currentTime % m.L;
      else if (remix && !remix.paused) t = m.remixAt + remix.currentTime;
      else if (piece && !piece.paused) { const pt = piece.currentTime - 3.6; t = pt >= 0 ? pt % m.L : null; }   // the piece opens with the 3.6s scroll stopper
      if (t === null) { m.head.classList.remove('on'); }
      else {
        const px = f(m.x(t)); m.head.setAttribute('x1', px); m.head.setAttribute('x2', px); m.head.classList.add('on');
      }
      if (seen) raf = requestAnimationFrame(tick);
    };
    new IntersectionObserver(es => { seen = es[0].isIntersecting; if (seen && !raf) raf = requestAnimationFrame(tick); }).observe(box);
  }

  const load = () => fetch(box.dataset.src).then(r => r.json()).then(d => follow(draw(d))).catch(e => {
    box.textContent = 'The stem map could not load.'; console.warn('stem map', e);
  });
  if ('IntersectionObserver' in window) {
    const near = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { near.disconnect(); load(); } }, {rootMargin: '800px 0px'});
    near.observe(box);
  } else load();
})();

/* ── 3. the edit map ─────────────────────────────────────────────────────
   The whole 42.3-second piece as a stack of layers on one clock, from m/edit.json
   (build_edit_map.py): the picture, the scenes, the camera, the jump cuts, the
   outfit swaps, the persona flashes, the 3D objects, the finish and the sound.
   Its own player sits above it: the playhead follows it, a tap on the map jumps
   the video there, and the line under the player names what is on screen. */
(() => {
  const box = document.getElementById('edit-map');
  if (!box) return;
  const vid = document.getElementById('edit-video'), now = document.getElementById('edit-now');
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent, text) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text !== undefined) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  };
  const f = n => Math.round(n * 10) / 10;
  const clock = t => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, '0')}`;

  function draw(d) {
    const PX = 64, W = Math.ceil(d.total * PX) + 16, x = t => 8 + t * PX;
    const LANES = [['ruler', '', 22], ['film', 'Picture', 100], ['scenes', 'Scenes', 44], ['camera', 'Camera', 50],
      ['speed', 'Speed', 64], ['zoom', 'Zoom', 52], ['turn', 'Turn', 52], ['reframe', 'Reframe', 44], ['picture', 'Treatment', 50],
      ['jumps', 'Jump cuts', 28], ['outfits', 'Outfits', 34], ['flashes', 'Personas', 34], ['objects', '3D objects', 50], ['osize', 'Object size', 48], ['ospeed', 'Object speed', 48],
      ['finish', 'Finish', 50], ['sound', 'Sound', 44]];
    const top = {}; let y = 0;
    LANES.forEach(([k, , h]) => { top[k] = y; y += h; });
    const H = y + 6;
    const labels = box.querySelector('.gj-edit-labels'), scroll = box.querySelector('.gj-edit-scroll');
    labels.replaceChildren(...LANES.map(([k, name, h]) => { const s = document.createElement('span'); s.textContent = name; s.style.height = h + 'px'; return s; }));
    const svg = el('svg', {width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': 'The edit as layers over 42.3 seconds: picture, scenes, camera, jump cuts, outfits, personas, 3D objects, finish and sound.'});
    const tip = (n, t) => { el('title', {}, n, t); return n; };
    const band = (k, a, b, cls, row = 0, rows = 1, label) => {
      const h = (LANES.find(l => l[0] === k)[2] - 10) / rows, yy = top[k] + 5 + row * h;
      const r = el('rect', {class: cls, x: f(x(a)), y: f(yy + 1), width: f(Math.max(2, x(b) - x(a) - 1)), height: f(h - 2), rx: 3}, svg);
      if (label && x(b) - x(a) > label.length * 6.2 + 8) el('text', {class: 't-in', x: f(x(a) + 5), y: f(yy + h / 2 + 4)}, svg, label);
      return r;
    };
    // the loop starts after the opener: shade the opener, rule every lane
    el('rect', {class: 'e-pre', x: x(0), y: 0, width: f(x(d.pre) - x(0)), height: H}, svg);
    LANES.slice(1).forEach(([k]) => el('line', {class: 'grid', x1: 0, x2: W, y1: top[k], y2: top[k]}, svg));
    // the ruler: seconds, and the bar numbers of the loop
    for (let s = 0; s <= d.total; s++) {
      el('line', {class: 'grid' + (s % 5 ? '' : ' bar1'), x1: x(s), x2: x(s), y1: 14, y2: H}, svg);
      if (s % 5 === 0) el('text', {class: 't-bar', x: x(s) + 3, y: 12}, svg, clock(s).replace('.0', ''));
    }
    // picture
    const fm = d.film, fh = LANES[1][2] - 4, fw = fh * fm.w / fm.h, n = Math.floor(d.total / fm.step);
    const clip = el('clipPath', {id: 'e-film'}, el('defs', {}, svg));
    el('rect', {x: x(0), y: top.film + 2, width: f(x(d.total) - x(0)), height: fh}, clip);
    const g = el('g', {'clip-path': 'url(#e-film)'}, svg);
    for (let i = 0; i < n; i++) {
      const sv = el('svg', {x: f(x(i * fm.step)), y: top.film + 2, width: f(fm.step * PX), height: fh, viewBox: `${i * fm.w} 0 ${fm.w} ${fm.h}`, preserveAspectRatio: 'xMidYMid slice'}, g);
      el('image', {href: fm.src, x: 0, y: 0, width: n * fm.w, height: fm.h}, sv);
    }
    // scenes
    d.scenes.forEach(s => tip(band('scenes', s.a, s.b, 'e-scene ' + s.kind, 0, 1, s.n), `${s.n} · ${s.name || ''} — ${s.what}`));
    // camera: moves on two rows, turns at the cuts as marks
    d.camera.forEach((c, i) => tip(band('camera', c.a, c.b, 'e-cam', i === 0 || i === 2 || i === 6 ? 0 : 1, 2, c.t), c.t));
    d.camera.filter(c => c.hat).forEach(c => el('circle', {class: 'e-hat', cx: f(x(c.hat)), cy: top.camera + 30, r: 4}, svg));
    d.turns.forEach(t => tip(el('path', {class: 'e-turn', d: `M${f(x(t))} ${top.camera + 3} l5 5 -5 5 -5 -5z`}, svg), 'turn + push around him at the cut'));
    // the picture and the movement, frame by frame: curves on the loop's clock (the opener is a 3D render)
    const C = d.curves, ct = i => C.start + i / C.fps;
    const curve = (k, arr, lo, hi, cls, refs) => {
      const h = LANES.find(l => l[0] === k)[2], y0 = top[k] + 6, yh = h - 12;
      const yy = v => f(y0 + yh - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo) * yh);
      (refs || []).forEach(([v, t]) => {
        el('line', {class: 'e-ref', x1: x(C.start), x2: x(d.total), y1: yy(v), y2: yy(v)}, svg);
        el('text', {class: 't-ref', x: f(x(C.start) - 4), y: yy(v) + 3, 'text-anchor': 'end'}, svg, t);
      });
      let path = '', pen = false;
      arr.forEach((v, i) => {
        if (v === null || v === undefined) { pen = false; return; }
        path += (pen ? 'L' : 'M') + f(x(ct(i))) + ' ' + yy(v); pen = true;
      });
      el('path', {class: 'e-curve ' + cls, d: path}, svg);
    };
    curve('speed', C.speed, -4, 6, 'c-speed', [[0, ''], [-3, '−3×'], [5, '5×']]);
    curve('zoom', C.zoom, 1, 2.1, 'c-zoom', [[1, '1×'], [1.5, '1.5×'], [2, '2×']]);
    curve('turn', C.turn, -12, 12, 'c-turn', [[0, '0°'], [11, '11°'], [-11, '−11°']]);
    curve('reframe', C.reframe, 0, Math.max(60, ...C.reframe), 'c-ref', [[0, '0'], [Math.round(Math.max(...C.reframe) / 10) * 10, Math.round(Math.max(...C.reframe) / 10) * 10 + 'px']]);
    d.picture.forEach(q => tip(band('picture', q.a, q.b, 'e-pic' + (q.row ? ' r1' : ''), q.row, 2, q.t), q.t));
    curve('osize', C.osize, 0, 3.6, 'c-osize', [[1, '1×'], [3.4, 'at lens']]);
    curve('ospeed', C.ospeed, 0, 120, 'c-ospeed', [[0, '0'], [14, 'smear'], [100, '100px']]);
    const _o = el('text', {class: 't-ref', x: f(x(d.pre / 2)), y: top.zoom + 30, 'text-anchor': 'middle'}, svg, 'opener: a 3D render');
    // jump cuts
    d.jumps.forEach(t => tip(el('line', {class: 'e-jump', x1: f(x(t)), x2: f(x(t)), y1: top.jumps + 6, y2: top.jumps + 22}, svg), 'jump cut on the kick'));
    // outfits, personas
    d.outfits.forEach(o => tip(band('outfits', o.a, o.b, 'e-fit', 0, 1, o.o), 'AI him in the ' + o.o + ' look, same motion'));
    d.flashes.forEach(p => {
      tip(band('flashes', p.a, p.b + 0.05, 'e-flash'), p.p + ' flash · 4 frames');
      el('text', {class: 't-flash', x: f(x(p.b) + 5), y: top.flashes + 21}, svg, p.p);
    });
    // 3D objects on two rows, with the hand-offs at the lens
    d.objects.forEach((o, i) => {
      tip(band('objects', o.a, o.b, 'e-obj', i % 2, 2, o.o), o.o);
      o.lens.forEach(t => el('circle', {class: 'e-lens', cx: f(x(t)), cy: top.objects + 5 + (i % 2) * 20 + 10, r: 3.5}, svg));
    });
    // finish
    d.finish.forEach((q, i) => tip(band('finish', q.a, q.b, 'e-fin' + (i === 2 ? ' frz' : ''), i === 2 ? 1 : i, 2, q.t), q.t));
    // sound: the phone-speaker lead-in, bars, kicks
    tip(band('sound', d.sound.pre[0], d.sound.pre[1], 'e-lead', 0, 1, 'lead-in'), 'the song, thin like a phone speaker, opening up');
    d.sound.bars.forEach((t, i) => {
      el('line', {class: 'e-barl', x1: f(x(t)), x2: f(x(t)), y1: top.sound + 4, y2: top.sound + 40}, svg);
      if (i < 12) el('text', {class: 't-bar', x: f(x(t) + 4), y: top.sound + 15}, svg, 'bar ' + (i + 1));
    });
    d.sound.kicks.forEach(t => el('line', {class: 'kick', x1: f(x(t)), x2: f(x(t)), y1: top.sound + 22, y2: top.sound + 38}, svg));
    const head = el('line', {class: 'head on', x1: x(0), x2: x(0), y1: 0, y2: H}, svg);
    scroll.replaceChildren(svg);
    return {d, x, PX, head, svg, scroll};
  }

  function live(m) {
    const {d} = m, at = (list, t) => list.find(o => o.a <= t && t < o.b);
    const say = t => {
      const s = at(d.scenes, t), o = at(d.outfits, t), p = at(d.flashes, t), b = at(d.objects, t), c = d.camera.filter(c => c.a <= t && t < c.b).pop();
      const bits = [clock(t), s ? `scene ${s.n}${s.name ? ' · ' + s.name : ''}` : ''];
      if (p) bits.push(p.p + ' flash'); else if (o) bits.push(o.o + ' look');
      if (b) bits.push(b.o); if (c) bits.push(c.t);
      const i = Math.round((t - d.curves.start) * d.curves.fps);
      if (i >= 0 && i < d.curves.zoom.length) {
        const sp = d.curves.speed[i];
        bits.push(`speed ${sp === null ? '3D' : sp.toFixed(1) + '×'} · zoom ${d.curves.zoom[i].toFixed(2)}× · turn ${d.curves.turn[i].toFixed(0)}°`);
      }
      if (now) now.textContent = bits.filter(Boolean).join('  ·  ');
    };
    let raf = 0, seen = false, last = -1;
    const tick = () => {
      raf = 0;
      const piece = document.getElementById('piece');
      const src = vid && !vid.paused ? vid : piece && !piece.paused ? piece : vid;
      const t = src ? src.currentTime % d.total : 0;
      if (Math.abs(t - last) > 0.01) {
        last = t; const px = f(m.x(t)); m.head.setAttribute('x1', px); m.head.setAttribute('x2', px); say(t);
        if (src && !src.paused) {                       // keep the playhead in view while it plays
          const sc = m.scroll, left = px - sc.clientWidth * 0.35;
          if (px < sc.scrollLeft + 40 || px > sc.scrollLeft + sc.clientWidth - 60) sc.scrollLeft = left;
        }
      }
      if (seen) raf = requestAnimationFrame(tick);
    };
    new IntersectionObserver(es => { seen = es[0].isIntersecting; if (seen && !raf) raf = requestAnimationFrame(tick); }).observe(box);
    m.svg.addEventListener('click', e => {             // tap the map: the video jumps there
      const r = m.svg.getBoundingClientRect(), t = Math.max(0, Math.min(d.total - 0.05, (e.clientX - r.left - 8) / m.PX));
      if (vid) { vid.currentTime = t; const p = vid.play(); p && p.catch && p.catch(() => {}); }
      say(t);
    });
    say(0);
  }

  const load = () => fetch(box.dataset.src).then(r => r.json()).then(d => live(draw(d))).catch(e => {
    box.querySelector('.gj-edit-scroll').textContent = 'The edit map could not load.'; console.warn('edit map', e);
  });
  if ('IntersectionObserver' in window) {
    const near = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { near.disconnect(); load(); } }, {rootMargin: '800px 0px'});
    near.observe(box);
  } else load();
})();
