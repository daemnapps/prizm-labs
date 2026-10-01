#!/usr/bin/env python3
"""render_board.py — the Style Board page, built from bank.json + swatches/ +
board-content.json (the written sections). One self-contained HTML file, pictures
inlined, so it publishes as an artifact and opens from disk.

    python3 styles/render_board.py            # -> styles/style-board.html

The bank is the truth; this page is a print of it. Change a style in bank.json,
change a written section in board-content.json, run this, republish over the
same artifact (link in ~/devel/daemn/context/artifacts.md — The Format Frontier).
"""
import base64, html, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
E = html.escape


def img(rel):
    p = HERE / rel
    if not p.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def lib(name):
    p = REPO / "components/elements/library" / name
    return json.loads(p.read_text())["rows"] if p.exists() else []


def mirror(bank, C):
    """The Markdown copy of the page, for the team."""
    L = ["# The Format Frontier — style board, the stack, the line, the edit hand", "",
         "Artifact: https://claude.ai/artifact/RUBXajrAH5uyiVH6eyJM5h (republish over it, never a second one). Printed by `render_board.py`; do not edit by hand.", "",
         "## The test", "", bank["the_test"], "", "## The style bank", "",
         "| Style | Family | Looks like | The internet calls it | Keeps the proof | Flag |", "|---|---|---|---|---|---|"]
    for s in bank["styles"]:
        L.append(f"| **{s['name']}** (`{s['id']}`) | {s['family']} | {s['what']} | {s.get('seen_as') or ''} | {s.get('keeps_proof','')} | {s.get('ip_flag') or ''} |")
    L += ["", "### Style locks", ""]
    for s in bank["styles"]:
        L += [f"**{s['id']}** — {s['formula']}  ", f"*Moves:* {s['motion']}", ""]
    sfm = json.loads((HERE.parent / "formats/show-formats.json").read_text())
    L += ["## Show formats (candidates)", "", C["shows"]["intro"], "", "**The six roles — the brand injection:** " + " · ".join(f"{r['name']} = {r['what']}" for r in sfm["roles"]), ""]
    for x in sfm["shows"]:
        L += [f"### {x['name']} (`{x['id']}`)", "", x["what"] + " " + x["why_it_works"], ""] + [f"- **{r['name']}:** {x['roles'][r['id']]}" for r in sfm["roles"]]
        L += [f"- **Sound:** {x['sound']}", f"- **Styles it pairs with:** {', '.join(x['pairs_with_styles'])}", f"- **Who watches (a guess to check):** {x['who_watches_hypothesis']}", ""]
    st = C["stack"]
    L += ["## The stack", "", st["intro"], "", "| Element | Question | Example |", "|---|---|---|"]
    L += [f"| {e['name']} | {e['question']} | {e['example']} |" for e in st["elements"]]
    L += ["", f"### {st['thirty']['title']}", ""] + [f"- **{r['element']}:** {r['value']}" for r in st["thirty"]["rows"]]
    L += ["", "### The Instagram list of 21, sorted", "", "| # | They call it | It is | Where it goes |", "|---|---|---|---|"]
    L += [f"| {r['n']} | {r['name']} | {' + '.join(r['is'])} | {r['goes']} |" for r in st["sorted21"]]
    ln = C["line"]
    L += ["", f"## {ln['title']}", "", ln["intro"], "", "| Step | Your eye | State | Note |", "|---|---|---|---|"]
    L += [f"| {r['t']} | {'yes' if r['you'] else ''} | {r['state']} | {r['d']} |" for r in ln["steps"]]
    if ln.get("sound_note"):
        L += ["", f"**{ln['sound_note']['title']}.** {ln['sound_note']['text']}"]
    L += ["", "**The roll labels:** " + " · ".join(f"`{r[0]}` {r[1]} — {r[2]}" for r in ln.get("labels", [])), "", "**Prompts:**", ""] + [f"- {p['name']}: `{p['file']}`" for p in ln.get("prompts", [])]
    L += ["", "**Built next, in order:**", ""] + [f"{i+1}. {n}" for i, n in enumerate(ln["next"])]
    ed = C["edit"]
    L += ["", f"## {ed['title']}", "", ed["intro"], "", "> " + ed["principle"], "", "**Proof:** " + ed["proof"]["note"], ""] + [f"- {p}" for p in ed["proof"]["points"]]
    if ed.get("model_note"):
        L += ["", f"**{ed['model_note']['title']}.** {ed['model_note']['text']}"]
    L += ["", "### The steps", ""] + [f"{i+1}. **{r['t']}** ({r['who']}) — {r['d']}" for i, r in enumerate(ed["steps"])]
    L += ["", f"### {ed['controls_title']}", ""] + [f"- **{b['name']}** — {b['note']}" for b in ed["controls"]]
    L += ["", f"### {ed['elements_title']}", ""] + [f"- **{b['name']}** — {b['note']}" for b in ed["elements"]]
    L += ["", "### Editing rules", ""] + [f"{i+1}. **{r['t']}** — {r['d']}" for i, r in enumerate(ed["rules"])]
    L += ["", "### Prompts", ""] + [f"- {p['name']}: `video-edit/{p['file']}`" for p in ed["prompts"]]
    L += ["", f"### {ed['gaps_title']}", ""] + [f"- {g}" for g in ed["gaps"]]
    L += ["", "## Tools mined", ""]
    for t in C["tools"]["rows"]:
        L += [f"### [{t['name']}]({t['url']}) — {t['verdict']}", "", t["what"], ""] + [f"- {x}" for x in t["lifted"]] + [""]
    pl = C["plan"]
    L += [f"## {pl['title']}", "", pl["intro"], ""] + [f"- **{d['name']}** — {d['what']}" for d in pl["doors"]]
    L += ["", f"### {pl['steps_title']}", ""] + [f"{i+1}. **{r['t']}** — {r['d']}" for i, r in enumerate(pl["steps"])]
    L += ["", "### The three tests", ""] + [f"- **{b['name']}** {b['note']}" for b in pl["tests"]]
    L += ["", "| Piece | State | Missing |", "|---|---|---|"] + [f"| {r['piece']} | {r['state']} | {r['gap']} |" for r in pl["exists"]]
    la = C["land"]
    L += ["", "## Landscape", "", "| Rung | Everyone | You |", "|---|---|---|"] + [f"| {r['rung']} | {r['all']} | {r['you']} |" for r in la["rows"]]
    return "\n".join(L) + "\n"


def main():
    bank = json.loads((HERE / "bank.json").read_text())
    content = json.loads((HERE / "board-content.json").read_text())
    styles = bank["styles"]
    for s in styles:
        s["_img"] = img(s["swatch"])
    base = img("swatches/_base.jpg")
    formats = [{"id": r["id"], "name": r["name"]} for r in lib("format.video.json")]
    frameworks = [{"id": r["id"], "name": r["name"]} for r in lib("framework.all.json")]
    sf = json.loads((HERE.parent / "formats/show-formats.json").read_text())
    for x in sf["shows"]:
        p = HERE.parent / "formats" / x["frame"]
        x["_img"] = ("data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()) if p.exists() else None
        x.pop("frame_prompt", None)
    (HERE / "STYLE-BOARD.md").write_text(mirror(bank, content))
    pr, missing = content["edit"]["proof"], []
    for k, mime in (("video", "video/mp4"), ("img", "image/jpeg")):
        f = HERE / pr[k]
        if f.exists():
            pr[k] = f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()
        else:
            missing.append(str(f.relative_to(HERE)))
            pr[k] = ""
    data = {
        "styles": [{k: s.get(k) for k in ("id", "name", "what", "family", "formula", "motion", "seen_as", "ip_flag", "fits_formats", "status", "keeps_proof", "proof_note", "_img")} for s in styles],
        "families": bank["families"], "test": bank["the_test"], "base": base,
        "shows": sf["shows"], "roles": sf["roles"], "formats": formats, "frameworks": frameworks, "content": content,
    }
    page = (HERE / "board-template.html").read_text().replace("/*__DATA__*/", "const DATA = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";")
    out = HERE / "style-board.html"
    out.write_text(page)
    for s in styles:
        if not s["_img"]:
            missing.append(s["swatch"])
    for x in sf["shows"]:
        if not x["_img"]:
            missing.append("../formats/" + x["frame"])
    have = sum(1 for s in styles if s["_img"])
    print(f"{out}  ·  {len(styles)} styles, {have} with pictures  ·  {out.stat().st_size // 1024} KB")
    if missing:
        print(f"{len(missing)} pictures not here (they live on the Drive, not in git — see README):")
        for m in missing[:6]:
            print("   " + m)
        if len(missing) > 6:
            print(f"   … and {len(missing) - 6} more")


if __name__ == "__main__":
    main()
