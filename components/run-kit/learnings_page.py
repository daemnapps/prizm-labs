#!/usr/bin/env python3
"""The learnings page: every rule in force, newest first, where each came from, which stations it reaches.

    python3 learnings_page.py [--brand b ...] [--html <page.html>] [--md <copy.md>]

The page (HTML) is the owner's: it carries his own words beside a rule when this machine holds them (his node, see
run_kit/learnings.py `quotes`). The Markdown copy is the team's and never carries them. Default outputs: the copy at
runs/learnings/LEARNINGS.md; the page only where --html says (it holds his words, so it is never written into the repo).
"""
import argparse
import html
from collections import Counter
from pathlib import Path

from run_kit import learnings as L
from run_kit import paths

ICON = {"writing": "✍️", "copy": "💬", "image": "🖼️", "video": "🎬", "edit": "✂️"}


def rows(brands):
    seen, out = set(), []
    for b in [None] + list(brands):
        for r in L.in_force(b):
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            out.append(r)
    out.sort(key=lambda r: (r.get("at", ""), r.get("id", "")), reverse=True)
    return out


def _brands():
    d = Path(paths.repo()) / "runs" / "learnings"
    return sorted(f.stem for f in d.glob("*.jsonl") if f.stem not in ("_all", "candidates"))


def markdown(rs, waiting):
    out = ["# Learnings in force", "",
           "Every rule the chain hands its stations, newest first. Source of truth: `runs/learnings/` "
           "(components/run-kit `run_kit/learnings.py`). Rebuilt by `components/run-kit/learnings_page.py`.", "",
           "%d in force · %d candidates waiting for a second run · one-off fixes to single pieces (an edited line, a "
           "remade picture, a price change) stay candidates for their own run and are never handed on" % (len(rs), waiting), "",
           "| id | date | brand | stations | rule | from |", "|---|---|---|---|---|---|"]
    for r in rs:
        src = " · ".join(x for x in (r.get("run"), r.get("from"), r.get("file")) if x)
        out.append("| %s | %s | %s | %s | %s %s | %s |" % (
            r["id"], r.get("at", ""), r.get("brand") or "every brand", ", ".join(r["stations"]),
            "NEVER:" if r["kind"] == "never" else "DO:", r["rule"].replace("|", "/"), src.replace("|", "/")))
    return "\n".join(out) + "\n"


def page(rs, waiting, quotes):
    by = Counter(s for r in rs for s in r["stations"])
    tiles = "".join('<div class="st"><span>%s</span><b>%d</b><i>%s</i></div>' % (ICON.get(s, "•"), by.get(s, 0), s)
                    for s in L.STATIONS)
    cards = []
    for r in rs:
        q = quotes.get(r["id"]) or []
        chips = "".join('<span class="chip">%s %s</span>' % (ICON.get(s, ""), s) for s in r["stations"])
        if r.get("formats"):
            chips += "".join('<span class="chip f">%s</span>' % html.escape(f) for f in r["formats"])
        chips += '<span class="chip b">%s</span>' % html.escape(r.get("brand") or "every brand")
        src = " · ".join(html.escape(x) for x in (r.get("run"), r.get("from")) if x)
        cards.append(
            '<article class="%s"><div class="top"><span class="mark">%s</span><span class="when">%s</span>%s</div>'
            '<p class="rule">%s</p>%s<details><summary>Where it came from</summary><p>%s</p><p class="id">%s · %s</p>'
            '</details></article>' % (
                r["kind"], "✕ NEVER" if r["kind"] == "never" else "✓ DO", html.escape(r.get("at", "")), chips,
                html.escape(r["rule"]),
                "".join('<blockquote>“%s”</blockquote>' % html.escape(x) for x in q[:1]),
                src or "earlier review", html.escape(r["id"]), html.escape(r.get("file") or "")))
    return TEMPLATE.replace("{N}", str(len(rs))).replace("{W}", str(waiting)).replace("{TILES}", tiles) \
        .replace("{CARDS}", "\n".join(cards))


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Learnings In Force</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#16161a;--soft:#6b6b73;--line:#e4e2dc;--do:#1f8a4c;--never:#c2410c;--chip:#eef0f4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121214;--card:#1c1c20;--ink:#f2f2f4;--soft:#a1a1aa;--line:#2c2c33;--do:#4ade80;--never:#fb923c;--chip:#26262c}}
:root[data-theme="dark"]{--bg:#121214;--card:#1c1c20;--ink:#f2f2f4;--soft:#a1a1aa;--line:#2c2c33;--do:#4ade80;--never:#fb923c;--chip:#26262c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 -apple-system,"SF Pro Text",Inter,system-ui,sans-serif}
main{max-width:880px;margin:0 auto;padding:28px 16px 48px}h1{font-size:26px;margin:0 0 16px}
.top3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.k{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--soft)}.v{font-size:22px;font-weight:650;margin-top:4px}
.sts{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:22px}
.st{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px;text-align:center}
.st span{font-size:20px;display:block}.st b{font-size:20px;display:block}.st i{font-style:normal;font-size:12px;color:var(--soft)}
article{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--do);border-radius:12px;padding:12px 14px;margin-bottom:10px}
article.never{border-left-color:var(--never)}
.top{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.mark{font-weight:700;font-size:13px;color:var(--do)}article.never .mark{color:var(--never)}
.when{font-size:13px;color:var(--soft);margin-right:4px}
.chip{font-size:12px;padding:3px 8px;border-radius:999px;background:var(--chip)}.chip.b{font-weight:600}
.rule{margin:8px 0 4px;font-weight:550}blockquote{margin:4px 0;color:var(--soft);font-style:italic;font-size:14px}
details{font-size:13px;color:var(--soft)}summary{cursor:pointer}.id{font-family:ui-monospace,monospace;font-size:12px}
@media (max-width:600px){.top3{grid-template-columns:1fr}.sts{grid-template-columns:repeat(3,1fr)}h1{font-size:22px}}
</style></head><body><main>
<h1>What every run now knows</h1>
<section class="top3">
<div class="tile"><div class="k">Needs you</div><div class="v">Nothing</div></div>
<div class="tile"><div class="k">In force</div><div class="v">{N} rules</div></div>
<div class="tile"><div class="k">Waiting on a 2nd run</div><div class="v">{W}</div></div>
</section>
<section class="sts">{TILES}</section>
{CARDS}
</main></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", action="append", default=None)
    ap.add_argument("--html")
    ap.add_argument("--md", default=str(Path(paths.repo()) / "runs" / "learnings" / "LEARNINGS.md"))
    x = ap.parse_args()
    rs = rows(x.brand if x.brand is not None else _brands())
    active = {r["id"] for r in rs}
    waiting = len({c["id"] for c in L.candidates() if c["id"] not in active and not c.get("one_off")})
    Path(x.md).write_text(markdown(rs, waiting))
    print("copy: %s (%d in force, %d waiting)" % (x.md, len(rs), waiting))
    if x.html:
        Path(x.html).parent.mkdir(parents=True, exist_ok=True)
        Path(x.html).write_text(page(rs, waiting, L.quotes()))
        print("page: %s" % x.html)


if __name__ == "__main__":
    main()
