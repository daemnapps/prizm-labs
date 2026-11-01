/* reels.js — every video gets the piece's treatment, and one immersive viewer plays them all.

   1. Play on every video. In the feed and in every part, a video is a muted,
      looping preview (page.js still plays only the one in focus) with a Play
      pill over it. The piece's own Play and "Play with sound" work the same way.
   2. The immersive viewer. Play opens a full-screen overlay of our own (not the
      phone's player, which can't swipe to the next video) that plays that
      video from 0:00 with sound. Swipe up / down, scroll, or use the arrow
      keys for the next or previous video: the piece first, then every part's
      videos in order, one continuous feed. Tap to pause. ✕, Esc, Back, or a
      pull down at the very top closes it, and you land on the part and the
      video you last watched (#part.n, via feed.js), the history intact.
      Only the video on screen plays and only the next one is fetched ahead.
      On Android and desktop it also asks for true full screen.
   No colours here. */
(() => {
  const root = document.documentElement;
  const CALM = matchMedia('(prefers-reduced-motion:reduce)');
  const IOS = /iP(hone|ad|od)/.test(navigator.platform) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const hold = on => document.dispatchEvent(new CustomEvent('gj-hold', {detail: on}));
  const piece = document.getElementById('piece');
  const clean = t => (t || '').replace(/,? animated$/i, '').replace(/\s+/g, ' ').trim();

  /* the list, in the order of the page: the piece, then each part's videos */
  const items = [];
  if (piece) items.push({el: piece, stream: true, poster: piece.getAttribute('poster'), cap: 'Carousel', part: null, label: 'The piece'});
  document.querySelectorAll('.gj-post[data-go]').forEach(a => {
    const sec = document.getElementById(a.dataset.go);
    if (!sec) return;
    const n = a.querySelector('.gj-post-n'), num = n ? n.firstChild.textContent.trim() : '';
    sec.querySelectorAll('video').forEach((v, k) => {
      const fig = v.closest('figure'), fc = fig && fig.querySelector('figcaption');
      items.push({el: v, stream: v.id === 'edit-video', src: v.dataset.clip || v.getAttribute('src'), poster: v.dataset.poster || v.getAttribute('poster'),
        cap: clean(v.getAttribute('aria-label') || (fc && fc.textContent)) || a.dataset.title, part: a.dataset.go, k, label: a.dataset.title, num});
    });
  });
  if (!items.length) return;
  const bySrc = src => items.findIndex(it => it.src && src && it.src.split('?')[0] === src.split('?')[0]);

  /* 1 · a Play pill on every video */
  const pill = (tag, label) => {
    const b = document.createElement(tag);
    b.className = 'gj-play sm';
    if (tag === 'button') b.type = 'button'; else { b.setAttribute('role', 'button'); b.tabIndex = 0; }
    b.setAttribute('aria-label', label);
    b.innerHTML = '<span class="gj-play-icon" aria-hidden="true"></span><span>Play</span>';
    return b;
  };
  items.forEach((it, i) => {
    if (it.el === piece) return;
    const v = it.el;
    v.removeAttribute('controls');                          // the viewer has the sound; the preview stays clean
    if (it.stream) v.loop = true;
    const wrap = document.createElement('span'); wrap.className = 'gj-vwrap';
    v.before(wrap); wrap.appendChild(v);
    const b = pill('button', `Play ${it.cap} from the start, with sound`);
    b.addEventListener('click', e => { e.preventDefault(); openAt(i, b); });
    wrap.appendChild(b);
  });
  // the feed's video covers: Play opens that clip in the viewer; the rest of the cover still opens the part
  document.querySelectorAll('.gj-post .gj-post-media > video').forEach(v => {
    const i = bySrc(v.dataset.clip);
    if (i < 0) return;
    const b = pill('span', `Play ${items[i].cap} from the start, with sound`);
    const fire = e => { e.preventDefault(); e.stopPropagation(); openAt(i, b); };
    b.addEventListener('click', fire);
    b.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') fire(e); });
    v.parentElement.appendChild(b);
  });
  // the piece: Play and "Play with sound" open the viewer at the piece
  ['play', 'sound'].forEach(id => { const b = document.getElementById(id); if (b) b.addEventListener('click', e => { e.preventDefault(); openAt(0, b); }); });
  const snd = document.getElementById('sound'); if (snd) snd.textContent = 'Play with sound';

  /* 2 · the viewer */
  let box, track, slides, player, pre, partEl, capB, capN, bar, soundB, closeB;
  let open = false, cur = -1, last = 0, muted = false, raf = 0, hinted = false;

  function build() {
    if (box) return;
    box = document.createElement('div');
    box.className = 'gj-reels'; box.hidden = true;
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', 'Videos, one at a time');
    box.innerHTML =
      '<div class="gj-reels-track"></div>' +
      '<div class="gj-reels-top"><span class="gj-reels-part"></span><span class="sp"></span>' +
        '<button class="gj-nb pill" type="button">Sound on</button>' +
        '<button class="gj-nb round" type="button" aria-label="Close">✕</button></div>' +
      '<div class="gj-reels-tip" aria-hidden="true"><i></i></div>' +
      '<div class="gj-reels-cap" aria-live="polite"><b></b><span></span><div class="gj-reels-bar"><b></b></div></div>';
    document.body.appendChild(box);
    track = box.querySelector('.gj-reels-track');
    slides = items.map((it, i) => { const s = document.createElement('div'); s.className = 'gj-reel-slide'; s.dataset.i = i; track.appendChild(s); return s; });
    partEl = box.querySelector('.gj-reels-part');
    capB = box.querySelector('.gj-reels-cap > b'); capN = box.querySelector('.gj-reels-cap > span'); bar = box.querySelector('.gj-reels-bar b');
    [soundB, closeB] = box.querySelectorAll('.gj-reels-top button');
    player = document.createElement('video');
    player.playsInline = true; player.setAttribute('playsinline', ''); player.loop = true; player.preload = 'auto';
    player.addEventListener('pause', () => box.classList.toggle('is-paused', open && !player.ended));
    player.addEventListener('play', () => box.classList.remove('is-paused'));
    pre = document.createElement('video'); pre.muted = true; pre.preload = 'auto'; pre.playsInline = true;   // fetches the next clip ahead, never shown
    soundB.addEventListener('click', () => { muted = !muted; player.muted = muted; if (!muted && player.paused) player.play().catch(() => {}); paintSound(); });
    closeB.addEventListener('click', () => close());
    let raf2 = 0;
    track.addEventListener('scroll', () => { if (!raf2) raf2 = requestAnimationFrame(() => { raf2 = 0; const i = Math.round(track.scrollTop / (track.clientHeight || 1)); if (i !== cur) show(i); }); }, {passive: true});
    // tap to pause / play
    let tx = 0, ty = 0, tt = 0;
    track.addEventListener('pointerdown', e => { tx = e.clientX; ty = e.clientY; tt = Date.now(); });
    track.addEventListener('pointerup', e => {
      if (Math.hypot(e.clientX - tx, e.clientY - ty) > 10 || Date.now() - tt > 500) return;
      if (player.paused) player.play().catch(() => {}); else player.pause();
    });
    // a pull down at the very top closes it
    let sy = null;
    track.addEventListener('touchstart', e => { sy = track.scrollTop <= 0 ? e.touches[0].clientY : null; }, {passive: true});
    track.addEventListener('touchmove', e => { if (sy !== null && e.touches[0].clientY - sy > 110) { sy = null; close(); } }, {passive: true});
  }

  const paintSound = () => { soundB.textContent = muted ? 'Tap for sound' : 'Sound on'; soundB.setAttribute('aria-pressed', String(!muted)); };
  const still = i => { const s = slides[i]; if (!s || s.firstChild || !items[i].poster) return; const im = new Image(); im.decoding = 'async'; im.alt = ''; im.src = items[i].poster; s.appendChild(im); };

  function show(i) {
    if (!open || i < 0 || i >= items.length || i === cur) return;
    cur = i; last = i;
    const it = items[i], s = slides[i];
    [i - 1, i, i + 1, i + 2].forEach(still);
    player.pause();
    s.appendChild(player);
    if (window.gjStream) window.gjStream.detach(player);
    player.removeAttribute('src');
    player.poster = it.poster || '';
    if (it.stream && window.gjStream) window.gjStream.attach(player);
    else player.src = it.src || (it.el.currentSrc || it.el.getAttribute('src'));
    player.muted = muted;
    const p = player.play();
    if (p && p.catch) p.catch(() => { if (!muted) { muted = true; player.muted = true; paintSound(); player.play().catch(() => {}); } });
    paintSound();
    partEl.innerHTML = '';
    if (it.part) { const b = document.createElement('b'); b.textContent = it.num; partEl.append(b, it.label); } else partEl.textContent = 'Prizm Labs · the piece';
    capB.textContent = it.cap;
    capN.textContent = `${i + 1} / ${items.length}` + (i + 1 < items.length ? ' · swipe up for the next' : ' · the end');
    // fetch the next clip ahead (the piece streams, so it needs nothing)
    const nx = items[i + 1];
    if (nx && !nx.stream) { pre.src = nx.src; pre.load(); } else pre.removeAttribute('src');
  }

  function tick() {
    raf = 0;
    if (!open) return;
    const d = player.duration;
    bar.style.transform = `scaleX(${d ? Math.min(1, player.currentTime / d).toFixed(4) : 0})`;
    raf = requestAnimationFrame(tick);
  }

  function step(d) {
    const i = Math.max(0, Math.min(items.length - 1, cur + d));
    track.scrollTo({top: i * track.clientHeight, behavior: CALM.matches ? 'auto' : 'smooth'});
  }

  addEventListener('keydown', e => {
    if (!open || e.altKey || e.metaKey || e.ctrlKey) return;
    const k = e.key;
    if (k === 'Escape') close();
    else if (k === 'ArrowDown' || k === 'PageDown' || k === 'j') step(1);
    else if (k === 'ArrowUp' || k === 'PageUp' || k === 'k') step(-1);
    else if (k === ' ') { if (player.paused) player.play().catch(() => {}); else player.pause(); }
    else if (k === 'm') soundB.click();
    else return;
    e.preventDefault(); e.stopImmediatePropagation();
  }, true);

  function openAt(i, from) {
    build();
    if (open) return;
    open = true; cur = -1; muted = false;
    history.pushState({reel: 1}, '', '#watch');
    root.classList.add('gj-reels-open');
    hold(true);
    box.hidden = false;
    track.scrollTop = i * track.clientHeight;
    show(i);                                                   // inside the tap, so the phone lets it play with sound
    if (!IOS && box.requestFullscreen) box.requestFullscreen({navigationUI: 'hide'}).catch(() => {});
    if (!CALM.matches && box.animate && from) {
      const r = from.getBoundingClientRect();
      box.style.transformOrigin = `${r.left + r.width / 2}px ${r.top + r.height / 2}px`;
      box.animate([{opacity: 0, transform: 'scale(.9)'}, {opacity: 1, transform: 'none'}], {duration: 380, easing: 'cubic-bezier(.16,1,.3,1)'});
    }
    if (!hinted && items.length > 1) {
      hinted = true;
      const h = document.createElement('p'); h.className = 'gj-reels-hint'; h.textContent = 'Swipe up · next video';
      box.appendChild(h); h.addEventListener('animationend', () => h.remove());
      if (CALM.matches) setTimeout(() => h.remove(), 3000);
    }
    if (!raf) raf = requestAnimationFrame(tick);
    closeB.focus({preventScroll: true});
  }

  function close(fromHistory) {
    if (!open) return;
    if (!fromHistory && history.state && history.state.reel) { history.back(); return; }   // Back and ✕ take the same road
    open = false;
    cancelAnimationFrame(raf); raf = 0;
    player.pause();
    if (window.gjStream) window.gjStream.detach(player);
    player.removeAttribute('src'); player.load(); pre.removeAttribute('src'); pre.load();
    if (document.fullscreenElement === box && document.exitFullscreen) document.exitFullscreen().catch(() => {});
    box.hidden = true;
    root.classList.remove('gj-reels-open');
    // land where they stopped watching: the part and its video, or the piece on the feed
    const it = items[last], F = window.gjFeed;
    if (it.part && F) F.land(it.part, it.k, !F.part());   // from the feed: a new step, so Back still returns to the feed
    else {
      if (location.hash === '#watch') history.replaceState(null, '', location.pathname + location.search);
      if (F && F.part()) { history.replaceState(null, '', location.pathname + location.search); F.feed(0); }
      if (piece) piece.scrollIntoView({block: 'center'});
    }
    hold(false);
  }

  addEventListener('popstate', () => { if (open && location.hash !== '#watch') close(true); });
  if (location.hash === '#watch') history.replaceState(null, '', location.pathname + location.search);
  window.gjReels = {open: openAt};
})();
