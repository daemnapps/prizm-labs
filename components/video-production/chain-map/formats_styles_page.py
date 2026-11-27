#!/usr/bin/env python3
"""The owner's formats-and-looks page, drawn in pictures: the format x look matrix (a real swipe frame for every
format, the swatch for every look, a still from an ad we made wherever we made one), what the body says, how it
opens, every look, his calls (defaults pre-filled, saved through the page's own store) and batch 1.
Reads chains/<chain>-format-style-calls.json, the locked names in components/video-production/formats/names.json and the pictures; writes
runs/stage-handoff/<chain>/formats-styles.html (pictures embedded) and formats-styles.md (the team's copy).

    python3 components/video-production/chain-map/formats_styles_page.py [video]
"""
import base64
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "components" / "stage-handoff"          # the page data stays there (folded 2026-11-19)
WORK = "runs/video-teardown/_work/"


def thumb(rel, w=240):
    """A small JPEG of a repo-relative picture, as a data URI; None when the picture is not on this machine."""
    p = REPO / rel
    if not p.is_file():
        return None
    im = Image.open(p).convert("RGB")
    h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


CSS = """
:root{--bg:#f6f6f4;--card:#fff;--fg:#17171a;--mute:#6b6b73;--line:#e2e2e0;--accent:#2f5bea;--accent-soft:#e9eefd;
--ok:#15803d;--ok-soft:#dcf5e3;--warn:#b45309;--warn-soft:#fdf0d2;--bad:#b91c1c;--bad-soft:#fde2e2;--na:#ececea;
--f-head:"Space Grotesk",system-ui,sans-serif;--f-body:"Inter",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d0d0f;--card:#17171b;--fg:#f3f3f4;--mute:#a0a0a8;
--line:#2a2a30;--accent:#7c9cff;--accent-soft:#1a2240;--ok:#4ade80;--ok-soft:#0f2e1b;--warn:#fbbf24;--warn-soft:#30250a;
--bad:#f87171;--bad-soft:#371313;--na:#1f1f24;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0d0d0f;--card:#17171b;--fg:#f3f3f4;--mute:#a0a0a8;--line:#2a2a30;--accent:#7c9cff;
--accent-soft:#1a2240;--ok:#4ade80;--ok-soft:#0f2e1b;--warn:#fbbf24;--warn-soft:#30250a;--bad:#f87171;--bad-soft:#371313;
--na:#1f1f24;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--f-body);font-size:15px;line-height:1.4}
.wrap{max-width:1180px;margin:0 auto;padding-block:20px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));
padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;grid-template-columns:minmax(0,1fr);gap:36px}
h1,h2{font-family:var(--f-head);margin:0;text-wrap:balance}
h1{font-size:28px;letter-spacing:-.01em}h2{font-size:20px}
.sub{color:var(--mute);font-size:13px}
section{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;min-width:0}
.top{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:grid;gap:4px;min-width:0}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mute)}
.tile .v{font-family:var(--f-head);font-size:18px}
.tile.now{border-color:var(--accent);background:var(--accent-soft)}
a.tile{color:inherit;text-decoration:none}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--mute)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.d-hand{background:var(--warn)}.d-proof{background:var(--accent)}.d-block{background:var(--bad)}.d-na{background:var(--line)}
.d-made{background:var(--ok)}
/* the matrix */
.mx-wrap{overflow-x:auto;padding-bottom:6px}
.mx{display:grid;grid-template-columns:160px repeat(6,minmax(120px,1fr));gap:6px;min-width:920px}
.corner{display:grid;align-content:space-between;font-size:12px;font-weight:700;color:var(--mute);padding:4px}
.corner span:first-child{text-align:right}
.cell.empty{background:var(--na);display:grid;place-items:center;color:var(--mute);cursor:default}
.cell.made{background:var(--card)}
.mx .cell.empty{justify-content:center;align-items:center}
.cell .badge{position:absolute;top:6px;left:6px;font-size:11.5px;font-weight:700;background:var(--ok);color:#fff;border-radius:6px;padding:2px 7px}
.cell .how{position:relative;margin:6px;padding:3px 7px;border-radius:6px;font-size:11px;font-weight:600;background:var(--card);color:var(--fg);align-self:flex-start}
.cell .how.chain{background:var(--accent);color:#fff}
.ch{display:grid;gap:4px;align-content:end;font-size:12px;font-weight:600}
.ch .sw{height:96px}
.ch .sw img{width:100%;object-fit:cover;border-radius:6px;height:96px;display:block}
.ch small{font-weight:400;color:var(--mute)}
.ch.proven .sw{outline:2px solid var(--ok);outline-offset:2px;border-radius:6px}
.rh{position:sticky;left:0;z-index:2;display:grid;grid-template-columns:56px 1fr;gap:8px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px}
.rh img{width:56px;height:110px;object-fit:cover;border-radius:6px}
.rh b{font-family:var(--f-head);font-size:14px;display:block}
.rh span{font-size:11.5px;color:var(--mute);display:block}
.rh .w{color:var(--fg);font-weight:600;margin-top:4px}
.cell{border-radius:10px;min-height:150px;position:relative;overflow:hidden;cursor:pointer;display:flex;flex-direction:column;justify-content:flex-end}
.cell:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.cell.hand{background:var(--warn-soft)}.cell.proof{background:var(--accent-soft)}.cell.block{background:var(--bad-soft)}
.cell.na{background:var(--na)}
.cell .pics{position:absolute;inset:0;display:flex;gap:2px}
.cell .pics img{flex:1;min-width:0;object-fit:cover;height:100%}
.cell .lab{position:relative;margin:6px;padding:4px 7px;border-radius:7px;font-size:11.5px;font-weight:600;background:var(--card);color:var(--fg);
display:flex;align-items:center;gap:5px;align-self:flex-start;max-width:calc(100% - 12px)}
.cell .need{display:none;position:relative;margin:0 6px 6px;padding:6px 7px;border-radius:7px;font-size:11.5px;background:var(--card);color:var(--fg)}
.cell.open .need{display:block}
.cell .made{position:absolute;top:6px;left:6px;font-size:11px;font-weight:700;background:var(--ok);color:#fff;border-radius:6px;padding:2px 6px}
/* strips */
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;display:grid;align-content:start;min-width:0}
.card img{width:100%;aspect-ratio:9/14;object-fit:cover;display:block}
.card .ph{aspect-ratio:9/14;display:grid;place-items:center;background:var(--na);color:var(--mute);font-size:12px;text-align:center;padding:8px}
.card .cap{padding:7px 9px;font-size:12.5px;font-weight:600;display:grid;gap:2px}
.card .cap span{font-weight:400;color:var(--mute);font-size:11.5px}
.card.proven{border-color:var(--ok);box-shadow:0 0 0 1px var(--ok)}
.looks{grid-template-columns:repeat(auto-fill,minmax(96px,1fr))}
.looks .card img,.looks .card .ph{aspect-ratio:1/1}
/* groups */
.gh{grid-column:1/-1;margin:8px 0 0;font-family:var(--f-head);font-size:15px;color:var(--mute)}
/* names */
.names{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.names div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:grid;gap:2px}
.names b{font-family:var(--f-head);font-size:16px}.names span{color:var(--mute);font-size:12px}.names p{margin:6px 0 0;font-size:13.5px}
/* calls */
.bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button{font:inherit;cursor:pointer;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:8px 12px}
button:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
button[disabled]{opacity:.5;cursor:default}
.calls{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.call{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;gap:10px;align-content:start;min-width:0}
.call.saved{border-color:var(--ok)}
.call .hd{display:flex;gap:8px;align-items:baseline}
.id{font-family:var(--f-head);font-size:12px;font-weight:700;color:var(--mute);min-width:24px}
.call .t{font-family:var(--f-head);font-weight:600;font-size:16px}
.call .cp{display:flex;gap:4px}
.call .cp img{flex:1;min-width:0;height:96px;object-fit:cover;border-radius:6px}
.call ul{margin:0;padding-left:18px;display:grid;gap:3px;font-size:13px}
.ifs{display:grid;gap:4px;font-size:12.5px;background:var(--bg);border-radius:6px;padding:8px}
.rev{font-size:12.5px;background:var(--warn-soft);color:var(--warn);border-radius:6px;padding:6px 8px}
.seg{display:flex;gap:6px}.seg button{flex:1}
.seg button.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.note{width:100%;box-sizing:border-box;font:inherit;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg)}
.state{font-size:12px;color:var(--ok)}
/* batch */
.lanes{display:grid;gap:14px}
.lane{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;display:grid;gap:10px;min-width:0}
.lane .eq{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:13px;font-weight:600}
.lane .eq .x{color:var(--mute);font-weight:400}
.chip{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:3px 10px;background:var(--bg)}
.chip.need{border-color:var(--warn);color:var(--warn);background:transparent}
.lane .briefs{display:grid;grid-template-columns:repeat(auto-fill,minmax(84px,1fr));gap:6px}
.lane .briefs .card .cap{font-size:10.5px;font-weight:500;word-break:break-word}
@media (max-width:640px){.top{grid-template-columns:1fr}h1{font-size:23px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = r"""
const D = JSON.parse(document.getElementById('data').textContent);
const P = D.pics, picks = {};
let db = null;
const el = (t, a = {}, ...kids) => { const e = document.createElement(t);
  for (const [k, v] of Object.entries(a)) { if (k === 'class') e.className = v; else if (k.startsWith('on')) e[k] = v; else e.setAttribute(k, v); }
  for (const k of kids) if (k != null) e.append(k); return e; };
const img = (key, alt) => P[key] ? el('img', {src: P[key], alt: alt || '', loading: 'lazy'}) : null;
const fmt = id => D.lists.production.find(p => p.id === id) || {name: id};

function matrix() {
  const g = D.grid, m = document.getElementById('mx');
  m.append(el('div', {class: 'corner'}, el('span', {}, 'Style →'), el('span', {}, 'Production format ↓')));
  for (const c of g.columns) m.append(el('div', {class: 'ch'}, el('div', {class: 'sw'}, img(c.pic, c.name)), el('div', {}, c.name)));
  for (const r of g.rows) {
    const p = fmt(r.format);
    m.append(el('div', {class: 'rh'}, img('f-' + r.format, p.name),
      el('div', {}, el('b', {}, p.name), el('span', {}, p.what), r.waiting ? el('span', {class: 'w'}, r.waiting + ' briefs waiting') : null)));
    for (const c of g.columns) {
      const x = r.cells[c.id];
      if (!x) { m.append(el('div', {class: 'cell empty'}, el('span', {}, '—'))); continue; }
      const pics = el('div', {class: 'pics'}); x.pics.forEach(k => { const i = img(k, ''); if (i) pics.append(i); });
      m.append(el('div', {class: 'cell made'}, pics, el('span', {class: 'badge'}, '✓ ' + x.made + ' made'),
        el('span', {class: 'how ' + x.how.replace(' ', '-')}, g.how[x.how])));
    }
  }
}

function strip(id, items) {
  const box = document.getElementById(id);
  for (const it of items) box.append(el('div', {class: 'card'}, img(it.pic, it.name), el('div', {class: 'cap'}, it.name)));
}

function renderCalls() {
  const box = document.getElementById('calls'); box.textContent = '';
  const GH = {hook: 'Decided · hook formats added (tap Undo if wrong)', script: 'Decided · script formats added',
              headline: 'Decided · headline formats added (the words first)',
              length: 'Decided · a new setting', undefined: 'Your call · the spend'};
  let last = null;
  for (const c of D.calls) {
    if (c.group !== last) { box.append(el('h3', {class: 'gh'}, GH[c.group] || 'The spend')); last = c.group; }
    const p = picks[c.id] || {}, pick = p.pick || 'yes';
    const card = el('div', {class: 'call' + (p.pick ? ' saved' : '')});
    card.append(el('div', {class: 'hd'}, el('span', {class: 'id'}, c.id), el('span', {class: 't'}, c.title)));
    if (c.pics) { const cp = el('div', {class: 'cp'}); c.pics.forEach(k => { const i = img(k, ''); if (i) cp.append(i); }); card.append(cp); }
    const ul = el('ul'); c.yes.forEach(y => ul.append(el('li', {}, y))); card.append(ul);
    if (c.reverses) card.append(el('div', {class: 'rev'}, '↺ ' + c.reverses));
    const seg = el('div', {class: 'seg'});
    if (c.thens) card.append(el('div', {class: 'ifs'}, ...c.options.map((o, i) => el('div', {}, el('b', {}, o[1] + ' → '), c.thens[i]))));
    else if (c.if_yes) card.append(el('div', {class: 'ifs'}, el('div', {}, el('b', {}, (c.options || [])[0][1] + ' → '), c.if_yes),
      el('div', {}, el('b', {}, (c.options || [])[1][1] + ' → '), c.if_no)));
    for (const [v, lab] of (c.options || [['yes', 'Yes'], ['change', 'Change']]))
      seg.append(el('button', {class: p.pick === v ? 'on' : '', type: 'button', onclick: () => save(c.id, v, (picks[c.id] || {}).note || '')}, lab));
    card.append(seg);
    if (pick === 'change') {
      const inp = el('input', {class: 'note', id: 'note-' + c.id, 'aria-label': 'What to change on ' + c.id});
      inp.value = p.note || ''; inp.onchange = () => save(c.id, 'change', inp.value); card.append(inp);
    }
    if (p.pick) card.append(el('div', {class: 'state'}, '✓ saved'));
    box.append(card);
  }
  const n = D.calls.filter(c => picks[c.id]).length;
  document.getElementById('count').textContent = n + ' of ' + D.calls.length + ' saved';
  document.getElementById('lockall').disabled = !db || n === D.calls.length;
}
async function save(id, pick, note) {
  picks[id] = {pick, note}; renderCalls();
  if (!db) return;
  try { await db.doc('calls/' + id).set({pick, note: note || '', at: new Date().toISOString()}); }
  catch (e) { document.getElementById('count').textContent = 'Could not save: ' + (e && e.message || e); }
}
async function lockAll() { for (const c of D.calls) if (!picks[c.id]) await save(c.id, (c.options || [['yes']])[0][0], ''); }

function batch() {
  const box = document.getElementById('lanes');
  const look = id => (D.lists.looks.find(l => l.id === id) || {name: id}).name;
  const scr = id => (D.lists.script.find(l => l.id === id) || {name: id}).name;
  for (const l of D.batch1.lanes) {
    l.needs = l.needs || [];
    const eq = el('div', {class: 'eq'}, el('span', {class: 'chip'}, scr(l.script)), el('span', {class: 'x'}, '×'),
      el('span', {class: 'chip'}, fmt(l.production).name), el('span', {class: 'x'}, '×'),
      el('span', {class: 'chip'}, look(l.style)), el('span', {class: 'x'}, '= ' + l.briefs.length + ' ads'));
    l.needs.forEach(n => eq.append(el('span', {class: 'chip need'}, 'needs ' + n)));
    const bs = el('div', {class: 'briefs'});
    l.briefs.forEach(b => bs.append(el('div', {class: 'card'}, img('b:' + b, b) || el('div', {class: 'ph'}, 'written first'),
      el('div', {class: 'cap'}, b.split('/').pop()))));
    box.append(el('div', {class: 'lane'}, eq, bs));
  }
}

function filed() {
  const box = document.getElementById('filed'); if (!box) return;
  for (const f of D.filed || []) box.append(el('div', {class: 'card'}, img(f.pic, f.name) || el('div', {class: 'ph'}, ''),
    el('div', {class: 'cap'}, f.name, el('span', {}, '= ' + f.is.join(' + ') + ' · ' + f.n + ' videos'))));
}
filed();
matrix(); strip('scripts', D.lists.script); strip('hooks', D.lists.hook || []); renderCalls(); batch();
document.getElementById('lockall').onclick = lockAll;
(async () => {
  try {
    db = await claude.use('db');
    if (!db) { document.getElementById('count').textContent = 'Read-only here: open the page signed in to save'; return; }
    const timer = setTimeout(() => { document.getElementById('count').textContent = 'Saved calls did not load; tap again to save'; }, 10000);
    db.collection('calls').onSnapshot(snap => {
      clearTimeout(timer);
      snap.docs.forEach(d => { const v = d.data(); picks[d.id] = {pick: v.pick, note: v.note || ''}; });
      renderCalls();
    }, () => clearTimeout(timer));
    renderCalls();
  } catch (e) { /* stays read-only */ }
})();
"""


def build(chain="video"):
    d = json.loads((DATA / "chains" / ("%s-format-style-calls.json" % chain)).read_text(encoding="utf-8"))
    # names come only from the locked names file; a name it does not hold stops the build
    locked = json.loads((REPO / "components" / "video-production" / "formats" / "names.json").read_text(encoding="utf-8"))
    for kind, key in (("production_format", "production"), ("style", "looks"), ("script_format", "script"),
                      ("hook_format", "hook")):
        byid = {n["id"]: n for n in locked[kind]["names"]}
        for x in d["lists"][key]:
            if x["id"] not in byid:
                raise SystemExit("%s %r is not in components/video-production/formats/names.json" % (kind, x["id"]))
            x["name"] = byid[x["id"]]["name"]
            if byid[x["id"]].get("what"):
                x["what"] = byid[x["id"]]["what"]
    for c in d["grid"]["columns"]:
        c["name"] = next(x["name"] for x in d["lists"]["looks"] if x["id"] == c["id"])
    pics = {k: thumb(rel, 300 if k.startswith("f-") else 260) for k, rel in d["pictures"].items()}
    for l in d["batch1"]["lanes"]:
        for b in l["briefs"]:
            if "/" in b:
                pics["b:" + b] = thumb(WORK + b.split("/", 1)[1] + "/poster.jpg", 160)
    pics = {k: v for k, v in pics.items() if v}
    lanes = d["batch1"]["lanes"]
    n_ads = sum(len(l["briefs"]) for l in lanes)
    n_made = sum(x["made"] for r in d["grid"]["rows"] for x in r["cells"].values())
    data = json.dumps({"calls": d["calls"], "grid": d["grid"], "batch1": d["batch1"], "lists": d["lists"], "pics": pics,
                       "filed": d.get("filed") or []},
                      ensure_ascii=False).replace("</", "<\\/")

    page = """<title>Video Formats and Styles</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap">
<style>%(css)s</style>
<div class="wrap">
 <header style="display:grid;gap:6px">
  <h1>What we can make</h1>
  <div class="sub">Every ad = production format (left, how it's made) × style (top, what it looks like). Only what has made a finished video is here: %(nmade)d.</div>
 </header>
 <section class="top" aria-label="What needs you">
  <a class="tile now" href="#calls-h"><span class="k">Now · your calls</span><span class="v">1 call: batch 1</span><span class="sub">The rest is decided; Undo if wrong</span></a>
  <div class="tile"><span class="k">Then · batch 1</span><span class="v">%(nads)d ads · stop at $%(cap)d</span><span class="sub">After the Black Friday briefs</span></div>
  <div class="tile"><span class="k">After · biggest unlock</span><span class="v">Narrator montage</span><span class="sub">19 briefs waiting; onto the chain</span></div>
 </section>
 <section>
  <h2>The matrix</h2>
  <div class="legend"><span><i class="dot d-made"></i>Finished ads in this pairing</span><span><i class="dot d-proof"></i>On the line = the video chain makes it</span>
   <span><i class="dot d-na"></i>— = never made</span></div>
  <div class="mx-wrap"><div class="mx" id="mx"></div></div>
  <div class="sub">Left: a real swipe of each production format. Top and boxes: frames from our own finished videos.</div>
 </section>
 <section>
  <h2>Script formats</h2>
  <div class="sub">What the ad says. Rides on any box above.</div>
  <div class="strip" id="scripts"></div>
 </section>
 <section>
  <h2>Hook formats</h2>
  <div class="sub">The scroll stopper: the first seconds, made differently from the body, ending where the pitch starts. Only some ads have one.</div>
  <div class="strip" id="hooks"></div>
 </section>
 <section>
  <h2>Headline formats</h2>
  <div class="sub">The words first, spoken or on screen. Only some ads have them.</div>
  <div class="names"><div><p>%(hl)s</p></div></div>
 </section>
 <section>
  <h2>The names</h2>
  <div class="names">
   <div><b>Production format</b><span>how it's made</span><p>%(pf)s</p></div>
   <div><b>Style</b><span>what it looks like</span><p>%(st)s</p></div>
   <div><b>Script format</b><span>what it says</span><p>%(sc)s</p></div>
   <div><b>Hook format</b><span>the scroll stopper, when there is one</span><p>%(hk)s</p></div>
  </div>
  <div class="sub">Locked. These names, and only these, on every page, brief and run. Kept in the video process at components/video-production/formats/names.json, beside the format bank.</div>
 </section>
 <section>
  <div class="bar"><h2 id="calls-h">Decided, for your review</h2><span class="sub">I answered these myself by your rules; Undo any that are wrong. Only the spend is yours.</span><button id="lockall" type="button" hidden>Keep all</button><span class="sub" id="count"></span></div>
  <div class="calls" id="calls"></div>
 </section>
 <section>
  <h2>Already on the list</h2>
  <div class="sub">%(filed)s</div>
  <div class="strip" id="filed"></div>
 </section>
 <section>
  <h2>Batch 1 · %(nads)d ads</h2>
  <div class="sub">Each row: script format × production format × style. Every brief already written and carries all three names.</div>
  <div class="lanes" id="lanes"></div>
 </section>
</div>
<script type="application/json" id="data">%(data)s</script>
<script>%(js)s</script>
""" % {"css": CSS, "ncalls": len(d["calls"]), "nads": n_ads, "cap": d["batch1"]["cap_usd"], "nmade": n_made,
       "pf": " · ".join(html.escape(x["name"]) for x in d["lists"]["production"]),
       "st": " · ".join(html.escape(x["name"]) for x in d["lists"]["looks"]),
       "sc": " · ".join(html.escape(x["name"]) for x in d["lists"]["script"]),
       "hk": " · ".join(html.escape(x["name"]) for x in d["lists"].get("hook") or []),
       "filed": html.escape(d.get("filed_summary") or ""),
       "hl": " · ".join(html.escape(x["name"]) for x in d["lists"].get("headline") or []),
       "data": data, "js": JS}

    fname = {p["id"]: p["name"] for p in d["lists"]["production"]}
    cols = d["grid"]["columns"]
    md = ["# Video formats and looks (%s)" % d["as_of"], "", d["_what"], "", d["used_rule"], "",
          "## The owner's calls (default: yes)", ""]
    for c in d["calls"]:
        md.append("- **%s %s**: %s%s" % (c["id"], c["title"], "; ".join(c["yes"]),
                                         (" _Reverses: %s_" % c["reverses"]) if c.get("reverses") else ""))
    md += ["", "## Matrix (finished videos)", "", "| Production format | " + " | ".join(c["name"] for c in cols) + " |",
           "|---|" + "---|" * len(cols)]
    for r in d["grid"]["rows"]:
        cells = ["%d (%s)" % (r["cells"][c["id"]]["made"], r["cells"][c["id"]]["how"]) if c["id"] in r["cells"] else "-"
                 for c in cols]
        md.append("| %s | %s |" % (fname[r["format"]], " | ".join(cells)))
    md += ["", d["grid"]["note"], "", "## Shelved (off the screen)", ""] + ["- %s: %s" % kv for kv in d["lists"]["shelved"].items()]
    md += ["", "## Batch 1", "", "Starts %s. Cap $%d ($%d an ad), %d ads. %s" % (
        d["batch1"]["starts"], d["batch1"]["cap_usd"], d["batch1"]["per_ad_usd"], n_ads, d["batch1"]["checks"]), ""]
    for l in lanes:
        md.append("- %s x %s x %s%s: %s" % (l["script"], fname[l["production"]], l["style"],
                                           (" (needs %s)" % ", ".join(l.get("needs") or [])) if l.get("needs") else "", ", ".join(l["briefs"])))
    md += ["", "## After the calls", ""] + ["- " + x for x in d["after_calls"]]
    md += ["", "## Pictures", ""] + ["- %s: %s" % kv for kv in d["pictures"].items()]

    out = REPO / "runs" / "stage-handoff" / chain
    out.mkdir(parents=True, exist_ok=True)
    (out / "formats-styles.html").write_text(page, encoding="utf-8")
    (out / "formats-styles.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return out / "formats-styles.html"


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "video"))
