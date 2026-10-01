#!/usr/bin/env python3
"""
chain.py — THE BRIEF-BUILDING CHAIN, read off the brief itself.

This chain has one job: turn a brief into every asset the brief asks for. It
ENDS AT THE OFFER CARDS.

    brief → cast → openings → A-roll → B-roll → offer cards → editor

Captions, the cut and delivery are NOT stages here. They belong to the
editor's chain, downstream, and putting them on this board only made it look
like this chain was failing at work it was never responsible for (Damon,
2026-09-13).

What the editor DOES need from here is control: when a take is wrong he
re-rolls it from the brief itself, on the card that holds it, so the
correction lands against the thing that specified it and no slop survives the
handoff. That is what the change note and the version history on every card
are for.

    python3 chain.py <run>          print the chain and its gates

THE RULE. A stage is not "done" because someone made something; it is done
when the brief's own count is met. The brief asks for six openings, thirty-
three caption lines and three offer cards. All three went missing for a week
and nobody noticed, because the board could only show what HAD been made and
had no idea what had been ASKED FOR.

So every stage carries two numbers — what the brief wants and what is on disk
— and the gate is the comparison. The brief is the only source for the first
number; it is parsed here, never retyped, so it cannot drift from the file the
writing stages actually produced.

DELIBERATE OVERRIDES ARE DECLARED, NOT HIDDEN. Where a call was made to
depart from the brief — the thirty-three scenes consolidated to eight talking
beats — the plan records it in `overrides` with the reason, and the stage
shows the brief's number, the agreed number, and why. A gap you decided on is
a decision; a gap nobody mentions is a mistake.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DONE, GAP, OVER = "done", "gap", "override"


def _brief(run: Path) -> str:
    """The brief, wherever the run keeps it.

    assets/ first — that is where the lane files its input, mirroring the
    image lane — then the run root, for runs made before the move.
    """
    for n in ("assets/brief-final.md", "assets/brief.md",
              "brief-final.md", "brief.md"):
        f = run / n
        if f.exists():
            return f.read_text()
    return ""


def _n(pat: str, t: str) -> int:
    return len(re.findall(pat, t, re.M))


def _files(run: Path, sub: str) -> int:
    """Count the clips in a run folder, wherever that folder sits.

    finals/ holds what ships, iterations/ holds working takes — so a name is
    looked for in both rather than each caller knowing which.
    """
    for parent in ("rushes", "iterations", "out", ""):
        d = run / parent / sub if parent else run / sub
        if d.is_dir():
            return len(list(d.glob("*.mp4")))
    return 0


def read(run: Path) -> list[dict]:
    t = _brief(run)
    pp = run / "out" / "plan.json"
    plan = json.loads(pp.read_text()) if pp.exists() else {}
    ov = plan.get("overrides", {})
    scenes = plan.get("scenes", [])
    cuts = [c for c in plan.get("cutaways", []) if not c.get("dropped")]
    dropped = [c for c in plan.get("cutaways", []) if c.get("dropped")]

    PROMPT = {
        "readbrief": "stage-0-read-brief/stage0-read-brief-v1-damon.md",
        "openings": "stage-1-openings/stage1-openings-v1-damon.md",
        "aroll": "stage-2-aroll/stage2-aroll-v2-damon.md",
        "broll": "stage-3-broll/stage3-broll-v1-damon.md",
        "offer": "stage-4-offer/stage4-offer-v2-damon.md",
    }

    def stage(key, name, why, want, got, detail=""):
        o = ov.get(key)
        if o:
            want_eff = o.get("agreed", want)
            state = OVER if got >= want_eff else GAP
            detail = o.get("why", "") or detail
        else:
            want_eff, state = want, (DONE if got >= want and want else
                                     GAP if want else DONE)
        return dict(key=key, name=name, why=why, brief=want, agreed=want_eff,
                    built=got, state=state, detail=detail,
                    prompt=PROMPT.get(key))

    voiced = _files(run, "clips")
    return [
        stage("brief", "The brief", "the spec every other stage answers to",
              1, 1 if t else 0,
              f"{_n(r'^\*\*Scene ', t)} scenes · {_n(r'^\*\*Opening ', t)} openings"),
        stage("readbrief", "Read the brief",
              "every item the brief asks for becomes a row — all of them",
              _n(r"^\*\*Opening \d+", t) + _n(r"^\*\*Scene ", t),
              len(plan.get("openings", [])) + len(scenes) +
              len(plan.get("cutaways", [])) + len(plan.get("offer", [])),
              "the plan was built from old working files, not from this"),
        stage("cast", "The cast", "banked elements, so nothing is described twice",
              len(plan.get("cast", {}).get("elements", [])) or 4,
              len(plan.get("cast", {}).get("elements", [])) +
              len(plan.get("cast", {}).get("also", []))),
        stage("openings", "The openings",
              "one hook each — a tested body can carry a dozen fronts",
              _n(r"^\*\*Opening \d+", t), _files(run, "openings")),
        stage("aroll", "The A-roll", "the talking spine, generated then revoiced",
              _n(r"TYPE A", t), voiced),
        stage("broll", "The B-roll", "inserts laid over the take they cover",
              _n(r"TYPE B", t), len([c for c in cuts
                                     if (run / "rushes" / "broll" /
                                         f"{c['id']}.mp4").exists()]),
              f"{len(dropped)} dropped" if dropped else ""),
        stage("offer", "The offer cards",
              "price and guarantee ON SCREEN, not only spoken",
              _n(r"TYPE C", t), _files(run, "offer")),
    ]


def handoff(run: Path) -> dict:
    """What goes downstream, and what the editor owns.

    Not a stage. The editor's chain starts here — captions, the cut, the
    grade, delivery — and it is listed so the boundary is explicit rather
    than simply missing from the page.
    """
    rows = read(run)
    gaps = [r for r in rows if r["state"] == GAP]
    return dict(ready=not gaps, gaps=[r["name"] for r in gaps],
                owns=["captions — the brief writes an exact line per scene",
                      "the cut — spine and inserts assembled",
                      "the grade and the sound bed",
                      "delivery to Drive"],
                control=("Every take is re-rollable from the card that holds "
                         "it: write what is wrong in plain words, press "
                         "Regenerate, and the note is kept against the take it "
                         "replaced."))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = Path(sys.argv[1]).expanduser().resolve()
    mark = {DONE: "done", GAP: "GAP", OVER: "agreed"}
    print(f"\n  {'stage':16} {'brief':>6} {'built':>6}  state")
    print("  " + "-" * 62)
    for s in read(run):
        n = (f"{s['brief']}" if s["agreed"] == s["brief"]
             else f"{s['brief']}→{s['agreed']}")
        print(f"  {s['name']:16} {n:>6} {s['built']:>6}  {mark[s['state']]:8}"
              f" {s['detail'][:28]}")
    gaps = [s for s in read(run) if s["state"] == GAP]
    print(f"\n  {len(gaps)} gap(s): " + ", ".join(s["name"] for s in gaps) + "\n")


if __name__ == "__main__":
    main()
