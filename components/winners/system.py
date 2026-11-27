#!/usr/bin/env python3
"""system: where one brand stands on every step of the winners process, from ad results to a brief, and the exact
next step on each. Reached as `winners.py system --brand <b>`. Any brand: the brand enters only as data.

Steps, in the order they run:
  results    the newest score (`score/<asof>/score.json`) and where its numbers came from
  audit      the widest audit window and how many of its creatives still wait for tags
  bank       rows, Core rows
  bar        the paid bar and the creator bar (the brand owner's; never set here)
  teardowns  Core rows with a finished teardown run tied to them in the winner index
  proof      winner-index records that reached the bank's sales (keep / watch)
  index      the winner index, and whether the bank changed after it was built
  messages   winners through every gate (proof, teardown, message, group, rules)
  shapes     winners with a story shape call; the shape build
  profiles   avatar profiles drafted and filed (creative-strategist)
  brief      winners ready to brief

Each step is `ready`, `owner` (only the brand owner can move it), `spend` (moving it costs money, on a person's go),
`todo` (a free step a person or a session runs), `stale` or `blocked` (an earlier step holds it). Reads files only:
no warehouse, no ad account, no model, no spend. Writes runs/winners/<brand>/system.json and system.md.

Results enter the process in one place (the score's results read, the audit's pull). A new results source, such as an
app connected to the ad account, replaces that read; every step below reads the bank and the score, so nothing here
changes.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component

import bank as B  # noqa: E402
import messages as MG  # noqa: E402
import shapes as SH  # noqa: E402

STALE_DAYS = 14
STATES = ("ready", "owner", "spend", "todo", "stale", "blocked")
W = "python3 components/winners/winners.py"
WI = "python3 components/video-writing/machine/winner_index.py"


def _json(p, empty=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return empty


def _age(day, today):
    try:
        return (today - dt.date.fromisoformat(str(day)[:10])).days
    except ValueError:
        return None


def step(sid, name, state, has, nxt="", why=""):
    assert state in STATES, state
    return {"step": sid, "name": name, "state": state, "has": has, "next": nxt, "why": why}


def build(root, brand, today=None):
    root, today = Path(root), today or dt.date.today()
    home = root / "runs" / "winners" / brand
    out = []

    # results
    scores = sorted(p.parent for p in (home / "score").glob("*/score.json"))
    if scores:
        sc = _json(scores[-1] / "score.json", {}) or {}
        age = _age(scores[-1].name, today)
        out.append(step("results", "Ad results", "ready" if age is not None and age <= STALE_DAYS else "stale",
                        "score %s (%s days), from %s" % (scores[-1].name, age, sc.get("results_from") or "?"),
                        "" if age is not None and age <= STALE_DAYS else "%s score --brand %s" % (W, brand)))
    else:
        out.append(step("results", "Ad results", "todo", "no score yet", "%s score --brand %s" % (W, brand)))

    # audit
    windows = []
    for f in sorted((home / "audit").glob("*/window.json")):
        w = _json(f, {}) or {}
        windows.append((str(w.get("since") or ""), str(w.get("until") or ""), f.parent))
    if windows:
        widest = max(windows, key=lambda x: (_span(x[0], x[1]), x[1]))
        left = len(_json(widest[2] / "to_tag.json", []) or []) if (widest[2] / "to_tag.json").is_file() else 0
        tags = _json(home / "tags.json", {}) or {}
        untagged = left if not tags else 0
        out.append(step("audit", "Audit + tags", "todo" if untagged else "ready",
                        "widest window %s" % widest[2].name + (", %d to tag" % untagged if untagged else ", tagged"),
                        "%s tag --brand %s --window %s --tags <file>" % (W, brand, widest[2].name) if untagged else ""))
    else:
        out.append(step("audit", "Audit + tags", "todo", "no audit yet",
                        "%s audit --brand %s --since <YYYY-MM-DD> --until <YYYY-MM-DD>" % (W, brand)))

    # bank and bar
    bank = B.load_bank(B.bank_path(root, brand), brand) if B.bank_path(root, brand).is_file() else None
    rows = (bank or {}).get("rows") or []
    core = [r for r in rows if r.get("core")]
    out.append(step("bank", "Bank", "ready" if rows else "blocked", "%d rows, %d Core" % (len(rows), len(core)),
                    "" if rows else "%s bank --brand %s" % (W, brand), "" if rows else "needs an audit"))
    if bank is None:
        out.append(step("bar", "Winner bar", "blocked", "no bank", "", "needs a bank"))
    else:
        paid_open = B.bar_is_open(bank)
        cb = bank.get("creator_bar") or {}
        cb_set = any(v is not None for v in cb.values())
        out.append(step("bar", "Winner bar", "owner" if paid_open else "ready",
                        "paid bar %s; creator bar %s" % ("open" if paid_open else "set", "set" if cb_set else "open"),
                        "%s bar --brand %s --min-spend N --max-cpa N --min-roas N" % (W, brand) if paid_open else "",
                        "the brand owner's call" if paid_open else ""))

    # winner index: teardowns, proof, freshness
    ixf = home / "winner-index.json"
    ix = _json(ixf, None)
    if ix is None:
        for sid, name in (("teardowns", "Core teardowns"), ("proof", "Proof")):
            out.append(step(sid, name, "todo", "no winner index", "%s build --brand %s" % (WI, brand)))
        out.append(step("index", "Winner index", "todo", "not built", "%s build --brand %s" % (WI, brand)))
    else:
        recs = ix.get("winners") or []
        tied = {r.get("bank_id") for r in recs if r.get("bank_id") and r.get("run") and (r.get("teardown") or {}).get("complete")}
        vids = [r for r in core if str(r.get("format") or "Video").lower() == "video"]
        torn = [r for r in vids if r.get("id") in tied]
        untorn = len(vids) - len(torn)
        images = len(core) - len(vids)
        out.append(step("teardowns", "Core teardowns", "spend" if untorn else "ready",
                        "%d of %d Core videos torn down" % (len(torn), len(vids)) +
                        (" (%d Core image ads: winners.py statics)" % images if images else "") +
                        ("; not tied: " + ", ".join(str(r.get("name"))[:40] for r in vids if r.get("id") not in tied)[:300]
                         if untorn else ""),
                        "%s videos --brand %s --window <window> --top %d, then the teardown" % (W, brand, len(core)) if untorn else "",
                        "untied rows may have a teardown under another name (tie it), else tearing down spends: a person's go"
                        if untorn else ""))
        live = [r for r in recs if not r.get("copy_of") and (r.get("retire") or {}).get("call") in ("keep", "watch")]
        noproof = [r for r in recs if r.get("run") and not r.get("copy_of") and not (r.get("proof") or {}).get("purchases")]
        out.append(step("proof", "Proof", "ready" if live else "blocked",
                        "%d winners with sales%s" % (len(live), ", %d runs with none" % len(noproof) if noproof else ""),
                        "" if live else "tie each Core teardown run to its bank row (registry or audit video)",
                        "" if live else "no run reached the bank's sales"))
        built = str(ix.get("built") or "")
        bank_day = dt.date.fromtimestamp(B.bank_path(root, brand).stat().st_mtime).isoformat() if bank is not None else ""
        fresh = built >= bank_day
        out.append(step("index", "Winner index", "ready" if fresh else "stale",
                        "built %s, %d records" % (built, len(recs)), "" if fresh else "%s build --brand %s" % (WI, brand),
                        "" if fresh else "the bank changed on %s" % bank_day))

    # messages
    walked = MG.walk(root, brand) if ix is not None else []
    through = [r for r in walked if r["stuck"] is None]
    stuck, parked = {}, 0
    for r in walked:
        if r["stuck"] == "parked":          # parked on purpose, with its reason in messages.json: a decision, not a gap
            parked += 1
        elif r["stuck"]:
            stuck[r["stuck"]] = stuck.get(r["stuck"], 0) + 1
    if not walked:
        out.append(step("messages", "Messages", "blocked", "0 winners", "", "needs proof"))
    else:
        first = next((g for g in MG.GATES + ("parked",) if g in stuck), None)
        out.append(step("messages", "Messages", "ready" if not stuck else ("owner" if first == "group" else "todo"),
                        "%d of %d through every gate" % (len(through), len(walked)) +
                        (", %d parked on purpose" % parked if parked else "") +
                        ("; stuck: " + ", ".join("%s %d" % kv for kv in sorted(stuck.items())) if stuck else ""),
                        "" if not stuck else "%s messages --brand %s status" % (W, brand),
                        "a new group needs the owner's yes" if first == "group" else ""))

    # shapes
    if ix is None or not walked:
        out.append(step("shapes", "Story shapes", "blocked", "0 winners", "", "needs proof"))
    else:
        uncalled = SH.todo(root, brand)
        built_shapes = (home / "shapes" / "shapes.json").is_file()
        state = "todo" if uncalled or not built_shapes else "ready"
        out.append(step("shapes", "Story shapes", state,
                        "%d uncalled; %s" % (len(uncalled), "built" if built_shapes else "not built"),
                        "%s shapes --brand %s todo" % (W, brand) if uncalled else
                        ("%s shapes --brand %s build" % (W, brand) if not built_shapes else "")))

    # profiles
    people = (_json(root / "runs" / "creative-strategist" / brand / "profiles" / "index.json", {}) or {}).get("people") or []
    filed = [p for p in people if "brand folder" in str(p.get("state") or "")]
    out.append(step("profiles", "Avatar profiles", "ready" if filed else ("owner" if people else "todo"),
                    "%d drafted, %d filed" % (len(people), len(filed)),
                    "python3 components/creative-strategist/machine/who.py build --brand %s --avatar <avatar>" % brand
                    if not people else "", "drafts wait for the owner's yes" if people and not filed else ""))

    # brief
    ok = MG.ready(walked) if walked else []
    out.append(step("brief", "Brief from a winner", "ready" if ok else "blocked",
                    "%d ready to brief" % len(ok), "%s messages --brand %s next" % (W, brand) if ok else "",
                    "" if ok else "an earlier step holds it"))

    return {"schema": "winners-system/1", "brand": brand, "made": today.isoformat(), "steps": out,
            "waiting_on_owner": [s for s in out if s["state"] == "owner"],
            "needs_spend": [s for s in out if s["state"] == "spend"]}


def _span(since, until):
    try:
        return (dt.date.fromisoformat(until) - dt.date.fromisoformat(since)).days
    except ValueError:
        return -1


MARK = {"ready": "✓", "owner": "● owner", "spend": "$ spend", "todo": "→ todo", "stale": "◐ stale", "blocked": "✗ blocked"}


def markdown(d):
    L = ["# %s — winners system" % d["brand"].upper(), "",
         "Made %s by `winners.py system --brand %s`. Files only; facts, no verdicts." % (d["made"], d["brand"]), "",
         "| step | state | has | next |", "|---|---|---|---|"]
    for s in d["steps"]:
        L.append("| %s | %s | %s | %s |" % (s["name"], MARK[s["state"]] + (" (%s)" % s["why"] if s["why"] else ""),
                                            s["has"], ("`%s`" % s["next"]) if s["next"] else "—"))
    return "\n".join(L) + "\n"


def write(root, brand):
    d = build(root, brand)
    home = Path(root) / "runs" / "winners" / brand
    home.mkdir(parents=True, exist_ok=True)
    (home / "system.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    (home / "system.md").write_text(markdown(d))
    return home / "system.md", d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=str(HERE.parents[1]))
    a = ap.parse_args(argv)
    p, d = write(a.root, a.brand)
    for s in d["steps"]:
        print("%-20s %-10s %s%s" % (s["name"], MARK[s["state"]], s["has"], ("  ->  " + s["next"]) if s["next"] else ""))
    print("->", p.relative_to(a.root) if Path(a.root) in p.parents else p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
