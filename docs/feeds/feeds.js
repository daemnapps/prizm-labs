/* My Feeds — Damon's board (the desk, port 8820) on the site, read-only.
   Same controls, same cards, same behaviour; reads the static export in
   /feeds/data/ (written by the team repo's components/swipe-organic/
   feedsexport.py after each Pull). No server, no keys, nothing here spends.
   Organic = the desk. Paid = competitors' ads on the same control bar. */
(() => {
  const DATA = '/feeds/data/';
  const PAGE = 240;
  const $ = id => document.getElementById(id);
  const esc = s => (s ?? '').toString().replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => n == null ? '' : n >= 1e9 ? (n/1e9).toFixed(1) + 'B' : n >= 1e6 ? (n/1e6).toFixed(1) + 'M' : n >= 1e3 ? Math.round(n/1e3) + 'K' : '' + n;
  const day = s => s ? new Date(s.length > 10 ? s : s + 'T12:00:00Z') : null;
  const days = s => s ? Math.floor((Date.now() - day(s)) / 864e5) : null;
  const md = s => s ? day(s).toLocaleDateString('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'}) : '';
  const mdy = s => s ? day(s).toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'}) : '';
  const UP = b => b == 'general' ? 'General' : b.toUpperCase();
  const P = {tiktok: 'TIKTOK', instagram: 'REEL', youtube: 'YOUTUBE'};
  const PLATN = {tiktok: 'TikTok', instagram: 'Instagram', youtube: 'YouTube'};
  const SORTS = [['in', 'Just in'], ['sent', 'Most sent'], ['rise', 'Rising'], ['punch', 'Punching above'], ['views', 'Most viewed'], ['new', 'Newest post']];
  const PSORTS = [['days', 'Running longest'], ['new', 'Newest ad'], ['copies', 'Most copies']];
  const WINS = [['7', '7d'], ['30', '30d'], ['90', '90d'], ['all', 'All time']];

  // ---- state (kept in the address bar, so a view can be sent as a link)
  const u = new URLSearchParams(location.search);
  let t = u.get('t') == 'paid' ? 'paid' : 'organic';
  let brand = u.get('brand') || 'all', feed = u.get('who') || 'all', q0 = u.get('q') || '';
  let lane = u.get('lane') || 'entertainment', shape = u.get('shape') || 'all', plat = u.get('plat') || 'all';
  let win = u.get('win') || 'all', showOut = u.get('out') == '1', adv = u.get('adv') || 'all', kind = u.get('kind') || 'all';
  let sort = u.get('sort') || '';
  // links from the page this replaced: ?sort=views|new (organic), ?t=paid&sort=views|copies
  if (t == 'paid') sort = {views: 'days', copies: 'copies'}[sort] || (PSORTS.some(s => s[0] == sort) ? sort : 'days');
  else if (!SORTS.some(s => s[0] == sort)) sort = 'in';
  let view = 'feed', stageOn = 1, CH = null, shown = PAGE;
  let S = null, CARDS = [], ADS = null;
  $('q').value = q0;

  function save() {
    const p = new URLSearchParams();
    const put = (k, v, d) => { if (v != d) p.set(k, v); };
    put('t', t, 'organic'); put('brand', brand, 'all'); put('who', feed, 'all'); put('q', $('q').value.trim(), '');
    put('sort', sort, t == 'paid' ? 'days' : 'in'); put('win', win, 'all');
    if (t == 'organic') { put('lane', lane, 'entertainment'); put('shape', shape, 'all'); put('plat', plat, 'all'); put('out', showOut ? '1' : '0', '0'); }
    else { put('adv', adv, 'all'); put('kind', kind, 'all'); }
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }

  function chips(el, opts, cur, set) {
    el.innerHTML = opts.map(([v, l]) => `<button class="${v == cur ? 'on' : ''}" data-v="${esc(v)}">${esc(l)}</button>`).join('');
    el.querySelectorAll('button').forEach(b => b.onclick = () => { set(b.dataset.v); shown = PAGE; draw(); });
  }

  const fb = f => f.core && f.brand != 'general' ? f.brand : 'general';
  const own = f => !f.core;

  // ---- the avatar picker
  // It used to be one <select> holding everything, which buried the shape of
  // the thing: a real avatar, Damon's own saved scrolls and a shop/clipper
  // collection all looked alike in one flat list (Damon, 2 Oct: "our menu to
  // select through our different avatars is clunky"). Now it opens as a panel
  // that shows the actual tree — core avatar with its subs indented under it —
  // and keeps saves and collections in their own named columns, because they
  // are not avatars and never were.
  // Everything that belongs to a core avatar sits under that avatar — its subs
  // and its collections alike (Damon, 2 Oct: "Base, Shop, and Clipper videos
  // still go underneath the avatar. That's the whole thing."). Only his own
  // saved scrolls stand apart, because they are not an avatar at all.
  const isSave = f => own(f);
  const isCore = f => !own(f) && !f.sub && f.core == f.id;
  // Menu labels drop the parenthetical gloss — "El Jefe de la Casa (The
  // Spanish-First Working Man)" wrapped to three lines and made the list ragged.
  // The full name still shows on the button and in the feed's own header.
  const short = f => (f.title || (f.id || '').replace(/-/g, ' ')).replace(/\s*\([^)]*\)\s*$/, '');

  function pickerGroups(inBrand, count) {
    const cores = {}, saves = [];
    inBrand.forEach(f => isSave(f) ? saves.push(f) : (cores[f.core] = cores[f.core] || []).push(f));
    const row = (f, cls) => `<button type="button" data-feed="${esc(f.id)}" class="${cls}${feed == f.id ? ' on' : ''}">` +
      `<span class="t">${esc(short(f))}</span><span class="n">${count(f)}</span></button>`;
    let out = `<div class="m-mg"><button type="button" data-feed="all" class="core${feed == 'all' ? ' on' : ''}">` +
      `<span class="t">All avatars${brand == 'all' ? '' : ' in ' + UP(brand)}</span></button></div>`;
    Object.keys(cores).sort().forEach(c => {
      const list = cores[c], head = list.find(isCore);
      const rest = list.filter(f => f !== head).sort((a, b) => short(a).localeCompare(short(b)));
      const br = head && brand == 'all' ? `<span class="br">${esc(UP(head.brand))}</span>` : '';
      out += `<hr><div class="m-mg"><div class="h">${br}<span>${esc(c.replace(/-/g, ' '))}</span></div>` +
        (head ? row(head, 'core') : '') + rest.map(f => row(f, 'sub')).join('') + '</div>';
    });
    if (saves.length) out += `<hr><div class="m-mg"><div class="h"><span>Saved by hand</span></div>` +
      saves.map(f => row(f, '')).join('') +
      `<p class="note">Not avatars. Each post keeps the brand it was saved for.</p></div>`;
    return out;
  }

  // The detail half of the mega menu: who this avatar actually is, what their
  // scroll looks like, and where we go looking for it. Damon, 2 Oct: "so that
  // we can actually see what the avatar would look like and each of the
  // sub-avatars, so it's very clear who we are actually speaking to."
  function detailHTML(f, count) {
    if (!f) return '<p class="who">Point at an avatar to see who they are.</p>';
    const path = [UP(f.brand), (f.core || '').replace(/-/g, ' ')]
      .filter(Boolean).concat(f.sub && f.sub != f.core ? ['sub-avatar'] : []).join(' · ');
    const pics = (typeof CARDS != 'undefined' ? CARDS : [])
      .filter(c => c.feed == f.id && c.thumb && c.keep !== false).slice(0, 5);
    const srcs = f.source_list || [];
    const seen = [];
    srcs.forEach(x => { const v = (x.value || '').trim(); if (v && !seen.some(y => y.v == v)) seen.push({ v, k: x.kind }); });
    const chips = seen.slice(0, 14).map(x =>
      `<span class="${x.k == 'hashtag' ? 'tag' : ''}">${x.k == 'hashtag' ? '#' : ''}${esc(x.v)}</span>`).join('');
    return `<p class="path">${esc(path)}</p><h4>${esc(f.title || f.id)}</h4>` +
      (f.whose ? `<p class="who">${esc(f.whose)}</p>` : '') +
      (pics.length ? `<div><p class="lab">What they watch</p><div class="m-strip">` +
        pics.map(c => `<img loading="lazy" alt="" src="${DATA}thumbs/${esc(c.id)}.webp" onerror="this.style.visibility='hidden'">`).join('') +
        `</div></div>` : '') +
      (seen.length ? `<div><p class="lab">Where we look — ${seen.length} source${seen.length == 1 ? '' : 's'}</p>` +
        `<div class="m-look">${chips}${seen.length > 14 ? `<span class="more">+${seen.length - 14} more</span>` : ''}</div></div>` : '') +
      `<p class="nums"><span><b>${count(f)}</b> posts kept</span>` +
      (f.sweeps ? `<span><b>${f.sweeps}</b> sweep${f.sweeps == 1 ? '' : 's'}</span>` : '') +
      (f.probation ? `<span><b>${f.probation}</b> on trial</span>` : '') + `</p>`;
  }

  function mountPicker(inBrand, count, onPick) {
    const btn = $('avatarbtn'), menu = $('avatarmenu');
    const cur = inBrand.find(f => f.id == feed);
    btn.querySelector('.cur').textContent = cur ? short(cur) :
      'All avatars' + (brand == 'all' ? '' : ' in ' + UP(brand));
    btn.querySelector('.cnt').textContent = cur ? count(cur) : '';
    menu.className = 'm-menu mega';
    menu.innerHTML = `<div class="m-mtree">${pickerGroups(inBrand, count)}</div>` +
                     `<div class="m-mdet" id="avatardet"></div>`;
    const byId = {};
    inBrand.forEach(f => byId[f.id] = f);
    const show = f => { $('avatardet').innerHTML = detailHTML(f, count); };
    show(cur || inBrand.find(f => !f.sub && f.core == f.id) || inBrand[0]);
    menu.querySelectorAll('button[data-feed]').forEach(b => {
      const f = byId[b.dataset.feed];
      b.addEventListener('mouseenter', () => show(f));
      b.addEventListener('focus', () => show(f));
    });
    const close = () => { menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); };
    // The panel is far wider than its button, so opened near the right of the
    // window it ran off the edge and cut the detail pane in half. Nudge it back
    // by however much it overhangs, once it is on screen and measurable.
    const fit = () => {
      menu.style.transform = '';
      const over = menu.getBoundingClientRect().right - (innerWidth - 12);
      if (over > 0) menu.style.transform = `translateX(${-Math.ceil(over)}px)`;
    };
    btn.onclick = e => {
      e.stopPropagation();
      menu.hidden = !menu.hidden;
      btn.setAttribute('aria-expanded', String(!menu.hidden));
      if (!menu.hidden) fit();
    };
    if (!menu.hidden) fit();
    menu.onclick = e => {
      const b = e.target.closest('button[data-feed]');
      if (!b) return;
      close();
      onPick(b.dataset.feed);
    };
    if (!mountPicker.wired) {           // one listener for the life of the page
      mountPicker.wired = true;
      document.addEventListener('click', e => { if (!e.target.closest('.m-pick')) close(); });
      document.addEventListener('keydown', e => { if (e.key == 'Escape') close(); });
    }
  }


  // Every card reads the same way: two numbers big enough to actually see,
  // then one signal, then the quiet dates. Damon, 2 Oct — the counts "need to
  // be way clearer… right now they're just light", and the cards were ragged
  // because the performance badges appeared on some and not others, floating
  // over the picture at whatever count happened to qualify. They sit in one
  // fixed slot now, so two cards side by side are comparable.
  const stat = (n, label) => n ? `<b>${fmt(n)}</b><i>${label}</i>` : '';
  // One signal per card, the strongest it has, always in the same place.
  function signal(c) {
    const s = c.punch >= 3 ? `${c.punch >= 100 ? Math.round(c.punch) : c.punch}× their following`
      : c.rise >= 5 ? `▲ ${Math.round(c.rise)}%/day`
      : c.sent >= 5 ? `↗ ${c.sent} sent/1K` : '';
    return s ? `<span class="m-sig">${s}</span>` : '';
  }

  // A card with no lane used to pass EVERY lane filter (`!c.lane ||`), so the
  // 1,095 unclassified posts — all of BASED, all of Clipper Videos, all of his
  // own saves — showed up under Entertainment and under Educational alike.
  // Damon, 2 Oct: "all of Based is in Entertainment when clearly that's about
  // Product and Brand." They answer to "Unsorted" now and nothing else, so what
  // has been classified and what has not is visible instead of blended.
  const laneOK = c => lane == 'all' || (lane == 'unsorted' ? !c.lane : c.lane == lane);

  function draw() {
    if (!S) return;
    chips($('tabs'), [['organic', 'Organic'], ['paid', 'Paid']], t, v => {
      if (v == t) return;
      t = v; view = 'feed'; sort = t == 'paid' ? 'days' : 'in';
      if (t == 'paid' && !ADS) loadAds();
    });
    $('desk').classList.toggle('paid', t == 'paid');
    if (t == 'paid') drawPaid(); else drawOrganic();
    save();
  }

  // ================================================================ ORGANIC
  function drawOrganic() {
    const newToday = CARDS.filter(c => c.seen_days === 0 && c.keep !== false).length;
    $('stats').textContent = `${S.feeds.length} feeds · ${CARDS.length.toLocaleString()} posts · ${newToday} new today · ${S.updated}`;
    $('q').placeholder = 'Search every post — captions, creators, hashtags, formats';
    const bl = [...new Set(S.feeds.map(fb))].sort((x, y) => (x == 'general') - (y == 'general') || x.localeCompare(y));
    chips($('brands'), [['all', 'All brands'], ...bl.map(b => [b, UP(b)])], brand, v => { brand = v; feed = 'all'; view = 'feed'; });
    // A feed with no avatar of its own (his saves) is never filtered out by a
    // brand chip — each of its cards carries the brand it was saved for.
    const inBrand = S.feeds.filter(f => brand == 'all' || own(f) || fb(f) == brand);
    const count = f => CARDS.filter(c => c.feed == f.id && c.keep !== false && laneOK(c)).length;
    if (feed != 'all' && !S.feeds.some(f => f.id == feed)) feed = 'all';
    mountPicker(inBrand, count, v => { feed = v; if (feed == 'all') view = 'feed'; shown = PAGE; draw(); });
    $('advsel').hidden = true;
    $('sortsel').innerHTML = SORTS.map(([v, l]) => `<option value="${v}" ${v == sort ? 'selected' : ''}>Sort: ${l}</option>`).join('');
    $('sortsel').onchange = () => { sort = $('sortsel').value; shown = PAGE; draw(); };
    for (const id of ['lanes', 'shapes', 'plats']) $(id).hidden = false;
    $('dropped').hidden = false;
    chips($('lanes'), [['entertainment', 'Entertainment'], ['educational', 'Educational'], ['unsorted', 'Unsorted'], ['all', 'All']], lane, v => lane = v);
    chips($('wins'), WINS, win, v => win = v);
    chips($('plats'), [['all', 'All'], ['tiktok', 'TikTok'], ['instagram', 'Instagram'], ['youtube', 'YouTube']], plat, v => plat = v);
    // his saves carry their own read — ad-shaped or culture. Other feeds have
    // none and are never hidden by this chip.
    chips($('shapes'), [['all', 'Any shape'], ['swipe', 'Ad-shaped'], ['organic', 'Culture']], shape, v => shape = v);
    $('dropped').classList.toggle('on', showOut);

    const f = S.feeds.find(x => x.id == feed);
    $('feedhead').innerHTML = f ? `${f.whose ? `<div class="m-ask">${esc(f.whose)}</div>` : f.line ? `<div class="m-ask">${esc(f.line)}</div>` : ''}
      ${f.sources} sources${f.probation ? ` · ${f.probation} on trial (found by following winners)` : ''} · ${f.sweeps} pulls so far
      · <button class="m-chip ${view == 'chain' ? 'on' : ''}" id="chainbtn">The research chain</button>
      <details><summary>What it watches, and why</summary>${f.source_list.map(s => `<span class="m-src ${s.status == 'probation' ? 'pro' : ''}" title="${esc(s.why)}">${esc(s.platform.slice(0, 2).toUpperCase())} ${s.kind == 'hashtag' ? '#' : s.kind == 'account' ? '@' : '“'}${esc(s.value)}${s.kind == 'search' ? '”' : ''}</span>`).join('')}</details>` : '';
    if (f) $('chainbtn').onclick = () => { view = view == 'chain' ? 'feed' : 'chain'; draw(); };
    const chain = f && view == 'chain';
    $('grid').hidden = chain; $('chainbox').hidden = !chain;
    if (chain) { $('more').hidden = true; drawChain(f.id); return; }

    const words = $('q').value.toLowerCase().split(/\s+/).filter(Boolean);
    const okFeeds = new Set(inBrand.map(f => f.id));
    const ownFeeds = new Set(S.feeds.filter(own).map(f => f.id));
    let cs = CARDS.filter(c => (feed == 'all' ? okFeeds.has(c.feed) : c.feed == feed) && (plat == 'all' || c.platform == plat)
      && (showOut || c.keep !== false) && laneOK(c) && (win == 'all' || (c.age != null && c.age <= +win))
      && (shape == 'all' || !c.swipe_lane || c.swipe_lane == shape)
      && (brand == 'all' || !ownFeeds.has(c.feed) || !c.brand_fit || c.brand_fit == brand || (brand == 'general' && c.brand_fit == 'general')));
    if (words.length) cs = cs.filter(c => { const hay = [c.author, c.caption, c.what, c.format, c.why, c.source, (c.tags || []).join(' ')].join(' ').toLowerCase(); return words.every(w => hay.includes(w)); });
    const key = {in: c => [-(c.seen_days ?? 999), c.views || 0], rise: c => [c.rise ?? -1, c.views || 0], sent: c => [c.sent ?? -1, c.views || 0], punch: c => [c.punch ?? -1, c.views || 0],
      views: c => [c.views || 0, 0], new: c => [-(c.age ?? 9999), c.views || 0]}[sort];
    cs.sort((a, b) => { const x = key(a), y = key(b); return y[0] - x[0] || y[1] - x[1]; });
    const seen = new Set(); cs = cs.filter(c => !seen.has(c.key) && seen.add(c.key));
    $('grid').innerHTML = cs.length ? cs.slice(0, shown).map((c, i) => `<div class="m-card ${c.keep === false ? 'out' : ''}"><a class="m-thumb" href="${esc(c.url)}" target="_blank" rel="noopener">
      ${c.thumb ? `<img loading="lazy" alt="" src="${DATA}thumbs/${esc(c.id)}.webp" onerror="this.remove()">` : ''}
      <span class="m-pb">${P[c.platform] || '?'}</span><span class="m-badges">
      ${c.seen_days === 0 ? '<span class="m-bd new">NEW</span>' : ''}</span></a>
      <div class="m-body"><div class="m-author">@${esc(c.author)}${c.kind ? ` <span class="m-sub">· ${esc(c.kind)}</span>` : ''}</div>
      ${c.what ? `<div class="m-what">${esc(c.what)}</div>` : ''}<div class="m-cap">${esc(c.caption)}</div>
      <div class="m-stats">${stat(c.views, 'views')}${stat(c.likes, 'likes')}${signal(c)}</div>
      <div class="m-meta">${[md(c.posted), c.age != null ? c.age + 'd old' : ''].filter(Boolean).join(' · ')}</div>
      ${c.format && c.format != 'unread' ? `<div class="m-fmt">format: ${esc(c.format)}</div>` : ''}
      ${c.why ? `<div class="m-why">${esc(c.why)}</div>` : ''}
      <div class="m-acts"><a href="${esc(c.url)}" target="_blank" rel="noopener">Open</a>
      ${c.sheet || c.frames ? `<button data-i="${i}" data-sheet="1">Sheet</button>` : ''}
      <button data-i="${i}">Make your own</button></div></div></div>`).join('')
      : `<div class="m-empty">Nothing matches.</div>`;
    $('more').hidden = cs.length <= shown;
    $('grid')._list = cs;
  }

  async function drawChain(id) {
    const box = $('chainbox');
    if (!CH || CH.feed != id) { box.innerHTML = '<div class="m-empty">Reading the chain…</div>'; CH = await get(`chain/${id}.json`); if (!CH || !CH.stages) { box.innerHTML = '<div class="m-empty">No chain for this feed.</div>'; return; } }
    const st = CH.stages, o = n => st[n - 1].output;
    const big = [o(1) ? ['TIKTOK_SEARCHES', 'TIKTOK_HASHTAGS', 'INSTAGRAM_HASHTAGS', 'YOUTUBE_SEARCHES'].reduce((a, k) => a + (o(1)[k] || []).length, 0) + ' searches' : 'built by hand',
      o(2) ? `${o(2).new} new of ${Object.values(o(2).by_source || {}).reduce((a, x) => a + x.returned, 0) || o(2).observed} returned` : 'not yet',
      (() => { const k = Object.values(o(3).kinds); const a = k.reduce((x, y) => x + y.kept, 0), d = k.reduce((x, y) => x + y.dropped, 0); return a + d ? `${a} in · ${d} out` : 'not sifted'; })(),
      `${o(4).length} creators found`, `${o(5).pulls_so_far} pulls so far`];
    box.innerHTML = `<div class="m-pipe">${st.map((x, i) => `<div class="m-st ${stageOn == x.n ? 'on' : ''}" data-n="${x.n}"><div class="n">Stage ${x.n}</div><div class="nm">${esc(x.name)}</div><div class="d">${esc(x.does)}</div><div class="big">${esc(big[i])}</div><div class="n">${esc(x.model)}</div></div>`).join('')}</div><div class="m-stage" id="stagebox"></div>`;
    box.querySelectorAll('.m-st').forEach(e => e.onclick = () => { stageOn = +e.dataset.n; drawChain(id); });
    const x = st[stageOn - 1]; let out = '';
    const tbl = h => `<div class="tablewrap"><table>${h}</table></div>`;
    if (x.n == 1) out = x.output ? tbl(Object.entries(x.output).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(Array.isArray(v) ? v.map(y => typeof y == 'object' ? JSON.stringify(y) : y).join(' · ') : v)}</td></tr>`).join('')) : 'This feed’s sources were seated by hand from the avatar’s receipts — no plan stage ran.';
    if (x.n == 2) out = x.output ? `<p class="m-sub">Door rules: nothing older than ${x.entry?.max_age_days ?? '—'} days · search finds need ${fmt(x.entry?.hashtag_min_views)} views or ${fmt(x.entry?.hashtag_min_likes)} likes · declared ads never enter</p>
      ${tbl(`<tr><th>source</th><th>returned</th><th>new in</th><th>ads</th><th>too old</th><th>too small</th></tr>${Object.entries(x.output.by_source || {}).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${v.returned}</td><td class="kp">${v.new}</td><td>${v.ad}</td><td>${v.too_old}</td><td>${v.too_small}</td></tr>`).join('')}`)}${x.output.trouble ? `<p class="dr">${x.output.trouble} source(s) failed on the last pull.</p>` : ''}` : 'Hasn’t pulled yet.';
    if (x.n == 3) { const rows = l => l.map(r => `<tr><td><a href="${esc(r.url)}" target="_blank" rel="noopener">@${esc(r.author)}</a></td><td>${esc(r.kind)}</td><td>${esc(r.why)}</td></tr>`).join('');
      out = Object.keys(x.output.kinds).length ? `${tbl(`<tr><th>kind</th><th>kept</th><th>thrown out</th></tr>${Object.entries(x.output.kinds).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="kp">${v.kept || ''}</td><td class="dr">${v.dropped || ''}</td></tr>`).join('')}`)}
      <div class="m-two"><div><h4 class="kp">Kept — and why</h4>${tbl(rows(x.output.kept))}</div><div><h4 class="dr">Thrown out — and why</h4>${tbl(rows(x.output.dropped))}</div></div>` : 'No sift on this feed — it has no ask to sift against.'; }
    if (x.n == 4) out = x.output.length ? tbl(x.output.map(d => `<tr><td>${esc(d.platform)}</td><td>@${esc(d.value)}</td><td>${esc(d.why)}</td></tr>`).join('')) : 'Nothing followed yet.';
    if (x.n == 5) out = 'Stages 2–4 run again each time the feed is pulled.';
    $('stagebox').innerHTML = `<h3>Stage ${x.n} — ${esc(x.name)}</h3><div class="m-sub">${esc(x.does)}</div>
      <div class="m-two"><div><h4>What it was sent</h4>${x.prompt_file ? `<p>The prompt <b>${esc(x.prompt_file)}</b> — in full under “The prompts — exactly as sent” at the bottom of this page.</p>` : '<div class="m-sub">No prompt at this stage.</div>'}</div>
      <div><h4>What came back</h4>${out}</div></div>`;
  }

  // ================================================================ PAID
  function drawPaid() {
    $('q').placeholder = 'Search every ad — headlines, copy, advertisers';
    for (const id of ['lanes', 'shapes']) $(id).hidden = true;
    $('dropped').hidden = true; $('grid').hidden = false; $('chainbox').hidden = true;
    if (!ADS) { $('stats').textContent = 'Loading ads…'; $('grid').innerHTML = '<div class="m-empty">Loading ads…</div>'; $('more').hidden = true; return; }
    const A = {}; S.advertisers.forEach(a => A[a.id] = a);
    $('stats').textContent = `${S.advertisers.length} advertisers · ${ADS.length.toLocaleString()} ads · ${S.updated}`;
    // brands: ours, by the competitors each one names; General = named by none
    const bl = [...new Set(S.advertisers.flatMap(a => a.brands))].sort((x, y) => (x == 'general') - (y == 'general') || x.localeCompare(y));
    chips($('brands'), [['all', 'All brands'], ...bl.map(b => [b, UP(b)])], brand, v => { brand = v; feed = 'all'; adv = 'all'; });
    const people = S.feeds.filter(f => f.brand != 'general');
    const fbr = f => f.brand;
    const advOf = b => S.advertisers.filter(a => b == 'all' || a.brands.includes(b)).map(a => a.id);
    if (feed != 'all' && !people.some(f => f.id == feed)) feed = 'all';
    const pf = people.find(f => f.id == feed);
    const scope = pf ? fbr(pf) : brand;
    const inScope = new Set(advOf(scope));
    const inBrand = people.filter(f => brand == 'all' || fbr(f) == brand);
    const countFor = f => ADS.filter(r => advOf(fbr(f)).includes(r.adv)).length;
    mountPicker(brand == 'general' ? [] : inBrand, countFor,
                v => { feed = v; adv = 'all'; shown = PAGE; draw(); });
    if (brand == 'general') {       // competitors none of our brands name
      $('avatarbtn').querySelector('.cur').textContent = 'No avatars here';
      $('avatarbtn').querySelector('.cnt').textContent = '';
    }
    if (adv != 'all' && !inScope.has(adv)) adv = 'all';
    $('advsel').hidden = false;
    $('advsel').innerHTML = `<option value="all">All advertisers</option>` + S.advertisers.filter(a => inScope.has(a.id)).map(a =>
      `<option value="${esc(a.id)}" ${adv == a.id ? 'selected' : ''}>${esc(a.name)} (${a.ads})</option>`).join('');
    $('advsel').onchange = () => { adv = $('advsel').value; shown = PAGE; draw(); };
    chips($('plats'), [['all', 'All'], ['video', 'Video'], ['image', 'Image']], kind, v => kind = v);
    $('plats').hidden = false;
    chips($('wins'), WINS, win, v => win = v);
    $('sortsel').innerHTML = PSORTS.map(([v, l]) => `<option value="${v}" ${v == sort ? 'selected' : ''}>Sort: ${l}</option>`).join('');
    $('sortsel').onchange = () => { sort = $('sortsel').value; shown = PAGE; draw(); };

    const names = [...inScope].map(id => A[id].name).join(', ');
    $('feedhead').innerHTML = pf ? `<div class="m-ask">${esc(pf.title)}${pf.line ? ' — ' + esc(pf.line) : ''}</div>Ads from the competitors ${esc(UP(pf.brand))} names: ${esc(names)}.`
      : brand != 'all' ? (brand == 'general' ? `Competitors none of our brands name: ${esc(names)}.` : `${esc(UP(brand))} — the competitors it names: ${esc(names)}.`) : '';
    $('feedhead').innerHTML += ` <a class="m-chip" href="/feeds/examples/${adv != 'all' ? esc(adv) + '/' : ''}">${adv != 'all' ? 'Full breakdown of ' + esc(A[adv].name) + '’s ads' : 'Full breakdowns of one brand’s ads'}</a>`;

    const words = $('q').value.toLowerCase().split(/\s+/).filter(Boolean);
    let rs = ADS.filter(r => inScope.has(r.adv) && (adv == 'all' || r.adv == adv) && (kind == 'all' || (kind == 'video') == !!r.video)
      && (win == 'all' || (r.first && days(r.first) <= +win)));
    if (words.length) rs = rs.filter(r => { const hay = [A[r.adv].name, r.headline, r.copy].join(' ').toLowerCase(); return words.every(w => hay.includes(w)); });
    const key = {days: r => [r.days || 0, r.copies], new: r => [r.first ? day(r.first).getTime() : 0, r.days || 0], copies: r => [r.copies, r.days || 0]}[sort];
    rs.sort((a, b) => { const x = key(a), y = key(b); return y[0] - x[0] || y[1] - x[1]; });
    $('grid').innerHTML = rs.length ? rs.slice(0, shown).map((r, i) => `<div class="m-card"><a class="m-thumb" href="${esc(r.url)}" target="_blank" rel="noopener">
      ${r.thumb ? `<img loading="lazy" alt="" src="${DATA}thumbs/${esc(r.id)}.webp" onerror="this.remove()">` : ''}
      <span class="m-pb">${r.video ? 'VIDEO AD' : 'IMAGE AD'}</span></a>
      <div class="m-body"><div class="m-author">${esc(A[r.adv].name)}</div>
      ${r.headline ? `<div class="m-what">${esc(r.headline)}</div>` : ''}<div class="m-cap">${esc(r.copy)}</div>
      <div class="m-stats">${stat(r.days, 'days running')}${stat(r.copies, 'copies')}</div>
      <div class="m-meta">${[r.first ? 'started ' + mdy(r.first) : '', r.last ? 'last seen ' + md(r.last) : ''].filter(Boolean).join(' · ')}</div>
      <div class="m-acts"><a href="${esc(r.url)}" target="_blank" rel="noopener">Open</a><button data-i="${i}">Make your own</button></div></div></div>`).join('')
      : `<div class="m-empty">Nothing matches.</div>`;
    $('more').hidden = rs.length <= shown;
    $('grid')._list = rs;
  }

  // ================================================================ the side panel
  function whoFor(c) {
    const f = S.feeds.find(x => x.id == (t == 'paid' ? feed : c.feed)) || S.feeds.find(x => x.id == feed);
    if (f && f.brand != 'general') return `${f.title}${f.line ? ' — ' + f.line : f.whose ? ' — ' + f.whose : ''} (${UP(f.brand)})`;
    if (c.brand_fit && c.brand_fit != 'general') return `a ${UP(c.brand_fit)} customer`;
    if (t == 'paid' && brand != 'all' && brand != 'general') return `a ${UP(brand)} customer`;
    return 'pick the brand and the person before you run it';
  }
  function prompt(c) {
    if (t == 'paid') return ['Take this ad apart and write a brief from it.', '',
      `Ad: ${c.url}`, `Brand running it: ${S.advertisers.find(a => a.id == c.adv)?.name || ''}`, c.headline ? `Headline: ${c.headline}` : null,
      `Who it's for: ${whoFor(c)}`, '',
      `Use ${c.video ? 'tools/video-teardown' : 'tools/image-teardown'} in the Prizm Labs repo (https://github.com/daemnapps/prizm-labs). ` +
      "Take the ad apart, then write the brief for that person. Copy the structure, not the words. Don't invent anything."].filter(x => x !== null).join('\n');
    return ['Take this post apart and write a brief from it.', '',
      `Post: ${c.url}`, `Who it's for: ${whoFor(c)}`, '',
      `Use ${c.pic ? 'tools/image-teardown' : 'tools/video-teardown (or tools/image-teardown if it is a picture)'} in the Prizm Labs repo (https://github.com/daemnapps/prizm-labs). ` +
      "Take the post apart, then write the brief for that person. Copy the structure, not the words. Don't invent anything."].join('\n');
  }
  function mdown(src) {
    const out = [], L = esc(src).split('\n');
    const inl = s => s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/(^|\s)\*(\S.+?)\*/g, '$1<em>$2</em>').replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    for (let i = 0; i < L.length; i++) {
      const l = L[i];
      if (/^```/.test(l)) { const b = []; while (++i < L.length && !/^```/.test(L[i])) b.push(L[i]); out.push(`<pre>${b.join('\n')}</pre>`); }
      else if (/^#{1,3} /.test(l)) { const n = l.match(/^#+/)[0].length + 1; out.push(`<h${n}>${inl(l.replace(/^#+ /, ''))}</h${n}>`); }
      else if (/^\|/.test(l)) { const tb = []; while (i < L.length && /^\|/.test(L[i])) tb.push(L[i++]); i--;
        out.push('<div class="tablewrap"><table>' + tb.filter(x => !/^\|[\s|:-]+\|$/.test(x)).map((x, j) =>
          '<tr>' + x.replace(/^\||\|$/g, '').split('|').map(c => j ? `<td>${inl(c.trim())}</td>` : `<th>${inl(c.trim())}</th>`).join('') + '</tr>').join('') + '</table></div>'); }
      else if (/^\s*[-*] /.test(l)) { const ul = []; while (i < L.length && /^\s*[-*] /.test(L[i])) ul.push(`<li>${inl(L[i++].replace(/^\s*[-*] /, ''))}</li>`); i--; out.push(`<ul>${ul.join('')}</ul>`); }
      else if (l.trim()) out.push(`<p>${inl(l)}</p>`);
    }
    return out.join('');
  }
  function openPanel(html) {
    const s = $('panel');
    s.innerHTML = `<button class="btn ghost x" id="x">Close</button>` + html;
    s.hidden = false; $('scrim').hidden = false; s.scrollTop = 0;
    $('x').onclick = closePanel;
  }
  function closePanel() { $('panel').hidden = true; $('scrim').hidden = true; }

  async function openCard(c, toSheet) {
    const p = prompt(c), paid = t == 'paid';
    const claude = 'https://claude.ai/new?q=' + encodeURIComponent(p);
    const where = paid ? 'the Meta Ad Library' : (PLATN[c.platform] || 'the app');
    const stat = paid ? [c.days ? `Running ${c.days} days` : '', `${c.copies.toLocaleString()} cop${c.copies == 1 ? 'y' : 'ies'}`].filter(Boolean).join(' · ')
      : [PLATN[c.platform], c.views ? fmt(c.views) + ' views' : '', c.likes ? fmt(c.likes) + ' likes' : ''].filter(Boolean).join(' · ');
    const head = paid ? `<p class="label hue">${esc(S.advertisers.find(a => a.id == c.adv)?.name)}</p><h3>${esc(c.headline || 'An ad')}</h3><p>${esc(c.copy)}</p>`
      : `<p class="label hue">@${esc(c.author)}</p><h3>${esc(c.what || 'A post')}</h3><p>${esc(c.caption)}</p>`;
    openPanel(`<p class="eyebrow">${esc(stat)}</p>${head}
      ${c.thumb ? `<img class="cover" src="${DATA}thumbs/${esc(c.id)}.webp" alt="">` : ''}
      <h2>1 · Watch it</h2><p><a class="btn ghost" href="${esc(c.url)}" target="_blank" rel="noopener">Watch it on ${esc(where)}</a></p>
      ${c.frames ? `<img class="frames" src="${DATA}thumbs/${esc(c.id)}-frames.webp" alt="Six moments from the video, left to right">` : ''}
      <h2 id="builthead">2 · How it's built</h2><div id="built">${c.sheet ? '<p>Loading…</p>' : c.frames ? '<p>No written sheet for this one yet — the six frames above are the rebuild material. The prompt below takes it apart.</p>' : '<p>Not taken apart yet. The prompt below does it.</p>'}</div>
      <h2>3 · Make your own</h2>
      <div class="btns"><a class="btn" href="${esc(claude)}" target="_blank" rel="noopener">Open in Claude</a>
      <button class="btn ghost" id="copy">Copy the prompt</button></div>
      <ol class="steps">
        <li><div><b>Press a button</b><p>Open in Claude, or Copy the prompt.</p></div></li>
        <li><div><b>Open your tool</b><p>Your Higgsfield Supercomputer, or Claude Code with the Prizm Labs repo.</p></div></li>
        <li><div><b>Paste and press Enter</b><p>It takes the ${paid ? 'ad' : 'post'} apart and writes the brief.</p></div></li>
      </ol>
      <details><summary>See the prompt</summary><pre>${esc(p)}</pre></details>`);
    $('copy').onclick = async () => {
      try { await navigator.clipboard.writeText(p); $('copy').textContent = 'Copied — now paste it'; }
      catch { $('copy').textContent = 'Press and hold the prompt below to copy'; $('panel').querySelector('details').open = true; }
    };
    if (toSheet) $('builthead').scrollIntoView();
    if (c.sheet) {
      const d = await get(`sheets/${c.id}.json`);
      $('built').innerHTML = d && d.text ? `<div class="brief">${mdown(d.text)}</div>` : '<p>Not taken apart yet. The prompt below does it.</p>';
      if (toSheet) $('builthead').scrollIntoView();
    }
  }

  function openFormats() {
    const F = S.formats || [];
    openPanel(`<p class="eyebrow">${F.length} formats</p><h2>Format library</h2>
      <p>The structures behind organic posts that work — camera, text, beat order, what carries it. Never the topic. Strongest evidence first.</p>` +
      F.map(f => `<div class="m-fm"><h3>${esc(f.name)}</h3>
        <p class="m-meta">${esc(f.status || '')} · ${f.posts < 2 ? `${f.posts} post — seen once, not proven` : `${f.posts} posts behind it`}${f.best ? ` · ${f.best.toLocaleString()} views at best` : ''}${f.text_mechanic ? ' · ' + esc(f.text_mechanic) : ''}</p>
        <p>${esc(f.mechanic)}</p>${f.why_it_works ? `<p><b>Why it works.</b> ${esc(f.why_it_works)}</p>` : ''}
        ${(f.beats || []).length ? `<ol>${f.beats.map(b => `<li>${esc(b)}</li>`).join('')}</ol>` : ''}
        ${f.proof ? `<p class="m-why">${f.proof.url ? `Proved by <a href="${esc(f.proof.url)}" target="_blank" rel="noopener">@${esc(f.proof.author)}</a>` : esc(f.proof.author)}${f.proof.line ? ` — “${esc(f.proof.line)}”` : ''}</p>` : ''}</div>`).join(''));
  }
  function openSounds() {
    const R = S.sounds || [];
    openPanel(`<p class="eyebrow">${R.length} sounds</p><h2>Trending sounds</h2><p>This week's trending TikTok sounds, recent only. Press play to hear one; tap the name to see the posts using it.</p>` +
      (R.length ? `<div class="tablewrap"><table><tr><th>#</th><th>sound</th><th>feel</th><th>length</th></tr>${R.map(r => `<tr><td>${r.rank ?? ''}</td>
        <td><a href="${esc(r.url)}" target="_blank" rel="noopener"><b>${esc(r.title)}</b></a><br><span class="m-sub">${esc(r.artist || '')}</span>${r.use ? `<br><span class="m-why">${esc(r.use)}</span>` : ''}${r.audio ? `<audio controls preload="none" src="${DATA}${esc(r.audio)}" style="display:block;width:100%;max-width:320px;height:32px;margin-top:6px"></audio>` : ''}</td>
        <td>${esc([r.mood, r.energy && r.energy + ' energy', r.bpm && r.bpm + ' bpm'].filter(Boolean).join(' · '))}</td><td>${r.seconds ? r.seconds + 's' : ''}</td></tr>`).join('')}</table></div>` : '<p>No sounds pulled yet.</p>'));
  }

  // ================================================================ wiring
  const cache = {};
  function get(path) {
    if (!cache[path]) cache[path] = fetch(DATA + path, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);
    return cache[path];
  }
  async function loadAds() { ADS = (await get('ads.json')) || []; draw(); }

  $('grid').addEventListener('click', e => {
    const b = e.target.closest('button[data-i]');
    if (b) openCard($('grid')._list[+b.dataset.i], !!b.dataset.sheet);
  });
  $('more').onclick = () => { shown += PAGE; draw(); };
  $('scrim').onclick = closePanel;
  document.addEventListener('keydown', e => { if (e.key == 'Escape') closePanel(); });
  let qt; $('q').oninput = () => { clearTimeout(qt); qt = setTimeout(() => { shown = PAGE; draw(); }, 120); };
  $('dropped').onclick = () => { showOut = !showOut; shown = PAGE; draw(); };
  $('formatsbtn').onclick = openFormats;
  $('soundsbtn').onclick = openSounds;

  (async () => {
    S = await get('index.json');
    if (!S) { $('stats').textContent = 'Could not load the feeds.'; return; }
    $('prompts').innerHTML = Object.entries(S.prompts || {}).map(([n, tx]) => `<h4>${esc(n)}</h4><pre>${esc(tx)}</pre>`).join('');
    if (t == 'paid') loadAds();
    const lists = await Promise.all(S.feeds.map(f => get(`cards/${f.id}.json`)));
    CARDS = lists.flatMap(l => l || []);
    CARDS.forEach(c => { c.age = days(c.posted); c.seen_days = days(c.seen); });
    draw();
  })();
})();
