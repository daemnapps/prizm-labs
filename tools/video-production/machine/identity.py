"""THE FACE CHECK — every person in a made picture is the person in their
reference, checked after every picture, before anything is built on it
(the owner, 2026-10-02: "we literally are always supposed to use references of our
created person, why is this happening?? FIX THIS!").

    check(picture, masters) -> [{"master": path, "verdict": "SAME"|"DIFFERENT"|"UNCHECKED", "why": …}]

Each master is asked three times and the majority wins (a single ask flips on
small details — element_match learned it the same day). A picture with any
DIFFERENT is made again by the caller (run.py), twice at most; still different,
it is HELD and named, never passed on. Brand-agnostic: masters are whatever
casting references the picture was made from.
"""
from __future__ import annotations

import importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]


def _rule(name: str) -> str:
    """The words sent live in model-inputs.json frame_rules (rendered in MODEL-INPUTS.md)."""
    return ((json.loads((HERE / "model-inputs.json").read_text()).get("frame_rules") or {}).get(name) or {}).get("says", "")

Q = _rule("face_check")


def _review():
    sp = importlib.util.spec_from_file_location("qc_review", WS / "components/quality-checks/marketing_chain_checks/review.py")
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def check(picture, masters, caller=None, votes: int = 3) -> list[dict]:
    rv = _review()
    out = []
    for mp in masters:
        answers = []
        for _ in range(votes):
            try:
                a = rv.ask([{"text": Q}, rv._part(mp), rv._part(picture)], caller=caller)
                answers.append((a.get("verdict") or "").upper())
                why = a.get("why", "")
            except Exception as e:
                answers.append("UNCHECKED"); why = f"{type(e).__name__}"
        top = max(set(answers), key=answers.count)
        out.append({"master": str(mp), "verdict": top, "votes": answers, "why": why})
    return out


def masters_of(medias) -> list[str]:
    return [str(m.get("value")) for m in medias or []
            if "/casting/" in str(m.get("value")) and str(m.get("value")).endswith("master.png")]


if __name__ == "__main__":
    pic, *ms = sys.argv[1:]
    print(json.dumps(check(pic, ms), indent=1))
