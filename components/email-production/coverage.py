#!/usr/bin/env python3
"""Which calendar sends ahead have nothing written for them (email_lead, 2026-11-10).

editor's emails page only shows emails that exist, so a send the calendar plans and nobody wrote leaves no hole anyone
can see. This lists, for each brand, every send in the window ahead (today and the next 14 days by default) whose
email has no written version, and every text whose email has none. A run is matched to its send by the slot it
records (sms.recorded_slot), never by its folder name: brand_b-nov-08a is slot nov-09, brand_a-nov-10--fed-up-king is
nov-56. A run kept off editor's page (off-page.json) does not count as written. A send the reviewer cut is not listed.

    python3 coverage.py --brand brand_b [--brand brand_a] [--from YYYY-MM-DD] [--days 14]

run_month.py prints the same list before and after every writing batch, so a batch is built from what is missing,
not from a list typed from memory. Reads only; writes nothing, calls nothing outside this Mac.

It also lists every text in the window that is WRITTEN but NOT SCHEDULED (email_lead, 2026-11-24: three brand_b texts for
Nov 27-30 were written and never scheduled, caught by hand three days out; developer 2026-11-18: texts go out as planned).
Scheduled means the text's sms-card.json state is "scheduled". On a brand whose platform (brands/<brand>/operations/
brand.json `sms_platform`) is one a person places texts on by hand, "approved — place in Postscript" counts too but is
listed apart as "placed by a person, not confirmed". Superseded texts and texts whose send the reviewer cut are skipped.
This reads the repo's own cards; the platform itself stays a manual cross-check.
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from paths import HERE, WORKSPACE
import sms

sys.path.insert(0, str(HERE / "machine"))
import reviewed_plan as RP  # noqa: E402
from sms_facts import platform_of  # noqa: E402

SCHEDULED = "scheduled"
PLACED_BY_HAND = "approved — place in Postscript"   # the state sms_launch.approve leaves on a hand-placed platform


def gaps(slots, start, days, email_written, text_written):
    """The sends in [start, start + days) with nothing written. `email_written(slot_id)` says whether a written email
    exists; `text_written(slot)` returns None when the slot's text is written for it, else why not (no text, or one
    written for another day or another email: the calendar renumbers texts when it is re-planned).
    -> [{"id", "date", "channel", "why"}] in date order."""
    end = (date.fromisoformat(start) + timedelta(days=days)).isoformat()
    out = []
    for s in sorted(slots, key=lambda x: (x.get("date") or "", str(x.get("hour") or ""))):
        d = s.get("date") or ""
        if not (start <= d < end):
            continue
        if s.get("channel", "email") == "email":
            if not email_written(s["id"]):
                out.append({"id": s["id"], "date": d, "channel": "email", "why": "no email written for this send"})
        else:
            why = text_written(s)
            if why:
                out.append({"id": s["id"], "date": d, "channel": "sms", "why": why})
            f = s.get("follows")
            if f and not email_written(f):
                out.append({"id": s["id"], "date": d, "channel": "sms",
                            "why": "the email it goes with (%s) has no written version" % f})
            elif not f:
                out.append({"id": s["id"], "date": d, "channel": "sms", "why": "it names no email to go with"})
    return out


def month_slots(brand, month):
    """The month's sends as the reviewer left them (cut sends gone), or [] when the month is not planned."""
    d = WORKSPACE / "runs" / "marketing-calendar" / brand / month
    if not (d / "slots.json").is_file():
        return []
    return RP.reviewed(d, json.loads((d / "slots.json").read_text()))


def for_brand(brand, start=None, days=14):
    start = start or date.today().isoformat()
    first = date.fromisoformat(start)
    months = sorted({(first + timedelta(days=i)).strftime("%Y-%m") for i in range(days)})
    slots = [s for m in months for s in month_slots(brand, m)]
    home = WORKSPACE / "runs" / "email-production" / brand

    def text_written(slot):
        f = home / ("%s-%s-sms" % (brand, slot["id"])) / "sms.json"
        if not f.is_file() or (f.parent / "off-page.json").exists():
            return "no text written for this send"
        rec = json.loads(f.read_text())
        if rec.get("date") != slot.get("date") or rec.get("follows") != slot.get("follows"):
            return "the text in %s was written for %s with %s; the calendar now has %s with %s" % (
                f.parent.name, rec.get("date"), rec.get("follows"), slot.get("date"), slot.get("follows"))
        return None

    return gaps(slots, start, days, lambda sid: bool(sms.email_runs(brand, sid)), text_written)


def unscheduled(texts, start, days, cut=()):
    """The texts in [start, start + days) that are written and not scheduled. `texts` are
    {"label", "slot", "date", "state", "card_state"} (card_state None when no card was made); `cut` holds the slot ids
    the reviewer cut. -> {"open": [{"label", "date", "why"}], "unconfirmed": [{"label", "date"}]} in date order."""
    end = (date.fromisoformat(start) + timedelta(days=days)).isoformat()
    out = {"open": [], "unconfirmed": []}
    for t in sorted(texts, key=lambda x: (x.get("date") or "", x.get("label") or "")):
        d = t.get("date") or ""
        if not (start <= d < end) or (t.get("state") or "").startswith("superseded") or t.get("slot") in cut:
            continue
        cs = t.get("card_state")
        if cs == SCHEDULED:
            continue
        if cs == PLACED_BY_HAND:
            out["unconfirmed"].append({"label": t["label"], "date": d})
            continue
        why = "no card made" if cs is None else "card is %s" % cs
        if (t.get("state") or "").startswith("held"):
            why += "; draft %s" % t["state"]
        out["open"].append({"label": t["label"], "date": d, "why": why})
    return out


def texts_of(brand):
    """Every written text the brand has, as unscheduled() reads it. A text kept off editor's page is not written."""
    home = WORKSPACE / "runs" / "email-production" / brand
    out = []
    for f in sorted(home.glob("*-sms/sms.json")):
        if (f.parent / "off-page.json").exists():
            continue
        rec = json.loads(f.read_text())
        card = f.parent / "sms-card.json"
        out.append({"label": f.parent.name, "slot": rec.get("slot"), "date": rec.get("date"),
                    "state": rec.get("state"),
                    "card_state": json.loads(card.read_text()).get("state") if card.is_file() else None})
    return out


def cut_slots(brand, months):
    """The slot ids the reviewer cut: in the plan as written, gone from the plan as reviewed."""
    cut = set()
    for m in months:
        d = WORKSPACE / "runs" / "marketing-calendar" / brand / m
        if (d / "slots.json").is_file():
            raw = json.loads((d / "slots.json").read_text())
            cut |= {s["id"] for s in raw} - {s["id"] for s in RP.reviewed(d, raw)}
    return cut


def texts_for_brand(brand, start=None, days=14):
    start = start or date.today().isoformat()
    first = date.fromisoformat(start)
    months = sorted({(first + timedelta(days=i)).strftime("%Y-%m") for i in range(days)})
    found = unscheduled(texts_of(brand), start, days, cut_slots(brand, months))
    if platform_of(brand) != "postscript":         # only a hand-placed platform has an unconfirmed state
        found["open"] += [dict(u, why="card is %s" % PLACED_BY_HAND) for u in found["unconfirmed"]]
        found["open"].sort(key=lambda x: (x["date"], x["label"]))
        found["unconfirmed"] = []
    return found


def text_lines(brand, found, start, days):
    out = ["Texts written, not scheduled (%s, %s for %d days; check the platform by hand):" % (brand, start, days)]
    out += ["  %s  %-22s %s" % (t["date"], t["label"], t["why"]) for t in found["open"]] or ["  none"]
    if found["unconfirmed"]:
        out.append("  placed by a person, not confirmed:")
        out += ["  %s  %s" % (t["date"], t["label"]) for t in found["unconfirmed"]]
    return out


def lines(brand, found, start, days):
    if not found:
        return ["coverage %s: every send from %s for %d days has something written" % (brand, start, days)]
    out = ["coverage %s: %d send(s) from %s for %d days with nothing written:" % (brand, len(found), start, days)]
    out += ["  %s  %-7s %-5s %s" % (g["date"], g["id"], g["channel"], g["why"]) for g in found]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", action="append", required=True)
    ap.add_argument("--from", dest="start", default=None, metavar="YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    start = a.start or date.today().isoformat()
    for b in a.brand:
        print("\n".join(lines(b, for_brand(b, start, a.days), start, a.days)))
        print("\n".join(text_lines(b, texts_for_brand(b, start, a.days), start, a.days)))


if __name__ == "__main__":
    main()
