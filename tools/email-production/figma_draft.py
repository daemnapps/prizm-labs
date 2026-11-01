#!/usr/bin/env python3
"""FIGMA DRAFT — the copy of one slot, laid into the brand's own Figma
template (RULED 2026-09-09: drafts are built directly in Figma from the
templates already in the file; Eve tweaks; Eve puts the finals into Klaviyo).

    python3 figma_draft.py results/<slot> [--brand <brand>] [--template <nodeId>]
                           [--page "Drafts - September 2026 (machine)"] [--col N]
    python3 figma_draft.py results/<slot> --record '<json the connector returned>'

What it does:
  1 reads the slot's live blocks (design.json — made from the chain's BLOCKS
    by design_email.py; made here if missing), the subject and preview
    (stage 5), the open facts, and the slot's calendar row (date, segments,
    type)
  2 picks the template frame in the brand's file whose slot counts are
    nearest the copy's (display / sub / body / button) —
    brands/<brand>/email-sms/design-formats/figma-templates.json, read off the
    file on 2026-09-09; --template overrides
  3 writes results/<slot>/figma-draft.js: the code the Figma connector runs
    (use_figma, fileKey from brands/<brand>/email-sms/machine.json). The code
    clones the template onto the drafts page, names the frame by slot, types
    the copy into the template's text layers top to bottom by kind, marks
    every layer the copy did not need UNUSED, clones the Subject card where
    the file has one, and writes a notes card beside the frame: subject,
    preview, date, segments, open facts, copy that found no layer, pictures
    to place, and the font note
  4 --record stores what the connector returned (frame id, page) in
    results/<slot>/figma-draft.json with the link, so the review page and
    the runbook can point at it

The brand's faces (Untitled Sans, Marlide Display, Inter Tight …) are not
loadable from the connector's runtime — Figma refuses to type into a layer
whose font is not loaded — so the copy is typed in Inter at the same size
and weight, and the notes card tells the designer how to restore the face in
one action. The session runs the connector; nothing here talks to Figma
itself.
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

from paths import HERE, WORKSPACE

DISPLAY, SUB, BODY, CTA = "D", "S", "B", "C"
KIND_OF = {"headline": DISPLAY, "subhead": SUB, "copy": BODY, "quote": BODY, "bullets": BODY,
           "signoff": BODY, "ps": BODY, "button": CTA}


def slot_row(label, brand):
    """The calendar row behind this run: results/calendar-YYYY-MM[-brand]/slots.json."""
    sid = label.split("--")[0]
    if sid.startswith(brand + "-"):              # a second brand's runs carry a <brand>- prefix (run_month.py)
        sid = sid[len(brand) + 1:]
    abbr = sid.split("-")[0]
    for f in sorted(glob.glob(str(HERE / "results" / "calendar-*" / "slots.json")), reverse=True):
        d = json.loads(Path(f).read_text())
        rows = d.get("slots", d) if isinstance(d, dict) else d
        if not rows or not str(rows[0].get("id", "")).startswith(abbr):
            continue
        run = Path(f).parent / "run.json"
        if run.is_file() and json.loads(run.read_text()).get("brand") not in (None, brand):
            continue
        for s in rows:
            if s.get("id") == sid:
                return s, Path(f).parent.name
    return {}, None


def subject_preview(run_dir):
    subj = prev = ""
    f = run_dir / "stage5--subjects.md"
    if f.is_file():
        t = f.read_text()
        m = re.search(r"^\**Subject:?\**\s*[:—-]?\s*(.+)$", t, re.M)     # the first subject the stage offers
        subj = m.group(1).strip() if m else ""
        m = re.search(r"^\**Preview:?\**\s*[:—-]?\s*(.+)$", t, re.M)
        prev = m.group(1).strip() if m else ""
    subj, prev = subj.strip("`* "), prev.strip("`* ")
    if prev.lower().startswith("(none"):            # the stage's note that the source had no preview — not a preview
        prev = ""
    return subj, prev


def text_of(b):
    t = b.get("type")
    if t == "button":
        return b.get("label") or ""
    if t == "bullets":
        items = b.get("items") or []
        return "\n".join(f"• {i}" for i in items) if items else (b.get("text") or "")
    if t == "quote":
        q = (b.get("text") or "").strip()
        who = b.get("attribution") or b.get("who")
        return f"“{q}”" + (f"\n— {who}" if who else "")
    return b.get("text") or ""


def dedupe(blocks):
    """The chain often writes a passage twice: as the pieces (headline, body) and
    again merged into one typographic picture. Keep the first of two identical
    texts; drop a text that wholly contains another block's text."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    out, seen = [], []
    for b in blocks:
        n = norm(b["text"])
        if n in seen:
            continue
        seen.append(n); out.append(b)
    keep = []
    for i, b in enumerate(out):
        n = norm(b["text"])
        twin = any(j != i and len(n) > len(norm(o["text"])) + 20 and norm(o["text"]) in n and o["kind"] != CTA
                   for j, o in enumerate(out))
        if not twin:
            keep.append(b)
    return keep


def pick_template(bank, counts, override=None):
    tpls = bank["templates"]
    if override:
        for t in tpls:
            if t["id"] == override:
                return t
        return {"id": override, "name": override, "D": 0, "S": 0, "B": 0, "C": 0}
    def dist(t):
        d = 0
        for k, w in ((DISPLAY, 3), (SUB, 1), (BODY, 1), (CTA, 2)):
            gap = t.get(k, 0) - counts.get(k, 0)
            d += w * (abs(gap) if gap >= 0 else 2 * abs(gap))   # too few layers costs double
        return (d, t.get("h", 0))
    return min(tpls, key=dist)


JS = r"""
// figma_draft.py — %(slot)s — generated %(stamp)s. Run through the Figma connector (use_figma).
const P = %(payload)s;
const clean = s => String(s == null ? '' : s).replace(/[^\x20-\x7e]/g, '_').slice(0, 90);
// the drafts live on their own page; a file whose plan caps pages gets a SECTION of that name on the fallback page instead
let page = P.hostPage ? null : figma.root.children.find(p => p.name === P.page), container = null;
if (!page && !P.hostPage) { try { page = figma.createPage(); page.name = P.page; } catch (e) { page = null; } }
if (page) { if (page.loadAsync) await page.loadAsync(); container = page; }
else {
  const host = await figma.getNodeByIdAsync(P.hostPage || P.fallbackPage);
  if (host.loadAsync) await host.loadAsync();
  let sec = host.children.find(n => n.type === 'SECTION' && n.name === P.page);
  if (!sec) { sec = figma.createSection(); sec.name = P.page; host.appendChild(sec); let bottom = 0; for (const c of host.children) if (c !== sec) bottom = Math.max(bottom, c.y + c.height); sec.x = 0; sec.y = bottom + 600; }
  container = sec;
}
const old = container.children.filter(n => n.name === P.frameName || n.name.startsWith(P.frameName + ' '));
for (const n of old) n.remove();
const tpl = await figma.getNodeByIdAsync(P.template);
if (!tpl) throw new Error('template not found: ' + P.template);
const frame = tpl.clone(); container.appendChild(frame);
frame.x = P.col * 760; frame.y = 320; frame.name = P.frameName;
const styleFor = fn => { const s = (fn && fn.style) || ''; return /bold|black|heavy|extra/i.test(s) ? 'Bold' : /medium|semi|demi/i.test(s) ? 'Medium' : 'Regular'; };
for (const st of ['Regular', 'Medium', 'Bold']) await figma.loadFontAsync({family: 'Inter', style: st});
const skipNames = /footer|logo|header|nav|social|unsubscribe/i;
const inSkipped = n => { let p = n.parent; while (p && p !== frame) { if (skipNames.test(p.name)) return true; p = p.parent; } return false; };
const absY = n => n.absoluteTransform[1][2];
const layers = frame.findAll(n => n.type === 'TEXT' && !inSkipped(n)).map(n => {
  const fs = n.fontSize === figma.mixed ? 20 : n.fontSize;
  const pn = (n.parent && n.parent.name) || '';
  const chars = n.characters.trim();
  let kind;
  if (/cta|button/i.test(pn) || (/^[A-Z0-9 !'&\-_>]{6,}$/.test(chars) && fs <= 24 && chars.length < 40)) kind = 'C';
  else if (fs >= 40) kind = 'D'; else if (fs >= 26) kind = 'S'; else if (fs >= 15) kind = 'B'; else kind = 'F';
  return {n, kind, fs, y: absY(n)};
}).filter(l => l.kind !== 'F').sort((a, b) => a.y - b.y);
const queues = {D: [], S: [], B: [], C: []};
for (const b of P.blocks) if (queues[b.kind]) queues[b.kind].push(b);
const fallback = {D: ['S', 'B'], S: ['D', 'B'], B: ['S', 'D'], C: []};
const reflow = (n, delta) => {              // absolute layouts do not reflow: push what sits below, grow the containers
  if (delta <= 0) return;
  let node = n;
  while (node && node !== frame) {
    const par = node.parent; if (!par) break;
    if (!par.layoutMode || par.layoutMode === 'NONE') {
      for (const c of par.children) if (c !== node && c.y > node.y + 1) c.y += delta;
      if (par.type === 'FRAME' || par.type === 'COMPONENT' || par.type === 'INSTANCE') { try { par.resize(par.width, par.height + delta); } catch (e) {} }
    }
    node = par;
  }
};
const setText = (n, text) => {
  const fn = n.fontName === figma.mixed ? n.getRangeFontName(0, 1) : n.fontName;
  const h0 = n.height;
  n.fontName = {family: 'Inter', style: styleFor(fn)};
  if (n.textAutoResize === 'NONE' || n.textAutoResize === 'TRUNCATE') n.textAutoResize = 'HEIGHT';
  n.characters = text;
  reflow(n, n.height - h0);
};
let filled = 0, unused = 0;
for (const l of layers) {
  let b = queues[l.kind].shift();
  if (!b) for (const alt of fallback[l.kind]) { if (queues[alt].length) { b = queues[alt].shift(); break; } }
  if (b) { setText(l.n, b.text); l.n.name = 'COPY ' + b.kind + ' ' + clean(b.text).slice(0, 30); filled++; }
  else { setText(l.n, '[UNUSED - delete]'); l.n.name = 'UNUSED - delete'; unused++; }
}
const leftover = [].concat(queues.D, queues.S, queues.B, queues.C);
let subjectId = null;
if (P.subjectGroup) {
  const sg = await figma.getNodeByIdAsync(P.subjectGroup);
  if (sg) { const s = sg.clone(); container.appendChild(s); s.x = frame.x; s.y = frame.y - s.height - 20; s.name = P.frameName + ' subject';
    for (const t of s.findAll(n => n.type === 'TEXT')) { if (t.characters.trim() !== 'Subject') setText(t, P.subject || '[subject]'); }
    subjectId = s.id; }
}
const notes = figma.createText(); container.appendChild(notes);
notes.x = frame.x + 640; notes.y = frame.y; notes.resize(400, 100); notes.textAutoResize = 'HEIGHT';
notes.fontName = {family: 'Inter', style: 'Regular'}; notes.fontSize = 13; notes.name = P.frameName + ' notes';
const L = [];
L.push(P.frameName); L.push('');
L.push('SUBJECT: ' + (P.subject || '[none]')); L.push('PREVIEW: ' + (P.preview || '[none]'));
L.push('SEND: ' + P.date + '  TO: ' + P.segments); L.push('TYPE: ' + P.type + (P.avatar ? '  VOICE: ' + P.avatar : '')); L.push('');
L.push('TEMPLATE: ' + P.templateName + ' (' + filled + ' layers filled, ' + unused + ' unused' + (leftover.length ? ', ' + leftover.length + ' copy blocks below found no layer' : '') + ')');
L.push('FONT: copy is typed in Inter because the connector cannot load ' + P.faces + '. Click any copy layer > Edit > Select all with same font > set the family back.'); L.push('');
if (P.openFacts.length) { L.push('OPEN FACTS (a person closes these before send):'); for (const o of P.openFacts) L.push(' - ' + o); L.push(''); }
if (leftover.length) { L.push('COPY WITHOUT A LAYER:'); for (const b of leftover) L.push(' [' + b.kind + '] ' + b.text); L.push(''); }
if (P.pictures.length) { L.push('PICTURES:'); for (const p of P.pictures) L.push(' - ' + p); L.push(''); }
L.push('Built by the email machine from ' + P.runDir + '. Template pictures are the template\'s own - swap them.');
notes.characters = L.join('\n');
try { const r = figma.createRectangle(); container.appendChild(r); r.x = notes.x - 16; r.y = notes.y - 16; r.resize(432, notes.height + 32); r.fills = [{type: 'SOLID', color: {r: 1, g: 0.97, b: 0.85}}]; r.name = P.frameName + ' notes bg'; container.insertChild(container.children.indexOf(notes), r); } catch (e) {}
if (container.type === 'SECTION') { let w = 0, h = 0; for (const c of container.children) { w = Math.max(w, c.x + c.width); h = Math.max(h, c.y + c.height); } container.resizeWithoutConstraints(w + 120, h + 120); }
return {page: container.id, container: container.type, frame: frame.id, notes: notes.id, subject: subjectId, filled, unused, leftover: leftover.length, template: P.template};
"""


def build(run_dir, brand, template=None, page=None, col=None):
    run = json.loads((run_dir / "run.json").read_text())
    label = run.get("label") or run_dir.name
    dj = run_dir / "design.json"
    if not dj.is_file():
        import design_email
        design_email.design(run_dir, brand)
    d = json.loads(dj.read_text())
    blocks = []
    for b in d.get("blocks", []):
        k = KIND_OF.get(b.get("type"))
        t = text_of(b).strip()
        if k and t:
            blocks.append({"kind": k, "text": t})
    blocks = dedupe(blocks)
    counts = {k: sum(1 for b in blocks if b["kind"] == k) for k in (DISPLAY, SUB, BODY, CTA)}
    bank = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "design-formats" / "figma-templates.json").read_text())
    machine = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "machine.json").read_text())
    tpl = pick_template(bank, counts, template)
    subj, prev = subject_preview(run_dir)
    if not prev:
        prev = next((b.get("text") for b in d.get("blocks", []) if b.get("type") == "preheader"), "") or ""
    row, month_dir = slot_row(label, brand)
    sid = label.split("--")[0]
    if sid.startswith(brand + "-"):
        sid = sid[len(brand) + 1:]
    variant = label.split("--")[1] if "--" in label else ""
    month = (row.get("date") or "")[:7] or "month"
    page = page or f"Drafts - {month} (machine)"
    if col is None:                      # one column per run, in the month's order (variants side by side)
        abbr = sid.split("-")[0]
        pre = label[: len(label) - len(label.split("--")[0])] if False else (brand + "-" if label.startswith(brand + "-") else "")
        runs = sorted(p.name for p in (HERE / "results").glob(f"{pre}{abbr}-*") if (p / "run.json").is_file()
                      and (pre or not p.name.startswith(brand + "-")))
        col = runs.index(run_dir.name) if run_dir.name in runs else 0
    frame_name = f"{sid.upper()} | {row.get('date', '')} | {row.get('type', '')}" + (f" | {variant}" if variant else "")
    pictures = []
    for p in d.get("pictures", []):
        if p.get("kind") == "product photo":
            pictures.append(f"product photo: {p.get('alt')} ({p.get('source')})")
        else:
            pictures.append(f"to make: {(p.get('brief') or p.get('alt') or '')[:160]}")
    payload = {"page": page, "template": tpl["id"], "templateName": tpl.get("name", tpl["id"]),
               "subjectGroup": tpl.get("subject_group"), "frameName": frame_name, "col": col,
               "blocks": blocks, "subject": subj, "preview": prev, "date": row.get("date", ""),
               "segments": ", ".join(row.get("segments") or []), "type": row.get("type", ""),
               "avatar": variant, "openFacts": d.get("open_facts", []), "pictures": pictures,
               "faces": ", ".join(bank.get("faces", [])), "runDir": f"results/{run_dir.name}",
               "fallbackPage": bank.get("drafts_fallback_page"), "hostPage": bank.get("drafts_host_page")}
    import datetime
    js = JS % {"slot": label, "stamp": datetime.date.today().isoformat(), "payload": json.dumps(payload, ensure_ascii=False)}
    (run_dir / "figma-draft.js").write_text(js.strip() + "\n")
    print(f"{label}: counts {counts} -> template {tpl.get('name')} [{tpl['id']}] · page “{page}” col {col} · "
          f"{len(blocks)} blocks · fileKey {machine.get('figma_file', {}).get('key')}")
    return payload


def record(run_dir, brand, result):
    machine = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "machine.json").read_text())
    key = machine.get("figma_file", {}).get("key")
    r = json.loads(result)
    node = r.get("frame", "").replace(":", "-")
    r["url"] = f"https://www.figma.com/design/{key}/?node-id={node}" if key and node else None
    r["brand"] = brand
    import datetime
    r["built"] = datetime.datetime.now().isoformat(timespec="minutes")
    (run_dir / "figma-draft.json").write_text(json.dumps(r, indent=1) + "\n")
    print(r["url"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--brand", default=None)
    ap.add_argument("--template", default=None)
    ap.add_argument("--page", default=None)
    ap.add_argument("--col", type=int, default=None)
    ap.add_argument("--record", default=None, help="json the connector returned; writes figma-draft.json")
    a = ap.parse_args()
    rd = Path(a.run_dir)
    if not rd.is_absolute():
        rd = HERE / rd
    sys.path.insert(0, str(HERE / "machine"))
    import brand_facts as BF
    brand = BF.run_brand(rd, a.brand)
    if a.record:
        record(rd, brand, a.record)
    else:
        build(rd, brand, a.template, a.page, a.col)


if __name__ == "__main__":
    main()
