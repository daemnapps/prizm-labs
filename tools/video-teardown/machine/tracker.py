#!/usr/bin/env python3
"""Read the brand's creator tracker directly, instead of a typed-out copy.

    python3 tracker.py --check     what the sheet says vs what we hold
    python3 tracker.py --sync      rewrite creators.json from the sheet

`creators.json` was a copy of the tracker somebody typed by hand, once. The
sheet kept moving; the copy did not. Pam was a signed partner sitting on the
sheet marked "waiting for brief" and the machine had never heard of her — found
on 2026-08-27 only because two lists were compared by eye. Her top post turned
out to be the biggest on the whole roster.

The service account can already read the sheet, so there is no reason to keep
a copy. A row that cannot be right — a handle that resolves nowhere, a platform
that disagrees with its own link — is said out loud instead of silently doing
nothing (which is how Katie sat unpullable all day).
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import drive as D

# The tracker lives in the brand's own folder, never hard-coded per brand:
# brands/<brand>/tracker.json names the sheet. Falls back to the id below only
# for <brand>, which is what exists today.
CREATORS = HERE / "creators.json"
PARTNER_TAB_HINT = "Handle"


def sheet_id(brand):
    f = HERE.parent.parent.parent / "brands" / brand / "tracker.json"
    if f.is_file():
        return json.loads(f.read_text()).get("sheet_id")
    return None


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def read_sheet(sid):
    """Every tab, as rows.

    CSV export returns only the FIRST tab, which is the prospecting list — the
    partners are on the second, so a CSV read finds zero partners and looks
    exactly like an empty sheet (2026-08-27). The Sheets API would be cleaner
    but is not enabled on the Google project; an xlsx export needs nothing
    beyond the Drive read we already have."""
    import io, openpyxl
    svc = D.service()
    data = svc.files().export(fileId=sid, mimeType=XLSX).execute()
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    rows = []
    for name in wb.sheetnames:
        for r in wb[name].iter_rows(values_only=True):
            rows.append(["" if c is None else str(c) for c in r])
    return rows


def partners(rows):
    """Rows from the partners tab: the one whose header carries a Handle
    column and a Rate column."""
    out, head = [], None
    for r in rows:
        cells = [c.strip() for c in r]
        if not any(cells):
            continue
        low = [c.lower() for c in cells]
        if "handle" in low and any("rate" in c for c in low):
            head = {c.lower(): i for i, c in enumerate(cells)}
            continue
        if not head:
            continue
        def g(k, d=""):
            i = head.get(k)
            return cells[i].strip() if i is not None and i < len(cells) else d
        name, url = g("creator name"), g("handle")
        if not name or not url.startswith("http"):
            continue
        out.append({"name": name, "url": url,
                    "platform": "TikTok" if "tiktok.com" in url else "Instagram",
                    "stated_platform": g("platform"),
                    "rate": g("rate"), "status": g("status"),
                    "done": g("videos done")})
    return out


def handle_of(url):
    m = re.search(r"(?:instagram\.com|tiktok\.com)/@?([^/?#]+)", url or "")
    return (m.group(1) if m else "").lstrip("@")


def compare(brand):
    if not brand:
        raise SystemExit("tracker: no brand named — say which with --brand "
                         "(there is no default brand; rule 4)")
    sid = sheet_id(brand)
    if not sid:
        return None, [f"no tracker.json for brand '{brand}' — nothing to read"]
    rows = partners(read_sheet(sid))
    have = {handle_of(c.get("url")): c for c in json.loads(CREATORS.read_text())}
    notes = []
    for p in rows:
        h = handle_of(p["url"])
        if h not in have:
            notes.append(f"ON THE SHEET, NOT IN THE MACHINE — {p['name']} ({h})")
        sp = (p.get("stated_platform") or "").lower()
        if sp and sp != p["platform"].lower():
            notes.append(f"ROW CONTRADICTS ITSELF — {p['name']}: platform says "
                         f"{p['stated_platform']}, link is {p['platform']}")
    sheet_handles = {handle_of(p["url"]) for p in rows}
    for h, c in have.items():
        if c.get("partner") and h not in sheet_handles:
            notes.append(f"IN THE MACHINE, NOT A PARTNER ON THE SHEET — {c['name']} ({h})")
    return rows, notes


def main():
    ap = argparse.ArgumentParser(description="The creator tracker, read directly.")
    ap.add_argument("--brand", required=True,
                    help="which brand's creator tracker to read "
                         "(brands/<brand>/tracker.json names the sheet). "
                         "Named every time — there is no default brand (rule 4).")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--sync", action="store_true")
    a = ap.parse_args()

    rows, notes = compare(a.brand)
    if rows is None:
        for n in notes:
            print("  " + n)
        return
    print(f"  {len(rows)} partner(s) on the sheet")
    for n in notes:
        print("  " + n)
    if not notes:
        print("  the sheet and the machine agree")
    if a.sync:
        cur = {handle_of(c.get("url")): c for c in json.loads(CREATORS.read_text())}
        out = []
        for p in rows:
            h = handle_of(p["url"])
            base = cur.get(h, {})
            out.append({**base, "name": p["name"], "url": p["url"],
                        "platform": p["platform"], "partner": True,
                        "rate": p["rate"], "status": p["status"],
                        "brand": a.brand})
        for h, c in cur.items():
            if not c.get("partner"):
                out.append(c)
        CREATORS.write_text(json.dumps(out, indent=2) + "\n")
        print(f"  creators.json rewritten from the sheet — "
              f"{sum(1 for c in out if c.get('partner'))} partners")


if __name__ == "__main__":
    main()
