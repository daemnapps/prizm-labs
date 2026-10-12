#!/usr/bin/env python3
"""The mix-and-match board — every section of a winner, its format versions and
its Distinct Six side by side, from real frames.

the owner, 2026-10-08: "we'll have all the frames and sections. We can actually see
how it would mix and match … I want to actually visually see this now."

    python3 components/distinct-six/board.py <winner run> [--formats <run> …] [--six <versions.json>] --out <file.html>

For every run: the doctrine stage's section map (stages/1c-doctrine.md), one
frame per section pulled from the run's own video at the section's midpoint
(ffmpeg, local), and the words spoken inside it (transcript.json). Distinct Six
versions come in as words (nothing is produced yet). Writes one self-contained
HTML page (frames embedded). Never calls Meta or a model.
"""
import argparse
import base64
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.argv_backup = sys.argv
sys.argv = ["x"]
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402
sys.argv = sys.argv_backup

C = R.COLOR
NAME = {x["id"]: x["name"] for x in R.SECTIONS}
ORDER = [x["id"] for x in R.SECTIONS]
e = html.escape


CHAIN_RUNS = ROOT / "tools" / "video-teardown" / "machine" / "runs"
_TOKEN = [None]


def playable(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True, timeout=20)
        return float((r.stdout or "0").strip() or 0) > 0.5
    except Exception:  # noqa: BLE001
        return False


def video_of(run, meta):
    """Where to read a run's video: its own copy, the chain's working copy, the
    recorded path — or, for a Drive file this Mac hasn't downloaded, the cloud
    (Drive API link, read by ffmpeg a few seconds at a time; nothing downloaded)."""
    # Drive first (the owner, 2026-10-08: "we should always be pulling from the Google
    # Drive because that's literally going to have the most up-to-date content").
    rec = Path(meta.get("video") or "")
    try:
        fid = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(rec)],
                             capture_output=True, text=True).stdout.strip() if "CloudStorage" in str(rec) else ""
    except Exception:  # noqa: BLE001
        fid = ""
    if not fid:
        for p in (run / "source.mp4", CHAIN_RUNS / run.name / "source.mp4", rec):
            if str(p) and p.exists() and playable(p):
                return str(p), []
        return None, []
    if _TOKEN[0] is None:
        sys.path.insert(0, str(ROOT / "components" / "gdrive-creator"))
        import daemn_keys
        from gdrive_creator import engine as G
        import google.auth.transport.requests as TR
        G.configure(key_lookup=daemn_keys.key)
        c = G._creds()
        c.refresh(TR.Request())
        _TOKEN[0] = c.token
    return (f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media&supportsAllDrives=true",
            ["-headers", f"Authorization: Bearer {_TOKEN[0]}\r\n"])


def frame(video, t, tmp, extra=()):
    f = Path(tmp) / f"f{abs(hash((str(video), round(t, 2))))}.jpg"
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", *extra, "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=270:-2", "-q:v", "6", str(f)], capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"  slow frame skipped at {t:.1f}s", file=sys.stderr)
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def words(tr, a, b):
    got = [x["text"] for x in tr if a <= (x.get("start", 0) + x.get("end", 0)) / 2 < b]
    t = re.sub(r"\s*\(corrected:.*?\)", "", " ".join(got))
    return (t[:170] + "…") if len(t) > 170 else t


def source(run, label, tmp):
    run = ROOT / run if not Path(run).is_absolute() else Path(run)
    meta = json.loads((run / "run.json").read_text())
    smap = R.section_map((run / "stages" / "1c-doctrine.md").read_text())
    tr = json.loads((run / "transcript.json").read_text()) if (run / "transcript.json").exists() else []
    video, extra = video_of(run, meta)
    cells = []
    for s, a, b in smap:
        cells.append({"section": s, "start": a, "end": b, "img": frame(video, (a + b) / 2, tmp, extra) if video else "",
                      "says": words(tr, a, b)})
    return {"label": label, "run": run.name, "kind": "video", "cells": cells,
            "length": max((c["end"] for c in cells), default=0)}


def six(path):
    d = json.loads(Path(path).read_text())
    out = []
    for i, v in enumerate(d["versions"], 1):
        t, cells = 0.0, []
        for b in v["beats"]:
            s = float(b.get("seconds") or 1)
            cells.append({"section": b["section"], "start": t, "end": t + s, "img": "", "says": b.get("says", ""),
                          "shows": b.get("shows", "")})
            t += s
        p = v["piece"]
        out.append({"label": f"V{i} · {v['title']}", "run": "", "kind": "words", "cells": cells, "length": t,
                    "sub": f"{p['awareness']} · {p['format']} · {p['setting']} · {p['style_id']}"})
    return out


def page(winner, formats, versions, out):
    srcs = [winner] + formats + versions
    present = [s for s in ORDER if any(c["section"] == s for x in srcs for c in x["cells"])]
    # winner's order first, then any other section
    wo = list(dict.fromkeys(c["section"] for c in winner["cells"]))
    rows = wo + [s for s in present if s not in wo]
    legend = "".join(f'<span><i style="background:{C[s]}"></i>{e(NAME[s])}</span>' for s in rows)

    def strip(x):
        tot = x["length"] or 1
        segs = "".join(
            f'<div class="seg" style="flex:{max(c["end"] - c["start"], 0.6) / tot:.4f};--c:{C.get(c["section"], "#999")}">'
            + (f'<img src="{c["img"]}" alt="">' if c["img"] else "")
            + f'<span>{e(NAME.get(c["section"], c["section"]))}</span></div>' for c in x["cells"])
        return f'<div class="strip">{segs}</div>'

    strips = "".join(
        f'<div class="srow"><div class="slab"><b>{e(x["label"])}</b><small>{e(x.get("sub") or x["run"])} · {x["length"]:.0f}s</small></div>{strip(x)}</div>'
        for x in srcs)
    head = "".join(f'<th>{e(x["label"])}</th>' for x in srcs)
    body = ""
    for s in rows:
        tds = ""
        for k, x in enumerate(srcs):
            hit = [c for c in x["cells"] if c["section"] == s]
            if not hit:
                tds += "<td class='none'>—</td>"
                continue
            c = hit[0]
            more = f' <small>+{len(hit) - 1} more</small>' if len(hit) > 1 else ""
            pic = f'<img src="{c["img"]}" alt="">' if c["img"] else f'<div class="wordsonly">{e(c.get("shows", ""))}</div>'
            tds += (f'<td><button class="cell" data-row="{e(s)}" data-col="{k}" aria-pressed="{str(k == 0).lower()}">{pic}'
                    f'<span class="says">{e(c["says"])}</span><span class="t">{c["end"] - c["start"]:.0f}s{more}</span></button></td>')
        body += f'<tr><th class="rh" style="--c:{C[s]}">{e(NAME[s])}</th>{tds}</tr>'
    data = json.dumps({s: {str(k): {"img": ([c for c in x["cells"] if c["section"] == s] or [{}])[0].get("img", ""),
                                     "says": ([c for c in x["cells"] if c["section"] == s] or [{}])[0].get("says", ""),
                                     "src": x["label"]}
                           for k, x in enumerate(srcs)} for s in rows})
    doc = f'''<title>Mix and Match Board</title>
<style>
:root{{--bg:#fbf7f0;--card:#fff;--ink:#1f2333;--soft:#5f6478;--line:#e6e0d4;--pick:#2f6fd6}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;--pick:#6c9cf0;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;--pick:#6c9cf0;color-scheme:dark}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif;margin:0}}
.wrap{{max-width:1400px;margin:0 auto;padding-inline:16px;padding-block:22px 64px;display:grid;gap:18px}}
h1,h2{{margin:0;line-height:1.15}}h1{{font-size:1.8rem}}h2{{font-size:1.2rem}}.soft{{color:var(--soft)}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.82rem}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:grid;gap:10px;min-width:0}}
.srow{{display:grid;grid-template-columns:200px 1fr;gap:10px;align-items:center}}.slab small{{display:block;color:var(--soft);font-size:.74rem}}
.strip{{display:flex;gap:2px;height:96px;border-radius:8px;overflow:hidden;min-width:0}}
.seg{{position:relative;background:var(--c);border-top:5px solid var(--c);min-width:6px;overflow:hidden}}.seg img{{width:100%;height:100%;object-fit:cover;display:block}}
.seg span{{position:absolute;left:3px;bottom:3px;font-size:.62rem;background:rgba(0,0,0,.6);color:#fff;padding:1px 4px;border-radius:3px;white-space:nowrap}}
.gw{{overflow-x:auto}}table{{border-collapse:separate;border-spacing:6px}}th{{font-size:.8rem;text-align:left;vertical-align:bottom;min-width:150px}}
th.rh{{border-left:6px solid var(--c);padding-left:8px;min-width:120px;vertical-align:middle}}td{{vertical-align:top}}td.none{{color:var(--soft);text-align:center}}
.cell{{all:unset;cursor:pointer;display:grid;gap:4px;width:160px;background:var(--bg);border:2px solid transparent;border-radius:10px;padding:5px}}
.cell[aria-pressed="true"]{{border-color:var(--pick);box-shadow:0 0 0 2px color-mix(in srgb,var(--pick) 30%,transparent)}}.cell:focus-visible{{outline:2px solid var(--pick)}}
.cell img{{width:100%;aspect-ratio:9/12;object-fit:cover;border-radius:6px}}.wordsonly{{font-size:.72rem;color:var(--soft);aspect-ratio:9/12;overflow:hidden;background:var(--card);border-radius:6px;padding:6px}}
.says{{font-size:.74rem}}.t{{font-size:.7rem;color:var(--soft)}}
#mine .strip{{height:150px}}#mine .seg span{{font-size:.7rem}}
@media (max-width:640px){{.srow{{grid-template-columns:1fr}}}}
</style>
<div class="wrap">
<header style="display:grid;gap:6px"><h1>Mix and Match Board</h1>
<p class="soft">The winner, its format versions and its Distinct Six, laid out section by section from real frames. Click one cell in each row to build a new ad at the top. Frames come from each video at the middle of the section; words are what's said in it.</p>
<div class="legend">{legend}</div></header>
<section class="box" id="mine"><h2>Your mix</h2><div class="srow"><div class="slab"><b>New ad</b><small id="mine-from"></small></div><div class="strip" id="mine-strip"></div></div><ol id="mine-words" class="soft" style="margin:0;padding-left:18px;font-size:.85rem"></ol></section>
<section class="box"><h2>Every version, section by section</h2>{strips}</section>
<section class="box"><h2>Pick one per section</h2><div class="gw"><table><tr><th></th>{head}</tr>{body}</table></div></section>
</div>
<script>
var D={data}, ROWS={json.dumps(rows)}, COL={json.dumps({s: C[s] for s in rows})}, NAMES={json.dumps({s: NAME[s] for s in rows})};
var pick={{}}; ROWS.forEach(function(r){{pick[r]=D[r]["0"]&&D[r]["0"].src?"0":Object.keys(D[r]).find(function(k){{return D[r][k].src&&(D[r][k].img||D[r][k].says)}})}});
function draw(){{var s=document.getElementById("mine-strip"),w=document.getElementById("mine-words"),from={{}};s.innerHTML="";w.innerHTML="";
 ROWS.forEach(function(r){{var k=pick[r];if(k==null)return;var c=D[r][k];if(!c||(!c.img&&!c.says))return;from[c.src]=1;
  var d=document.createElement("div");d.className="seg";d.style.flex="1";d.style.setProperty("--c",COL[r]);
  if(c.img){{var i=document.createElement("img");i.src=c.img;d.appendChild(i)}}var sp=document.createElement("span");sp.textContent=NAMES[r];d.appendChild(sp);s.appendChild(d);
  var li=document.createElement("li");li.innerHTML="<b>"+NAMES[r]+"</b> ("+c.src+"): ";li.appendChild(document.createTextNode(c.says||""));w.appendChild(li)}});
 document.getElementById("mine-from").textContent="from "+Object.keys(from).length+" source(s)"}}
document.querySelectorAll(".cell").forEach(function(b){{b.addEventListener("click",function(){{var r=b.dataset.row;pick[r]=b.dataset.col;
 document.querySelectorAll('.cell[data-row="'+r+'"]').forEach(function(x){{x.setAttribute("aria-pressed",String(x===b))}});draw()}})}});
draw();
</script>'''
    Path(out).write_text(doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("winner")
    ap.add_argument("--formats", nargs="*", default=[])
    ap.add_argument("--six")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        w = source(a.winner, "Winner · " + Path(a.winner).name.replace("top1-brand-a-01-", ""), tmp)
        fs = [source(r, f"Format {i} · {Path(r).name.split('-x-')[-1]}", tmp) for i, r in enumerate(a.formats, 1)]
    vs = six(a.six) if a.six else []
    page(w, fs, vs, a.out)
    print(f"board: winner {len(w['cells'])} sections · {len(fs)} formats · {len(vs)} versions → {a.out}")


if __name__ == "__main__":
    main()
