#!/usr/bin/env python3
"""lane — how the whole ad is made, decided by rule with its reason (the logic layer, 2026-11-18).

    python3 machine/lane.py <writing run folder>            # the call for a brief, as JSON
    python3 machine/lane.py --production <brief.json>       # the lane an existing production runs in

A production is made one of four ways (machine/lanes.json `lanes`): ai (every shot made), mix (our footage where the
footage decision passed the shot, AI for the rest), real (our own footage on every shot), creator (a creator films it).

Until this file nothing decided it. The Produce button sent "ai" when nobody chose, and two readers of one production
disagreed about a production that carried no lane: the hand-off pack and Produce read "ai", the next-step tools read
"real". 12 of 15 productions on file carried none.

    default(fmt, route, footage, style)   the lane for a NEW production nobody picked a lane for, with the reason:
        1. the maker route says a creator films it            -> creator
        2. the format is made one way by its own definition   -> that lane (lanes.json `by_format`)
        3. the style is not filmed footage (drawn, rendered)  -> ai: our filmed clips are not in that look
        4. else the footage decision (storyboard-footage.json, footage.py): no shot passed -> ai; every shot passed
           and nobody talks to camera -> real; some passed -> mix. No footage decision on file -> ai, said as such.
    for_writing(run_dir)                  the same call, reading the writing run's own record
    of(brief)                             the lane an EXISTING production runs in: the one recorded on it, else the
                                          one answer for an older production (lanes.json `older_production`)
    label(lane)                           the lane's words for a page

Every reader asks here: the Studio's Produce and next-step tools, the production seed, the editor hand-off pack. A
person's pick at Produce always wins and is recorded as theirs (`lane_by`); the Studio shows the call and its reason.

Brand-agnostic: nothing here names a brand, a product or a person.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BY = "the chain: format, route and the footage decision"
PICKED = "a person at Produce"


def settings() -> dict:
    return json.loads((HERE / "lanes.json").read_text())


def lanes() -> tuple:
    return tuple(settings()["lanes"])


def label(lane: str | None) -> str:
    return settings()["lanes"].get(lane or "", str(lane or ""))


def _read(p):
    try:
        d = json.loads(Path(p).read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def footage_counts(doc: dict | None) -> dict | None:
    """What the footage decision passed, counted off its own record (storyboard-footage.json): shots cut from our
    footage, shots to make, scenes where someone talks to camera (never the library's), scenes made another way.
    None when the decision has not run."""
    rows = (doc or {}).get("scenes")
    if not isinstance(rows, dict) or not rows:
        return None
    plan = [str((v or {}).get("plan") or "") for v in rows.values() if isinstance(v, dict)]
    return {"cut": plan.count("cut"), "make": plan.count("generate"), "presenter": plan.count("presenter"),
            "other": sum(1 for p in plan if p not in ("cut", "generate", "presenter"))}


def settled(fmt: str | None = None, route: str | None = None, style: str | None = None) -> dict | None:
    """The lane when it is decided BEFORE any footage is looked at (rules 1-3 of default: a creator route, a format
    made one way, a style our filmed footage is not in), else None — then the footage decision decides. The writing
    chain asks this before its storyboard footage pass: a settled ai or creator lane never searches our archive
    (2026-11-19, the owner, on a 3D-animated brief that came back with our creator clips on every shot)."""
    S = settings()
    inputs = {"format": fmt or None, "route": route or None, "style": style or None, "footage": None}

    def call(lane, why):
        return {"lane": lane, "why": why, "by": BY, "inputs": inputs}

    if str(route or "").strip().lower() == "creator":
        return call("creator", "the maker route for this piece is a creator: a person films it, so nothing is made here")
    pin = (S.get("by_format") or {}).get(fmt or "")
    if isinstance(pin, dict) and pin.get("lane") in S["lanes"]:
        return call(pin["lane"], f"the {fmt} format is {pin.get('why') or 'made this way by its own definition'}")
    filmed = set((S.get("filmed_styles") or {}).get("ids") or [])
    if style and style not in filmed:
        return call("ai", f"the ad is made in the {style} style: our filmed footage is not in that look, so every shot is made")
    return None


def default(fmt: str | None = None, route: str | None = None, footage: dict | None = None,
            style: str | None = None) -> dict:
    """The lane for a new production nobody picked one for. -> {"lane", "why", "by", "inputs"}."""
    S = settings()
    n = footage_counts(footage) if footage and "scenes" in footage else footage     # the decision's own record, or counts
    inputs = {"format": fmt or None, "route": route or None, "style": style or None, "footage": n or None}

    def call(lane, why):
        return {"lane": lane, "why": why, "by": BY, "inputs": inputs}

    first = settled(fmt, route, style)
    if first:
        return dict(first, inputs=inputs)
    if not n:
        return call("ai", "no footage decision is on file for this brief yet, so nothing says a shot is covered by "
                          "footage we own: every shot is made")
    shots = n["cut"] + n["make"]
    if not n["cut"]:
        return call("ai", (f"the footage decision passed none of the {shots} shot(s) it looked at" if shots else
                           "the brief has no shot footage could stand in for") + ": every shot is made")
    if not n["make"] and not n["presenter"]:
        return call("real", f"the footage decision passed all {n['cut']} shot(s): each is cut from clean footage we own "
                            "and nothing needs making")
    rest = []
    if n["make"]:
        rest.append(f"{n['make']} {'is' if n['make'] == 1 else 'are'} made")
    if n["presenter"]:
        rest.append(f"{n['presenter']} {'talks' if n['presenter'] == 1 else 'talk'} to camera, and the presenter is "
                    "never the library's")
    return call("mix", f"the footage decision passed {n['cut']} of {shots} shot(s): those are cut from clean footage we "
                       f"own; {' and '.join(rest)}")


def for_writing(run_dir) -> dict:
    """The call for a brief, read off its writing run: the format and the maker route on run.json, the style, and the
    storyboard's footage decision beside the brief."""
    w = Path(run_dir)
    rj = _read(w / "run.json")
    fd = _read(w / "stages" / "storyboard-footage.json")
    return default(rj.get("format_id") or rj.get("format"), rj.get("production_route"),
                   fd if fd.get("scenes") else None, rj.get("style_id"))


def of(brief: dict | None) -> dict:
    """The lane an existing production runs in. -> {"lane", "why", "by"}. A lane recorded on the production stands,
    with whoever chose it; a production saved before lanes were recorded gets the one answer every reader shares."""
    b = brief or {}
    if b.get("lane") in lanes():
        return {"lane": b["lane"], "why": b.get("lane_why") or "picked at Produce",
                "by": b.get("lane_by") or PICKED}
    old = settings()["older_production"]
    return {"lane": old["lane"], "why": old["why"], "by": "the chain: an older production"}


def chosen(picked: str | None, run_dir=None) -> dict:
    """What a new production is seeded with: a person's pick at Produce when there is one (recorded as theirs, with the
    chain's own call beside it when it differs), else the chain's call."""
    call = for_writing(run_dir) if run_dir else default()
    if picked in lanes():
        out = {"lane": picked, "why": "picked at Produce", "by": PICKED}
        if call["lane"] != picked:
            out["chain_call"] = {"lane": call["lane"], "why": call["why"]}
        return out
    return {k: call[k] for k in ("lane", "why", "by")}


def main(argv=None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    if not a:
        print(__doc__)
        return 2
    if a[0] == "--production":
        print(json.dumps(of(_read(a[1])), indent=1, ensure_ascii=False))
        return 0
    print(json.dumps(for_writing(a[0]), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
