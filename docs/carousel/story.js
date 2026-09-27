/* story.js — DÆMN's story. The neon ring round the profile picture is the
   "has a story" cue, as on Instagram; tapping it opens the story full screen.

   Seven slides, all 9:16: five of the personas (a still each, 5 seconds) and
   the two memes (as long as the clip runs). Segments along the top fill as it
   plays. Tap the right side for the next slide, the left for the previous;
   hold to pause; swipe down or ✕ to close. Arrow keys, Space and Esc on a
   keyboard. Clips start muted with a sound button. Everything behind pauses
   while it is open (the 'gj-hold' event, page.js). Nothing loads until it
   opens, and then only the slide on screen and the next one.
   Deep link: /carousel/#story. No colours here. */
(() => {
  const btn = document.getElementById('story-open');
  if (!btn) return;
  const root = document.documentElement;
  const CALM = matchMedia('(prefers-reduced-motion:reduce)');
  const SLIDES = [
    {src: 'm/story-weeknd.jpg', kicker: 'The stage', cap: 'Me as The Weeknd'},
    {src: 'm/story-tiger.jpg', kicker: 'The golfer', cap: 'Me as Tiger Woods'},
    {src: 'm/story-obama.jpg', kicker: 'The president', cap: 'Me as Obama'},
    {src: 'm/story-serena.jpg', kicker: 'The champion', cap: 'Me as Serena Williams'},
    {src: 'm/story-elon.jpg', kicker: 'The anchor', cap: 'Me as Elon Musk'},
    {src: 'm/meme-neuron.mp4?v=1', poster: 'm/meme-neuron.jpg?v=1', video: true, kicker: 'Meme', cap: 'Neuron activation'},
    {src: 'm/meme-introvert.mp4?v=1', poster: 'm/meme-introvert.jpg?v=1', video: true, kicker: 'Meme', cap: 'Introvert with AI'}
  ];
  const N = SLIDES.length, STILL_MS = 5000;
  const TH = '๐๑๒๓๔๕๖๗๘๙', th = n => String(n).replace(/\d/g, d => TH[d]);   // Thai numerals for the count
  const hold = on => document.dispatchEvent(new CustomEvent('gj-hold', {detail: on}));
  // run fn when the animation ends, or after its time anyway (a background tab doesn't advance animations)
  const after = (a, ms, fn) => { let ran = false; const go = () => { if (!ran) { ran = true; fn(); } }; a.onfinish = go; setTimeout(go, ms + 150); };

  let box, frame, fills, segs, kicker, capB, capN, soundB, closeB;
  let open = false, cur = -1, muted = true, paused = false, ready = false, elapsed = 0, last = 0, raf = 0;
  const cache = new Map();

  function build() {
    if (box) return;
    box = document.createElement('div');
    box.className = 'gj-story'; box.hidden = true;
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', 'DÆMN’s story');
    const av = btn.querySelector('img').getAttribute('src');
    box.innerHTML =
      '<div class="gj-story-frame">' +
        '<div class="gj-story-top">' +
          '<div class="gj-story-seg">' + '<i><b></b></i>'.repeat(N) + '</div>' +
          '<div class="gj-story-who"><span class="gj-story-av"><img alt="" src="' + av + '"></span><b>DÆMN</b><span></span><span class="sp"></span>' +
            '<button class="gj-nb pill" type="button" hidden>Tap for sound</button>' +
            '<button class="gj-nb round" type="button" aria-label="Close the story">✕</button></div>' +
        '</div>' +
        '<div class="gj-story-cap" aria-live="polite"><span></span><b></b></div>' +
      '</div>';
    document.body.appendChild(box);
    frame = box.querySelector('.gj-story-frame');
    segs = [...box.querySelectorAll('.gj-story-seg i')]; fills = segs.map(s => s.firstChild);
    kicker = box.querySelector('.gj-story-who > span:not(.sp):not(.gj-story-av)');
    capN = box.querySelector('.gj-story-cap span'); capB = box.querySelector('.gj-story-cap b');
    [soundB, closeB] = box.querySelectorAll('.gj-story-who button');
    soundB.addEventListener('click', () => { muted = !muted; const m = cache.get(cur); if (m && m.tagName === 'VIDEO') { m.muted = muted; if (!muted) m.play().catch(() => {}); } paintSound(); });
    closeB.addEventListener('click', () => close());
    gestures();
  }

  // a slide's picture or clip, made once and kept only while it is on screen or next
  function media(i) {
    if (cache.has(i)) return cache.get(i);
    const s = SLIDES[i];
    let m;
    if (s.video) {
      m = document.createElement('video');
      m.muted = true; m.defaultMuted = true; m.playsInline = true; m.setAttribute('playsinline', ''); m.preload = 'auto';
      m.poster = s.poster; m.src = s.src;
      m.addEventListener('ended', () => { if (open && cache.get(cur) === m) go(cur + 1); });
      m.addEventListener('playing', () => { if (cache.get(cur) === m) box.classList.remove('is-loading'); });
    } else {
      m = new Image(); m.decoding = 'async'; m.alt = s.cap; m.src = s.src;
    }
    m.className = 'gj-story-media';
    cache.set(i, m);
    return m;
  }
  function prune(keep) {
    cache.forEach((m, i) => {
      if (keep.includes(i)) return;
      if (m.tagName === 'VIDEO') { m.pause(); m.removeAttribute('src'); m.load(); }
      m.remove(); cache.delete(i);
    });
  }
  const paintSound = () => { soundB.textContent = muted ? 'Tap for sound' : 'Sound on'; soundB.setAttribute('aria-pressed', String(!muted)); };

  function go(i) {
    if (!open) return;
    if (i >= N) { close(); return; }
    if (i < 0) i = 0;
    const was = cache.get(cur);
    if (was && was.tagName === 'VIDEO') was.pause();
    cur = i; elapsed = 0; ready = false; paused = false; box.classList.remove('is-held');
    const s = SLIDES[i], m = media(i);
    frame.querySelectorAll('.gj-story-media').forEach(x => { if (x !== m) x.remove(); });
    if (!m.isConnected) frame.prepend(m);
    segs.forEach((g, j) => { g.classList.toggle('done', j < i); g.classList.toggle('on', j === i); fills[j].style.transform = j < i ? 'scaleX(1)' : 'scaleX(0)'; });
    kicker.textContent = s.kicker;
    capB.textContent = s.cap;
    capN.textContent = `${i + 1} / ${N} · ${th(i + 1)} / ${th(N)}`;
    soundB.hidden = !s.video;
    box.classList.add('is-loading');
    if (s.video) {
      try { m.currentTime = 0; } catch (e) {}
      m.muted = muted; ready = true;
      const p = m.play();
      if (p && p.catch) p.catch(() => { if (!muted) { muted = true; m.muted = true; paintSound(); m.play().catch(() => {}); } });
      paintSound();
    } else {
      const ok = () => { if (cache.get(cur) === m) { ready = true; last = performance.now(); box.classList.remove('is-loading'); } };
      if (m.complete && m.naturalWidth) ok(); else { m.addEventListener('load', ok, {once: true}); m.addEventListener('error', ok, {once: true}); }
    }
    // the next slide, and only the next, loads now
    if (i + 1 < N) media(i + 1);
    prune([i, i + 1]);
    last = performance.now();
    if (!raf) raf = requestAnimationFrame(tick);
  }

  function tick(now) {
    raf = 0;
    if (!open) return;
    const s = SLIDES[cur], m = cache.get(cur);
    let p = 0;
    if (s.video) p = m.duration ? m.currentTime / m.duration : 0;
    else { if (ready && !paused) elapsed += now - last; p = elapsed / STILL_MS; }
    last = now;
    fills[cur].style.transform = `scaleX(${Math.min(1, p).toFixed(4)})`;
    if (!s.video && p >= 1) { go(cur + 1); return; }
    raf = requestAnimationFrame(tick);
  }

  function pause(on) {
    paused = on; box.classList.toggle('is-held', on);
    const m = cache.get(cur);
    if (m && m.tagName === 'VIDEO') { if (on) m.pause(); else m.play().catch(() => {}); }
  }

  // tap left / right, hold to pause, drag down to close
  function gestures() {
    let down = null, timer = 0, held = false, drag = false;
    frame.addEventListener('pointerdown', e => {
      if (e.target.closest('button') || e.button > 0) return;
      down = {x: e.clientX, y: e.clientY}; held = false; drag = false;
      clearTimeout(timer); timer = setTimeout(() => { held = true; pause(true); }, 220);
      try { frame.setPointerCapture(e.pointerId); } catch (err) {}
    });
    frame.addEventListener('pointermove', e => {
      if (!down) return;
      const dx = e.clientX - down.x, dy = e.clientY - down.y;
      if (!drag && dy > 12 && dy > Math.abs(dx)) { drag = true; clearTimeout(timer); if (!held) pause(true); }
      if (drag) { const d = Math.max(0, dy); frame.style.transform = `translateY(${d}px) scale(${1 - Math.min(d, 500) / 2500})`; box.style.opacity = String(1 - Math.min(d, 500) / 900); }
    });
    const up = e => {
      if (!down) return;
      clearTimeout(timer);
      const dy = e.clientY - down.y, r = frame.getBoundingClientRect(), x = down.x;
      down = null;
      if (drag) {
        if (dy > 110 && e.type === 'pointerup') { close(); return; }
        frame.animate([{transform: frame.style.transform}, {transform: 'none'}], {duration: 260, easing: 'cubic-bezier(.16,1,.3,1)'});
        frame.style.transform = ''; box.style.opacity = ''; pause(false); return;
      }
      if (held || e.type === 'pointercancel') { pause(false); return; }
      go(x - r.left < r.width / 3 ? cur - 1 : cur + 1);
    };
    frame.addEventListener('pointerup', up);
    frame.addEventListener('pointercancel', up);
    frame.addEventListener('contextmenu', e => e.preventDefault());
  }

  addEventListener('keydown', e => {
    if (!open || e.altKey || e.metaKey || e.ctrlKey) return;
    const k = e.key;
    if (k === 'Escape') close();
    else if (k === 'ArrowRight') go(cur + 1);
    else if (k === 'ArrowLeft') go(cur - 1);
    else if (k === ' ') pause(!paused);
    else return;
    e.preventDefault(); e.stopImmediatePropagation();
  }, true);

  const centre = () => { const r = btn.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; };

  function start(fromHistory) {
    build();
    if (open) return;
    open = true;
    if (!fromHistory && location.hash !== '#story') history.pushState({story: 1}, '', '#story');
    root.classList.add('gj-story-open');
    hold(true);
    box.hidden = false; box.style.opacity = ''; frame.style.transform = '';
    if (!CALM.matches && box.animate) {
      const {x, y} = centre();
      box.style.transformOrigin = `${x}px ${y}px`;
      box.animate([{opacity: 0, transform: 'scale(.14)'}, {opacity: 1, transform: 'none'}], {duration: 480, easing: 'cubic-bezier(.16,1,.3,1)'});
      const ring = document.createElement('div'); ring.className = 'gj-burst'; ring.setAttribute('aria-hidden', 'true');
      document.body.appendChild(ring);
      after(ring.animate([{transform: `translate(${x}px,${y}px) scale(1)`, opacity: 1}, {transform: `translate(${x}px,${y}px) scale(10)`, opacity: 0}],
        {duration: 700, easing: 'cubic-bezier(.16,1,.3,1)'}), 700, () => ring.remove());
    }
    cur = -1; go(0);
    closeB.focus({preventScroll: true});
  }

  function close(fromHistory) {
    if (!open) return;
    // the story has its own step in the history: Back closes it, and ✕ / Esc / swipe go back through it
    if (!fromHistory && history.state && history.state.story) { history.back(); return; }
    if (!fromHistory && location.hash === '#story') history.replaceState(null, '', location.pathname + location.search);
    open = false;
    cancelAnimationFrame(raf); raf = 0;
    const m = cache.get(cur); if (m && m.tagName === 'VIDEO') m.pause();
    const end = () => {
      box.hidden = true; box.style.opacity = ''; frame.style.transform = '';
      prune([]); cur = -1;
      root.classList.remove('gj-story-open');
      hold(false);
      btn.focus({preventScroll: true});
    };
    if (!CALM.matches && box.animate) {
      const {x, y} = centre();
      box.style.transformOrigin = `${x}px ${y}px`;
      after(box.animate([{opacity: box.style.opacity || 1, transform: frame.style.transform ? 'scale(.9)' : 'none'}, {opacity: 0, transform: 'scale(.14)'}],
        {duration: 320, easing: 'cubic-bezier(.7,0,.2,1)'}), 320, end);
    } else end();
  }

  btn.addEventListener('click', e => { e.preventDefault(); start(false); });
  addEventListener('popstate', () => {
    if (open && location.hash !== '#story') close(true);
    else if (!open && location.hash === '#story') start(true);
  });
  // a deep link opens it once the page's own scripts are ready (so everything behind knows to wait)
  if (location.hash === '#story') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => start(true), {once: true});
    else start(true);
  }
})();
