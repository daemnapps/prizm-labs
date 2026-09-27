/* feed.js — the page as a feed.

   The landing is a profile, the pinned piece, and one post per part of the
   making-of. Tapping a post opens that part full screen (its <section> gets
   .on, everything else on the landing hides), with a sticky bar: back, the
   title, previous / next, and story-style segments. Swipe sideways or use the
   arrow keys to move between parts; Esc or Back returns to the feed where you
   left it. Each part deep-links with a bare hash (#edit, #objects…).

   The parts are the same sections as before, untouched. They measure and load
   themselves when they come into view (page.js, carousel.js, objects-grid.js
   all watch with IntersectionObserver), so a hidden part costs nothing until
   it opens; a resize is sent on open so anything sized while hidden re-fits.

   One focus at a time: inside a part, every grid of clips, stills or 3D
   objects becomes a row you swipe one item at a time, with a count (3 / 12)
   and arrows. page.js plays only the one thing most in view. three.js and
   the 3D scripts load only when a 3D part (sheets, objects) opens.
   No colours here. */
(() => {
  const root = document.documentElement;
  // three.js and the light map are the heaviest things here: they load only when a 3D part opens
  let three = false;
  const load3d = () => {
    if (three) return; three = true;
    ['carousel.js?v=6', 'objects-grid.js?v=3'].forEach(src => { const s = document.createElement('script'); s.type = 'module'; s.src = src; document.body.appendChild(s); });
  };
  if (!root.classList.contains('gj-app')) { load3d(); return; }
  const posts = [...document.querySelectorAll('.gj-post[data-go]')]
    .map(a => ({id: a.dataset.go, title: a.dataset.title, n: a.querySelector('.gj-post-n').textContent, a, sec: document.getElementById(a.dataset.go)}))
    .filter(p => p.sec);
  if (!posts.length) { root.classList.remove('gj-app'); load3d(); return; }
  const ALIAS = {sound: 'sound-map', stems: 'sound-map', map: 'edit', carousel: 'objects', bible: 'sheets', making: 'how', bonus: 'memes', words: 'vocab'};
  const $ = id => document.getElementById(id);
  const back = $('xp-back'), prev = $('xp-prev'), next = $('xp-next'), seg = $('xp-seg'), num = $('xp-n'), ttl = $('xp-t'), up = $('xp-upnext');
  const TITLE = document.title;
  const THREE_D = new Set(['sheets', 'objects']);

  /* one item on screen at a time: every grid of clips, stills or 3D objects becomes a swipeable row
     with a count and arrows. Only the item in focus plays or turns (page.js decides the focus). */
  document.querySelectorAll('.gj-sec .gj-strip, .gj-sec .gj-cards, .gj-sec .gj-sheets, .gj-sec .gj-memes, .gj-sec .gj-objs').forEach(box => {
    let row = box;
    if (box.classList.contains('gj-objs')) {             // the 3D canvas stays put over a track that scrolls
      row = document.createElement('div'); row.className = 'gj-objs-track';
      row.append(...box.querySelectorAll(':scope > .gj-obj')); box.prepend(row);
      box.classList.add('gj-focus-mode');
      box.querySelectorAll('.gj-obj-view').forEach(v => v.setAttribute('data-focus', ''));
    }
    row.classList.add('gj-snap');
    const items = [...row.children], n = items.length;
    if (n < 2) return;
    const nav = document.createElement('div'); nav.className = 'gj-snapnav';
    nav.innerHTML = '<button type="button" aria-label="Previous">‹</button><span class="gj-count" aria-live="polite"><b>1</b> / ' + n + '</span><button type="button" aria-label="Next">›</button>';
    box.after(nav);
    const [pb, nb] = nav.querySelectorAll('button'), cnt = nav.querySelector('b');
    const pitch = () => row.clientWidth + (parseFloat(getComputedStyle(row).columnGap) || 0);
    const at = () => Math.max(0, Math.min(n - 1, Math.round(row.scrollLeft / (pitch() || 1))));
    const paint = () => { const i = at(); cnt.textContent = i + 1; pb.disabled = i === 0; nb.disabled = i === n - 1; };
    const to = i => row.scrollTo({left: Math.max(0, Math.min(n - 1, i)) * pitch(), behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth'});
    pb.addEventListener('click', () => to(at() - 1)); nb.addEventListener('click', () => to(at() + 1));
    let raf = 0; row.addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; paint(); }); }, {passive: true});
    row.addEventListener('keydown', e => { if (e.key === 'ArrowRight') { to(at() + 1); e.preventDefault(); } else if (e.key === 'ArrowLeft') { to(at() - 1); e.preventDefault(); } });
    row.tabIndex = 0; row.setAttribute('aria-label', 'Swipe sideways, one at a time');
    paint();
  });
  // post covers that are drawn, not filmed, move only while they are the focus
  document.querySelectorAll('.gj-post .gj-post-media').forEach(m => { if (!m.querySelector('video')) m.setAttribute('data-focus', ''); });
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

  // story segments, one per part
  const segs = posts.map((p, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.setAttribute('aria-label', `${p.title} (${i + 1} of ${posts.length})`);
    b.addEventListener('click', () => go(i));
    seg.appendChild(b); return b;
  });

  let cur = -1, feedY = 0;

  function show(i, dir) {
    if (i === cur) return;
    const p = posts[i];
    if (cur === -1) feedY = scrollY;
    if (THREE_D.has(p.id)) load3d();
    posts.forEach((q, j) => q.sec.classList.toggle('on', j === i));
    root.classList.add('xp-open');
    const s = p.sec;
    s.classList.remove('gj-in', 'gj-in-l', 'gj-in-r'); void s.offsetWidth;
    s.classList.add(dir > 0 ? 'gj-in-r' : dir < 0 ? 'gj-in-l' : 'gj-in');
    cur = i;
    num.textContent = p.n; ttl.textContent = p.title;
    prev.disabled = i === 0;
    next.setAttribute('aria-label', i === posts.length - 1 ? 'Back to the feed' : 'Next post');
    segs.forEach((b, j) => { b.classList.toggle('done', j < i); if (j === i) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
    // up next: the next part, or back to the start
    const nx = posts[(i + 1) % posts.length], media = nx.a.querySelector('.gj-post-media');
    up.href = '#' + nx.id; up.querySelector('b').textContent = nx.title;
    up.querySelector('.label').textContent = i === posts.length - 1 ? 'Back to the start' : 'Up next';
    const slot = up.querySelector('.gj-post-media'), cover = media.querySelector('img, .gj-mosaic, .gj-reel, .gj-bars, .gj-type');
    const still = media.querySelector('video');
    slot.replaceChildren();
    if (still) { const im = new Image(); im.src = still.getAttribute('poster') || still.dataset.poster; im.alt = ''; im.decoding = 'async'; slot.appendChild(im); }
    else if (cover) slot.appendChild(cover.cloneNode(true));
    document.title = `${p.title} — Carousel — DÆMN`;
    scrollTo(0, 0);
    const h = s.querySelector('h2') || s.querySelector('.eyebrow');
    if (h) { h.setAttribute('tabindex', '-1'); h.focus({preventScroll: true}); }
    // anything that measured itself while hidden (the carousel, the 3D tiles) re-fits now it has a size
    requestAnimationFrame(() => { dispatchEvent(new Event('resize')); dispatchEvent(new Event('scroll')); });
  }

  function feed() {
    if (cur === -1) return;
    const was = cur; cur = -1;
    posts.forEach(q => q.sec.classList.remove('on'));
    root.classList.remove('xp-open');
    document.title = TITLE;
    scrollTo(0, feedY);
    posts[was].a.focus({preventScroll: true});
    requestAnimationFrame(() => dispatchEvent(new Event('scroll')));
  }

  const find = hash => { const h = decodeURIComponent(hash.replace(/^#/, '')); const id = ALIAS[h] || h; return posts.findIndex(p => p.id === id); };
  function route() {
    const i = find(location.hash);
    if (i >= 0) show(i, cur >= 0 ? Math.sign(i - cur) : 0); else feed();
  }
  function open(i) { history.pushState({xp: 1}, '', '#' + posts[i].id); show(i, 0); }
  function close() {
    if (history.state && history.state.xp) history.back();
    else { history.replaceState(null, '', location.pathname + location.search); feed(); }
  }
  function go(i) {
    if (i < 0) return;
    if (i >= posts.length) { close(); return; }
    if (i === cur) return;
    history.replaceState(history.state, '', '#' + posts[i].id);   // moving between parts is one history step, so Back returns to the feed
    show(i, Math.sign(i - cur));
  }

  posts.forEach((p, i) => p.a.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault(); open(i);
  }));
  up.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault(); if (cur === posts.length - 1) close(); else go(cur + 1);
  });
  back.addEventListener('click', close);
  prev.addEventListener('click', () => go(cur - 1));
  next.addEventListener('click', () => go(cur + 1));
  addEventListener('popstate', route);
  addEventListener('hashchange', route);

  // keys: Esc back to the feed, arrows between parts (not while the carousel or a player has focus)
  const OWN = '.gj-carousel, input, textarea, select, video, audio, .gj-edit-scroll, .gj-map, .gj-snap';
  addEventListener('keydown', e => {
    if (cur < 0 || e.altKey || e.metaKey || e.ctrlKey) return;
    if (e.key === 'Escape') { close(); return; }
    if (e.target.closest && e.target.closest(OWN)) return;
    if (e.key === 'ArrowRight') go(cur + 1); else if (e.key === 'ArrowLeft') go(cur - 1);
  });

  // swipe sideways between parts, except on things that are dragged sideways themselves
  const NOSWIPE = '.gj-snap, .gj-map, .gj-edit, .gj-carousel, .gj-objs, video[controls], audio, .gj-xp-seg';
  let sx = 0, sy = 0, st = 0, ok = false;
  addEventListener('touchstart', e => {
    ok = cur >= 0 && e.touches.length === 1 && !(e.target.closest && e.target.closest(NOSWIPE));
    if (!ok) return; const t = e.touches[0]; sx = t.clientX; sy = t.clientY; st = Date.now();
  }, {passive: true});
  addEventListener('touchend', e => {
    if (!ok || cur < 0) return; ok = false;
    const t = e.changedTouches[0], dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 2 && Date.now() - st < 800) go(cur + (dx < 0 ? 1 : -1));
  }, {passive: true});

  route();
  // a deep link: the browser jumps to the anchor once the page loads; put the part back at its top
  addEventListener('load', () => { if (cur >= 0) scrollTo(0, 0); });
})();
