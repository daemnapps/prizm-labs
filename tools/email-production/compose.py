#!/usr/bin/env python3
"""The composer: the brand's own record in, one month of slots out.

    python3 compose.py 2026-09 --brand brand-b [--dry-run] [--label sep]

Reads the brand tree (read-only, always): the type catalogue, the eight
segments, the cultural moments, the learnings, and the whole sent library.
One model call composes the month; this script then CHECKS the month against
SLOT.md's rules deterministically and writes the violations beside the plan
rather than trusting the model to have obeyed.

The composer decides what exists and when. It writes no copy, no subject
line, no layout — production's job, via brief.py and the chain.
"""
import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path


def _json_or(path, default):
    """A brand file that is not there yet reads as empty — a brand with no
    history is a brand, not an error (Brand A, 2026-09-09)."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return default


def _text_or(path, default=""):
    try:
        return path.read_text()
    except FileNotFoundError:
        return default

from paths import HERE, WORKSPACE, calendar_tool, component, run_home
sys.path.append(str(component("brandpath")))   # appended, never ahead of this machine
import brandpath as BP                                # noqa: E402
from email import claude, fill, latest_prompt, sha  # the chain's own plumbing

from email import catalogue_path  # brand-first resolution

# The brand-record readers and the month checker moved to
# the marketing-calendar tool on 2026-09-13, when the calendar became its
# own component: a month of ad concepts reads the same record, and it could not
# reach these while they lived inside the email chain. Re-exported here so this
# file is the command it always was — same names, same bodies, one copy.
_CAL = calendar_tool("machine")
if not _CAL:
    sys.exit("cannot find the marketing-calendar tool — compose.py reads its "
             "brand-record readers and its month checker")
sys.path.append(str(_CAL))                  # appended, never ahead of this machine
from brandrecord import (                   # noqa: E402,F401
    brand_segments, offerless_avatars, render_types, render_offers,
    render_products, findings, responsiveness, cadence_history, coldness,
    per_person, parse_slots, check, L,
)

DEFAULT_MODEL = "claude-opus-5"
CATEGORY = {"ask": "Promotional", "help": "Educational", "belong": "Cultural",
            "real": "Community", "brand": "Brand", "affiliate": "Affiliate"}






def render_moments(path):
    d = json.loads(Path(path).read_text())
    out = ["Streams: " + " · ".join(f"{k} ({v})" for k, v in d["streams"].items()), ""]
    for av, block in d["avatars"].items():
        out.append(f"## {av}")
        out.append(f"Territory: {block['territory']}")
        for m in block["moments"]:
            line = f"- `{m['key']}` · {m['stream']} · {m['window']} · {m['evidence']}"
            if m.get("sent"):
                line += " · already sent: " + " / ".join(m["sent"])
            out.append(line)
            if m.get("note"):
                out.append(f"    ({m['note']})")
        out.append("")
    return "\n".join(out)


def render_library(brand_root):
    """Every send: file · type · subject. The spent ground AND the source shelf."""
    cl = _json_or(brand_root / "email-sms/classified.json", [])
    return "\n".join(f"- {r['sent']} · {r.get('type', '?')} · {r['file']} · "
                     f"“{r['subject']}”" for r in cl)




















def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("month", help="YYYY-MM, the month to compose")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--recheck", default=None, metavar="LABEL",
                    help="re-run the checks on an existing compose result — "
                         "no model call, free")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve and report every input, then stop — no model call")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        sys.exit(f"month must be YYYY-MM, got {args.month!r}")

    brand_root = WORKSPACE / "brands" / args.brand
    sends_dir = brand_root / "email-sms" / "sends"
    catalogue = json.loads(catalogue_path(args.brand).read_text())
    segments = brand_segments(brand_root)
    no_offer = offerless_avatars(brand_root, {a['key'] for a in (L.avatars(args.brand, WORKSPACE) if L else [])})
    types_by_key = {t["key"]: t for t in catalogue["types"]}
    roster_full = L.avatars(args.brand, WORKSPACE) if L else []
    roster = {a["key"] for a in roster_full}
    subs_by_avatar = {a["key"]: set(a.get("subs") or []) for a in roster_full}

    roster_txt = "\n".join(
        f"- `{a['key']}` — {a['rows']:,} language rows"
        + (f" · sub-avatars: {', '.join(a['subs'])}" if a["subs"] else "")
        for a in (L.avatars(args.brand, WORKSPACE) if L else [])) \
        or "- (this brand has no avatar language banks)"

    fields = dict(
        today=f"{datetime.date.today():%A, %-d %B %Y}",
        month=args.month,
        slot_spec=(HERE / "SLOT.md").read_text(),
        types=render_types(catalogue_path(args.brand)),
        segments=(brand_root / "email-sms/segments.md").read_text(),
        moments=render_moments(BP.brand_path(brand_root.name, "strategy", "moments.json", root=brand_root.parent)),
        learnings=_text_or(brand_root / "email-sms/learnings.md", "No learnings yet — this brand has no classified sends on file."),
        sent_library=render_library(brand_root),
        findings="\n".join(findings(brand_root)) or "(no learnings yet — this brand has no measured sends)",
        coldness=coldness(brand_root, catalogue),
        avatars=roster_txt,
        products=render_products(brand_root),
        offers=render_offers(brand_root),
    )

    if args.dry_run:
        print(f"--- dry run: compose {args.month} for {args.brand} ---")
        for k, v in fields.items():
            print(f"  {'OK' if v else 'MISSING':7} {k:12} {len(v):>8,} chars")
        print(f"  roster: {', '.join(sorted(roster)) or '(none)'}")
        return

    label = args.recheck or args.label or f"compose-{args.month}"
    out_dir = run_home(args.brand, label)          # email-production#19: beside the chain's runs
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = latest_prompt("composer")
    filled = fill(prompt_file.read_text(), fields)
    (out_dir / "composer--sent.md").write_text(filled)
    (out_dir / "record.json").write_text(json.dumps(
        {k: len(str(v)) for k, v in fields.items()}, indent=1) + "\n")
    print(f"composer: {args.month} for {args.brand}  ({prompt_file.name}, "
          f"{len(filled):,} chars in)")

    if args.recheck:
        slots = json.loads((out_dir / "slots.json").read_text())
        seconds = 0.0
        output = (out_dir / "composer--month.md").read_text()
    else:
        import time
        t0 = time.time()
        output = claude(filled, args.model)
        seconds = round(time.time() - t0, 1)
        (out_dir / "composer--month.md").write_text(output + "\n")
        slots = parse_slots(output)
    errors, warns = check(slots, args.month, types_by_key, sends_dir, roster,
                          subs_by_avatar, segments, no_offer)
    # CMP-2's teeth: a why that cites nothing is a hunch. Citations are a
    # finding id, a moment key, or an explicit hold.
    moment_keys = set()
    mf = BP.brand_path(brand_root.name, "strategy", "moments.json", root=brand_root.parent)
    if mf.is_file():
        for blk in json.loads(mf.read_text())["avatars"].values():
            moment_keys |= {m["key"] for m in blk["moments"]}
    for s in slots:
        why = (s.get("why") or "") + " " + (s.get("occasion") or "")
        cited = (re.search(r"\[F\d+\]", why)
                 or any(k in why for k in moment_keys)
                 or "HELD OPEN" in why.upper()
                 or re.search(r"days? cold|never (been )?(sent|planned)|last planned|/recipient|meets that obligation", why))
        if not cited:
            warns.append(f"{s.get('id')}: why cites no finding, no moment, "
                         "no hold — a hunch, flagged per CMP-2")
    (out_dir / "slots.json").write_text(json.dumps(slots, indent=1) + "\n")

    report = ["# The month, checked", "",
              f"{len(slots)} slots for {args.month}. "
              f"{len(errors)} rule breaks · {len(warns)} warnings.", ""]
    if errors:
        report += ["## Breaks — fix before this month stands", ""]
        report += [f"- {e}" for e in errors] + [""]
    if warns:
        report += ["## Warnings — a human reads these", ""]
        report += [f"- {w}" for w in warns] + [""]
    if not errors and not warns:
        report += ["Nothing broken, nothing to flag."]
    report += ["", per_person(slots)]
    (out_dir / "checks.md").write_text("\n".join(report) + "\n")

    (out_dir / "run.json").write_text(json.dumps({
        "label": label, "brand": args.brand, "month": args.month,
        "lane_kind": "email-compose", "model": args.model,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "prompt_file": prompt_file.name, "prompt_sha256_12": sha(prompt_file),
        "seconds": seconds, "chars_in": len(filled), "chars_out": len(output),
        "slots": len(slots), "errors": len(errors), "warnings": len(warns),
    }, indent=2) + "\n")

    print(f"  {len(slots)} slots · {len(errors)} breaks · {len(warns)} warnings"
          f"  ({seconds}s)")
    print(f"done -> {out_dir}")
    print(f"briefs:  python3 brief.py {out_dir}")


if __name__ == "__main__":
    main()
