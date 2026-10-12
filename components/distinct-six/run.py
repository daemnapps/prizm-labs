#!/usr/bin/env python3
"""The Distinct Six — one concept written as N genuinely different ads.

Off to the side of the video chain (the owner, 2026-10-08: the developer is working in it).
Reads a finished chain run and writes N versions, each a full ad built from the
doctrine's own sections, each declaring its moves. Every
pair must be 3+ moves apart and each one clear of what's running (scored with
creative-diversity/check.py); failures go back once for a rewrite.

    python3 components/distinct-six/run.py runs/video-teardown/<brand>/<run> --angle pigment-memory [--n 6]

Writes runs/distinct-six/<brand>/<run>/versions.json + page.html. Claude runs on
the owner's own plan (`claude -p`, the Viewer Check's way); Meta is never called.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIB = ROOT / "components" / "elements" / "library"
sys.path.insert(0, str(ROOT / "components" / "creative-diversity"))
import check as K  # noqa: E402
import matrix as M  # noqa: E402

SECTIONS = json.loads((LIB / "doctrine.section.json").read_text())["rows"]
SECTION_IDS = [x["id"] for x in SECTIONS]
# one colour per doctrine section, in the doctrine's own order (the page's colours, nothing more)
PALETTE = ["#e0663a", "#d1a12a", "#c2410c", "#8a5a2b", "#2f6fd6", "#3aa3b8", "#5b6ee1", "#2a9d6f",
           "#a35bd1", "#e05a9a", "#b8862a", "#16825d", "#4fb37a", "#7a7f99", "#c94f4f"]
COLOR = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(SECTION_IDS)}
PROMPT = sorted((HERE / "prompts").glob("stage4v-distinct-v*-damon.md"),
                key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))[-1]
MIN = json.loads((ROOT / "components" / "creative-diversity" / "dimensions.json").read_text())["rule"]["min_moves"]


def rows(name):
    return json.loads((LIB / f"{name}.json").read_text())["rows"]


def stage(run, *names):
    for n in names:
        f = run / "stages" / n
        if f.exists():
            return f.read_text()
    return ""


def section_map(doctrine_md):
    """[(section, start_s, end_s)] from the doctrine read's SECTIONS CARRIED."""
    out = []
    for m in re.finditer(r"^([a-z-]+)\s+(\d+):(\d+(?:\.\d+)?)\s*[–-]\s*(\d+):(\d+(?:\.\d+)?)", doctrine_md, re.M):
        s = int(m.group(2)) * 60 + float(m.group(3))
        e = int(m.group(4)) * 60 + float(m.group(5))
        if m.group(1) in COLOR:
            out.append((m.group(1), s, e))
    return out


def library_hints(brand, avatar):
    mx, _ = K.library(brand)
    if not mx:
        return "no running library read yet", "anything"
    n = len(mx["items"]) or 1
    crowded = []
    for k, label in (("setting", "setting"), ("face", "face"), ("format", "format"), ("look", "style_id")):
        for v, c in mx["counts"][k][:3]:
            if v not in ("unclear", None) and c / n >= 0.12:
                crowded.append(f"{label} `{v}` ({c} of {n} running)")
    open_ = [f"awareness `{lv}` ({x['have']:.0%} running vs {x['target']:.0%} target)"
             for lv, x in mx["spread"].items() if x["have"] < x["target"]]
    av = mx["avatars"].get(avatar, {})
    open_ += [f"setting `{s}` (never used)" for s in av.get("settings_never_used", [])]
    return "; ".join(crowded) or "none", "; ".join(open_) or "anything"


LEDGER = Path(os.environ.get("CREATIVE_INDEX_DB") or ROOT / "records" / "asset-ledger" / "ledger.db")


def index_table(brand, per_move=6):
    """What each value of each move has earned on Meta — the Creative Index
    (asset-ledger/db/creative.py, view element_score)."""
    import sqlite3
    if not LEDGER.exists():
        return "(no index yet — build the Creative Index into $CREATIVE_INDEX_DB)"
    db = sqlite3.connect(LEDGER)
    out = []
    for move in ("format", "style", "setting", "face", "awareness", "angle", "sub_avatar"):
        rows = db.execute("SELECT value, live, spend, purchases, cpa FROM element_score WHERE brand_id=? AND move=? "
                          "AND COALESCE(spend,0) > 0 ORDER BY COALESCE(purchases,0) DESC, spend DESC LIMIT ?",
                          (brand, move, per_move)).fetchall()
        if rows:
            out.append(f"**{move}** — " + " · ".join(
                f"`{v}` ${s:,.0f} → {p or 0:g} purchases" + (f" (${c:,.0f} each)" if c else "") for v, l, s, p, c in rows))
    return "\n".join(out) or "(nothing has run yet)"


def fill(run, brand, avatar, angle, n, sub=None):
    core = json.loads((ROOT / "brands" / brand / "brand-identity/core-message/core-message.json").read_text())["core"]
    settings = json.loads((ROOT / "brands" / brand / "strategy/settings.json").read_text())["settings"]
    cards = json.loads((ROOT / "brands" / brand / "ai-elements/characters/casting/cards-v6.json").read_text())["cards"]
    cast = [f"- `{c['id']}` — {c.get('role')}, {c.get('gender')}, {c.get('age-band')}, {c.get('ethnic-appearance')}: {(c.get('reads') or '')[:90]}"
            for c in cards if avatar in (c.get("avatars-fit") or []) or not c.get("avatars-fit")]
    crowded, open_ = library_hints(brand, avatar)
    index = index_table(brand)
    sections = "\n".join(f"- `{x['id']}` — {(x.get('what') or '')[:110]}" for x in SECTIONS)
    smap = section_map(stage(run, "1c-doctrine.md"))
    vals = {
        "N": str(n), "AVATAR": avatar, "ANGLE": angle, "CORE": core,
        "CROWDED": crowded, "OPEN": open_, "SECTIONS": sections, "INDEX": index,
        "SCRIPT": (stage(run, "4e-close.md", "4d-expansion.md", "3-injection.md")
                   or "(our own winning ad — its transcript and spec)\n" + stage(run, "1-transcript.md") + "\n\n" + stage(run, "2-spec.md"))[:30000],
        "SECTION_MAP": "\n".join(f"{s} {a:.1f}s–{e:.1f}s" for s, a, e in smap) or "not read",
        "HOOKS": stage(run, "4b-hooks.md")[:12000] or "none written yet — write each version's own opening",
        "CULTURE": stage(run, "1k-culture.md")[:4000] or "none",
        "FORMATS": " · ".join(f"`{r['id']}`" for r in rows("format.video") + rows("structure.video")),
        "STYLES": " · ".join(f"`{r['id']}`" for r in rows("style.video")),
        "SETTINGS": " · ".join(f"`{s['id']}` ({s['what']})" for s in settings),
        "CAST": "\n".join(cast[:60]) or "no banked cast — use NEW (description)",
    }
    text = PROMPT.read_text()
    if sub:
        card = next((ROOT / "brands" / brand / "core-avatars" / avatar / "sub-avatars").glob(f"sub-*-{sub}.md"), None)
        desire = card.read_text().split("Core desire", 1)[-1].split("\n", 1)[0][:300] if card else ""
        text = text.replace("Every version is for this avatar and argues this angle.",
                            f"Every version is for this avatar and argues this angle. **Sub-avatar `{sub}`**: {desire}")
    for k, v in vals.items():
        text = text.replace("{" + k + "}", v)
    return text, smap


def claude(text):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE", "ANTHROPIC")) and k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    r = subprocess.run(["claude", "-p", "--model", "opus", "--allowed-tools", "", "--output-format", "json"],
                       input=text + "\n\n(Answer with the JSON only.)", capture_output=True, text=True,
                       env=env, timeout=1800, cwd="/tmp")
    d = json.loads(r.stdout or "{}")
    if d.get("is_error") or not d.get("result"):
        raise SystemExit(f"Claude didn't answer: {str(d.get('result') or r.stderr)[:400]}")
    t = d["result"]
    i = t.find("{")
    return json.JSONDecoder().raw_decode(t[i:])[0]


def moves(v):
    p = v.get("piece", {})
    return {"who": p.get("sub") if p.get("sub") not in (None, "", "none") else p.get("avatar"),
            "awareness": p.get("awareness"), "argument": p.get("angle"), "format": p.get("format"),
            "face": p.get("face") or "none", "setting": p.get("setting"), "look": p.get("style_id")}


def score(brand, versions):
    for v in versions:
        v["_moves"] = moves(v)
        v["running"] = {k: x for k, x in K.score(brand, v["_moves"]).items() if k != "moves"}
    pairs = {}
    for (i, a), (j, b) in combinations(enumerate(versions), 2):
        d, diff = M.distance(a["_moves"], b["_moves"])
        pairs[f"{i}-{j}"] = {"moves": d, "differs_on": diff}
    bad = [k for k, p in pairs.items() if p["moves"] < MIN]
    stale = [i for i, v in enumerate(versions) if v["running"].get("verdict") == "variation"]
    return pairs, bad, stale


def page(brand, run, avatar, angle, versions, pairs, smap, out):
    e = html.escape

    def bar(beats):
        total = sum(max(0.5, float(b.get("seconds") or 1)) for b in beats) or 1
        segs = "".join(f'<i style="flex:{max(0.5, float(b.get("seconds") or 1)) / total:.4f};background:{COLOR.get(b.get("section"), "#999")}" '
                       f'title="{e(b.get("section", ""))} · {e(str(b.get("seconds")))}s"></i>' for b in beats)
        return f'<div class="bar">{segs}</div><div class="secs">{total:.0f}s</div>'

    src = [{"section": s, "seconds": b - a} for s, a, b in smap]
    cards = []
    for i, v in enumerate(versions):
        p = v["piece"]
        chips = "".join(f'<span class="chip"><b>{k}</b> {e(str(p.get(k, "")))}</span>'
                        for k in ("awareness", "format", "lead", "face", "setting", "style_id"))
        verdict = v["running"].get("verdict", "?")
        beats = "".join(f'<li><span class="dot" style="background:{COLOR.get(b.get("section"), "#999")}"></span>'
                        f'<b>{e(b.get("section", ""))}</b> · {e(str(b.get("seconds")))}s — {e(b.get("says", ""))}'
                        f'<div class="shows">{e(b.get("shows", ""))}</div></li>' for b in v.get("beats", []))
        hooks = "".join(f"<li>{e(h)}</li>" for h in v.get("hooks", []))
        cards.append(f'''<article class="v"><div class="vh"><span class="n">V{i + 1}</span><h3>{e(v.get("title", ""))}</h3>
<span class="pill {'ok' if verdict == 'new' else 'warn' if verdict == 'risky' else 'bad'}">{e(verdict)} vs running · {v["running"].get("moves_apart", "?")} moves</span></div>
<p class="why">{e(v.get("why_different", ""))}</p><div class="chips">{chips}</div>{bar(v.get("beats", []))}
<details><summary>Beats and words</summary><ol class="beats">{beats}</ol>{f'<p class="hk">Hook tests</p><ul>{hooks}</ul>' if hooks else ""}</details></article>''')
    n = len(versions)
    grid = '<table class="grid"><tr><th></th>' + "".join(f"<th>V{j + 1}</th>" for j in range(n)) + "</tr>"
    for i in range(n):
        grid += f"<tr><th>V{i + 1}</th>"
        for j in range(n):
            if i == j:
                grid += "<td class='self'></td>"
                continue
            p = pairs[f"{min(i, j)}-{max(i, j)}"]
            cls = "ok" if p["moves"] >= MIN else "warn" if p["moves"] == MIN - 1 else "bad"
            grid += f"<td class='{cls}' title='differs on {e(', '.join(p['differs_on']))}'>{p['moves']}</td>"
        grid += "</tr>"
    grid += "</table>"
    legend = "".join(f'<span><i style="background:{COLOR[x["id"]]}"></i>{e(x["name"])}</span>' for x in SECTIONS)
    doc = f'''<title>Distinct Six · {e(run.name[:40])}</title>
<style>
:root{{--bg:#fbf7f0;--card:#fff;--ink:#1f2333;--soft:#5f6478;--line:#e6e0d4;--ok:#2a9d6f;--warn:#d1a12a;--bad:#cf3f3f}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#14161f;--card:#1d2030;--ink:#eef0f7;--soft:#a3a8bd;--line:#2d3145;color-scheme:dark}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif;margin:0}}
.wrap{{max-width:980px;margin:0 auto;padding-inline:16px;padding-block:24px 64px;display:grid;gap:18px}}
h1,h2,h3{{margin:0;line-height:1.15}}h1{{font-size:1.9rem}}.soft{{color:var(--soft)}}
.legend{{display:flex;flex-wrap:wrap;gap:12px;font-size:.9rem}}.legend i{{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:5px;vertical-align:-2px}}
.bar{{display:flex;height:22px;border-radius:6px;overflow:hidden;gap:2px}}.bar i{{display:block}}.secs{{font-size:.78rem;color:var(--soft);text-align:right}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:grid;gap:10px}}
.vs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:12px}}
.v{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:grid;gap:8px;min-width:0}}
.vh{{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}}.n{{font-weight:800;font-size:1.2rem}}
.pill{{font-size:.75rem;padding:2px 8px;border-radius:999px;background:var(--line)}}.pill.ok{{color:var(--ok)}}.pill.warn{{color:var(--warn)}}.pill.bad{{color:var(--bad)}}
.why{{color:var(--soft);font-size:.93rem}}.chips{{display:flex;flex-wrap:wrap;gap:5px}}
.chip{{font-size:.76rem;padding:2px 8px;border-radius:6px;background:var(--bg);font-family:ui-monospace,monospace}}.chip b{{font-family:system-ui;color:var(--soft);font-weight:600}}
details summary{{cursor:pointer;color:var(--soft);font-size:.9rem}}.beats{{padding-left:18px;font-size:.88rem;display:grid;gap:6px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}.shows{{color:var(--soft);font-size:.82rem}}.hk{{font-weight:600;margin:6px 0 0}}
.gw{{overflow-x:auto}}.grid{{border-collapse:collapse;font-variant-numeric:tabular-nums}}.grid th,.grid td{{padding:6px 10px;text-align:center;border:1px solid var(--line)}}
.grid td.ok{{background:color-mix(in srgb,var(--ok) 25%,transparent)}}.grid td.warn{{background:color-mix(in srgb,var(--warn) 30%,transparent)}}.grid td.bad{{background:color-mix(in srgb,var(--bad) 30%,transparent)}}.grid td.self{{background:var(--line)}}
</style>
<div class="wrap">
<header style="display:grid;gap:6px"><h1>The Distinct Six</h1>
<p class="soft">{e(brand)} · ad set <b>{e(avatar)} × {e(angle)}</b> · concept from <code>{e(run.name)}</code> · prompt {e(PROMPT.name)}</p>
<div class="legend">{legend}</div></header>
<section class="box"><h2>The winning swipe, by section</h2>{bar(src) if src else '<p class="soft">no section read</p>'}</section>
<section class="box"><h2>How far apart they are</h2><p class="soft">Moves between each pair. Green = {MIN}+ (Meta sees two creatives) · yellow = {MIN - 1} · red = Meta likely groups them.</p><div class="gw">{grid}</div></section>
<section class="vs">{"".join(cards)}</section>
</div>'''
    (out / "page.html").write_text(doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--angle", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--sub")
    a = ap.parse_args()
    run = (ROOT / a.run) if not Path(a.run).is_absolute() else Path(a.run)
    meta = json.loads((run / "run.json").read_text())
    brand = meta["brand"]
    avatar = a.avatar or (re.search(r"Avatar:\s*([a-z-]+)", stage(run, "4e-close.md")) or [None, None])[1] or "unclear"
    text, smap = fill(run, brand, avatar, a.angle, a.n, a.sub)
    out = ROOT / "runs" / "distinct-six" / brand / run.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "sent.md").write_text(text)
    print(f"writing {a.n} versions for {brand} · {avatar} × {a.angle} …")
    got = claude(text)
    versions = got["versions"]
    rounds = [{"round": 1}]
    for rnd in (2,):
        pairs, bad, stale = score(brand, versions)
        rounds[-1].update({"too_close": bad, "like_running": stale})
        if not bad and not stale:
            break
        notes = [f"V{int(k.split('-')[0]) + 1} and V{int(k.split('-')[1]) + 1} are only {pairs[k]['moves']} moves apart "
                 f"(they differ only on {', '.join(pairs[k]['differs_on']) or 'nothing'})" for k in bad]
        notes += [f"V{i + 1} is a variation of a creative already running (same {', '.join(versions[i]['running'].get('same_on', []))})"
                  for i in stale]
        print("rewriting:", "; ".join(notes))
        fix = (text + "\n\n## YOUR FIRST ANSWER\n" + json.dumps({"versions": versions}, ensure_ascii=False)[:40000]
               + "\n\n## WHAT TO FIX\n" + "\n".join(f"- {x}" for x in notes)
               + f"\n\nRewrite only the versions named so every pair is {MIN}+ moves apart and none copies what's running. "
               "Keep the others exactly. Return all versions in the same JSON shape.")
        versions = claude(fix)["versions"]
        rounds.append({"round": rnd})
    pairs, bad, stale = score(brand, versions)
    rounds[-1].update({"too_close": bad, "like_running": stale})
    (out / "versions.json").write_text(json.dumps({"brand": brand, "run": run.name, "avatar": avatar, "angle": a.angle,
                                                   "prompt": PROMPT.name, "rounds": rounds, "pairs": pairs,
                                                   "versions": [{k: x for k, x in v.items() if k != "_moves"} for v in versions]},
                                                  indent=1, ensure_ascii=False))
    page(brand, run, avatar, a.angle, versions, pairs, smap, out)
    mins = min((p["moves"] for p in pairs.values()), default=0)
    print(f"done: {len(versions)} versions · closest pair {mins} moves · too close {len(bad)} · like running {len(stale)} → {out.relative_to(ROOT)}/page.html")


if __name__ == "__main__":
    main()
