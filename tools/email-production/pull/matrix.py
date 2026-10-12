#!/usr/bin/env python3
"""The audience matrix — every planning cell, as one record. (EM-1)

    python3 pull/matrix.py --brand brand-b

Joins what already exists and never invents: the platform segments (from the
brand's segment audit), the avatar roster with its sub-avatars, and the
language depth behind each, into email-sms/audience-matrix.json — proposed under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)).

The honest limit, recorded in the file rather than papered over: platform
segments do not carry avatar membership, so the SIZE of an intersection cell
(e.g. Returning × avatar-one) is unknown today. The axes are real; the
crossings are planning cells, not measured populations.

Like every pull, this is a deliberate refresh job, not something a run does on
its way past — and like every pull it PROPOSES; a person folds it into brands/.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from paths import WORKSPACE
import facts_proposal

sys.path.insert(0, str(HERE.parent / "copy"))
import language as L


def segments_from_audit(brand_root):
    """The eight, read off the audit table — name, id, profiles."""
    text = (brand_root / "email-sms/segments.md").read_text()
    out = []
    # the audit escapes the pipe in "Core \| Lead" for its own table
    for m in re.finditer(r"^\|\s*(Core \\\|[^|]+?)\s*\|\s*([^|]+?)\s*\|\s*`(\w+)`\s*\|\s*([\d,]+)\s*\|",
                         text, re.M):
        out.append(dict(name=m.group(1).replace("\\|", "|").strip(),
                        rule=m.group(2), id=m.group(3),
                        profiles=int(m.group(4).replace(",", ""))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    brand_root = WORKSPACE / "brands" / args.brand

    segments = segments_from_audit(brand_root)
    if not segments:
        sys.exit("no segments parsed from the audit — the matrix would be half blind")

    idx = json.loads((brand_root / "core-avatars" / "language-index.json").read_text())
    avatars = []
    for a in L.avatars(args.brand, WORKSPACE):
        files = idx.get("per_avatar", {}).get(a["key"], {})
        sub_rows = {}
        for f in files.values():
            for sub, n in (f.get("sub_counts") or {}).items():
                sub_rows[sub] = sub_rows.get(sub, 0) + n
        subs = []
        for sub in a.get("subs") or []:
            short = re.sub(r"^sub-\d+-", "", sub)
            subs.append(dict(key=sub, tagged_rows=sub_rows.get(short, 0)))
        avatars.append(dict(key=a["key"], language_rows=a["rows"],
                            funnels=a["funnels"], subs=subs))

    matrix = dict(
        generated=f"{datetime.date.today()}",
        brand=args.brand,
        note=("The planning cell is segment × avatar × sub-avatar (RULED, "
              "the owner 2026-08-29 — the email-per-day concept is dead). Axes "
              "below are measured; intersection sizes are NOT — platform "
              "segments carry no avatar membership, so a cell is a planning "
              "unit, not a counted population."),
        caveats=[
            "Intersection sizes unknown: no avatar tag exists in the platform.",
            f"Sub-avatar language is thin: {idx['totals']['sub_tagged']} of "
            f"{idx['totals']['rows']} rows carry a sub tag — a sub-targeted "
            "piece leans on the sub's PROFILE plus the avatar's bank, and "
            "should say so.",
            "Lifecycle language is mostly unsegmented (89%) — a lifecycle "
            "cell may be targeted commercially, never claimed linguistically.",
        ],
        segments=segments,
        avatars=avatars,
        cells=dict(
            planning=sum(1 + len(a["subs"]) for a in avatars) * len(segments),
            note="avatar-level + sub-level rows × the eight segments; the "
                 "composer serves and reports cells from this space.",
        ),
    )
    run = facts_proposal.run_dir(args.brand, args.label)
    out = facts_proposal.write(run, args.brand, "email-sms/audience-matrix.json", json.dumps(matrix, indent=1) + "\n")
    n_subs = sum(len(a["subs"]) for a in avatars)
    print(f"{out.name}: {len(segments)} segments × ({len(avatars)} avatars + "
          f"{n_subs} sub-avatars) = {matrix['cells']['planning']} planning cells")
    print(f"proposal -> {facts_proposal.note(run, args.brand)}")


if __name__ == "__main__":
    main()
