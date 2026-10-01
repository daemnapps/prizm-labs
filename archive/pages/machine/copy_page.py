#!/usr/bin/env python3
"""Render a run's brief (stage 6) as a page a person reads: the copy in page
order, filled lines as copy, every [UNFILLED: …] hole as a marked block with
its reason, then the offer it hands to and what must be ruled before build.
Writes pages/copy-<label>.html and runs/<label>/deliverable/<page>.md.

    python3 copy_page.py <label> [--title "Face Scrub Offer Page"]
"""
import argparse, html, json, os, re, sys, datetime, io, base64
from pathlib import Path
try:
    from PIL import Image
except ImportError:            # thumbnails are a nicety; the page still renders without them
    Image = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_paths as P         # noqa: E402

RASTER_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

HERE = P.HERE
RUNS = P.RUNS                  # runs/page-machine/<brand>/<label>/; the old runs/ is read too (P.find_run)
# What the side-by-side calls its two columns, and the page's opening line — said
# by the person rendering the page (--before-label / --after-label / --lede),
# never written into this script: it serves any product of any brand.
LABELS = {"before": "The source page — original", "after": "Our page — new", "lede": ""}

def esc(s): return html.escape(s or "", quote=False)

def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t

def section(text, start_pat, end_pats):
    lines = text.splitlines(); out = []; on = False
    for l in lines:
        if re.match(start_pat, l): on = True; continue
        if on and any(re.match(p, l) for p in end_pats): break
        if on: out.append(l)
    return "\n".join(out).strip()

def render_copy(copy):
    """-> html, filled count, hole count"""
    blocks, filled, holes = [], 0, 0
    secs = re.split(r"^## \[(\d+)\]\s*(.*)$", copy, flags=re.M)
    # secs = [pre, n, title, body, n, title, body, ...]
    for i in range(1, len(secs), 3):
        n, title, body = secs[i], secs[i+1].strip(), secs[i+2].strip()
        parts = []
        has_copy = False
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if not para: continue
            if para.startswith("[UNFILLED"):
                for m in re.finditer(r"\[UNFILLED:?\s*([^\]]*)\]", para):
                    holes += 1
                    reason = m.group(1).strip()
                    slot, _, why = reason.partition(" — ")
                    parts.append(f'<div class="hole"><span class="slot">Empty: {esc(slot) or "slot"}</span>{("<span class=why>"+inline(why)+"</span>") if why else ""}</div>')
                continue
            if para.startswith("*[CONTESTED"):
                parts.append(f'<div class="flag">{inline(para.strip("*"))}</div>'); continue
            has_copy = True
            if para.startswith("### "):
                parts.append(f"<h3>{inline(para[4:])}</h3>"); continue
            lines = [ln for ln in para.splitlines()]
            if all(ln.startswith("**") and "**" in ln[2:] for ln in lines) and len(lines) > 1 and all(re.match(r"^\*\*\d+%\*\*", ln) for ln in lines):
                parts.append('<div class="stats">' + "".join(f'<div class="stat"><b>{esc(re.match(r"^\*\*(\d+%)\*\*", ln).group(1))}</b><span>{inline(re.sub(r"^\*\*\d+%\*\*\s*", "", ln))}</span></div>' for ln in lines) + "</div>"); continue
            inner = "<br>".join(inline(ln) for ln in lines)
            # inline holes inside a paragraph
            inner = re.sub(r"\[UNFILLED:?\s*([^\]]*)\]", lambda m: (globals().__setitem__("_h", 1), f'<span class="hole-inline">Empty: {esc(m.group(1).split(" — ")[0])}</span>')[1], inner)
            if "hole-inline" in inner: holes += inner.count("hole-inline")
            parts.append(f"<p>{inner}</p>")
        if has_copy: filled += 1
        blocks.append(f'<section class="sec {"empty" if not has_copy else ""}"><div class="secno">{n}</div><div class="secbody"><div class="sectitle">{inline(title)}</div>{"".join(parts)}</div></section>')
    return "".join(blocks), filled, holes, len(range(1, len(secs), 3))

def render_sbs(run):
    p = run / "sidebyside.json"
    if not p.exists(): return ""
    rows = json.loads(p.read_text())
    out = []
    for r in rows:
        kind = r.get("kind", "changed")
        chip = {"changed": "changed", "kept": "kept as is", "empty": "now empty"}.get(kind, kind)
        before = "".join(f"<p>{esc(x)}</p>" for x in r.get("before", [])) or "<p class=none>—</p>"
        after = "".join(f"<p>{esc(x)}</p>" for x in r.get("after", [])) or "<p class=none>— nothing on this page —</p>"
        why = f'<div class="sbs-why">{esc(r["why"])}</div>' if r.get("why") else ""
        out.append(f'''<div class="sbs-row {kind}">
  <div class="sbs-head"><span class="secno">{r["n"]}</span><span class="sectitle">{esc(r["title"])}</span><span class="chip {kind}">{chip}</span></div>
  <div class="sbs-cols"><div class="sbs-col before"><div class="lbl">{esc(LABELS["before"])}</div>{before}</div><div class="sbs-col after"><div class="lbl">{esc(LABELS["after"])}</div>{after}{why}</div></div>
</div>''')
    return "".join(out)

def render_machine(label):
    """A second run's checked page (stage 4, THE PAGE) as a plain reading column."""
    d = P.find_run(label)
    p = (d or RUNS / label) / "stage4--close.md"
    if not p.exists(): return ""
    t = p.read_text()
    body = section(t, r"^#+\s*THE PAGE\s*$", [r"^#+\s*THE CHECK"])
    out = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para or para == "---": continue
        if re.match(r"^\[\d+[a-z]?\s*·", para) or re.match(r"^\*\*\[\d+", para):
            out.append(f'<div class="sectitle">{inline(para.strip("*"))}</div>'); continue
        m = re.match(r"^(#{1,4})\s+(.*)", para)
        if m: out.append(f"<h3>{inline(m.group(2))}</h3>"); continue
        out.append("<p>" + "<br>".join(inline(x) for x in para.splitlines()) + "</p>")
    return f'<div class="machine"><p class="note">The machine\'s own clean injection — run <code>{esc(label)}</code>, as checked by stage 4. Lines it flagged for a ruling are in its check, not edited here.</p>{"".join(out)}</div>'

def _drive():
    """The company Shared Assets mount: SHARED_ASSETS if set, else found under
    ~/Library/CloudStorage (the <brand> account first)."""
    if os.environ.get("SHARED_ASSETS"):
        return Path(os.environ["SHARED_ASSETS"]).expanduser()
    cloud = Path.home() / "Library" / "CloudStorage"
    hits = sorted(cloud.glob("GoogleDrive-*/Shared drives/Shared Assets"),
                  key=lambda p: (0 if "<brand>" in str(p) else 1, str(p))) if cloud.is_dir() else []
    return hits[0] if hits else cloud / "GoogleDrive" / "Shared drives" / "Shared Assets"

DRIVE = _drive()

def asset_roots(state):
    """Where a picture named only by its file name is looked for: the RUN's own
    brand — its product folder first (the run's product_dir, or any product
    folder named like the run's product card), then the whole brand tree."""
    brand = state.get("brand")
    if not brand: return []
    roots = []
    if state.get("product_dir"): roots.append(DRIVE / state["product_dir"])
    stem = Path(state.get("product") or "").stem
    products = DRIVE / "brands" / brand / "products"
    if stem and products.is_dir():
        roots += sorted(p for p in products.iterdir() if p.is_dir() and stem in p.name)
    roots.append(DRIVE / "brands" / brand)
    return roots

def thumb(path, size=240):
    """A small JPEG data URI, or None."""
    try:
        import base64, io
        im = Image.open(path).convert("RGB"); im.thumbnail((size, size))
        b = io.BytesIO(); im.save(b, "JPEG", quality=70)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return None

def find_asset(asset, state=None):
    if not asset or "MISSING" in asset.upper(): return None
    asset = asset.split(",")[0].strip()          # a list of files: show the first
    p = DRIVE / asset
    if p.is_file(): return p
    base = Path(asset).name
    for root in asset_roots(state or {}):
        hits = list(root.rglob(base)) if root.is_dir() else []
        if hits: return hits[0]
    return None

def render_pictures(run):
    p = run / "pictures-map.json"
    if not p.exists(): return ""
    rows = json.loads(p.read_text())
    sp = run / "run.json"
    state = json.loads(sp.read_text()) if sp.exists() else {}
    imgdir = next(iter((run / "source").glob("*/img")), None)
    counts, missing, out = {}, 0, []
    for r in rows:
        d = r.get("decision", "").upper(); counts[d] = counts.get(d, 0) + 1
        is_missing = "MISSING" in ((r.get("asset") or "") + (r.get("note") or "")).upper()
        if is_missing: missing += 1
        # source thumb: first file matching the slot's first token
        src = None
        if imgdir:
            first = re.split(r"[ ,+/→]|\.\.", r.get("slot", ""))[0].strip()
            first = re.sub(r"\.(jpg|jpeg|png|svg)$", "", first)
            cands = sorted(imgdir.glob(first + "*")) + sorted(imgdir.glob(first.rstrip("0123456789-") + "*"))
            cands = [c for c in cands if c.suffix.lower() in (".jpg", ".jpeg", ".png")]
            src = thumb(cands[0]) if cands else None
        left = f'<img src="{src}" alt="">' if src else '<div class="ph">no thumb</div>'
        if d == "DRIVE":
            a = find_asset(r.get("asset"), state)
            t = thumb(a) if a else None
            right = f'<img src="{t}" alt="">' if t else ('<div class="ph miss">missing — needs a real photo</div>' if is_missing else '<div class="ph">on the Drive</div>')
        elif d == "REGEN": right = '<div class="ph regen">to generate</div>'
        elif d == "COMPOSITE": right = '<div class="ph">rebuild the slide</div>'
        else: right = f'<img src="{src}" alt="" class="dim">' if src else '<div class="ph">kept</div>'
        brief = f'<details><summary>the brief</summary><p>{inline(r["brief"])}</p></details>' if r.get("brief") else ""
        note = f'<p class="pnote">{inline(r["note"])}</p>' if r.get("note") else ""
        asset = f'<p class="passet"><code>{esc(Path(r["asset"]).name if r.get("asset") and "MISSING" not in r["asset"].upper() else (r.get("asset") or ""))}</code></p>' if r.get("asset") else ""
        out.append(f'''<div class="pic">
  <div class="pthumb">{left}</div><div class="parrow">→</div><div class="pthumb">{right}</div>
  <div class="ptext"><div class="phead"><span class="pslot">{esc(r.get("slot",""))}</span><span class="chip {d.lower()}">{esc(d.lower())}</span></div>
  <div class="psec">{esc(r.get("section",""))} · {esc(r.get("shows",""))}</div><p>{inline(r.get("why",""))}</p>{asset}{brief}{note}</div>
</div>''')
    order = ["KEEP", "DRIVE", "REGEN", "COMPOSITE"]
    tally = " · ".join(f"{counts.get(k,0)} {dict(KEEP='kept', DRIVE='from the Drive', REGEN='to generate', COMPOSITE='slides to rebuild')[k]}" for k in order if counts.get(k))
    tally += f" · <b>{missing} missing — need real photos</b>" if missing else ""
    return f'<p class="note">Every picture on the source page, left, and what fills its slot on the face page, right. {tally}.</p>' + "".join(out)

def render_handoff(run):
    p = run / "deliverable" / "HANDOFF.md"
    if not p.exists(): return ""
    out, para, in_list, in_table = [], [], False, False
    def flush():
        nonlocal para
        if para: out.append(f"<p>{inline(' '.join(para))}</p>"); para = []
    for line in p.read_text().splitlines():
        if line.startswith("|"):
            flush()
            if re.match(r"^\|[-| ]+\|$", line): continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table: out.append("<div class='tw'><table>"); in_table = True; out.append("<tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr>"); continue
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>"); continue
        if in_table: out.append("</table></div>"); in_table = False
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush()
            if in_list: out.append("</ol>" if in_list == "ol" else "</ul>"); in_list = False
            lvl = len(m.group(1)); out.append(f"<h{min(lvl+1,4)}>{inline(m.group(2))}</h{min(lvl+1,4)}>"); continue
        m = re.match(r"^\s*(-|\d+\.)\s+(.*)", line)
        if m:
            flush(); tag = "ol" if m.group(1)[0].isdigit() else "ul"
            if in_list != tag:
                if in_list: out.append("</ol>" if in_list == "ol" else "</ul>")
                out.append(f"<{tag}>"); in_list = tag
            out.append(f"<li>{inline(m.group(2))}</li>"); continue
        if re.match(r"^\s+\S", line) and in_list:
            out[-1] = out[-1][:-5] + " " + inline(line.strip()) + "</li>"; continue
        if not line.strip():
            flush()
            if in_list: out.append("</ol>" if in_list == "ol" else "</ul>"); in_list = False
            continue
        para.append(line.strip())
    flush()
    if in_list: out.append("</ol>" if in_list == "ol" else "</ul>")
    if in_table: out.append("</table></div>")
    return '<div class="handoff">' + "".join(out) + "</div>"

def build(label, title, also=None):
    run = P.need_run(label)
    words = run / "deliverable" / "landing.md"
    brief = (words if words.exists() else run / "stage6--brief.md").read_text()
    state = json.loads((run / "run.json").read_text())
    copy = section(brief, r"^## THE COPY\s*$", [r"^## THE OFFER IT HANDS TO", r"^---\s*$"])
    # the copy section may be followed by --- before THE OFFER; take up to THE OFFER instead
    copy = section(brief, r"^## THE COPY\s*$", [r"^## THE OFFER IT HANDS TO"]).replace("\n---\n", "\n")
    offer = section(brief, r"^## THE OFFER IT HANDS TO", [r"^## WHAT TO WATCH", r"^---\s*$"])
    watch = section(brief, r"^## WHAT TO WATCH", [r"^## BEFORE YOU BUILD IT", r"^---\s*$"])
    before = section(brief, r"^## BEFORE YOU BUILD IT", [r"^## ", r"^---\s*$"])
    body, filled, holes, total = render_copy(copy)
    sbs = render_sbs(run)
    machine = render_machine(also) if also else ""
    pictures = render_pictures(run)
    handoff = render_handoff(run)
    def bullets(t):
        items = [ln[2:].strip() for ln in t.splitlines() if ln.startswith("- ")]
        return "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>" if items else f"<p>{inline(t)}</p>"
    today = datetime.date.today().isoformat()
    lede = LABELS["lede"] or (f"The {state.get('page_name') or label} page for {state.get('brand')}, made from the source page "
                              f"{state.get('source_url') or ''} — same structure, same proof, same story; only the product facts "
                              f"and the places change. Left is the source, right is ours.")
    # deliverable mirror
    d = run / "deliverable"; d.mkdir(exist_ok=True)
    if not words.exists(): (d / "landing.md").write_text(brief)
    page = f'''<title>{esc(title)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--good:#2F6B3A;--good-soft:#DCEFDF;--bg:#F5F3EE;--surface:#FFFFFF;--ink:#20242A;--muted:#66707B;--line:#DDD8CF;--accent:#7A5A1E;--hole:#FFF3D6;--hole-line:#D9A441;--hole-ink:#6B4A0E;--flag:#F3DFDA;--flag-ink:#8A3A2C;--code:#ECE8E0;--radius:8px}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--good:#8FCB9A;--good-soft:#1B3320;--bg:#14161A;--surface:#1D2126;--ink:#E8E6E1;--muted:#9AA3AD;--line:#2E343B;--accent:#D9B36A;--hole:#3A2E12;--hole-line:#B98A2E;--hole-ink:#F0D48A;--flag:#3F221C;--flag-ink:#F0A796;--code:#262B31}}}}
:root[data-theme="dark"]{{--good:#8FCB9A;--good-soft:#1B3320;--bg:#14161A;--surface:#1D2126;--ink:#E8E6E1;--muted:#9AA3AD;--line:#2E343B;--accent:#D9B36A;--hole:#3A2E12;--hole-line:#B98A2E;--hole-ink:#F0D48A;--flag:#3F221C;--flag-ink:#F0A796;--code:#262B31}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,sans-serif;padding:0 16px;padding-block:28px 72px}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{font:600 26px/1.2 "IBM Plex Sans",sans-serif;margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}}
.lede{{color:var(--muted);max-width:70ch;margin:0 0 14px}}
.tally{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 26px}}
.tally span{{font:13px "IBM Plex Mono",monospace;border:1px solid var(--line);border-radius:999px;padding:3px 11px;background:var(--surface)}}
.tally .h{{border-color:var(--hole-line);background:var(--hole);color:var(--hole-ink)}}
.sec{{display:grid;grid-template-columns:44px 1fr;gap:12px;padding:16px 0;border-top:1px solid var(--line)}}
.sec.empty .sectitle{{color:var(--muted)}}
.secno{{font:13px "IBM Plex Mono",monospace;color:var(--muted);padding-top:3px}}
.sectitle{{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin-bottom:8px}}
.secbody{{max-width:68ch}}
.secbody p{{font:400 17px/1.55 "Source Serif 4",Georgia,serif;margin:0 0 12px}}
.secbody h3{{font:600 22px/1.25 "Source Serif 4",Georgia,serif;margin:4px 0 10px;text-wrap:balance}}
.sec:nth-of-type(2) .secbody p{{font-size:30px;line-height:1.15;font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:0 0 12px}}
.stat{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px}}
.stat b{{display:block;font:600 28px/1 "Source Serif 4",serif;margin-bottom:6px}}
.stat span{{font-size:13.5px;color:var(--muted)}}
.hole{{background:var(--hole);border-left:3px solid var(--hole-line);border-radius:0 var(--radius) var(--radius) 0;padding:8px 12px;margin:0 0 10px;font-size:13.5px;color:var(--hole-ink)}}
.hole .slot{{display:block;font:500 12px "IBM Plex Mono",monospace;letter-spacing:.03em;margin-bottom:2px}}
.hole .why{{display:block}}
.hole-inline{{background:var(--hole);color:var(--hole-ink);border-radius:4px;padding:0 6px;font:500 13px "IBM Plex Mono",monospace}}
.flag{{background:var(--flag);color:var(--flag-ink);border-radius:var(--radius);padding:10px 12px;font-size:13.5px;margin:0 0 12px}}
code{{font:13px "IBM Plex Mono",monospace;background:var(--code);padding:1px 5px;border-radius:4px}}
.after{{margin-top:36px;display:grid;gap:18px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px}}
.card h2{{font:600 16px "IBM Plex Sans",sans-serif;margin:0 0 8px}}
.card p,.card li{{font-size:14.5px;margin:0 0 6px}}
.card ul{{margin:0;padding-left:18px}}
.foot{{margin-top:28px;font-size:12.5px;color:var(--muted)}}
.machine{{max-width:68ch}}
.machine .note{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.machine p{{font:400 16px/1.55 "Source Serif 4",Georgia,serif;margin:0 0 10px}}
.machine h3{{font:600 21px/1.25 "Source Serif 4",Georgia,serif;margin:6px 0 8px}}
.machine .sectitle{{margin-top:18px}}
.handoff{{max-width:76ch}}
.handoff h2{{font:600 22px/1.25 "IBM Plex Sans",sans-serif;margin:22px 0 8px}}
.handoff h3{{font:600 17px/1.3 "IBM Plex Sans",sans-serif;margin:18px 0 6px}}
.handoff p,.handoff li{{font-size:15px;line-height:1.55;margin:0 0 8px}}
.handoff ul,.handoff ol{{padding-left:22px;margin:0 0 10px}}
.handoff .tw{{overflow-x:auto;margin:0 0 12px}}
.handoff table{{border-collapse:collapse;width:100%;font-size:14px}}
.handoff th,.handoff td{{text-align:left;vertical-align:top;padding:8px 10px;border-top:1px solid var(--line)}}
.handoff th{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);border-top:0}}
.pic{{display:grid;grid-template-columns:124px 24px 124px 1fr;gap:12px;align-items:start;padding:14px 0;border-top:1px solid var(--line)}}
.pthumb img{{width:120px;height:120px;object-fit:cover;border-radius:6px;border:1px solid var(--line);display:block}}
.pthumb img.dim{{opacity:.5}}
.parrow{{text-align:center;color:var(--muted);padding-top:50px}}
.ph{{width:120px;height:120px;border-radius:6px;border:1px dashed var(--line);display:flex;align-items:center;justify-content:center;text-align:center;font-size:12px;color:var(--muted);padding:8px;background:var(--surface)}}
.ph.regen,.ph.miss{{background:var(--hole);border-color:var(--hole-line);color:var(--hole-ink);border-style:solid}}
.phead{{display:flex;align-items:center;gap:10px;margin-bottom:4px}}
.pslot{{font:500 13px "IBM Plex Mono",monospace}}
.psec{{font-size:12px;color:var(--muted);margin-bottom:6px}}
.ptext p{{font-size:14px;margin:0 0 6px}}
.passet code{{font-size:12px}}
.pnote{{color:var(--hole-ink)}}
.chip.drive{{background:var(--good-soft);color:var(--good);border-color:var(--good)}}
.chip.regen{{background:var(--hole);color:var(--hole-ink);border-color:var(--hole-line)}}
.chip.keep,.chip.composite{{background:var(--code);color:var(--muted)}}
.ptext details{{font-size:13.5px;margin:4px 0}}
.ptext summary{{cursor:pointer;color:var(--accent);font-weight:500}}
@media (max-width:640px){{.pic{{grid-template-columns:1fr 1fr}}.parrow{{display:none}}.ptext{{grid-column:1 / -1}}}}
.tabs{{display:flex;gap:6px;margin:0 0 18px}}
.tabs button{{font:500 13.5px "IBM Plex Sans",sans-serif;padding:7px 14px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;cursor:pointer}}
.tabs button[aria-selected="true"]{{background:var(--ink);color:var(--bg);border-color:var(--ink)}}
.tabs button:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.sbs-row{{border-top:1px solid var(--line);padding:14px 0}}
.sbs-head{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.sbs-head .sectitle{{margin:0}}
.chip{{margin-left:auto;font:500 12px "IBM Plex Mono",monospace;padding:2px 9px;border-radius:999px;border:1px solid var(--line)}}
.chip.changed{{background:var(--surface)}}
.chip.kept{{background:var(--code);color:var(--muted)}}
.sbs-row.kept .sbs-col.after{{opacity:.75}}
.chip.empty{{background:var(--hole);color:var(--hole-ink);border-color:var(--hole-line)}}
.sbs-cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.sbs-col{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;font-size:14px}}
.sbs-col.before{{color:var(--muted)}}
.sbs-col p{{margin:0 0 8px;line-height:1.5}}
.sbs-col .lbl{{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin-bottom:8px}}
.sbs-col .none{{font-style:italic}}
.sbs-row.empty .sbs-col.after{{background:var(--hole);border-color:var(--hole-line);color:var(--hole-ink)}}
.sbs-why{{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line);font-size:13px;color:var(--hole-ink)}}
@media (max-width:640px){{.sbs-cols{{grid-template-columns:1fr}}}}
@media (max-width:560px){{.sec{{grid-template-columns:1fr}}.secno{{padding:0}}.sec:nth-of-type(2) .secbody p{{font-size:24px}}}}
</style>
<div class="wrap">
<h1>{esc(title)}</h1>
<p class="lede">{esc(lede)}</p>
<div class="tally"><span>{filled} of {total} sections carry copy</span><span class="h">{holes} empty slots</span><span>run <code>{esc(label)}</code> · {today}</span></div>
<div class="tabs" role="tablist">{'<button id="tab-handoff" role="tab" aria-selected="true" aria-controls="view-handoff">Handoff</button>' if handoff else ""}<button id="tab-sbs" role="tab" aria-selected="{"false" if handoff else "true"}" aria-controls="view-sbs">Side by side</button><button id="tab-copy" role="tab" aria-selected="false" aria-controls="view-copy">The new page, in order</button>{'<button id="tab-machine" role="tab" aria-selected="false" aria-controls="view-machine">Machine\'s own swap</button>' if machine else ""}{'<button id="tab-pictures" role="tab" aria-selected="false" aria-controls="view-pictures">Pictures</button>' if pictures else ""}</div>
{f'<div id="view-handoff" role="tabpanel">{handoff}</div>' if handoff else ""}
<div id="view-sbs" role="tabpanel"{" hidden" if handoff else ""}>{sbs}</div>
<div id="view-copy" role="tabpanel" hidden>{body}</div>
{f'<div id="view-machine" role="tabpanel" hidden>{machine}</div>' if machine else ""}
{f'<div id="view-pictures" role="tabpanel" hidden>{pictures}</div>' if pictures else ""}
<script>
(function(){{var b=document.querySelectorAll('.tabs button');function pick(id){{b.forEach(function(x){{var on=x.id===id;x.setAttribute('aria-selected',on);document.getElementById(x.getAttribute('aria-controls')).hidden=!on;}});try{{localStorage.setItem('copytab',id)}}catch(e){{}}}}
b.forEach(function(x){{x.addEventListener('click',function(){{pick(x.id)}})}});var saved=null;try{{saved=localStorage.getItem('copytab')}}catch(e){{}}if(saved&&document.getElementById(saved))pick(saved);}})();
</script>
<div class="after">
<div class="card"><h2>The offer it hands to</h2>{"".join(f"<p>{inline(x)}</p>" for x in offer.split(chr(10)+chr(10)) if x.strip())}</div>
<div class="card"><h2>Before it can be built</h2>{bullets(before)}</div>
<div class="card"><h2>What to watch once it runs</h2>{bullets(watch)}</div>
</div>
<p class="foot">Words file: <code>{esc(P.rel(run))}/deliverable/landing.md</code> · every stage's prompt and output in the same folder.</p>
</div>
'''
    out = HERE / "pages" / f"copy-{label}.html"
    out.write_text(page)
    print(out, f"{filled}/{total} sections with copy, {holes} holes")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("label"); ap.add_argument("--title", default="Copy")
    ap.add_argument("--also", help="another run whose checked page is shown as a third tab")
    ap.add_argument("--lede", default="", help="the page's opening line (default: built from the run's own page name, brand and source)")
    ap.add_argument("--before-label", default=LABELS["before"], help="what the side-by-side calls the source column")
    ap.add_argument("--after-label", default=LABELS["after"], help="what the side-by-side calls our column")
    a = ap.parse_args()
    LABELS.update(before=a.before_label, after=a.after_label, lede=a.lede)
    build(a.label, a.title, a.also)
