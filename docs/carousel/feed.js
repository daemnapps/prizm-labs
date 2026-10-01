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

   The portal (neon.js, window.gjPortal): opening a post, a lit disc opens
   from the tapped cover and the part settles in behind it; closing reverses
   it into the post you came from. Off under reduced motion.
   A video inside a part deep-links as #part.n (the n-th video in it, from 0):
   the part opens scrolled to that video. The immersive viewer (reels.js) uses
   this to land you where you stopped watching (window.gjFeed).
   No colours here. */
(() => {
  const root = document.documentElement;
  // three.js and the light map are the heaviest things here: they load only when a 3D part opens
  let three = false;
  const load3d = () => {
    if (three) return; three = true;
    ['carousel.js?v=7', 'objects-grid.js?v=4'].forEach(src => { const s = document.createElement('script'); s.type = 'module'; s.src = src; document.body.appendChild(s); });
  };
  if (!root.classList.contains('gj-app')) { load3d(); return; }
  const posts = [...document.querySelectorAll('.gj-post[data-go]')]
    .map(a => { const n = a.querySelector('.gj-post-n'), th = n.querySelector('.gj-th');
      return {id: a.dataset.go, title: a.dataset.title, n: n.firstChild.textContent.trim(), th: th ? th.textContent : '', a, sec: document.getElementById(a.dataset.go)}; })
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
    // the item in view is the one whose centre is nearest the row's centre (works with a peek of the next card)
    const at = () => { const c = row.scrollLeft + row.clientWidth / 2; let best = 0, bd = Infinity;
      items.forEach((it, i) => { const d = Math.abs(it.offsetLeft + it.offsetWidth / 2 - c); if (d < bd) { bd = d; best = i; } }); return best; };
    const paint = () => { const i = at(); cnt.textContent = i + 1; pb.disabled = i === 0; nb.disabled = i === n - 1; };
    const to = i => { const it = items[Math.max(0, Math.min(n - 1, i))];
      row.scrollTo({left: it.offsetLeft + it.offsetWidth / 2 - row.clientWidth / 2, behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth'}); };
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

  // the n-th video of a part, in view: its swipe row turned to it, the page scrolled so it sits in the middle
  function toItem(sec, k) {
    const v = sec.querySelectorAll('video')[k];
    if (!v) return;
    const slide = v.closest('.gj-snap > *');
    if (slide) { const row = slide.parentElement; row.scrollLeft = slide.offsetLeft + slide.offsetWidth / 2 - row.clientWidth / 2; }
    v.scrollIntoView({block: 'center'});
  }

  function show(i, dir, how) {
    if (i === cur) return;
    const p = posts[i];
    if (cur === -1) feedY = scrollY;
    if (THREE_D.has(p.id)) load3d();
    posts.forEach((q, j) => q.sec.classList.toggle('on', j === i));
    root.classList.add('xp-open');
    const s = p.sec;
    s.classList.remove('gj-in', 'gj-in-l', 'gj-in-r', 'gj-portal-in'); void s.offsetWidth;
    s.classList.add(how === 'portal' ? 'gj-portal-in' : dir > 0 ? 'gj-in-r' : dir < 0 ? 'gj-in-l' : 'gj-in');
    cur = i;
    num.textContent = p.n;
    if (p.th) { const t = document.createElement('span'); t.className = 'gj-th'; t.lang = 'th'; t.textContent = p.th; num.appendChild(t); }
    ttl.textContent = p.title;
    prev.disabled = i === 0;
    next.setAttribute('aria-label', i === posts.length - 1 ? 'Back to the feed' : 'Next post');
    segs.forEach((b, j) => { b.classList.toggle('done', j < i); if (j === i) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
    // up next: the next part, or back to the start
    const nx = posts[(i + 1) % posts.length], media = nx.a.querySelector('.gj-post-media');
    up.href = '#' + nx.id; up.querySelector('b').textContent = nx.title;
    up.querySelector('.label').textContent = i === posts.length - 1 ? 'Back to the start' : 'Up next';
    const slot = up.querySelector('.gj-post-media'), cover = media.querySelector('.gj-ecover, .gj-mosaic, .gj-reel, .gj-bars, .gj-type, img');
    const still = media.querySelector('video');
    slot.replaceChildren();
    if (still) { const im = new Image(); im.src = still.getAttribute('poster') || still.dataset.poster; im.alt = ''; im.decoding = 'async'; slot.appendChild(im); }
    else if (cover) slot.appendChild(cover.cloneNode(true));
    document.title = `${p.title} — Carousel — Prizm Labs`;
    scrollTo(0, 0);
    const h = s.querySelector('h2') || s.querySelector('.eyebrow');
    if (h) { h.setAttribute('tabindex', '-1'); h.focus({preventScroll: true}); }
    // anything that measured itself while hidden (the carousel, the 3D tiles) re-fits now it has a size
    requestAnimationFrame(() => { dispatchEvent(new Event('resize')); dispatchEvent(new Event('scroll')); });
  }

  function feed(y) {
    if (cur === -1) { if (y !== undefined) scrollTo(0, y); return; }
    const was = cur; cur = -1;
    const swap = () => {
      posts.forEach(q => q.sec.classList.remove('on'));
      root.classList.remove('xp-open');
      document.title = TITLE;
      scrollTo(0, y !== undefined ? y : feedY);
      posts[was].a.focus({preventScroll: true});
      requestAnimationFrame(() => dispatchEvent(new Event('scroll')));
    };
    const P = window.gjPortal;
    if (P && P.ok() && y === undefined) P.close(swap, () => posts[was].a.querySelector('.gj-post-media'),
      ['.gj-profile', '.gj-hero', '.gj-feed'].map(q => document.querySelector(q)));
    else swap();
  }

  // '#edit' → the edit; '#vocab.12' → the vocabulary, at its 13th video
  const find = hash => { const [h0, k] = decodeURIComponent(hash.replace(/^#/, '')).split('.'); const id = ALIAS[h0] || h0;
    const i = posts.findIndex(p => p.id === id); return {i, k: k === undefined || k === '' ? -1 : parseInt(k, 10)}; };
  function route() {
    const {i, k} = find(location.hash);
    if (i >= 0) { show(i, cur >= 0 ? Math.sign(i - cur) : 0); if (k >= 0) requestAnimationFrame(() => toItem(posts[i].sec, k)); }
    else feed();
  }
  function open(i) {
    history.pushState({xp: 1}, '', '#' + posts[i].id);
    const P = window.gjPortal;
    if (P && P.ok()) P.open(posts[i].a.querySelector('.gj-post-media'), () => show(i, 0, 'portal'));
    else show(i, 0);
  }
  /* for the immersive viewer: land on part `id` at its k-th video (push: add a history step from the feed),
     or back on the feed at scroll y */
  window.gjFeed = {
    part: () => (cur >= 0 ? posts[cur].id : null),
    land(id, k, push) {
      const i = posts.findIndex(p => p.id === id);
      if (i < 0) return;
      const url = '#' + id + (k >= 0 ? '.' + k : '');
      if (push) history.pushState({xp: 1}, '', url); else history.replaceState(history.state, '', url);
      if (cur !== i) show(i, 0);
      requestAnimationFrame(() => toItem(posts[i].sec, k >= 0 ? k : 0));
    },
    feed(y) { feed(y); }
  };
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
  const NOSWIPE = '.gj-snap, .gj-map, .gj-edit, .gj-carousel, .gj-objs, video[controls], audio, .gj-xp-seg, .gj-story, .gj-reels';
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
