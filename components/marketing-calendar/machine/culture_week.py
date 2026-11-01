#!/usr/bin/env python3
"""The week in their world: fills the weekly culture prompt for one brand and one week.

    /usr/bin/python3 machine/culture_week.py --brand <brand> [--week YYYY-MM-DD]   # Monday; default next Monday

Writes runs/culture-weekly/<brand>/<week>/prompt-as-sent.md — the prompt
(prompts/culture-week-v1-damon.md) with its slots filled from the record:
the brand's core avatars and culture maps, the moments that land that week,
the seasons running, the emails already planned that week (held-open slots
first), and the top posts in the brand's avatar feeds. A Claude session then
runs it with web search and writes week.json + WEEK.md beside it (the Monday
routine "culture-week-monday" does both). Reads only, apart from that one file.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import marketing_calendar as CAL  # noqa: E402  (this folder's planner)
import paths as P  # noqa: E402

TOOL = HERE.parent
PROMPT = TOOL / "prompts" / "culture-week-v1-damon.md"


def repo():
    return P.workspace() if hasattr(P, "workspace") else TOOL.parents[1]


def next_monday(today=None):
    t = today or dt.date.today()
    return t + dt.timedelta(days=(7 - t.weekday()) % 7 or 7)


def months_of(a, b):
    out, m = [], a.replace(day=1)
    while m <= b:
        out.append(m.isoformat()[:7])
        m = (m + dt.timedelta(days=32)).replace(day=1)
    return out


def avatars(root, brand):
    mj = json.loads((root / "brands" / brand / "strategy" / "moments.json").read_text())
    out = []
    for av, block in mj["avatars"].items():
        lines = [f"### {av}", block.get("territory", "")]
        cm = root / "brands" / brand / "core-avatars" / av / "culture-map.md"
        if cm.is_file():
            body = [x for x in cm.read_text().splitlines() if x.strip() and not x.startswith("---")][:30]
            lines += ["Culture map (first lines):", *body]
        out.append("\n".join(lines))
    return "\n\n".join(out)


def moments(root, brand, a, b):
    rows = []
    for mo in months_of(a, b):
        rows += CAL.resolve_moments(root / "brands" / brand, mo)
    seen, dated, seasons = set(), [], []
    for r in rows:
        if not r.get("start") or (r["key"], r["start"]) in seen:
            continue
        s, e = dt.date.fromisoformat(r["start"]), dt.date.fromisoformat(r["end"])
        if s > b or e < a:
            continue
        seen.add((r["key"], r["start"]))
        note = (r.get("note") or "")[:220]
        line = f"- {r['key']} ({r['avatar']}) · {r['start']}{'' if r['end'] == r['start'] else ' to ' + r['end']} · evidence: {r['evidence']}" + (f" · {note}" if note else "")
        (seasons if (e - s).days > 10 else dated).append(line)
    return "\n".join(dated) or "(none)", "\n".join(seasons) or "(none)"


def emails(root, brand, a, b):
    out = []
    for mo in months_of(a, b):
        f = root / "runs" / "marketing-calendar" / brand / mo / "slots.json"
        if not f.is_file():
            continue
        L = json.loads(f.read_text())
        L = L.get("slots", L) if isinstance(L, dict) else L
        for x in L:
            d = dt.date.fromisoformat(x["date"])
            if a <= d <= b:
                held = "HELD OPEN" in str(x.get("occasion"))
                out.append((0 if held else 1, x["date"], f"- {'HELD OPEN · ' if held else ''}{x['id']} · {x['date']} · {x.get('type')} · {str(x.get('occasion'))[:120]}"))
    out.sort(key=lambda t: (t[1], t[0]))
    return "\n".join(t[2] for t in out) or "(no emails planned yet for this week: the month has not been planned)"


def feeds(root, brand, a, n=15):
    base = root / "components" / "swipe-organic" / "records" / "avatar-feeds"
    since = (a - dt.timedelta(days=21)).isoformat()
    posts = []
    for d in sorted(base.glob(f"{brand}--*")):
        it = d / "items.json"
        if not it.is_file():
            continue
        items = json.loads(it.read_text()).get("items", [])
        items = list(items.values()) if isinstance(items, dict) else items
        views = {}
        ob = d / "observations.jsonl"
        if ob.is_file():
            for ln in ob.read_text().splitlines():
                try:
                    o = json.loads(ln)
                except ValueError:
                    continue
                views[o["item"]] = o.get("views") or 0
        for x in items:
            if (x.get("posted") or "") < since:
                continue
            v = views.get(f"{x.get('platform')}:{x.get('id')}", 0)
            cap = " ".join((x.get("caption") or "").split())[:160]
            posts.append((v, f"- {d.name} · {v:,} views · {x.get('posted', '')[:10]} · {cap} · {x.get('url')}"))
    posts.sort(key=lambda t: -t[0])
    return "\n".join(p for _, p in posts[:n]) or "(no feed posts from the last 21 days: refresh the feeds in My Feeds)"


def build(brand, week):
    root = repo()
    a = dt.date.fromisoformat(week)
    b = a + dt.timedelta(days=6)
    dated, seasons = moments(root, brand, a, b)
    text = PROMPT.read_text()
    filled = text.format(brand=brand, avatars=avatars(root, brand),
                         week=f"{a.isoformat()} (Monday) to {b.isoformat()} (Sunday)",
                         dated=dated, seasons=seasons, emails=emails(root, brand, a, b), feeds=feeds(root, brand, a))
    out = root / "runs" / "culture-weekly" / brand / a.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    (out / "prompt-as-sent.md").write_text(filled)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--week", help="the Monday the week starts (default: next Monday)")
    a = ap.parse_args()
    wk = a.week or next_monday().isoformat()
    if dt.date.fromisoformat(wk).weekday() != 0:
        raise SystemExit(f"--week must be a Monday: {wk}")
    print(build(a.brand, wk) / "prompt-as-sent.md")


if __name__ == "__main__":
    main()
