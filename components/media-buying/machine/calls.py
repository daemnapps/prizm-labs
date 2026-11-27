#!/usr/bin/env python3
"""calls.py — what the desk's recorded calls say, for readers outside the desk.

    python3 calls.py <brand> [--root REPO]        # print the summary

Read-only, offline, stdlib only. Reads runs/media-buying/<brand>/decisions.jsonl (decide.py writes it, one line per
call, carrying the flag as it was shown, the desk's suggestion, the call and its reason).

A call DISAGREES with the desk when it is not the desk's own suggestion (`agreed` false on the line). The summary
keeps every disagreement with its numbers and the reason on record, newest first, grouped by what the desk had
suggested, so the desk's lines can be retuned from where they were overruled: shown to the person first, never
changed on their own. The winners feed reads this summary (components/winners/feed_sections.py).
"""
import argparse, json, sys
from pathlib import Path

NUMBERS = ("spend", "purchases", "cpa", "cpa7", "cpa3", "spend7", "break_even", "share7")


def decisions_path(root, brand):
    return Path(root) / "runs" / "media-buying" / brand / "decisions.jsonl"


def read(path):
    """Every call on file, oldest first. A line that is not valid JSON is skipped; a missing file is no calls."""
    p = Path(path)
    if not p.is_file():
        return []
    rows = []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows


def _row(r):
    nums = r.get("numbers") if isinstance(r.get("numbers"), dict) else {}
    return {"at": r.get("at"), "asof": r.get("asof"), "flag": r.get("flag"), "kind": r.get("kind"), "name": r.get("name"),
            "suggested": r.get("suggested"), "call": r.get("call"), "why": " ".join(str(r.get("why") or "").split()),
            "numbers": {k: nums[k] for k in NUMBERS if nums.get(k) is not None}}


def summary(rows, last=10):
    """{"calls", "agreed", "disagreed", "by_suggestion", "disagreements", "last"} for a list of recorded calls."""
    rows = [r for r in rows if isinstance(r, dict)]
    by = {}
    for r in rows:
        b = by.setdefault(str(r.get("suggested")), {"calls": 0, "agreed": 0, "overruled_to": {}})
        b["calls"] += 1
        if r.get("agreed"):
            b["agreed"] += 1
        else:
            c = str(r.get("call"))
            b["overruled_to"][c] = b["overruled_to"].get(c, 0) + 1
    newest = sorted(enumerate(rows), key=lambda ir: (str(ir[1].get("at") or ""), ir[0]), reverse=True)
    return {"calls": len(rows), "agreed": sum(1 for r in rows if r.get("agreed")),
            "disagreed": sum(1 for r in rows if not r.get("agreed")),
            "by_suggestion": {k: by[k] for k in sorted(by)},
            "disagreements": [_row(r) for _, r in newest if not r.get("agreed")],
            "last": [_row(r) for _, r in newest[:last]]}


def for_brand(root, brand, last=10):
    return summary(read(decisions_path(root, brand)), last)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    a = ap.parse_args(argv)
    print(json.dumps(for_brand(a.root, a.brand), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
