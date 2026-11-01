#!/usr/bin/env python3
"""The production briefs for a winner's re-cuts, as one page.

    python3 components/distinct-six/brief_page.py brand-a brand-a-grandma-winner --out <file.html>

Each brief drawn as a strip: winner footage (its real frame), a library clip (its
real frame, read from Drive), or a NEW piece (a dashed card saying what to make).
Frames are read from Drive in the cloud; nothing is downloaded; never Meta.
"""
import argparse
import html
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.argv_saved, sys.argv = sys.argv, ["x"]
sys.path.insert(0, str(HERE))
import board as B  # noqa: E402
sys.argv = sys.argv_saved
e = html.escape



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def drive_url(fid):
    if B._TOKEN[0] is None:
        sys.path.insert(0, str(ROOT / "components" / "gdrive-creator"))
        from gdrive_creator import engine as G
        import google.auth.transport.requests as TR
        G.configure(key_lookup=_shared_keys().lookup)
        c = G._creds()
        c.refresh(TR.Request())
        B._TOKEN[0] = c.token
    return (f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media&supportsAllDrives=true",
            ["-headers", f"Authorization: Bearer {B._TOKEN[0]}\r\n"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("winner")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run = ROOT / "runs" / "distinct-six" / a.brand / a.winner
    briefs = [json.loads(f.read_text()) for f in sorted((run / "briefs").glob("*.json"))]
    order = [c["id"] for c in json.loads((run / "recipes.json").read_text())["cuts"]]
    briefs.sort(key=lambda b: order.index(b["cut"]) if b["cut"] in order else 99)
    clips = {}
    for f in (ROOT / "runs" / "distinct-six" / a.brand / "clip-library").glob("*.json"):
        clips.update({c["clip"]: c for c in json.loads(f.read_text())["clips"]})
    db = sqlite3.connect(os.environ.get("CREATIVE_INDEX_DB") or ROOT / "records" / "asset-ledger" / "ledger.db")
    beats = {n: (s, st, d) for n, s, st, d in db.execute(
        "SELECT n, section, start_s, seconds FROM beat WHERE creative_id=?", (f"creative_winner_{a.brand}_{a.winner}",))}
    wrun = ROOT / "runs" / "video-teardown" / a.brand / a.winner
    wvid, wextra = B.video_of(wrun, json.loads((wrun / "run.json").read_text()))
    img = {}
    with tempfile.TemporaryDirectory() as tmp:
        for n, (s, st, d) in beats.items():
            img[f"w{n}"] = B.frame(wvid, st + d / 2, tmp, wextra) if wvid else ""
        used = {str(p.get("ref", "")).split(" ")[0] for b in briefs for p in b.get("plan", []) if p.get("source") == "clip"}
        for c in used:
            if c in clips and clips[c].get("drive_id") and clips[c]["kind"] == "video":
                url, ex = drive_url(clips[c]["drive_id"])
                img[c] = B.frame(url, 2.0, tmp, ex)

    def ref_img(p):
        if p.get("source") == "winner":
            import re
            m = re.search(r"\d+", str(p.get("ref", "")))
            return img.get(f"w{m.group(0)}") if m else ""
        if p.get("source") == "clip":
            return img.get(str(p.get("ref", "")).split(" ")[0], "")
        return ""

    tot = {"winner": 0, "clip": 0, "new": 0}
    cards = ""
    for b in briefs:
        plan = b.get("plan", [])
        for p in plan:
            tot[p.get("source", "new")] = tot.get(p.get("source", "new"), 0) + 1
        T = sum(max(float(p.get("seconds") or 1), 1) for p in plan) or 1
        segs = ""
        for p in plan:
            src, w = p.get("source", "new"), max(float(p.get("seconds") or 1), 1) / T
            im = ref_img(p)
            col = B.C.get(p.get("section"), "#999")
            inner = f'<img src="{im}" alt="">' if im else f'<div class="newc">NEW<br>{e(str(p.get("ref", ""))[:40])}</div>'
            segs += (f'<div class="seg {src}" style="flex:{w:.4f};--c:{col}" title="{e(p.get("says", ""))}">{inner}'
                     f'<span>{e(B.NAME.get(p.get("section"), p.get("section", "")))}</span></div>')
        rows = "".join(f'<tr><td><span class="src {e(p.get("source", ""))}">{e(p.get("source", ""))}</span></td>'
                       f'<td><i class="sw" style="background:{B.C.get(p.get("section"), "#999")}"></i>{e(B.NAME.get(p.get("section"), p.get("section", "")))}</td>'
                       f'<td class="mono">{e(str(p.get("ref", ""))[:40])}</td><td>{e(str(p.get("seconds")))}s</td>'
                       f'<td>{e(p.get("says", ""))}<div class="soft">{e(p.get("shows", ""))}</div></td></tr>' for p in plan)
        brk = "".join(f'<li><b>beat {e(str(x.get("at_beat")))}:</b> {e(x.get("problem", ""))} <span class="fix">→ {e(x.get("fix", ""))}</span></li>'
                      for x in b.get("breaks", []))
        new = "".join(f'<li><b>{e(n.get("name", ""))}</b> ({e(n.get("kind", ""))}, for {e(n.get("for_section", ""))}): {e(n.get("make", ""))}'
                      f'<div class="soft">Why not reused: {e(n.get("why_not_reused", ""))}</div></li>' for n in b.get("new_pieces", []))
        ck = "".join(f'<li><b>{e(k.replace("_", " "))}:</b> {e(str(v))}</li>' for k, v in (b.get("checklist") or {}).items())
        v = b.get("verdict", "?")
        cards += f'''<article class="brief" id="{e(b["cut"])}"><div class="bh"><h2>{e(b["name"])}</h2>
<span class="pill {e(v)}">{e(v)}</span><span class="soft">{e(str(b.get("length_s", "")))}s · {sum(p.get("source") == "winner" for p in plan)} winner · {sum(p.get("source") == "clip" for p in plan)} library · {len(b.get("new_pieces", []))} new</span></div>
<p class="vw">{e(b.get("verdict_why", ""))}</p><div class="strip">{segs}</div>
<details><summary>{len(b.get("breaks", []))} break(s) found in the plain re-cut</summary><ul>{brk}</ul></details>
<details open><summary>The plan, beat by beat</summary><div class="tw"><table>{rows}</table></div></details>
{f'<details open><summary>{len(b.get("new_pieces", []))} new piece(s) to make</summary><ul>{new}</ul></details>' if new else ''}
<details><summary>Checklist</summary><ul>{ck}</ul></details></article>'''
    verdicts = {}
    for b in briefs:
        verdicts[b.get("verdict", "?")] = verdicts.get(b.get("verdict", "?"), 0) + 1
    nav = "".join(f'<a href="#{e(b["cut"])}" class="pill {e(b.get("verdict", ""))}">{e(b["name"])}</a>' for b in briefs)
    legend = "".join(f'<span><i style="background:{B.C[x["id"]]}"></i>{e(x["name"])}</span>' for x in B.R.SECTIONS)
    doc = f'''<title>Re-cut Production Briefs</title>
<style>
:root{{--bg:#fbf7f0;--card:#fff;--ink:#1f2333;--soft:#5f6478;--line:#e6e0d4;--w:#2a9d6f;--c:#2f6fd6;--n:#e0663a;--bad:#cf3f3f}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;color-scheme:dark}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif;margin:0}}
.wrap{{max-width:1200px;margin:0 auto;padding-inline:16px;padding-block:22px 64px;display:grid;gap:14px}}
h1,h2{{margin:0;line-height:1.15}}h1{{font-size:1.9rem}}h2{{font-size:1.15rem}}.soft{{color:var(--soft);font-size:.85rem}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}.tile{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;display:grid}}
.tile b{{font-size:1.8rem}}.tile.w b{{color:var(--w)}}.tile.c b{{color:var(--c)}}.tile.n b{{color:var(--n)}}
.nav{{display:flex;flex-wrap:wrap;gap:6px}}.nav a{{text-decoration:none}}
.pill{{font-size:.75rem;padding:2px 9px;border-radius:999px;background:var(--line);color:var(--ink)}}
.pill.ready{{background:color-mix(in srgb,var(--w) 25%,transparent)}}.pill.needs-new-pieces{{background:color-mix(in srgb,var(--n) 25%,transparent)}}.pill.drop{{background:color-mix(in srgb,var(--bad) 30%,transparent)}}
.legend{{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:.78rem}}.legend i{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:4px;vertical-align:-1px}}
.brief{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:grid;gap:8px;min-width:0}}
.bh{{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}}.vw{{margin:0;font-size:.92rem}}
.strip{{display:flex;gap:3px;height:120px;border-radius:8px;overflow:hidden;min-width:0}}
.seg{{position:relative;border-top:6px solid var(--c);min-width:10px;overflow:hidden;background:var(--bg)}}.seg img{{width:100%;height:100%;object-fit:cover;display:block}}
.seg.new{{outline:2px dashed var(--n);outline-offset:-2px}}.seg.clip{{box-shadow:inset 0 -5px 0 var(--c)}}
.newc{{font-size:.65rem;color:var(--n);font-weight:700;padding:6px;line-height:1.2}}
.seg span{{position:absolute;left:3px;bottom:7px;font-size:.6rem;background:rgba(0,0,0,.6);color:#fff;padding:1px 4px;border-radius:3px;white-space:nowrap}}
details summary{{cursor:pointer;font-weight:600;font-size:.9rem}}ul{{margin:6px 0;padding-left:20px;display:grid;gap:4px;font-size:.88rem}}.fix{{color:var(--w)}}
.tw{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.84rem}}td{{border-bottom:1px solid var(--line);padding:5px 8px;vertical-align:top}}
.src{{font-size:.7rem;font-weight:700;padding:1px 7px;border-radius:5px;color:#fff}}.src.winner{{background:var(--w)}}.src.clip{{background:var(--c)}}.src.new{{background:var(--n)}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}}.mono{{font-family:ui-monospace,monospace;font-size:.75rem}}
</style>
<div class="wrap">
<header style="display:grid;gap:8px"><h1>Re-cut Production Briefs</h1>
<p class="soft">{e(a.brand)} · <b>{e(a.winner)}</b> · each re-cut read like a viewer and rebuilt so it actually reads. Reuse first: the winner's own footage, then clips we already made, and only then something new. Strip: <b style="color:var(--w)">winner</b> · <b style="color:var(--c)">library clip</b> · <b style="color:var(--n)">dashed = new to make</b>.</p>
<div class="tiles"><div class="tile"><b>{len(briefs)}</b><span>briefs · {", ".join(f"{v} {k}" for k, v in verdicts.items())}</span></div>
<div class="tile w"><b>{tot.get("winner", 0)}</b><span>beats from the winner itself</span></div>
<div class="tile c"><b>{tot.get("clip", 0)}</b><span>beats from clips we already made</span></div>
<div class="tile n"><b>{tot.get("new", 0)}</b><span>beats that need something new</span></div></div>
<div class="nav">{nav}</div><div class="legend">{legend}</div></header>
{cards}
</div>'''
    Path(a.out).write_text(doc)
    print(f"{len(briefs)} briefs → {a.out} · reuse: {tot}")


if __name__ == "__main__":
    main()
