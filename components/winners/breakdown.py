#!/usr/bin/env python3
"""breakdown: check and file one winner's part-by-part breakdown. HELD FOR REVIEW: nothing calls this yet.

    breakdown.py check <breakdown.json>
    breakdown.py file  --brand <brand> --row <bank row id> --from <breakdown.json> [--board <board.json>] [--root REPO]

The breakdown is the record the proposed prompt returns (proposed/winner-breakdown-v1.md), in one fixed order: hook,
lead, offer, mechanism, outcome, features against benefits, guarantee, ask, the scenes with the sound off, type and
angle, what to change. Offline, stdlib only; no model is called here.

`file` writes runs/winners/<brand>/breakdown/<row id>.json and .md (what the writing stages are handed), and with
--board fills that winner's `breakdown` on the top-ads board (components/meta-upload/top1_board.py reads `message`,
`hook`, `format`, `why_it_works`, `keep`, `vary`, `flags`), matched by one of the row's ad ids. Exit 2 on bad input.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import bank as B  # noqa: E402

ORDER = ("hook", "lead", "offer", "mechanism", "outcome", "features_benefits", "guarantee", "ask", "sound_off",
         "type", "angle", "what_to_change")
TITLES = {"hook": "Hook", "lead": "Lead", "offer": "Offer", "mechanism": "Mechanism", "outcome": "Outcome",
          "features_benefits": "Features against benefits", "guarantee": "Guarantee", "ask": "Ask",
          "sound_off": "The scenes with the sound off", "type": "Type", "angle": "Angle",
          "what_to_change": "What to change"}
LISTS = ("features_benefits", "sound_off", "what_to_change")


def check(rec):
    """Problems with a breakdown record, [] when it is whole and in order."""
    if not isinstance(rec, dict):
        return ["not an object"]
    bad = ["missing %s" % k for k in ORDER if k not in rec]
    bad += ["%s is not a list" % k for k in LISTS if k in rec and not isinstance(rec[k], list)]
    have = [k for k in rec if k in ORDER]
    if not bad and have != list(ORDER):
        bad.append("parts are out of order: %s" % ", ".join(have))
    if isinstance(rec.get("what_to_change"), list) and not rec["what_to_change"]:
        bad.append("what_to_change is empty: a breakdown ends with a list of what to change")
    return bad


def _say(v):
    if isinstance(v, dict):
        return " · ".join("%s: %s" % (k, _say(x)) for k, x in v.items() if x not in (None, "", []))
    if isinstance(v, list):
        return "; ".join(_say(x) for x in v)
    return " ".join(str(v).split())


def render(row_id, rec):
    out = ["# Breakdown — `%s`" % row_id, ""]
    for k in ORDER:
        out += ["## %s" % TITLES[k], ""]
        v = rec.get(k)
        out += (["- %s" % _say(x) for x in v] or ["none"]) if isinstance(v, list) else [_say(v) or "none"]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def board_fields(rec):
    """The board's own `breakdown` shape, read off the ordered record. Nothing is added that the record lacks."""
    changes = [x for x in rec.get("what_to_change") or [] if isinstance(x, dict)]
    return {"message": _say((rec.get("angle") or {}).get("claim")), "hook": _say(rec.get("hook")),
            "format": _say(rec.get("type")),
            "why_it_works": [], "keep": "; ".join(dict.fromkeys(_say(x.get("keep")) for x in changes if x.get("keep"))),
            "vary": [_say(x.get("change")) for x in changes if x.get("change")], "flags": "none"}


def file(root, brand, row_id, rec, board=None):
    """Write the breakdown beside the bank and, when a board is named, onto its matching winner. -> [paths]."""
    bad = check(rec)
    if bad:
        raise ValueError("; ".join(bad))
    bank = B.load_bank(B.bank_path(root, brand), brand)
    row = next((r for r in bank["rows"] if r["id"] == row_id), None)
    if row is None:
        raise ValueError("no bank row %s for %s" % (row_id, brand))
    d = B.brand_dir(root, brand) / "breakdown"
    d.mkdir(parents=True, exist_ok=True)
    doc = {"row": row_id, "name": row.get("name"), "ad_ids": row.get("ad_ids"), **{k: rec[k] for k in ORDER}}
    (d / ("%s.json" % row_id)).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    (d / ("%s.md" % row_id)).write_text(render(row_id, rec))
    wrote = [d / ("%s.json" % row_id), d / ("%s.md" % row_id)]
    if board:
        data = json.loads(Path(board).read_text())
        ids = {str(x) for x in row.get("ad_ids") or []}
        hit = next((w for w in (data.get(brand) or {}).get("winners") or []
                    if ids & {str(a.get("ad_id")) for a in w.get("ads") or []}), None)
        if hit is None:
            raise ValueError("the board has no %s winner carrying one of this row's ads" % brand)
        old = hit.get("breakdown") if isinstance(hit.get("breakdown"), dict) else {}
        new = {k: v for k, v in board_fields(rec).items() if v not in ("", [], None, "none")}
        hit["breakdown"] = {**old, **new}          # merged: a field the record leaves empty keeps what was there
        Path(board).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        wrote.append(Path(board))
    return wrote


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="verb", required=True)
    c = sub.add_parser("check"); c.add_argument("path")
    f = sub.add_parser("file")
    f.add_argument("--brand", required=True); f.add_argument("--row", required=True)
    f.add_argument("--from", dest="src", required=True); f.add_argument("--board")
    f.add_argument("--root", default=str(paths.repo(__file__)))
    a = ap.parse_args(argv)
    try:
        rec = json.loads(Path(a.path if a.verb == "check" else a.src).read_text())
    except (OSError, ValueError) as e:
        print("bad input: %s" % e, file=sys.stderr)
        return 2
    if a.verb == "check":
        bad = check(rec)
        print("\n".join(bad) if bad else "whole and in order")
        return 2 if bad else 0
    try:
        for p in file(Path(a.root), a.brand, a.row, rec, a.board):
            print("wrote %s" % B.rel(a.root, p))
    except (ValueError, B.BadInput) as e:
        print("bad input: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
