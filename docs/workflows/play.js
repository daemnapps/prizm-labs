/* Chat vs. Workflow: the race, the line, the ladder.
   Workflow stage times are the medians from /machine.html. Chat times are estimates, and the page says so. */
(() => {
  const M = '/three-doctors/m/';
  const ic = n => (window.studioIcon ? window.studioIcon(n) : '');
  const CALM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const wait = ms => new Promise(r => setTimeout(r, CALM ? 0 : ms));
  const hm = m => (m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`);
  const ms = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  /* ── 01 · the race ─────────────────────────────────────────────────── */
  const CHAT = [
    { i: 'video', t: 'Upload the video and describe it', p: 'It can only skim a long video, so you write out what happens in it.', m: 8 },
    { i: 'list', t: 'Ask for a scene-by-scene breakdown', p: 'You compare it to the video and find the gaps.', m: 12, tag: ['stop', 'missed 3 scenes'] },
    { i: 'user', t: 'Explain your brand and product', p: 'Who buys it, what it does, what you can and can’t say.', m: 10, again: 1 },
    { i: 'pen', t: 'Ask it to rewrite the ad for your product', p: 'It reads well. One of the customer quotes is made up.', m: 6, tag: ['stop', 'invented a quote'] },
    { i: 'clipboard', t: 'Paste in real customer reviews', p: 'Copied from your store, one by one.', m: 15 },
    { i: 'sparkles', t: 'Ask for six different openings', p: 'Three of them are the same idea in new words.', m: 8 },
    { i: 'chat', t: 'Start a new chat, it’s forgetting things', p: 'The conversation got long. Explain the brand again.', m: 10, again: 1, tag: ['wait', 're-explained'] },
    { i: 'film', t: 'Ask for a shot list', p: 'Scene by scene, so someone can film it.', m: 12 },
    { i: 'shield', t: 'Check every claim yourself', p: 'One line promises a result you’re not allowed to promise.', m: 15, tag: ['stop', 'risky claim'] },
    { i: 'page', t: 'Copy it all into a doc and tidy it up', p: 'Fix the formatting, name the file, send it on.', m: 20 },
  ];
  const FLOW = [
    { i: 'search', t: 'Triage', p: 'Is this even an ad worth copying?', s: 25 },
    { i: 'eye', t: 'Read it frame by frame', p: 'Every scene, every word on screen, every cut.', s: 485 },
    { i: 'layers', t: 'Pull out the structure', p: 'The shape that made it work, with their brand stripped out.', s: 797 },
    { i: 'folder', t: 'Put your brand in', p: 'Your product and your customers’ own words, read from the brand folder.', s: 157 },
    { i: 'sparkles', t: 'Write six openings and the close', p: 'Each one checked so they are really different.', s: 999 },
    { i: 'pen', t: 'Write the brief', p: 'Scene by scene, written for a person to shoot.', s: 271 },
    { i: 'check', t: 'Shot list and what we learned', p: 'Filed with its number, ready for the next tool.', s: 155 },
  ];

  const chat = document.getElementById('chat'), flow = document.getElementById('flow'), verdict = document.getElementById('verdict');
  if (chat && flow) {
    const set = (root, k, v) => { root.querySelector(`[data-k=${k}]`).textContent = v; };
    const row = (feed, i, t, p, right, tag) => {
      const li = document.createElement('li');
      li.innerHTML = `<i class="ib">${ic(i)}</i><div><b>${t}</b><p>${p}</p>${tag ? `<span class="pill ${tag[0]}">${tag[1]}</span>` : ''}</div><span class="t">${right}</span>`;
      feed.appendChild(li); feed.scrollTop = feed.scrollHeight;
    };
    const cFeed = chat.querySelector('.feed'), fFeed = flow.querySelector('.feed');
    const sendBtn = chat.querySelector('[data-a=send]'), runBtn = flow.querySelector('[data-a=run]');
    let c = { n: 0, min: 0, again: 0, done: false }, f = { done: false, running: false };

    function judge() {
      if (!(c.done && f.done)) return;
      verdict.hidden = false;
      verdict.innerHTML = `<p class="label">The result</p><p>The chat way took <b>${hm(c.min)}</b> of your time, ${c.n} messages, and you caught 3 mistakes yourself.
        The workflow took <b>one click</b>. The machine worked for 48 minutes while you did something else, and the next one costs you the same single click.</p>`;
    }

    sendBtn.addEventListener('click', () => {
      if (c.done) { c = { n: 0, min: 0, again: 0, done: false }; cFeed.innerHTML = ''; verdict.hidden = true; sendBtn.textContent = 'Send the next message'; }
      const s = CHAT[c.n];
      c.n++; c.min += s.m; c.again += s.again || 0;
      row(cFeed, s.i, s.t, s.p, `+${s.m}m`, s.tag);
      set(chat, 'time', hm(c.min)); set(chat, 'msgs', c.n); set(chat, 'again', c.again);
      if (c.n === CHAT.length) {
        c.done = true; sendBtn.textContent = 'Start over';
        const li = document.createElement('li'); li.style.setProperty('--hue', 'var(--amber)');
        li.innerHTML = `<i class="ib">${ic('check')}</i><div class="done-note"><b>Brief done.</b> Next week, you do all of it again.</div><span></span>`;
        cFeed.appendChild(li); cFeed.scrollTop = cFeed.scrollHeight;
        judge();
      } else sendBtn.textContent = `Send message ${c.n + 1} of ${CHAT.length}`;
    });

    runBtn.addEventListener('click', async () => {
      if (f.running) return;
      f = { done: false, running: true }; fFeed.innerHTML = ''; verdict.hidden = true;
      runBtn.textContent = 'Running…'; runBtn.disabled = true;
      set(flow, 'you', '1 click');
      let clock = 0;
      for (let k = 0; k < FLOW.length; k++) {
        const s = FLOW[k], from = clock, to = clock + s.s, d = Math.max(350, s.s * 2.2);
        if (!CALM) {
          const t0 = performance.now();
          await new Promise(r => (function tick(t) {
            const p = Math.min(1, (t - t0) / d); set(flow, 'clock', ms(Math.round(from + (to - from) * p)));
            p < 1 ? requestAnimationFrame(tick) : r();
          })(t0));
        }
        clock = to; set(flow, 'clock', ms(clock)); set(flow, 'steps', k + 1);
        row(fFeed, s.i, s.t, s.p, ms(s.s), k === FLOW.length - 1 ? ['ready', 'brief ready'] : null);
      }
      const li = document.createElement('li'); li.style.setProperty('--hue', 'var(--green)');
      li.innerHTML = `<i class="ib">${ic('check')}</i><div class="done-note"><b>Brief done, 48m 09s, unattended.</b> It's waiting in the folder with its number on it.</div><span></span>`;
      fFeed.appendChild(li); fFeed.scrollTop = fFeed.scrollHeight;
      f = { done: true, running: false }; runBtn.disabled = false; runBtn.textContent = 'Run it again';
      judge();
    });
  }

  /* ── 03 · the line ─────────────────────────────────────────────────── */
  const COVERS = ['control', 'g01-h2', 'g01-h3', 'g01-h4', 'g01-h5', 'g01-h6'];
  const S = [
    { n: 'Swipe', i: 'search', h: 'violet', tools: ['My Feeds'], big: [6269, 'competitor ads on watch'],
      io: ['What’s already selling, paid and organic', 'One video worth copying'], scr: { img: 'swipe.jpg' },
      ev: [['ok', 'Ranked by how long it has run'], ['ok', 'Filed under its format']] },
    { n: 'Teardown', i: 'scissors', h: 'violet', tools: ['Video teardown', 'Image teardown'], big: [18, 'stages, run in order'],
      io: ['The video', 'Its structure, their brand removed'], scr: { grid: ['sw-1', 'sw-2', 'sw-3', 'sw-4', 'sw-5', 'sw-6', 'sw-7', 'sw-8', 'sw-9'] },
      ev: [['ok', 'Every scene labelled'], ['ok', 'The shape locked']] },
    { n: 'Brief', i: 'pen', h: 'magenta', tools: ['Copywriter', 'Language layer'], big: [1, 'numbered brief'],
      io: ['The structure + your brand folder', 'A brief anyone can shoot from'], scr: { pairs: [['sw-1', 'p-s1-f1'], ['sw-5', 'p-s8-f1'], ['sw-7', 'p-s21-f1']] },
      ev: [['ok', 'Your product goes in'], ['ok', 'Every line from real customer words']] },
    { n: 'Make', i: 'image', h: 'cyan', tools: ['Video production', 'Image production'], big: [22, 'pictures, one per scene'],
      io: ['The brief', 'Voices, pictures and clips'], scr: { grid: ['p-s1-f1', 'p-s6-f1', 'p-s8-f1', 'p-s16-f1', 'p-s2-f1', 'p-s21-f1', 'p-s26-f1', 'p-s34-f1', 'p-s40-f1', 'p-s41-f1', 'p-s42-f1', 'p-s9-f1'] },
      ev: [['ok', 'Faces locked for every scene'], ['ok', 'Product checked against its real shape']] },
    { n: 'Edit', i: 'film', h: 'cyan', tools: ['Video edit', 'Edit kit', 'Image edit', 'Asset index'], big: [6, 'versions cut'],
      io: ['The pieces', 'Finished, captioned videos'], scr: { vid: 'turn.mp4', poster: 'turn.jpg' },
      ev: [['ok', 'Lips within 1 frame of the voice'], ['stop', 'A word cut off'], ['fix', 'Re-voiced and checked again'], ['ok', 'No dead air, no black frames']] },
    { n: 'Hand-off', i: 'folder', h: 'amber', tools: ['Editor onboarding'], big: [10, 'checks passed'],
      io: ['Finished work', 'One folder, one instruction file'], scr: { files: COVERS, tag: '✓', cap: k => `asset-0${k + 1}.mp4` },
      ev: [['ok', 'Named to the standard'], ['ok', 'Every link opened and checked']] },
    { n: 'Your yes', i: 'check', h: 'amber', wait: true, tools: ['You'], big: [1, 'click'],
      io: ['The finished ad', 'Permission to go live'], scr: { img: 'cover-control.jpg' },
      ev: [['ok', 'Approved']] },
    { n: 'Live', i: 'loop', h: 'green', tools: ['Ad uploader', 'Klaviyo uploader'], big: [6, 'openings tested'],
      io: ['The approved ad', 'Results, read back into the next swipe'], scr: { files: COVERS, tag: '● live', live: true, cap: k => `opening ${k + 1}` },
      ev: [['ok', 'Set up in Meta'], ['ok', 'Numbers read back'], ['ok', 'The winner feeds the next run']] },
  ];

  const root = document.getElementById('factory');
  if (root) {
    root.innerHTML = `
      <div class="fx-belt"><div class="fx-track">
        <div class="fx-crate" aria-hidden="true">AD</div>
        ${S.map((s, i) => `<button class="fx-st" type="button" data-n="${i}" style="--hue:var(--${s.h})" aria-label="${s.n}">
          <span class="fx-led"></span><i class="ib">${ic(s.i)}</i><b>${i + 1} · ${s.n}</b></button>`).join('')}
      </div></div>
      <div class="fx-ctl"><button class="go" type="button" data-a="run">▶ Run the line</button><span class="fx-k" data-a="hint">or tap any station</span></div>
      <div class="fx-mon" style="--hue:var(--violet)"><div class="fx-scr"></div><div class="fx-out"></div></div>`;

    const $ = q => root.querySelector(q);
    const sts = [...root.querySelectorAll('.fx-st')];
    const crate = $('.fx-crate'), belt = $('.fx-belt'), scr = $('.fx-scr'), out = $('.fx-out'), mon = $('.fx-mon');
    const runBtn = $('[data-a=run]'), hint = $('[data-a=hint]');
    let token = 0;

    const screen = c => {
      if (c.img) scr.innerHTML = `<img src="${M}${c.img}" alt="">`;
      else if (c.vid) scr.innerHTML = `<video src="${M}${c.vid}" poster="${M}${c.poster}" muted autoplay loop playsinline></video>`;
      else if (c.grid) scr.innerHTML = `<div class="fx-grid" style="grid-template-columns:repeat(${c.grid.length <= 9 ? 3 : 4},1fr)">${c.grid.map((g, k) => `<img src="${M}${g}.jpg" alt="" style="animation-delay:${k * 60}ms">`).join('')}</div>`;
      else if (c.pairs) scr.innerHTML = `<div class="fx-pairs">${c.pairs.map(([a, b], k) => `<figure style="animation-delay:${k * 160}ms"><img src="${M}${a}.jpg" alt=""><span class="fx-tag">Theirs</span></figure><figure style="animation-delay:${k * 160 + 80}ms"><img src="${M}${b}.jpg" alt=""><span class="fx-tag ours">Ours</span></figure>`).join('')}</div>`;
      else if (c.files) scr.innerHTML = `<div class="fx-files">${c.files.map((v, k) => `<figure style="animation-delay:${k * 110}ms"><img src="${M}cover-${v}.jpg" alt=""><span class="fx-tag${c.live ? ' live' : ''}">${c.tag}</span><figcaption>${c.cap(k)}</figcaption></figure>`).join('')}</div>`;
    };

    const addEv = ([kind, text]) => {
      const li = document.createElement('li');
      if (kind === 'stop') li.className = 'stop';
      li.innerHTML = `<span class="fx-led ${kind === 'stop' ? 'stop' : 'ok'}"></span>${kind === 'stop' ? '<b>STOP</b>&nbsp;' : kind === 'fix' ? '↳ ' : ''}${text}`;
      out.querySelector('.fx-ev').appendChild(li);
    };

    const show = (i, instant) => {
      const s = S[i];
      mon.style.setProperty('--hue', `var(--${s.h})`);
      screen(s.scr);
      out.innerHTML = `<span class="fx-k">Station ${i + 1} of ${S.length}</span><h3>${s.n}</h3>
        <div class="fx-big">${s.big[0].toLocaleString('en-US')}</div><span class="fx-k">${s.big[1]}</span>
        <div class="fx-io"><span class="fx-k">In</span><span>${s.io[0]}</span><span class="fx-k">Out</span><span>${s.io[1]}</span></div>
        <div class="tools fx-chips">${s.tools.map(t => `<span>${t}</span>`).join('')}</div>
        <ul class="fx-ev"></ul>`;
      if (instant) s.ev.forEach(addEv);
    };

    const moveTo = i => {
      const st = sts[i];
      crate.style.left = st.offsetLeft + 'px';
      belt.scrollTo({ left: st.offsetLeft - belt.clientWidth / 2 + st.offsetWidth / 2, behavior: CALM ? 'auto' : 'smooth' });
    };

    const approval = () => new Promise(r => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'approve'; b.textContent = '✓ Approve it';
      runBtn.hidden = true; hint.textContent = 'The line is waiting for you';
      $('.fx-ctl').prepend(b);
      b.addEventListener('click', () => { b.remove(); runBtn.hidden = false; hint.textContent = 'or tap any station'; r(); }, { once: true });
    });

    async function run() {
      const my = ++token;
      sts.forEach(b => (b.className = 'fx-st'));
      root.classList.add('is-on'); runBtn.textContent = '■ Stop';
      for (let i = 0; i < S.length; i++) {
        const s = S[i], st = sts[i];
        moveTo(i); st.classList.add('is-run'); show(i, false);
        await wait(500); if (my !== token) return;
        if (s.wait) {
          st.classList.replace('is-run', 'is-wait'); root.classList.remove('is-on');
          await approval(); if (my !== token) return;
          root.classList.add('is-on');
        }
        for (const e of s.ev) {
          if (e[0] === 'stop') st.classList.add('is-stop');
          if (e[0] === 'fix') st.classList.remove('is-stop');
          addEv(e); await wait(e[0] === 'ok' ? 380 : 700); if (my !== token) return;
        }
        st.className = 'fx-st is-done';
      }
      root.classList.remove('is-on'); runBtn.textContent = '▶ Run it again';
    }

    runBtn.addEventListener('click', () => {
      if (root.classList.contains('is-on')) { token++; root.classList.remove('is-on'); runBtn.textContent = '▶ Run the line'; return; }
      run();
    });
    sts.forEach((b, i) => b.addEventListener('click', () => {
      if (root.querySelector('.approve')) return;
      token++; root.classList.remove('is-on'); runBtn.textContent = '▶ Run the line';
      sts.forEach(x => x.classList.remove('is-pick')); b.classList.add('is-pick');
      moveTo(i); show(i, true);
    }));
    show(0, true); requestAnimationFrame(() => moveTo(0));
  }

  /* ── 06 · the ladder ───────────────────────────────────────────────── */
  const NEXT = [
    ['Write your business down once.', 'What you sell, who buys it, how they talk, and what you never say. Keep it in one document and give it to the AI at the start of every chat. That is step 2, done by hand, and it is our brand folder in its simplest form.'],
    ['Connect the app you copy from most.', 'Your store, your inbox or your ad account. Claude and ChatGPT both connect to common tools now. Every copy and paste you stop doing is time back, and it is the first piece of a workflow.'],
    ['Chain one job you do every week.', 'Pick a task you always do the same way. Write each step as its own instruction, so step one’s answer becomes step two’s input. Add one check after each step and one stop where you say yes. That is a workflow.'],
    ['Feed the results back in.', 'You are running a machine. The next gain is the loop: what worked last week should change the next run. That is how ours gets better without anyone rewriting it by hand.'],
  ];
  const ladder = document.querySelectorAll('.ladder button'), next = document.getElementById('next');
  ladder.forEach(b => b.addEventListener('click', () => {
    ladder.forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    const [h, p] = NEXT[+b.dataset.n];
    next.innerHTML = `<p class="label">Your next move</p><h3>${h}</h3><p>${p}</p>`;
  }));
})();
