#!/usr/bin/env python3
"""Render the import kit as one page to read before anything is imported.

    python3 components/meta-upload/review_page.py --kit <dir> --out page.html

Reads only what build.py already emitted, plus the copy the sheet quotes.
"""
import argparse, base64, csv, html, io, json, sys
from collections import OrderedDict
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand import Brand

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "components/naming"))
import names as N            # parse_any: an ad name in either form -> its fields


def fields(ad_name):
    """format / concept / asset off the name by field, whichever form the
    sheet carries. A name that is not ours gives blanks, not a crash."""
    f = N.parse_any(ad_name) or {}
    return f.get("format", ""), f.get("concept", ""), f.get("asset", ad_name.rsplit("-", 1)[-1])


def thumb(p, w=190):
    im = Image.open(p).convert("RGB")
    im.thumbnail((w, w * 4), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def esc(s):
    return html.escape(str(s or ""))


CSS = """
:root{
  --ink:#15130f; --ink-2:#4a453c; --ink-3:#8a8275;
  --ground:#faf8f4; --card:#ffffff; --line:#e4dfd4;
  --live:#1f6f4a; --live-bg:#e8f2ec;
  --held:#9a3412; --held-bg:#fdf0e7;
  --wait:#6b5f8a; --wait-bg:#f0ecf6;
  --rule:#c9c1b2;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ink:#f2efe8; --ink-2:#b8b1a4; --ink-3:#7d7568;
  --ground:#14130f; --card:#1d1b16; --line:#2f2c25;
  --live:#7fd4a6; --live-bg:#16281f;
  --held:#f0a97a; --held-bg:#2b1d13;
  --wait:#c0aee8; --wait-bg:#211b2c;
  --rule:#3a362d;
}}
:root[data-theme="dark"]{
  --ink:#f2efe8; --ink-2:#b8b1a4; --ink-3:#7d7568;
  --ground:#14130f; --card:#1d1b16; --line:#2f2c25;
  --live:#7fd4a6; --live-bg:#16281f;
  --held:#f0a97a; --held-bg:#2b1d13;
  --wait:#c0aee8; --wait-bg:#211b2c;
  --rule:#3a362d;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font:15px/1.55 "Iowan Old Style",Charter,Georgia,serif;}
.wrap{max-width:1120px;margin:0 auto;padding:40px 28px 90px}
h1{font-size:34px;line-height:1.1;margin:0 0 6px;letter-spacing:-.02em;text-wrap:balance}
.sub{color:var(--ink-2);margin:0 0 30px;font-size:16px;max-width:62ch}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.eyebrow{font:600 11px/1 ui-sans-serif,system-ui;letter-spacing:.13em;
  text-transform:uppercase;color:var(--ink-3);margin:0 0 12px}

.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));
  gap:1px;background:var(--line);border:1px solid var(--line);border-radius:9px;
  overflow:hidden;margin-bottom:38px}
.cell{background:var(--card);padding:15px 16px}
.cell .n{font:600 27px/1 ui-sans-serif,system-ui;font-variant-numeric:tabular-nums;
  letter-spacing:-.02em}
.cell .l{font:500 11px/1.3 ui-sans-serif,system-ui;letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink-3);margin-top:6px}
.cell.go .n{color:var(--live)} .cell.hold .n{color:var(--held)} .cell.wait .n{color:var(--wait)}

.set{background:var(--card);border:1px solid var(--line);border-radius:11px;
  margin-bottom:20px;overflow:hidden}
.set > summary{list-style:none;cursor:pointer;padding:17px 20px;
  display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.set > summary::-webkit-details-marker{display:none}
.set > summary:hover{background:var(--ground)}
.set h2{margin:0;font-size:20px;letter-spacing:-.01em}
.count{font:600 12px/1 ui-sans-serif,system-ui;color:var(--live);
  background:var(--live-bg);padding:5px 9px;border-radius:20px}
.targ{color:var(--ink-3);font:400 13px/1 ui-sans-serif,system-ui;margin-left:auto}
.body{padding:0 20px 22px;border-top:1px solid var(--line)}
.lands{font:400 13px/1.5 ui-sans-serif,system-ui;color:var(--ink-2);
  padding:13px 0;border-bottom:1px solid var(--line);margin-bottom:16px}
.lands a{color:inherit}
.lands b{font-weight:600;color:var(--ink)}

.copy{border-left:2px solid var(--rule);padding:2px 0 2px 15px;margin:0 0 18px}
.copy .t{font-weight:600;margin-bottom:3px}
.copy .d{color:var(--ink-3);font-size:13px;margin-bottom:8px}
.copy .b{color:var(--ink-2);font-size:14px;white-space:pre-wrap}
.fmt{font:600 11px/1 ui-sans-serif,system-ui;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ink-3);margin:20px 0 9px}
.shelf{display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:11px}
.shelf figure{margin:0}
.shelf img{width:100%;border-radius:6px;display:block;border:1px solid var(--line)}
.shelf figcaption{font:400 10px/1.35 ui-monospace,Menlo,monospace;
  color:var(--ink-3);margin-top:5px;word-break:break-all}

table{width:100%;border-collapse:collapse;font:400 13px/1.5 ui-sans-serif,system-ui}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
th{text-align:left;font:600 11px/1 ui-sans-serif,system-ui;letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink-3);padding:0 14px 9px 0;
  border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 14px 9px 0;border-bottom:1px solid var(--line);vertical-align:top}
td.m{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:var(--ink-2)}
section{margin-top:44px}
h3{font-size:22px;margin:0 0 6px;letter-spacing:-.01em}
.note{color:var(--ink-2);font-size:14px;margin:0 0 18px;max-width:66ch}
.tag{display:inline-block;font:600 10px/1 ui-sans-serif,system-ui;
  padding:4px 7px;border-radius:4px;letter-spacing:.05em;text-transform:uppercase}
.tag.h{color:var(--held);background:var(--held-bg)}
.tag.w{color:var(--wait);background:var(--wait-bg)}
.tag.g{color:#2E7D52;background:#E4F2EA}
footer{margin-top:56px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--ink-3);font:400 13px/1.6 ui-sans-serif,system-ui}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    kit = Path(a.kit)
    s = json.loads((kit / "summary.json").read_text())
    rows = list(csv.DictReader((kit / "import.csv").open(encoding="utf-8-sig")))
    # Brand, lane and run all come off the kit's own summary, so this tool
    # takes no brand flag and names no brand.
    b    = Brand(s["brand"])
    book = json.loads((b.copy / s["run"] / "copy.json").read_text())["formats"]
    sets = json.loads(b.adsets.read_text()) if b.adsets else {"sub_avatars": {}}

    by_set = OrderedDict()
    for r in rows:
        by_set.setdefault(r["Ad Set Name"], []).append(r)

    title = f'{s.get("campaign", "Upload Kit")} \u00b7 {s["run"]}'
    o = [f"<title>{esc(title)}</title><style>{CSS}</style>",
         '<div class="wrap">',
         '<p class="eyebrow">' + esc(s.get("brand", "").upper()) + ' \u00b7 '
         + esc(s.get("lane", "")) + ' \u00b7 built ' + esc(s["run"]) + '</p>',
         "<h1>" + esc(s.get("campaign", "Upload Kit")) + "</h1>",
         '<p class="sub">The 138 pictures are already in the account, paused, in six '
         'ad sets by avatar. This is the re-cut: <b>thirteen ad sets, split by avatar '
         '&times; the man in the picture &times; the promise the ad makes</b> &mdash; the '
         'three things Meta must not be allowed to choose between, because inside one '
         'ad set it backs one and starves the rest. It separates the creative so each '
         'gets shown; every ad set still buys the same broad 18&ndash;65+ US audience. '
         'Nothing here can spend &mdash; every campaign, ad set and ad is PAUSED.</p>']

    held, gaps = s["held_back"], s["gaps"]
    o.append('<div class="strip">')
    for n, l, k in [(s["ads"], "ads ready", "go"), (len(by_set), "ad sets", ""),
                    ("$" + s["daily_budget"], "a day, campaign-wide", ""),
                    (len(held), "held by review", "hold"),
                    (len(gaps), "waiting on copy", "wait")]:
        o.append(f'<div class="cell {k}"><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>')
    o.append("</div>")

    o.append('<p class="eyebrow">One ad set per avatar &times; man &times; promise</p>')
    # An ad set has "its own page" when it does not land where most of the
    # others do. When every ad set shares one link — a brand running the
    # offer page while the per-avatar presells are still being written — the
    # shared one is called out and nothing is flagged as bespoke.
    from collections import Counter
    link_counts = Counter(r["Link"] for r in rows)
    shared_link = link_counts.most_common(1)[0][0] if len(link_counts) > 1 else (
        link_counts.most_common(1)[0][0] if link_counts else "")
    all_same = len(link_counts) == 1

    for name, rs in sorted(by_set.items(), key=lambda kv: -len(kv[1])):
        # the ad set's own rows are the truth for where it lands and who it buys
        link = rs[0]["Link"]
        sub  = rs[0]["URL Tags"].split("utm_term=")[-1]
        t = sets["sub_avatars"].get(sub, {})
        own = not (all_same or link == shared_link)
        o.append(f'<details class="set" open><summary><h2>{esc(name)}</h2>'
                 f'<span class="count">{len(rs)} ads</span>'
                 f'<span class="targ">{esc(rs[0]["Age Min"])}–{esc(rs[0]["Age Max"])}+ · US · all placements</span>'
                 f"</summary><div class='body'>")
        o.append('<p class="lands">Lands on <b><a href="%s">%s</a></b>%s<br>%s</p>' % (
            esc(link), esc(link.replace("https://", "").rstrip("/")),
            "" if own else " — the shared page, until this avatar&rsquo;s own presell is written",
            esc(t.get("note", ""))))

        # Group by the IDEA, not the brief. An idea is one format carrying one
        # headline: its pictures are variations of each other and belong side
        # by side. Grouping by brief id (which is what this did until
        # 2026-09-11) splits one idea across two blocks whenever it was built
        # in two production runs, and the variations then read as duplicates.
        # the owner, looking at exactly that: "these are still the same....".
        by_idea = OrderedDict()
        for r in rs:
            by_idea.setdefault((fields(r["Ad Name"])[0], r["Title"]), []).append(r)
        for (f, title), frs in sorted(by_idea.items(), key=lambda kv: -len(kv[1])):
            n = len(frs)
            state = ("full" if n >= 3 else "thin")
            o.append(f'<p class="fmt">{esc(f)} &middot; <b>{esc(title)}</b> '
                     f'<span class="tag {"g" if n >= 3 else "w"}">{n} of 3</span>'
                     f'{"" if n >= 3 else " &mdash; needs " + str(3 - n) + " more"}</p>')
            v = frs[0]
            o.append('<div class="copy"><div class="t">%s</div><div class="d">%s</div>'
                     '<div class="b">%s</div></div>'
                     % (esc(v["Title"]), esc(v["Link Description"]), esc(v["Body"])))
            o.append('<div class="shelf">')
            for r in frs:
                p = kit / "images" / r["Image File Name"]
                if p.is_file():
                    o.append('<figure><img alt="%s" src="%s"><figcaption>%s</figcaption></figure>'
                             % (esc(r["Ad Name"]), thumb(p),
                                esc(" ".join(fields(r["Ad Name"])[1:]))))
            o.append("</div>")
        o.append("</div></details>")

    if held:
        o.append('<section><h3>Held by the review</h3><p class="note">These never reach '
                 'the account. Either you killed them, or the headline audit found the '
                 'picture does not show what its headline claims.</p><div class="scroll">'
                 "<table><tr><th>Ad</th><th>Why</th></tr>")
        for h in held:
            o.append(f'<tr><td class="m">{esc(h["ad"][-46:])}</td><td>'
                     f'<span class="tag h">held</span> {esc(h["why"])}</td></tr>')
        o.append("</table></div></section>")

    if gaps:
        g = OrderedDict()
        for x in gaps:
            g.setdefault((x["format"], x["sub_avatar"]), []).append(x)
        o.append('<section><h3>Waiting on copy</h3><p class="note">Pictures exist for '
                 'these, but no copy has been written for that format and that '
                 'sub-avatar. A picture never ships with words written for someone '
                 'else, so they sit out until the copy lands.</p><div class="scroll">'
                 "<table><tr><th>Format</th><th>Sub-avatar</th><th>Man</th><th>Pictures</th></tr>")
        for (f, sub), xs in sorted(g.items()):
            o.append(f"<tr><td>{esc(f)}</td><td>{esc(sub)}</td><td>{esc(xs[0]['talent'])}</td>"
                     f'<td><span class="tag w">{len(xs)}</span></td></tr>')
        o.append("</table></div></section>")

    o.append('<footer>One CBO campaign at $%s a day. Ad set budgets and spend limits '
             'left blank, so the campaign budget decides where the money goes. '
             'One row per picture, because Meta takes one image per ad. '
             'Every ad name carries all thirteen fields, so the spend report joins '
             'straight back to the picture that earned it.<br><br>'
             'Built by <span class="mono">components/meta-upload/build.py</span>. '
             'Rebuild it any time — the sheet is disposable.</footer></div>'
             % esc(s["daily_budget"]))

    Path(a.out).write_text("\n".join(o), encoding="utf-8")
    print(f"{Path(a.out)}  ({Path(a.out).stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
