/* My Feeds — reads the static export in /feeds/data/ (written by the team
   repo's components/swipe-organic/feedsexport.py). No server, no keys. */
(() => {
  const DATA = '/feeds/data/';
  const PAGE = 24;
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const PLAT = {tiktok: 'TikTok', instagram: 'Instagram', youtube: 'YouTube'};
  const big = n => n == null ? '' : n >= 1e9 ? (n/1e9).toFixed(1).replace(/\.0$/,'') + 'B'
    : n >= 1e6 ? (n/1e6).toFixed(1).replace(/\.0$/,'') + 'M' : n >= 1e3 ? Math.round(n/1e3) + 'K' : String(n);

  const q = new URLSearchParams(location.search);
  const st = {t: q.get('t') === 'paid' ? 'paid' : 'organic', who: q.get('who'), sort: q.get('sort') || 'views', shown: PAGE};
  let index = null, people = {}, rows = [];
  const cache = {};

  function save() {
    const p = new URLSearchParams();
    if (st.t === 'paid') p.set('t', 'paid');
    if (st.who) p.set('who', st.who);
    if (st.sort !== 'views') p.set('sort', st.sort);
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }

  async function get(path) {
    if (!cache[path]) cache[path] = fetch(DATA + path).then(r => r.ok ? r.json() : []).catch(() => []);
    return cache[path];
  }

  function drawTabs() {
    document.querySelectorAll('.tab').forEach(b => b.setAttribute('aria-selected', b.dataset.t === st.t));
    document.body.classList.toggle('paid', st.t === 'paid');
    document.documentElement.style.setProperty('--hue', st.t === 'paid' ? 'var(--indigo)' : 'var(--violet)');
    $('#examples').style.display = st.t === 'paid' ? '' : 'none';
    const opts = st.t === 'paid' ? [['views', 'Running longest'], ['copies', 'Most copies']] : [['views', 'Most views'], ['new', 'Newest']];
    if (!opts.some(o => o[0] === st.sort)) st.sort = 'views';
    $('#sort').innerHTML = opts.map(([k, l]) =>
      `<button class="btn ${k === st.sort ? '' : 'ghost'}" data-sort="${k}">${l}</button>`).join('');
  }

  function drawWho() {
    const box = $('#who');
    let html = '<span class="label">Who is it for?</span>';
    for (const g of index.groups) {
      html += `<span class="label">${esc(g)}</span>`;
      for (const p of index.people.filter(p => p.group === g))
        html += `<button data-who="${esc(p.slug)}" aria-pressed="${p.slug === st.who}">${esc(p.label)}</button>`;
    }
    box.innerHTML = html;
    const p = people[st.who];
    $('#wholine').textContent = p ? p.line : '';
  }

  function sorted() {
    const r = rows.slice();
    if (st.t === 'paid') r.sort(st.sort === 'copies' ? (a, b) => b.copies - a.copies : (a, b) => (b.days || 0) - (a.days || 0));
    else if (st.sort === 'new') r.sort((a, b) => String(b.posted || '').localeCompare(String(a.posted || '')));
    else r.sort((a, b) => (b.views || 0) - (a.views || 0));
    return r;
  }

  function stat(r) {
    if (st.t === 'paid') return [r.days ? `Running ${r.days} day${r.days === 1 ? '' : 's'}` : null,
      `${r.copies.toLocaleString()} cop${r.copies === 1 ? 'y' : 'ies'}`].filter(Boolean).join(' · ');
    return [PLAT[r.platform] || r.platform, r.views ? big(r.views) + ' views' : null].filter(Boolean).join(' · ');
  }

  function line(r) {
    if (st.t === 'paid') return r.headline || r.copy || '';
    return r.what || (r.author ? '@' + r.author : '');
  }

  function drawFeed() {
    const list = sorted();
    const img = r => r.thumb ? `<img src="${DATA}thumbs/${esc(r.id)}.webp" alt="" loading="lazy">` : '<div class="noimg"></div>';
    $('#feed').innerHTML = list.slice(0, st.shown).map((r, i) =>
      `<button class="pc" data-i="${i}">${img(r)}<span class="b">` +
      (st.t === 'paid' ? `<span class="label hue">${esc(r.brand)}</span>` : '') +
      `<span class="w">${esc(line(r))}</span><span class="s">${esc(stat(r))}</span></span></button>`).join('') ||
      '<p class="lede">Nothing here yet for this person.</p>';
    $("#more").style.display = list.length <= st.shown ? "none" : "";
    $('#feed')._list = list;
  }

  async function load() {
    drawTabs(); drawWho(); save();
    rows = await get(`${st.t}/${st.who}.json`);
    drawFeed();
  }

  /* ---- the side panel */
  function prompt(r) {
    const p = people[st.who] || {};
    const who = `${p.label || 'anyone'} — ${p.line || ''}`.trim();
    if (st.t === 'paid') return [
      'Take this ad apart and write a brief from it.', '',
      `Ad: ${r.url}`, `Brand running it: ${r.brand}`, r.headline ? `Headline: ${r.headline}` : null,
      `Who it's for: ${who}`, '',
      `Use ${r.video ? 'tools/video-teardown' : 'tools/image-teardown'} in the Prizm Labs repo (https://github.com/daemnapps/prizm-labs). ` +
      "Take the ad apart, then write the brief for that person. Copy the structure, not the words. Don't invent anything."
    ].filter(x => x !== null).join('\n');
    return [
      'Take this post apart and write a brief from it.', '',
      `Post: ${r.url}`, `Who it's for: ${who}`, '',
      `Use ${r.pic ? 'tools/image-teardown' : 'tools/video-teardown (or tools/image-teardown if it is a picture)'} in the Prizm Labs repo (https://github.com/daemnapps/prizm-labs). ` +
      "Take the post apart, then write the brief for that person. Copy the structure, not the words. Don't invent anything."
    ].join('\n');
  }

  function md(src) {
    const out = [], L = esc(src).split('\n');
    const inl = s => s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/(^|\s)\*(\S.+?)\*/g, '$1<em>$2</em>').replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    for (let i = 0; i < L.length; i++) {
      const l = L[i];
      if (/^```/.test(l)) { const b = []; while (++i < L.length && !/^```/.test(L[i])) b.push(L[i]); out.push(`<pre>${b.join('\n')}</pre>`); }
      else if (/^#{1,3} /.test(l)) { const n = l.match(/^#+/)[0].length + 1; out.push(`<h${n}>${inl(l.replace(/^#+ /, ''))}</h${n}>`); }
      else if (/^\|/.test(l)) {
        const t = []; while (i < L.length && /^\|/.test(L[i])) t.push(L[i++]); i--;
        out.push('<div class="tablewrap"><table>' + t.filter(x => !/^\|[\s|:-]+\|$/.test(x)).map((x, j) =>
          '<tr>' + x.replace(/^\||\|$/g, '').split('|').map(c => j ? `<td>${inl(c.trim())}</td>` : `<th>${inl(c.trim())}</th>`).join('') + '</tr>').join('') + '</table></div>');
      }
      else if (/^\s*[-*] /.test(l)) { const u = []; while (i < L.length && /^\s*[-*] /.test(L[i])) u.push(`<li>${inl(L[i++].replace(/^\s*[-*] /, ''))}</li>`); i--; out.push(`<ul>${u.join('')}</ul>`); }
      else if (l.trim()) out.push(`<p>${inl(l)}</p>`);
    }
    return out.join('');
  }

  async function open(r) {
    const s = $('#sheet');
    const p = prompt(r);
    const claude = 'https://claude.ai/new?q=' + encodeURIComponent(p);
    const watch = st.t === 'paid'
      ? `<p><a class="btn ghost" href="${esc(r.url)}" target="_blank" rel="noopener">Watch it in the Meta Ad Library</a></p>`
      : `<p><a class="btn ghost" href="${esc(r.url)}" target="_blank" rel="noopener">Watch it on ${esc(PLAT[r.platform] || 'the app')}</a></p>`;
    const head = st.t === 'paid'
      ? `<p class="label hue">${esc(r.brand)}</p><h3>${esc(r.headline || 'An ad')}</h3><p>${esc(r.copy)}${r.copy && r.copy.length >= 200 ? '…' : ''}</p>`
      : `<p class="label hue">${r.author ? '@' + esc(r.author) : ''}</p><h3>${esc(r.what || 'A post')}</h3>`;
    s.innerHTML = `<button class="btn ghost x" id="x">Close</button>
      <p class="eyebrow">${esc(stat(r))}</p>${head}
      ${r.thumb ? `<img class="cover" src="${DATA}thumbs/${esc(r.id)}.webp" alt="">` : ''}
      <h2>1 · Watch it</h2>${watch}
      ${r.frames ? `<img class="frames" src="${DATA}thumbs/${esc(r.id)}-frames.webp" alt="Six moments from the video, left to right">` : ''}
      <h2>2 · How it's built</h2><div id="built">${r.sheet ? '<p>Loading…</p>' : "<p>Not taken apart yet. The prompt below does it.</p>"}</div>
      <h2>3 · Make your own</h2>
      <div class="btns"><a class="btn" href="${esc(claude)}" target="_blank" rel="noopener">Open in Claude</a>
      <button class="btn ghost" id="copy">Copy the prompt</button></div>
      <ol class="steps">
        <li><div><b>Press a button</b><p>Open in Claude, or Copy the prompt.</p></div></li>
        <li><div><b>Open your tool</b><p>Your Higgsfield Supercomputer, or Claude Code with the Prizm Labs repo.</p></div></li>
        <li><div><b>Paste and press Enter</b><p>It takes the ${st.t === 'paid' ? 'ad' : 'post'} apart and writes the brief.</p></div></li>
      </ol>
      <details><summary>See the prompt</summary><pre>${esc(p)}</pre></details>`;
    s.hidden = false; $('#scrim').hidden = false; s.scrollTop = 0;
    $('#x').onclick = close;
    $('#copy').onclick = async () => {
      try { await navigator.clipboard.writeText(p); $('#copy').textContent = 'Copied — now paste it'; }
      catch { $('#copy').textContent = 'Press and hold the prompt below to copy'; s.querySelector('details').open = true; }
    };
    if (r.sheet) {
      const d = await get(`sheets/${r.id}.json`);
      $('#built').innerHTML = d && d.text ? `<div class="brief">${md(d.text)}</div>` : '<p>Not taken apart yet. The prompt below does it.</p>';
    }
  }
  function close() { $('#sheet').hidden = true; $('#scrim').hidden = true; }

  /* ---- wiring */
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-t]'), w = e.target.closest('[data-who]'), so = e.target.closest('[data-sort]'), c = e.target.closest('.pc');
    if (t) { st.t = t.dataset.t; st.shown = PAGE; load(); }
    else if (w) { st.who = w.dataset.who; st.shown = PAGE; load(); }
    else if (so) { st.sort = so.dataset.sort; st.shown = PAGE; drawTabs(); save(); drawFeed(); }
    else if (c) open($('#feed')._list[+c.dataset.i]);
  });
  $('#more').onclick = () => { st.shown += PAGE; drawFeed(); };
  $('#scrim').onclick = close;
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  get('index.json').then(ix => {
    index = ix;
    ix.people.forEach(p => people[p.slug] = p);
    if (!people[st.who]) st.who = ix.people[0] && ix.people[0].slug;
    $('#updated').textContent = ix.updated;
    load();
  });
})();
