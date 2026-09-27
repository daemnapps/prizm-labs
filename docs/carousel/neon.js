/* neon.js — the small lights of the Neon system v1 (THEME.md).

   1. Lit type: a heading marked .gj-flick flickers on once, the first time it
      comes into view (the glow itself is CSS).
   2. Press: every neon control sends a ripple out from where it was touched.
   3. Travelling through: where the browser can't drive the feed's depth from
      the scroll itself (animation-timeline), an observer does it instead.
   4. The portal (window.gjPortal): a lit disc that opens from a point to fill
      the screen, and shrinks back into one. feed.js uses it to open and close
      a part; transform and opacity only.
   5. The edit post's cover: the real timeline, drawn from m/edit.json.
   Everything here is off under reduced motion. No colours here. */
(() => {
  const root = document.documentElement;
  const CALM = matchMedia('(prefers-reduced-motion:reduce)');
  const IO = 'IntersectionObserver' in window;

  /* 1 · lit type */
  if (IO && !CALM.matches) {
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('is-lit'); io.unobserve(e.target); }
    }), {threshold: .3});
    document.querySelectorAll('.gj-flick').forEach(el => io.observe(el));
  }

  /* 2 · press: the ripple starts under the finger */
  const RIP = '.btn, .gj-xpbar-in button, .gj-snapnav button, .gj-play, .gj-nb';
  document.addEventListener('pointerdown', e => {
    if (CALM.matches || !e.target.closest) return;
    const b = e.target.closest(RIP);
    if (!b || b.disabled) return;
    const r = b.getBoundingClientRect();
    b.style.setProperty('--rx', (e.clientX - r.left) + 'px');
    b.style.setProperty('--ry', (e.clientY - r.top) + 'px');
    b.classList.remove('is-rip');
    requestAnimationFrame(() => b.classList.add('is-rip'));
  }, {passive: true});
  document.addEventListener('animationend', e => { if (e.animationName === 'gj-ripple') e.target.classList.remove('is-rip'); });

  /* 3 · travelling through, for browsers without scroll-driven animations */
  if (root.classList.contains('gj-app') && IO && !CALM.matches && !(window.CSS && CSS.supports('animation-timeline: view()'))) {
    root.classList.add('gj-depth-io');
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.remove('gj-far'); io.unobserve(e.target); }
    }), {threshold: .12});
    requestAnimationFrame(() => {
      const vh = innerHeight, posts = [...document.querySelectorAll('.gj-post')];
      const below = posts.map(p => p.getBoundingClientRect().top > vh);      // read everything first, then write
      posts.forEach((p, i) => { if (below[i]) { p.classList.add('gj-far'); io.observe(p); } });
    });
  }

  /* 4 · the portal */
  const disk = document.createElement('div');
  disk.className = 'gj-portal'; disk.setAttribute('aria-hidden', 'true');
  document.body.appendChild(disk);
  const D = 160;                                                  // the disc's drawn size; it is scaled, never resized
  const centre = el => { if (!el) return {x: innerWidth / 2, y: innerHeight / 2}; const r = el.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; };
  const fill = (x, y) => 2 * Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) / D * 1.1;
  const at = (x, y, s) => `translate(${x}px,${y}px) scale(${s})`;
  const IN = 'cubic-bezier(.7,0,.2,1)';
  // run fn when the animation ends, or after its time anyway (a background tab doesn't advance animations)
  const after = (a, ms, fn) => { let ran = false; const go = () => { if (!ran) { ran = true; fn(); } }; a.onfinish = go; setTimeout(go, ms + 150); };
  const done = () => { disk.getAnimations().forEach(a => a.cancel()); disk.style.willChange = ''; };
  const settle = els => els.forEach(el => {
    if (!el) return;
    el.classList.add('gj-portal-back');
    el.addEventListener('animationend', () => el.classList.remove('gj-portal-back'), {once: true});
  });
  window.gjPortal = {
    ok: () => !CALM.matches && typeof disk.animate === 'function',
    // from the element outwards; swap() runs once the disc covers the screen
    open(el, swap) {
      done();
      const {x, y} = centre(el), S = fill(x, y);
      disk.style.willChange = 'transform,opacity';
      after(disk.animate([{transform: at(x, y, .04), opacity: 1}, {transform: at(x, y, S), opacity: 1}], {duration: 420, easing: IN, fill: 'forwards'}), 420, () => {
        swap();
        after(disk.animate([{opacity: 1}, {opacity: 0}], {duration: 360, easing: 'ease-out', fill: 'forwards'}), 360, done);
      });
    },
    // cover the screen, swap(), then shrink into getEl() (what was tapped); `back` settles in behind
    close(swap, getEl, back) {
      done();
      const c = centre(null), S0 = fill(c.x, c.y);
      disk.style.willChange = 'transform,opacity';
      after(disk.animate([{transform: at(c.x, c.y, S0), opacity: 0}, {transform: at(c.x, c.y, S0), opacity: 1}], {duration: 200, easing: 'ease-out', fill: 'forwards'}), 200, () => {
        swap();
        const {x, y} = centre(getEl()), S = fill(x, y);
        settle(back || []);
        after(disk.animate([{transform: at(x, y, S), opacity: 1}, {transform: at(x, y, .05), opacity: .9, offset: .86}, {transform: at(x, y, .02), opacity: 0}],
          {duration: 480, easing: IN, fill: 'forwards'}), 480, done);
      });
    }
  };

  /* 5 · the edit post's cover: scenes, speed and zoom, outfits and personas, the 3D objects and the kicks,
     all on the piece's own clock — crisp at any size. A playhead sweeps it while it is the focus (CSS). */
  const cov = document.querySelector('.gj-ecover[data-src]');
  if (cov) {
    const NS = 'http://www.w3.org/2000/svg';
    const el = (tag, attrs, parent, text) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (text) n.textContent = text; parent.appendChild(n); return n; };
    const f = n => Math.round(n * 10) / 10;
    const draw = d => {
      const W = 300, H = 132, x = t => 4 + (t / d.total) * (W - 8);
      const svg = el('svg', {viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true', focusable: 'false'}, document.createDocumentFragment());
      d.sound.bars.forEach(t => el('line', {class: 'g', x1: f(x(t)), x2: f(x(t)), y1: 12, y2: H}, svg));
      const lane = (y, name) => el('text', {x: 4, y}, svg, name);
      // scenes
      lane(9, 'scenes');
      d.scenes.forEach(s => el('rect', {class: s.kind, x: f(x(s.a)), y: 13, width: f(Math.max(1.5, x(s.b) - x(s.a) - 1)), height: 16, rx: 2}, svg));
      // speed + zoom, sampled from the frame-by-frame curves
      lane(41, 'speed · zoom');
      el('rect', {class: 'l', x: 4, y: 45, width: W - 8, height: 36, rx: 3, opacity: .35}, svg);
      const C = d.curves, curve = (arr, cls) => {
        let lo = Infinity, hi = -Infinity; arr.forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; });
        const pts = []; for (let i = 0; i < arr.length; i += 4) pts.push(`${f(x(C.start + i / C.fps))},${f(79 - ((arr[i] - lo) / ((hi - lo) || 1)) * 32)}`);
        el('polyline', {class: 'c ' + cls, points: pts.join(' ')}, svg);
      };
      curve(C.speed, 'speed'); curve(C.zoom, 'zoom');
      // outfits and persona flashes
      lane(93, 'outfits · personas');
      d.outfits.forEach(o => el('rect', {class: 'fit', x: f(x(o.a)), y: 96, width: f(Math.max(1.5, x(o.b) - x(o.a) - 1)), height: 7, rx: 1.5}, svg));
      d.flashes.forEach(o => el('rect', {class: 'flash', x: f(x(o.a)), y: 94, width: 2.5, height: 11, rx: 1}, svg));
      // the 3D objects
      lane(113, '3D objects · kick');
      d.objects.forEach(o => el('rect', {class: 'obj', x: f(x(o.a)), y: 116, width: f(Math.max(1.5, x(o.b) - x(o.a) - 1)), height: 6, rx: 1.5}, svg));
      d.sound.kicks.forEach(t => el('line', {class: 'kick', x1: f(x(t)), x2: f(x(t)), y1: 125, y2: 131}, svg));
      cov.prepend(svg);
    };
    const load = () => fetch(cov.dataset.src).then(r => r.json()).then(draw).catch(e => console.warn('edit cover', e));
    if (IO) { const near = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { near.disconnect(); load(); } }, {rootMargin: '600px 0px'}); near.observe(cov); }
    else load();
  }
})();
