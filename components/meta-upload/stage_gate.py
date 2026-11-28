#!/usr/bin/env python3
"""The stage-check gate: no piece goes into Meta unless its stage-check ran and passed.

stage-check (components/stage-check) walks a piece's steps by its brief number and writes where it stands to
runs/stage-check/<brand>/<brief key>/latest.json. Before an upload, the card's brief is looked up there:

  never ran        no record for this brief            -> refused: "stage-check has never run on <brief>"
  failed           a step before the card failed       -> refused: names each failing step
  stale            the last run is older than the card -> refused: "last ran <date>, before this card was filed"

The card step itself (and anything after it, such as the Queue entry) is not asked: the card is what is being
checked, and stage-check's card step waits on this very gate. `format` is not asked either; stage-check itself
treats it as advice, not a stop.

    stage_gate.py <card folder>      what the gate says for one card (exit 1 when refused)
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "naming"))
import names as N  # noqa: E402

NOT_ASKED = {"format"}          # advice in stage-check, not a stop
FROM_CARD = {"card", "queue"}   # the card step and what follows it


def root():
    return Path(os.environ.get("STAGE_CHECK_ROOT") or REPO / "runs" / "stage-check")


def records(brand):
    d = root() / (brand or "_")
    out = []
    for f in sorted(d.glob("*/latest.json")) if d.is_dir() else []:
        try:
            r = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def record_for(brand, ad_name):
    """The newest stage-check record whose brief is this card's brief (brand + product + number)."""
    key = N.full_brief_key(ad_name)
    if not key:
        return None
    hits = [r for r in records(brand) if N.full_brief_key(r.get("brief") or r.get("piece") or "") == key]
    return max(hits, key=lambda r: str(r.get("at") or "")) if hits else None


def _day(at):
    return str(at or "")[:10] or "an unknown day"


def check(card):
    """{"ok": bool, "why": plain words} for one card."""
    brand, name = card.get("brand"), card.get("ad_name") or ""
    label = N.full_brief_key(name)
    if not label:
        return {"ok": False, "why": "the card's name carries no brief, so stage-check cannot have run on it"}
    rec = record_for(brand, name)
    if rec is None:
        return {"ok": False, "why": f"stage-check has never run on {label} — run it on this brief before upload"}
    steps = rec.get("steps") or []
    upto = next((i for i, s in enumerate(steps) if s.get("step") in FROM_CARD), len(steps))
    bad = [s for s in steps[:upto] if not s.get("ok") and s.get("step") not in NOT_ASKED]
    if bad:
        return {"ok": False, "why": f"stage-check failed on {label} (last run {_day(rec.get('at'))}): "
                                    + "; ".join(str(s.get("name") or s.get("step")) for s in bad)}
    made = str(card.get("made_at") or "")
    if made and str(rec.get("at") or "") < made:
        return {"ok": False, "why": f"stage-check last ran on {label} on {_day(rec.get('at'))}, before this card "
                                    f"was filed ({_day(made)}) — run it again"}
    return {"ok": True, "why": f"stage-check passed on {label} ({_day(rec.get('at'))})"}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    c = json.loads((Path(sys.argv[1]) / "card.json").read_text())
    r = check(c)
    print(("PASS  " if r["ok"] else "REFUSED  ") + r["why"])
    sys.exit(0 if r["ok"] else 1)
