#!/usr/bin/env python3
"""messages: from ad analysis to the next brief, one path for every winner. Reached as `winners.py messages <do>`.

    status   every winner through the same gates, what is stuck and on what
    next     what to brief next, best first, with the command that starts it; then what to tear down first
    check    exit 1 when a winner is ungrouped, or a group or rule read is not whole
    page     the owner's page and its Markdown copy (runs/winners/<brand>/messages/page.html, .md)
    start <run>   the command that writes a creator brief from one winner

THE GATES, in order. A winner is briefed only when it has passed all of them:
  proof      it is in the winner index with sales, and its retire call is keep or watch
  teardown   triage, teardown, transcript, culture, persuasion read and spec are on its run
  message    its teardown wrote THE CORE MESSAGE, its beliefs, delivery and angle; its spec says what is load-bearing
  group      it sits under one of the brand's core messages (messages.json). Grouped on the core message line alone,
             never on a caption tag, a hook or a reading of the script. A new group needs the owner's yes.
  rules      what the brand's rules cut from its load-bearing list is written down: carries whole, swap or breaks

The record, runs/winners/<brand>/messages/messages.json, holds only what a person decides:
  {"messages": [{id, message, state, winners: [{run, carries, cut: [], fill: [], briefs: []}]}], "parked": [{run, why}]}
Everything else is read from runs/winners/<brand>/winner-index.json (its `message_read`, as the run wrote it). Ranking in
`next`: no brief yet; whole before swap; breaks never; then sales. Offline, stdlib only, no model, no spend."""
import argparse, base64, html, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit import paths  # noqa: E402
CARRIES = ("whole", "swap", "breaks")
GATES = ("proof", "teardown", "message", "group", "rules")


def home(root, brand):
    return root / "runs/winners" / brand / "messages"


def load(root, brand):
    p = home(root, brand) / "messages.json"
    return json.loads(p.read_text()) if p.is_file() else {"messages": [], "parked": []}


def index(root, brand):
    p = root / "runs/winners" / brand / "winner-index.json"
    rows = json.loads(p.read_text())["winners"] if p.is_file() else []
    return [w for w in rows if not w.get("copy_of") and (w.get("retire") or {}).get("call") not in ("fold", "retire")]


def placed(d):
    return {w["run"]: (m, w) for m in d["messages"] for w in m.get("winners") or []}


def walk(root, brand):
    """One row per winner: its numbers, its message and the first gate it is stuck at (None = ready to brief)."""
    d = load(root, brand)
    at, parked, out = placed(d), {x["run"]: x["why"] for x in d.get("parked") or []}, []
    for w in index(root, brand):
        p, mr, run = w.get("proof") or {}, w.get("message_read") or {}, w.get("run")
        m, g = at.get(run, (None, None))
        miss = [x for x in (w.get("teardown") or {}).get("missing") or [] if x != "core message"]
        whole = all(mr.get(k) for k in ("core", "beliefs", "delivery", "angle", "load_bearing"))
        stuck = ("proof" if not p.get("purchases") else "teardown" if not run or miss else "message" if not whole else
                 "parked" if run in parked else "group" if not g else
                 "rules" if g.get("carries") not in CARRIES or (g["carries"] != "whole" and not g.get("cut")) else None)
        out.append({"run": run, "label": w["label"], "sales": p.get("purchases") or 0, "cpa": p.get("cpa"),
                    "spend": p.get("spend") or (p.get("purchases") or 0) * (p.get("cpa") or 0), "watch": w.get("watch"), "read": mr,
                    "message": m, "group": g, "stuck": stuck, "why": ", ".join(miss) if stuck == "teardown" else parked.get(run, "")})
    return out


def check(root, brand):
    d, rows, seen, bad = load(root, brand), walk(root, brand), set(), []
    known = {r["run"] for r in rows if r["run"]}
    for m in d["messages"]:
        if m.get("state") not in ("draft", "approved", "deprecated"):
            bad.append("%s: state is not draft, approved or deprecated" % m.get("id"))
        for w in m.get("winners") or []:
            if w["run"] in seen:
                bad.append("%s: grouped twice" % w["run"])
            seen.add(w["run"])
            if w["run"] not in known:
                bad.append("%s: not a winner in the index" % w["run"])
    bad += ["%s: stuck at %s%s" % (r["label"], r["stuck"], " (%s)" % r["why"] if r["why"] else "") for r in rows
            if r["stuck"] in ("message", "group", "rules")]
    return bad


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def untorn(root, brand, rows):
    """Proven videos of the widest audit that no winner in the index stands for: matched on the post link, the name, then the total."""
    boards = sorted((root / "runs/winners" / brand / "audit").glob("*/board.json"), key=lambda p: p.parent.name)
    if not boards:
        return []
    links = {r["watch"] for r in rows if r["watch"]}
    idx = json.loads((root / "runs/winners" / brand / "winner-index.json").read_text())["winners"]
    links |= {w.get("watch") for w in idx if w.get("watch")} | {(w.get("traits") or {}).get("post_url") for w in idx}
    names = {norm(re.sub(r"^.*· ", "", w["label"])) for w in idx} - {""}
    sold = {(w.get("proof") or {}).get("purchases") for w in idx} - {None, 0}      # the same total is the same ad under another name
    out = []
    for x in json.loads(boards[0].read_text()):
        n = norm(x["name"])
        if x.get("format") != "Video" or (x.get("link") and x["link"] in links) or any(len(k) > 4 and k in n for k in names) \
                or (x["purchases"] >= 100 and x["purchases"] in sold):
            continue
        out.append({"label": x["name"], "sales": x["purchases"], "cpa": x["cpa"], "watch": x.get("link"), "why": x.get("screen") or ""})
    return sorted(out, key=lambda x: -x["sales"])


def ready(rows):
    r = [x for x in rows if x["stuck"] is None and x["group"]["carries"] != "breaks" and not x["group"].get("briefs")]
    return sorted(r, key=lambda x: (CARRIES.index(x["group"]["carries"]), -x["sales"]))


def to_tear(rows):
    return sorted([x for x in rows if x["stuck"] in ("teardown", "message")], key=lambda x: -x["sales"])


def start(run, brand):
    return ("python3 components/video-teardown/machine/line.py creator --label <brief label> --brand %s "
            "--writing-lane winner --winner %s" % (brand, run))


def line(x):
    return "%s · %s sales at $%.0f" % (x["label"], format(x["sales"], ","), x["cpa"] or 0)


def show_status(root, brand):
    rows, out = walk(root, brand), []
    for g in GATES + ("parked",):
        s = [r for r in rows if r["stuck"] == g]
        if s:
            out += ["stuck at %s: %d" % (g, len(s))] + ["  " + line(x) + (" (%s)" % x["why"] if x["why"] else "") for x in s]
            if g == "group":
                out += ["    core message: " + x["read"]["core"] for x in s]
    ok = [r for r in rows if r["stuck"] is None]
    return out + ["through every gate: %d of %d" % (len(ok), len(rows))]


def show_next(root, brand, n=10):
    rows = walk(root, brand)
    out = ["brief next:"]
    for x in ready(rows)[:n]:
        out += ["  %s · %s · %s" % (line(x), x["group"]["carries"], x["message"]["message"])]
    t = to_tear(rows) + [dict(x, stuck="teardown") for x in untorn(root, brand, rows)]
    if t:
        out += ["tear down first (spends, on the owner's go):"] + ["  %s (%s)" % (line(x), x["why"] or x["stuck"]) for x in t[:n]]
    return out


# ---------- the owner's page ----------
CSS = (HERE / "messages_page.css")


def page(root, brand):
    e, rows = html.escape, walk(root, brand)
    def pic(run):
        for n in ("poster-small.jpg", "poster.jpg"):
            p = root / "runs/video-teardown/_work" / str(run) / n
            if p.is_file() and p.stat().st_size < 400000:
                return '<img src="data:image/jpeg;base64,%s" alt="">' % base64.b64encode(p.read_bytes()).decode()
        return ""
    def ul(xs, cls=""):
        return "<ul>" + "".join("<li%s>%s</li>" % (cls, e(x)) for x in xs) + "</ul>"
    tag = {"whole": ("ok", "Carries whole"), "swap": ("half", "Refill"), "breaks": ("bad", "Breaks")}
    def card(x):
        g, r = x["group"], x["read"]
        c, t = tag[g["carries"]]
        chips = "".join('<li class="cut">%s</li>' % e(y) for y in g.get("cut") or []) + "".join('<li class="fill">%s</li>' % e(y) for y in g.get("fill") or [])
        br = "".join('<span class="br">%s</span>' % e(b) for b in g.get("briefs") or []) or '<span class="br none">No brief</span>'
        w = ' <a href="%s">Watch</a>' % e(x["watch"]) if x["watch"] else ""
        return ('<article class="row %s">%s<div class="bd"><div class="hd"><h3>%s</h3><span class="st">%s</span></div><div class="nm"><b>%s</b> sales <b>$%.0f</b> each%s</div>'
                '<div class="why">%s</div>%s<div>%s</div><details><summary>What must stay</summary>%s<h4>Beliefs</h4>%s<h4>Delivery</h4>%s<h4>Free to change</h4>%s<h4>Desire</h4>%s</details></div></article>'
                % (c, pic(x["run"]), e(x["label"]), t, format(x["sales"], ","), x["cpa"] or 0, w, e(r["core"]),
                   '<ol class="chips">%s</ol>' % chips if chips else "", br, ul(r["load_bearing"]), ul(r["beliefs"]), e(r["delivery"]), ul(r["angle"]), e(r["desire"])))
    nx, tr, d = ready(rows), to_tear(rows) + untorn(root, brand, rows), load(root, brand)
    ok = [r for r in rows if r["stuck"] is None]
    tops = [("Brief next", nx[0]["label"].split(" · ")[-1] if nx else "Nothing waiting", line(nx[0]).split(" · ")[-1] if nx else ""),
            ("Through every gate", "%d of %d" % (len(ok), len(rows)), "proof, teardown, message, group, rules"),
            ("Tear down next", tr[0]["label"].split(" · ")[-1] if tr else "None", line(tr[0]).split(" · ")[-1] if tr else "every winner is torn down")]
    body = '<div class="top">' + "".join('<div class="t"><span>%s</span><b>%s</b><small>%s</small></div>' % tuple(map(e, t)) for t in tops) + "</div>"
    body += '<div class="flow">' + "<i>→</i>".join("<span><b>%d</b>%s</span>" % (sum(1 for r in rows if r["stuck"] is None or GATES.index("group" if r["stuck"] == "parked" else r["stuck"]) > i), g.title()) for i, g in enumerate(GATES)) + "<i>→</i><span><b>%d</b>Briefed</span></div>" % sum(1 for r in ok if r["group"].get("briefs"))
    mine = lambda m: [x for x in ok if x["message"]["id"] == m["id"]]
    ms = sorted(d["messages"], key=lambda m: (-sum(x["group"]["carries"] == "whole" for x in mine(m)), -sum(x["sales"] for x in mine(m))))
    for m in ms:
        xs = sorted([x for x in ok if x["message"]["id"] == m["id"]], key=lambda x: (CARRIES.index(x["group"]["carries"]), -x["sales"]))
        n, sp = sum(x["sales"] for x in xs), sum(x["spend"] for x in xs)
        body += '<h2>%s</h2><div class="nm"><b>%s</b> sales <b>$%.0f</b> each</div><div class="grid">%s</div>' % (e(m["message"]), format(n, ","), sp / n if n else 0, "".join(map(card, xs)))
    if tr:
        body += "<h2>Proven, not torn down <em>%d</em></h2>" % len(tr) + ul([line(x) for x in tr[:20]])
    stuck = [r for r in rows if r["stuck"]]
    if stuck:
        body += "<h2>Not through yet</h2>" + ul(["%s: %s%s" % (line(r), r["stuck"], " (%s)" % r["why"] if r["why"] else "") for r in stuck])
    name = brand.upper() + " Brief Gaps"
    extra = home(root, brand) / "brief.html"
    doc = ('<meta name="claude:viewport-fit-sides" content="cover"><title>%s</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;600;700&display=swap"><style>%s</style>'
           '<main><h1>%s</h1>%s%s</main>' % (name, CSS.read_text(), name, body if not extra.is_file() else body.replace('<h2>', extra.read_text() + '<h2>', 1), ""))
    h = home(root, brand)
    h.mkdir(parents=True, exist_ok=True)
    (h / "page.html").write_text(doc)
    md = ["# %s" % name, "", "Every winner through proof, teardown, message, group and rules. `winners.py messages status`.", "",
          "| Message | Winner | Sales | CPA | Carries | Cut | Briefs |", "|---|---|---|---|---|---|---|"]
    md += ["| %s | %s | %s | $%.0f | %s | %s | %s |" % (x["message"]["message"], x["label"], format(x["sales"], ","), x["cpa"] or 0, x["group"]["carries"],
           "; ".join(x["group"].get("cut") or []), ", ".join(x["group"].get("briefs") or [])) for x in ok]
    md += ["", "## Next", ""] + show_next(root, brand)
    (h / "page.md").write_text("\n".join(md) + "\n")
    return h / "page.html"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("do", choices=("status", "next", "check", "page", "start"))
    ap.add_argument("run", nargs="?")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=str(paths.repo(__file__)))
    a = ap.parse_intermixed_args(argv)
    root = Path(a.root)
    if a.do == "check":
        bad = check(root, a.brand)
        print("\n".join(bad) or "every winner with a teardown is grouped and read against the rules")
        return 1 if bad else 0
    if a.do == "page":
        print(page(root, a.brand).relative_to(root))
        return 0
    if a.do == "start":
        x = next((r for r in walk(root, a.brand) if r["run"] == a.run), None)
        if not x or x["stuck"] or x["group"]["carries"] == "breaks":
            print("%s is not ready: %s" % (a.run, "not a winner" if not x else x["stuck"] or "the rules cut what it stands on"))
            return 2
        print(start(a.run, a.brand))
        return 0
    print("\n".join(show_status(root, a.brand) if a.do == "status" else show_next(root, a.brand)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
