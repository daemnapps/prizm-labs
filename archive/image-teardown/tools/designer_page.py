#!/usr/bin/env python3
"""The one page the graphic designer opens — the instructions and every brief.

    designer_page.py --out <file.html>              every finished brief
    designer_page.py --brand <brand> --out <f>      one brand's

Damon, 2026-09-14: *"turn this brief page and the working a brief page into
an artifact that I can share with the graphic designer so I can get her
feedback."* Then, when the first build shipped one brief as a sample:
*"you didn't even put those other briefs that literally just generated in
here."*

Right. **Every finished brief goes in, not an example of one.** The page is
the batch — she picks a brief, sees its swipe, our draft, the brief itself
and its prompts, and moves to the next. One sample answers "what does a
brief look like"; the batch answers "can I work this way", which is the
question being asked.

**Built from the live files, never retyped.** The swipes and drafts are the
actual images, each brief is its run's own `06-brief.md`, the prompts are the
same `.txt` files that ship in her Drive folder. A page that restates any of
that by hand is a fourth copy that starts drifting the day it is written.
"""
import argparse, base64, html, json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import briefs as B

ROOT = HERE.parent

BRIEFS_HEAD = """<header>
  <div class="eyebrow"><span>The static ad machine</span><span>For the graphic designer</span></div>
  <h1>The Brief Board</h1>
  <p class="standfirst">Every brief that is ready, with the photo it was swiped
  from, our first attempt at copying it, and the prompts to run.
  <b>How to work one is on the other page</b> &mdash; this is the work itself.</p>
  {{PACKS}}
</header>

"""

# Fifteen briefs means thirty inlined pictures, so each one is cut small.
# The artifact has no file server — every byte is in the page — and the
# pictures are here to be compared with each other, not printed.
PX, Q = 460, 58


def thumb(src, px=None, q=None):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
        out = Path(t.name)
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions",
                    str(q or Q), "-Z", str(px or PX), str(src), "--out", str(out)],
                   capture_output=True)
    b = base64.b64encode(out.read_bytes()).decode()
    out.unlink(missing_ok=True)
    return "data:image/jpeg;base64," + b


# ---- the brief's own Markdown, as HTML ---------------------------------
def md(t):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    out, lines, i = [], t.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            lang, body = ln[3:].strip(), []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i]); i += 1
            out.append(f'<pre class="code">{html.escape(chr(10).join(body))}</pre>')
        elif ln.startswith("## ") or ln.startswith("# "):
            out.append(f"<h4>{inline(ln.lstrip('# '))}</h4>")
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            i -= 1
            out.append(table(rows))
        elif re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            i -= 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
        elif re.match(r"^\s*\d+\.\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            i -= 1
            out.append("<ol class='plain'>"
                       + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
        elif ln.strip():
            m = re.fullmatch(r"\*\*(.+?)\.?\*\*", ln.strip())
            out.append(f"<p class='label'>{inline(m.group(1))}</p>" if m
                       else f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def table(rows):
    cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]] if len(rows) > 2 else []
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                for r in body)
    return f'<div class="tw"><table><tr>{h}</tr>{b}</table></div>'


def inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<i>\1</i>", s)
    return s


def doc_one(brief_md):
    """Document One only. Two and Three are ours, not hers."""
    m = re.search(r"## DOCUMENT ONE.*?(?=\n## DOCUMENT TWO|\Z)", brief_md, re.S)
    t = m.group(0) if m else brief_md
    return md(re.sub(r"^## DOCUMENT ONE[^\n]*\n", "", t))


def headline(brief_md):
    """The brief's own first sentence — the chip's subtitle, in its words."""
    m = re.search(r"\*\*What this is[.:]?\*\*\s*\n+(.+?)(?=\n\n)", brief_md, re.S)
    if not m:
        return ""
    s = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.split(r"(?<=[.]) ", s)[0][:150]


# ---- one brief's panel --------------------------------------------------
def panel(bid, rec, n):
    run = P.RUNS / rec["run"]
    ws = ROOT / "worksheets" / rec["brand"] / bid
    bm = (run / "out/06-brief.md").read_text()

    src = run / "assets/source.jpg"
    # the same draft the pack and the Drive folder carry — a judged set is
    # the last word, so a brief the judge passed nothing for shows why
    import deliver as DV
    draft = DV.newest_draft(rec["brand"], bid)
    imgs = ""
    if src.is_file():
        a = (f'<figure><img loading="lazy" src="{thumb(src)}" alt="The swiped '
             f'original for {bid}."><figcaption><span>source.jpg</span>'
             f'<b>The swipe</b></figcaption></figure>')
        flag = None
        if draft and (draft.parent / "flags.json").is_file():
            flag = json.loads((draft.parent / "flags.json").read_text()).get(bid)
        if draft:
            note = ""
            if flag:
                fl = "; ".join(f"{k}: {v}" for k, v in flag["failed"].items())
                note = (f'<p class="flagnote"><b>Best of {flag["rolls_tried"]} rolls — '
                        f'did not pass:</b> {html.escape(fl)}</p>')
            b = (f'<figure><img loading="lazy" src="{thumb(draft)}" alt="Our '
                 f'draft for {bid}."><figcaption><span>draft.png</span><b>Ours'
                 f'{" — flagged" if flag else ""}</b></figcaption>{note}</figure>')
        else:
            why = ""
            for v in sorted((ROOT / "drafts" / rec["brand"]).glob("v*/rejects.md"),
                            reverse=True):
                m = re.search(rf"## {bid}\n(.+?)(?=\n## |\Z)", v.read_text(), re.S)
                if m:
                    why = html.escape(re.sub(r"`[^`]*` — ", "", m.group(1)).strip())
                    break
            b = (f'<figure><div class="nodraft"><b>No draft passed the judge</b>'
                 f'<p>{why or "every roll failed a check"}</p></div>'
                 f'<figcaption><span>draft.png</span><b>Ours</b></figcaption></figure>')
        imgs = f'<div class="sheet"><div class="frames">{a}{b}</div></div>'

    prompts = []
    for f in sorted((ws / "prompts").glob("*.txt")):
        nm = re.sub(r"^\d+-", "", f.stem).replace("-", " ")
        prompts.append((f.stem, "Control" if nm == "control" else nm.title(),
                        f.read_text().strip()))
    tabs = "".join(
        f'<button class="tab{" on" if k == 0 else ""}" type="button" '
        f'data-pane="{bid}-{i}">{html.escape(lbl)}</button>'
        for k, (i, lbl, _) in enumerate(prompts))
    panes = "".join(
        f'<div class="pane{" on" if k == 0 else ""}" id="pane-{bid}-{i}">'
        f'<div class="pane-head"><span>{html.escape(i)}.txt</span>'
        f'<button class="copy" type="button" data-for="txt-{bid}-{i}">Copy</button>'
        f'</div><pre id="txt-{bid}-{i}">{html.escape(txt)}</pre></div>'
        for k, (i, lbl, txt) in enumerate(prompts))

    d = rec.get("declares") or {}
    meta = " · ".join(x for x in (rec["brand"], d.get("problem"), d.get("angle"),
                                  d.get("concept")) if x)
    sw = (rec.get("swipe") or {})
    why = sw.get("why") or ""
    blk = sw.get("block") or ""

    return f'''<div class="briefpanel{" on" if n == 0 else ""}" id="brief-{bid}">
  <div class="bp-head">
    <div><span class="bp-id">{bid}</span>
      <span class="bp-meta">{html.escape(meta)}</span></div>
    <a class="bp-drive" href="{html.escape((rec.get('drive') or {}).get('folder',''))}"
       target="_blank" rel="noopener">Open the folder &rarr;</a>
  </div>
  <p class="bp-swipe"><b>Swiped from</b> {html.escape(blk)}
     {(" — " + html.escape(why)) if why else ""}</p>
  {imgs}
  <h3 class="bp-h">The brief</h3>
  <div class="brief">{doc_one(bm)}</div>
  <h3 class="bp-h">Its {len(prompts)} prompts</h3>
  <p class="bp-sub">One control, the rest variations, each moving a single thing.
     Verbatim — nothing shortened for display.</p>
  <div class="prompts"><div class="tabbar">{tabs}</div>{panes}</div>
</div>'''


GITHUB = "https://github.com/<brand>-team/ai-workspace/tree/main/"
DRIVE_LAB = "Shared Assets/image-teardown/"
DRIVE_RUNS = "Shared Assets/runs/image-teardown/"


def where(reg, only=None):
    """Where each brand's briefs and pack live, on both planes."""
    rows = []
    for key, pk in sorted(reg.get("packs", {}).items()):
        b = pk.get("brand") or key.split("--")[0]
        if only and b != only:
            continue
        ids = [i for i in pk.get("briefs", [])
               if i in reg["briefs"]] or \
              [i for i, r in reg["briefs"].items() if r.get("brand") == b and r.get("run")]
        first = next((reg["briefs"][i] for i in sorted(ids)
                      if (reg["briefs"][i].get("drive") or {}).get("folder")), {})
        run = json.loads((P.RECORDS / b / pk["label"]
                          / "run.json").read_text())
        gh_briefs = f"image-teardown/worksheets/{b}/"
        gh_pack = f"runs/image-teardown/{b}/{pk['label']}/deliverable/"
        dr_briefs = DRIVE_LAB + b + "/"
        dr_pack = DRIVE_RUNS + b + "/" + pk["label"] + "/"
        parent = (first.get("drive") or {}).get("folder", "")
        # the brand folder on Drive is the brief folder's parent; the
        # register keeps only the brief's own link, so link that
        rows.append(f"""<div class="where-brand">
  <h3>{html.escape(b)} · {html.escape(pk.get("product") or "")} <em>{len(ids)} briefs</em></h3>
  <table>
    <tr><th></th><th>GitHub</th><th>Google Drive</th></tr>
    <tr><td>The briefs &mdash; one folder each: work order, prompts</td>
        <td><a href="{GITHUB}{gh_briefs}" target="_blank" rel="noopener"><code>{gh_briefs}</code></a></td>
        <td><a href="{html.escape(run['drive'].get('briefs_folder', parent))}" target="_blank" rel="noopener"><code>{dr_briefs}&lt;brief&gt;/</code></a></td></tr>
    <tr><td>The pack &mdash; the zip and its README</td>
        <td><a href="{GITHUB}{gh_pack}" target="_blank" rel="noopener"><code>{gh_pack}README.md</code></a></td>
        <td><a href="{html.escape(run['drive']['folder'])}" target="_blank" rel="noopener"><code>{dr_pack}{html.escape(run['zip'])}</code></a></td></tr>
  </table>
</div>""")
    if not rows:
        return ""
    return ('<div class="where"><div class="eyebrow"><span>Where these live</span></div>'
            + "".join(rows)
            + '<p class="pack-note">GitHub holds the words (work orders, prompts, '
              'briefs, the README). Drive holds the pictures and the zip. The '
              'brief number is the same in both.</p></div>')


def standard():
    """The draft standard, on the page he reads — the steps and the prompts
    verbatim. Damon, 2026-09-17: "LOCK IN THE PROMPT / WORKFLOW." A prompt he
    cannot see is a prompt he cannot correct."""
    doc = (ROOT / "DRAFT-STANDARD.md").read_text()
    steps = re.search(r"## The six steps\n\n(\|.*?)\n\n", doc, re.S)
    files = [("The draft — adult in the swipe", "stage7-draft-match-swipe-v2-damon.md"),
             ("The draft — organic, no adult", "stage7-draft-leave-alone-v1-damon.md"),
             ("The judge", "stage8-draft-judge-v2-damon.md")]
    tabs = "".join(
        f'<button class="tab{" on" if k == 0 else ""}" type="button" '
        f'data-pane="std-{k}">{html.escape(lbl)}</button>' for k, (lbl, _) in enumerate(files))
    panes = "".join(
        f'<div class="pane{" on" if k == 0 else ""}" id="pane-std-{k}">'
        f'<div class="pane-head"><span>prompts/{f}</span>'
        f'<button class="copy" type="button" data-for="txt-std-{k}">Copy</button></div>'
        f'<pre id="txt-std-{k}">{html.escape((ROOT / "prompts" / f).read_text().strip())}</pre></div>'
        for k, (_, f) in enumerate(files))
    return f'''<details class="standard">
  <summary><span class="eyebrow"><span>How these drafts are made</span></span>
    <b>The draft standard</b> <em>ruled 2026-09-17 · do not deviate</em></summary>
  <p class="bp-sub">One command: <code>chain.py draft --brand &lt;brand&gt;</code>. The swipe is
  the picture; our woman (a different one), our product (from three angles, at the swipe's
  angle), our words, our offer and our colour go in; every roll is judged on eleven tests
  and only a passing roll ships. The full ruling is <code>DRAFT-STANDARD.md</code>.</p>
  <div class="brief">{md(steps.group(1)) if steps else ""}</div>
  <h3 class="bp-h">The prompts, verbatim</h3>
  <div class="prompts briefpanel on"><div class="tabbar">{tabs}</div>{panes}</div>
</details>'''


def build(out_path, brand=None, part="all"):
    reg = B.load()
    ids = [b for b, r in sorted(reg["briefs"].items())
           if r.get("run") and (not brand or r["brand"] == brand)
           and (P.RUNS / r["run"] / "out/06-brief.md").is_file()
           and (ROOT / "worksheets" / r["brand"] / b / "work-order.md").is_file()]

    # The chips group by PRODUCT on a one-brand board and by brand otherwise
    # (Damon, 2026-09-18: "update the board so the products are separated").
    # The first group is selected on load, so a board opens on one product's
    # briefs, never on a mix. Each chip carries a thumbnail of our draft
    # ("I also need thumbnails of our versions in the board").
    import deliver as DV

    def group_of(rec):
        return (rec.get("product") or "—") if brand else rec["brand"]

    def group_label(g):
        return g.replace("-", " ") if brand else g

    chips, panels, counts, order = [], [], {}, []
    for bid in ids:
        g = group_of(reg["briefs"][bid])
        if g not in order:
            order.append(g)
    first_group = order[0] if order else None
    first_on = None
    for bid in ids:
        rec = reg["briefs"][bid]
        bm = (P.RUNS / rec["run"] / "out/06-brief.md").read_text()
        g = group_of(rec)
        counts[g] = counts.get(g, 0) + 1
        on = first_on is None and g == first_group
        if on:
            first_on = bid
        d = DV.newest_draft(rec["brand"], bid)
        pic = (f'<img class="chip-pic" loading="lazy" src="{thumb(d, 220, 52)}" '
               f'alt="">' if d else '<span class="chip-pic none">no draft</span>')
        chips.append(
            f'<button class="chip{" on" if on else ""}" type="button" '
            f'data-brief="{bid}" data-group="{html.escape(g)}"'
            f'{"" if g == first_group else " hidden"}>{pic}'
            f'<span class="chip-id">{bid}</span>'
            f'<span class="chip-sub">{html.escape(headline(bm)[:88])}</span>'
            f'</button>')
        panels.append(panel(bid, rec, 0 if bid == first_on else 1))

    filters = "".join(
        f'<button class="filt{" on" if g == first_group else ""}" type="button" '
        f'data-group="{html.escape(g)}">{html.escape(group_label(g))} <em>{counts[g]}</em></button>'
        for g in order) + (
        f'<button class="filt" type="button" data-group="all">all <em>{len(ids)}</em></button>'
        if len(order) > 1 else "")

    # The masthead pair states the standard in one glance, so it is fed from
    # the first brief in the set rather than a picture chosen for the page.
    first = reg["briefs"][ids[0]]
    frun = P.RUNS / first["run"]
    fdrafts = sorted((ROOT / "drafts" / first["brand"]).glob(f"v*/{ids[0]}-draft.png"))

    tpl = (HERE / "designer-page.html").read_text()

    # Damon, 2026-09-14: *"Give me a sharable artifact for each page we
    # made."* One combined page was the wrong unit — the instructions are
    # read once and the briefs are worked through fifteen times, so they are
    # two links he can send separately. They share this template because they
    # share a design; the part flag decides which half survives.
    if part == "instructions":
        tpl = tpl[:tpl.index('<div class="example">')] + tpl[tpl.index("<footer>"):]
    elif part == "briefs":
        head = tpl[:tpl.index("<header>")]
        rest = tpl[tpl.index('<div class="example">'):]
        tpl = head + BRIEFS_HEAD + rest
        tpl = tpl.replace("<title>Working a Brief</title>",
                          "<title>The Brief Board</title>")

    # The pack: one zip per brand holding every folder on this page, built
    # by tools/pack.py and recorded in briefs.json. Damon, 2026-09-17: "a
    # download pack to give to our graphic designer so she can just plug it
    # into Higgsfield". The board is where she reads; the pack is what she
    # downloads — so the link sits at the top, one per brand that has one.
    packs = ""
    if part == "briefs" and reg.get("packs"):
        packs = '<div class="packs">' + "".join(
            f'<a class="pack" href="{html.escape(pk["url"])}" target="_blank" '
            f'rel="noopener">Download the {html.escape(pk.get("product") or key)} pack '
            f'<small>{html.escape(pk.get("brand") or key.split("--")[0])} &middot; '
            f'{len(pk.get("briefs", []))} briefs &middot; '
            f'{html.escape(pk.get("packed", ""))}</small></a>'
            for key, pk in sorted(reg["packs"].items())
            if not brand or (pk.get("brand") or key.split("--")[0]) == brand) + "</div>"
        packs += ('<p class="pack-note">One zip per brand: a folder per brief with the '
                  'swipe, our draft, the work order, the brief and its prompts, plus a '
                  'README listing the batch and the settings to set once.</p>')
        # Damon, 2026-09-17: "separate <brand> from <brand> and show me the
        # paths in both github and google drive of where these live." One row
        # per brand, each place named by what it holds and linked where a
        # link exists. Read off the register and the pack's run.json, so the
        # page cannot say a path the files are not at.
        packs += where(reg, brand)
        packs += standard()

    page = (tpl.replace("{{PACKS}}", packs)
               .replace("{{SOURCE}}", thumb(frun / "assets/source.jpg"))
               .replace("{{DRAFT}}", thumb(fdrafts[-1]) if fdrafts else "")
               .replace("{{BRIEF_ID}}", ids[0])
               .replace("{{CHIPS}}", "".join(chips))
               .replace("{{PANELS}}", "".join(panels))
               .replace("{{FILTERS}}", filters)
               .replace("{{NBRIEFS}}", str(len(ids)))
               .replace("{{NPLATES}}", str(sum(
                   len(list((ROOT / "worksheets" / reg["briefs"][b]["brand"] / b
                             / "prompts").glob("*.txt"))) for b in ids)))
               .replace("{{BRANDS}}", " and ".join(
                   f"{c} for {b}" for b, c in sorted(counts.items()))))
    Path(out_path).write_text(page)
    return len(ids), len(page)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand"); ap.add_argument("--out", required=True)
    ap.add_argument("--part", default="all",
                    choices=("all", "instructions", "briefs"))
    a = ap.parse_args()
    n, size = build(a.out, a.brand, a.part)
    print(f"{a.out}  ·  {n} briefs  ·  {size/1_000_000:.1f} MB")
