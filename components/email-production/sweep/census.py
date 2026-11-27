#!/usr/bin/env python3
"""The sweep, step 1: census every email in the format bank. (the owner,
2026-08-31: "this is bigger than just the simple 8" — so the format
vocabulary is read off ALL the boards, not the sample.)

    python3 sweep/census.py --bank <path-to-format-bank> \
        --out runs/email-production/<brand>/facts-<YYYY-MM-DD>/email-sms/design-formats

Parses vfs-src/<board>.jsx (the handoff's exact-value transcriptions),
registers every email artboard (550-820px wide per the handoff's rule),
extracts design features from its inline styles, and clusters recurring
format families. Output: census.json + census.md in --out, which may never sit
under brands/ (K2 (brands write wall)): write it in a run folder and a person
folds it in. Deterministic — no model calls, nothing invented.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import refuse_brand_write  # noqa: E402

ARTBOARD = re.compile(
    r'<div data-name=\{"(?P<name>[^"]+)"\} style=\{\{\s*'
    r'position: "absolute",\s*left: [\d.-]+,\s*top: [\d.-]+,\s*'
    r'width: (?P<w>\d+(?:\.\d+)?),\s*height: (?P<h>\d+(?:\.\d+)?),', re.S)
IMPORTED = re.compile(
    r'<(?P<comp>[A-Za-z0-9]+) /> \{/\* → [^(]*\((?P<w>\d+)×(?P<h>\d+) at [\d.,\s-]+\) \*/\}')


def features(seg):
    f = {}
    f["serif_uses"] = len(re.findall(r'fontFamily: "(?:GT Super|Gt Super)[^"]*"', seg))
    f["sans_uses"] = len(re.findall(r'fontFamily: "Untitled Sans[^"]*"', seg))
    sizes = [float(x) for x in re.findall(r"fontSize: ([\d.]+)", seg)]
    f["max_font"] = max(sizes) if sizes else 0
    f["images"] = len(re.findall(r'backgroundImage: "url\(', seg)) + seg.count("<img")
    f["glass"] = bool(re.search(r"linear-gradient\(270deg, rgba\(12,\s*16,\s*15", seg))
    f["glow"] = bool(re.search(r"radial-gradient", seg)) or seg.count("Ellipse") > 2
    f["confetti"] = "onfetti" in seg
    f["ctas"] = len(re.findall(r"height: (?:61\.5|62|70\.4|70),", seg))
    bgs = Counter(re.findall(r'backgroundColor: "(rgb\([^"]+\))"', seg))
    f["bg"] = bgs.most_common(1)[0][0] if bgs else ""
    return f


def bg_family(bg):
    m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", bg or "")
    if not m:
        return "unknown"
    r, g, b = map(int, m.groups())
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum > 180:
        return "light"
    if g > r + 15 and g > 40:
        return "deep-green"
    if b > r + 60:
        return "blue"
    return "dark"


def family(email):
    f = email
    h = f["h"]
    tall = "tall" if h > 3200 else ("mid" if h > 2200 else "short")
    parts = [bg_family(f.get("bg", ""))]
    if f.get("serif_uses", 0) and f.get("max_font", 0) >= 46:
        parts.append("bigserif")
    if f.get("glass"):
        parts.append("glass")
    if f.get("confetti"):
        parts.append("offer")
    dens = f.get("images", 0)
    parts.append("imageheavy" if dens >= 8 else ("imaged" if dens >= 3 else "typeled"))
    parts.append(tall)
    return "/".join(parts)


MONTHS = {"jan":"January","feb":"February","mar":"March","apr":"April",
          "may":"May","jun":"June","jul":"July","aug":"August","sep":"September",
          "oct":"October","nov":"November","dec":"December"}


def board_month(board):
    """The bank is organized by month — keep that organization first-class."""
    m = re.match(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(\d{4})", board)
    if m:
        return f"{m.group(2)}-{list(MONTHS).index(m.group(1))+1:02d}", \
               f"{MONTHS[m.group(1)]} {m.group(2)}" + (" (flow)" if "flow" in board else "")
    return "9999-99", board


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    outdir = refuse_brand_write(a.out)
    bank = Path(a.bank).expanduser()
    emails = []
    for jsx in sorted((bank / "vfs-src").glob("*.jsx")):
        board = jsx.stem
        text = jsx.read_text(errors="replace")
        # positions of every artboard-shaped div; each segment runs to the next
        marks = []
        for m in ARTBOARD.finditer(text):
            w, h = float(m.group("w")), float(m.group("h"))
            if 550 <= w <= 820 and h >= 700:
                marks.append((m.start(), m.group("name"), w, h))
        for i, (pos, name, w, h) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            seg = text[pos:end]
            mk, ml = board_month(board)
            e = dict(board=board, month=ml, month_key=mk,
                     name=name.strip(), w=int(w), h=int(h),
                     detail=True, **features(seg))
            emails.append(e)
        # imported one-liners: name + size only, detail lived elsewhere
        for m in IMPORTED.finditer(text):
            w, h = int(m.group("w")), int(m.group("h"))
            if 550 <= w <= 820 and h >= 700:
                mk, ml = board_month(board)
                emails.append(dict(board=board, month=ml, month_key=mk,
                                   name=m.group("comp"), w=w, h=h, detail=False))
    for e in emails:
        e["family"] = family(e) if e["detail"] else "(structure elsewhere)"

    fams = Counter(e["family"] for e in emails if e["detail"])
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "census.json").write_text(json.dumps(
        {"generated": "2026-08-31", "source": "format-bank/vfs-src (exact transcriptions)",
         "emails": emails,
         "families": dict(fams.most_common())}, indent=1) + "\n")

    boards = Counter(e["board"] for e in emails)
    L = ["# The email census — every design in the bank, registered", "",
         f"{len(emails)} emails across {len(boards)} boards, read from the "
         "handoff's exact-value transcriptions. Families are clustered on "
         "measured features (ground, display type, glass, offer dressing, "
         "image density, length) — the raw material for the format set that "
         "is bigger than the sample 8.", "",
         "## Recurring families (detailed emails only)", "",
         "| Family | Count |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in fams.most_common()]
    L += ["", "## Per board", "", "| Board | Emails |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(boards.items())]
    L += ["", "## Every email — in the bank's own month order", "",
          "| Month | Email | Size | Family |", "|---|---|---|---|"]
    for e in sorted(emails, key=lambda x: (x["month_key"], x["board"], x["name"])):
        L.append(f"| {e['month']} | {e['name']} | {e['w']}×{e['h']} | {e['family']} |")
    (outdir / "census.md").write_text("\n".join(L) + "\n")
    print(f"{len(emails)} emails registered · {len(fams)} families -> {outdir}/census.md")


if __name__ == "__main__":
    main()
