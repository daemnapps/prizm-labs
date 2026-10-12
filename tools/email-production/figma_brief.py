#!/usr/bin/env python3
"""FIGMA BRIEF — what the designer actually gets (RULED 2026-09-09, the owner,
superseding the draft-building step: "the actual designing of what you're
doing looks like dog shit... it's more about just mapping out that month. We
can still put the copy in Figma and pull in a reference email we've already
created, so the designer has something to work with. Then look at the
construct of that email, do a teardown on that, and see how we can inject
copy based on the framework of those emails.").

    python3 figma_brief.py results/<slot> [--brand <brand>] [--reference <nodeId>]
    python3 figma_brief.py results/<slot> --record '<json the connector returned>'

Per slot, three things land side by side on the month's Figma page:

  1 THE REFERENCE — an untouched copy of a real email the brand already
    designed, the one this slot is modelled on. Named
    "REF <name> (do not edit)". Nothing is typed into it.
  2 THE TEARDOWN — that reference read as a framework: every slot in it, in
    reading order, with what it is (display / sub / body / button / picture)
    and how big it runs (words, or pixels for a picture). Read off the frame
    itself, so it is true of that email and no other.
  3 THE INJECTION — our copy mapped onto that framework, slot by slot: this
    headline goes in slot 2, this body in slot 5, this button label in slot
    7; a framework slot our copy does not fill says so; copy the framework
    has no slot for is listed at the end as the extra the email needs room
    for. Then the send facts (subject, preview, date, segments), the open
    facts a person must close, and the pictures to place.

The designer builds the email. The machine never does.
"""
import argparse
import datetime
import glob
import json
import re
import sys
from pathlib import Path

from paths import HERE, WORKSPACE


def _bf():
    """Brand words and a run's own brand, read at run time (machine/brand_facts.py)."""
    sys.path.insert(0, str(HERE / "machine"))
    import brand_facts
    return brand_facts

DISPLAY, SUB, BODY, CTA = "D", "S", "B", "C"
KIND_OF = {"headline": DISPLAY, "subhead": SUB, "copy": BODY, "quote": BODY, "bullets": BODY,
           "signoff": BODY, "ps": BODY, "button": CTA}
KIND_NAME = {DISPLAY: "display", SUB: "subhead", BODY: "body", CTA: "button"}


def slot_row(label, brand):
    sid = label.split("--")[0]
    if sid.startswith(brand + "-"):
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
        m = re.search(r"^\**Subject:?\**\s*[:—-]?\s*(.+)$", t, re.M)
        subj = m.group(1).strip() if m else ""
        m = re.search(r"^\**Preview:?\**\s*[:—-]?\s*(.+)$", t, re.M)
        prev = m.group(1).strip() if m else ""
    subj, prev = subj.strip("`* "), prev.strip("`* ")
    # stage 5 sometimes writes a note where the preview goes ("none — the source
    # carried no preview…"). A note is not a preview.
    low = prev.lower()
    if (low.startswith("(none") or low.startswith("none") or len(prev) > 160
            or "the source" in low or "version 0" in low or "improvements belong" in low):
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


SCENE_HEAD = re.compile(r"^(a|an|the|two|three|four|close on|closeup|close-up|overhead|side|wide|macro|split|before)\b", re.I)
SCENE_NOUN = re.compile(r"\b(light|daylight|photograph|photo|screenshot|shot|frame|picture|packshot|tube|bottle|hands?|forearms?|skin|kitchen|table|surface|shower|scene|in use|mid-application|on its cap|side by side)\b", re.I)


def is_scene(b):
    """A picture direction the chain wrote inside an image block — art direction
    for the designer, never copy for the reader."""
    if b.get("from") != "typographic picture":
        return False
    txt = (b.get("text") or "").strip()
    if not txt or len(txt) > 240 or "\n" in txt or "?" in txt:
        return False
    if re.search(r"\b(you|your|we|our)\b", txt, re.I):
        return False
    return bool(SCENE_HEAD.match(txt) and SCENE_NOUN.search(txt))


STRAY = re.compile(r"^[\s,.;:\]\)\"'\u201d]+|[\[\(\"\u201c]\s*$")


def tidy(txt, opens):
    """The chain lifts [UNFILLED: …] out of a sentence, which sometimes leaves a
    stump ("We just got word that ."). A stump is not copy: it becomes an open
    fact instead, named by what is left of the sentence."""
    s = re.sub(r"\s+", " ", txt or "").strip()
    # the chain writes conditional copy inside quoted brackets; when the fact is
    # lifted the bracket's tail is left behind. Cut back to the last one.
    if '"]' in s:
        head, _, s = s.rpartition('"]')
        opens.append("a conditional clause was cut here - the chain wrote: " + head.strip(' [\"')[:110])
        s = s.strip()
    s = re.sub(r"\[UNFILLED[^\]]*\]", "", s).strip()
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)
    s = STRAY.sub("", s).strip()
    s = re.sub(r"^[a-z,]+\s*[.\"\]]+\s*", "", s) if s[:1] in ",]\"" else s
    dangling = re.search(r"\b(that|the|a|an|is|was|were|with|for|of|and|to|in|on|at|from|by)\s*[.,!?]*$", s, re.I)
    if len(s) < 6 or (dangling and len(s) < 120):
        if s and dangling:
            opens.append(f"this line is unfinished - the chain lifted a fact out of it: \u201c{s}\u201d")
        return ""
    return s


def dedupe(blocks):
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


def source_reference(bank, brand, slot):
    """The reference is the email this one was actually built from: the chain
    swiped a source (slots.json "source"), and for a brand whose library came
    out of its own Figma file that source names a frame. Shape-matching is the
    fallback, not the rule."""
    src = (slot or {}).get("source") or ""
    if not src or src.startswith("[UNFILLED"):
        return None
    idx = WORKSPACE / "brands" / brand / "email-sms" / "sends" / "index.json"
    if not idx.is_file():
        return None
    rows = {r.get("file"): r for r in json.loads(idx.read_text())}
    frame = (rows.get(src) or {}).get("frame")
    if not frame:
        return None
    want = re.sub(r"[^a-z0-9]+", "", frame.lower())
    for t in bank["templates"]:
        if re.sub(r"[^a-z0-9]+", "", t.get("name", "").lower()) == want:
            return t
    for t in bank["templates"]:
        if want and want in re.sub(r"[^a-z0-9]+", "", t.get("name", "").lower()):
            return t
    return None


def pick_reference(bank, counts, override=None):
    """The brand's own email whose framework carries this copy with least strain."""
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
            d += w * (abs(gap) if gap >= 0 else 2 * abs(gap))
        return (d, t.get("h", 0))
    return min(tpls, key=dist)


JS = r"""
// figma_brief.py — %(slot)s — generated %(stamp)s. Run through the Figma connector (use_figma).
const P = %(payload)s;
const clean = s => String(s == null ? '' : s).replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"').replace(/[\u2013\u2014]/g, '-').replace(/\u2192/g, '->').replace(/\u2026/g, '...').replace(/\u00a0/g, ' ').replace(/\u2122/g, '(TM)').replace(/\u00ae/g, '(R)').replace(/[^\x20-\x7e\n]/g, '');
let page = P.hostPage ? null : figma.root.children.find(p => p.name === P.page), container = null;
if (!page && !P.hostPage) { try { page = figma.createPage(); page.name = P.page; } catch (e) { page = null; } }
if (page) { if (page.loadAsync) await page.loadAsync(); container = page; }
else {
  const host = await figma.getNodeByIdAsync(P.hostPage);
  if (host.loadAsync) await host.loadAsync();
  let sec = host.children.find(n => n.type === 'SECTION' && n.name === P.page);
  if (!sec) { sec = figma.createSection(); sec.name = P.page; host.appendChild(sec); let bottom = 0; for (const c of host.children) if (c !== sec) bottom = Math.max(bottom, c.y + c.height); sec.x = 0; sec.y = bottom + 600; }
  container = sec;
}
// anything this slot left behind on an earlier run, including the designed drafts that are now retired
for (const n of [...container.children]) if (n.name === P.slotTag || n.name.startsWith(P.slotTag + ' ') || n.name.startsWith(P.slotTag + '|') || n.name.indexOf(P.slotTag + ' |') === 0) n.remove();
const ref = await figma.getNodeByIdAsync(P.reference);
if (!ref) throw new Error('reference not found: ' + P.reference);
// 1 THE TEARDOWN — the reference read as a framework, off the frame itself
const inFurniture = n => { let p = n.parent; while (p && p !== ref) { if (/footer|logo|header|nav|social|unsubscribe/i.test(p.name)) return true; p = p.parent; } return false; };
const isImg = n => { try { const f = n.fills; return Array.isArray(f) && f.some(x => x.type === 'IMAGE'); } catch (e) { return false; } };
const absY = n => n.absoluteTransform[1][2];
const parts = [];
for (const n of ref.findAll(() => true)) {
  if (inFurniture(n)) continue;
  if (n.type === 'TEXT') {
    const fs = n.fontSize === figma.mixed ? 20 : n.fontSize;
    const ch = n.characters.trim(); if (!ch) continue;
    const pn = (n.parent && n.parent.name) || '';
    let kind;
    if (/cta|button/i.test(pn) || (/^[A-Z0-9 !'&\-_>]{6,}$/.test(ch) && fs <= 24 && ch.length < 40)) kind = 'C';
    else if (fs >= 40) kind = 'D'; else if (fs >= 26) kind = 'S'; else if (fs >= 15) kind = 'B'; else continue;
    parts.push({kind, y: absY(n), words: ch.split(/\s+/).length, fs: Math.round(fs), sample: clean(ch).slice(0, 46)});
  } else if (isImg(n)) {
    parts.push({kind: 'I', y: absY(n), w: Math.round(n.width), h: Math.round(n.height)});
  }
}
parts.sort((a, b) => a.y - b.y);
// 2 THE INJECTION — our copy onto that framework, in the framework's own order
const queues = {D: [], S: [], B: [], C: []};
for (const b of P.blocks) if (queues[b.kind]) queues[b.kind].push(b);
const fallback = {D: ['S', 'B'], S: ['D', 'B'], B: ['S', 'D'], C: []};
const NAME = {D: 'display', S: 'subhead', B: 'body', C: 'button', I: 'picture'};
const lines = [];
let used = 0, empty = 0, i = 0;
for (const p of parts) {
  i++;
  if (p.kind === 'I') { lines.push(i + '. PICTURE ' + p.w + 'x' + p.h + '  <-  place a picture'); continue; }
  let b = queues[p.kind].shift();
  if (!b) for (const alt of fallback[p.kind]) { if (queues[alt].length) { b = queues[alt].shift(); break; } }
  const head = i + '. ' + NAME[p.kind].toUpperCase() + ' ' + p.fs + 'px, runs ~' + p.words + (p.words === 1 ? ' word' : ' words') + '  (ref: "' + p.sample + '")';
  if (b) { used++; lines.push(head); lines.push('   <- ' + clean(b.text).replace(/\n/g, ' / ')); }
  else { empty++; lines.push(head); lines.push('   <- nothing from this email - cut the slot or keep the reference line'); }
}
const leftover = [].concat(queues.D, queues.S, queues.B, queues.C);
// 3 the brief card
for (const st of ['Regular', 'Medium', 'Bold']) await figma.loadFontAsync({family: 'Inter', style: st});
const card = figma.createText(); container.appendChild(card);
card.fontName = {family: 'Inter', style: 'Regular'}; card.fontSize = 13;
card.x = P.col * 1180; card.y = 320; card.resize(520, 100); card.textAutoResize = 'HEIGHT';
card.name = P.slotTag + ' | brief';
const L = [];
L.push(P.slotTag + '   ' + P.date + '   ' + P.type + (P.avatar ? '   voice: ' + P.avatar : ''));
L.push('to: ' + P.segments);
L.push('');
L.push('SUBJECT   ' + (P.subject || '[none written]'));
L.push('PREVIEW   ' + (P.preview || '[none written]'));
L.push('');
L.push('REFERENCE   ' + P.referenceName + '   (the frame to the right - do not edit it)');
L.push('This email is built on that one. Below is that email read as a framework,');
L.push('with this month\'s copy dropped into each slot. Design it your way - the');
L.push('framework and the copy are the brief, not a layout.');
L.push('');
L.push('THE FRAMEWORK, AND WHAT GOES IN IT   (' + used + ' slots filled, ' + empty + ' empty)');
L.push('');
for (const ln of lines) L.push(ln);
L.push('');
if (leftover.length) { L.push('COPY THE FRAMEWORK HAS NO SLOT FOR - this email needs room for it:'); for (const b of leftover) L.push(' [' + NAME[b.kind] + '] ' + clean(b.text).replace(/\n/g, ' / ')); L.push(''); }
if (P.openFacts.length) { L.push('OPEN FACTS - a person closes these before this can send:'); for (const o of P.openFacts) L.push(' - ' + clean(o)); L.push(''); }
if (P.pictures.length) { L.push('PICTURES:'); for (const p of P.pictures) L.push(' - ' + clean(p)); L.push(''); }
L.push('Built by the email machine from ' + P.runDir + '. Copy is final; design is yours.');
card.characters = L.join('\n');
let bg = null;
try { bg = figma.createRectangle(); container.appendChild(bg); bg.x = card.x - 20; bg.y = card.y - 20; bg.resize(560, card.height + 40); bg.fills = [{type: 'SOLID', color: {r: 1, g: 0.98, b: 0.92}}]; bg.name = P.slotTag + ' | brief bg'; container.insertChild(container.children.indexOf(card), bg); } catch (e) {}
// the reference, untouched, beside the brief
const copy = ref.clone(); container.appendChild(copy);
copy.x = card.x + 600; copy.y = 320; copy.name = P.slotTag + ' | REF ' + P.referenceName + ' (do not edit)';
if (container.type === 'SECTION') { let w = 0, h = 0; for (const c of container.children) { w = Math.max(w, c.x + c.width); h = Math.max(h, c.y + c.height); } container.resizeWithoutConstraints(w + 200, h + 200); }
return {page: container.id, container: container.type, brief: card.id, reference: copy.id, slots: parts.length, filled: used, empty: empty, leftover: leftover.length};
"""


def build(run_dir, brand, reference=None, page=None, col=None):
    run = json.loads((run_dir / "run.json").read_text())
    label = run.get("label") or run_dir.name
    dj = run_dir / "design.json"
    if not dj.is_file():
        import design_email
        design_email.design(run_dir, brand)
    d = json.loads(dj.read_text())
    blocks, scenes, stumps = [], [], []
    for b in d.get("blocks", []):
        k = KIND_OF.get(b.get("type"))
        t = text_of(b).strip()
        if not (k and t):
            continue
        if is_scene(b):
            scenes.append(t)
        else:
            t2 = tidy(t, stumps)
            if t2:
                blocks.append({"kind": k, "text": t2})
    blocks = dedupe(blocks)
    counts = {k: sum(1 for b in blocks if b["kind"] == k) for k in (DISPLAY, SUB, BODY, CTA)}
    bank = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "design-formats" / "figma-templates.json").read_text())
    row0, _ = slot_row(label, brand)
    ref = None
    if not reference:
        ref = source_reference(bank, brand, row0)
    ref = ref or pick_reference(bank, counts, reference)
    subj, prev = subject_preview(run_dir)
    if not prev:
        prev = next((b.get("text") for b in d.get("blocks", []) if b.get("type") == "preheader"), "") or ""
    row = row0
    sid = label.split("--")[0]
    if sid.startswith(brand + "-"):
        sid = sid[len(brand) + 1:]
    variant = label.split("--")[1] if "--" in label else ""
    month = (row.get("date") or "")[:7] or "month"
    page = page or f"Briefs - {month} (machine)"
    if col is None:
        abbr = sid.split("-")[0]
        pre = brand + "-" if label.startswith(brand + "-") else ""
        runs = sorted(p.name for p in (HERE / "results").glob(f"{pre}{abbr}-*") if (p / "run.json").is_file()
                      and (pre or not p.name.startswith(brand + "-")))
        col = runs.index(run_dir.name) if run_dir.name in runs else 0
    slot_tag = f"{sid.upper()}" + (f" {variant}" if variant else "")
    pictures = [f"to make: {s}" for s in scenes]
    for p in d.get("pictures", []):
        if p.get("kind") == "product photo":
            pictures.append(f"product photo: {p.get('alt')} ({p.get('source')})")
        else:
            pictures.append(f"to make: {(p.get('brief') or p.get('alt') or '')[:160]}")
    payload = {"page": page, "reference": ref["id"], "referenceName": ref.get("name", ref["id"]),
               "slotTag": slot_tag, "col": col, "blocks": blocks, "subject": subj, "preview": prev,
               "date": row.get("date", ""), "segments": ", ".join(row.get("segments") or []),
               "type": row.get("type", ""), "avatar": variant, "openFacts": (d.get("open_facts", []) + stumps)[:8],
               "pictures": pictures, "runDir": f"results/{run_dir.name}",
               "hostPage": bank.get("drafts_host_page")}
    js = JS % {"slot": label, "stamp": datetime.date.today().isoformat(),
               "payload": json.dumps(payload, ensure_ascii=False)}
    (run_dir / "figma-brief.js").write_text(js.strip() + "\n")
    # the team's copy of the same brief, in Markdown
    md = [f"# {slot_tag} — {row.get('date','')} · {row.get('type','')}" + (f" · {variant}" if variant else ""), "",
          f"- to: {', '.join(row.get('segments') or [])}", f"- subject: {subj or '[none written]'}",
          f"- preview: {prev or '[none written]'}", f"- reference email: **{ref.get('name')}** (in the brand's Figma file)",
          "", "## The copy, in order", ""]
    for b in blocks:
        md.append(f"- **{KIND_NAME[b['kind']]}** — {b['text']}")
    if d.get("open_facts") or stumps:
        md += ["", "## Open facts — a person closes these before send", ""] + [f"- {o}" for o in (d.get("open_facts", []) + stumps)]
    if pictures:
        md += ["", "## Pictures", ""] + [f"- {p}" for p in pictures]
    (run_dir / "brief-for-design.md").write_text("\n".join(md) + "\n")
    print(f"{label}: {len(blocks)} copy blocks · reference “{ref.get('name')}” [{ref['id']}] · page “{page}” col {col}")
    return payload


def record(run_dir, brand, result):
    machine = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "machine.json").read_text())
    key = machine.get("figma_file", {}).get("key")
    r = json.loads(result)
    node = (r.get("brief") or "").replace(":", "-")
    r["url"] = f"https://www.figma.com/design/{key}/?node-id={node}" if key and node else None
    r["brand"] = brand
    r["built"] = datetime.datetime.now().isoformat(timespec="minutes")
    (run_dir / "figma-brief.json").write_text(json.dumps(r, indent=1) + "\n")
    print(r["url"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--brand", default=None)
    ap.add_argument("--reference", default=None, help="node id of the reference email to model on")
    ap.add_argument("--page", default=None)
    ap.add_argument("--col", type=int, default=None)
    ap.add_argument("--record", default=None)
    a = ap.parse_args()
    rd = Path(a.run_dir)
    if not rd.is_absolute():
        rd = HERE / rd
    brand = _bf().run_brand(rd, a.brand)
    if a.record:
        record(rd, brand, a.record)
    else:
        build(rd, brand, a.reference, a.page, a.col)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- the source
# The furniture every email carries. A BRAND's own furniture — its name, its
# tagline, its sign-off, its nav words — is read at run time from
# brands/<brand>/email-sms/simple.json (machine/brand_facts.py), never typed here.
FURNITURE_LINE = re.compile(
    r"unsubscribe|no longer (want|find value)|^respectfully,?$|^cheers,?$|"
    r"^founder,|^\{|organization\.|^warmly,?$|^with love",
    re.I)


def source_email(brand, slot):
    """The email the chain actually swiped, read off the file it swiped."""
    src = (slot or {}).get("source") or ""
    if not src or src.startswith("[UNFILLED"):
        return None
    f = WORKSPACE / "brands" / brand / "email-sms" / "sends" / src
    if not f.is_file():
        return None
    raw = f.read_text()
    BF = _bf()
    furn = BF.vocab(brand)
    meta = {}
    for k in ("sent", "preview", "campaign", "from"):
        m = re.search(rf"^- {k}:\s*(.*)$", raw, re.M)
        meta[k] = (m.group(1).strip() if m else "")
    subject = (re.search(r"^#\s*(.+)$", raw, re.M) or [None, src])[1].strip()
    body = raw.split("\n---\n", 1)[-1]
    blocks = []
    for line in body.splitlines():
        s = line.strip().replace("​", "")
        if not s or s.startswith("{{") or s.startswith("{%"):
            continue
        m = re.match(r"\[LINK\]\s*\[IMAGE alt=(.*?)\]\s*(\S+)\s*->\s*(\S+)$", s)
        if m:
            alt = m.group(1).strip()
            if BF.is_furniture_alt(alt, furn) or "unsubscribe" in alt.lower():
                continue
            kind = "button" if re.fullmatch(r"\[?[A-Z0-9 '’,.&!?-]{4,60}\]?", alt) else "image"
            if kind == "image":
                inner = re.search(r"\[([A-Z][A-Z0-9 '’,.&!?-]{3,60})\]?\s*$", alt)
                if inner:
                    head = alt[: inner.start()].strip(" [")
                    if head:
                        blocks.append({"kind": "image", "alt": head, "to": m.group(3)})
                    blocks.append({"kind": "button", "alt": inner.group(1).strip(), "to": m.group(3)})
                    continue
            blocks.append({"kind": kind, "alt": alt.strip("[]"), "to": m.group(3)})
            continue
        m = re.match(r"\[IMAGE alt=(.*?)\]", s)
        if m:
            alt = m.group(1).strip()
            if not BF.is_furniture_alt(alt, furn):
                blocks.append({"kind": "image", "alt": alt.strip("[]"), "to": ""})
            continue
        if s.startswith("[LINK]"):
            continue
        if len(s) > 2 and not FURNITURE_LINE.search(s) and not BF.is_furniture_line(s, furn):
            blocks.append({"kind": "text", "alt": s, "to": ""})
    seen, uniq = set(), []
    for b in blocks:                       # some sends carry the body twice
        key = re.sub(r"\W+", "", b["alt"].lower())[:80]
        if key in seen:
            continue
        seen.add(key); uniq.append(b)
    return {"file": src, "subject": subject, "sent": meta["sent"], "preview": meta["preview"],
            "campaign": meta["campaign"], "blocks": uniq}


def card_text(run_dir, brand):
    """The whole brief, as text — computed here so the connector call is thin."""
    run = json.loads((run_dir / "run.json").read_text())
    label = run.get("label") or run_dir.name
    dj = run_dir / "design.json"
    if not dj.is_file():
        import design_email
        design_email.design(run_dir, brand)
    d = json.loads(dj.read_text())
    blocks, scenes, stumps = [], [], []
    for b in d.get("blocks", []):
        k = KIND_OF.get(b.get("type"))
        tx = text_of(b).strip()
        if not (k and tx):
            continue
        if is_scene(b):
            scenes.append(tx)
        else:
            t2 = tidy(tx, stumps)
            if t2:
                blocks.append({"kind": k, "text": t2})
    blocks = dedupe(blocks)
    row, _ = slot_row(label, brand)
    src = source_email(brand, row)
    sid = label.split("--")[0]
    variant = label.split("--")[1] if "--" in label else ""
    # the tag is the SEND DATE, never the slot's ordinal (the owner, 2026-09-09:
    # "i told you to only make emails for september 14th onwards" - SEP-01 read
    # as the 1st when it is the first send, on the 14th)
    date = row.get("date", "")
    slot_tag = ("SEP " + date[-2:] if date else sid.upper()) + (f" {variant}" if variant else "")
    subj, prev = subject_preview(run_dir)
    if not prev:
        prev = next((b.get("text") for b in d.get("blocks", []) if b.get("type") == "preheader"), "") or ""
    opens = (d.get("open_facts", []) + stumps)[:8]
    pics = [f"to make: {s}" for s in scenes]
    for p in d.get("pictures", []):
        pics.append(f"product photo: {p.get('alt')}" if p.get("kind") == "product photo"
                    else f"to make: {(p.get('brief') or p.get('alt') or '')[:180]}")

    L = [f"{slot_tag}   {row.get('date','')}   {row.get('type','')}" + (f"   voice: {variant}" if variant else ""),
         f"to: {', '.join(row.get('segments') or [])}", ""]
    L += [f"SUBJECT   {subj or '[none written]'}", f"PREVIEW   {prev or '[none written]'}", ""]
    if src:
        L += ["WRITTEN OFF THIS EMAIL OF OURS",
              f"  “{src['subject']}”",
              f"  sent {src['sent']}   campaign: {src['campaign']}",
              f"  its own preview: {src['preview'] or '[none]'}",
              f"  the whole email: brands/{brand}/email-sms/sends/{src['file']}", ""]
        L += ["THAT EMAIL, TORN DOWN, AND WHAT REPLACES EACH PART", ""]
        # pair in reading order, our line against theirs; a button slot takes the
        # next button we wrote, everything else takes the next line we wrote
        pool = list(blocks)
        def take(kinds):
            want_cta = kinds == [CTA]
            for i, b in enumerate(pool):
                if (b["kind"] == CTA) == want_cta:
                    return pool.pop(i)
            return None
        n = 0
        shown = src["blocks"][:18]
        if len(src["blocks"]) > 18:
            L.append(f"(the source runs {len(src['blocks'])} parts; the first 18 are laid out here, the rest repeat the same shapes)")
            L.append("")
        for b in shown:
            n += 1
            if b["kind"] == "button":
                L.append(f"{n}. BUTTON   it said: “{b['alt']}”")
                got = take([CTA])
            elif b["kind"] == "image":
                words = len(b["alt"].split())
                role = "HEADLINE CARD" if words <= 9 else "COPY CARD"
                L.append(f"{n}. {role}   it said: “{b['alt'][:110]}”")
                got = take([DISPLAY, SUB] if words <= 9 else [BODY, SUB, DISPLAY])
            else:
                L.append(f"{n}. TEXT   it said: “{b['alt'][:110]}”")
                got = take([BODY, SUB, DISPLAY])
            L.append(f"    -> {got['text']}" if got else "    -> nothing from this email fills that part - cut it")
        left = pool
        if left:
            L += ["", "THE REST OF THIS MONTH'S COPY - the source has no part for it, so this email needs new room:"]
            L += [f"  [{KIND_NAME[b['kind']]}] {b['text']}" for b in left]
    else:
        L += ["NO SOURCE EMAIL ON FILE for this slot - the copy below stands on its own.", "",
              "THIS MONTH'S COPY, IN ORDER", ""]
        L += [f"  [{KIND_NAME[b['kind']]}] {b['text']}" for b in blocks]
    L.append("")
    if opens:
        L += ["OPEN FACTS - a person closes these before this can send:"] + [f"  - {o}" for o in opens] + [""]
    if pics:
        L += ["PICTURES:"] + [f"  - {p}" for p in pics] + [""]
    L.append(f"Built by the email machine from results/{run_dir.name}. Copy is final; design is yours.")
    return slot_tag, "\n".join(L), row


# --------------------------------------------------------------- the wireframe
WIRE_KIND = {"headline": "H", "subhead": "S", "copy": "B", "quote": "B", "bullets": "B",
             "signoff": "B", "ps": "B", "button": "C", "image": "P", "product": "P"}


def wire_blocks(run_dir, brand):
    """The email as the chain proposed it, in order, reduced to what a layout
    needs: headline / subhead / body / button / picture. Grey boxes stand in for
    the pictures, with the direction written on them. It is a wireframe, not a
    design — the shape and the order, so the designer has something to read."""
    d = json.loads((run_dir / "design.json").read_text())
    out, stumps = [], []
    for b in d.get("blocks", []):
        t = b.get("type")
        k = WIRE_KIND.get(t)
        if not k:
            continue
        if k == "P":
            src = b.get("image") or ""
            note = (b.get("alt") or b.get("image_brief") or "picture").strip()
            out.append({"k": "P", "t": re.sub(r"\s+", " ", note)[:180],
                        "p": bool(b.get("image"))})
            continue
        txt = text_of(b).strip()
        if is_scene(b):
            out.append({"k": "P", "t": re.sub(r"\s+", " ", txt)[:180], "p": False})
            continue
        txt = tidy(txt, stumps)
        if txt:
            out.append({"k": k, "t": txt})
    # the chain repeats itself: the same passage as pieces and again merged
    norm = lambda s: re.sub(r"\W+", " ", s).strip().lower()
    keep, seen = [], []
    for b in out:
        n = norm(b["t"])
        if b["k"] != "P" and (n in seen or any(len(n) > len(o) + 20 and o in n for o in seen)):
            continue
        if b["k"] != "P":
            seen = [o for o in seen if not (len(o) > len(n) + 20 and n in o)]
            seen.append(n)
        b["t"] = b["t"].strip("[]") if b["k"] == "C" else b["t"]
        keep.append(b)
    return keep
