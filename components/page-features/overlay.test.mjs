// Offline check for overlay.js (card PF-2 (feature overlay)).
//
// Runs the browser file in a node:vm context with a minimal DOM stubbed
// below and an inline features.json v1 fixture (this test reads no other file
// of the component). Each scenario is a fresh context. Checks 1-4 and 10 are
// the card's; R2 is the lead's filing rider (badge collisions). B1, B2 and B4
// are PF-2b (number-first changes)'s: locator hits drawn dashed, the
// popover's own number, and the multi-select filter chips. C1-C7 are PF-2c
// (overlay read-only)'s: no marks layer (marks.js retired on developer's ruling,
// feedback happens in a Claude session by number), the change history in the
// popover, and the one "Tell your Claude the number" line. D0-D8 are PF-2d
// (overlay remembers settings)'s: a viewer's view kept per page across reloads.
//
// Run:  node components/page-features/overlay.test.mjs
// No dependencies, no network, no build step.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import vm from "node:vm";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const OVERLAY = fs.readFileSync(path.join(HERE, "overlay.js"), "utf8");

const fails = [];
let passed = 0;
const ck = (name, cond, extra = "") => {
  console.log((cond ? "ok    " : "FAIL  ") + name + (extra && !cond ? " — " + extra : ""));
  if (cond) passed++; else fails.push(name);
};

/* ---------------------------------------------------------------------------
 * The DOM: just real enough for the two files. Simple selectors only
 * (tag, #id, .class, [attr], [attr="v"], compounds of those).
 * ------------------------------------------------------------------------ */
const escHtml = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function parseSel(sel) {
  const m = /^([a-zA-Z][a-zA-Z0-9-]*)?((?:#[\w-]+|\.[\w-]+|\[[^\]]+\])*)$/.exec(sel.trim());
  if (!m) throw new Error("stub: unsupported selector " + sel);
  const parts = [];
  for (const p of m[2].match(/#[\w-]+|\.[\w-]+|\[[^\]]+\]/g) || []) {
    if (p[0] === "#") parts.push((e) => e.getAttribute("id") === p.slice(1));
    else if (p[0] === ".") parts.push((e) => e.classList.contains(p.slice(1)));
    else {
      const a = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(p);
      if (!a) throw new Error("stub: unsupported attribute selector " + p);
      parts.push((e) => (a[2] === undefined ? e.hasAttribute(a[1]) : e.getAttribute(a[1]) === a[2]));
    }
  }
  const tag = m[1] && m[1].toUpperCase();
  return (e) => e.nodeType === 1 && (!tag || e.tagName === tag) && parts.every((f) => f(e));
}

class Node_ {
  constructor(tag) {
    this.nodeType = 1; this.tagName = tag.toUpperCase(); this.attrs = {}; this.children = [];
    this.parentElement = null; this.style = {}; this.listeners = []; this.rect = null; this.raw = null;
    const self = this;
    this.classList = {
      list: () => (self.attrs.class || "").split(/\s+/).filter(Boolean),
      contains: (c) => self.classList.list().includes(c),
      add: (c) => { if (!self.classList.contains(c)) self.attrs.class = self.classList.list().concat(c).join(" "); },
      remove: (c) => { self.attrs.class = self.classList.list().filter((x) => x !== c).join(" "); },
    };
    this.dataset = new Proxy({}, {
      get: (_, k) => self.getAttribute("data-" + String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase())) ?? undefined,
      set: (_, k, v) => { self.setAttribute("data-" + String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()), v); return true; },
    });
  }
  get className() { return this.attrs.class || ""; }
  set className(v) { this.attrs.class = String(v); }
  get id() { return this.attrs.id || ""; }
  set id(v) { this.attrs.id = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  appendChild(c) { if (c.parentElement) c.remove(); c.parentElement = this; this.children.push(c); return c; }
  remove() { const p = this.parentElement; if (p) { p.children = p.children.filter((x) => x !== this); this.parentElement = null; } }
  contains(n) { for (let x = n; x; x = x.parentElement) if (x === this) return true; return false; }
  get isConnected() { let x = this; while (x.parentElement) x = x.parentElement; return x.tagName === "#DOCUMENT"; }
  get textContent() { return this.raw != null ? this.raw.replace(/<[^>]*>/g, "") : this.children.map((c) => (c.nodeType === 3 ? c.text : c.textContent)).join(""); }
  set textContent(v) { this.raw = null; this.children = v === "" ? [] : [{ nodeType: 3, text: String(v) }]; }
  get innerHTML() {
    if (this.raw != null) return this.raw;
    return this.children.map((c) => (c.nodeType === 3 ? escHtml(c.text) : c.outerHTML)).join("");
  }
  set innerHTML(v) { this.children = []; this.raw = String(v); }
  get outerHTML() {
    const t = this.tagName.toLowerCase();
    const a = Object.entries(this.attrs).map(([k, v]) => ` ${k}="${escHtml(v)}"`).join("");
    return `<${t}${a}>${this.innerHTML}</${t}>`;
  }
  descendants() { const out = []; const walk = (e) => e.children.forEach((c) => { if (c.nodeType === 1) { out.push(c); walk(c); } }); walk(this); return out; }
  querySelectorAll(sel) { const m = parseSel(sel); return this.descendants().filter(m); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  closest(sel) { const m = parseSel(sel); for (let x = this; x && x.nodeType === 1; x = x.parentElement) if (m(x)) return x; return null; }
  addEventListener(type, fn, opts) {
    const capture = opts === true || !!(opts && opts.capture);
    this.listeners.push({ type, fn, capture, once: !!(opts && opts.once) });
  }
  removeEventListener(type, fn) { this.listeners = this.listeners.filter((l) => l.type !== type || l.fn !== fn); }
  getBoundingClientRect() {
    const r = this.rect || { left: 10, top: 10, width: 100, height: 20 };
    return { left: r.left, top: r.top, width: r.width, height: r.height, right: r.left + r.width, bottom: r.top + r.height };
  }
  get offsetWidth() { return 0; }
  get offsetHeight() { return 0; }
}

function fire(node, ev, capture) {
  for (const l of node.listeners.slice()) {
    if (l.type !== ev.type || (capture !== null && l.capture !== capture)) continue;
    if (l.once) node.removeEventListener(l.type, l.fn);
    l.fn.call(node, ev);
    if (ev.stopped) return;
  }
}
// Capture from the document down, the target itself, then bubble back up.
function dispatch(target, type, extra = {}) {
  const ev = Object.assign({ type, target, stopped: false, defaultPrevented: false,
    stopPropagation() { this.stopped = true; }, preventDefault() { this.defaultPrevented = true; } }, extra);
  const chain = [];
  for (let x = target.parentElement; x; x = x.parentElement) chain.push(x);
  for (const n of chain.slice().reverse()) { fire(n, ev, true); if (ev.stopped) return ev; }
  fire(target, ev, null); if (ev.stopped) return ev;
  for (const n of chain) { fire(n, ev, false); if (ev.stopped) return ev; }
  return ev;
}

/* ---------------------------------------------------------------------------
 * A context: the DOM, fake timers, a recording console.
 * ------------------------------------------------------------------------ */
function makeWorld({ build, version, store: given, storage, pathname = "/fixture.html" } = {}) {
  const document = new Node_("#document");
  const html = document.appendChild(new Node_("html"));
  document.documentElement = html;
  document.head = html.appendChild(new Node_("head"));
  document.body = html.appendChild(new Node_("body"));
  document.readyState = "complete";
  document.createElement = (t) => new Node_(t);
  document.dispatchEvent = (ev) => { fire(document, ev, null); return true; };

  const logs = { log: [], info: [], warn: [], error: [] };
  const rec = (k) => (...a) => logs[k].push(a.map(String).join(" "));
  const timers = [];
  let tid = 0, observer = null;
  const store = given || {};             // pass one store to two worlds: a reload in the same browser
  const fetches = [];

  const sandbox = {
    console: { log: rec("log"), info: rec("info"), warn: rec("warn"), error: rec("error") },
    document,
    location: { protocol: "file:", href: "file://" + pathname, pathname },
    localStorage: storage || { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } },
    fetch: (u) => { fetches.push(String(u)); return Promise.reject(new Error("no network in this test")); },
    setTimeout: (fn, ms) => { const id = ++tid; timers.push({ id, fn, ms }); return id; },
    clearTimeout: (id) => { const i = timers.findIndex((t) => t.id === id); if (i >= 0) timers.splice(i, 1); },
    MutationObserver: class { constructor(cb) { observer = cb; } observe() {} disconnect() {} },
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init && init.detail; } },
    scrollX: 0, scrollY: 0, innerWidth: 1024, innerHeight: 768,
    listeners: [],
  };
  sandbox.addEventListener = (type, fn) => sandbox.listeners.push({ type, fn });
  sandbox.window = sandbox;
  if (version !== undefined) sandbox.PAGE_FEATURES_VERSION = version;
  vm.createContext(sandbox);
  if (build) build(document, sandbox);

  const w = {
    sandbox, document, logs, store, fetches,
    run: (src, name) => vm.runInContext(src, sandbox, { filename: name }),
    flush: () => { for (let i = 0; i < 200 && timers.length; i++) timers.shift().fn(); },
    mutate: (target) => { if (observer) observer([{ target, type: "childList" }]); },
    api: () => sandbox.PAGE_FEATURES_API,
    badge: (n) => (sandbox.PAGE_FEATURES_API.badges().find((b) => b.n === n) || {}).badge,
    pop: () => document.querySelector("#pf-pop"),
    click: (el) => dispatch(el, "click"),
    key: (k, target) => dispatch(target || document.body, "keydown", { key: k }),
  };
  return w;
}

function add(parent, tag, attrs = {}, rect = null) {
  const e = new Node_(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  e.rect = rect;
  return parent.appendChild(e);
}

/* ---------------------------------------------------------------------------
 * The fixture: a features.json v1 object. Kind meanings are deliberately
 * unlike any fallback, so a match proves they came from the FILE.
 * ------------------------------------------------------------------------ */
const KINDS = {
  data: { letter: "D", name: "Data", means: "FILE-MEANS-DATA: a value saved in a data file." },
  rule: { letter: "R", name: "Rule", means: "FILE-MEANS-RULE: worked out on the page." },
  media: { letter: "M", name: "Media", means: "FILE-MEANS-MEDIA: a file on Drive." },
  layout: { letter: "L", name: "Layout", means: "FILE-MEANS-LAYOUT: arrangement only." },
  action: { letter: "A", name: "Action", means: "FILE-MEANS-ACTION: runs a command." },
};
const STATE_WORDS = { "wired": "FILE-STATE-WIRED", "after-card": "FILE-STATE-AFTER-CARD", "not-built": "FILE-STATE-NOT-BUILT" };
const fixture = (features, extra = {}) => Object.assign({ schema: 1, title: "Fixture page", status: "draft", kinds: KINDS, state_words: STATE_WORDS, page: "fixture.html", features }, extra);
const F = (n, kind, state, more = {}) => Object.assign({ n, name: "Feature " + n, kind, state, status: "draft", source: null }, more);

const MAIN = fixture([
  F(4, "data", "wired", { name: "Run id", source: { component: "c", file: "runs/x/run.json", field: "id" }, place: "the header", note: "read off the run record" }),
  F(9, "rule", "after-card", { name: "Days late" }),
  F(2, "data", "not-built", { name: "Stage list", source: { component: "c", file: "runs/x/stages.json", field: "stages[]" } }),
  F(5, "layout", "wired", { name: "Section order" }),
  F(12, "media", "wired", { name: "Nowhere on this page" }),
]);
const TAGGED = [4, 9, 2, 5];
const rectAt = (i) => ({ left: 100, top: 100 + i * 120, width: 300, height: 40 });
function buildMain(doc) {
  const main = add(doc.body, "div", { id: "main" });
  TAGGED.forEach((n, i) => add(main, "div", { "data-feature": String(n), id: "f" + n }, rectAt(i)));
  add(main, "div", { "data-feature": "99", id: "f99" }, rectAt(TAGGED.length));
}
const LETTERS = { 4: "D4", 9: "R9", 2: "D2", 5: "L5" };

/* ---------------------------------------------------------------------------
 * 1. One badge per tagged element; letter + n; kind class; state dot; reorder.
 * ------------------------------------------------------------------------ */
{
  const w = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; buildMain(d); } });
  w.run(OVERLAY, "overlay.js");
  const api = w.api();
  ck("0. the overlay exposes PAGE_FEATURES_API and reads inline data without fetching",
    !!api && typeof api.badges === "function" && w.fetches.length === 0, JSON.stringify(w.fetches));
  const known = api.badges().filter((b) => b.tag !== "?");
  ck("1a. one badge per tagged element", known.length === TAGGED.length
    && TAGGED.every((n) => known.filter((b) => b.n === n).length === 1), known.map((b) => b.tag).join(","));
  ck("1b. badge text is letter + n (data 4 -> D4, rule 9 -> R9)",
    w.badge(4).textContent === "D4" && w.badge(9).textContent === "R9" && w.badge(5).textContent === "L5",
    [4, 9, 5].map((n) => w.badge(n) && w.badge(n).textContent).join(","));
  ck("1c. the badge class names the kind",
    w.badge(4).classList.contains("pf-k-data") && w.badge(9).classList.contains("pf-k-rule") && w.badge(5).classList.contains("pf-k-layout"));
  ck("1d. the corner dot names the state (wired / after-card / not-built)",
    w.badge(4).classList.contains("pf-s-wired") && w.badge(9).classList.contains("pf-s-after-card")
    && w.badge(2).classList.contains("pf-s-not-built"));

  // Reorder: reverse the elements; each now draws at its new position.
  const main = w.document.querySelector("#main");
  main.children.reverse();
  main.children.forEach((e, i) => { e.rect = rectAt(i); });
  w.mutate(main); w.flush();
  const after = w.api().badges().filter((b) => b.tag !== "?");
  ck("1e. after reordering, each element's badge still shows its own tag and sits on it",
    after.length === TAGGED.length && after.every((b) => b.el.getAttribute("data-feature") === String(b.n)
      && b.badge.textContent === LETTERS[b.n]
      && b.badge.style.left === (b.el.rect.left - 8) + "px" && b.badge.style.top === (b.el.rect.top - 10) + "px"),
    after.map((b) => b.tag + "@" + b.badge.style.top + " on " + b.el.id + "@" + b.el.rect.top).join(", "));

  /* 3. Unknown number -> "?" and one warning, even after a re-place. */
  const unk = w.api().badges().filter((b) => b.tag === "?");
  ck("3a. data-feature=\"99\" not in features gets a \"?\" badge",
    unk.length === 1 && unk[0].badge.textContent === "?" && unk[0].el.id === "f99");
  ck("3b. ... and exactly one console.warn naming it (re-placing does not repeat it)",
    w.logs.warn.length === 1 && w.logs.warn[0] === "page features: no feature 99", JSON.stringify(w.logs.warn));
  ck("3c. features found nowhere are counted in one console line",
    w.logs.info.filter((l) => /1 of 5 features not found/.test(l)).length === 1, JSON.stringify(w.logs.info));

  /* 4. The popover. */
  w.click(w.badge(4));
  let pop = w.pop();
  ck("4a. clicking D4 opens a popover titled with tag + name", !!pop && pop.querySelector("h4").textContent === "D4. Run id");
  ck("4b. it shows the kind's name and meaning FROM THE FILE'S kinds",
    !!pop && /Data/.test(pop.querySelector(".pf-kind").textContent) && pop.textContent.includes(KINDS.data.means));
  ck("4c. it shows source.file → source.field", !!pop && pop.querySelector(".pf-src").textContent === "runs/x/run.json → id");
  ck("4d. it shows place and note", !!pop && pop.textContent.includes("the header") && pop.textContent.includes("read off the run record"));
  ck("4e. a wired feature's state chip carries the file's state word as its tooltip",
    !!pop && pop.querySelector(".pf-chip").textContent === "wired" && pop.querySelector(".pf-chip").title === STATE_WORDS.wired);
  w.click(w.badge(9));
  pop = w.pop();
  ck("4f. an after-card feature shows its state chip",
    w.document.querySelectorAll("#pf-pop").length === 1 && pop.querySelector(".pf-chip").classList.contains("pf-chip-after-card")
    && pop.querySelector(".pf-chip").textContent === "after-card" && pop.querySelector(".pf-chip").title === STATE_WORDS["after-card"]);
  w.click(w.badge(5));
  pop = w.pop();
  ck("4g. a layout feature with source null shows \"no data of its own\"",
    !!pop && pop.querySelector(".pf-src").textContent === "no data of its own");
  w.key("Escape");
  ck("4h. Escape closes the popover", !w.pop());
  w.click(w.badge(5)); w.click(w.document.querySelector("#f4"));
  ck("4i. an outside click closes the popover", !w.pop());

  /* F toggles the badges; the preference is stored (PF-2d (overlay remembers
     settings): under the page's own pf-prefs key); typing in a field never toggles. */
  const numbers = () => JSON.parse(w.store["pf-prefs:/fixture.html"] || "{}").numbers;
  w.key("F");
  ck("4j. key F hides the badges and stores the preference",
    w.api().badges().length === 0 && numbers() === false, JSON.stringify(w.store));
  const input = add(w.document.body, "input");
  w.key("F", input);
  ck("4k. F typed into an INPUT does not toggle", w.api().badges().length === 0);
  w.key("f");
  ck("4l. F again brings them back", w.api().badges().length === TAGGED.length + 1 && numbers() === true, JSON.stringify(w.store));
}

/* A served page with no inline data fetches features.json; a file:// page gets the banner. */
{
  const w = makeWorld({ build: (d) => add(d.body, "div") });
  w.run(OVERLAY, "overlay.js");
  const banner = w.document.querySelector(".pf-banner");
  ck("0b. no inline data on file:// -> a banner naming why, no fetch, no API",
    !!banner && /file:\/\//.test(banner.textContent) && w.fetches.length === 0 && !w.api());
}

/* ---------------------------------------------------------------------------
 * 2. A `where` locator places a badge on an untagged element; a tag beats it.
 * ------------------------------------------------------------------------ */
{
  const fx = fixture([
    F(7, "data", "wired", { where: { A: { sel: "#x" } } }),
    F(8, "rule", "wired", { where: { A: { sel: "#y" } } }),
    F(6, "media", "wired", { where: { A: { sel: ".card", text: "second" } } }),
  ], { versions: { A: "page-a.html" } });
  const w = makeWorld({ build: (d, s) => {
    s.PAGE_FEATURES_INLINE = fx;
    add(d.body, "div", { id: "x" }, { left: 50, top: 50, width: 80, height: 20 });
    add(d.body, "div", { id: "y" }, { left: 50, top: 300, width: 80, height: 20 });
    add(d.body, "div", { id: "z", "data-feature": "8" }, { left: 500, top: 300, width: 80, height: 20 });
    add(d.body, "div", { class: "card", id: "c1" }, { left: 50, top: 500, width: 80, height: 20 }).textContent = "first";
    add(d.body, "div", { class: "card", id: "c2" }, { left: 50, top: 600, width: 80, height: 20 }).textContent = "second";
  } });
  w.run(OVERLAY, "overlay.js");
  const by = (n) => w.api().badges().find((b) => b.n === n);
  ck("2a. the only key of versions is the version", w.api().version === "A");
  ck("2b. where.A.sel \"#x\" places feature 7's badge on #x", !!by(7) && by(7).el.id === "x" && by(7).badge.textContent === "D7");
  ck("2c. a data-feature tag beats the locator (8 on #z, not #y)", !!by(8) && by(8).el.id === "z");
  ck("2d. the locator's text filter picks the matching element", !!by(6) && by(6).el.id === "c2");
}

/* ---------------------------------------------------------------------------
 * R2. Badge collisions: three anchors on one rect -> three clear boxes.
 * ------------------------------------------------------------------------ */
{
  const same = { left: 200, top: 200, width: 60, height: 20 };
  const w = makeWorld({ build: (d, s) => {
    s.PAGE_FEATURES_INLINE = fixture([F(11, "media", "wired"), F(12, "data", "wired"), F(13, "data", "wired")]);
    [11, 12, 13].forEach((n) => add(d.body, "span", { "data-feature": String(n) }, same));
  } });
  w.run(OVERLAY, "overlay.js");
  const BW = 40, BH = 26;                // the badge box (min-width x height in overlay.js's CSS)
  const pos = w.api().badges().map((b) => [parseFloat(b.badge.style.left), parseFloat(b.badge.style.top)]);
  const clear = (a, b) => a[0] + BW <= b[0] || b[0] + BW <= a[0] || a[1] + BH <= b[1] || b[1] + BH <= a[1];
  ck("R2. three features on the same rect get three non-overlapping badge positions",
    pos.length === 3 && clear(pos[0], pos[1]) && clear(pos[0], pos[2]) && clear(pos[1], pos[2]), JSON.stringify(pos));
}

/* ---------------------------------------------------------------------------
 * 10. overlay.js, comments and strings stripped (I-102 (test shape
 *     convention)), never names the runtime. The stripper is shown to FIRE
 *     on a planted reference and RELEASE on comment/string mentions.
 * ------------------------------------------------------------------------ */
function stripCode(src) {
  let out = "", i = 0;
  while (i < src.length) {
    const c = src[i], d = src[i + 1];
    if (c === "/" && d === "/") { while (i < src.length && src[i] !== "\n") i++; continue; }
    if (c === "/" && d === "*") { const j = src.indexOf("*/", i + 2); i = j < 0 ? src.length : j + 2; continue; }
    if (c === '"' || c === "'" || c === "`") {
      i++;
      while (i < src.length && src[i] !== c) i += src[i] === "\\" ? 2 : 1;
      i++; out += '""'; continue;
    }
    out += c; i++;
  }
  return out;
}
const mentions = (src) => /claude/i.test(stripCode(src));
ck("10a. the stripper fires on code that names it and releases on a comment or string that does",
  mentions(OVERLAY + "\nwindow.claude.use(1);") && !mentions("/* claude */ var a = 'claude'; // claude\n var b = \"x\";")
  && /PAGE_FEATURES_API/.test(stripCode(OVERLAY)));
ck("10b. overlay.js's code (comments and strings stripped) has no \"claude\"", !mentions(OVERLAY));

/* ===========================================================================
 * PF-2b (number-first changes), after its scope cut: no change box. A person
 * names a NUMBER to their own Claude, which applies it.
 * ======================================================================== */

/* B1. A data-feature tag beats the CSS locator; a locator hit is drawn dashed. */
{
  const fx = fixture([
    F(7, "data", "wired", { where: { A: { sel: "#x" } } }),
    F(8, "rule", "wired", { where: { A: { sel: "#y" } } }),
  ], { versions: { A: "page-a.html" } });
  let z = null;
  const w = makeWorld({ build: (d, s) => {
    s.PAGE_FEATURES_INLINE = fx;
    add(d.body, "div", { id: "x" }, { left: 50, top: 50, width: 80, height: 20 });
    add(d.body, "div", { id: "y" }, { left: 50, top: 300, width: 80, height: 20 });
    z = add(d.body, "div", { id: "z", "data-feature": "8" }, { left: 500, top: 300, width: 80, height: 20 });
  } });
  w.run(OVERLAY, "overlay.js");
  const by = (n) => w.api().badges().find((b) => b.n === n);
  const label = (n) => by(n).badge.getAttribute("aria-label");
  ck("B1a. feature 8, found by its data-feature tag on #z (not its locator #y), is drawn solid: no pf-fallback",
    !!by(8) && by(8).el.id === "z" && by(8).by === "tag" && !by(8).badge.classList.contains("pf-fallback")
    && !/found by locator/.test(label(8)), by(8) && by(8).badge.className);
  ck("B1b. feature 7, found only by where.A.sel, is drawn dashed (pf-fallback) and its label ends \" (found by locator)\"",
    !!by(7) && by(7).el.id === "x" && by(7).by === "locator" && by(7).badge.classList.contains("pf-fallback")
    && label(7).endsWith(" (found by locator)") && by(7).badge.title === label(7), by(7) && label(7));
  ck("B1c. the stylesheet draws a pf-fallback badge with a dashed border",
    w.document.head.children.some((s) => s.textContent.includes(".pf-b.pf-fallback{border-style:dashed}")));
  z.removeAttribute("data-feature"); w.mutate(z); w.flush();
  ck("B1d. remove #z's tag and feature 8 falls back to its locator #y, now dashed",
    !!by(8) && by(8).el.id === "y" && by(8).badge.classList.contains("pf-fallback"));
}

/* B2. The overlay's own popover carries its number when the file lists it. */
const POPOVER = { component: "page-features", file: "components/page-features/overlay.js", field: "popover" };
{
  const fx = fixture(MAIN.features.concat([F(42, "layout", "wired", { name: "Feature popover", source: POPOVER })]));
  const w = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = fx; buildMain(d); } });
  w.run(OVERLAY, "overlay.js");
  w.click(w.badge(4));
  let pop = w.pop();
  const own = pop && pop.querySelector(".pf-own");
  ck("B2a. with a popover feature (L42) in the file, D4's popover carries data-feature=\"42\" and a visible \"L42\" label",
    !!pop && pop.getAttribute("data-feature") === "42" && !!own && own.textContent === "L42"
    && pop.querySelector("h4").textContent === "D4. Run id", pop && pop.outerHTML.slice(0, 200));
  w.mutate(w.document.querySelector("#main")); w.flush();
  const bs = w.api().badges();
  ck("B2b. ... and no badge is drawn on the popover, even after a re-place",
    !!w.pop() && !w.badge(42) && bs.every((b) => !w.pop().contains(b.el)) && bs.filter((b) => b.tag === "?").length === 1,
    bs.map((b) => b.tag).join(","));
  ck("B2c. the popover's own feature is not counted missing from the page (1 of 6, feature 12 only)",
    w.logs.info.some((l) => /1 of 6 features not found/.test(l)), JSON.stringify(w.logs.info));
  w.click(w.api().badges().find((b) => b.tag === "?").badge);
  pop = w.pop();
  ck("B2d. the popover for an unknown number carries the same number", !!pop && pop.getAttribute("data-feature") === "42");
}
{
  const w = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; buildMain(d); } });
  w.run(OVERLAY, "overlay.js");
  w.click(w.badge(4));
  const pop = w.pop();
  ck("B2e. with no popover feature in the file, #pf-pop carries no data-feature and no label",
    !!pop && !pop.hasAttribute("data-feature") && !pop.querySelector(".pf-own"));
}

/* B4. Filter chips: multi-select ORs within a group, ANDs across groups;
   "All" chooses every chip in its group; a group with nothing chosen shows all. */
{
  const w = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; buildMain(d); } });
  w.run(OVERLAY, "overlay.js");
  const tags = () => w.api().badges().map((b) => b.tag).sort().join(",");
  const chip = (g, v) => w.document.querySelector(v == null ? `[data-pf-group="${g}"][data-pf-all]` : `[data-pf-group="${g}"][data-pf-value="${v}"]`);
  const chips = (g) => w.document.querySelectorAll(`[data-pf-group="${g}"]`);
  const pressed = (g) => chips(g).filter((c) => c.getAttribute("aria-pressed") === "true").map((c) => c.textContent).join(",");
  const EVERY = "?,D2,D4,L5,R9";
  ck("B4a. two chip groups, each led by All: kind All D R M L A, state All wired after-card not-built; nothing chosen, everything shown",
    chips("kind").map((c) => c.textContent).join() === "All,D,R,M,L,A"
    && chips("state").map((c) => c.textContent).join() === "All,wired,after-card,not-built"
    && pressed("kind") === "All" && pressed("state") === "All" && tags() === EVERY, tags());
  w.click(chip("kind", "data"));
  ck("B4b. kind D alone shows the D badges only", tags() === "D2,D4" && pressed("kind") === "D", tags());
  w.click(chip("kind", "rule"));
  ck("B4c. D and R chosen: within a group the chips OR", tags() === "D2,D4,R9" && pressed("kind") === "D,R", tags());
  w.click(chip("state", "wired"));
  ck("B4d. ... and state wired: across groups they AND ((D or R) and wired)", tags() === "D4", tags());
  w.click(chip("state", "not-built"));
  ck("B4e. ... add not-built: (D or R) and (wired or not-built)", tags() === "D2,D4", tags());
  w.click(chip("kind", null));
  ck("B4f. kind All chooses every kind chip, so the kind group shows all; the state chips still filter",
    pressed("kind") === "All,D,R,M,L,A" && tags() === "D2,D4,L5", pressed("kind") + " / " + tags());
  w.click(chip("state", null));
  ck("B4g. state All resets that group too: every badge is back", pressed("state") === "All,wired,after-card,not-built" && tags() === EVERY, tags());
  const w2 = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; buildMain(d); } });
  w2.run(OVERLAY, "overlay.js");
  const c2 = w2.document.querySelector('[data-pf-group="state"][data-pf-value="after-card"]');
  w2.click(c2); const narrowed = w2.api().badges().map((b) => b.tag).join();
  w2.click(c2);
  ck("B4h. a chip clicked on then off leaves its group with nothing chosen, which shows everything",
    narrowed === "R9" && w2.api().badges().map((b) => b.tag).sort().join(",") === EVERY, narrowed);
  w.key("F");
  ck("B4i. F hides the chips with the badges", w.document.querySelector("#pf-filters").style.display === "none" && w.api().badges().length === 0);
}

/* ===========================================================================
 * PF-2c (overlay read-only): no marks layer, the number's change history in
 * the popover, and one line telling the reader to name the number to Claude.
 * ======================================================================== */
const XSS = "<img src=x onerror=alert(1)>";
const LOG = [
  { n: 4, said: "older: show the run id in full", at: "2026-10-19T08:00:00Z", by: "developer", route: "page" },
  { n: 2, said: "list the stages as chips", at: "2026-10-20T09:00:00Z", by: "owner", route: "page" },
  { n: 4, said: "newer: copy button beside it", at: "2026-10-21T03:00:00Z", by: "editor", route: "page" },
];
const histLines = (w, n) => {
  w.click(w.badge(n));
  const h = w.pop() && w.pop().querySelector(".pf-history");
  const out = h ? h.querySelectorAll("li").map((li) => li.textContent) : null;
  w.key("Escape");
  return out;
};
const D4_LINES = ["2026-10-21 · editor: newer: copy button beside it", "2026-10-19 · developer: older: show the run id in full"];
const D2_LINES = ["2026-10-20 · owner: list the stages as chips"];

/* C1-C2. No marks: no pick, note or mark-control element; no data-count; no setMarks. */
{
  const w = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; s.PAGE_FEATURES_CHANGES = LOG; buildMain(d); } });
  w.run(OVERLAY, "overlay.js");
  const drawn = () => w.document.querySelectorAll(".pf-picks").length + w.document.querySelectorAll(".pf-pick-word").length
    + w.document.querySelectorAll(".pf-controls-mark").length + w.document.querySelectorAll("[data-pf-pick]").length
    + w.document.querySelectorAll("input").length + w.document.querySelectorAll("textarea").length;
  let seen = drawn();
  TAGGED.forEach((n) => { w.click(w.badge(n)); seen += drawn(); w.key("Escape"); });
  ck("C1. no element with class pf-picks, pf-pick-word or pf-controls-mark (nor a pick or note field) is drawn, popovers open; badges carry no data-count",
    seen === 0 && w.api().badges().length === TAGGED.length + 1 && w.api().badges().every((b) => !b.badge.hasAttribute("data-count"))
    && !w.document.head.children.some((s) => s.textContent.includes("data-count")), String(seen));
  const api = w.api();
  ck("C2. PAGE_FEATURES_API has no setMarks, and keeps badges / features / onPopover / version",
    !("setMarks" in api) && typeof api.badges === "function" && typeof api.features === "function"
    && typeof api.onPopover === "function" && "version" in api, Object.keys(api).join(","));

  /* C3. History from window.PAGE_FEATURES_CHANGES, newest first. */
  const d4 = histLines(w, 4), d2 = histLines(w, 2);
  ck("C3. with PAGE_FEATURES_CHANGES holding two entries for n=4 and one for n=2: D4 lists two lines newest first, D2 one",
    JSON.stringify(d4) === JSON.stringify(D4_LINES) && JSON.stringify(d2) === JSON.stringify(D2_LINES), JSON.stringify([d4, d2]));
  ck("C3b. a number with no entries draws no history element", histLines(w, 9) === null);

  /* C5. The one line in the filter bar. */
  const bar = w.document.querySelector("#pf-filters");
  const tells = bar.querySelectorAll(".pf-tell");
  ck("C5. the \"Tell your Claude the number\" line appears exactly once in #pf-filters, as text",
    tells.length === 1 && bar.textContent.split("Tell your Claude the number").length === 2
    && w.document.documentElement.textContent.split("Tell your Claude the number").length === 2
    && tells[0].textContent === 'Tell your Claude the number, e.g. "L9 on my page: make it a grid"'
    && tells[0].children.every((c) => c.nodeType === 3), tells.map((t) => t.textContent).join(" | "));

  /* The popover hook still runs (other code may hook a popover). */
  let hooked = null;
  api.onPopover((o) => { hooked = o.n; });
  w.click(w.badge(5));
  ck("C5b. onPopover still hooks a popover", hooked === 5);
}

/* C4. The same history from a <script type="application/json" id="fo-changes"> block; then no log at all. */
{
  const w = makeWorld({ build: (d, s) => {
    s.PAGE_FEATURES_INLINE = MAIN; buildMain(d);
    add(d.body, "script", { type: "application/json", id: "fo-changes" }).textContent = JSON.stringify(LOG);
  } });
  w.run(OVERLAY, "overlay.js");
  const d4 = histLines(w, 4), d2 = histLines(w, 2);
  ck("C4. the same from a #fo-changes block: D4 two lines newest first, D2 one",
    JSON.stringify(d4) === JSON.stringify(D4_LINES) && JSON.stringify(d2) === JSON.stringify(D2_LINES), JSON.stringify([d4, d2]));
}
{
  const w = makeWorld({ build: (d, s) => {
    s.PAGE_FEATURES_INLINE = MAIN; buildMain(d);
    add(d.body, "script", { type: "application/json", id: "fo-changes" }).textContent = LOG.map((c) => JSON.stringify(c)).join("\n") + "\n";
  } });
  w.run(OVERLAY, "overlay.js");
  const d4 = histLines(w, 4);
  ck("C4b. a #fo-changes block holding changes.jsonl lines (one object per line) reads the same",
    JSON.stringify(d4) === JSON.stringify(D4_LINES), JSON.stringify(d4));
}
{
  const w = makeWorld({ build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; buildMain(d); } });
  w.run(OVERLAY, "overlay.js");
  const any = TAGGED.map((n) => histLines(w, n));
  ck("C4c. no change log on the page -> no history element in any popover, and no error",
    any.every((x) => x === null) && w.document.querySelectorAll(".pf-history").length === 0 && w.logs.error.length === 0, JSON.stringify(any));
}

/* C6. A said holding markup renders escaped (moved here from the retired marks note check). */
{
  const w = makeWorld({ build: (d, s) => {
    s.PAGE_FEATURES_INLINE = MAIN; buildMain(d);
    s.PAGE_FEATURES_CHANGES = [{ n: 4, said: XSS, at: "2026-10-21T00:00:00Z", by: "bea", route: "page" }];
  } });
  w.run(OVERLAY, "overlay.js");
  w.click(w.badge(4));
  const h = w.pop() && w.pop().querySelector(".pf-history");
  const li = h && h.querySelector("li");
  const whole = w.document.documentElement.innerHTML;
  ck("C6. a said holding <img src=x onerror=...> renders escaped (no \"<img\" in any innerHTML)",
    !!li && li.textContent === "2026-10-21 · bea: " + XSS && !/<img/i.test(whole) && whole.includes("&lt;img src=x onerror=alert(1)&gt;"));
}

/* ===========================================================================
 * PF-2d (overlay remembers settings): a viewer's numbers on/off, filter panel
 * open/closed and kind/state chips survive a reload, per page, in one
 * "pf-prefs:" + path key; storage cleared, broken or throwing -> the defaults.
 * A "reload" is a second world over the SAME store and path.
 * ======================================================================== */
{
  const KEY = "pf-prefs:/fixture.html";
  const open = (store, opts = {}) => {
    const w = makeWorld(Object.assign({ store, build: (d, s) => { s.PAGE_FEATURES_INLINE = MAIN; buildMain(d); } }, opts));
    w.run(OVERLAY, "overlay.js");
    return w;
  };
  const chip = (w, g, v) => w.document.querySelector(v == null ? `[data-pf-group="${g}"][data-pf-all]` : `[data-pf-group="${g}"][data-pf-value="${v}"]`);
  const pressed = (w, g) => w.document.querySelectorAll(`[data-pf-group="${g}"]`)
    .filter((c) => c.getAttribute("aria-pressed") === "true").map((c) => c.textContent).join(",");
  const pbtn = (w) => w.document.querySelector("[data-pf-panel]");
  const bar = (w) => w.document.querySelector("#pf-filters");
  const view = (w) => ({
    numbers: w.api().badges().length > 0, barShown: bar(w).style.display !== "none",
    panel: !bar(w).classList.contains("pf-closed") && pbtn(w).getAttribute("aria-expanded") === "true",
    kind: pressed(w, "kind"), state: pressed(w, "state"),
  });
  const DEFAULT = { numbers: true, barShown: true, panel: true, kind: "All", state: "All" };
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  const fresh = open({});
  ck("D0. defaults: numbers on, panel open (Hide), no chip chosen, every badge drawn",
    same(view(fresh), DEFAULT) && pbtn(fresh).textContent === "Hide" && fresh.api().badges().length === TAGGED.length + 1,
    JSON.stringify(view(fresh)));

  // Kind = A (action) needs an action feature on the page: one more, tagged.
  const store = {};
  const ACT = fixture(MAIN.features.concat([F(21, "action", "wired", { name: "Run it" })]));
  const openA = (s, opts = {}) => {
    const w = makeWorld(Object.assign({ store: s, build: (d, x) => {
      x.PAGE_FEATURES_INLINE = ACT; buildMain(d); add(d.querySelector("#main"), "button", { "data-feature": "21" }, rectAt(7));
    } }, opts));
    w.run(OVERLAY, "overlay.js");
    return w;
  };
  const a = openA(store);
  a.click(chip(a, "kind", "action"));
  ck("D1. kind = A shows only the action badge", a.api().badges().map((b) => b.tag).join() === "A21", a.api().badges().map((b) => b.tag).join());
  a.click(pbtn(a));
  ck("D1b. the panel button closes the filter panel (chips and the tell line hidden by class), labelled Filters",
    bar(a).classList.contains("pf-closed") && pbtn(a).textContent === "Filters" && pbtn(a).getAttribute("aria-expanded") === "false");
  a.key("F");
  const before = view(a);
  ck("D1c. panel off + numbers off + kind = A, stored as one object under " + KEY,
    Object.keys(store).join() === KEY && same(JSON.parse(store[KEY]),
      { numbers: false, panel: "closed", kinds: ["action"], states: ["wired", "after-card", "not-built"] }), JSON.stringify(store));

  const b = openA(store);
  ck("D2. reload (same storage, same path) -> the same state: numbers off, panel closed, kind A chosen",
    same(view(b), before) && before.numbers === false && before.panel === false && before.kind === "A" && before.state === "All",
    JSON.stringify([before, view(b)]));
  b.key("F");
  ck("D2b. ... and numbers back on after the reload still honour kind = A with the panel closed",
    b.api().badges().map((x) => x.tag).join() === "A21" && bar(b).classList.contains("pf-closed"), b.api().badges().map((x) => x.tag).join());

  const c = openA(store, { pathname: "/other-page.html" });
  ck("D3. another page's path does not inherit this page's view", same(view(c), DEFAULT), JSON.stringify(view(c)));

  delete store[KEY];
  const d = openA(store);
  ck("D4. storage cleared -> the defaults", same(view(d), DEFAULT), JSON.stringify(view(d)));

  const throwing = { getItem: () => { throw new Error("SecurityError"); }, setItem: () => { throw new Error("QuotaExceeded"); } };
  const t = open({}, { storage: throwing });
  ck("D5. storage that throws on every call -> the defaults, the page works, no error logged",
    same(view(t), DEFAULT) && t.api().badges().length === TAGGED.length + 1 && t.logs.error.length === 0, JSON.stringify(view(t)));
  t.click(chip(t, "kind", "data")); t.key("F"); t.click(pbtn(t));
  ck("D5b. ... and changing the view with throwing storage still works in the page",
    view(t).numbers === false && view(t).panel === false && view(t).kind === "D" && t.logs.error.length === 0, JSON.stringify(view(t)));

  const g2 = makeWorld({ build: (dd, s) => { s.PAGE_FEATURES_INLINE = MAIN; s.localStorage = undefined; buildMain(dd); } });
  g2.run(OVERLAY, "overlay.js");
  ck("D5c. no localStorage at all -> the defaults, the page works", !!g2.api() && same(view(g2), DEFAULT), JSON.stringify(g2.api() && view(g2)));

  const junk = open({ [KEY]: "{not json" });
  const odd = open({ [KEY]: JSON.stringify({ numbers: "no", panel: "sideways", kinds: ["nope"], states: 7 }) });
  ck("D6. a stored value that is not JSON, or holds unknown values -> the defaults",
    same(view(junk), DEFAULT) && same(view(odd), DEFAULT), JSON.stringify([view(junk), view(odd)]));

  const legacy = open({ "pageFeatures.badges": "0" });
  ck("D7. the old pageFeatures.badges = 0 is read once as the numbers choice when the new key has none",
    view(legacy).numbers === false && view(legacy).panel === true && view(legacy).kind === "All", JSON.stringify(view(legacy)));
  const both = open({ "pageFeatures.badges": "0", [KEY]: JSON.stringify({ numbers: true }) });
  ck("D7b. ... and the new key wins over it when it holds a numbers choice", view(both).numbers === true);
  const ls = {};
  const l2 = open(ls);
  l2.key("F");
  ck("D7c. a change writes only the new key, never the old one", Object.keys(ls).join() === KEY, JSON.stringify(ls));

  const allK = {};
  const w5 = open(allK);
  w5.click(chip(w5, "kind", null));
  const w6 = open(allK);
  ck("D8. kind All stored as every kind reads back as showing every kind",
    w6.api().badges().length === TAGGED.length + 1 && pressed(w6, "kind").startsWith("All"), pressed(w6, "kind"));
}

/* C7. marks.js is retired (kept in git history only). */
ck("C7. marks.js does not exist", !fs.existsSync(path.join(HERE, "marks.js")));

console.log(`\n${passed} ok, ${fails.length} FAIL` + (fails.length ? `: ${fails.join("; ")}` : ""));
process.exit(fails.length ? 1 : 0);
