#!/usr/bin/env python3
"""Build My Feeds — paid (the angle-shape pack) from the competitor sweeps.

Organic tells you what people choose to watch. Paid tells you what someone
is willing to pay to put in front of them — and, because spend concentrates,
it tells you which angles are actually converting.

This reads the sweep records, finds the ANGLE SHAPES that recur across
brands, and writes them as reusable templates with the numbers behind them.

    python3 paidpack.py [--named] [--site <where to write the zip>]

By default brands are described, not named, and no ad ids, sweep fields or
live funnel URLs ship — the lesson travels, the dataset does not. `--named`
includes brand names for an internal build.
"""
import argparse, json, os, re, shutil, subprocess, sys, zipfile
from datetime import date
from pathlib import Path
import desklib as D


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    This used to be `HERE.parents[2]`, which was the root only while this file
    sat in lab/. It moved to components/ on 2026-09-22 and every lookup
    silently pointed one level too high, at ~/Projects. A marker cannot go
    quietly wrong the next time something moves.

    The walk is run-kit's paths.repo() (SI-111 (organic one locator)).
    """
    return repo(start)


HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)
PAID = HERE.parent / "swipe-paid"
EMPLOYEE = ("https://higgsfield.ai/supercomputer/skills"
            "?employeeId=0d38d619-0ac2-45c9-bfd5-3371837ccad3")

def read():
    brands = []
    for f in sorted(PAID.glob("*/blocks.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        blocks = sorted(d.get("blocks", []), key=lambda b: -b.get("count", 0))
        live = sum(b.get("count", 0) for b in blocks)
        brands.append({
            "slug": d.get("brand", f.parent.name),
            "market": market_of(f.parent),
            "angles": len(blocks), "creatives": live,
            "video": d.get("video", 0), "image": d.get("image", 0),
            "top": [{"headline": b.get("headline", ""),
                     "text": (b.get("primary_text") or "")[:400],
                     "count": b.get("count", 0),
                     "variants": b.get("video_count", 0) + b.get("image_count", 0)}
                    for b in blocks[:12]],
            "concentration": round(sum(b.get("count", 0) for b in blocks[:3]) / live * 100) if live else 0,
        })
    return brands

def market_of(d):
    p = d / "PROFILE.md"
    if p.exists():
        m = re.search(r"Market:\s*(.+)", p.read_text())
        if m:
            return m.group(1).strip()[:180]
    return ""

def record(site, built):
    """A pack build is a run, so it files like one.

    The index reads runs/<machine>/<brand>/<label>/run.json. These kits are
    brand-agnostic by design — the guard above refuses any file that names a
    brand — so the brand slot is `_packs` and says so. Without this the build
    showed up in the index as a run with no record.
    """
    (site / "run.json").write_text(json.dumps(
        {"machine": "swipe-organic", "brand": "_packs", "label": site.name,
         "state": "filed" if built else "held",
         "opened": date.today().isoformat(),
         "note": "public download kits — brand-agnostic by the guard, so no brand",
         "built": built}, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--named", action="store_true")
    # Default inside the workspace, per the filing standard. Pass --site to
    # publish into the daemn.co repo when there is something to publish.
    ap.add_argument("--site", default=str(_workspace() / "runs" / "swipe-organic" /
                                         "_packs" / date.today().isoformat()))
    a = ap.parse_args()
    brands = read()
    if not brands:
        sys.exit("no sweeps found")
    total = sum(b["creatives"] for b in brands)
    print(f"{len(brands)} brands · {sum(b['angles'] for b in brands)} angles · {total:,} creatives")

    work = HERE / ".paid"
    if work.exists():
        shutil.rmtree(work)
    kit = work / "paid-ad-swipe-pack"
    (kit / "angle-shapes").mkdir(parents=True)
    brief = work / "digest.json"
    brief.write_text(json.dumps(brands, indent=1))

    names = "brand names included" if a.named else (
        "NO brand names — describe each brand by its market only (\"an Italian men's "
        "face-treatment brand\", \"a US body-care brand\"). Never name one, never quote a "
        "URL, never include an ad id.")
    prompt = f"""Turn a competitor ad sweep into a pack a beginner can actually use.

The data: {brief} — every swept brand, its market, how many live creatives and angles it is running, its video/image split, how concentrated its spend is on its top three angles, and its top angles with the real headline and body copy.

Write, into {kit}:

**`START-HERE.md`** — what a paid swipe is and why it is different from organic. The argument to make, in plain words: organic tells you what people choose to watch; paid tells you what someone is paying to put in front of them, and because ad budgets concentrate fast, the angles carrying the most creatives are the ones converting. Say what is in the pack and how to use it with the brand folder and the teardown kit. End with: paste the prompts into Higgsfield Supercomputer — {EMPLOYEE}

**`what-the-spend-says.md`** — the strategy lesson, from these actual numbers. Concentration (what share sits on the top three angles, brand by brand), how many variants they build per winning angle, the video-versus-image split and what it implies, and what the funnel shape suggests. Every claim carries its number. Where the data cannot tell you something, say so.

**`angle-shapes/<slug>.md`** — one file per RECURRING ANGLE SHAPE you find across these brands. A shape is the structure of the pitch, never the topic: what the headline does, what the first line of body copy does, what the proof is, what the close asks for. Merge across brands — if three brands run the same shape about different products, that is one shape, and say so. For each: the shape as a fill-in-the-blank template with {{PLACEHOLDER}} slots, why it works, how many creatives across how many brands sit on it, one worked example rewritten for a made-up brand (never a real one), and an image prompt + motion note for making a video version. Aim for the six to ten shapes that actually recur; do not pad.

Rules: {names}
Never reproduce a competitor's body copy verbatim — describe what it does and rewrite it as a template. Plain language throughout; the reader has never run ads before. No jargon, no file paths, no talk of scrapers or data fields."""
    r = subprocess.run(["claude", "-p", prompt, "--allowedTools", "Read", "Write"],
                       capture_output=True, text=True, timeout=1800,
                       cwd=str(D.WS))
    if not (kit / "START-HERE.md").exists():
        print("pack not written:", (r.stdout or "")[-500:])
        sys.exit(1)

    if not a.named:
        bad = re.compile("|".join(b["slug"] for b in brands) + r"|adplexity", re.I)
        hits = [f"{p.name}: {ln.strip()[:80]}" for p in kit.rglob("*.md")
                for ln in p.read_text().splitlines() if bad.search(ln)]
        if hits:
            print("REFUSED — the pack names a swept brand:")
            for h in hits[:6]:
                print("   ", h)
            sys.exit(1)

    out = Path(a.site).expanduser() / "paid-ad-swipe-pack.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in kit.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(work))
    n = sum(1 for p in kit.rglob("*") if p.is_file())
    shapes = len(list((kit / "angle-shapes").glob("*.md")))
    shutil.rmtree(work)
    print(f"{out}  ·  {out.stat().st_size/1e6:.2f} MB  ·  {n} files  ·  {shapes} angle shapes")
    record(out.parent, [{"kit": out.stem, "mb": round(out.stat().st_size / 1e6, 2),
                         "files": n, "angle_shapes": shapes}])

if __name__ == "__main__":
    main()
