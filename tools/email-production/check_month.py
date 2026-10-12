#!/usr/bin/env python3
"""Read a month's finished copy and say what is wrong with it.

    python3 check_month.py --brand brand-b --month 2026-09
    python3 check_month.py --brand brand-b --month 2026-09 --only moment

Zero cost, no model calls. Every finding names the run, the check and the line,
so it can be fixed or ruled on. This exists because two whole classes of fault
shipped to the board unnoticed:

**THE MOMENT** (RULED 2026-09-10, the owner: "this literally has nothing to do with
football"). A send scheduled on a dated moment came out with no trace of that
moment in it — the occasion reached the filing layer and never reached a stage
that writes. A reader must be able to name the moment from the copy alone, so
that is what this checks.

**THE SEND DAY.** Copy borrowed the swiped email's weekday, so a September send
opened "It's Monday" on a Saturday.

The rest are mechanics — the things a person would catch reading it aloud, and
therefore the things nobody catches reading thirty of them.

Brand-agnostic: every brand fact comes from the brand's own moments file and
its slots, never from this file.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from paths import HERE, WORKSPACE

STOP = {"season", "day", "days", "the", "of", "and", "week", "month"}

# A moment is named in copy by its own words OR by the words people actually
# use for it. Only genuinely ambiguous keys need a row here; the rest are
# matched off the key itself.
ALSO = {
    "nfl": ["football", "sunday", "kickoff", "gameday", "game day", "touchdown",
            "quarterback", "tailgate", "the league"],
    "photos": ["photo", "picture day", "yearbook", "class photo"],
    "school": ["school", "classroom", "first day back", "back-to-school"],
    "prime": ["prime day"],
    "labor": ["labor day", "long weekend"],
    "halloween": ["halloween", "costume", "trick or treat"],
    "thanksgiving": ["thanksgiving", "the table", "family dinner"],
    "bfcm": ["black friday", "cyber monday"],
    "christmas": ["christmas", "the holidays", "gift"],
}
DIRECTION = re.compile(
    r"must read as|close on |a screenshot of|photographed|shot on|packshot|"
    r"overhead shot|so a reader|with images off|reads as a plain sentence",
    re.I)
# a sentence that stops where its fact should be
# Words that cannot end an English sentence. "for." and "like." can, so they
# are not here — flagging those buried the real holes under false alarms.
# The signature of a fact that was never supplied: a gap left before the full
# stop ("we just got word that ."), or a sentence ending on a word English
# cannot end on. "that.", "to.", "for." and "like." CAN end a sentence, so they
# are not here — flagging them buried the real holes under false alarms.
STUB = re.compile(r"\s[.!?]$|\b(said|because|and|but|with|the|a|an|than)\s*[.!?]$", re.I)
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def copy_of(run_dir):
    """Every written line in the finished email, in order."""
    f = run_dir / "design.json"
    if not f.is_file():
        return []
    out = []
    for b in json.loads(f.read_text()).get("blocks", []):
        t = (b.get("text") or b.get("label") or "").strip()
        if t:
            out.append((b.get("type", "?"), t))
    return out


def moment_words(occasion):
    """What this moment would sound like if the copy really carried it."""
    key = (occasion or "").split(" — ")[0].strip().strip("`")
    words = [w for w in re.split(r"[-_\s]+", key.lower()) if w and w not in STOP]
    out = list(words)
    for w in words:
        out += ALSO.get(w, [])
    return key, sorted(set(out))


def misspellings(text, brand):
    """The brand's own name, spelled wrong. Brand-agnostic: the name comes from
    the run, and anything one transposition away from it is a typo (DOXUDS)."""
    out = set()
    b = brand.lower()
    for w in set(re.findall(r"\b[A-Za-z]{4,12}\b", text)):
        lw = w.lower()
        if lw == b or len(lw) != len(b) or sorted(lw) != sorted(b):
            continue
        out.add(w)
    return sorted(out)


# A holiday named in copy that the send does not sit in. Brand-agnostic: the
# windows come from the brand's own moments file; this list is only what the
# words look like in prose, and an unknown one is simply not checked.
HOLIDAY = re.compile(
    r"labor day|memorial day|father'?s day|mother'?s day|easter|black friday|"
    r"cyber monday|prime day|christmas|new year|halloween|thanksgiving|"
    r"independence day|4th of july|king'?s month|valentine'?s", re.I)
# an offer, in the words copy actually uses
PRICE = re.compile(r"\$\d|\b\d{1,3}% ?off\b|\bsave up to\b|\bfree \w+ with\b|"
                   r"\bdiscount\b|\bcloses tomorrow\b|\bends (tonight|today|tomorrow)\b|"
                   r"\bwhile stock lasts\b|\bcomplimentary\b", re.I)


def check(run_dir, slot, brand):
    lines = copy_of(run_dir)
    if not lines:
        return []
    text = " ".join(t for _, t in lines)
    low = text.lower()
    found = []

    # The calendar said what this send sells. Copy that sells something else is
    # the source's week leaking through (RULED 2026-09-10).
    if (slot.get("offer") or "none") == "none":
        m = PRICE.search(text)
        if m:
            i = max(0, m.start() - 60)
            found.append(("OFFER", f"the calendar gave this send NO offer and the copy sells "
                                   f"anyway — “…{text[i:m.end() + 40]}…”"))
    for m in HOLIDAY.finditer(text):
        found.append(("STALE MOMENT", f"names “{m.group(0)}” — check it against the "
                                      f"{slot.get('date')} send date before this ships"))

    for w in misspellings(text, brand):
        found.append(("BRAND", f"the brand's own name spelled “{w}”"))

    occ = (slot.get("occasion") or "").strip()
    dated = occ and not occ.startswith("recorded problem") and not occ.startswith("HELD OPEN")
    if dated:
        key, words = moment_words(occ)
        if words and not any(w in low for w in words):
            found.append(("MOMENT", f"scheduled on `{key}` and the copy never names it — "
                                    f"nothing matching {', '.join(words[:6])}"))

    # Only a weekday used AS TODAY is wrong. "by Sunday the brush is on the
    # shelf" and "the brotherhood who shave Monday morning" are narrative, and
    # flagging those buries the real ones.
    date = slot.get("date")
    if date:
        real = datetime.date.fromisoformat(date).strftime("%A").lower()
        for d in DAYS:
            if d == real:
                continue
            m = re.search(rf"\b(happy|good|it'?s|today is)\s+{d}\b", low)
            if m:
                found.append(("SEND DAY", f"opens “{m.group(0)}” but goes out on "
                                          f"{real.capitalize()} {date}"))

    for kind, t in lines:
        if "[UNFILLED" in t:
            found.append(("UNFILLED", f"{kind}: {t[:90]}"))
        if "(TM)" in t or "(tm)" in t:
            found.append(("MARK", f"{kind}: (TM) written out instead of ™ — {t[:70]}"))
        if "  " in t:
            found.append(("SPACING", f"{kind}: double space — {t[:70]}"))
        if re.search(r" [,.;:!?]", t):
            found.append(("SPACING", f"{kind}: space before punctuation — {t[:70]}"))
        m = re.search(r"\b(\w+)\s+\1\b", t, re.I)
        if m and m.group(1).lower() not in ("that", "had"):
            found.append(("DOUBLED", f"{kind}: “{m.group(0)}” — {t[:70]}"))
        if "'" in t and "’" in t:
            found.append(("QUOTES", f"{kind}: straight and curly apostrophes in one line — {t[:70]}"))
        # a block already broken into paragraphs is laid out, not a wall
        if kind == "copy" and len(t) > 400 and "\n\n" not in t:
            found.append(("WALL", f"{len(t)} characters in one block — {t[:70]}"))
        # art direction written as if it were copy. It reaches the reader as a
        # sentence about a photograph nobody took (RULED 2026-09-10 — one send
        # shipped a note to the designer as a line in the email).
        if kind in ("copy", "headline", "subhead") and DIRECTION.search(t):
            found.append(("DIRECTION", f"{kind}: reads as a note to the designer, not copy — {t[:80]}"))
        # A sentence whose fact was never supplied. The chain is right to refuse
        # to invent one, but it leaves the hole open: "After week 1, we said."
        for s in ([] if kind in ("footer", "preheader") else re.split(r"(?<=[.!?])\s+", t)):
            s = s.strip()
            if 4 < len(s) < 90 and STUB.search(s):
                found.append(("STUB", f"{kind}: a sentence with its fact missing — “{s}”"))
                break

    # a CTA is SUPPOSED to repeat — a button echoing the headline, the same
    # button twice down a long email. Only prose repeating prose is a fault.
    PROSE = ("copy", "headline", "subhead", "preheader", "quote", "bullets", "ps")
    seen = {}
    for kind, t in lines:
        k = re.sub(r"[^a-z0-9 ]", "", t.lower())[:70]
        if k and k in seen and kind in PROSE and seen[k] in PROSE:
            found.append(("REPEAT", f"{kind} repeats an earlier {seen[k]}: {t[:70]}"))
        seen[k] = kind
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--month", default="2026-09")
    ap.add_argument("--only", default=None, help="one check name, e.g. moment")
    a = ap.parse_args()

    cal = HERE / "results" / f"calendar-{a.month}"
    rows = json.loads((cal / "slots.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("slots", [])
    by_id = {r["id"]: r for r in rows}
    abbr = rows[0]["id"].rsplit("-", 1)[0] if rows else ""

    runs = sorted(p for p in (HERE / "results").glob(f"{abbr}-*")
                  if p.is_dir() and (p / "design.json").is_file())
    total, clean = 0, 0
    for r in runs:
        slot = by_id.get(r.name.split("--")[0])
        if not slot:
            continue
        found = check(r, slot, a.brand)
        if a.only:
            found = [f for f in found if f[0].lower() == a.only.lower()]
        if not found:
            clean += 1
            continue
        print(f"\n{r.name}  ({slot.get('date')} · {slot.get('type')})")
        for what, why in found:
            print(f"  {what:9} {why}")
        total += len(found)
    print(f"\n{len(runs)} runs · {clean} clean · {total} finding(s)")


if __name__ == "__main__":
    main()
