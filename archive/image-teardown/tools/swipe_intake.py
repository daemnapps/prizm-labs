#!/usr/bin/env python3
"""Pull a swipe out of the swipe library and open a run on it.

    swipe_intake.py --list <competitor>
    swipe_intake.py --brand <competitor> --angle 03
    swipe_intake.py --brand <competitor> --angle 03 --ad 151224660 --run 2026-08-29-serum

The image lane used to take a file path someone remembered. That meant a run
could not say what it was a copy of, and the same ad could arrive twice under
two names. The swipe library already records every angle a brand runs — the
copy verbatim, the landing page, how many creatives it carries and how often
one got cloned — so a run starts from a swipe id, not a path.

**Code in the repo, pictures on Drive** (`README.md`). The angle
records live here in git; the creatives live at the mirrored Drive path. This
reads the record from git and copies the one picture it needs off Drive into
the run, so the run holds the ad it was built from and nothing else.
"""

import argparse, json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as _P
LAB = _P.LAB                                              # lab/damon — found, not counted
# The library split into swipe-paid / swipe-organic; plain "swipe" has not
# existed since, so intake could not open a single run from a swipe id.
SWIPE = LAB / "swipe-paid"
DRIVE = Path.home() / (
    "Library/CloudStorage/GoogleDrive-${DRIVE_ACCOUNT}/"
    "Shared drives/Shared Assets/swipe-paid")
RUNS = LAB / "image-teardown" / "runs"


def angles(brand):
    d = SWIPE / brand / "angles"
    if not d.is_dir():
        sys.exit(f"no swipe brand {brand!r} — have: "
                 + ", ".join(sorted(p.name for p in SWIPE.iterdir()
                                    if p.is_dir() and not p.name.startswith("_"))))
    return sorted(d.glob("*.md"))


def read_angle(p):
    t = p.read_text()
    def grab(pat, cast=str):
        m = re.search(pat, t, re.M)
        return cast(m.group(1).strip()) if m else None
    imgs = grab(r"\*\*(\d+) live creatives?\*\*.*?(\d+) image", lambda s: s)
    m = re.search(r"\*\*(\d+) live creatives?\*\*\s*—\s*(\d+) video, (\d+) image", t)
    return dict(
        key=p.stem,
        rank=p.stem.split("_")[0],
        title=grab(r"^#\s*\d+\s*·\s*(.+)$"),
        headline=grab(r"^>\s*(.+)$"),
        creatives=int(m.group(1)) if m else None,
        video=int(m.group(2)) if m else None,
        image=int(m.group(3)) if m else None,
        cloned=grab(r"most-cloned single creative ran (\d+x)"),
        page=grab(r"\*\*Landing page:\*\*\s*`([^`]+)`"),
        drive=grab(r"\*\*Drive:\*\*\s*`([^`]+)`"),
        record=str(p.relative_to(LAB)),
    )


def photos(brand, key):
    d = DRIVE / brand / "angles" / key / "photos"
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", metavar="BRAND")
    ap.add_argument("--brand")
    ap.add_argument("--angle", help="rank prefix, e.g. 03")
    ap.add_argument("--ad", help="ad id; omit to list what the angle holds")
    ap.add_argument("--run", help="run folder name; default is dated + angle")
    a = ap.parse_args()

    brand = a.list or a.brand
    if not brand:
        ap.error("--list BRAND or --brand BRAND")

    recs = [read_angle(p) for p in angles(brand)]

    if a.list:
        print(f"{brand} — {len(recs)} angles\n")
        for r in recs:
            if not r["image"]:
                continue
            heat = f"cloned {r['cloned']}" if r["cloned"] else "not cloned"
            print(f"  {r['rank']}  {r['image']:>3} statics  {heat:<12}  {r['title']}")
        print("\n(angles with no statics are hidden — this lane only takes stills)")
        return

    if not a.angle:
        ap.error("--angle is required")
    hit = next((r for r in recs if r["rank"] == a.angle.zfill(2)), None)
    if not hit:
        sys.exit(f"no angle {a.angle!r} for {brand}")

    pics = photos(brand, hit["key"])
    if not a.ad:
        print(f"{hit['rank']} · {hit['title']}")
        print(f"  {hit['image']} statics, most-cloned ran {hit['cloned']}")
        print(f"  landing page: {hit['page']}")
        print(f"  on Drive: {len(pics)} files\n")
        for p in pics[:40]:
            print("   ", p.stem)
        if len(pics) > 40:
            print(f"    … and {len(pics)-40} more")
        return

    src = next((p for p in pics if p.stem == a.ad), None)
    if not src:
        sys.exit(f"ad {a.ad!r} not on Drive for this angle "
                 f"({len(pics)} there). Is Drive mounted?")

    run = RUNS / (a.run or f"{brand}-{hit['rank']}-{a.ad}")
    (run / "assets").mkdir(parents=True, exist_ok=True)
    (run / "out").mkdir(exist_ok=True)
    (run / "vars").mkdir(exist_ok=True)
    shutil.copy2(src, run / "assets" / f"source{src.suffix}")

    prov = dict(brand=brand, ad_id=a.ad, angle=hit["key"], angle_title=hit["title"],
                headline=hit["headline"], landing_page=hit["page"],
                statics_in_angle=hit["image"], most_cloned=hit["cloned"],
                swipe_record=hit["record"], drive=hit["drive"],
                pulled_from="swipe-paid via Drive mirror")
    (run / "assets" / "source.json").write_text(json.dumps(prov, indent=2) + "\n")
    print(f"run opened: {run.relative_to(LAB)}")
    print(f"  source:  assets/source{src.suffix}")
    print(f"  swipe:   {hit['rank']} · {hit['title']}")
    print(f"  heat:    {hit['image']} statics in this angle, most-cloned ran {hit['cloned']}")


if __name__ == "__main__":
    main()
