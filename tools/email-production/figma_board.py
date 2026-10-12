#!/usr/bin/env python3
"""The month's board, as one Figma payload.

    python3 figma_board.py --brand brand-b --month 2026-09 > board.js

The board used to be drawn by whatever connector script a session happened to
write that day, which meant a rebuild was a rewrite and no two months looked
alike. This emits the whole section from the run folders: one heading per SEND,
its versions side by side beneath it, each version a wireframe in the brand's
own palette with a caption above it.

What the board is (RULED 2026-09-09, the owner: "the machine does not design"):
shape and order, not design. A wireframe the designer reads and then designs
from — headline / subhead / body / button / picture, in the order the chain
proposed, with the picture directions written on their grey boxes.

What the board obeys:
- **one send a day** — the columns run in date order, one date per heading
- **a send is not a version** — versions sit under one heading, not beside it
- **the tag is the send date**, never the slot's ordinal

Brand-agnostic: the palette and type come from the brand's own
`email-sms/design-formats/components.json`. Nothing here knows a colour.
"""
import argparse
import json
from pathlib import Path

import figma_brief as FB
from paths import HERE, WORKSPACE

W_COL, GAP, TOP = 700, 160, 30000          # column width, gap between sends, where the band sits
PAD, LINE = 28, 14


def palette(brand):
    f = WORKSPACE / "brands" / brand / "email-sms" / "design-formats" / "components.json"
    d = json.loads(f.read_text()) if f.is_file() else {}
    p = d.get("palette", {})
    return {
        "canvas": p.get("canvas", "#0c100f"),
        "surface": p.get("surface", "#171a18"),
        "raised": p.get("surface_raised", "#1e211d"),
        "ink": p.get("ink", "#f2f6ea"),
        "muted": p.get("ink_muted", "#cabbac"),
        "accent": p.get("accent", "#c7cfad"),
        "cta_bg": p.get("cta_bg", "#c7cfad"),
        "cta_ink": p.get("cta_ink", "#0c100f"),
    }


def sends(brand, month):
    """Every send in date order, each with its versions — the board's own shape."""
    cal = HERE / "results" / f"calendar-{month}"
    rows = json.loads((cal / "slots.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("slots", [])
    out = []
    for s in sorted(rows, key=lambda r: r["date"]):
        versions = []
        for p in sorted((HERE / "results").glob(f"{s['id']}*")):
            if not p.is_dir() or not (p / "design.json").is_file():
                continue
            if p.name.split("--")[0] != s["id"]:
                continue
            variant = p.name.split("--", 1)[1] if "--" in p.name else ""
            try:
                blocks = FB.wire_blocks(p, brand)
            except Exception as e:                      # a run that never finished
                blocks = [{"k": "B", "t": f"[this version has no built copy: {e}]"}]
            subj, prev = FB.subject_preview(p)
            versions.append({"variant": variant, "blocks": blocks,
                             "subject": subj, "preview": prev,
                             "facts": len(json.loads((p / "design.json").read_text())
                                          .get("open_facts", []))})
        if versions:
            out.append({"slot": s, "versions": versions})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--month", default="2026-09")
    ap.add_argument("--section", default=None, help="the section name on the page")
    a = ap.parse_args()

    C = palette(a.brand)
    data = sends(a.brand, a.month)
    y, m = a.month.split("-")
    label = a.section or (f"{a.brand.upper()} "
                          f"{['January','February','March','April','May','June','July','August','September','October','November','December'][int(m)-1]}"
                          f" {y} — one send a day")

    payload = {"section": label, "palette": C, "top": TOP, "col": W_COL, "gap": GAP,
               "pad": PAD, "line": LINE, "sends": []}
    for s in data:
        slot = s["slot"]
        dd = slot["date"][-2:]
        mon = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"][int(m) - 1]
        payload["sends"].append({
            "tag": f"{mon} {dd}",
            "type": slot.get("type", ""),
            "segment": slot.get("segment", ""),
            "offer": slot.get("offer") or "none",
            "occasion": (slot.get("occasion") or "")[:90],
            "versions": s["versions"],
        })
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
