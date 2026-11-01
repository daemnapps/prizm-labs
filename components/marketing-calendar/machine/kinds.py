"""Design or letter: the calendar decides, per send, which emails are designed and which stay letters.

the owner, 2026-10-17: "when we do the marketing calendar every 2 weeks, we can also determine which
emails become design and which ones stay less design. All mapping and context and runs need to
operate on the same principles."

Every slot gets three fields, written into the month's slots.json (the machine's record):
    kind      design | letter     (definitions/email-kinds.json, a brand's own email-kinds.json wins)
    format    the section stack   (email-production's formats.json type_to_format; a letter is `simple`)
    kind_why  one line saying which rule decided it

Runs inside layer 9 (calendar.py finish) and alone, free, for a two-week window:

    python3 machine/kinds.py <brand> <YYYY-MM> [--from 2026-11-02 --days 14]

Brand-agnostic: no brand is named here; a brand's exceptions live in its own file.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

RULES = paths.DEFINITIONS / "email-kinds.json"
FORMATS = paths.COMPONENTS / "email-production" / "formats.json"


def rules(brand_root=None):
    """The shared rule, with the brand's own letter/design lists laid over it."""
    r = json.loads(RULES.read_text())
    letter, design, days = set(r["letter"]), set(), {}
    own = None
    if brand_root:
        f = Path(brand_root) / "email-sms" / "email-kinds.json"
        if f.exists():
            own = json.loads(f.read_text())
            letter |= set(own.get("letter", []))
            design = set(own.get("design", []))
            letter -= design
            days = own.get("by_weekday", {})
    return letter, design, r.get("default", "design"), own is not None, days


def decide(slot, letter, design, default, branded, fmts, days=None):
    t = slot.get("type")
    day = datetime.date.fromisoformat(slot["date"]).strftime("%a")
    if days and day in days:
        kind, why = days[day], "this brand sends %s on %ss (its email-kinds.json)" % (days[day] + "s", day)
    elif t in design:
        kind, why = "design", "this brand's email-kinds.json makes `%s` designed" % t
    elif t in letter:
        kind, why = "letter", ("`%s` is a letter type" % t) + (" (with this brand's own list)" if branded else "")
    else:
        kind, why = default, "`%s` sells or argues: designed by default" % t
    if kind == "letter":
        fmt = "simple"
    else:
        fmt = fmts.get("type_to_format", {}).get(t) or fmts.get("_default", "simple")
        if fmt == "simple":           # a designed email needs a designed stack
            fmt = "hero-product"
            why += "; no designed stack for this type, so hero-product"
    return kind, fmt, why


def apply(slots, brand_root=None):
    """Write kind / format / kind_why onto every slot (and its variants). Returns the slots."""
    letter, design, default, branded, days = rules(brand_root)
    fmts = json.loads(FORMATS.read_text()) if FORMATS.exists() else {}
    for s in slots:
        if s.get("kind_set_by"):      # a person's call on the board is never overwritten
            continue
        s["kind"], s["format"], s["kind_why"] = decide(s, letter, design, default, branded, fmts, days)
    return slots


def window(slots, start=None, days=14):
    if not start:
        return slots
    a = datetime.date.fromisoformat(start)
    b = a + datetime.timedelta(days=days)
    return [s for s in slots if a <= datetime.date.fromisoformat(s["date"]) < b]


def table(slots):
    rows = ["| Date | Send | Type | Audience | Kind | Format |", "|---|---|---|---|---|---|"]
    for s in slots:
        segs = ", ".join(s.get("segments") or [s.get("segment", "")]).replace("|", "·")
        rows.append("| %s | %s | %s | %s | **%s** | %s |" % (s["date"], s["id"], s["type"], segs, s["kind"], s["format"]))
    n = sum(1 for s in slots if s["kind"] == "design")
    return "\n".join(rows) + "\n\n%d designed, %d letters.\n" % (n, len(slots) - n)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("brand")
    ap.add_argument("month")
    ap.add_argument("--from", dest="start", help="first day of the window, YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--dry-run", action="store_true", help="print the table, write nothing")
    a = ap.parse_args()
    d = paths.month_dir(a.brand, a.month)
    f = d / "slots.json"
    if not f.exists():
        sys.exit("no slots.json at %s: run the calendar first" % paths.rel(f))
    slots = apply(json.loads(f.read_text()), paths.brand_root(a.brand))
    shown = window(slots, a.start, a.days)
    out = "# Design or letter, %s %s%s\n\n%s" % (
        a.brand, a.month, (" · %s + %d days" % (a.start, a.days)) if a.start else "", table(shown))
    print(out)
    if not a.dry_run:
        f.write_text(json.dumps(slots, indent=1, default=str) + "\n")
        (d / "kinds.md").write_text(out)
        print("written: %s, %s" % (paths.rel(f), paths.rel(d / "kinds.md")))


if __name__ == "__main__":
    main()
