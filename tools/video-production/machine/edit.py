#!/usr/bin/env python3
"""
edit.py — a regen is an EDIT off the plate, never a fresh shot.

    python3 machine/edit.py <run> --scene 1 --change "she is front-on, not in profile"
    python3 machine/edit.py <run> --scene 1 --show     # the split and the last instruction

**Damon's ruling, frames-by-edit.md, 2026-09-02.** Measured on a real run:

    generate from a description        4,262 chars   wrong wardrobe, blended faces
    edit, but still describing it      766-1,133     composition better, caption wrong
    EDIT, DELTA ONLY                     204-386     scene held, wardrobe right, legible

The whole finding is one rule: **an edit instruction must never describe
anything the plate already shows.** Re-describing the room tells the model to
rebuild it, and rebuilding is the generation we are escaping.

Ignored on 2026-09-11: every regen that day was a fresh generation, so Nina
got a new room, a new pose and a new everything each time, and nothing stayed
consistent between takes. This exists so that cannot happen again.

## How an edit is built

Each scene carries a **keep/change split** — a written decision, not a guess:

    LOAD-BEARING   never changes. The identity, the product geometry, the
                   thing the beat is about.
    SWAPPABLE      may change. Framing, wardrobe register, room dressing.

The instruction then carries the delta and nothing else, and the plate rides
along as the reference. If the instruction runs past ~400 characters it has
started describing the scene again, and it says so rather than spending money.

Type is never generated. Captions and prices are layers over a clean plate,
so one plate carries every headline variation for free.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

DELTA_MIN, DELTA_MAX = 120, 400        # measured band, with a little headroom
MAX_CHANGES = 2                        # an edit moves one thing, two at a push

# Length was only ever the symptom. A 349-character instruction that changes
# the room, the wardrobe, the shelves, the light and adds a person is five
# edits wearing one sentence, and when it comes back wrong nothing says which
# of the five did it. Damon's rule, 2026-09-11: change one thing, and only one,
# so the next result answers a question.
import re as _re
_SPLIT = _re.compile(r",\s+|\band\b|\bthen\b|;\s*", _re.I)
_VERB = _re.compile(
    r"\b(is|are|make[s]?|move[s]?|change[s]?|put[s]?|add[s]?|remove[s]?|swap[s]?|"
    r"turn[s]?|face[s]?|hold[s]?|look[s]?|stand[s]?|sit[s]?|open[s]?|close[s]?|"
    r"lift[s]?|drop[s]?|bring[s]?|show[s]?|lose[s]?|keep[s]?)\b", _re.I)


def count_changes(change: str) -> int:
    """How many separate alterations this asks for."""
    parts = [p.strip() for p in _SPLIT.split(change) if p.strip()]
    return max(1, sum(1 for p in parts if _VERB.search(p) or len(p.split()) > 4))

# What is load-bearing is a property of the shot type, and these are the
# defaults a scene inherits until somebody writes a better split for it.
DEFAULT_SPLIT = {
    "A": {"keep": ["the presenter's identity and face",
                   "her wardrobe and the bracelets on her left wrist",
                   "the room she is standing in"],
          "change": ["framing", "where she is looking", "her gesture"]},
    "B": {"keep": ["the product's exact geometry",
                   "whose hands and whose skin",
                   "what the beat is demonstrating"],
          "change": ["framing", "light", "room dressing behind"]},
    "C": {"keep": ["the product's exact geometry and finish",
                   "that its surface carries no rendered lettering"],
          "change": ["angle", "light", "surface it stands on"]},
}


def board(run: Path) -> dict:
    return json.loads((run / "storyboard.json").read_text())


def save(run: Path, b: dict) -> None:
    (run / "storyboard.json").write_text(json.dumps(b, indent=1))


def scene(b: dict, n: int) -> dict:
    s = next((x for x in b["scenes"] if x["n"] == n), None)
    if s is None:
        raise SystemExit(f"no scene {n} in this run")
    return s


def split_for(s: dict) -> dict:
    return s.get("split") or DEFAULT_SPLIT[s["type"]]


# Banked assets that must never be re-described, only referenced.
ASSETS = {
    "flex": "8fad5612-d46f-4c19-baec-c3a636f22a4e",
    "brush": "8fad5612-d46f-4c19-baec-c3a636f22a4e",
    "device": "8fad5612-d46f-4c19-baec-c3a636f22a4e",
    "nina": "4157e549-dd65-450e-995d-cc50e369d107",
}


def assets_in(text: str) -> list[str]:
    """Which banked elements this edit touches."""
    found, seen = [], set()
    for word, eid in ASSETS.items():
        if eid in seen:
            continue
        if _re.search(rf"\b{word}\b", text, _re.I):
            found.append(eid); seen.add(eid)
    return found


def instruction(s: dict, change: str) -> str:
    """The delta, and only the delta — with any banked asset it touches.

    An edit off the plate alone re-derives whatever the plate got wrong. A
    brush face that came back as coarse ridges stays coarse ridges, because
    the only picture in the room still shows ridges. When the change is ABOUT
    a banked thing, the bank comes too (2026-09-11 — Damon: "you should be
    using the actual flex model in higgsfield").
    """
    sp = split_for(s)
    keep = "; ".join(sp["keep"])
    text = (f"Keep the reference image exactly as it is — {keep} — and change "
            f"only this: {change.strip().rstrip('.')}.")
    for eid in assets_in(change):
        text += f" The {'' if False else ''}<<<{eid}>>> is reproduced exactly from its own reference."
    return text


def edit(run: Path, n: int, change: str, dry: bool = False) -> dict:
    b = board(run)
    s = scene(b, n)
    takes = s.get("takes") or []
    if not takes:
        raise SystemExit(f"scene {n} has no plate to edit — generate one first")
    base = takes[s.get("chosen", 0)]
    if not base.get("job_id"):
        raise SystemExit(
            f"scene {n}'s plate has no job id recorded, so it cannot be used as "
            f"a reference. Regenerate it once through the chain and the id is kept.")

    text = instruction(s, change)
    moves = count_changes(change)
    note = None
    if moves > MAX_CHANGES:
        note = (f"this asks for {moves} changes at once. An edit moves one thing "
                f"so the next plate answers a question — run them one at a time, "
                f"starting with whichever is most wrong.")
    elif len(text) > DELTA_MAX:
        note = (f"instruction is {len(text)} chars, past the {DELTA_MAX} band — "
                "it has started describing the scene again. Narrow the change.")
    req = {"scene": n, "asked": change, "instruction": text,
           "chars": len(text), "changes": moves, "reference_job": base["job_id"],
           "keep": split_for(s)["keep"], "at": datetime.now().isoformat(timespec="seconds")}
    if note:
        req["refused"] = note

    s.setdefault("edits", []).append(req)
    if not dry:
        b.setdefault("queue", [])
        b["queue"] = [q for q in b["queue"] if q.get("n") != n]
        if not note:
            b["queue"].append({"n": n, "kind": "edit", **req})
            s["status"] = "queued"
    save(run, b)
    return req


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--scene", type=int, required=True)
    ap.add_argument("--change")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    run = a.run.expanduser().resolve()

    if a.show:
        s = scene(board(run), a.scene)
        sp = split_for(s)
        print(f"scene {s['n']} · TYPE {s['type']}\n")
        print("  LOAD-BEARING (never changes)")
        for k in sp["keep"]:
            print(f"    · {k}")
        print("  SWAPPABLE")
        for c in sp["change"]:
            print(f"    · {c}")
        for e in s.get("edits", []):
            flag = "  REFUSED" if e.get("refused") else ""
            print(f"\n  {e['at']}  {e['chars']} chars{flag}\n    asked: {e['asked']}")
            if e.get("refused"):
                print(f"    {e['refused']}")
        return

    if not a.change:
        raise SystemExit("--change is what you want different. Nothing else.")
    r = edit(run, a.scene, a.change, a.dry)
    print(f"scene {r['scene']} · {r['chars']} chars · {r['changes']} change(s)"
          f"{'  REFUSED' if r.get('refused') else '  queued as an edit'}")
    print(f"  reference: {r['reference_job']}")
    print(f"  {r['instruction']}")
    if r.get("refused"):
        print(f"  ! {r['refused']}")


if __name__ == "__main__":
    main()
