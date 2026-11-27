#!/usr/bin/env python3
"""Swipe check: the gate every picture passes before it counts as done.

A picture is held up against its swipe and six things are checked and written down: STYLE (photo, illustration or
animated 3D, the same as the swipe), LAYOUT (the swipe's arrangement), WORDS (no stray text; the words fit what the
picture shows; nothing that looks painted onto skin unless the swipe has it), TEXTSTYLE (the type looks like the
swipe's), ANATOMY (no malformed legs, hands or feet) and PRODUCT (the real tube, one size, and only when the swipe shows
a product). Records from before version 2 keep their four checks until reopened. The swipe's own style is read out of the
teardown (out/01-teardown.md) and printed first, so the person or session making the check sees it before looking.

    python3 swipe_check.py show   <run> [<run> ...] [--brand brand_b]
        builds out/swipe-check.jpg (swipe left, ours right) and prints the swipe's style and the four checks
    python3 swipe_check.py record <run> --by <name> --style "same: <what both are>" --layout ok --words ok --textstyle ok --anatomy ok --product ok
        writes out/swipe-check.json (version 2); every check must be given, style with a few words that name it
    python3 swipe_check.py reopen <run> --why "<what is wrong>"
        marks a recorded ad open again until it is fixed and recorded again
    python3 swipe_check.py batch  <batch-number> [--brand brand_b] [--require]
        a table for one batch of dry-skin-batch/board-batches.json; --require exits 1 if any run is not fully checked

Works on any machine: reads only the repo's run folders and the board's picture folder. Pictures are the newest one
in runs/image-production/<brand>/prompt-bench/<run>*.png, else runs/image-teardown/<brand>/<run>/pictures/*.png.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHECKS_V1 = ("style", "layout", "words", "product")
CHECKS = ("style", "layout", "words", "textstyle", "anatomy", "product")      # version 2 (owner, 2 Nov): the type must look like the swipe's, bodies must be right, product only when the swipe has one
ASK = {
    "style": "same style as the swipe: photo, illustration or animated 3D",
    "layout": "same arrangement as the swipe",
    "words": "no stray text, the words fit what the picture shows (a headline about shins shows shins), no words that look painted onto skin unless the swipe has them",
    "textstyle": "the type looks like the swipe's: same font feel, box or no box, colour, weight, placement",
    "anatomy": "every body part is right: no malformed legs, hands or feet",
    "product": "the real tube, one size, one look, and ONLY when the swipe shows a product; no product in the swipe means none in ours",
}


def run_dir(brand, run):
    return REPO / "runs" / "image-teardown" / brand / run


def newest_picture(brand, run):
    bench = REPO / "runs" / "image-production" / brand / "prompt-bench"
    found = sorted(bench.glob(f"{run}*.png"), key=lambda f: f.stat().st_mtime) if bench.is_dir() else []
    if not found:
        found = sorted((run_dir(brand, run) / "pictures").glob("*.png"), key=lambda f: f.stat().st_mtime)
    return found[-1] if found else None


def swipe_style(brand, run):
    f = run_dir(brand, run) / "out" / "01-teardown.md"
    if not f.is_file():
        return ["(no teardown on this machine: unpack the run pack first)"]
    out = []
    for line in f.read_text().splitlines():
        m = re.search(r"\*\*(Overall treatment|Style label|Generation tells|Style anchor):\*\*\s*(.+)", line)
        if m:
            out.append(f"{m.group(1)}: {m.group(2).strip()[:220]}")
    return out or ["(the teardown names no style line)"]


def swipe_image(brand, run):
    for name in ("assets/source.jpg", "assets/source.png"):
        p = run_dir(brand, run) / name
        if p.is_file():
            return p
    return None


def record_path(brand, run):
    return run_dir(brand, run) / "out" / "swipe-check.json"


def load(brand, run):
    p = record_path(brand, run)
    return json.loads(p.read_text()) if p.is_file() else {}


def sheet(brand, run):
    from PIL import Image
    sw, pic = swipe_image(brand, run), newest_picture(brand, run)
    if not (sw and pic):
        return None
    a, b = Image.open(sw).convert("RGB"), Image.open(pic).convert("RGB")
    h = 900
    a, b = (im.resize((max(1, round(im.width * h / im.height)), h)) for im in (a, b))
    canvas = Image.new("RGB", (a.width + b.width + 12, h), "white")
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + 12, 0))
    out = run_dir(brand, run) / "out" / "swipe-check.jpg"
    canvas.save(out, quality=85)
    return out


def status(rec):
    if rec.get("reopened"):
        return False
    need = CHECKS if rec.get("v", 1) >= 2 else CHECKS_V1
    return all(rec.get(k) for k in need)


def cmd_show(a):
    for run in a.runs:
        print(f"\n== {run}")
        for line in swipe_style(a.brand, run):
            print("  swipe  ", line)
        pic = newest_picture(a.brand, run)
        print("  ours   ", pic if pic else "no picture yet")
        s = sheet(a.brand, run)
        if s:
            print("  side by side:", s)
        rec = load(a.brand, run)
        if rec.get("reopened"):
            print("  REOPENED:", rec["reopened"])
        for k in CHECKS:
            print(f"  {k:9}", rec.get(k) or "NOT CHECKED", "|", ASK[k])
        print("  ->", "checked by " + rec.get("by", "?") if status(rec) else "NOT DONE until all four are recorded")


def cmd_record(a):
    vals = {k: getattr(a, k) for k in CHECKS}
    miss = [k for k, v in vals.items() if not v]
    if miss:
        sys.exit("give every check: missing " + ", ".join(miss) + ". Look at out/swipe-check.jpg first.")
    if len(a.style.split()) < 3:
        sys.exit('style needs a few words that name it, for example --style "same: both animated 3D cartoon"')
    pic = newest_picture(a.brand, a.run)
    rec = {**vals, "v": 2, "by": a.by, "picture": str(pic.name) if pic else None,
           "swipe_style": swipe_style(a.brand, a.run)}
    record_path(a.brand, a.run).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print("recorded", record_path(a.brand, a.run))


def cmd_reopen(a):
    rec = load(a.brand, a.run)
    rec["reopened"] = a.why
    record_path(a.brand, a.run).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print("reopened", a.run, "-", a.why)


def cmd_batch(a):
    plan = REPO / "runs" / "image-teardown" / a.brand / "dry-skin-batch" / "board-batches.json"
    batches = json.loads(plan.read_text())
    runs = batches[a.number - 1]
    bad = 0
    for r in runs:
        rec = load(a.brand, r)
        ok = status(rec)
        bad += not ok
        print(("OK   " if ok else "OPEN ") + r)
    if a.require and bad:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("runs", nargs="+"); s.add_argument("--brand", default="brand_b"); s.set_defaults(f=cmd_show)
    r = sub.add_parser("record"); r.add_argument("run"); r.add_argument("--brand", default="brand_b"); r.add_argument("--by", required=True)
    for k in CHECKS:
        r.add_argument("--" + k, help=ASK[k])
    r.set_defaults(f=cmd_record)
    o = sub.add_parser("reopen"); o.add_argument("run"); o.add_argument("--brand", default="brand_b"); o.add_argument("--why", required=True); o.set_defaults(f=cmd_reopen)
    b = sub.add_parser("batch"); b.add_argument("number", type=int); b.add_argument("--brand", default="brand_b"); b.add_argument("--require", action="store_true"); b.set_defaults(f=cmd_batch)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
