/* stream.js — the piece streams at the quality the connection can carry.
   Phones on a slow connection start on a light 360-wide picture within a second and step up to 1080 as it allows,
   the way Instagram and YouTube do. iPhones and Safari stream it natively; everything else uses hls.js, fetched only
   when needed. If neither works, the plain carousel.mp4 already in the src plays. build_web_video.py makes v/. */
(() => {
  const MASTER = 'v/master.m3u8?v=1';
  const vids = ['piece', 'edit-video'].map(id => document.getElementById(id)).filter(Boolean);
  if (!vids.length) return;
  const native = vids[0].canPlayType('application/vnd.apple.mpegurl');
  if (native) { vids.forEach(v => { v.src = MASTER; }); return; }
  if (!('MediaSource' in window || 'ManagedMediaSource' in window)) return;   // keep the mp4
  let lib = null;
  const load = () => lib || (lib = new Promise((ok, no) => {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.light.min.js'; s.async = true;
    s.onload = () => ok(window.Hls); s.onerror = no; document.head.appendChild(s);
  }));
  vids.forEach(v => {
    const fallback = v.getAttribute('src');
    let attached = false;
    const attach = () => {
      if (attached) return; attached = true;
      load().then(Hls => {
        if (!Hls || !Hls.isSupported()) return;
        const wasPlaying = !v.paused, t = v.currentTime;
        const h = new Hls({capLevelToPlayerSize: true, startLevel: -1, maxBufferLength: 20});
        h.on(Hls.Events.ERROR, (e, d) => { if (d.fatal) { h.destroy(); v.src = fallback; if (wasPlaying) v.play().catch(() => {}); } });
        h.loadSource(MASTER); h.attachMedia(v);
        h.on(Hls.Events.MANIFEST_PARSED, () => { if (t) v.currentTime = t; if (wasPlaying || v.dataset.want) v.play().catch(() => {}); });
      }).catch(() => {});
    };
    // stream as soon as the page wants this video: attach on the first play request, before the mp4 downloads
    v.addEventListener('play', () => { if (!attached) { v.dataset.want = '1'; v.pause(); attach(); } }, {once: true});
    if ('IntersectionObserver' in window) new IntersectionObserver((es, o) => { if (es.some(e => e.isIntersecting)) { o.disconnect(); attach(); } }, {rootMargin: '600px 0px'}).observe(v);
  });
})();
