#!/usr/bin/env python3
"""The owner's winner page: the swipe's match on top (the matrix, nothing picked), the retire proposal, then every
banked winner as a tile with its call and proof. Built from the index and the ranking; no model call.

    python3 winner_page.py --brand <brand> --swipe <swipe run> --out <page.html> [--md <copy.md>]
"""
import argparse
import base64
import html
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import winner_match as WM  # noqa: E402

WI = WM.WI
E = html.escape
MARK = {"same": ("✓", "y"), "close": ("~", "c"), "different": ("✗", "n")}
CALL = {"keep": ("Keep", "k"), "watch": ("Watch", "w"), "retire": ("Retire", "r"), "fold": ("Fold", "f")}
COLS = ["aware_in", "aware_out", "format", "cast", "framework", "sections", "sophistication", "length", "pace",
        "tone", "hook", "sound"]
SHORT = {"aware_in": "aware in", "aware_out": "aware out", "format": "format", "cast": "cast",
         "framework": "frame", "sections": "sections", "sophistication": "soph.", "length": "length",
         "pace": "pace", "tone": "tone", "hook": "hook", "sound": "sound"}


def thumb(run):
    p = WI.RUNS / run / "poster.jpg"
    if not p.is_file():
        return ""
    with tempfile.TemporaryDirectory() as t:
        o = Path(t) / "t.jpg"
        try:
            subprocess.run(["sips", "-Z", "160", "-s", "formatOptions", "60", str(p), "--out", str(o)],
                           check=True, capture_output=True)
            data = o.read_bytes()
        except (OSError, subprocess.CalledProcessError):
            data = p.read_bytes() if p.stat().st_size < 60000 else b""
    return "data:image/jpeg;base64," + base64.b64encode(data).decode() if data else ""


def money(v):
    return f"${v:,.0f}" if v else "–"


CSS = """
:root{--bg:#eef0eb;--panel:#fff;--ink:#14201a;--dim:#66736c;--line:#d5dad4;--accent:#1d7a55;--hl:#e3efe8;
--y:#1d7a55;--yb:#e3efe8;--c:#9a6b00;--cb:#fbf1d9;--n:#b23b2a;--nb:#f8e3df;--f:#5d6a8a;--fb:#e6e9f2;
--head:"Space Grotesk",Inter,system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141816;--panel:#1f2523;--ink:#eef2ee;
--dim:#9aa7a0;--line:#363f3b;--accent:#52c79a;--hl:#1f3329;--y:#52c79a;--yb:#1f3329;--c:#e6b44c;--cb:#3a3220;
--n:#f08a78;--nb:#3d2420;--f:#a7b3d6;--fb:#262b3a;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#141816;--panel:#1f2523;--ink:#eef2ee;--dim:#9aa7a0;--line:#363f3b;--accent:#52c79a;
--hl:#1f3329;--y:#52c79a;--yb:#1f3329;--c:#e6b44c;--cb:#3a3220;--n:#f08a78;--nb:#3d2420;--f:#a7b3d6;--fb:#262b3a;
color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;margin:0;
padding:20px max(16px,env(safe-area-inset-right,0px)) 60px max(16px,env(safe-area-inset-left,0px))}
.w{max-width:960px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
h1{font:700 26px var(--head);margin:0}h2{font:700 17px var(--head);margin:10px 0 0}
.sub,.m{color:var(--dim);font-size:13px}
.top{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.box{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;display:flex;
flex-direction:column;gap:6px;min-width:0}
.box .k{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--dim)}
.box .v{font:700 20px var(--head)}.box.now{border-color:var(--accent);background:var(--hl)}
.pick{display:flex;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:10px;min-width:0}
.pick img,.tile img{width:54px;height:96px;object-fit:cover;border-radius:6px;flex:0 0 54px;background:var(--line)}
.pick .b,.tile .b{min-width:0;flex:1;display:flex;flex-direction:column;gap:4px}
.sc{font:700 22px var(--head);min-width:42px;text-align:right}
.tg{display:inline-block;font-weight:800;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
padding:2px 7px;border-radius:99px;border:1px solid currentColor;white-space:nowrap}
.tg.k,.tg.y{color:var(--y);background:var(--yb)}.tg.w,.tg.c{color:var(--c);background:var(--cb)}
.tg.r,.tg.n{color:var(--n);background:var(--nb)}.tg.f{color:var(--f);background:var(--fb)}
.mx{width:100%;border-collapse:separate;border-spacing:2px;font-size:12px}
.mx th{font-weight:600;color:var(--dim);text-align:center;padding:4px 2px;white-space:nowrap}
.mx th.l,.mx td.l{text-align:left}.mx td{text-align:center;padding:6px 2px;border-radius:5px;background:var(--panel)}
.mx td.y{background:var(--yb);color:var(--y);font-weight:800}.mx td.c{background:var(--cb);color:var(--c);font-weight:800}
.mx td.n{background:var(--nb);color:var(--n);font-weight:800}.mx td.u{color:var(--dim)}
.mx td.l{background:transparent;font-weight:600;white-space:nowrap;max-width:190px;overflow:hidden;text-overflow:ellipsis}
.mxw{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.tile{display:flex;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;min-width:0}
.row{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.nums{display:flex;gap:10px;flex-wrap:wrap;font-size:12px}.nums b{font:700 14px var(--head)}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px;font-size:13px}
summary{cursor:pointer;font-weight:600}
.cnt{display:flex;gap:8px;flex-wrap:wrap}
.home{display:flex;align-items:center;gap:8px}.srcs{display:flex;flex-direction:column;gap:6px;flex:1;min-width:0}
.st code{font-size:11px;color:var(--dim);word-break:break-all}.st.one{flex:1.2;border:2px solid var(--accent);background:var(--hl)}
.ar.big{font-size:22px}
@media (max-width:640px){.home{flex-direction:column;align-items:stretch}.ar.big{transform:rotate(90deg);align-self:center}}
.flow{display:flex;align-items:stretch;gap:6px;flex-wrap:wrap}
.st{flex:1;min-width:120px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;
display:flex;flex-direction:column;gap:3px}
.st .n{font:700 13px var(--head);color:var(--accent)}.ar{align-self:center;color:var(--dim);font-weight:800}
.ex{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;display:flex;
flex-direction:column;gap:10px}
.exh{display:flex;align-items:center;justify-content:center;gap:18px}
.side{display:flex;flex-direction:column;align-items:center;gap:4px;font-size:13px;text-align:center;max-width:150px}
.side img{width:54px;height:96px;object-fit:cover;border-radius:6px}
.vs{display:flex;flex-direction:column;align-items:center}
.ext td.u{font-size:12px}.ext td{padding:5px 4px}
@media (max-width:640px){.ar{display:none}.st{min-width:46%}}
@media (max-width:640px){.top{grid-template-columns:1fr}.tiles{grid-template-columns:1fr}}
"""


HOME = [("Meta ad account", "sales, spend, months run", "runs/winners/<b>/bank.json"),
        ("Teardowns", "what each winner does", "runs/video-teardown/_work/<winner>/")]


def homes(idx):
    """Where this brand's winners come from: the bank, the teardowns, and its registry only when it has one."""
    reg = [x for x in (idx.get("sources") or []) if x.endswith(".json") and "/runs/" not in "/" + x]
    return HOME + [("Top-ads list", "ranks, hooks, offers", x) for x in reg]
READERS = ["Winner match (every swipe)", "The writing", "Studio pick", "This page"]


def where_they_live(brand, idx):
    H = ['<h2>Where winners live</h2><div class="home"><div class="srcs">']
    for a, b, c in homes(idx):
        H.append(f'<div class="st"><b>{a}</b><span class="m">{b}</span><code>{E(c.replace("<b>", brand))}</code></div>')
    H.append('</div><span class="ar big">→</span><div class="st one"><span class="n">THE ONE RECORD</span>'
             f'<b>Winner index</b><code>runs/winners/{E(brand)}/winner-index.json</code>'
             f'<span class="m">{sum(1 for r in idx["winners"] if r["retire"]["call"] in ("keep", "watch", "needs teardown"))}'
             ' video winners · rebuilt on every match</span></div><span class="ar big">→</span><div class="srcs">')
    for r in READERS:
        H.append(f'<div class="st"><b>{r}</b></div>')
    H.append('</div></div>')
    return H


STEPS = [("1", "Swipe teardown", "read once"), ("2", "12 traits", "pulled from it"),
         ("3", "Same 12", "from every winner's teardown"), ("4", "✓ ~ ✗ each", "weighed into /100"),
         ("5", "Top 3 to you", "you pick, writing starts")]


def how_it_works(sw, best, sw_img, wn_img):
    """The flow, then the real swipe laid against the top winner trait by trait, with each trait's weight."""
    H = ['<h2>How a swipe gets matched</h2><div class="flow">']
    for i, (n, a, b) in enumerate(STEPS):
        H.append(f'<div class="st"><span class="n">{n}</span><b>{a}</b><span class="m">{b}</span></div>')
        if i < len(STEPS) - 1:
            H.append('<span class="ar">→</span>')
    H.append('</div>')
    if not best:
        return H
    H.append(f'<div class="ex"><div class="exh"><div class="side"><img src="{sw_img}" alt=""><b>Swipe</b></div>'
             f'<div class="vs"><span class="sc">{best["score"]}</span><span class="m">/100</span></div>'
             f'<div class="side"><img src="{wn_img}" alt=""><b>{E(best["label"])}</b></div></div>'
             '<table class="mx ext"><tr><th class="l">trait</th><th>weight</th><th>swipe</th><th></th><th>winner</th></tr>')
    for k in WM.WEIGHTS:
        v = best["matrix"].get(k)
        if v:
            sym, cls = MARK[v["mark"]]
            sv, wv = str(v["swipe"]), str(v["winner"])
            if k == "sections":
                sv, wv = f'{len(str(v["swipe"]).split(" → "))} parts', f'{len(str(v["winner"]).split(" → "))} parts'
            H.append(f'<tr><td class="l">{WM.TRAIT_NAMES[k]}</td><td class="u">{WM.WEIGHTS[k]}</td>'
                     f'<td class="u">{E(sv)}</td><td class="{cls}">{sym}</td><td class="u">{E(wv)}</td></tr>')
        else:
            H.append(f'<tr><td class="l">{WM.TRAIT_NAMES[k]}</td><td class="u">{WM.WEIGHTS[k]}</td>'
                     '<td class="u" colspan="3">not in the winner\'s teardown · left out</td></tr>')
    H.append(f'</table><div class="m">✓ full weight · ~ half · ✗ none · 70+ strong · 55–69 workable · under 55 weak</div></div>')
    return H


def build(brand, swipe, top=6):
    idx = WI.build(brand)
    res = WM.rank(swipe, brand, top=50)
    recs = {r["run"]: r for r in idx["winners"]}
    thumbs = {}

    def th(run):
        if run not in thumbs:
            thumbs[run] = thumb(run)
        return thumbs[run]

    counts = {}
    for r in idx["winners"]:
        counts[r["retire"]["call"]] = counts.get(r["retire"]["call"], 0) + 1
    sw = res["swipe"]
    best = res["winners"][0] if res["winners"] else None
    H = [f'<title>{E(brand.upper())} Winners</title>',
         '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Space+Grotesk:wght@700&display=swap">',
         f"<style>{CSS}</style>", '<div class="w">',
         f'<header><h1>{E(brand.upper())} Winners</h1><div class="sub">{counts.get("keep", 0) + counts.get("watch", 0)} winners in the bank · proof as of '
         f'{E(idx["snapshot"])} · every swipe matched before writing</div></header>']
    # the three things on top
    H.append('<div class="top">')
    H.append(f'<div class="box now"><span class="k">Needs you</span><span class="v">Pick a winner</span>'
             f'<span class="m">for swipe {E(res["swipe_run"])} · nothing picked</span></div>')
    H.append(f'<div class="box"><span class="k">Best fit</span><span class="v">{best["score"] if best else "–"}/100'
             f'</span><span class="m">{E(best["label"]) if best else ""} · '
             f'<span class="tg {"y" if best and best["fit"]=="strong" else ("c" if best and best["fit"]=="workable" else "n")}">'
             f'{E(best["fit"]) if best else ""}</span></span></div>')
    H.append(f'<div class="box"><span class="k">Then</span><span class="v">Bank: {counts.get("keep", 0) + counts.get("watch", 0)} winners</span>'
             f'<span class="cnt">' + "".join(
                 f'<span class="tg {CALL[c][1]}">{CALL[c][0]} {counts.get(c, 0)}</span>'
                 for c in ("keep", "watch", "retire", "fold")) + '</span></div>')
    H.append('</div>')
    H += where_they_live(brand, idx)
    H += how_it_works(sw, best, th(res["swipe_run"]), th(best["winner"]) if best else "")
    # the swipe and its matrix
    H.append(f'<h2>The swipe · {E(sw["format"])} · {WI.mmss(sw["runtime"])}</h2>')
    H.append(f'<div class="pick"><img src="{th(res["swipe_run"])}" alt=""><div class="b"><b>{E(WI._clip(sw["one_line"], 90))}</b>'
             f'<div class="nums"><span class="tg y">{E(sw["aware_in"])} → {E(sw["aware_out"])}</span>'
             f'<span class="tg f">{E(sw["cast"])}</span><span class="tg f">{E(sw["framework"] or "no framework")}</span>'
             f'<span class="tg f">sold on {E(sw["sophistication"] or "?")}</span></div>'
             f'<span class="m">{E(" → ".join(sw["sections"]))}</span></div></div>')
    H.append('<div class="mxw"><table class="mx"><tr><th class="l">winner</th><th>fit</th>' +
             "".join(f"<th>{SHORT[c]}</th>" for c in COLS) + "</tr>")
    for x in res["winners"][:top]:
        cells = []
        for c in COLS:
            v = x["matrix"].get(c)
            if not v:
                cells.append('<td class="u" title="not in its teardown">·</td>')
            else:
                s, k = MARK[v["mark"]]
                cells.append(f'<td class="{k}" title="swipe {E(str(v["swipe"]))} · winner {E(str(v["winner"]))}">{s}</td>')
        H.append(f'<tr><td class="l">{E(x["label"].replace("Winner ", ""))}</td><td><b>{x["score"]}</b></td>'
                 + "".join(cells) + "</tr>")
    H.append('</table></div>')
    H.append('<div class="m">✓ same · ~ close · ✗ different · · not in the teardown</div>')
    # top picks as cards
    H.append('<h2>Your pick · top 3</h2>')
    for x in res["winners"][:3]:
        p = x["proof"]
        c = CALL.get(x["call"] or "keep")
        H.append(f'<div class="pick"><img src="{th(x["winner"])}" alt=""><div class="b"><div class="row">'
                 f'<b>{E(x["label"])}</b><span class="sc">{x["score"]}</span></div>'
                 f'<div class="nums"><span><b>{p.get("purchases") or "–"}</b> sales</span>'
                 f'<span><b>{money(p.get("cpa"))}</b> a sale</span><span><b>{p.get("roas") or "–"}x</b></span>'
                 f'<span>last ran <b>{E(str(p.get("last_ran") or "?"))}</b></span><span class="tg {c[1]}">{c[0]}</span></div>'
                 f'<span class="m">{E(x["reason"])}</span></div></div>')
    # retire proposal
    H.append('<h2>Folded and retired</h2>')
    H.append('<div class="m">Fold = a copy, removed from the bank · Retire = not a winner · '
             'Watch = lost money (under 1.0x), still matched</div>')
    for call in ("retire", "fold", "watch"):
        rows = [r for r in idx["winners"] if r["retire"]["call"] == call]
        if not rows:
            continue
        H.append(f'<details{" open" if call == "retire" else ""}><summary><span class="tg {CALL[call][1]}">'
                 f'{CALL[call][0]} {len(rows)}</span></summary><div class="tiles" style="margin-top:8px">')
        for r in rows:
            H.append(f'<div class="tile"><img src="{th(r["run"])}" alt=""><div class="b"><b>{E(r["label"])}</b>'
                     f'<span class="m">{E(r["retire"]["why"])}</span></div></div>')
        H.append('</div></details>')
    gaps = [r for r in idx["winners"] if r["retire"]["call"] in ("keep", "watch", "needs teardown")
            and not r["teardown"]["complete"]]
    if gaps:
        H.append(f'<h2>Can\'t be matched fully yet <span class="m">{len(gaps)}</span></h2><div class="tiles">')
        for r in sorted(gaps, key=lambda r: -(r["proof"].get("purchases") or 0)):
            miss = r["teardown"]["missing"]
            H.append(f'<div class="tile"><div class="b"><div class="row"><b>{E(r["label"])}</b>'
                     f'<span class="tg {"r" if not r["run"] else "w"}">{"no teardown" if not r["run"] else "incomplete"}</span></div>'
                     f'<div class="nums"><span><b>{r["proof"].get("purchases") or "–"}</b> sales</span></div>'
                     f'<span class="m">missing: {E(", ".join(miss))}</span></div></div>')
        H.append('</div>')
    # every winner
    H.append('<h2>Every winner</h2><div class="tiles">')
    order = {"keep": 0, "watch": 1, "retire": 2, "fold": 3}
    for r in sorted([r for r in idx["winners"] if r["retire"]["call"] in ("keep", "watch")], key=lambda r: (order[r["retire"]["call"]], -(r["proof"].get("purchases") or 0))):
        t, p = r["traits"], r["proof"]
        c = CALL[r["retire"]["call"]]
        H.append(f'<div class="tile"><img src="{th(r["run"])}" alt=""><div class="b"><div class="row">'
                 f'<b>{E(r["label"])}</b><span class="tg {c[1]}">{c[0]}</span></div>'
                 f'<div class="nums"><span><b>{p.get("purchases") or "–"}</b> sales</span>'
                 f'<span><b>{money(p.get("cpa"))}</b></span><span><b>{p.get("roas") or "–"}x</b></span>'
                 f'<span>ran to <b>{E(str(p.get("last_ran") or "?"))}</b></span></div>'
                 f'<span class="m">{E(t["format"])} · {WI.mmss(t["runtime"])} · {E(t["aware_in"] or "?")} → '
                 f'{E(t["aware_out"] or "?")} · {E(t["framework"] or "no framework")}</span>'
                 f'<details><summary>what it argues</summary>{E(r["argument"] or "–")}<br><br>'
                 f'<b>Hook</b> · {E(r["hook_words"] or "–")}<br><b>Sections</b> · {E(" → ".join(t["sections"]) or "–")}'
                 f'<br><b>Posted</b> · {E(r["posted"] or "–")}</details></div></div>')
    H.append('</div></div>')
    return "\n".join(H), idx, res


def markdown(idx, res):
    sw = res["swipe"]
    L = [f"# {idx['brand'].upper()} winners: matching, folded and retired ({idx['built']})", "",
         f"Source: `runs/winners/{idx['brand']}/winner-index.json`, built by "
         "`components/video-writing/machine/winner_index.py build`; ranking by `winner_match.py rank` (trait matrix, "
         "no model call, nothing picked; the owner picks, then `switch --why`).", "",
         f"## Test swipe `{res['swipe_run']}`", "",
         f"{sw['format']} · {sw['cast']} · {WI.mmss(sw['runtime'])} · {sw['aware_in']} → {sw['aware_out']} · "
         f"{sw['framework']} · sold on {sw['sophistication']}", "", f"Verdict: {res['verdict']}.", "",
         "| # | winner | fit | call | sales | $/sale | last ran | reason |", "|---|---|---|---|---|---|---|---|"]
    for x in res["winners"]:
        p = x["proof"]
        L.append(f"| {x['rank']} | {x['label']} | {x['score']} {x['fit']} | {x['call']} | {p.get('purchases') or '–'} | "
                 f"{money(p.get('cpa'))} | {p.get('last_ran') or '?'} | {x['reason']} |")
    L += ["", f"Weights: " + ", ".join(f"{WM.TRAIT_NAMES[k]} {v}" for k, v in WM.WEIGHTS.items()) +
          f". Strong ≥ {WM.FIT_STRONG}, weak < {WM.FIT_WEAK}.", "", "## Folded and retired", "", f"Rule: {idx['rule']}", ""]
    for call in ("retire", "fold", "watch"):
        for r in idx["winners"]:
            if r["retire"]["call"] == call:
                L.append(f"- **{call}** {r['label']}: {r['retire']['why']}")
    L += ["", "Full per-winner index: `runs/winners/%s/winner-index.md`." % idx["brand"]]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--swipe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--md")
    a = ap.parse_args()
    page, idx, res = build(a.brand, a.swipe)
    Path(a.out).write_text(page)
    if a.md:
        Path(a.md).write_text(markdown(idx, res))
    print(a.out, len(page) // 1024, "KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
