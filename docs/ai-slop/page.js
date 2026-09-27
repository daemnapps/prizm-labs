/* page.js — the making-of half of daemn.co/ai-slop/.

   1. Clips (video[data-clip]) load nothing until they are near, play muted
      while on screen, and pause when they leave.
   2. The stem map: draws the 38.7-second loop from m/sound.json as one SVG —
      12 bars, the kick hits, the bass notes as a piano roll, the four stem
      lanes as loudness, and the remix moves over the bars they change. While
      the piece (or the remix excerpt) plays, a playhead runs across it.
   No colours here: every mark carries a class that goja-theme.css paints.
*/
(() => {
  const CALM = matchMedia('(prefers-reduced-motion:reduce)').matches;

  /* ── 1. clips ─────────────────────────────────────────────────────── */
  const clips = [...document.querySelectorAll('video[data-clip]')];
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(e => {
      const v = e.target;
      if (e.isIntersecting) {
        if (!v.src) { v.src = v.dataset.clip; }
        if (!CALM) { const p = v.play(); p && p.catch && p.catch(() => {}); }
      } else if (!v.paused) v.pause();
    }), {rootMargin: '200px 0px'});
    clips.forEach(v => io.observe(v));
  } else clips.forEach(v => { v.src = v.dataset.clip; });

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
      else if (piece && !piece.paused) t = piece.currentTime % m.L;
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
