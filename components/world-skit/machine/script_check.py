#!/usr/bin/env python3
"""script_check.py: the skit rules as a check a machine can run. A script (lines + beats) in, a list of faults out.

    python3 script_check.py <video-edit run> [--problem "razor bump,bumps" --place neck]

Reads the run's lines.json, plan.json and ad.json. Exit 0 clean, 1 faults. Spends nothing."""
import argparse
import json
import re
import sys
from pathlib import Path

DR = ("product", "mechanism", "demo", "proof", "after", "objection", "offer", "ask")
AD_WORDS = re.compile(r"\b(when|your|you|get|try|shop|buy|finally|stop|best|new|free|save|won't quit)\b", re.I)
PRINT = re.compile(r"results? (may )?vary|terms apply|real customer", re.I)


def faults(run, problem, place):
    run = Path(run)
    ad = json.loads((run / "ad.json").read_text())
    lines = json.loads((run / "lines.json").read_text())
    who = {s["id"]: s["speaker"] for s in json.loads((run / "plan.json").read_text())["scenes"]}
    order = [r["id"] for r in ad["timeline"] if r["id"] in lines]
    out = []
    streak, last = 0, None
    for i in order:
        n = len(lines[i].split())
        streak = streak + n if who.get(i) == last else n
        last = who.get(i)
        if streak > 26:
            out.append("monologue: %s runs %d words in a row at %s" % (last, streak, i))
    early = " ".join(lines[i] for i in order[:max(6, len(order) // 8)]).lower()
    if problem and not any(w.strip() in early for w in problem.split(",")):
        out.append("the problem is not said out loud early")
    if place and place not in early:
        out.append("where the problem lives is not said out loud early")
    run_len, scene, worst = 0, None, 0
    for b in ad["beats"]:       # the skit half: from the product on, the sections set the pace
        key = "yard" if b.get("dreDown") or b.get("dreFly") else b.get("scene")
        if key == "prodw":
            break
        run_len = run_len + 1 if key == scene else 1
        scene = key
        worst = max(worst, run_len)
    if worst > 16:
        out.append("%d beats in a row in one place: needs a cutaway" % worst)
    head = ad.get("headline", "")
    if head != head.lower():
        out.append("top text is in capitals: it reads like an ad")
    if AD_WORDS.search(head):
        out.append("top text reads like an ad: %s" % head)
    if PRINT.search(json.dumps(ad.get("small_print", []))) or PRINT.search(json.dumps([b.get("quote", "") for b in ad["beats"]])):
        out.append("on-screen disclaimer present")
    marks = ad.get("dr_marks", {})
    seen = [m for m in DR if m in marks]
    if marks and seen != list(DR):
        out.append("direct response sections missing: %s" % ", ".join(m for m in DR if m not in marks))
    first = ad["timeline"][0]
    if first.get("hold", 0) < 1.5:
        out.append("opening is under 1.5 seconds")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--problem", default="")
    ap.add_argument("--place", default="")
    a = ap.parse_args()
    f = faults(a.run, a.problem, a.place)
    for x in f:
        print("FAULT", x)
    print("%d fault(s)" % len(f))
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
