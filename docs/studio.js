/* studio.js — the motion and the secrets, shared by every page on daemn.co.

   Everything here is optional: a page with no script is complete and still.
   Motion is small and slow, and none of it runs for anyone whose device asks
   for reduced motion. The easter eggs are listed at the bottom so nobody has
   to reverse-engineer them to change one.
*/
(() => {
  const CALM = matchMedia('(prefers-reduced-motion:reduce)').matches;
  const FINE = matchMedia('(hover:hover) and (pointer:fine)').matches;
  const root = document.documentElement;

  /* ── a note from the machine ─────────────────────────────────────── */
  let toastEl, toastT;
  const toast = (msg, ms = 2600) => {
    if (!toastEl) { toastEl = document.createElement('div'); toastEl.className = 'toast'; toastEl.setAttribute('role', 'status'); document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(() => toastEl.classList.remove('on'), ms);
  };
  window.studioToast = toast;

  /* ── reveals: things arrive as you reach them ────────────────────── */
  if (!CALM && 'IntersectionObserver' in window) {
    root.classList.add('moving');
    const pick = '.sec > *, .trio > div, .duo > *, .close > *, .card, .door, ol.steps li, .grid > *, .kit-card, .v, .acct, ' +
                 '.td .sec, .td .metric, .td .finding, .td .lp, .td .swipe, .td .panel, .td .wall-block';
    const seen = new Set();
    document.querySelectorAll(pick).forEach(el => {
      if (seen.has(el) || el.closest('[data-rv],.story') || el.getBoundingClientRect().top < innerHeight * .9) return;
      seen.add(el); el.setAttribute('data-rv', '');
      const sib = el.parentElement ? [...el.parentElement.children].filter(c => seen.has(c)) : [];
      el.style.setProperty('--i', Math.min(sib.indexOf(el), 6));
    });
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }), {rootMargin: '0px 0px -8% 0px'});
    document.querySelectorAll('[data-rv]').forEach(el => io.observe(el));
    // the chrome objects breathe
    document.querySelectorAll('img[src*="media/objects/"]').forEach((img, i) => {
      img.setAttribute('data-float', ''); img.style.setProperty('--i', i);
    });
  }

  /* ── the glint: a faint spectrum that follows a real pointer ─────── */
  if (!CALM && FINE) {
    const g = document.createElement('div'); g.className = 'glint'; document.body.appendChild(g);
    let x = innerWidth / 2, y = innerHeight / 3, tx = x, ty = y, raf = 0;
    const step = () => { x += (tx - x) * .12; y += (ty - y) * .12;
      g.style.transform = `translate3d(${x}px,${y}px,0)`;
      raf = Math.abs(tx - x) + Math.abs(ty - y) > .5 ? requestAnimationFrame(step) : 0; };
    addEventListener('pointermove', e => { tx = e.clientX; ty = e.clientY; g.classList.add('on'); if (!raf) raf = requestAnimationFrame(step); }, {passive: true});
    document.addEventListener('pointerleave', () => g.classList.remove('on'));
  }


  /* ── icons: <i class="ib" data-i="name"></i> anywhere ───────────────
     One set, one stroke, drawn here so no page carries its own. */
  const I = {
    search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    scissors:'<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    video:'<rect x="2" y="6" width="14" height="12" rx="2"/><path d="m16 10 6-3v10l-6-3"/>',
    image:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
    mail:'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/>',
    page:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
    pen:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    calendar:'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    film:'<rect x="2" y="2" width="20" height="20" rx="2"/><path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/>',
    send:'<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    folder:'<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9L9.6 3.9A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    link:'<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    code:'<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
    sparkles:'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17v4M17 19h4"/>',
    plug:'<path d="M12 22v-5M9 8V2M15 8V2M18 8v5a6 6 0 0 1-12 0V8z"/>',
    chat:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    clipboard:'<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    sync:'<path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5M3 21v-5h5"/>',
    check:'<path d="m9 11 3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    eye:'<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    layers:'<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
    shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    alert:'<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    music:'<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    play:'<path d="m7 4 13 8-13 8z"/>',
    arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
    bookmark:'<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    zap:'<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    download:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
    loop:'<path d="M17 2l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14M7 22l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
    map:'<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/>',
    book:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15zM6.5 22H20v-5"/>',
    cpu:'<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4"/>',
  };
  const icon = n => `<svg viewBox="0 0 24 24" aria-hidden="true">${I[n] || I.sparkles}</svg>`;
  document.querySelectorAll('[data-i]').forEach(el => { if(!el.firstChild) el.innerHTML = icon(el.dataset.i); });
  window.studioIcon = icon;

  /* ── headlines that rise a word at a time ────────────────────────── */
  if (!CALM && 'IntersectionObserver' in window) {
    document.querySelectorAll('.rise').forEach(h => {
      let wi = 0;
      const walk = node => [...node.childNodes].forEach(n => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
            const w = document.createElement('span'); w.className = 'w'; w.style.setProperty('--wi', wi++);
            const i = document.createElement('span'); i.textContent = part; w.appendChild(i); frag.appendChild(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1 && n.tagName !== 'BR') walk(n);
      });
      walk(h);
      const o = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { h.classList.add('in'); o.disconnect(); } }), {threshold:.2});
      o.observe(h);
    });
  }

  /* ── big numbers count up as they arrive ─────────────────────────── */
  document.querySelectorAll('.stat .v[data-to]').forEach(el => {
    const to = +el.dataset.to, pre = el.dataset.pre || '', suf = el.dataset.suf || '';
    const fmt = n => pre + Math.round(n).toLocaleString('en-US') + suf;
    if (CALM || !('IntersectionObserver' in window)) { el.textContent = fmt(to); return; }
    el.textContent = fmt(0);
    const o = new IntersectionObserver(es => { if (!es[0].isIntersecting) return; o.disconnect();
      const t0 = performance.now(), d = 1600;
      (function f(t){ const k = Math.min(1, (t - t0) / d); el.textContent = fmt(to * (1 - Math.pow(1 - k, 4))); if (k < 1) requestAnimationFrame(f); })(t0);
    }, {threshold:.5});
    o.observe(el);
  });

  /* ── the pinned story: which step is on, from how far you have scrolled ── */
  document.querySelectorAll('.story').forEach(st => {
    const steps = [...st.querySelectorAll('.story-step')], obj = st.querySelector('.obj'), dots = st.querySelector('.story-dots');
    if (dots) dots.innerHTML = steps.map(() => '<i></i>').join('');
    let cur = -1;
    const set = i => {
      if (i === cur) return; cur = i;
      steps.forEach((s, k) => s.classList.toggle('on', k === i));
      dots && [...dots.children].forEach((d, k) => d.classList.toggle('on', k === i));
      const s = steps[i];
      if (obj && s.dataset.stepObj) obj.dataset.obj = s.dataset.stepObj;
      if (s.dataset.hue) st.style.setProperty('--hue', s.dataset.hue);
    };
    const onScroll = () => {
      const r = st.getBoundingClientRect(), span = r.height - innerHeight;
      const p = Math.min(.999, Math.max(0, -r.top / Math.max(1, span)));
      set(Math.floor(p * steps.length));
    };
    addEventListener('scroll', onScroll, {passive:true}); addEventListener('resize', onScroll); onScroll();
  });

  /* ── the 3D objects: load the engine only where a page has one ───── */
  if (document.querySelector('[data-obj]')) {
    if (!document.querySelector('script[type="importmap"]')) {
      const m = document.createElement('script'); m.type = 'importmap';
      m.textContent = JSON.stringify({imports:{three:'https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js',
        'three/addons/':'https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/'}});
      document.head.appendChild(m);
    }
    const s = document.createElement('script'); s.type = 'module'; s.src = '/objects3d.js?v=2'; document.body.appendChild(s);
  }

  /* ── light: the beam at each break, the bar, the drifting room light ── */
  const SPEC = ['var(--violet)','var(--indigo)','var(--cyan)','var(--green)','var(--amber)','var(--coral)','var(--magenta)'];
  document.querySelectorAll('.beam').forEach(b => b.setAttribute('aria-hidden', 'true'));
  if ('IntersectionObserver' in window) {
    const bo = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('lit'); bo.unobserve(e.target); } }), {threshold:.6});
    document.querySelectorAll('.beam').forEach(b => bo.observe(b));
  } else document.querySelectorAll('.beam').forEach(b => b.classList.add('lit'));
  const bar = document.createElement('div'); bar.className = 'lightbar'; document.body.appendChild(bar);
  if (!CALM) { const a = document.createElement('div'); a.className = 'aurora'; document.body.prepend(a); }
  let spRaf = 0;
  const sp = () => { spRaf = 0; const h = document.documentElement.scrollHeight - innerHeight;
    root.style.setProperty('--sp', h > 0 ? (scrollY / h).toFixed(4) : 0); };
  addEventListener('scroll', () => { if (!spRaf) spRaf = requestAnimationFrame(sp); }, {passive:true}); sp();

  /* ═══ ASK — the repo answers questions about itself ═══════════════════
     Every guide in the repo is split into sections (docs/ask/knowledge.json,
     built by tools/build_ask.py). A question is matched against them here in
     the browser and answered with the passage that says it, and a link to it.
     Set ASK_AI to the AI worker's address (receiver/ask-ai.js) and the same
     box answers in plain sentences from the same sections instead. */
  const ASK_AI = '';
  let KB = null, panel, log, input;
  const STOP = new Set('a an the is it to of and or in on for how do does i my me what where when why which who can you your with this that be are was will should get use from at by as about into'.split(' '));
  const words = t => (t.toLowerCase().match(/[a-z0-9]+/g) || []).filter(w => w.length > 1 && !STOP.has(w)).map(w => w.replace(/(ing|ed|es|s)$/, ''));
  async function kb(){
    if (KB) return KB;
    const d = await (await fetch('/ask/knowledge.json')).json();
    const N = d.items.length, df = {};
    d.items.forEach(it => { it.w = words(it.section + ' ' + it.section + ' ' + it.doc + ' ' + it.tool.replace(/-/g, ' ') + ' ' + it.text);
      new Set(it.w).forEach(w => df[w] = (df[w] || 0) + 1); });
    KB = {items:d.items, idf:w => Math.log(1 + N / (1 + (df[w] || 0)))};
    return KB;
  }
  function best(q, K){
    const qs = [...new Set(words(q))];
    return K.items.map(it => {
      let sc = 0; const tf = {}; it.w.forEach(w => tf[w] = (tf[w] || 0) + 1);
      qs.forEach(w => { if (tf[w]) sc += K.idf(w) * (1 + Math.log(tf[w])); });
      // Two boosts, because one was not enough. A flat "any title word matched"
      // bonus scored image and video teardown identically for "what does the
      // video teardown do?" — and so did counting title hits, because the image
      // tool's own title says "the static-ad twin of the video chain". The tool's
      // SLUG is what actually separates them: image-teardown vs video-teardown.
      const head = (it.section + ' ' + it.tool).toLowerCase();
      const slug = (it.tool || '').toLowerCase().replace(/^\d+-/, '').replace(/-/g, ' ');
      const headHits = qs.filter(w => head.includes(w)).length;
      const slugHits = qs.filter(w => slug.includes(w)).length;
      if (headHits) sc *= 1 + 0.4 * headHits;
      if (slugHits) sc *= 1 + 0.8 * slugHits;
      return {it, sc};
    }).filter(x => x.sc > 0).sort((a, b) => b.sc - a.sc).slice(0, 3);
  }
  const esc = t => t.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const md = t => esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>');
  function excerpt(text, q){
    const qs = words(q), sents = text.replace(/\s+/g, ' ').split(/(?<=[.!?])\s+/);
    const ranked = sents.map((s, i) => ({s, i, n:words(s).filter(w => qs.includes(w)).length})).sort((a, b) => b.n - a.n || a.i - b.i);
    return ranked.slice(0, 3).sort((a, b) => a.i - b.i).map(x => x.s).join(' ').slice(0, 520);
  }
  function say(html, cls){ const d = document.createElement('div'); d.className = cls; d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }
  async function answer(q){
    q = q.trim(); if (!q) return;
    say(esc(q), 'me');
    const low = q.toLowerCase();
    if (/\bprizm\b/.test(low)) { shatter(); return say('<p>You found one. ✦</p>', 'it'); }
    if (/\blabs\b/.test(low) && low.length < 12) { window.dispatchEvent(new Event('labs')); return say('<p>The machine is listening.</p>', 'it'); }
    const wait = say('<p>Reading the repo…</p>', 'it');
    try {
      if (ASK_AI) {
        const r = await fetch(ASK_AI, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({q})});
        const d = await r.json(); if (!r.ok) throw new Error(d.error || 'ask failed');
        const srcs = (d.sources || []).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)} →</a>`).join('');
        wait.innerHTML = d.answer.split(/\n{2,}/).map(p => `<p>${md(p)}</p>`).join('') + (srcs ? `<div class="src">${srcs}</div>` : '');
        return;
      }
      const K = await kb(), hits = best(q, K);
      if (!hits.length) { wait.innerHTML = '<p>Nothing in the repo answers that yet. Try naming the tool, or <a href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">browse the repo</a>.</p>'; return; }
      const top = hits[0].it;
      wait.innerHTML = `<p><b>${esc(top.section)}</b>${top.tool ? ' · ' + esc(top.tool.replace(/^\d+-/, '').replace(/-/g, ' ')) : ''}</p><p>${md(excerpt(top.text, q))}</p>` +
        `<div class="src">${hits.map(h => `<a href="${esc(h.it.url)}" target="_blank" rel="noopener">${esc(h.it.section)} — ${esc(h.it.path)} →</a>`).join('')}</div>`;
    } catch (e) { wait.innerHTML = '<p>That didn’t go through. Try again in a moment.</p>'; }
  }
  function openAsk(q){
    if (!panel) {
      panel = document.createElement('div'); panel.className = 'ask-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Ask the machine');
      panel.innerHTML = `<div class="ask-head"><i class="ib" data-i="sparkles" style="--hue:var(--violet)">${icon('sparkles')}</i><b>Ask the machine</b><button class="x" aria-label="Close">×</button></div>
        <div class="ask-log"><div class="it"><p>Ask how anything works: where to start, what a tool does, how to get updates. Answers come straight from the repo.</p>
        <div class="ask-chips">${['What does the video teardown do?','What is My Feeds?','How does the email calendar work?','What is a brief?'].map(c => `<button type="button">${c}</button>`).join('')}</div></div></div>
        <form class="ask-form"><input type="text" placeholder="Ask a question…" aria-label="Your question" autocomplete="off" enterkeyhint="send"><button type="submit" aria-label="Ask">${icon('send')}</button></form>`;
      document.body.appendChild(panel);
      log = panel.querySelector('.ask-log'); input = panel.querySelector('input');
      panel.querySelector('.x').addEventListener('click', () => { panel.hidden = true; btn.hidden = false; });
      panel.querySelector('form').addEventListener('submit', e => { e.preventDefault(); answer(input.value); input.value = ''; });
      panel.querySelectorAll('.ask-chips button').forEach(b => b.addEventListener('click', () => answer(b.textContent)));
      kb().catch(() => {});
    }
    panel.hidden = false; btn.hidden = true;
    if (q) answer(q); else setTimeout(() => input.focus(), 50);
  }
  window.openAsk = openAsk;
  const btn = document.createElement('button'); btn.className = 'askbtn'; btn.type = 'button';
  btn.innerHTML = `<i class="ib">${icon('sparkles')}</i><span>Ask the machine</span>`; btn.setAttribute('aria-label', 'Ask the machine');
  btn.addEventListener('click', () => openAsk()); document.body.appendChild(btn);
  document.addEventListener('click', e => { const a = e.target.closest('[data-ask]'); if (a) { e.preventDefault(); openAsk(a.dataset.ask || ''); } });

  /* ═══ EASTER EGGS ════════════════════════════════════════════════════
     1  Konami code, or type "prizm" (on a phone: long-press the logo, or
        ask the Ask box "prizm") — the page shatters into spectrum.
     2  Tap the ® in the logo three times — the whole page runs the prism.
     3  Open the console — a note for whoever reads source.
     4  (home only) double-tap the head — it spins. See index.html.
     5  Type "labs" — the machine answers.
  */
  const shatter = () => {
    toast('One beam in. Everything out.');
    if (CALM) return;
    const c = document.createElement('canvas'); c.className = 'shards';
    const dpr = Math.min(2, devicePixelRatio || 1); c.width = innerWidth * dpr; c.height = innerHeight * dpr;
    document.body.appendChild(c); const k = c.getContext('2d'); k.scale(dpr, dpr);
    const hues = ['#6D3BF5', '#2F5BFF', '#00A8CC', '#12A06F', '#F09000', '#F04A2E', '#DB2A8C'];
    const ox = innerWidth / 2, oy = innerHeight * .42;
    const P = Array.from({length: 140}, (_, i) => {
      const a = Math.random() * Math.PI * 2, v = 3 + Math.random() * 9;
      return {x: ox, y: oy, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 4, r: Math.random() * 6.3, vr: (Math.random() - .5) * .3,
              w: 3 + Math.random() * 9, h: 1.5 + Math.random() * 3, c: hues[i % hues.length]};
    });
    const t0 = performance.now();
    (function frame(t) {
      const age = (t - t0) / 1000; k.clearRect(0, 0, innerWidth, innerHeight);
      for (const p of P) { p.vy += .22; p.vx *= .99; p.x += p.vx; p.y += p.vy; p.r += p.vr;
        k.save(); k.globalAlpha = Math.max(0, 1 - age / 2.4); k.translate(p.x, p.y); k.rotate(p.r);
        k.fillStyle = p.c; k.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); k.restore(); }
      if (age < 2.5) requestAnimationFrame(frame); else c.remove();
    })(t0);
  };

  const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  let seq = [], typed = '';
  addEventListener('keydown', e => {
    if (e.target.closest && e.target.closest('input,textarea,[contenteditable]')) return;
    seq = [...seq, e.key].slice(-KONAMI.length);
    if (seq.join() === KONAMI.join()) { seq = []; shatter(); }
    if (e.key.length === 1) typed = (typed + e.key.toLowerCase()).slice(-12);
    if (typed.endsWith('prizm')) { typed = ''; shatter(); }
    if (typed.endsWith('labs')) { typed = ''; toast('The machine is listening.'); window.dispatchEvent(new Event('labs')); }
  });

  // on a phone there is no keyboard: long-press the mark for the shatter,
  // or type the words into the Ask box
  const markEl = document.querySelector('nav.bar .mark');
  if (markEl) {
    let lp = 0, fired = false;
    markEl.addEventListener('pointerdown', () => { fired = false; lp = setTimeout(() => { fired = true; shatter(); }, 650); });
    ['pointerup','pointerleave','pointercancel'].forEach(t => markEl.addEventListener(t, () => clearTimeout(lp)));
    markEl.addEventListener('click', e => { if (fired) { e.preventDefault(); fired = false; } });
    markEl.addEventListener('contextmenu', e => e.preventDefault());
  }
  // the ® in the mark, three taps
  const mark = document.querySelector('nav.bar .mark');
  if (mark && mark.textContent.includes('®')) {
    mark.innerHTML = mark.innerHTML.replace('®', '<span class="reg">®</span>');
    let n = 0, t = 0;
    mark.querySelector('.reg').addEventListener('click', e => {
      e.preventDefault(); e.stopPropagation();
      n = performance.now() - t < 700 ? n + 1 : 1; t = performance.now();
      if (n >= 3) { n = 0; root.classList.remove('spectrum'); void root.offsetWidth; root.classList.add('spectrum');
        toast('You found the prism.'); setTimeout(() => root.classList.remove('spectrum'), 1700); }
    });
  }

  try {
    console.log('%cPRIZM LABS', 'font:800 22px Unbounded,sans-serif;background:linear-gradient(96deg,#6D3BF5,#2F5BFF,#00A8CC,#12A06F,#F09000,#F04A2E,#DB2A8C);-webkit-background-clip:text;color:transparent');
    console.log('%cYou read source. You are our kind of person.\nEvery prompt behind this site is a readable file: https://github.com/daemnapps/prizm-labs\n(try typing "prizm" on the page)', 'font:12px "DM Mono",monospace;color:#6A635A');
  } catch (e) {}
})();
