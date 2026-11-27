#!/usr/bin/env python3
"""The layout index — every email in the bank read for its STRUCTURE and
its THEME, then clustered into the unique layouts the brand actually uses.
This is the expansive format bank the owner asked for (2026-09-02): "index ALL
of our designs and identify UNIQUE layouts … Prime Day emails are blue, the
Fourth of July emails are red white and blue, October gets Halloween themes".

    python3 sweep/layouts.py --bank <format-bank dir>

Reads, per email:
  structure  the ordered blocks of the artboard — from the bank's exact JSX
             transcription (vfs-src), each node classified: display type,
             headline, body, kicker, CTA, glass card, image (w×h), section
             ground — sorted top to bottom; the sequence is the layout
  theme      the dominant colours of the RENDERED email (sweep/capture.py's
             picture) — the artwork carries the seasonal palette the code
             does not; plus the campaign name and month
Writes (the first two as a PROPOSAL under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/, K2 (brands write wall) — a
person folds them into brands/<brand>/):
  email-sms/design-formats/layouts.json   the index, by email and by layout
  email-sms/design-formats/layouts.md     the team's readable version
  design/format-bank/index.html                       the browsable bank — every
                                                      email as a picture, grouped
                                                      by layout, theme chips on each
"""
import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "sweep"))
sys.path.insert(0, str(HERE))
import board_pass as BP  # noqa: E402
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
from capture import BOARD_PAGES, OUT as SHOTS, boards_in  # noqa: E402

BOARD_CODE = {"jan-2025": "JAN25", "jan-2025-welcome": "WEL25", "feb-2025": "FEB25",
              "feb-2025-flow": "FEBFL", "mar-2025": "MAR25", "apr-2025": "APR25",
              "may-2025": "MAY25", "jun-2025": "JUN25", "jul-2025": "JUL25",
              "aug-2025": "AUG25", "sep-2025": "SEP25", "oct-2025": "OCT25",
              "nov-2025": "NOV25", "flow-nov-2025": "NOVFL", "dec-2025": "DEC25",
              "jan-2026": "JAN26", "flow-2026": "F26", "flow-results-request": "RRQ"}
MONTH = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
         "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def e(s):
    return html.escape(str(s if s is not None else ""))


# ---------------------------------------------------------- structure ---

IMG_TAGS = {"img", "video"}


def classify(n, ab_w, texts):
    """One JSX node -> a block kind, or None if it is chrome/nothing."""
    st = n["style"]
    w, h = st.get("width") or 0, st.get("height") or 0
    txt = n.get("text")
    fam = str(st.get("fontFamily", ""))
    fs = st.get("fontSize") or 0
    bg = str(st.get("backgroundColor", ""))
    bgi = str(st.get("backgroundImage", "")) + str(st.get("background", ""))
    cls = str(st.get("className", ""))
    if n.get("tag") in ("CTA", "Component1", "LinkCTA1", "LinkCTA2", "LinkCTA3"):
        return ("cta", n["tag"])
    if txt and fs:
        serif = "GT Super" in fam or "Gt Super" in fam
        up = bool(re.fullmatch(r"[^a-z]*", txt)) and len(txt) > 3
        if fs >= 44:
            return ("display-serif" if serif else "display-sans", f"{int(fs)}px" + (" italic" if st.get("fontStyle") == "italic" else ""))
        if fs >= 28:
            return ("headline-serif" if serif else "headline-sans", f"{int(fs)}px")
        if fs >= 19:
            return ("body", f"{int(fs)}px")
        if up and fs <= 18 and w >= 300:
            return ("cta-label", txt[:30])
        return ("kicker" if up else "small", f"{int(fs)}px")
    is_img = (n.get("tag") in IMG_TAGS or "url(" in bgi or "backgroundImage" in st
              or "fig-asset" in cls)
    if not is_img and bg in BP.SOLIDS and w >= 180 and h >= 120:
        # a solid box nothing is written on is a dropped bitmap — the
        # bank paints its IMAGE w×h placeholder over exactly these
        if not any(BP.overlap_frac(n, t) > 0.5 for t in texts if t is not n):
            is_img = True
    if is_img:
        if w >= ab_w - 20 and h >= 500:
            return ("image-full-bleed", f"{int(w)}x{int(h)}")
        if w >= 380:
            return ("image-hero", f"{int(w)}x{int(h)}")
        if w >= 120 and h >= 100:
            return ("image-tile", f"{int(w)}x{int(h)}")
        return ("icon", f"{int(w)}x{int(h)}")
    if "linear-gradient" in bgi and w >= 300 and 120 <= h <= 700:
        return ("glass-card", f"{int(w)}x{int(h)}")
    if bg in ("rgb(199,207,173)", "rgb(187,199,158)", "rgb(0,0,0)", "rgb(242,246,234)") and 50 <= h <= 80 and 280 <= w <= 560:
        return ("cta", f"{int(w)}x{int(h)}")
    if bg and w >= ab_w - 20 and h >= 200:
        return ("ground", bg)
    if "radial-gradient" in bgi:
        return ("glow", "")
    return None


def structure(nodes, ab):
    ab_w = ab["style"].get("width") or 600
    kids = [n for n in nodes if BP.within(n, ab)]
    texts = [n for n in kids if n.get("text") and n["style"].get("fontSize")]
    blocks = []
    for n in kids:
        c = classify(n, ab_w, texts)
        if not c:
            continue
        x, y = BP.abs_pos(n)
        blocks.append((y, x, c[0], c[1], n))
    blocks.sort(key=lambda b: (round(b[0] / 12), b[1]))
    seq, last = [], None
    for y, x, kind, detail, n in blocks:
        if kind == "cta-label" and last and last[0] == "cta" and abs(y - last[2]) < 90:
            continue
        if kind == "glow":
            continue
        if kind in ("body", "small", "kicker") and last and last[0] == kind and y - last[2] < 140:
            continue
        seq.append((kind, detail, round(y)))
        last = (kind, detail, y)
    return seq


def signature(seq):
    """The coarse shape that clusters into a layout: the email read as
    SECTIONS. Type (display or headline + its copy) is one unit; a CTA
    closes a section; images, glass cards and tiles are counted as few /
    many. Kickers, small print and grounds are not layout."""
    units = []
    for kind, _, _ in seq:
        k = {"display-serif": "T", "display-sans": "T", "headline-serif": "T", "headline-sans": "T",
             "body": "t", "cta": "C", "glass-card": "G", "image-hero": "I",
             "image-full-bleed": "F", "image-tile": "i"}.get(kind)
        if not k:
            continue
        if k == "t" and units and units[-1] in ("T", "t"):
            units[-1] = "T"                      # type + its copy = one type unit
            continue
        if k in "Gi" and units and units[-1] == k:
            continue                             # a run of cards / tiles = one unit
        units.append(k)
    s = "".join(units).replace("t", "T")
    s = re.sub(r"T{2,}", "T", s)
    return s


UNIT_NAME = {"T": "type", "C": "CTA", "G": "glass cards", "I": "hero image",
             "F": "full-bleed image", "i": "image tiles"}


def family(sig):
    """The coarse family a signature belongs to: what LEADS the email and
    what it is MADE OF. Variants inside a family differ only in order and
    repetition."""
    if not sig:
        return "structure elsewhere"
    return {"T": "type-led", "I": "hero-image-led", "F": "full-bleed-led",
            "G": "glass-cards-led", "i": "tile-grid-led", "C": "cta-led"}[sig[0]]


def made_of(sig):
    return [UNIT_NAME[u] for u in "GIFi" if u in sig] or ["type only"]


# -------------------------------------------------------------- theme ---

def dominant(png):
    try:
        from PIL import Image
    except ImportError:
        return []
    try:
        im = Image.open(png).convert("RGB")
    except Exception:
        return []
    im = im.resize((60, max(1, int(60 * im.size[1] / im.size[0]))))
    px = list(im.getdata())
    q = Counter((r // 32 * 32, g // 32 * 32, b // 32 * 32) for r, g, b in px)
    total = sum(q.values())
    return [(rgb, n / total) for rgb, n in q.most_common(10)]


def words(name):
    """'Nov27ThanksgivingBLACKFRIDAY' -> 'nov 27 thanksgiving blackfriday' — the
    bank's names are glued Figma layer names."""
    n = re.sub(r"([a-z])([A-Z])", r"\1 \2", name or "")
    n = re.sub(r"([A-Za-z])(\d)", r"\1 \2", n)
    n = re.sub(r"(\d)([A-Za-z])", r"\1 \2", n)
    n = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", n)
    return " " + re.sub(r"[^a-z0-9]+", " ", n.lower()).strip() + " "


KEYWORDS = [
    ("prime", "prime-day"), ("black friday", "bfcm"), ("blackfriday", "bfcm"), ("bfcm", "bfcm"),
    ("cyber", "bfcm"), ("thanksgiving", "thanksgiving"), ("halloween", "halloween"), ("spooky", "halloween"),
    ("tricks", "halloween"), ("trick", "halloween"), ("4 th", "july-4th"), ("4th", "july-4th"),
    ("fourth", "july-4th"), ("july", "july-4th"), ("father", "fathers-day"), ("valentine", "valentines"),
    ("christmas", "christmas"), ("holiday", "holiday"), ("gift", "gift"), ("labor", "labor-day"),
    ("memorial", "memorial-day"), ("new year", "new-year"), ("kings month", "kings-month"),
    ("king s month", "kings-month"), ("welcome", "welcome"), ("cart", "abandoned-cart"),
    ("result", "results"), ("fall", "fall"), ("autumn", "fall"), ("winter", "winter"),
    ("summer", "summer"), ("spring", "spring"), ("back to school", "back-to-school"),
    ("backtoschool", "back-to-school"), ("super bowl", "super-bowl"), ("superbowl", "super-bowl"),
    ("launch", "launch"), ("early access", "early-access"), ("last chance", "last-chance"),
    ("last call", "last-chance"), ("flash", "flash-sale"), ("sale", "sale"), ("off", "offer"),
]


def theme_tags(colors, name, board):
    tags = []
    if colors:
        def share(pred):
            return sum(f for rgb, f in colors if pred(*rgb))
        ink = share(lambda r, g, b: r < 48 and g < 48 and b < 48)
        cream = share(lambda r, g, b: r > 200 and g > 200 and b > 180)
        bright_blue = share(lambda r, g, b: b >= 128 and b > r + 60 and b > g + 10)
        navy = share(lambda r, g, b: 40 <= b < 128 and b > r + 20 and b > g + 8)
        red = share(lambda r, g, b: r > 90 and g < 60 and b < 60 and r > g + 60)
        orange = share(lambda r, g, b: r > 180 and 80 <= g <= 160 and b < 70)
        amber = share(lambda r, g, b: 60 <= r <= 170 and g < r and b < g and b < 48 and r - b >= 48)
        gold = share(lambda r, g, b: r > 150 and g > 110 and b < 90 and r - b > 90)
        green = share(lambda r, g, b: g > r + 20 and g > b + 20 and g < 140)
        if ink >= 0.45: tags.append("dark")
        elif cream >= 0.45: tags.append("light")
        if green >= 0.25: tags.append("deep-green")
        if bright_blue >= 0.10: tags.append("blue")
        if red >= 0.05 and (navy + bright_blue) >= 0.06: tags.append("red-white-blue")
        elif red >= 0.08: tags.append("red")
        if orange >= 0.08: tags.append("orange")
        if amber >= 0.12: tags.append("amber")
        if gold >= 0.10: tags.append("gold")
    low = words(name)
    for k, tag in KEYWORDS:
        if f" {k} " in low and tag not in tags:
            tags.append(tag)
    return tags


# --------------------------------------------------------------- build ---

def build(bank, brand):
    cf = WORKSPACE / "brands" / brand / "email-sms/design-formats/census.json"
    census = json.loads(cf.read_text())["emails"] if cf.is_file() else []      # a brand without a census yet
    emails = []
    for board in boards_in(bank):
        page = BOARD_PAGES.get(board, board)
        src_f = bank / "vfs-src" / f"{board}.jsx"
        bund = bank / "boards" / board / "Components.bundle.js"
        nodes, src = BP.load_nodes(bund if bund.is_file() else src_f)

        def email_sized(n):
            return 550 <= (n["style"].get("width") or 0) <= 820 and (n["style"].get("height") or 0) >= 500

        def has_anc(n):
            p = n["parent"]
            while p:
                if email_sized(p):
                    return True
                p = p["parent"]
            return False
        abs_ = sorted([n for n in nodes if email_sized(n) and not has_anc(n)],
                      key=lambda n: (round(BP.abs_pos(n)[1] / 400), BP.abs_pos(n)[0]))
        rects_f = SHOTS / board / "rects.json"
        rects = json.loads(rects_f.read_text()) if rects_f.is_file() else []
        reg = [dict(x) for x in census if x["board"] == board]
        for i, ab in enumerate(abs_, 1):
            w, h = int(ab["style"]["width"]), int(ab["style"]["height"])
            hit = next((x for x in reg if abs(x["w"] - w) <= 3 and abs(x["h"] - h) <= 6), None)
            if hit:
                reg.remove(hit)
            # the picture: rects are in the board's own render order; match on size
            shot = None
            for j, rc in enumerate(rects, 1):
                if abs(rc["w"] - w) <= 3 and abs(rc["h"] - h) <= 6 and not rc.get("_used"):
                    rc["_used"] = True
                    shot = SHOTS / board / f"{j:02d}.png"
                    break
            seq = structure(nodes, ab)
            colors = dominant(shot) if shot and shot.is_file() else []
            name = (hit or {}).get("name") or ab["style"].get("data-name") or f"{board} #{i}"
            mk = re.match(r"([a-z]{3})-(\d{4})", board)
            month_key = f"{mk.group(2)}-{MONTH[mk.group(1)]:02d}" if mk else ""
            emails.append(dict(
                code=f"{BOARD_CODE[board]}-{i:02d}", board=board, month=month_key, name=name,
                w=w, h=h, ground=ab["style"].get("backgroundColor", ""),
                blocks=[{"kind": k, "detail": d, "y": y} for k, d, y in seq],
                signature=signature(seq),
                shot=str(shot.relative_to(HERE)) if shot and shot.is_file() else None,
                colors=[{"rgb": list(c), "share": round(f, 3)} for c, f in colors[:6]],
                themes=theme_tags(colors, name, board)))

    # cluster: one layout per signature
    groups = defaultdict(list)
    for em in emails:
        groups[em["signature"]].append(em)
    layouts = []
    for sig, ems in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        ex = max(ems, key=lambda x: len(x["blocks"]))
        layouts.append(dict(
            id=f"L{len(layouts) + 1:02d}", signature=sig, count=len(ems),
            recipe=[f"{b['kind']} {b['detail']}".strip() for b in ex["blocks"]],
            example=ex["code"], emails=[x["code"] for x in ems],
            months=sorted({x["month"] for x in ems if x["month"]}),
            themes=sorted(Counter(t for x in ems for t in x["themes"]).items(), key=lambda kv: -kv[1]),
            heights=[min(x["h"] for x in ems), max(x["h"] for x in ems)]))
    for em in emails:
        em["layout"] = next(L["id"] for L in layouts if L["signature"] == em["signature"])
        em["family"] = family(em["signature"])
    fams = defaultdict(list)
    for L in layouts:
        L["family"] = family(L["signature"])
        fams[L["family"]].append(L)
    families = [dict(id=f"F{i + 1:02d}", name=name, count=sum(L["count"] for L in Ls),
                     variants=[L["id"] for L in Ls],
                     mixes=sorted(Counter(" + ".join(made_of(L["signature"])) for L in Ls for _ in range(L["count"])).items(),
                                  key=lambda kv: -kv[1]),
                     themes=sorted(Counter(t for L in Ls for t, n in L["themes"] for _ in range(n)).items(),
                                   key=lambda kv: -kv[1]))
                for i, (name, Ls) in enumerate(sorted(fams.items(), key=lambda kv: -sum(L["count"] for L in kv[1])))]
    return emails, layouts, families


LEGEND = {"T": "a type section (display or headline with its copy)", "C": "CTA", "G": "a run of glass cards",
          "I": "hero image", "F": "full-bleed image", "i": "a run of image tiles"}


def write_outputs(emails, layouts, families, brand, label=None):
    run = facts_proposal.run_dir(brand, label)
    facts_proposal.write(run, brand, "email-sms/design-formats/layouts.json", json.dumps(
        {"generated": "2026-09-02", "note": "The layout index — every email in the bank read for structure "
         "(from the exact JSX) and theme (from the rendered picture), clustered into the unique layouts "
         "the brand actually uses. Built by lab/email-production/sweep/layouts.py. Signature letters: "
         + ", ".join(f"{k}={v}" for k, v in LEGEND.items()),
         "families": families, "emails": emails, "layouts": layouts}, indent=1) + "\n")
    md = [f"# The layout index — {len(emails)} emails, {len(layouts)} unique layouts", "",
          "Every email in the format bank, read for its structure (the exact JSX transcription) and its "
          "theme (the rendered picture's dominant colours plus the campaign name). Emails with the same "
          "block sequence are one layout. Signature letters: " + " · ".join(f"`{k}` {v}" for k, v in LEGEND.items()), "",
          "## Themes across the bank", ""]
    tc = Counter(t for x in emails for t in x["themes"])
    md += [f"- **{t}** — {n}" for t, n in tc.most_common()]
    md += ["", f"## The families — {len(families)}", "",
           "What leads the email and what it is made of. Every variant below belongs to one.", ""]
    md += [f"- **{F['id']} {F['name']}** — {F['count']} email(s) across {len(F['variants'])} variant(s); made of: "
           + "; ".join(f"{m} ({n})" for m, n in F["mixes"][:6]) for F in families]
    md += ["", "## The layouts (variants), most used first", ""]
    for L in layouts:
        md += [f"### {L['id']} · `{L['signature']}` · {L['count']} email(s) · {L['family']}", "",
               f"Example: {L['example']} · months: {', '.join(L['months']) or '—'} · heights {L['heights'][0]}–{L['heights'][1]}px",
               f"Themes: {', '.join(f'{t} ({n})' for t, n in L['themes']) or '—'}", "",
               "Recipe, top to bottom:", ""] + [f"- {r}" for r in L["recipe"]] + ["",
               "Emails: " + ", ".join(L["emails"]), ""]
    facts_proposal.write(run, brand, "email-sms/design-formats/layouts.md", "\n".join(md) + "\n")

    # the browsable bank
    cards = []
    by_fam = defaultdict(list)
    for L in layouts:
        by_fam[L["family"]].append(L)
    fam_html = []
    for F in families:
        mixes = " · ".join(f"{e(m)} ({n})" for m, n in F["mixes"][:6])
        fam_html.append(f'<section class="family" id="{F["id"]}"><h2 class="fh">{F["id"]} · {e(F["name"])} '
                        f'<span class="n">{F["count"]} emails · {len(F["variants"])} variants</span></h2>'
                        f'<p class="mix">Made of: {mixes}</p>')
        for L in by_fam[F["name"]]:
            fam_html.append(f"@@{L['id']}@@")
        fam_html.append("</section>")
    for L in layouts:
        thumbs = []
        for code in L["emails"]:
            em = next(x for x in emails if x["code"] == code)
            chips = "".join(f'<span class="chip">{e(t)}</span>' for t in em["themes"])
            img = (f'<img src="/{e(em["shot"])}" loading="lazy" alt="{e(em["name"])}">' if em["shot"]
                   else '<div class="noshot">no picture</div>')
            thumbs.append(f'<figure><a href="/{e(em["shot"] or "#")}" target="_blank">{img}</a>'
                          f'<figcaption><b>{e(em["code"])}</b> {e(em["name"])}<br>'
                          f'<span class="m">{e(em["month"])} · {em["w"]}×{em["h"]}</span><br>{chips}</figcaption></figure>')
        recipe = "".join(f"<li>{e(r)}</li>" for r in L["recipe"])
        themes = " · ".join(f"{e(t)} ({n})" for t, n in L["themes"]) or "—"
        cards.append(f'''<section class="layout" id="{L["id"]}">
<div class="lh"><h2>{L["id"]} <code>{e(L["signature"])}</code></h2><span class="n">{L["count"]} email{"s" if L["count"] != 1 else ""} · {", ".join(L["months"])}</span></div>
<details><summary>Recipe, top to bottom · themes: {themes}</summary><ol>{recipe}</ol></details>
<div class="grid">{"".join(thumbs)}</div></section>''')
    tc_html = "".join(f'<span class="chip big">{e(t)} <i>{n}</i></span>' for t, n in tc.most_common(18))
    by_id = {L["id"]: c for L, c in zip(layouts, cards)}
    body = "".join(by_id.get(x[2:-2], x) if x.startswith("@@") else x for x in fam_html)
    toc = "".join(f'<a href="#{F["id"]}">{F["id"]} {e(F["name"])} <i>{F["count"]}</i></a>' for F in families)
    doc = f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(brand.upper())} — the layout index</title>
<link rel="stylesheet" href="/design/fonts.css">
<style>
:root{{--bg:#141614;--card:#1c1f1c;--ink:#f2f6ea;--mut:#a9ae9f;--line:#2b2f2a;--acc:#c7cfad}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Untitled Sans","Instrument Sans",system-ui,sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 80px}}
h1{{font:400 44px/1.05 "GT Super Display",Georgia,serif;margin:0 0 8px}} .lede{{color:var(--mut);max-width:900px}}
.chips{{margin:14px 0 30px}} .chip{{display:inline-block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border:1px solid var(--line);border-radius:99px;color:var(--mut);margin:2px 4px 2px 0}}
.chip.big{{font-size:12px;padding:5px 12px}} .chip i{{font-style:normal;color:var(--acc)}}
.family{{border-top:2px solid var(--acc);margin-top:34px;padding-top:18px}} .fh{{font:400 30px "GT Super Display",Georgia,serif;margin:0 0 6px}} .fh .n{{font:14px "Untitled Sans",sans-serif;color:var(--mut);margin-left:10px}}
.mix{{color:var(--mut);margin:0 0 8px}}
.toc{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}} .toc a{{font-size:13px;color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:8px;padding:6px 10px}} .toc a i{{font-style:normal;color:var(--acc);margin-left:4px}}
.layout{{border-top:1px solid var(--line);padding:22px 0 10px}} .lh{{display:flex;align-items:baseline;gap:16px}}
.lh h2{{font:400 26px "GT Super Display",Georgia,serif;margin:0}} .lh code{{font-size:14px;color:var(--acc);background:#22261f;padding:2px 8px;border-radius:6px}} .lh .n{{color:var(--mut)}}
details{{margin:8px 0 14px;color:var(--mut)}} summary{{cursor:pointer;color:var(--acc)}} ol{{columns:2;max-width:900px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:18px}}
figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
figure img{{display:block;width:100%;height:320px;object-fit:cover;object-position:top}} .noshot{{height:320px;display:grid;place-items:center;color:var(--mut)}}
figcaption{{padding:10px 12px;font-size:13px;line-height:1.4}} figcaption .m{{color:var(--mut)}}
</style>
<div class="wrap">
<h1>The layout index</h1>
<p class="lede">{len(emails)} emails from the bank, read for structure and theme — <b>{len(families)} families</b> (what leads the email, what it is made of), <b>{len(layouts)} exact variants</b> inside them. Each card opens the full-size email. Themes are read off the rendered artwork — that is where Prime blue, July 4th and Halloween live — plus the campaign name.</p>
<div class="chips">{tc_html}</div>
<nav class="toc">{toc}</nav>
{body}
</div>'''
    (HERE / "design" / "format-bank" / "index.html").write_text(doc)
    print(f"{len(emails)} emails · {len(layouts)} unique layouts -> layouts.json, layouts.md, design/format-bank/index.html")
    print(f"proposal -> {facts_proposal.note(run, brand)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    a = ap.parse_args()
    emails, layouts, families = build(Path(a.bank), a.brand)
    write_outputs(emails, layouts, families, a.brand, a.label)


if __name__ == "__main__":
    main()
