#!/usr/bin/env python3
"""What to go and find out, before a month's emails get written.

    python3 live_read.py --brand brand-b --month 2026-09
    python3 live_read.py --brand brand-b --month 2026-09 --slot sep-13
    python3 live_read.py --brand brand-b --month 2026-09 --status

RULED 2026-09-10 (the owner): "you could also look deeper into this event, see what
games are going on for the week too, and bait the audience to engage with it on
top of whatever offer or concept the mail is running… this type of processing
needs to run for EVERY email, not just this sports thing."

A moment is not a label. It is a week, with specific things happening in it,
and the reader is already inside that week. An email that says "football season
is back" is barely better than one that ignores it; an email that names what is
happening the day after it lands is the one that gets answered.

So every send gets a **live read** — the checkable facts of its week, the one
odd thing in it, and two or three ways to invite the reader to engage with the
moment itself on top of whatever the email is selling.

This file writes the RESEARCH BRIEF: the questions to go and answer for each
send, built from that send's own moment, date, market and audience. The answers
come back as `research/<slot>.md` and the chain reads them at stage 1c.

Brand-agnostic and market-agnostic by construction: nothing here knows about a
sport, a country, a brand or a product. The questions are shaped by the KIND of
moment a slot carries, and the brand's own files supply the rest.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

from paths import HERE, WORKSPACE, component, run_home
sys.path.append(str(component("brandpath")))   # appended, never ahead of this machine
import brandpath as BP                                # noqa: E402

# What kind of week a slot sits in, and therefore what is worth finding out.
# Named by the shape of the moment, never by its content.
KINDS = {
    "dated": [
        "What exactly happens in this moment during the send week, and on which "
        "days? Name each thing, its date and its local time.",
        "What happens the DAY AFTER this email lands? That is the thing the "
        "reader is about to do, and the thing to ask about.",
        "What is the single strangest true detail of this particular week — the "
        "one a person would mention to a friend?",
        "What did the audience argue about in the last seven days of this moment?",
        "Is there anything in this week that would make the email land badly — a "
        "death, a scandal, a disaster, a public mourning?",
    ],
    "seasonal": [
        "What is actually true of this market in this week — weather, daylight, "
        "school term, pay cycle, what people are physically doing?",
        "What changes for this audience between this week and the one after?",
        "What does this audience complain about at exactly this point in the year?",
        "Is there anything in this week that would make the email land badly?",
    ],
    "none": [
        "What is this product category arguing about right now — the last thirty "
        "days, in the audience's own spaces?",
        "What has changed for this audience in the last month: a price, a law, a "
        "shortage, a platform, a trend they are reacting to?",
        "What is live in this market this week that this audience is inside of?",
        "Is there anything in this week that would make the email land badly?",
    ],
}

ALWAYS = [
    "Every answer needs a source and a date. A fact without one does not go in.",
    "Nothing that happens AFTER the send date may be stated as known — results "
    "not yet played, outcomes not yet decided.",
    "Read the market as the reader's, not as your own.",
]


def kind_of(slot, moments):
    occ = (slot.get("occasion") or "").strip()
    if not occ or occ.startswith("recorded problem") or occ.startswith("HELD OPEN"):
        return "none"
    key = occ.split(" — ")[0].strip().strip("`")
    rec = moments.get(key, {})
    stream = (rec.get("stream") or "").lower()
    return "seasonal" if stream in ("seasonal", "weather") else "dated"


def moments_index(brand):
    f = BP.brand_path(brand, "strategy", "moments.json", root=WORKSPACE / "brands")
    if not f.is_file():
        return {}
    out = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("key"):
                out[o["key"]] = o
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(json.loads(f.read_text()))
    return out


def market_of(brand):
    for rel in ("market.md", "identity/market.md", "strategy/market.md"):
        f = BP.resolve_rel(brand, rel, root=WORKSPACE / "brands")
        if f.is_file():
            return f.read_text().strip()[:600]
    return None


def brief(slot, brand, moments):
    d = datetime.date.fromisoformat(slot["date"])
    kind = kind_of(slot, moments)
    occ = (slot.get("occasion") or "").strip()
    key = occ.split(" — ")[0].strip().strip("`")
    rec = moments.get(key, {})
    lines = [
        f"# Research brief — {slot['id']} · {d:%A %-d %B %Y}",
        "",
        f"- send lands: **{d:%A %-d %B %Y}**",
        f"- to: {slot.get('segment', '?')}",
        f"- the moment: " + (f"**{key}**" + (f" — {rec.get('window')}" if rec.get("window") else "")
                             if kind != "none" else "none scheduled — read the live week instead"),
        f"- week kind: {kind}",
        "",
        "## Find out",
        "",
    ]
    lines += [f"{i}. {q}" for i, q in enumerate(KINDS[kind], 1)]
    lines += ["", "## Rules for every answer", ""]
    lines += [f"- {r}" for r in ALWAYS]
    lines += [
        "",
        "## Then answer this",
        "",
        "**What can this email ask that the reader can answer without buying "
        "anything, and that is about the moment rather than the product?**",
        "",
        "---",
        "",
        "## FINDINGS",
        "",
        "_(write them here — the chain reads this file at stage 1c)_",
        "",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--month", default="2026-09")
    ap.add_argument("--slot", default=None)
    ap.add_argument("--status", action="store_true",
                    help="which sends have a live read and which are still blind")
    a = ap.parse_args()

    cal = HERE / "results" / f"calendar-{a.month}"
    rows = json.loads((cal / "slots.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("slots", [])
    if a.slot:
        rows = [r for r in rows if r["id"] == a.slot]
    moments = moments_index(a.brand)
    out_dir = run_home(a.brand, f"research-{a.month}")   # email-production#19

    if a.status:
        done = blind = 0
        for r in rows:
            f = out_dir / f"{r['id']}.md"
            has = f.is_file() and "FINDINGS" in f.read_text() and \
                len(f.read_text().split("## FINDINGS", 1)[1].strip()) > 200
            print(f"  {'RESEARCHED' if has else 'BLIND     '} {r['id']}  {r['date']}  "
                  f"{r.get('occasion', '')[:60]}")
            done, blind = done + bool(has), blind + (not has)
        print(f"\n{done} researched · {blind} blind")
        if not market_of(a.brand):
            print(f"\nNOTE: {a.brand} has no market file. Until it has one, every "
                  "live read has to guess where the reader lives — which it will "
                  "refuse to do, and say so instead.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    for r in rows:
        f = out_dir / f"{r['id']}.md"
        if f.is_file() and "## FINDINGS" in f.read_text() and \
                len(f.read_text().split("## FINDINGS", 1)[1].strip()) > 200:
            print(f"  kept    {f.name} (already researched)")
            continue
        f.write_text(brief(r, a.brand, moments))
        print(f"  brief   {f.name}")
    print(f"\n-> {out_dir}")


if __name__ == "__main__":
    main()
