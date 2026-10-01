#!/usr/bin/env python3
"""The draft standard, as one command. DRAFT-STANDARD.md is the ruling.

    draft.py --brand <brand>                    every finished brief
    draft.py --brand <brand> --briefs p152      just these
    draft.py --brand <brand> --no-ship          stop after the judge

Damon, 2026-09-17: "THIS IS THE STANDARD WE OPERATE WITH. DO NOT DEVIATE THIS
AT ALL AND LOCK IN THE PROMPT / WORKFLOW." So the workflow is one command
with no options that change it: three rolls per brief with the swipe as the
reference, every roll judged, the best passing roll shipped — to the brief's
Drive folder, the brand's pack and the Brief Board. A brief the judge passes
nothing for ships no draft and its reason.

Each run is a new version folder under drafts/<brand>/ (v7, v8, …), so the
last judged set is always the newest and nothing is overwritten.
"""
import argparse, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ROLLS = 3
ROUNDS = 4          # rounds of ROLLS before the best available ships flagged


def sh(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT)
    if r.returncode:
        sys.exit(f"stopped: {' '.join(str(a) for a in args[:2])} failed")


def next_version(brand):
    d = ROOT / "drafts" / brand
    n = max((int(m.group(1)) for x in d.glob("v*") if x.is_dir()
             for m in [re.fullmatch(r"v(\d+)", x.name)] if m), default=0)
    return f"drafts/{brand}/v{n + 1}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--briefs")
    ap.add_argument("--no-ship", action="store_true")
    ap.add_argument("--product", help="pack this product's briefs (default: the brand's baseline product)")
    a = ap.parse_args()
    out = next_version(a.brand)
    sel = ["--briefs", a.briefs] if a.briefs else []

    print(f"── 1–5 · generate · {ROLLS} rolls each, the swipe as the reference → {out}")
    sh(HERE / "fal_drafts.py", "--brand", a.brand, "--count", str(ROLLS),
       "--match-swipe", "--out", out, *sel)
    print(f"\n── 6 · judge · every roll, best passing one becomes the draft")
    sh(HERE / "draft_judge.py", "--brand", a.brand, "--dir", out, *sel)
    # Damon, 2026-09-17: "if a draft didn't make it then you need to
    # generate." A reject is not an end state. Whatever the judge passed
    # nothing for gets another round of three rolls, judged again, up to
    # ROUNDS rounds. What still has no passing roll ships the best roll it
    # has — highest match, fewest fails — flagged on the board with what it
    # failed, so there is always a draft and never a hole.
    d = ROOT / out
    for rnd in range(2, ROUNDS + 1):
        left = sorted({x.stem[:4] for x in d.glob("p*-roll-*.png")}
                      - {x.stem[:4] for x in d.glob("p*-draft.png")})
        if not left:
            break
        print(f"\n── 6 · round {rnd} for {', '.join(left)}")
        sh(HERE / "fal_drafts.py", "--brand", a.brand, "--count", str(ROLLS),
           "--match-swipe", "--out", out, "--briefs", ",".join(left))
        sh(HERE / "draft_judge.py", "--brand", a.brand, "--dir", out,
           "--briefs", ",".join(left))
    left = sorted({x.stem[:4] for x in d.glob("p*-roll-*.png")}
                  - {x.stem[:4] for x in d.glob("p*-draft.png")})
    if left:
        print(f"\n── best available for {', '.join(left)} — flagged")
        sh(HERE / "draft_judge.py", "--brand", a.brand, "--dir", out,
           "--briefs", ",".join(left), "--best-available")
    if a.no_ship:
        return
    print(f"\n── ship · Drive folders, the pack, the board")
    sh(HERE / "deliver.py", "--brand", a.brand, *sel)
    sh(HERE / "pack.py", "--brand", a.brand, "--upload", *(["--product", a.product] if a.product else []))
    sh(HERE / "designer_page.py", "--part", "briefs", "--brand", a.brand,
       "--out", ROOT / f"board-{a.brand}.html")
    print(f"\nboard-{a.brand}.html rebuilt — republish it over this brand's Brief "
          f"Board (context/artifacts.md). Flags, if any: {out}/flags.json")


if __name__ == "__main__":
    main()
