#!/usr/bin/env python3
"""edit_line_page.py — prints The Edit Line from context/edit-line.json:
the page (context/edit-line.html, published as the artifact) and its Markdown
mirror (EDIT-LINE.md). Prompts are read from their files and shown verbatim.

    python3 machine/edit_line_page.py
"""
from __future__ import annotations
import html
import json
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent
E = html.escape
KIND = {"a": "k-a", "b": "k-b", "t": "k-t", "i": "k-i", "s": "k-s"}


def current(rel: str) -> Path:
    """A prompt path, or the newest -vN- of the same prompt in the same folder
    (prompts move to archive/ when a new version lands)."""
    import re
    f = (TOOL / rel).resolve()
    if f.exists():
        return f
    stem = re.sub(r"-v\d+-", "-v*-", f.name)
    found = sorted(f.parent.glob(stem), key=lambda q: int(re.search(r"-v(\d+)-", q.name).group(1)))
    if not found:
        raise SystemExit(f"prompt not found: {rel}")
    return found[-1]


def stage_html(s: dict) -> str:
    tracks = "".join(f'<span class="{KIND[k]}">{E(t)}</span>' for t, k in s["tracks"])
    rules = "".join(f"<li>{E(r)}</li>" for r in s["rules"])
    listen = f'<div><span class="k">What listening found</span><p>{E(s["listen"])}</p></div>' if s.get("listen") else ""
    bug = f'<div class="dec" style="background:var(--fixbg)"><span class="n" style="color:var(--fix)">FIX</span><p>{E(s["bug"])}</p></div>' if s.get("bug") else ""
    decs = "".join(f'<div class="dec"><span class="n">{E(d["n"])}</span><p>{E(d["q"])}<span class="now">{E(d["now"])}</span></p></div>' for d in s.get("open") or [])
    done = "".join(f'<div class="dec" style="background:var(--builtbg)"><span class="n" style="color:var(--built)">{E(d["n"])}</span><p>{E(d["q"])}<span class="now">Settled: {E(d["answer"])}</span></p></div>' for d in s.get("settled") or [])
    prompt = "".join(f'<details><summary>{E(x["name"])} (current: {E(current(x["file"]).name)})</summary><pre>{E(current(x["file"]).read_text())}</pre></details>' for x in s.get("prompts") or [])
    if s.get("prompt"):
        prompt += f'<details><summary>{E(s["prompt_name"])}, word for word</summary><pre>{E((TOOL / s["prompt"]).read_text())}</pre></details>'
    return f"""<article class="stage" id="{s['id']}">
<div class="stage-side"><span class="stage-id">{E(s['id'].upper().replace('-', ' '))}</span><h3>{E(s['name'])}</h3>
<span class="chip {s['status']}">{E(s['status_note'])}</span><div class="tracks">{tracks}</div><span class="who">Done by: {E(s['who'])}</span></div>
<div class="stage-main"><div class="io"><div><span class="k">Takes in</span><p>{E(s['in'])}</p></div><div><span class="k">Makes</span><p>{E(s['out'])}</p></div></div>
<div><span class="k">Rules today</span><ul class="rules">{rules}</ul></div>
{listen}{bug}<div class="decs"><span class="k">Your call</span>{decs}{done}</div>{prompt}</div></article>"""


def main() -> None:
    d = json.loads((TOOL / "context/edit-line.json").read_text())
    phases = "".join(f'<section class="phase"><div class="phase-head"><h2>{E(p["name"])}</h2><p>{E(p["what"])}</p></div>{"".join(stage_html(s) for s in p["stages"])}</section>' for p in d["phases"])
    ST = {"have": ("built", "Have"), "building": ("fix", "Building"), "partly": ("fix", "Partly"), "missing": ("none", "Missing")}
    counts = {k: sum(1 for e in d.get("elements", []) if e["status"] == k) for k in ST}
    rows, grp = [], None
    for e in d.get("elements", []):
        if e["group"] != grp:
            grp = e["group"]
            rows.append(f'<tr class="grp"><td colspan="6">{E(grp)}</td></tr>')
        cls, lab = ST[e["status"]]
        note = f'<small>{E(e["note"])}</small>' if e.get("note") else ""
        rows.append(f'<tr><td><b>{E(e["name"])}</b><small>{E(e["what"])}</small></td><td>{E(e["teardown"])}</td><td>{E(e["production"])}</td><td>{E(e["edit"])}</td><td><span class="chip {cls}">{lab}</span>{note}</td></tr>')
    elements = ""
    if d.get("elements"):
        tally = " · ".join(f"{counts[k]} {ST[k][1].lower()}" for k in ST)
        elements = (f'<section class="phase" id="elements"><div class="phase-head"><h2>Every element of a video</h2><p>{E(tally)}</p></div>'
                    f'<p>{E(d["elements_intro"])}</p><div class="etab"><table><thead><tr><th>Element</th><th>Teardown names it</th><th>Production makes it</th><th>Edit assembles it</th><th>Today</th></tr></thead>'
                    f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    variation = ""
    v = d.get("variation")
    if v:
        axes = "".join(f'<tr><td><b>{E(a["axis"])}</b><small>{E(a["what"])}</small></td><td>{E(a["level"])}</td><td>{E(a["made"])}</td></tr>' for a in v["axes"])
        vr = "".join(f"<li>{E(r)}</li>" for r in v["rules"])
        vd = "".join(f'<div class="dec"><span class="n">{E(x["n"])}</span><p>{E(x["q"])}</p></div>' for x in v["decisions"])
        vs = "".join(f'<div class="dec" style="background:var(--builtbg)"><span class="n" style="color:var(--built)">{E(x["n"])}</span><p>{E(x["q"])}<span class="now">Settled: {E(x["answer"])}</span></p></div>' for x in v.get("settled") or [])  # hoisted for 3.9 (rule 10)
        variation = (f'<section class="phase" id="variation"><div class="phase-head"><h2>The variation engine</h2><p>planned, not built yet</p></div>'
                     f'<p>{E(v["intro"])}</p><div class="etab"><table><thead><tr><th>What varies</th><th>Level</th><th>What gets made (paid once)</th></tr></thead><tbody>{axes}</tbody></table></div>'
                     f'<div class="dec" style="background:var(--builtbg)"><span class="n" style="color:var(--built)">MATH</span><p>{E(v["math"])}</p></div>'
                     f'<div><span class="k">Rules that make it work</span><ul class="rules">{vr}</ul></div><div class="decs"><span class="k">Your call</span>{vd}{vs}</div></section>')
    inventory = ""
    inv = d.get("inventory")
    if inv:
        SC = {"built": ("built", "Built"), "building": ("fix", "Building"), "planned": ("none", "Planned")}
        srows = "".join(
            f'<tr><td><b>{E(r["stage"])}</b></td><td>{E(r["does"])}'
            + (f'<small style="color:var(--fix)">Fixed today: {E(r["fixed_today"])}</small>' if r.get("fixed_today") else "")
            + (f'<small>Open: {E(r["open"])}</small>' if r.get("open") else "")
            + f'</td><td><span class="chip {SC[r["state"]][0]}">{SC[r["state"]][1]}</span>' + (f'<small>{E(r["prompt"])}</small>' if r.get("prompt") else "") + '</td></tr>'
            for r in inv["stages"])
        lib = "".join(f'<tr><td><b>{E(a)}</b></td><td>{E(b)}</td></tr>' for a, b in inv["libraries"])
        pages = "".join(f'<li><a href="{E(u)}">{E(n)}</a> · {E(w)}</li>' for n, u, w in inv["pages"])
        yours = "".join(f'<li>{E(x)}</li>' for x in inv["yours"])
        known = "".join(f'<li>{E(x)}</li>' for x in inv["known"])
        inventory = (f'<section class="phase" id="inventory"><div class="phase-head"><h2>Where everything stands</h2><p>{E(d.get("updated", ""))}</p></div><p>{E(inv["intro"])}</p>'
                     f'<div class="etab"><table><thead><tr><th>Stage</th><th>What it does</th><th>Today</th></tr></thead><tbody>{srows}</tbody></table></div>'
                     f'<div class="io"><div><span class="k">The libraries it draws from</span><div class="etab"><table><tbody>{lib}</tbody></table></div></div>'
                     f'<div style="display:flex;flex-direction:column;gap:14px"><div><span class="k">Waiting on you</span><ul class="rules">{yours}</ul></div>'
                     f'<div><span class="k">Known gaps</span><ul class="rules">{known}</ul></div><div><span class="k">Pages to open</span><ul class="rules">{pages}</ul></div></div></div></section>')
    ticks = "".join(f'<i style="left:{t / 20 * 100:.2f}%">00:{t:02d}</i>' for t in range(0, 20, 2))
    page = (TOOL / "context/edit-line.tpl.html").read_text()
    page = page.replace("__PHASES__", elements + variation + phases).replace("<section style=\"display:flex;flex-direction:column;gap:12px\">\n  <h2>Which stage fills which track</h2>", inventory + "<section style=\"display:flex;flex-direction:column;gap:12px\">\n  <h2>Which stage fills which track</h2>", 1).replace("__TICKS__", ticks).replace(
        "__PROMPT_READ__", E((TOOL / "prompts/stage-1-read-pack/stage1-read-pack-v1-damon.md").read_text())).replace("Updated 23 Sep 2026", f"Updated {d['updated']}")
    (TOOL / "context/edit-line.html").write_text(page)

    L = ["# The Edit Line — cut and dress", "", f"Updated {d['updated']}. Artifact: see `context/artifacts.md`. Printed by `machine/edit_line_page.py` from `context/edit-line.json` — edit the JSON, not this file.", "",
         "The brief folder is done (clips, voice, handoff doc). These stages turn it into a finished ad with no editor. Each open decision has a code so it can be answered in one line.", ""]
    for p in d["phases"]:
        L += [f"## {p['name']}", "", p["what"], ""]
        for s in p["stages"]:
            L += [f"### {s['id'].upper()} · {s['name']} — {s['status_note']}", "",
                  f"- **Tracks:** {', '.join(t for t, _ in s['tracks'])} · **Done by:** {s['who']}",
                  f"- **Takes in:** {s['in']}", f"- **Makes:** {s['out']}", "", "Rules today:", ""] + [f"- {r}" for r in s["rules"]]
            if s.get("listen"):
                L += ["", f"**What listening found:** {s['listen']}"]
            if s.get("bug"):
                L += ["", f"**Fix:** {s['bug']}"]
            L += ["", "Open decisions:", ""] + [f"- **{x['n']}** {x['q']} _{x['now']}_" for x in s.get("open") or []]
            L += [f"- **{x['n']}** {x['q']} — settled: {x['answer']}" for x in s.get("settled") or []]
            if s.get("prompt"):
                L += ["", f"Prompt: `{s['prompt']}` (verbatim on the page)"]
            for x in s.get("prompts") or []:
                L += ["", f"{x['name']}: `{x['file'].replace('../../../', '')}` (verbatim on the page)"]
            L.append("")
    L += ["## Before the cut — reading the handoff (built, parked)", "", "Prompt: `prompts/stage-1-read-pack/stage1-read-pack-v1-damon.md` (verbatim on the page).", ""]
    if d.get("elements"):
        L += ["## Every element of a video", "", d["elements_intro"], "", "| Group | Element | What it is | Teardown | Production | Edit | Today |", "|---|---|---|---|---|---|---|"]
        L += [f"| {e['group']} | {e['name']} | {e['what']} | {e['teardown']} | {e['production']} | {e['edit']} | {e['status']}{' — ' + e['note'] if e.get('note') else ''} |" for e in d["elements"]]
    if d.get("variation"):
        v = d["variation"]
        L += ["", "## The variation engine (planned)", "", v["intro"], "", "| What varies | Level | What gets made |", "|---|---|---|"]
        L += [f"| {a['axis']} — {a['what']} | {a['level']} | {a['made']} |" for a in v["axes"]]
        L += ["", v["math"], ""] + [f"- {r}" for r in v["rules"]] + [""] + [f"- **{x['n']}** {x['q']}" for x in v["decisions"]]
    if d.get("inventory"):
        inv = d["inventory"]
        L[5:5] = ["## Where everything stands", "", inv["intro"], "", "| Stage | What it does | Today |", "|---|---|---|"] + [
            f"| {r['stage']} | {r['does']}" + (f" Fixed today: {r['fixed_today']}" if r.get('fixed_today') else "") + (f" Open: {r['open']}" if r.get('open') else "") + f" | {r['state']} |" for r in inv["stages"]] + [
            "", "**Libraries:**", ""] + [f"- **{a}:** {b}" for a, b in inv["libraries"]] + ["", "**Waiting on the owner:**", ""] + [f"- {x}" for x in inv["yours"]] + ["", "**Known gaps:**", ""] + [f"- {x}" for x in inv["known"]] + [""]
    (TOOL / "EDIT-LINE.md").write_text("\n".join(L))
    print(TOOL / "context/edit-line.html")


if __name__ == "__main__":
    main()
