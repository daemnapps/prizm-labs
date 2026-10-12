#!/usr/bin/env python3
"""Tier 1 — re-cut the winner's own footage by formula (formulas.json).

the owner, 2026-10-08: "you're supposed to just do it on the actual winner itself.
It's literally just rearranging the existing content first."

    python3 components/distinct-six/recut.py brand-a brand-a-grandma-winner [--page <file.html>]

Reads the winner's beats from the Creative Index (section, in/out, words) and the
doctrine frameworks, applies hook-from-inside · framework-order · cut-down, and
writes runs/distinct-six/<brand>/<winner>/recipes.json — every cut as an edit
list of source in/out times (render = ffmpeg trim + concat of the winner itself).
With --page, draws every cut from the winner's real frames (read from Drive).
Never calls Meta or a model.
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
LEDGER = Path(os.environ.get("CREATIVE_INDEX_DB") or ROOT / "records" / "asset-ledger" / "ledger.db")
F = json.loads((HERE / "formulas.json").read_text())
FW = json.loads((ROOT / "components" / "marketing-doctrine" / "ad-frameworks.json").read_text())
FW = FW.get("frameworks") or [v for v in FW.values() if isinstance(v, list)][0]


def beats_of(brand, winner):
    db = sqlite3.connect(LEDGER)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT n, section, start_s, seconds, says, frame_ref FROM beat WHERE creative_id=? ORDER BY n",
                      (f"creative_winner_{brand}_{winner}",)).fetchall()
    if not rows:
        sys.exit(f"no beats for {winner} in the Creative Index — run asset-ledger/db/creative.py")
    return [dict(r) for r in rows]


def cut(cid, formula, name, picked, extra=None):
    segs = [(b["start_s"], b["start_s"] + b["seconds"]) for b in picked]
    return {"id": cid, "formula": formula, "name": name, "beats": [b["n"] for b in picked],
            "sections": [b["section"] for b in picked], "segments": segs,
            "length_s": round(sum(b - a for a, b in segs), 1), "opens_with": picked[0]["says"][:140] if picked else "",
            **(extra or {})}


def recipes(beats):
    out = []
    order = [b["section"] for b in beats]
    # hook from inside
    for b in beats[1:]:
        if b["section"] in F["hook_sections"]:
            rest = [x for x in beats if x["n"] != b["n"]]
            out.append(cut(f"hook-from-{b['n']}", "hook-from-inside", f"Open on beat {b['n']} ({b['section']})", [b] + rest))
    # framework order
    have = {b["section"] for b in beats}
    for fw in FW:
        seq = [s["id"] for s in fw["sections"]]
        shared = [s for s in dict.fromkeys(seq) if s in have]
        if len(shared) < F["framework_min_shared"]:
            continue
        picked = [b for s in shared for b in beats if b["section"] == s]
        if [b["n"] for b in picked] == [b["n"] for b in beats]:
            continue
        aw = fw.get("awareness") or {}
        out.append(cut(f"order-{fw['id']}", "framework-order", f"{fw['name']} order", picked,
                       {"framework": fw["id"], "entry": aw.get("entry"), "exit": aw.get("exit"),
                        "dropped": [b["section"] for b in beats if b not in picked]}))
    # cut-downs
    keep = F["cutdown_keep"]
    proofs = [b for b in beats if b["section"] == "proof"]
    head = [b for b in beats if b["section"] == "hook"][:1]
    tail = [b for b in beats if b["section"] in ("offer", "call-to-action")]
    if proofs and head:
        short = sorted(proofs, key=lambda b: b["seconds"])[0]
        out.append(cut("cut-15", "cut-down", "~15s cut-down", head + [short] + tail))
        mid = [b for b in beats if b["section"] in ("proof", "failed-solutions", "transformation")]
        picked = head + [b for b in mid] + tail
        while sum(b["seconds"] for b in picked) > 36 and len(picked) > 3:
            picked.remove(max(picked[1:-len(tail)] or picked, key=lambda b: b["seconds"]))
        out.append(cut("cut-30", "cut-down", "~30s cut-down", sorted(picked, key=lambda b: (b not in head, b["n"]))))
    return out


def page(brand, winner, beats, cuts, outfile):
    sys.argv_saved = sys.argv
    sys.argv = ["x"]
    sys.path.insert(0, str(HERE))
    import board as B  # frames from Drive, section colours
    sys.argv = sys.argv_saved
    run = ROOT / "runs" / "video-teardown" / brand / winner
    meta = json.loads((run / "run.json").read_text())
    video, extra = B.video_of(run, meta)
    with tempfile.TemporaryDirectory() as tmp:
        img = {b["n"]: B.frame(video, b["start_s"] + b["seconds"] / 2, tmp, extra) if video else "" for b in beats}
    e = html.escape
    C, NAME = B.C, B.NAME
    by_n = {b["n"]: b for b in beats}

    def strip(ns, h=110):
        tot = sum(by_n[n]["seconds"] for n in ns) or 1
        return '<div class="strip" style="height:%dpx">' % h + "".join(
            f'<div class="seg" style="flex:{by_n[n]["seconds"] / tot:.4f};--c:{C[by_n[n]["section"]]}" title="{e(by_n[n]["says"])}">'
            f'<img src="{img[n]}" alt=""><span>{n} · {e(NAME[by_n[n]["section"]])}</span></div>' for n in ns) + "</div>"

    tiers = "".join(
        f'<div class="tier t{t["tier"]}"><b>Tier {t["tier"]} · {e(t["name"])}</b><span>{e(t["what"])}</span>'
        f'<em>{e(t["meta"])}</em><small>{" · ".join(e(f["name"]) for f in t["formulas"])}</small></div>' for t in F["tiers"])
    groups = ""
    for fid, title in (("hook-from-inside", "Hook from inside"), ("framework-order", "Framework order"), ("cut-down", "Cut-downs")):
        f = next(x for t in F["tiers"] for x in t["formulas"] if x["id"] == fid)
        rows = "".join(
            f'<div class="cut"><div class="cl"><b>{e(c["name"])}</b><small>{c["length_s"]:.0f}s'
            + (f' · enters {e(c["entry"])}' if c.get("entry") else "")
            + (f' · cuts {", ".join(e(x) for x in c["dropped"])}' if c.get("dropped") else "")
            + f'</small><span class="op">“{e(c["opens_with"][:110])}”</span></div>{strip(c["beats"])}</div>'
            for c in cuts if c["formula"] == fid)
        groups += f'<section class="box"><h2>{title}</h2><p class="soft">{e(f["how"])} Tests: {e(f["tests"])}.</p>{rows}</section>'
    legend = "".join(f'<span><i style="background:{C[s]}"></i>{e(NAME[s])}</span>' for s in dict.fromkeys(b["section"] for b in beats))
    doc = f'''<title>Winner Re-cuts</title>
<style>
:root{{--bg:#fbf7f0;--card:#fff;--ink:#1f2333;--soft:#5f6478;--line:#e6e0d4;--t1:#2a9d6f;--t2:#3aa3b8;--t3:#2f6fd6;--t4:#a35bd1;--t5:#e0663a}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;color-scheme:dark}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif;margin:0}}
.wrap{{max-width:1200px;margin:0 auto;padding-inline:16px;padding-block:22px 64px;display:grid;gap:16px}}
h1,h2{{margin:0;line-height:1.15}}h1{{font-size:1.9rem}}h2{{font-size:1.2rem}}.soft{{color:var(--soft);margin:0}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:grid;gap:10px;min-width:0}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.82rem}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
.tiers{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}}
.tier{{border-radius:12px;padding:10px;display:grid;gap:4px;align-content:start;background:var(--bg);border-top:6px solid var(--tc)}}
.tier.t1{{--tc:var(--t1)}}.tier.t2{{--tc:var(--t2)}}.tier.t3{{--tc:var(--t3)}}.tier.t4{{--tc:var(--t4)}}.tier.t5{{--tc:var(--t5)}}
.tier span{{font-size:.85rem}}.tier em{{font-size:.78rem;color:var(--soft)}}.tier small{{font-size:.74rem;color:var(--soft)}}
.cut{{display:grid;grid-template-columns:260px 1fr;gap:12px;align-items:center;padding-block:6px;border-bottom:1px dashed var(--line)}}
.cl{{display:grid;gap:2px;min-width:0}}.cl small{{color:var(--soft)}}.op{{font-size:.8rem;font-style:italic}}
.strip{{display:flex;gap:2px;border-radius:8px;overflow:hidden;min-width:0}}
.seg{{position:relative;background:var(--c);border-top:5px solid var(--c);min-width:8px;overflow:hidden}}.seg img{{width:100%;height:100%;object-fit:cover;display:block}}
.seg span{{position:absolute;left:3px;bottom:3px;font-size:.62rem;background:rgba(0,0,0,.6);color:#fff;padding:1px 4px;border-radius:3px;white-space:nowrap}}
@media (max-width:760px){{.tiers{{grid-template-columns:1fr 1fr}}.cut{{grid-template-columns:1fr}}}}
</style>
<div class="wrap">
<header style="display:grid;gap:6px"><h1>Winner Re-cuts</h1>
<p class="soft">{e(brand)} · <b>{e(winner)}</b> · every variation formula, closest to the winner first. Tier 1 below is the winner's own footage, rearranged. Every frame is real and every cut is an edit list ready to render.</p></header>
<section class="box"><h2>The five tiers of variation</h2><div class="tiers">{tiers}</div></section>
<section class="box"><h2>The winner, as it ran</h2><div class="legend">{legend}</div>{strip([b["n"] for b in beats], 140)}</section>
{groups}
</div>'''
    Path(outfile).write_text(doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("winner")
    ap.add_argument("--page")
    a = ap.parse_args()
    beats = beats_of(a.brand, a.winner)
    cuts = recipes(beats)
    out = ROOT / "runs" / "distinct-six" / a.brand / a.winner
    out.mkdir(parents=True, exist_ok=True)
    src = json.loads((ROOT / "runs" / "video-teardown" / a.brand / a.winner / "run.json").read_text()).get("video")
    (out / "recipes.json").write_text(json.dumps({"brand": a.brand, "winner": a.winner, "source_video": src,
                                                   "formulas": "components/distinct-six/formulas.json", "cuts": cuts},
                                                  indent=1, ensure_ascii=False))
    for c in cuts:
        print(f"{c['id']:<26} {c['length_s']:>5.0f}s  {' → '.join(c['sections'])}")
    if a.page:
        page(a.brand, a.winner, beats, cuts, a.page)
        print("page →", a.page)


if __name__ == "__main__":
    main()
