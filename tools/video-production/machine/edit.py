#!/usr/bin/env python3
"""
edit.py — a regen is an EDIT off the plate, never a fresh shot.

    python3 machine/edit.py <run> --scene 1 --change "she is front-on, not in profile"
    python3 machine/edit.py <run> --scene 1 --show     # the split and the last instruction

**the owner's ruling, frames-by-edit.md, 2026-09-02.** Measured on a real run:

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
import re as _re
import sys
from datetime import datetime
from pathlib import Path

# The discipline — the band, the one-change rule, the instruction shape — was
# lifted out of this file into `tools/image-edit` on 2026-09-22 so the
# image side runs the same rules (the owner: "effectively the same mechanics as
# making scene / frame adjustments"). This file is its first caller. Found by
# walking up, never counted; appended, never inserted at 0.
def _components():
    here = Path(__file__).resolve()
    for d in here.parents:
        if (d / "tools" / "image-edit" / "splits.json").is_file():
            return d / "tools" / "image-edit"
    raise SystemExit("tools/image-edit is not beside this workspace")

sys.path.append(str(_components()))
from image_edit import discipline as _D  # noqa: E402

DELTA_MIN, DELTA_MAX, MAX_CHANGES = _D.DELTA_MIN, _D.DELTA_MAX, _D.MAX_CHANGES
count_changes = _D.count_changes

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
    # A cast member is read from the brand's casting registry, never pinned
    # here. (The Brand B esthetician that used to sit on this map was retired
    # 2026-09-29 — no casting sheet.)
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
    a banked thing, the bank comes too (2026-09-11 — the owner: "you should be
    using the actual flex model in higgsfield").
    """
    return _D.instruction(split_for(s)["keep"], change, assets_in(change))


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
    note = _D.guard(change, text)
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
