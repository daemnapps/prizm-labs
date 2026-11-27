/* Page features overlay: lettered badges over a page's own elements.

   Each number names a FEATURE from the page's features.json (v1), never a DOM
   position. The letter before it is the kind (D data, R rule, M media,
   L layout, A action), its colour is the kind, and a corner dot is the state:
   green wired, amber after-card, red not-built. Click a badge for what the
   feature is and where its data lives. A badge whose element was found by the
   version's CSS locator, not by its data-feature tag, is drawn dashed.

   Filter chips (bottom left): one group for kind, one for state, each
   multi-select with an "All" chip. A badge shows when its kind is one of the
   chosen kinds AND its state one of the chosen states; a group with nothing
   chosen, or everything, shows all.

   The overlay's own popover carries a number when the file lists it: the
   layout feature whose source is {file: components/page-features/overlay.js,
   field: "popover"}. The load-failure banner carries none: it appears only
   when no file loaded.

   READ-ONLY. This file draws and never saves, and there is no marks layer:
   feedback happens in a Claude session, by number (the filter bar says so in
   one line). The one thing it keeps is a viewer's own view (PF-2d (overlay
   remembers settings)): numbers on/off, the filter panel open/closed and the
   kind and state chips, in this browser under "pf-prefs:" + the page's path,
   as {numbers, panel, kinds, states}. A convenience, never a page setting:
   storage empty, unreadable or throwing leaves the defaults below. The old
   "pageFeatures.badges" choice is read once when the new key has none. The
   popover lists the number's change history from the page's
   own change log: window.PAGE_FEATURES_CHANGES first, else a
   <script type="application/json" id="fo-changes"> block, else none. Other
   code may still hook a popover through window.PAGE_FEATURES_API.onPopover
   and the `page-features:ready` event; this file knows nothing about where a
   page is published.

   Data: window.PAGE_FEATURES_INLINE first (works opened from a file), else
   `features.json` beside the page when served over http(s), else a red banner
   naming why. Version: window.PAGE_FEATURES_VERSION, else the only key of
   `versions`, else none.

   Pattern imitated (never imported): ◆ PLAN's prototype in
   new-workflow-design/builds/page-features/seed/prototype/overlay.js, and
   components/page-picture-review/pic-index.js for the inline-first load and
   the public API. */
(function () {
  /* Fallbacks only: the file's own `kinds` and `state_words` win. */
  var KIND = { data: "Data", rule: "Rule", media: "Pictures and video", layout: "Layout", action: "Action" };
  var LETTER = { data: "D", rule: "R", media: "M", layout: "L", action: "A" };
  var STATE = { "wired": "Real data today", "after-card": "After its card lands", "not-built": "Not built yet" };
  var PREF_KEY = "pageFeatures.badges"; // before PF-2d: numbers on/off only, read once as a fallback
  var PREFS_KEY = "pf-prefs:";          // + location.pathname, per viewer (this browser) and page
  var BW = 40, BH = 26, GAP = 4;       // the badge box the collision rule reasons with
  var KINDS = ["data", "rule", "media", "layout", "action"];
  var STATES = ["wired", "after-card", "not-built"];
  var CHROME_FILE = "components/page-features/overlay.js";

  var F = null, version = null, byN = {}, popNo = null;
  var on = true, panel = true, layer = null, pop = null, popN = null, timer = null, bar = null;
  var chosen = { kind: {}, state: {} }; // the filter chips: value -> true, per group
  var shown = [];                      // [{n, tag, kind, state, el, badge, by}] from the last place()
  var popHooks = [];
  var warned = {}, lastMissing = -1;

  function kindOf(k) {
    var d = (F && F.kinds && F.kinds[k]) || {};
    return { letter: d.letter || LETTER[k] || "?", name: d.name || KIND[k] || String(k), means: d.means || "" };
  }
  function tag(f) { return kindOf(f.kind).letter + f.n; }
  function stateWord(s) { return (F && F.state_words && F.state_words[s]) || STATE[s] || String(s); }
  function slug(s) { return String(s == null ? "" : s).toLowerCase().replace(/[^a-z0-9]+/g, "-"); }

  function el(name, cls, text) {
    var e = document.createElement(name);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }

  function style() {
    var s = document.createElement("style");
    s.textContent =
      "#pf-layer{position:absolute;left:0;top:0;width:0;height:0;z-index:2147483000;pointer-events:none}" +
      ".pf-b{position:absolute;pointer-events:auto;min-width:" + BW + "px;height:" + BH + "px;padding:0 6px;box-sizing:border-box;" +
      "border-radius:13px;border:2px solid #fff;font:700 13px/22px system-ui,-apple-system,'Segoe UI',sans-serif;" +
      "font-variant-numeric:tabular-nums;text-align:center;cursor:pointer;color:#fff;background:#566270;" +
      "box-shadow:0 1px 2px rgba(0,0,0,.35),0 3px 10px rgba(0,0,0,.18)}" +
      ".pf-b:focus-visible{outline:3px solid #2b6cff;outline-offset:2px}.pf-b.pf-fallback{border-style:dashed}" +
      ".pf-k-data{background:#2457c5}.pf-k-rule{background:#7a3dbf}.pf-k-media{background:#0b7c7f}" +
      ".pf-k-layout{background:#566270}.pf-k-action{background:#b4530a}.pf-k-unknown{background:#222;color:#fff}" +
      ".pf-b::after{content:'';position:absolute;right:-5px;top:-5px;width:11px;height:11px;border-radius:50%;border:2px solid #fff;display:none}" +
      ".pf-s-wired::after{display:block;background:#22a05a}.pf-s-after-card::after{display:block;background:#f0b020}" +
      ".pf-s-not-built::after{display:block;background:#d8343f}" +
      ".pf-hl{outline:3px dashed rgba(43,108,255,.85)!important;outline-offset:3px!important}" +
      "#pf-pop{position:absolute;z-index:2147483001;width:min(320px,calc(100vw - 24px));box-sizing:border-box;background:#fff;color:#16202b;" +
      "border:1px solid #c9d2dc;border-radius:10px;box-shadow:0 10px 30px rgba(10,20,30,.22);padding:14px 14px 12px;" +
      "font:14px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif;text-align:left}" +
      "#pf-pop .pf-own{position:absolute;top:6px;right:8px;font:700 11px/1 system-ui,sans-serif;color:#55606c;" +
      "background:#eef3f8;border-radius:6px;padding:3px 5px}#pf-pop[data-feature] h4{padding-right:36px}" +
      "#pf-pop h4{margin:0 0 6px;font-size:16px;line-height:1.25}#pf-pop .pf-kind{font-size:12px;color:#55606c;margin-bottom:8px}" +
      "#pf-pop .pf-chip{display:inline-block;font-size:12px;font-weight:700;border-radius:999px;padding:2px 9px;margin-bottom:8px;cursor:help}" +
      ".pf-chip-wired{background:#d7f0e1;color:#0f5530}.pf-chip-after-card{background:#fbeac2;color:#5b3d00}.pf-chip-not-built{background:#f8d6d8;color:#7d1720}" +
      "#pf-pop .pf-place{margin:0 0 4px}#pf-pop .pf-src{display:block;font:12px/1.4 ui-monospace,Menlo,monospace;color:#3b4652;" +
      "background:#f1f4f7;border-radius:6px;padding:6px 8px;word-break:break-word;margin:4px 0 8px}" +
      "#pf-pop .pf-note{color:#3b4652;font-size:13px;margin:0 0 10px}" +
      "#pf-pop .pf-history{font-size:12.5px;color:#3b4652;margin:6px 0 0;padding:0;list-style:none}#pf-pop .pf-history li{margin:2px 0}" +
      "#pf-pop button{font:600 13px system-ui,sans-serif;border-radius:8px;border:1px solid #9fb0c2;background:#eef3f8;color:#16202b;padding:5px 9px;cursor:pointer}" +
      "#pf-filters{position:fixed;z-index:2147483001;left:12px;bottom:12px;display:flex;flex-wrap:wrap;gap:6px 12px;" +
      "max-width:calc(100vw - 24px);box-sizing:border-box;background:rgba(255,255,255,.96);border:1px solid #c9d2dc;border-radius:10px;" +
      "padding:6px 8px;box-shadow:0 4px 14px rgba(10,20,30,.16)}.pf-fg{display:flex;flex-wrap:wrap;gap:4px;align-items:center}" +
      ".pf-fc{font:600 12px/1 system-ui,sans-serif;border-radius:999px;border:1px solid #9fb0c2;background:#fff;color:#16202b;padding:5px 9px;cursor:pointer}" +
      ".pf-fc[aria-pressed='true']{background:#16202b;color:#fff;border-color:#16202b}.pf-fc:focus-visible{outline:3px solid #2b6cff;outline-offset:2px}" +
      ".pf-tell{flex-basis:100%;font:12px/1.4 system-ui,sans-serif;color:#3b4652}" +
      ".pf-pb{font:600 12px/1 system-ui,sans-serif;border-radius:999px;border:1px solid #9fb0c2;background:#eef3f8;color:#16202b;padding:5px 9px;cursor:pointer}" +
      ".pf-pb:focus-visible{outline:3px solid #2b6cff;outline-offset:2px}#pf-filters.pf-closed .pf-fg,#pf-filters.pf-closed .pf-tell{display:none}" +
      ".pf-banner{position:fixed;z-index:2147483002;top:0;left:0;right:0;background:#d8343f;color:#fff;" +
      "font:600 13px/1.5 system-ui,sans-serif;padding:8px 12px;text-align:center}";
    document.head.appendChild(s);
  }

  /* Visible = drawn with a size, and not inside a closed <details>. */
  function visible(e) {
    if (!e) return false;
    var d = e.parentElement && e.parentElement.closest("details");
    while (d) {
      if (!d.hasAttribute("open")) return false;
      d = d.parentElement && d.parentElement.closest("details");
    }
    var r = e.getBoundingClientRect();
    return r.width > 0 || r.height > 0;
  }

  function all(sel) {
    try { return Array.prototype.slice.call(document.querySelectorAll(sel)); } catch (e) { return []; }
  }

  /* The overlay's own elements are never one of the page's features. */
  function ours(e) {
    return !!(e.closest && (e.closest("#pf-pop") || e.closest("#pf-layer") || e.closest("#pf-filters")));
  }

  /* A data-feature tag first; the version's locator only when nothing is
     tagged. Says how it found the element: {el, by: "tag" | "locator"}. */
  function find(f) {
    var tagged = all('[data-feature="' + f.n + '"]');
    for (var i = 0; i < tagged.length; i++) if (!ours(tagged[i]) && visible(tagged[i])) return { el: tagged[i], by: "tag" };
    var w = f.where && version != null ? f.where[version] : null;
    if (!w || !w.sel) return null;
    var els = all(w.sel);
    if (w.text) els = els.filter(function (e) {
      var s = e.querySelector("summary") || e;
      return String(s.textContent).indexOf(w.text) >= 0;
    });
    for (var j = 0; j < els.length; j++) if (!ours(els[j]) && visible(els[j])) return { el: els[j], by: "locator" };
    return null;
  }

  /* The n of the layout feature that numbers one of the overlay's own
     elements (source.file is this file, source.field names the element). */
  function chrome(field) {
    for (var i = 0; i < F.features.length; i++) {
      var f = F.features[i], s = f.source;
      if (f.kind === "layout" && s && s.file === CHROME_FILE && s.field === field) return f.n;
    }
    return null;
  }

  /* A group with nothing chosen, or every chip chosen, shows everything. */
  function showsAll(group) {
    var c = Object.keys(chosen[group]).length;
    return c === 0 || c === (group === "kind" ? KINDS : STATES).length;
  }
  function passes(group, v) { return showsAll(group) || !!chosen[group][v]; }

  /* Each badge sits at its anchor's top-left. When its box would overlap one
     already placed, it moves right by a badge width plus GAP; past the
     viewport's right edge it starts again one row down. */
  function slot(r, taken) {
    var x0 = Math.max(4, r.left + window.scrollX - 8), y = Math.max(4, r.top + window.scrollY - 10);
    var x = x0, right = (window.innerWidth || 1024) + window.scrollX - BW - 4;
    function hit() {
      return taken.some(function (p) { return x < p[0] + BW + GAP && p[0] < x + BW + GAP && y < p[1] + BH + GAP && p[1] < y + BH + GAP; });
    }
    for (var i = 0; i < 200 && hit(); i++) {
      x += BW + GAP;
      if (x > right && x0 < right) { x = x0; y += BH + GAP; }
    }
    taken.push([x, y]);
    return [x, y];
  }

  function badge(t, cls, n, label, at) {
    var b = el("button", cls, t);
    b.type = "button";
    b.style.left = at[0] + "px";
    b.style.top = at[1] + "px";
    b.dataset.n = String(n);
    b.setAttribute("aria-label", label);
    b.title = label;
    layer.appendChild(b);
    return b;
  }

  function place() {
    timer = null;
    if (!layer) return;
    layer.textContent = "";
    shown = [];
    var taken = [], missing = 0;
    if (bar) bar.style.display = on ? "" : "none";
    F.features.forEach(function (f) {
      var hit = find(f);
      if (!hit) { if (f.n !== popNo) missing++; return; }
      if (!on || !passes("kind", f.kind) || !passes("state", f.state)) return;
      var e = hit.el, k = kindOf(f.kind), fb = hit.by === "locator";
      var label = k.name + " " + tag(f) + ": " + f.name + " (" + stateWord(f.state) + ")" + (fb ? " (found by locator)" : "");
      var b = badge(tag(f), "pf-b pf-k-" + slug(f.kind) + " pf-s-" + slug(f.state) + (fb ? " pf-fallback" : ""), f.n, label,
        slot(e.getBoundingClientRect(), taken));
      shown.push({ n: f.n, tag: tag(f), kind: f.kind, state: f.state, el: e, badge: b, by: hit.by });
    });
    /* A tag naming a number the file does not have is a page/file drift: it
       still gets a badge, so the reader sees it, and the console says which. */
    all("[data-feature]").forEach(function (e) {
      var raw = e.getAttribute("data-feature"), n = parseInt(raw, 10);
      if (byN[n] || ours(e) || !visible(e)) return;
      if (!warned[raw]) { warned[raw] = true; console.warn("page features: no feature " + raw); }
      if (!on || !showsAll("kind") || !showsAll("state")) return;
      var b = badge("?", "pf-b pf-k-unknown", raw, "Feature " + raw + " is not in features.json", slot(e.getBoundingClientRect(), taken));
      shown.push({ n: isNaN(n) ? raw : n, tag: "?", kind: null, state: null, el: e, badge: b });
    });
    if (missing !== lastMissing) {
      lastMissing = missing;
      if (missing) console.info("page features: " + missing + " of " + F.features.length + " features not found on this page" +
        (version != null ? " (version " + version + ")" : ""));
    }
  }
  function schedule() { if (!timer) timer = setTimeout(place, 120); }

  /* "All" (v null) chooses every chip in its group; any other chip toggles. */
  function choose(group, v) {
    var c = chosen[group];
    if (v == null) (group === "kind" ? KINDS : STATES).forEach(function (x) { c[x] = true; });
    else if (c[v]) delete c[v];
    else c[v] = true;
    savePrefs();
    paintChips();
    place();
  }
  function paintChips() {
    Array.prototype.slice.call(bar.querySelectorAll(".pf-fc")).forEach(function (c) {
      var g = c.getAttribute("data-pf-group"), v = c.getAttribute("data-pf-value");
      c.setAttribute("aria-pressed", (v == null ? showsAll(g) : !!chosen[g][v]) ? "true" : "false");
    });
    bar.classList[panel ? "remove" : "add"]("pf-closed");
    var pb = bar.querySelector("[data-pf-panel]");
    if (pb) {
      pb.textContent = panel ? "Hide" : "Filters";
      pb.setAttribute("aria-expanded", panel ? "true" : "false");
      pb.title = panel ? "Hide the filters" : "Show the filters";
    }
  }
  function setPanel(v) {
    panel = !!v;
    savePrefs();
    paintChips();
  }

  /* PF-2d (overlay remembers settings): a viewer's own view, kept per page in
     this browser. Every storage touch is in a try; any failure is the defaults. */
  function prefsKey() {
    try { return PREFS_KEY + String(location.pathname || ""); } catch (e) { return PREFS_KEY; }
  }
  /* A group is stored as the chips that pass: every value when it shows all. */
  function picked(group, all) {
    return showsAll(group) ? all.slice() : all.filter(function (v) { return !!chosen[group][v]; });
  }
  /* A stored list back to chips: only known values; none or every one = all. */
  function unpick(list, all) {
    var out = {};
    if (!Array.isArray(list)) return out;
    var known = all.filter(function (v) { return list.indexOf(v) >= 0; });
    if (known.length && known.length < all.length) known.forEach(function (v) { out[v] = true; });
    return out;
  }
  function loadPrefs() {
    var m = null;
    try { m = JSON.parse(localStorage.getItem(prefsKey()) || "null"); } catch (e) { m = null; }
    if (!m || typeof m !== "object" || Array.isArray(m)) m = {};
    if (typeof m.numbers === "boolean") on = m.numbers;
    else try { on = localStorage.getItem(PREF_KEY) !== "0"; } catch (e) { on = true; }
    if (m.panel === "open" || m.panel === "closed") panel = m.panel === "open";
    chosen.kind = unpick(m.kinds, KINDS);
    chosen.state = unpick(m.states, STATES);
  }
  function savePrefs() {
    try {
      localStorage.setItem(prefsKey(), JSON.stringify({ numbers: on, panel: panel ? "open" : "closed",
        kinds: picked("kind", KINDS), states: picked("state", STATES) }));
    } catch (e) {}
  }
  function filters() {
    bar = el("div");
    bar.id = "pf-filters";
    [["kind", KINDS, "Show features by kind"], ["state", STATES, "Show features by state"]].forEach(function (g) {
      var box = el("div", "pf-fg");
      box.setAttribute("role", "group");
      box.setAttribute("aria-label", g[2]);
      [null].concat(g[1]).forEach(function (v) {
        var c = el("button", "pf-fc", v == null ? "All" : g[0] === "kind" ? kindOf(v).letter : v);
        c.type = "button";
        c.setAttribute("data-pf-group", g[0]);
        if (v == null) c.setAttribute("data-pf-all", "1"); else c.setAttribute("data-pf-value", v);
        c.title = v == null ? "Every " + g[0] : g[0] === "kind" ? kindOf(v).name : stateWord(v);
        c.addEventListener("click", function (e) { e.stopPropagation(); choose(g[0], v); });
        box.appendChild(c);
      });
      bar.appendChild(box);
    });
    bar.appendChild(el("div", "pf-tell", 'Tell your Claude the number, e.g. "L9 on my page: make it a grid"'));
    var pb = el("button", "pf-pb");
    pb.type = "button";
    pb.setAttribute("data-pf-panel", "1");
    pb.addEventListener("click", function (e) { e.stopPropagation(); setPanel(!panel); });
    bar.appendChild(pb);
    document.body.appendChild(bar);
    paintChips();
  }

  function closePop() {
    if (pop) { pop.remove(); pop = null; popN = null; }
    all(".pf-hl").forEach(function (h) { h.classList.remove("pf-hl"); });
  }

  /* The page's change log: window.PAGE_FEATURES_CHANGES, else the JSON in
     #fo-changes (an array, or one object per line as in changes.jsonl), else
     none. Read on each popover, so a log set after load still shows. */
  function changes() {
    if (Array.isArray(window.PAGE_FEATURES_CHANGES)) return window.PAGE_FEATURES_CHANGES;
    var s = document.querySelector("#fo-changes");
    var raw = s ? String(s.textContent || "").trim() : "";
    if (!raw) return [];
    try { var a = JSON.parse(raw); return Array.isArray(a) ? a : [a]; } catch (e) {}
    var out = [];
    raw.split(/\r?\n/).forEach(function (line) {
      if (!line.trim()) return;
      try { out.push(JSON.parse(line)); } catch (e) { console.warn("page features: a #fo-changes line is not JSON"); }
    });
    return out;
  }

  /* Number n's entries, newest first ("at" descending; ties keep the later
     line first), one line each: "<YYYY-MM-DD> · <by>: <said>". */
  function history(n) {
    var hits = [];
    changes().forEach(function (c, i) { if (c && String(c.n) === String(n)) hits.push({ c: c, i: i }); });
    if (!hits.length) return null;
    hits.sort(function (a, b) {
      var x = String(a.c.at || ""), y = String(b.c.at || "");
      return x < y ? 1 : x > y ? -1 : b.i - a.i;
    });
    var ul = el("ul", "pf-history");
    ul.setAttribute("aria-label", "Changes to this number");
    hits.forEach(function (h) {
      var c = h.c;
      ul.appendChild(el("li", null, String(c.at || "").slice(0, 10) + " · " + (c.by || "someone") + ": " + (c.said || "")));
    });
    return ul;
  }

  function openPop(n, b) {
    closePop();
    var f = byN[n];
    pop = el("div");
    pop.id = "pf-pop";
    pop.setAttribute("role", "dialog");
    popN = n;
    if (popNo != null) {
      pop.setAttribute("data-feature", String(popNo));
      pop.appendChild(el("span", "pf-own", tag(byN[popNo])));
    }
    if (!f) {
      pop.setAttribute("aria-label", "Unknown feature " + n);
      pop.appendChild(el("h4", null, "?. Feature " + n));
      pop.appendChild(el("p", "pf-note", "This number is on the page but not in features.json."));
    } else {
      var k = kindOf(f.kind), s = f.source;
      var hit = find(f);
      if (hit) hit.el.classList.add("pf-hl");
      pop.setAttribute("aria-label", "Feature " + tag(f));
      pop.appendChild(el("h4", null, tag(f) + ". " + f.name));
      var kd = el("div", "pf-kind");
      kd.appendChild(el("b", null, k.name));
      if (k.means) kd.appendChild(el("span", null, " · " + k.means));
      pop.appendChild(kd);
      var chip = el("span", "pf-chip pf-chip-" + slug(f.state), f.state);
      chip.title = stateWord(f.state);
      pop.appendChild(chip);
      if (f.place) {
        var pl = el("p", "pf-place");
        pl.appendChild(el("b", null, "Where it is: "));
        pl.appendChild(el("span", null, f.place));
        pop.appendChild(pl);
      }
      pop.appendChild(el("code", "pf-src", s ? s.file + " → " + s.field : "no data of its own"));
      if (f.note) pop.appendChild(el("p", "pf-note", f.note));
      var hist = history(f.n);
      if (hist) pop.appendChild(hist);
      var ctl = el("div", "pf-controls");
      pop.appendChild(ctl);
      popHooks.forEach(function (fn) {
        try { fn({ n: f.n, feature: f, version: version, pop: pop, controls: ctl }); } catch (x) { console.error(x); }
      });
    }
    document.body.appendChild(pop);
    var r = b.getBoundingClientRect();
    var w = pop.offsetWidth || 320, h = pop.offsetHeight || 200;
    var vw = window.innerWidth || 1024, vh = window.innerHeight || 768;
    var left = Math.min(vw - w - 12, Math.max(12, r.left)) + window.scrollX;
    var top = (r.bottom + h + 12 < vh ? r.bottom + 8 : Math.max(12, r.top - h - 8)) + window.scrollY;
    pop.style.left = left + "px";
    pop.style.top = top + "px";
  }

  function setOn(v) {
    on = !!v;
    savePrefs();
    if (!on) closePop();
    place();
  }

  function fail(why) {
    var b = el("div", "pf-banner", "Page features did not load (" + why + ") — no feature numbers on this page.");
    b.setAttribute("role", "alert");
    document.body.appendChild(b);
    console.error("page features failed: " + why);
  }

  function start(file) {
    if (!file || !Array.isArray(file.features)) return fail("features.json has no features list");
    F = file;
    var vs = F.versions ? Object.keys(F.versions) : [];
    version = window.PAGE_FEATURES_VERSION != null ? String(window.PAGE_FEATURES_VERSION) : vs.length === 1 ? vs[0] : null;
    byN = {};
    F.features.forEach(function (f) { byN[f.n] = f; });
    popNo = chrome("popover");
    loadPrefs();

    style();
    layer = el("div");
    layer.id = "pf-layer";
    document.body.appendChild(layer);
    filters();
    place();

    new MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var t = list[i].target;
        if (t === layer || t === pop || t === bar || ours(t)) continue;
        return schedule();
      }
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["open", "class", "hidden", "data-feature"] });
    document.addEventListener("toggle", schedule, true);
    window.addEventListener("resize", schedule);
    window.addEventListener("load", schedule);

    document.addEventListener("click", function (e) {
      var b = e.target && e.target.closest && e.target.closest(".pf-b");
      if (b) {
        e.preventDefault(); e.stopPropagation();
        var raw = b.dataset.n, n = parseInt(raw, 10);
        openPop(byN[n] ? n : raw, b);
        return;
      }
      if (pop && !pop.contains(e.target)) closePop();
    }, true);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closePop(); return; }
      if (e.key !== "f" && e.key !== "F") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var t = e.target || {};
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || "") || t.isContentEditable) return;
      setOn(!on);
    });

    window.PAGE_FEATURES_API = {
      badges: function () { return shown.slice(); },
      features: function () { return F.features.slice(); },
      onPopover: function (fn) { if (typeof fn === "function") popHooks.push(fn); },
      version: version
    };
    document.dispatchEvent(new CustomEvent("page-features:ready"));
  }

  function load() {
    var served = /^https?:$/.test(location.protocol);
    if (window.PAGE_FEATURES_INLINE) start(window.PAGE_FEATURES_INLINE);
    else if (served) fetch("features.json?ts=" + Date.now())
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(start, function (e) { fail("features.json could not be read: " + e.message); });
    else fail("this page has no inline features and fetch is blocked on file:// URLs");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load); else load();
})();
