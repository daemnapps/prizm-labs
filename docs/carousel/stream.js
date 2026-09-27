/* stream.js — the piece streams at the quality the connection can carry, or at the quality the viewer picks.
   Auto: slow phones start on a light 360-wide picture within a second and step up to 1080 as the connection allows,
   the way Instagram and YouTube do (iPhones and Safari stream it natively; everything else uses hls.js, fetched only
   when needed). A picked quality plays a fixed file instead: "1080p · Max" is the untouched master (1080×1920,
   256k audio), for when the full experience is worth the wait. The pick is remembered on that device.
   build_web_video.py makes v/ and the q-*.mp4 files. Markup: <select data-quality-for="piece"> next to the video. */
(() => {
  const MASTER = 'v/master.m3u8?v=1';
  const FIXED = {'1080': 'q-1080.mp4?v=1', '720': 'carousel.mp4?v=14', '540': 'q-540.mp4?v=1', '360': 'q-360.mp4?v=1'};
  const vids = ['piece', 'edit-video'].map(id => document.getElementById(id)).filter(Boolean);
  if (!vids.length) return;
  const KEY = 'carousel-quality';
  let pick = 'auto';
  try { pick = localStorage.getItem(KEY) || 'auto'; } catch (e) {}
  const native = !!vids[0].canPlayType('application/vnd.apple.mpegurl');
  const mse = 'MediaSource' in window || 'ManagedMediaSource' in window;
  let lib = null;
  const load = () => lib || (lib = new Promise((ok, no) => {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.light.min.js'; s.async = true;
    s.onload = () => ok(window.Hls); s.onerror = no; document.head.appendChild(s);
  }));
  const state = new Map();   // video → {hls, fallback}

  // swap what a video plays, keeping its place and whether it was playing
  function apply(v, q) {
    const st = state.get(v) || {fallback: v.getAttribute('src')}; state.set(v, st);
    const t = v.currentTime, playing = !v.paused;
    const resume = () => { if (t) try { v.currentTime = t; } catch (e) {} if (playing) v.play().catch(() => {}); };
    if (st.hls) { st.hls.destroy(); st.hls = null; }
    if (q !== 'auto') { v.src = FIXED[q]; v.addEventListener('loadedmetadata', resume, {once: true}); if (playing) v.load(); return; }
    if (native) { v.src = MASTER; v.addEventListener('loadedmetadata', resume, {once: true}); return; }
    if (!mse) { v.src = st.fallback; return; }
    load().then(Hls => {
      if (!Hls || !Hls.isSupported()) return;
      const h = new Hls({capLevelToPlayerSize: true, startLevel: -1, maxBufferLength: 20}); st.hls = h;
      h.on(Hls.Events.ERROR, (e, d) => { if (d.fatal) { h.destroy(); st.hls = null; v.src = st.fallback; resume(); } });
      h.loadSource(MASTER); h.attachMedia(v);
      h.on(Hls.Events.MANIFEST_PARSED, resume);
    }).catch(() => {});
  }

  // Auto attaches as the video comes near (before anyone presses play); a fixed pick is just a file, already set
  vids.forEach(v => {
    if (pick !== 'auto') { v.src = FIXED[pick] || v.getAttribute('src'); return; }
    if (native) { v.src = MASTER; return; }
    if ('IntersectionObserver' in window) new IntersectionObserver((es, o) => { if (es.some(e => e.isIntersecting)) { o.disconnect(); apply(v, 'auto'); } }, {rootMargin: '600px 0px'}).observe(v);
    else apply(v, 'auto');
  });

  // the pickers: every one shows the current choice; changing one changes every video on the page
  const pickers = [...document.querySelectorAll('select[data-quality-for]')];
  pickers.forEach(sel => {
    sel.value = pick;
    sel.addEventListener('change', () => {
      pick = sel.value; try { localStorage.setItem(KEY, pick); } catch (e) {}
      pickers.forEach(s => { s.value = pick; });
      vids.forEach(v => apply(v, pick));
    });
  });
})();
