#!/usr/bin/env python3
"""One brief, as a page a person can work from.

    brief_page.py p005                one brief
    brief_page.py --all               every brief with a run behind it
    brief_page.py --all --index       …and the contact sheet over them

Damon, 2026-09-13: *"the brief output: what I want is a clean HTML page that
has all of the details of the brief… I can see the initial swipes and the spec
of the injection."* This is the review surface — he reads it, marks it, and
what he approves is what the designer builds from. It is deliberately NOT a
machine handoff: the step from brief to batch spec is where a person decides,
and automating it would remove the only gate that exists.

The page carries, in this order: what it is, the swipe it came from with its
duplication count, the injected frame zone by zone, the headlines with the
customer sentence behind each, the pictures and what each gives up, then the
whole brief, then what is still waiting on a person.
"""
import base64, html as H, io, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import briefs as B
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_artifact import md            # the lane's own markdown renderer

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "briefs"


def thumb(p: Path, wide=560, q=76):
    from PIL import Image
    im = Image.open(p).convert("RGB")
    im.thumbnail((wide, wide * 3), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def section(text, start, stop=None):
    """One numbered section out of a stage output, as markdown."""
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(stop, i + len(start)) if stop else -1
    return text[i:j if j > 0 else len(text)]


def readiness(bid, rec):
    """Six stages, an id, a draft, a page and a folder on Drive. Anything
    short of that is not ready, and the page must not claim it is."""
    run = HERE / "runs" / rec["run"]
    miss = []
    n = len(list((run / "out").glob("0*.md"))) if (run / "out").is_dir() else 0
    if n < 6:
        miss.append(f"stage {n + 1}")
    d = HERE / "drafts" / rec["brand"]
    if not any((v / f"{bid}-draft.png").is_file() or (v / f"{bid}-plate.png").is_file()
               for v in d.glob("v*") if v.is_dir()):
        miss.append("a draft picture")
    if not rec.get("drive"):
        miss.append("delivery to Drive")
    return miss



def draft(bid, rec_brand, rec_drive=None):
    """The first-pass plate, if one has been generated for this brief.

    A rough draft, deliberately: no type layer, no product composited, no
    offer bar. It exists so the designer starts from a picture rather than
    from a paragraph.
    """
    import json as _json
    # v2 is the concept draft — the whole ad. v1 were plates, which for a
    # product-on-a-stage format is an empty room.
    # Drafts live per brand now, newest version first.
    d = HERE / "drafts" / rec_brand
    cands = []
    for v in sorted((x for x in d.glob("v*") if x.is_dir()),
                    key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else -1, reverse=True):
        cands += [v / f"{bid}-draft.png", v / f"{bid}-plate.png"]
    f = next((c for c in cands if c.is_file()), None)
    if f is None or not f.is_file():
        return ""
    n = f.parent / "notes.json"
    note = ""
    if n.is_file():
        d = _json.loads(n.read_text())
        r = d.get("drafts", {}).get(bid, {})
        bits = []
        if r.get("cast"):
            bits.append(f'<strong>Cast {H.escape(r["cast"])}</strong> &mdash; {H.escape(r["why_cast"])}')
        if r.get("note"):
            bits.append(H.escape(r["note"]))
        bits.append(H.escape(d.get("what", "")))
        note = "".join(f"<p>{b}</p>" for b in bits if b)
    dr = ""
    if rec_drive:
        links = " &middot; ".join(
            f'<a href="{rec_drive[k]}" target="_blank" rel="noopener">{k}</a>'
            for k in ("source", "draft", "brief") if rec_drive.get(k))
        dr = (f'<p><strong><a href="{rec_drive["folder"]}" target="_blank" '
              f'rel="noopener">This brief&rsquo;s folder on Drive</a></strong> '
              f'&mdash; {links}</p>')
    return ('<h2>First pass, for the designer</h2>'
            f'<div class="two"><figure class="swipe"><img src="{thumb(f, 620, 80)}" '
            f'alt="draft"></figure><div class="body">{dr}{note}</div></div>')



def headline(brief_md):
    """The words OUR ad says, off the brief's own "The words, exactly" block.

    Read from there rather than from the injection table, whose first column
    is the *competitor's* copy — the index spent a build titling our briefs
    "50% Off + Free Gifts" and "Is Cortisol Hijacking Your T?", which are
    marsmen's headlines, not ours.
    """
    m = re.search(r"\*\*The words, exactly\.\*\*(.*)", brief_md, re.S)
    if not m:
        return ""
    after = m.group(1)
    h = re.search(r"^Headline[^\n]*:\s*\n+(?:```\s*\n)?((?:[^\n`]+\n){1,3})",
                  after, re.M)
    if not h:
        return ""
    lines = [l.strip() for l in h.group(1).strip().split("\n") if l.strip()]
    return " / ".join(lines)



def decisions(brief_md):
    """What the brief handed back to a person, and who owns each one.

    Stage 6 ends in a numbered list. Only some briefs mark each item
    `**Whose call:** Damon`; the rest say it in the sentence — "the owner
    decides", "the compositor must", "a specific roster man must be selected".
    Reading only the marked form reported three of four briefs as having
    nothing outstanding when between two and six things were, which is the
    worst way for this page to be wrong.
    """
    OWNERS = ((r"\bdamon\b|founder|\bowner\b", "Damon"),
              (r"compositor|production decision", "compositor"),
              (r"casting|roster man", "casting"),
              (r"customer research|research pull", "research"))
    # An item that states its own resolution is a note, not a decision.
    SETTLED = r"not a defect|awareness only|resolved by the injection|accepted in the injection|accepting the difference"

    tail = section(brief_md, "**Carried forward")
    out = []
    for block in re.split(r"\n(?=\d+\.\s+\*\*)", tail):
        m = re.match(r"\d+\.\s+\*\*(.+?)\*\*", block, re.S)
        if not m:
            continue
        title = re.split(r"\s+[—–-]\s+|\s*\(", m.group(1).strip().rstrip("."),
                         maxsplit=1)[0]
        marked = re.search(r"\*\*Whose call:\*\*\s*([^.\n]+)", block)
        if marked:
            owner, settled = marked.group(1).strip().rstrip("."), False
        else:
            owner = next((who for pat, who in OWNERS
                          if re.search(pat, block, re.I)), "unassigned")
            settled = bool(re.search(SETTLED, block, re.I))
        out.append({"what": title, "who": owner, "settled": settled})
    return out


CSS = """
:root{--ink:#14150f;--ink-2:#575c50;--ink-3:#8d9287;--ground:#f2f1ea;--card:#fff;--line:#dfdcd2;
--flag:#8a6a12;--flag-bg:#f6ecd2;--ok:#2f6b3d;--ok-bg:#e3efe4;
--sans:"Archivo",-apple-system,sans-serif;--serif:"Newsreader",Georgia,serif;--mono:"JetBrains Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ink:#edeee7;--ink-2:#a7aca0;--ink-3:#6f746a;
--ground:#0f100c;--card:#191a15;--line:#292b25;--flag:#d9b752;--flag-bg:#282010;--ok:#7ec48d;--ok-bg:#16251a}}
:root[data-theme="dark"]{--ink:#edeee7;--ink-2:#a7aca0;--ink-3:#6f746a;--ground:#0f100c;--card:#191a15;
--line:#292b25;--flag:#d9b752;--flag-bg:#282010;--ok:#7ec48d;--ok-bg:#16251a}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);line-height:1.55;margin:0}
.wrap{max-width:980px;margin:0 auto;padding:40px 20px 90px}
.id{font:600 12px var(--mono);letter-spacing:.12em;color:var(--ink-3);margin:0 0 8px}
.lede{font-family:var(--serif);font-size:17px;color:var(--ink-2);margin:11px 0 0;max-width:62ch}
h1{font-weight:800;font-size:clamp(27px,4.4vw,40px);margin:0;letter-spacing:-.025em;text-wrap:balance}
header{border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:26px}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:13px}
.chip{font:600 10px var(--mono);letter-spacing:.1em;text-transform:uppercase;padding:4px 9px;
  border-radius:999px;background:var(--card);border:1px solid var(--line);color:var(--ink-2)}
.chip.flag{background:var(--flag-bg);color:var(--flag);border-color:transparent}
.chip.ok{background:var(--ok-bg);color:var(--ok);border-color:transparent}
h2{font-size:12px;font-weight:800;letter-spacing:.15em;text-transform:uppercase;margin:40px 0 12px;
  border-top:2px solid var(--ink);padding-top:12px}
.two{display:grid;grid-template-columns:minmax(0,260px) minmax(0,1fr);gap:22px;align-items:start}
@media(max-width:680px){.two{grid-template-columns:1fr}}
.swipe{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.swipe img{width:100%;display:block}
.swipe figcaption{padding:11px 13px;font-size:12.5px;color:var(--ink-2)}
.body{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 22px}
.body :first-child{margin-top:0} .body :last-child{margin-bottom:0}
.body p{font-size:14.5px;color:var(--ink-2)} .body strong{color:var(--ink)}
.body h1,.body h2,.body h3,.body h4{font-size:14px;font-weight:800;letter-spacing:0;text-transform:none;
  border:0;padding:0;margin:20px 0 7px;color:var(--ink)}
.body ul,.body ol{font-size:14.5px;color:var(--ink-2);padding-left:20px}
.body li{margin:4px 0}
.body blockquote{margin:10px 0;padding:0 0 0 14px;border-left:2px solid var(--line);
  font-family:var(--serif);font-size:15.5px}
code{font:400 12.5px var(--mono);background:var(--ground);padding:1.5px 5px;border-radius:4px}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:520px}
th{text-align:left;font:600 10.5px var(--mono);letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-3);padding:0 11px 7px 0;border-bottom:1px solid var(--line)}
td{padding:9px 11px 9px 0;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink-2)}
td:first-child{color:var(--ink);font-weight:600}
.mark{color:var(--flag);font-weight:700}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:0 18px;margin:10px 0}
summary{cursor:pointer;padding:14px 0;font-weight:800;font-size:14px;list-style:none}
summary::-webkit-details-marker{display:none}
summary:before{content:"▸ ";color:var(--ink-3)} details[open] summary:before{content:"▾ "}
details .inner{padding-bottom:16px;border-top:1px solid var(--line);padding-top:14px}
footer{margin-top:48px;border-top:1px solid var(--line);padding-top:14px;
  font:400 11.5px var(--mono);color:var(--ink-3);line-height:1.9}
a{color:inherit}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}
.card{display:block;text-decoration:none;background:var(--card);border:1px solid var(--line);
  border-radius:10px;overflow:hidden}
.card img{width:100%;display:block;aspect-ratio:4/5;object-fit:cover}
.card .t{padding:12px 14px}
.card h3{margin:0 0 4px;font-size:14px;font-weight:800}
.card p{margin:0;font-size:12.5px;color:var(--ink-3)}\n.card .state{margin-top:7px;font:600 11px var(--mono);letter-spacing:.04em}\n.card .state.flag{color:var(--flag)} .card .state.ok{color:var(--ok)}
"""


def render(bid, rec, reg, extra=""):
    run = HERE / "runs" / rec["run"]
    out = run / "out"
    read = lambda n: (out / n).read_text() if (out / n).is_file() else ""
    brief, inj, hooks, pics = (read("06-brief.md"), read("03-injection.md"),
                               read("04-headlines.md"), read("05-image-variations.md"))
    sw = rec.get("swipe", {})
    src = run / "assets/source.jpg"
    # The one-liner the brief opens with — the lede, not the title.
    m = re.search(r"\*\*What this is\.\*\*\s*(.+?)(?:\n\n|\Z)", brief, re.S)
    what = m.group(1).strip() if m else ""
    d = rec.get("declares", {})

    # The title is the control headline — the words the ad actually says. A
    # truncated first sentence ("…where the problem is nam") is not a name.
    title = headline(brief) or str(sw.get("block") or rec["run"])

    dec = decisions(brief)
    mine = [x for x in dec if "damon" in x["who"].lower() and not x["settled"]]
    chips = [f'<span class="chip">{H.escape(rec["brand"])}</span>']
    for k in ("problem", "concept"):
        if d.get(k):
            chips.append(f'<span class="chip">{H.escape(d[k])}</span>')
    if d.get("angle") in (None, "", "unsigned"):
        chips.append('<span class="chip flag">No angle yet</span>')
    else:
        chips.append(f'<span class="chip ok">{H.escape(d["angle"])}</span>')
    if sw.get("clone"):
        chips.append(f'<span class="chip">Cloned {sw["clone"]}&times;</span>')
    miss = readiness(bid, rec)
    chips.append('<span class="chip ok">Ready for the designer</span>' if not miss
                 else f'<span class="chip flag">Waiting on {H.escape(", ".join(miss))}</span>')

    swipe_fig = ""
    if src.is_file():
        link = sw.get("drive") or "#"
        swipe_fig = (f'<figure class="swipe"><a href="{H.escape(link)}" target="_blank" '
                     f'rel="noopener"><img src="{thumb(src)}" alt="the swipe"></a>'
                     f'<figcaption><strong>{H.escape(str(sw.get("block") or "the swipe"))}</strong>'
                     f'<br>{H.escape(str(sw.get("why") or ""))}'
                     + (f'<br>cloned {sw["clone"]}&times; across {sw["variants"]} variants'
                        if sw.get("clone") else "")
                     + '</figcaption></figure>')

    def block(title, body_md, open_=False):
        if not body_md.strip():
            return ""
        o = " open" if open_ else ""
        return (f'<details{o}><summary>{H.escape(title)}</summary>'
                f'<div class="inner body">{md(body_md)}</div></details>')

    carried = section(brief, "**Carried forward", None)
    parts = [
        f'<div class="wrap"><header><p class="id">{bid} &middot; {H.escape(rec["run"])} '
        f'&middot; opened {rec["opened"]}</p>'
        f'<h1>{H.escape(title)}</h1>'
        + (f'<p class="lede">{H.escape(what)}</p>' if what else "")
        + f'<div class="chips">{"".join(chips)}</div></header>',

        extra,
        draft(bid, rec['brand'], rec.get('drive')),
        '<h2>The swipe, and what we put through it</h2>',
        f'<div class="two">{swipe_fig}<div class="body">{md(section(inj, "**1. THE INJECTED FRAME", "**2."))}</div></div>',

        '<h2>The work</h2>',
        block("The headlines — six, each on its own axis", section(hooks, "## 3. THE FIVE VARIATIONS", "## 4.")
              or section(hooks, "## 2. VERSION 0", "## 4."), open_=True),
        block("The pictures — one variable moved each time", pics),
        block("The art direction, zone by zone", section(inj, "**3. THE ART DIRECTION", "**4.")),
        block("The whole brief, as written", brief),
    ]
    if dec:
        rows = "".join(
            f'<tr><td>{H.escape(x["what"])}</td><td>{H.escape(x["who"])}</td>'
            f'<td>{"settled in the brief" if x["settled"] else "open"}</td></tr>'
            for x in dec)
        parts += ['<h2>Open notes</h2>',
                  '<div class="body"><div class="scroll"><table><thead><tr>'
                  '<th>What</th><th>Who decides</th><th>State</th></tr></thead><tbody>'
                  + rows + '</tbody></table></div></div>',
                  block("Each one, in full", carried)]
    parts.append(
        f'<footer>Brief register: <code>image-teardown/briefs.json</code> &middot; '
        f'run: <code>runs/{H.escape(rec["run"])}</code> &middot; '
        f'the id travels into every ad name as the <code>brief</code> field<br>'
        f'Stage two takes this page, not a file: cast, generate, keep or kill, '
        f'and every kill records why.</footer></div>')

    page = ('<meta charset="utf-8">'
            f'<title>Brief {bid}</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Archivo:wght@400;600;800&family=Newsreader:opsz,wght@6..72,400&'
            'family=JetBrains+Mono:wght@400;600&display=swap">'
            f'<style>{CSS}</style>' + "".join(parts))
    return page


LINK2 = ""         # "" on disk (brand-x.html), "/brand/" under the server
LINK = ""          # "" on disk (p005.html), "/b/" under the server


def brands(reg):
    """One card per brand. Briefs never appear in a mixed list.

    Damon, 2026-09-14: *"This would be a different brief for a different
    brand. They should not live together. We already established this."* He
    is right — everything else is keyed by brand (runs, drafts, baselines,
    Drive) and this page was the one place two brands were shown as one
    stream.
    """
    rows = {}
    for bid, r in reg["briefs"].items():
        if r.get("run"):
            rows.setdefault(r["brand"], []).append((bid, r))
    cards = ""
    for br in sorted(rows):
        ids = sorted(rows[br])
        last = max(r.get("opened", "") for _, r in ids)
        shown = None
        for bid, r in reversed(ids):
            d = HERE / "drafts" / br
            for v in sorted((x for x in d.glob("v*") if x.is_dir()),
                            key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else -1, reverse=True):
                for n in (f"{bid}-draft.png", f"{bid}-plate.png"):
                    if (v / n).is_file():
                        shown = v / n; break
                if shown: break
            if shown: break
        img = f'<img src="{thumb(shown, 420, 68)}" alt="">' if shown else ""
        cards.append if False else None
        href = f"{LINK2}{br}" if LINK2 else f"brand-{br}.html"
        cards += (f'<a class="card" href="{href}">{img}<div class="t">'
                  f'<h3>{H.escape(br)}</h3>'
                  f'<p>{len(ids)} brief{"s" if len(ids) != 1 else ""} '
                  f'&middot; newest {H.escape(last)}</p></div></a>')
    return ('<meta charset="utf-8">'
            '<title>Briefs</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Archivo:wght@400;600;800&family=Newsreader:opsz,wght@6..72,400&'
            'family=JetBrains+Mono:wght@400;600&display=swap">'
            f'<style>{CSS}</style><div class="wrap"><header>'
            '<p class="id">lab/damon &middot; the static ad machine</p><h1>Briefs</h1>'
            '<p class="lede">One swipe in, one brief out. Every brand keeps its own '
            'briefs, its own runs, its own cast and its own folder on Drive &mdash; '
            'nothing is shared but the machine.</p></header>'
            f'<div class="grid">{cards}</div>'
            '<footer>Brief ids come out of a separate block per brand, so two brands '
            'can never be handed the same one.</footer></div>')


def index(reg, brand=None):
    # The example row is whatever this register last ran, so the page names
    # no brand of its own. A placeholder shows before the first run.
    eg = {"brand": "&lt;brand&gt;", "product": "&lt;product&gt;",
          "avatar": "&lt;avatar or lane&gt;", "swipe": "&lt;competitor&gt;"}
    last = max((r for r in reg["briefs"].values()
                if r.get("run") and (not brand or r.get("brand") == brand)),
               key=lambda r: r.get("opened", ""), default=None)
    if last:
        eg = {"brand": last.get("brand", eg["brand"]),
              "product": last.get("product") or "&lt;product&gt;",
              "avatar": last.get("avatar") or "&lt;avatar or lane&gt;",
              "swipe": last["swipe"].get("brand") or eg["swipe"]}
    cards = []
    for bid, rec in sorted(reg["briefs"].items(), reverse=True):
        if not rec.get("run"):
            continue                      # reserved ids are bookkeeping, not work
        if brand and rec.get("brand") != brand:
            continue                      # a brand's briefs never mix with another's
        run = HERE / "runs" / rec["run"]
        src = run / "assets/source.jpg"
        b = (run / "out/06-brief.md")
        dec = decisions(b.read_text()) if b.is_file() else []
        mine = [x for x in dec if "damon" in x["who"].lower() and not x["settled"]]
        dd = HERE / "drafts" / rec["brand"]
        cands = []
        for v in sorted((x for x in dd.glob("v*") if x.is_dir()),
                        key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else -1, reverse=True):
            cands += [v / f"{bid}-draft.png", v / f"{bid}-plate.png"]
        shown = next((c for c in cands if c.is_file()), src)
        img = f'<img src="{thumb(shown, 420, 68)}" alt="">' if shown.is_file() else ""
        title = re.search(r"<h1>(.*?)</h1>", (OUT / f"{bid}.html").read_text()) \
            if (OUT / f"{bid}.html").is_file() else None
        name = title.group(1) if title else rec["run"]
        m = readiness(bid, rec)
        state = "Ready for the designer" if not m else "Waiting on " + ", ".join(m)
        cls = "ok" if not m else "flag"
        cards.append(
            f'<a class="card" href="{LINK}{bid}{"" if LINK else ".html"}">{img}<div class="t">'
            f'<h3>{name}</h3>'
            f'<p>{bid} &middot; {H.escape(str(rec["swipe"].get("brand") or rec["brand"]))} swipe'
            + (f' &middot; cloned {rec["swipe"]["clone"]}&times;' if rec["swipe"].get("clone") else "")
            + f'</p><p class="state {cls}">{state}</p></div></a>')

    page = ('<meta charset="utf-8">'
            '<title>Briefs</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Archivo:wght@400;600;800&family=Newsreader:opsz,wght@6..72,400&'
            'family=JetBrains+Mono:wght@400;600&display=swap">'
            f'<style>{CSS}</style><div class="wrap"><header>'
            f'<p class="id"><a href="index.html">&larr; all brands</a></p>'
            f'<h1>{H.escape(brand or "Briefs")}</h1>'
            '<p class="lede">One swipe in, one brief out. Every brief keeps its id for '
            'life, and that id rides in every ad name it produces &mdash; so a Meta report '
            'can be grouped by the brief that made the winner.</p></header>'

            '<h2>Start a run</h2>'
            '<div class="body"><p>Say these four. Nothing else is needed.</p>'
            '<div class="scroll"><table><thead><tr><th>&nbsp;</th><th>What to give</th>'
            f'<th>{"Last run" if eg else "Example"}</th></tr></thead><tbody>'
            f'<tr><td>Brand</td><td>whose language, avatars and offer get injected</td>'
            f'<td><code>{eg["brand"]}</code></td></tr>'
            f'<tr><td>Product</td><td>the thing being sold</td>'
            f'<td><code>{eg["product"]}</code></td></tr>'
            f'<tr><td>Who it is for</td><td>the core avatar, or the lane</td>'
            f'<td><code>{eg["avatar"]}</code></td></tr>'
            f'<tr><td>Swipe</td><td>whose ads to build from</td>'
            f'<td><code>{eg["swipe"]}</code></td></tr>'
            '</tbody></table></div>'
            f'<blockquote>Run the image chain for <strong>{eg["brand"]} {eg["product"]}'
            f'</strong>, aimed at <strong>{eg["avatar"]}</strong>, off the '
            f'<strong>{eg["swipe"]}</strong> swipe.</blockquote>'
            '<p>Add a count and a rule if you want them &mdash; <em>three shapes, the '
            'most-cloned</em>. Left unsaid, it takes the most-duplicated shapes in that file, '
            'because a competitor rebuilding the same ad dozens of times is the only free '
            'signal there is.</p>'
            '<p><strong>You never say</strong> which stages to run, how many headlines, what '
            'to name the brief, or which pictures are worth making. <strong>You always get '
            'back</strong> a brief id, a page like the ones below, and every note the chain '
            'resolved on its way there.</p></div>'

            f'<h2>The briefs</h2><div class="grid">{"".join(cards)}</div>'
            '<footer>A brief is the review gate. Nothing turns one into a production '
            'spec automatically &mdash; a person reads it, decides what is missing, and '
            'hands it to the designer.</footer></div>')
    return page


if __name__ == "__main__":
    reg = B.load()
    args = sys.argv[1:]
    ids = [a for a in args if a.startswith("p")]
    if "--all" in args:
        ids = [b for b, r in reg["briefs"].items() if r.get("run")]
    OUT.mkdir(exist_ok=True)
    for bid in ids:
        rec = reg["briefs"].get(bid)
        if not rec or not rec.get("run"):
            print(f"! {bid} has no run behind it"); continue
        (OUT / f"{bid}.html").write_text(render(bid, rec, reg))
        print("wrote", (OUT / f"{bid}.html").relative_to(HERE))
    if "--index" in args or "--all" in args:
        (OUT / "index.html").write_text(brands(reg))
        print("wrote", (OUT / "index.html").relative_to(HERE))
        for br in sorted({r["brand"] for r in reg["briefs"].values() if r.get("run")}):
            (OUT / f"brand-{br}.html").write_text(index(reg, br))
            print("wrote", (OUT / f"brand-{br}.html").relative_to(HERE))
