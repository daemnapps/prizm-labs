/* The ad factory: one ad riding the line, station by station.
   Every stop shown here happened on this ad, and each one is now a rule the line enforces. */
(() => {
  const M = 'm/';
  const VS = ['control', 'g01-h2', 'g01-h3', 'g01-h4', 'g01-h5', 'g01-h6'];
  const NAMES = ['Kerri', 'Doctor 1', 'Doctor 2', 'Doctor 3'];
  const POST = 'Two doctors said bleach or laser for the dark spots on her face. The third handed her a Thai turmeric scrub. Our family recipe of turmeric, moringa, ginger and chamomile. 60 seconds, once or twice a week.';
  const S = [
    { n: 'Swipe', i: 'search', h: 'violet', big: [1, 'winner pulled'], scr: { vid: 'swipe.mp4', poster: 'swipe.jpg', sound: true },
      chips: ['3 experts', '3 answers', 'the turn on #3'],
      ev: [['ok', 'Found in the feed, already working'], ['ok', 'Filed by its format']] },
    { n: 'Teardown', i: 'scissors', h: 'violet', big: [5, 'beats kept'], scr: { grid: ['sw-1', 'sw-2', 'sw-3', 'sw-4', 'sw-5', 'sw-6', 'sw-7', 'sw-8', 'sw-9'] },
      chips: ['visit 1', 'visit 2', 'visit 3', 'the turn', 'the close'],
      ev: [['ok', 'Their brand stripped out'], ['ok', 'The shape locked']] },
    { n: 'Brief', i: 'pen', h: 'magenta', big: [40, 'lines written'], scr: { pairs: [['sw-1', 'p-s1-f1'], ['sw-5', 'p-s8-f1'], ['sw-7', 'p-s21-f1']] },
      chips: ['brief 0286', '22 scenes', 'Kerri, 64', 'brown spots'],
      ev: [['ok', 'Our product goes in'], ['ok', 'Every line from real customer words']] },
    { n: 'Cast', i: 'user', h: 'cyan', big: [4, 'people made'], scr: { img: 'cast-doctors.jpg' }, hud: { people: 4 },
      ev: [['ok', 'Built from real reference photos'], ['ok', 'Faces locked for every scene']] },
    { n: 'Pictures', i: 'image', h: 'cyan', big: [22, 'pictures'], hud: { pics: 22 },
      scr: { grid: ['p-s1-f1', 'p-s6-f1', 'p-s8-f1', 'p-s16-f1', 'p-s2-f1', 'p-s21-f1', 'p-s26-f1', 'p-s34-f1', 'p-s40-f1', 'p-s41-f1', 'p-s42-f1', 'cover-g01-h4'] },
      ev: [['ok', 'One locked picture per scene'], ['ok', 'Product checked against its real shape']] },
    { n: 'Clips', i: 'video', h: 'cyan', big: [29, 'talking clips'], scr: { vid: 'turn.mp4' }, hud: { clips: 29 },
      ev: [['ok', 'Each clip starts from its picture'], ['ok', 'No copies of copies, so faces hold']] },
    { n: 'Voices', i: 'chat', h: 'cyan', big: [4, 'voices'], scr: { faces: ['kerri', 'doc1', 'doc2', 'doc3'] },
      chips: ['Kerri', 'Doctor 1', 'Doctor 2', 'Doctor 3'],
      ev: [['ok', 'One cloned voice per person'], ['ok', 'Mm-hmms on their own track']] },
    { n: 'Edit', i: 'film', h: 'cyan', big: [6, 'versions cut'], scr: { img: 'turn.jpg' }, hud: { versions: 6 },
      ev: [['ok', 'Every line at its real length'],
           ['stop', 'Her mouth moves on someone else’s voice'], ['fix', 'Covered with a close-up'],
           ['stop', 'A word cut off: “Guaranteed”'], ['fix', 'Re-voiced, heard back whole'],
           ['stop', 'Music stops before the end'], ['fix', 'Music under the whole ad'],
           ['ok', 'Lips within 1 frame of the voice'], ['ok', 'No dead air, no black frames']] },
    { n: 'Covers', i: 'sparkles', h: 'magenta', big: [6, 'covers'], scr: { img: 'scene-read.jpg' },
      ev: [['ok', 'Reads faces, lips, hands'], ['stop', 'The words land on her face'],
           ['fix', 'Moved to the clear spot', 'cover-g01-h5.jpg'], ['ok', 'One cover per version']] },
    { n: 'Words', i: 'clipboard', h: 'magenta', big: [3, 'post texts'], scr: { post: true },
      chips: ['The third option wasn’t bleach', 'A scrub, not a laser'],
      ev: [['ok', 'Built on our best ad’s copy'], ['stop', 'A price the site doesn’t show'], ['fix', 'Taken out'], ['ok', '2 headlines, 2 descriptions']] },
    { n: 'Pack', i: 'folder', h: 'amber', big: [10, 'checks green'], scr: { files: VS },
      chips: ['6 videos', '6 covers', 'words', 'landing page', '9:16'],
      ev: [['ok', 'Named to the standard'], ['ok', 'Filed in one folder'], ['ok', 'Waiting for your click']] },
    { n: 'Approve', i: 'check', h: 'amber', wait: true, big: [1, 'click'], scr: { img: 'cover-control.jpg' },
      ev: [['ok', 'Approved']] },
    { n: 'Meta', i: 'send', h: 'indigo', big: [1, 'flexible ad'], scr: { meta: true },
      ev: [['ok', 'Campaign found or made'], ['ok', 'Ad set made'], ['ok', '6 videos + 6 covers in one ad'], ['ok', 'All paused, nothing spends yet']] },
    { n: 'Live', i: 'loop', h: 'green', big: [6, 'openings tested'],
      scr: { wall: VS },
      ev: [['ok', 'Meta shows each person the opening that holds them'], ['ok', 'Numbers read back'], ['ok', 'The winner feeds the next swipe']] },
  ];

  const root = document.getElementById('factory');
  if (!root) return;
  const ic = n => (window.studioIcon ? window.studioIcon(n) : '');
  const $ = s => root.querySelector(s);
  const hudKeys = [['pics', 'pictures'], ['clips', 'clips'], ['versions', 'versions'], ['checks', 'checks passed'], ['stops', 'stops caught']];

  root.innerHTML = `
    <div class="fx-hud">${hudKeys.map(([k, l]) => `<div><b data-h="${k}">0</b><span>${l}</span></div>`).join('')}</div>
    <div class="fx-belt"><div class="fx-track">
      <div class="fx-crate" aria-hidden="true">AD</div>
      ${S.map((s, i) => `<button class="fx-st" data-n="${i}" style="--hue:var(--${s.h})" aria-label="${s.n}">
        <span class="fx-led"></span><i class="ib">${ic(s.i)}</i><b>${i + 1} · ${s.n}</b></button>`).join('')}
    </div></div>
    <div class="fx-ctl"><button class="go" data-a="run">▶ Run the factory</button><button data-a="speed">Speed 1×</button><span class="fx-k" data-a="hint">or tap any station</span></div>
    <div class="fx-mon" style="--hue:var(--violet)"><div class="fx-scr"></div><div class="fx-out"></div></div>`;

  const sts = [...root.querySelectorAll('.fx-st')];
  const crate = $('.fx-crate'), belt = $('.fx-belt'), scr = $('.fx-scr'), out = $('.fx-out'), mon = $('.fx-mon');
  const runBtn = $('[data-a=run]'), spdBtn = $('[data-a=speed]');
  let speed = 1, token = 0, hud = {};
  const wait = ms => new Promise(r => setTimeout(r, ms / speed));
  const setHud = (k, v) => { hud[k] = v; const el = root.querySelector(`[data-h=${k}]`); if (el) el.textContent = v; };
  const bump = k => setHud(k, (hud[k] || 0) + 1);

  function count(el, to) {
    const t0 = performance.now(), d = 700 / speed;
    const f = t => { const p = Math.min(1, (t - t0) / d); el.textContent = Math.round(to * p); if (p < 1) requestAnimationFrame(f); };
    requestAnimationFrame(f);
  }

  function screen(s) {
    const c = s.scr || {};
    if (c.img) scr.innerHTML = `<img src="${M}${c.img}" alt="">`;
    else if (c.vid) scr.innerHTML = `<video src="${M}${c.vid}"${c.poster ? ` poster="${M}${c.poster}"` : ''} muted autoplay loop playsinline${c.sound ? ' controls' : ''}></video>`;
    else if (c.pairs) scr.innerHTML = `<div class="fx-pairs">${c.pairs.map(([a, b], k) => `<figure style="animation-delay:${k * 160}ms"><img src="${M}${a}.jpg" alt=""><span class="fx-tag">Swipe</span></figure><figure style="animation-delay:${k * 160 + 80}ms"><img src="${M}${b}.jpg" alt=""><span class="fx-tag ours">Ours</span></figure>`).join('')}</div>`;
    else if (c.faces) scr.innerHTML = `<div class="fx-faces">${c.faces.map((f, k) => `<figure style="animation-delay:${k * 120}ms"><img src="${M}face-${f}.jpg" alt="${NAMES[k]}"><span class="fx-bars"><i></i><i></i><i></i><i></i><i></i></span><span class="fx-k">${NAMES[k]}</span></figure>`).join('')}</div>`;
    else if (c.post) scr.innerHTML = `<div class="fx-post"><header><i></i><div><b>Pasnida</b><span>Sponsored</span></div></header><p>${POST}</p><video src="${M}open-control.mp4" poster="${M}cover-control.jpg" muted autoplay loop playsinline></video><footer><b>The third option wasn’t bleach</b><em>Shop now</em></footer></div>`;
    else if (c.files) scr.innerHTML = `<div class="fx-files">${c.files.map((v, k) => `<figure style="animation-delay:${k * 110}ms"><img src="${M}cover-${v}.jpg" alt=""><span class="fx-tag">✓ ▶</span><figcaption>asset-0${k + 1}.mp4</figcaption></figure>`).join('')}</div>`;
    else if (c.wall) scr.innerHTML = `<div class="fx-files">${c.wall.map((v, k) => `<figure style="animation-delay:${k * 110}ms"><img src="${M}cover-${v}.jpg" alt=""><span class="fx-tag live">● live</span><figcaption>opening ${k + 1}</figcaption></figure>`).join('')}</div>`;
    else if (c.grid) scr.innerHTML = `<div class="fx-grid" style="grid-template-columns:repeat(${c.grid.length <= 9 ? 3 : 4},1fr)">${c.grid.map((g, k) => `<img src="${M}${g}.jpg" alt="" style="animation-delay:${k * 60}ms">`).join('')}</div>`;
    else if (c.meta) scr.innerHTML = `<div class="fx-nest"></div>`;
    else scr.innerHTML = `<i class="ib lg" style="width:96px;height:96px;padding:22px;--hue:var(--${s.h})">${ic(c.icon)}</i>`;
  }

  function show(i, instant) {
    const s = S[i];
    mon.style.setProperty('--hue', `var(--${s.h})`);
    screen(s);
    out.innerHTML = `<span class="fx-k">Station ${i + 1} of ${S.length}</span><h3>${s.n}</h3>
      <div class="fx-big">0</div><span class="fx-k">${s.big[1]}</span>
      ${s.chips ? `<div class="fx-chips">${s.chips.map((c, k) => `<span style="animation-delay:${k * 80}ms">${c}</span>`).join('')}</div>` : ''}
      <ul class="fx-ev"></ul>`;
    const big = out.querySelector('.fx-big');
    if (instant) { big.textContent = s.big[0]; s.ev.forEach(e => addEv(s, e)); } else count(big, s.big[0]);
  }

  function addEv(s, e) {
    const [kind, text, img] = e;
    const li = document.createElement('li');
    if (kind === 'stop') li.className = 'stop';
    li.innerHTML = `<span class="fx-led ${kind === 'stop' ? 'stop' : 'ok'}"></span>${kind === 'stop' ? '<b>STOP</b>&nbsp;' : kind === 'fix' ? '↳ ' : ''}${text}`;
    out.querySelector('.fx-ev').appendChild(li);
    if (img) scr.innerHTML = `<img src="${M}${img}" alt="">`;
    if (s.scr && s.scr.meta && kind === 'ok') nest(scr.querySelector('.fx-nest'));
  }

  function nest(box) {
    if (!box) return;
    let inner = box; while (inner.lastElementChild && inner.lastElementChild.tagName === 'DIV') inner = inner.lastElementChild;
    const depth = box.querySelectorAll('div').length;
    const lv = [['indigo', 'Campaign'], ['violet', 'Ad set'], ['green', 'Ad · flexible'], ['amber', 'Paused']][depth];
    if (!lv) return;
    if (lv[1] === 'Paused') { box.firstElementChild.insertAdjacentHTML('afterbegin', `<span class="pill" style="--hue:var(--amber)">paused</span>`); return; }
    inner.insertAdjacentHTML('beforeend', `<div style="--hue:var(--${lv[0]})"><span class="fx-k">${lv[1]}</span>${lv[1].startsWith('Ad ·') ? `<span class="row">${VS.map(v => `<img src="${M}cover-${v}.jpg" alt="">`).join('')}</span>` : ''}</div>`);
  }

  function moveTo(i) {
    const st = sts[i];
    crate.style.left = st.offsetLeft + 'px';
    belt.scrollTo({ left: st.offsetLeft - belt.clientWidth / 2 + st.offsetWidth / 2, behavior: 'smooth' });
  }

  function reset() {
    sts.forEach(b => b.className = 'fx-st');
    hudKeys.forEach(([k]) => setHud(k, 0));
    root.classList.remove('is-on');
  }

  async function run() {
    const me = ++token;
    reset();
    root.classList.add('is-on');
    runBtn.textContent = '■ Stop'; runBtn.dataset.a = 'halt';
    for (let i = 0; i < S.length; i++) {
      if (me !== token) return;
      const s = S[i], st = sts[i];
      moveTo(i);
      await wait(700);
      st.classList.add('is-run');
      show(i);
      if (s.hud) Object.entries(s.hud).forEach(([k, v]) => k in hud && setHud(k, v));
      if (s.wait) {
        st.classList.remove('is-run'); st.classList.add('is-wait');
        root.classList.remove('is-on');
        out.querySelector('.fx-ev').insertAdjacentHTML('beforebegin', `<div class="fx-ctl"><button class="approve" data-a="approve">✓ Approve</button></div>`);
        await new Promise(r => { root.querySelector('[data-a=approve]').onclick = r; });
        if (me !== token) return;
        out.querySelector('[data-a=approve]').parentNode.remove();
        root.classList.add('is-on');
        st.classList.remove('is-wait');
      }
      for (const e of s.ev) {
        await wait(e[0] === 'stop' ? 650 : 520);
        if (me !== token) return;
        if (e[0] === 'stop') { st.classList.remove('is-run'); st.classList.add('is-stop'); root.classList.remove('is-on'); bump('stops'); }
        if (e[0] === 'fix') { await wait(500); st.classList.remove('is-stop'); st.classList.add('is-run'); root.classList.add('is-on'); }
        if (e[0] !== 'stop') bump('checks');
        addEv(s, e);
      }
      await wait(600);
      st.classList.remove('is-run', 'is-stop'); st.classList.add('is-done');
    }
    root.classList.remove('is-on');
    runBtn.textContent = '↻ Run the next ad'; runBtn.dataset.a = 'run';
  }

  root.addEventListener('click', e => {
    const a = e.target.closest('[data-a]'), st = e.target.closest('.fx-st');
    if (a && a.dataset.a === 'run') run();
    else if (a && a.dataset.a === 'halt') { token++; reset(); runBtn.textContent = '▶ Run the factory'; runBtn.dataset.a = 'run'; }
    else if (a && a.dataset.a === 'speed') { speed = speed === 1 ? 2 : speed === 2 ? 4 : 1; spdBtn.textContent = `Speed ${speed}×`; }
    else if (st && runBtn.dataset.a === 'run') {
      sts.forEach(b => b.classList.remove('is-pick')); st.classList.add('is-pick');
      const i = +st.dataset.n; moveTo(i); show(i, true);
    }
  });

  show(0, true);
  moveTo(0);
})();
