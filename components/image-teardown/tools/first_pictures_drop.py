#!/usr/bin/env python3
"""First pictures, packed for the designer: one drop, one page, and it grows as briefs land.

    first_pictures_drop.py build <list.json> [--no-pack]     the drop, on disk and on Drive
    first_pictures_drop.py page <list.json> [<list.json> ...] --html <file> --md <file> --pics <folder>

A list is runs/image-teardown/<brand>/<drop>/list.json. It names the drop and each brief in it:

    {"brand", "product", "drop", "batch", "title", "offer": [lines], "window", "links": {name: url},
     "general_note": "a note for every brief, optional",
     "briefs": [{"code": "01", "run": "<teardown run>", "ready": true, "note": "open note, or empty",
                 "printed": true when the words are part of the picture itself}]}

`build` takes only the `ready` briefs, so a brief waiting on a reprint stays on the list and drops in by turning it
true and building again. For each it packs the designer's hand-off (components/image-edit/handoff.py: the variation
prompts, their pictures and the run sheet), then writes the drop components/ad-handoff checks: one folder per ad, the
ad name on the folder, copy.csv, drop.csv, links.json and HANDOFF.md, mirrored to Shared Assets at the same path.
Nothing is deleted, on disk or on Drive, and nothing is sent. This tool builds; components/ad-handoff/handoff.py is
the gate that says whether it passes.

copy.csv's primary_text holds the offer lines, which is all a first-picture drop has: the ad copy for Meta comes from
the copy machine when an ad is filed. The HANDOFF page says so.

`page` writes one page and its Markdown mirror from any number of lists; a brief not ready shows as waiting.
"""
import argparse
import base64
import csv
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402
import briefs as B  # noqa: E402
import deliver as DV  # noqa: E402

WS = P.REPO
sys.path.insert(0, str(WS / "components/naming"))
sys.path.insert(0, str(WS / "components/image-edit"))
import names as N  # noqa: E402
from image_edit import handoff as H  # noqa: E402


def load(f):
    d = json.loads(Path(f).read_text())
    d["home"] = Path(f).resolve().parent
    return d


def run_of(row, d):
    return WS / "runs/image-teardown" / d["brand"] / row["run"]


def swipe_of(row, d):
    got = sorted((run_of(row, d) / "assets").glob("source.*"))
    return next((x for x in got if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")), None)


def words_of(row, d):
    """The approved picture's words, as the writing station recorded them: one line per zone."""
    f = run_of(row, d) / "out/approved-words.md"
    lines = f.read_text().splitlines() if f.is_file() else []
    got = [ln.split("`")[1].replace("\xa0", " ") for ln in lines if ln.startswith("- Zone") and ln.count("`") >= 2]
    return [w for w in got if w.strip() and not w.lower().startswith("none")]


def variations_of(row, d):
    f = run_of(row, d) / "out/variations.json"
    return (json.loads(f.read_text()).get("variations") or []) if f.is_file() else []


def number(row, d):
    """The brief's number from the register, opened through the register's own door."""
    return B.open_brief(row["run"], d["brand"], B.load(), d["product"], d.get("avatar"))


def pack(row, d):
    """The designer's folder, through its own door. Returns (link, folder) or raises with the door's refusal."""
    r = subprocess.run([sys.executable, str(WS / "components/image-edit/handoff.py"), row["run"], "--brand", d["brand"]],
                       capture_output=True, text=True, cwd=str(WS))
    said = r.stdout + r.stderr
    if r.returncode:
        raise SystemExit(f"{row['code']}: the hand-off pack refused: {said.strip()[-400:]}")
    link = next((ln.split("link:", 1)[1].strip() for ln in r.stdout.splitlines() if ln.startswith("link:")), "")
    return link


def packed(row, d):
    """The Drive link of a variation folder packed earlier, from its own handoff.json."""
    key = number(row, d)[0]
    f = H.folder_of(d["brand"], H.home_key(d["brand"], key)) / "handoff.json"
    return (json.loads(f.read_text()).get("drive") or {}).get("link", "") if f.is_file() else ""


def build_ad(row, d, out, link):
    key, rec = number(row, d)
    bid = rec.get("brief") or key
    ad = f"{d['brand']}_{d['product']}_{bid}_{d['batch']}"
    if N.parse_any(ad) is None:
        raise SystemExit(f"{ad} does not parse to the naming convention")
    folder = out / ad
    (folder / "reference").mkdir(parents=True, exist_ok=True)
    pic = H.approved_of(row["run"], d["brand"])
    name = f"{ad}_asset-01.png"
    shutil.copy2(pic, folder / name)
    sw = swipe_of(row, d)
    if sw:
        shutil.copy2(sw, folder / "reference" / f"swipe{sw.suffix.lower()}")
    words = words_of(row, d)
    manifest = {"ad_name": ad, "brief": bid, "brief_key": key, "code": row["code"], "run": row["run"],
                "picture": str(pic.relative_to(WS)), "words": words, "offer": d["offer"],
                "note": row.get("note") or "", "printed": bool(row.get("printed")), "variations": variations_of(row, d), "pack": link,
                "ads": [{"name": name.rsplit(".", 1)[0], "file": name, "what": "the first picture, final",
                         "headline": " · ".join(words)}]}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    return manifest


def drive_home(d):
    engine, svc = DV.service()
    node = engine.shared_drive_id("Shared Assets", svc)
    for part in ("runs", "image-teardown", d["brand"], d["drop"], "deliverable"):
        node = engine.folder(part, node, svc=svc)
    return engine, svc, node


def handoff_page(d, ads, folder_id):
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    out = [f"# {d['title']}", "", f"### 📁 {url}", "",
           f"*Shared Assets › runs › image-teardown › {d['brand']} › {d['drop']} › deliverable*", "",
           f"**{len(ads)} ads, one final first picture each.** editor runs the variations with the designer. The chain makes "
           "them, the designer approves them. Each ad's variation folder holds the prompts, the pictures to upload and "
           "the words guide; finished pictures go in that folder's `returned/`.", "",
           f"**Offer:** {' · '.join(d['offer'])}. **Window:** {d['window']}.", "",
           "The folder name is the ad name. `copy.csv` holds the offer lines; the ad copy for Meta comes from the copy "
           "machine when an ad is filed.", ""] + ([f"**Every brief:** {d['general_note']}", ""] if d.get("general_note") else [])
    for a in ads:
        out += [f"## Brief {a['code']} · {a['brief']}", "", f"`{a['ad_name']}`", "",
                f"[Variation folder]({a['pack']})" if a["pack"] else "", "",
                "Words on the picture: " + " · ".join(a["words"]), ""]
        if a["note"]:
            out += [f"**Open note:** {a['note']}", ""]
        if a["printed"]:
            out += [PRINTED, ""]
        out += ["| # | What changes | Words |", "|---|---|---|"]
        for v in a["variations"]:
            out.append(f"| {v.get('id')} | {cell(v.get('picture') or 'only the words')} | {cell(' · '.join(v.get('words') or []))} |")
        out.append("")
    return "\n".join(out)


PRINTED = ("Words are printed into this picture, so the clean picture still carries them. To change a word, edit the "
           "first picture with one change and keep everything else the same. Do not set new type over it.")


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ")


def build(a):
    d = load(a.list)
    root = d["home"]
    out = root / "deliverable"
    out.mkdir(exist_ok=True)
    ready = [r for r in d["briefs"] if r.get("ready")]
    ads = []
    for row in ready:
        link = packed(row, d) if a.no_pack else pack(row, d)
        ads.append(build_ad(row, d, out, link))
        print(f"{row['code']}  {ads[-1]['ad_name']}")
    with (out / "copy.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["brief", "ad_name", "assets", "lane", "swipe", "format", "primary_text", "alt_format", "alt_text"])
        for m in ads:
            w.writerow([m["brief"], m["ad_name"], 1, d.get("lane", "offer"), m["run"], "static", ". ".join(d["offer"]) + ".", "", ""])
    with (out / "drop.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["brief", "ad_name", "asset", "what", "headline", "file"])
        for m in ads:
            for x in m["ads"]:
                w.writerow([m["brief"], m["ad_name"], "asset-01", x["what"], x["headline"], x["file"]])
    (out / "links.json").write_text(json.dumps(d["links"], indent=1) + "\n")
    engine, svc, dest = drive_home(d)
    (out / "HANDOFF.md").write_text(handoff_page(d, ads, dest))
    engine.mirror_tree(str(out), dest, svc)
    (root / "drop.json").write_text(json.dumps(dict({k: d[k] for k in ("brand", "product", "drop", "batch", "title")},
                                                    ads=[m["ad_name"] for m in ads]), indent=1) + "\n")
    (root / "run.json").write_text(json.dumps({"machine": "image-teardown", "brand": d["brand"], "label": d["drop"],
                                               "state": "filed", "ads": len(ads)}, indent=1) + "\n")
    print(f"{len(ads)} ads · https://drive.google.com/drive/folders/{dest}")


CSS = """
:root{--paper:#f3f2ee;--sheet:#fff;--ink:#1b1d22;--soft:#5e626c;--line:#dcdbd4;--gold:#8a6a1e;--tint:#f4ecd8;--flag:#a4400f;--flagbg:#fbeadf;
--head:"Archivo",system-ui,sans-serif;--body:"Source Sans 3",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#15161a;--sheet:#1e2026;--ink:#ecebe6;--soft:#a3a6af;--line:#33353d;--gold:#d9b45b;--tint:#2d2717;--flag:#f0a06c;--flagbg:#35210f;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#15161a;--sheet:#1e2026;--ink:#ecebe6;--soft:#a3a6af;--line:#33353d;--gold:#d9b45b;--tint:#2d2717;--flag:#f0a06c;--flagbg:#35210f;color-scheme:dark}
body{background:var(--paper);color:var(--ink);font:16px/1.5 var(--body);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:32px 64px}
.wrap{max-width:1120px;margin:0 auto;display:grid;gap:32px}
h1,h2,h3{font-family:var(--head);text-wrap:balance;margin:0;line-height:1.15}
h1{font-size:clamp(30px,5vw,44px);font-weight:800;letter-spacing:-.02em}
h2{font-size:24px;font-weight:800}
h3{font-size:18px;font-weight:700}
p{margin:0}
a{color:var(--gold);font-weight:600}
a:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.lead{max-width:62ch;color:var(--soft);font-size:18px}
.top{display:grid;gap:12px}
.jobs{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.job{background:var(--sheet);border:1px solid var(--line);padding:12px 14px;border-radius:6px}
.lab{font:700 12px/1.3 var(--head);letter-spacing:.06em;text-transform:uppercase;color:var(--soft);margin-bottom:4px}
.prod{display:grid;gap:16px}
.prodhead{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;justify-content:space-between;border-bottom:2px solid var(--ink);padding-bottom:8px}
.count{font-variant-numeric:tabular-nums;color:var(--soft)}
.offer{background:var(--tint);padding:10px 14px;border-radius:6px}
.brief{background:var(--sheet);border:1px solid var(--line);border-radius:8px;padding:16px;display:grid;grid-template-columns:minmax(0,260px) minmax(0,130px) minmax(0,1fr);gap:16px;align-items:start}
.brief img{display:block;width:100%;border-radius:4px;border:1px solid var(--line)}
.side{display:grid;gap:12px;min-width:0}
.cap{font-size:13px;color:var(--soft);margin-top:4px}
.words{font-weight:600}
.note{background:var(--flagbg);color:var(--flag);padding:8px 12px;border-radius:6px;font-weight:600}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:15px}
th{font:700 12px var(--head);letter-spacing:.05em;text-transform:uppercase;color:var(--soft);text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
td{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td:first-child{font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--soft)}
.wait{display:flex;flex-wrap:wrap;gap:8px}
.wait span{border:1px dashed var(--line);padding:4px 10px;border-radius:6px;color:var(--soft);font-variant-numeric:tabular-nums}
@media (max-width:820px){.brief{grid-template-columns:minmax(0,1fr) minmax(0,110px)}.side{grid-column:1/-1}}
"""


def small(src, dest, width):
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im.thumbnail((width, width * 2))
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(dest.read_bytes()).decode()


def e(s):
    return html.escape(str(s), quote=True)


def manifests(d):
    return {m["run"]: m for m in (json.loads(f.read_text()) for f in (d["home"] / "deliverable").glob("*/manifest.json"))}


def page(a):
    lists = [load(f) for f in a.lists]
    pics = Path(a.pics)
    made = sum(len(manifests(d)) for d in lists)
    total = sum(len(d["briefs"]) for d in lists)
    out = [f"<title>{e(a.title)}</title>", '<meta name="claude:viewport-fit-sides" content="cover">',
           '<link rel="preconnect" href="https://fonts.googleapis.com">',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=Source+Sans+3:wght@400;600&display=swap">',
           f"<style>{CSS}</style>", '<div class="wrap"><header class="top">', f"<h1>{e(a.title)}</h1>",
           f'<p class="lead">{made} of {total} briefs ready. Each one has its final picture, its swipe, the words, the offer and five variations to make.</p>',
           '<div class="jobs"><div class="job"><div class="lab">editor</div>Runs the variation work with the designer.</div>'
           '<div class="job"><div class="lab">The chain</div>Makes every variation from the prompts in the folder.</div>'
           '<div class="job"><div class="lab">The designer</div>Approves each one and saves it to returned/.</div></div></header>']
    md = [f"# {a.title}", "", f"{made} of {total} briefs ready. editor runs the variation work with the designer. The chain "
          "makes the variations and the designer approves them.", ""]
    for d in lists:
        have = manifests(d)
        out += ['<section class="prod"><div class="prodhead">', f"<h2>{e(d['title'])}</h2>",
                f'<span class="count">{len(have)} of {len(d["briefs"])} ready</span></div>',
                f'<p class="offer"><strong>Offer:</strong> {e(" · ".join(d["offer"]))}. {e(d["window"])}.</p>']
        md += [f"## {d['title']}", "", f"{len(have)} of {len(d['briefs'])} ready. Offer: {' · '.join(d['offer'])}. {d['window']}.", ""]
        if d.get("general_note"):
            out.append(f'<p class="note">{e(d["general_note"])}</p>')
            md += [f"Every brief: {d['general_note']}", ""]
        if d.get("folder"):
            out.append(f'<p><a href="{e(d["folder"])}">Open the Drive folder</a></p>')
            md += [f"Drive folder: {d['folder']}", ""]
        for row in d["briefs"]:
            m = have.get(row["run"])
            if not m:
                continue
            pic = f"pics/{d['drop']}-{row['code']}.jpg"
            swipe = f"pics/{d['drop']}-{row['code']}-swipe.jpg"
            pic = small(WS / m["picture"], pics / Path(pic).name, 560)
            sw = swipe_of(row, d)
            if sw:
                swipe = small(sw, pics / Path(swipe).name, 280)
            out += ['<article class="brief">',
                    f'<div><img src="{pic}" alt="Final picture, brief {e(row["code"])}" loading="lazy"><p class="cap">Final picture</p></div>',
                    f'<div><img src="{swipe}" alt="Swipe, brief {e(row["code"])}" loading="lazy"><p class="cap">Swipe</p></div>' if sw else "<div></div>",
                    f'<div class="side"><h3>Brief {e(row["code"])} · {e(m["brief"])}</h3>',
                    f'<div><div class="lab">Words</div><p class="words">{e(" · ".join(m["words"]))}</p></div>']
            if m["note"]:
                out.append(f'<p class="note">{e(m["note"])}</p>')
            if m["printed"]:
                out.append(f'<p class="cap">{e(PRINTED)}</p>')
            out += ['<div class="tbl"><table><thead><tr><th>#</th><th>What changes</th><th>Words</th></tr></thead><tbody>']
            for v in m["variations"]:
                out.append(f"<tr><td>{e(v.get('id'))}</td><td>{e(v.get('picture') or 'only the words')}</td><td>{e(' · '.join(v.get('words') or []))}</td></tr>")
            out += ["</tbody></table></div>"]
            if m["pack"]:
                out.append(f'<p><a href="{e(m["pack"])}">Open this brief\'s variation folder</a></p>')
            out += ["</div></article>"]
            md += [f"### Brief {row['code']} · {m['brief']}", "", f"Words: {' · '.join(m['words'])}", ""]
            if m["note"]:
                md += [f"Open note: {m['note']}", ""]
            if m["printed"]:
                md += [PRINTED, ""]
            md += ["| # | What changes | Words |", "|---|---|---|"]
            md += [f"| {v.get('id')} | {cell(v.get('picture') or 'only the words')} | {cell(' · '.join(v.get('words') or []))} |" for v in m["variations"]]
            md += ["", f"Variation folder: {m['pack']}", ""]
        rest = [r for r in d["briefs"] if r["run"] not in have]
        if rest:
            out += ['<div><div class="lab">Waiting</div><div class="wait">'] + [f"<span>{e(r['code'])}</span>" for r in rest] + ["</div></div>"]
            md += ["Waiting: " + ", ".join(r["code"] for r in rest), ""]
        out.append("</section>")
    out.append("</div>")
    Path(a.html).write_text("\n".join(out))
    Path(a.md).write_text("\n".join(md))
    print(a.html)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("list")
    b.add_argument("--no-pack", action="store_true", help="keep the variation folders already packed")
    b.set_defaults(go=build)
    p = sub.add_parser("page")
    p.add_argument("lists", nargs="+")
    p.add_argument("--title", required=True)
    p.add_argument("--html", required=True)
    p.add_argument("--md", required=True)
    p.add_argument("--pics", required=True)
    p.set_defaults(go=page)
    a = ap.parse_args()
    a.go(a)


if __name__ == "__main__":
    main()
