/* Marks: decide a picture from the page itself.

   Layered OVER pic-index.js, never inside it. The engine stays a read-only
   viewer of a state file; this module is the only place that knows about
   claude.ai capabilities, and it does nothing at all outside a published
   artifact (`claude.use` resolves null, so the page is exactly what it was).

   A mark is per VISUAL, not per slot: `D24` and `M24` are separate documents,
   because the desktop and the mobile renderings of one slot are different
   pictures and get judged separately. The engine already reads `state[id]`
   ahead of `state[number]`, so a mark on `D24` simply wins over whatever the
   baked state file says for `24`.

   The store is the page's working surface; `brands/<brand>/.../pic-state.json`
   in the workspace stays the record. Sync runs ONE WAY, marks -> repo, read
   back by Claude. Nothing here ever writes the repo, and a rebuild always
   starts from the repo. */
(function () {
  var WORDS = ['accepted', 'keep', 'updated', 'redo', 'replace'];
  var api = null, db = null, user = null, me = null, myName = '', writable = null;
  var marks = {};          // id -> {state, reason, by, byName, at}
  var open = null;         // the popover currently on screen

  function ready(fn) {
    if (window.PIC_INDEX_API) return fn();
    document.addEventListener('pic-index:ready', fn, { once: true });
  }

  function when(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return isNaN(d) ? '' : d.toISOString().slice(0, 10);
  }

  /* A reason typed on the page is another viewer's input and the note cards are
     drawn with innerHTML, so it is escaped here rather than trusted. */
  function esc(t) {
    return String(t == null ? '' : t)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var KIND = { redo: 'fix', replace: 'fix', accepted: 'ok', keep: 'ok', updated: 'spec' };

  /* A reason is a reason wherever it was written. One typed into the popover
     draws the same card as one curated in notes.json, so a reader never has to
     know which of the two a sentence came from. */
  function liveNotes() {
    var out = {};
    Object.keys(marks).forEach(function (id) {
      var m = marks[id];
      if (!m || !m.reason) return;
      out[id] = [{
        kind: KIND[m.state] || 'spec',
        title: esc(m.state || 'noted') + ' \u00b7 ' +
               esc(m.byName || 'someone') + (m.at ? ', ' + esc(when(m.at)) : ''),
        body: esc(m.reason)
      }];
    });
    return out;
  }

  function overrides() {
    var m = {};
    Object.keys(marks).forEach(function (id) { if (marks[id].state) m[id] = marks[id].state; });
    return m;
  }

  /* The signature rides on the badge itself, as its tooltip, so a reader who
     wants to know who decided something hovers it instead of opening a menu. */
  function label() {
    api.badges().forEach(function (b) {
      var m = marks[b.id];
      b.tag.style.pointerEvents = 'auto';
      b.tag.style.cursor = writable === false ? 'default' : 'pointer';
      if (!m) { b.tag.title = writable === false ? b.id : b.id + ' — click to mark'; return; }
      b.tag.title = b.id + ': ' + m.state +
        (m.byName ? ' — ' + m.byName : '') + (m.at ? ', ' + when(m.at) : '') +
        (m.reason ? '\n' + m.reason : '');
    });
  }

  function shut() { if (open) { open.remove(); open = null; } }

  function popover(b) {
    shut();
    var m = marks[b.id] || {};
    var el = document.createElement('div');
    el.style.cssText = 'position:absolute;z-index:100002;width:250px;background:#fff;color:#111;' +
      'font:400 13px/1.45 system-ui,-apple-system,sans-serif;border-radius:10px;padding:12px;' +
      'box-shadow:0 10px 34px rgba(0,0,0,.4);pointer-events:auto';
    var r = b.box.getBoundingClientRect();
    var x = Math.min(r.left + window.scrollX, document.documentElement.scrollWidth - 272);
    el.style.left = Math.max(10, x) + 'px';
    el.style.top = (r.top + window.scrollY + 30) + 'px';

    var head = document.createElement('div');
    head.style.cssText = 'font:700 11px/1.3 ui-monospace,Menlo,monospace;letter-spacing:.06em;' +
      'color:#666;margin-bottom:9px';
    head.textContent = b.id + (m.state ? ' · ' + m.state : ' · not decided');
    el.appendChild(head);

    if (m.byName || m.at) {
      var sig = document.createElement('div');
      sig.style.cssText = 'font-size:11.5px;color:#666;margin:-5px 0 9px';
      sig.textContent = (m.byName || 'someone') + (m.at ? ' · ' + when(m.at) : '');
      el.appendChild(sig);
    }

    var why = document.createElement('input');
    why.type = 'text';
    why.placeholder = 'why, if you have one';
    why.value = m.reason || '';
    why.id = 'pic-why-' + b.id;
    why.style.cssText = 'width:100%;box-sizing:border-box;border:1px solid #ccc;border-radius:6px;' +
      'padding:7px 8px;font:inherit;margin-bottom:9px';

    /* The word BUTTONS SELECT; one Save button commits. They used to save on
       click, which read as a toggle and cost a real reason: email_lead typed one on
       M39, looked for a send button, found none and lost it. One click saved is
       cheaper than one click; one click ambiguous is not. */
    var picked = m.state || null;
    var row = document.createElement('div');
    row.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px';
    var btns = {};
    WORDS.forEach(function (w) {
      var st = api.styles[w] || api.styles.undecided;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = w;
      btn.style.cssText = 'font:700 11.5px/1 system-ui;padding:7px 9px;border-radius:14px;cursor:pointer;' +
        'border:1px solid ' + st.bg + ';background:transparent;color:#333';
      /* No comment, no ceremony: clicking a word with the field empty saves on
         that one click, which is the whole of most marking. With something
         typed, the click only SELECTS and Save commits, so a reason can never
         be lost the way M39's was. `redo` never takes the fast path — email_lead's
         Q2 ruling says it needs a reason. */
      btn.addEventListener('click', function () {
        picked = w; repaint();
        var reason = why.value.trim();
        if (reason) { why.focus(); return; }
        if (w === 'redo') {
          el._msg.textContent = 'redo needs a reason \u2014 email_lead ruled that on 2026-09-23.';
          el._msg.style.display = 'block';
          why.focus();
          return;
        }
        write(b, w, '', el);
      });
      btns[w] = btn;
      row.appendChild(btn);
    });

    var save = document.createElement('button');
    save.type = 'button';
    save.style.cssText = 'margin-top:10px;width:100%;font:700 12px/1 system-ui;padding:9px;' +
      'border-radius:8px;border:none;cursor:pointer';

    function repaint() {
      WORDS.forEach(function (w) {
        var st = api.styles[w] || api.styles.undecided;
        btns[w].style.background = picked === w ? st.bg : 'transparent';
        btns[w].style.color = picked === w ? st.fg : '#333';
      });
      save.disabled = !picked;
      save.textContent = picked ? 'Save \u00b7 ' + picked
                                : (why.value.trim() ? 'Pick a word' : 'Pick a word to mark it');
      save.style.background = picked ? '#111' : '#e6e6e6';
      save.style.color = picked ? '#fff' : '#999';
      save.style.cursor = picked ? 'pointer' : 'default';
    }
    save.addEventListener('click', function () {
      if (picked) write(b, picked, why.value.trim(), el);
    });
    why.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && picked) { e.preventDefault(); write(b, picked, why.value.trim(), el); }
    });

    var clear = document.createElement('button');
    clear.type = 'button';
    clear.textContent = 'clear this mark';
    clear.style.cssText = 'margin-top:7px;width:100%;font:600 11.5px/1 system-ui;padding:7px;' +
      'border-radius:8px;border:1px dashed #bbb;background:transparent;color:#777;cursor:pointer';
    clear.addEventListener('click', function () { write(b, null, '', el); });

    var msg = document.createElement('div');
    msg.style.cssText = 'font-size:11.5px;color:#b00;margin-top:8px;display:none';

    el.appendChild(why); el.appendChild(row); el.appendChild(save);
    el.appendChild(clear); el.appendChild(msg);
    el._msg = msg;
    repaint();
    el.addEventListener('click', function (e) { e.stopPropagation(); });
    document.body.appendChild(el);
    open = el;
    why.focus();
  }

  function write(b, word, reason, el) {
    if (word === 'redo' && !reason) {
      el._msg.textContent = 'redo needs a reason — email_lead ruled that on 2026-09-23.';
      el._msg.style.display = 'block';
      return;
    }
    var ref = db.doc('marks/' + b.id);
    var done = function () { shut(); };
    var failed = function (e) {
      if (e && e.code === 'invalid_argument') {
        writable = false; label(); shut();
        return;
      }
      el._msg.textContent = 'could not save (' + ((e && e.code) || 'error') + ')';
      el._msg.style.display = 'block';
    };
    if (!word) { ref.delete().then(done, failed); return; }
    /* byName is stored deliberately, against the usual "ids only" rule: a
       signature is a historical fact, and it has to survive being read back by
       Claude, where a per-viewer id resolves to nothing. */
    ref.set({
      state: word,
      reason: reason || '',
      by: me || '',
      byName: myName || '',
      at: new Date().toISOString()
    }).then(done, failed);
  }

  ready(function () {
    api = window.PIC_INDEX_API;
    if (!window.claude || !window.claude.use) return;   // not an artifact: read-only, as before

    window.claude.use('db').then(function (d) {
      if (!d) return;
      db = d;

      window.claude.use('user').then(function (u) {
        user = u;
        if (!u) return;
        Promise.resolve(u.can && u.can('data.write')).then(function (w) {
          writable = w === false ? false : null; label();
        }, function () {});
        /* me() carries the id and the display name in one read. The name can
           still be "" — a declared scope is a ceiling, not a promise, and the
           viewer's organization has to allow it. When it is, the id is the
           signature and reviewers.json in the page's own folder is where it
           gets a human name. */
        Promise.resolve(u.me && u.me()).then(function (v) {
          if (!v) return;
          me = v.id || '';
          myName = v.name || '';
        }).catch(function () {});
      });

      db.collection('marks').onSnapshot(function (snap) {
        marks = {};
        snap.docs.forEach(function (doc) { marks[doc.id] = doc.data() || {}; });
        api.setOverrides(overrides());
        if (api.setLiveNotes) api.setLiveNotes(liveNotes());
        label();
      }, function () { /* terminal: the page stays on the baked state */ });

      document.addEventListener('click', shut);
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape') shut(); });

      api.badges().forEach(function (b) {
        b.tag.addEventListener('click', function (e) {
          e.stopPropagation();
          if (writable === false) return;
          popover(b);
        });
      });
      label();

      var c = document.getElementById('pic-count');
      if (c) {
        var hint = document.createElement('span');
        hint.textContent = 'click a badge to mark it';
        hint.style.cssText = 'margin-left:14px;font:400 11px/1 system-ui;color:#9a9a9a';
        c.parentNode.appendChild(hint);
      }
    });
  });
})();
