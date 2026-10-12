#!/usr/bin/env python3
"""What the sending has taught, joined from what each email WAS and DID.

    python3 calendar/learnings.py --brand brand-b

Not a tally. Every cut here exists to answer "where is the opportunity" —
which categories and types earn, which are under-used relative to what they
earn, and what the timing data says. Proposes email-sms/learnings.md under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)).

Two caveats carried everywhere rather than stated once:
- **Open rate is not trustworthy.** Apple Mail privacy auto-opens inflate it,
  and a segment selected FOR engagement inflates it again. Click rate and
  revenue per recipient are the honest columns.
- **Small n is small n.** Any cut under ~5 sends is labelled, because at that
  size one email moves the average.

Reads only.
"""
import argparse
import datetime
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"
from zoneinfo import ZoneInfo  # noqa: E402

HERE = Path(__file__).resolve().parent

# The tool holds the code; the BRAND holds its own record. A puller READS the
# facts from brands/<brand>/email-sms/ and proposes what it makes under runs/
# (facts_proposal.py); a person folds it into brands/, so the next tool —
# statics, video — reads the same facts from the same place.
BRANDS = next(d for d in HERE.parents if (d / "brands").is_dir() and (d / "components").is_dir()) / "brands"


CATS = {"ask": "Promotional", "help": "Educational", "belong": "Cultural",
        "real": "Community", "brand": "Brand"}


def load(brand):
    """Every campaign with real reported numbers, from the ledger joined to the
    performance record by campaign id. What each email WAS (its category and
    type) is attached where the classified library can be joined to it, and is
    None where it cannot — timing needs no classification, so an unjoinable
    library never again empties the timing tables (FOLD Y, 2026-09-23)."""
    B = BRANDS / brand / "email-sms"
    perf = {r["groupings"]["campaign_id"]: r["statistics"]
            for r in json.loads((B / "performance.json").read_text())}
    led_rows = json.loads((B / "ledger.json").read_text())
    cls, by_name = {}, {}
    cf, xf = B / "classified.json", B / "sends" / "index.json"
    if cf.is_file() and xf.is_file():
        files = {x["file"]: x for x in json.loads(cf.read_text())}
        # the sends index does not carry the campaign id — it was built for
        # reading, not joining. The ledger has it, keyed by (date, campaign name).
        by_name = {(x["sent"], x["campaign"]): x["id"] for x in led_rows}
        for x in json.loads(xf.read_text()):
            cid = by_name.get((x.get("sent"), x.get("campaign")))
            if cid and x.get("file") in files:
                cls[cid] = files[x["file"]]
    # Klaviyo reports send times in UTC; the calendar plans in the account's
    # own time zone, so the hour is converted with the brand's accounts.json row
    # (read directly: importing derive here pulls urllib through email.py's shadow)
    acct = json.loads((HERE / "accounts.json").read_text())["brands"].get(brand) or {}
    tz = ZoneInfo(acct.get("timezone") or "UTC")
    rows = []
    for x in led_rows:
        cid = x["id"]
        if cid not in perf:
            continue
        s = perf[cid]
        rec = s.get("recipients") or 0
        if rec < 50:
            continue
        c = cls.get(cid, {})
        hour = None
        if x.get("hour") and x.get("sent") and not x.get("is_local"):
            # a local-time send's hour is already each person's own; it is
            # compared in its own table below, never mixed into this one
            utc = datetime.datetime.fromisoformat(f"{x['sent']}T{int(x['hour']):02d}:00+00:00")
            hour = utc.astimezone(tz).hour
        rows.append(dict(
            id=cid, sent=x.get("sent"), subject=x.get("subject"),
            category=c.get("category"), type=c.get("type"),
            audiences=x.get("audiences", []), hour=hour,
            is_local=x.get("is_local"), recipients=rec,
            open_rate=(s.get("opens_unique") or 0) / rec,
            click_rate=(s.get("clicks_unique") or 0) / rec,
            conv=(s.get("conversions") or 0),
            revenue=(s.get("conversion_value") or 0),
            rpr=(s.get("revenue_per_recipient") or 0),
            unsub_rate=(s.get("unsubscribes") or 0) / rec,
            spam_rate=(s.get("spam_complaints") or 0) / rec))
    return rows, str(tz)


def agg(rows, keyfn):
    g = defaultdict(list)
    for r in rows:
        k = keyfn(r)
        if k:
            g[k].append(r)
    out = []
    for k, v in g.items():
        rec = sum(r["recipients"] for r in v)
        out.append(dict(
            key=k, sends=len(v), recipients=rec,
            revenue=sum(r["revenue"] for r in v),
            rpr=sum(r["revenue"] for r in v) / rec if rec else 0,
            click=sum(r["click_rate"] * r["recipients"] for r in v) / rec if rec else 0,
            open=sum(r["open_rate"] * r["recipients"] for r in v) / rec if rec else 0,
            unsub=sum(r["unsub_rate"] * r["recipients"] for r in v) / rec if rec else 0))
    return sorted(out, key=lambda x: -x["rpr"])


def table(rows, label, thin=5):
    L = [f"| {label} | Sends | Revenue | Rev/recipient | Click | Unsub |",
         "|---|---|---|---|---|---|"]
    for r in rows:
        n = f"{r['key']}" + (" *" if r["sends"] < thin else "")
        L.append(f"| {n} | {r['sends']} | ${r['revenue']:,.0f} | "
                 f"**${r['rpr']:.3f}** | {100*r['click']:.2f}% | {100*r['unsub']:.2f}% |")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    rows, tz = load(args.brand)
    tot_rec = sum(r["recipients"] for r in rows)
    tot_rev = sum(r["revenue"] for r in rows)
    typed = [r for r in rows if r["category"] or r["type"]]
    typed_rev = sum(r["revenue"] for r in typed)

    L = [f"# {args.brand} — what the sending has taught", "",
         f"{len(rows)} campaigns with real reported numbers. {int(tot_rec):,} recipients,",
         f"${tot_rev:,.0f} attributed. {len(typed)} of them could be joined to a",
         "classified email, and only those feed the category and type tables;",
         "day, hour and local-time use every campaign.", "",
         "**Two caveats, carried rather than footnoted.** Open rate is not",
         "trustworthy — Apple Mail privacy auto-opens inflate it and an",
         "engagement-selected segment inflates it again; click rate and revenue",
         "per recipient are the honest columns. And a row marked `*` has fewer",
         "than five sends behind it, where one email moves the average.", "",
         "## By category", "",
         "The question this answers: what is each kind of email worth per person",
         "it reaches, and what does it cost in unsubscribes.", ""]
    bycat = agg(typed, lambda r: CATS.get(r["category"]))
    L += table(bycat, "Category")

    L += ["", "## By type — the top earners", ""]
    bytype = [t for t in agg(typed, lambda r: r["type"]) if t["sends"] >= 3][:14]
    L += table(bytype, "Type", thin=5)

    L += ["", "## By type — the ones that cost more than they earn", ""]
    worst = sorted([t for t in agg(typed, lambda r: r["type"]) if t["sends"] >= 3],
                   key=lambda x: x["rpr"])[:8]
    L += table(worst, "Type", thin=5)

    L += ["", "## By day of week", ""]
    import datetime as dt
    byday = agg(rows, lambda r: dt.date.fromisoformat(r["sent"]).strftime("%A")
                if r["sent"] else None)
    L += table(byday, "Day")

    L += ["", "## By send hour", "",
          f"The hour the send was scheduled for, in the account's time zone ({tz}),",
          "converted from the UTC time Klaviyo reports. Local-time sends are left",
          "out — their hour is each person's own — and an hour with fewer than",
          "four sends behind it is not listed.", ""]
    byhour = [h for h in agg(rows, lambda r: f"{r['hour']}:00" if r["hour"] is not None else None)
              if h["sends"] >= 4]
    L += table(sorted(byhour, key=lambda x: -x["rpr"]), "Hour set")

    L += ["", "## Local time vs one fixed time", "",
          "Local-time send delivers at that hour in each person's own zone. It",
          "has been used on some sends and not others, which makes it the",
          "cleanest comparison on this page.", ""]
    L += table(agg(rows, lambda r: "each person's local time" if r["is_local"]
                   else "one fixed time for everyone"), "Method")

    L += ["", "## The opportunity", "",
          "Share of sends against share of revenue, per category. A category",
          "earning more than its share of the sending is one to send more of.", "",
          "| Category | Share of sends | Share of revenue | |", "|---|---|---|---|"]
    for c in sorted(bycat, key=lambda x: -x["revenue"]):
        ss = 100 * c["sends"] / len(typed)
        sr = 100 * c["revenue"] / typed_rev if typed_rev else 0
        verdict = "**under-sent**" if sr > ss * 1.25 else (
            "over-sent" if ss > sr * 1.25 else "balanced")
        L.append(f"| {c['key']} | {ss:.0f}% | {sr:.0f}% | {verdict} |")

    run = facts_proposal.run_dir(args.brand, args.label)
    facts_proposal.write(run, args.brand, "email-sms/learnings.md", "\n".join(L) + "\n")
    print("\n".join(L[:8]))
    print(f"\nproposal -> {facts_proposal.note(run, args.brand)}")


if __name__ == "__main__":
    main()
