#!/usr/bin/env python3
"""Package the competitor sweeps themselves as a download.

the owner's ruling 2026-09-04: ship the dataset, named. This is the raw
material behind My Feeds — paid — four brands, every angle they
are running, the copy on it, how many creatives sit on each, and where
the traffic goes.

    python3 paiddata.py [--site <where to write the zip>]

Ships: the per-brand profile, the angle blocks, the landing-page record.
Never ships: `own/` (the owner's own brands), scraped media, or anything
under a brand folder that is not one of the named records below.
"""
import argparse, json, os, shutil, sys, zipfile
from datetime import date
from pathlib import Path


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
KEEP = ["PROFILE.md", "blocks.json", "pages.json", "teardown.md",
        "language-bank.md", "connections.md"]
SKIP = {"own", "organic", "prompts", "context", "refs", "_TEMPLATE", "__pycache__"}

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
    # Default inside the workspace, per the filing standard. Pass --site to
    # publish into the daemn.co repo when there is something to publish.
    ap.add_argument("--site", default=str(_workspace() / "runs" / "swipe-organic" /
                                         "_packs" / date.today().isoformat()))
    a = ap.parse_args()
    work = HERE / ".paiddata"
    if work.exists():
        shutil.rmtree(work)
    kit = work / "paid-ad-dataset"
    kit.mkdir(parents=True)

    rows, total = [], 0
    for d in sorted(PAID.iterdir()):
        if not d.is_dir() or d.name in SKIP or not (d / "blocks.json").exists():
            continue
        out = kit / d.name
        out.mkdir()
        for name in KEEP:
            f = d / name
            if f.exists():
                shutil.copy(f, out / name)
        b = json.loads((d / "blocks.json").read_text())
        live = sum(x.get("count", 0) for x in b.get("blocks", []))
        total += live
        rows.append((d.name, len(b.get("blocks", [])), live,
                     b.get("video", 0), b.get("image", 0)))

    lines = ["# The competitor ad sweeps — the raw records", "",
             f"Swept and packaged {date.today()} · {len(rows)} brands · "
             f"{sum(r[1] for r in rows)} angles · {total:,} live creatives", "",
             "This is the data behind My Feeds — paid. The pack tells you what",
             "the shapes are; this tells you exactly who is running what.", "",
             "| Brand | Angles | Live creatives | Video | Image |",
             "|---|---|---|---|---|"]
    lines += [f"| {n} | {ang} | {live:,} | {v} | {i} |" for n, ang, live, v, i in rows]
    lines += ["", "## What each file is", "",
              "- **PROFILE.md** — the read on that brand: what market they are in, how",
              "  concentrated their spend is, where the traffic goes, and their angle",
              "  leaderboard.",
              "- **blocks.json** — every angle they are running, with the real headline",
              "  and body copy, how many creatives sit on it, and the ad ids.",
              "- **pages.json** — the landing pages behind the ads.",
              "- **teardown.md** / **language-bank.md** / **connections.md** — where they",
              "  exist: the deeper read on that brand's creative and language.", "",
              "## How to use it", "",
              "Find a brand near your market. Open its PROFILE and look at what carries",
              "the most creatives — that is the pitch that is paying for itself. Then",
              "open blocks.json and read the actual copy on it. Rebuild that shape for",
              "your brand with the teardown kit; do not copy the words.", "",
              "## Honest notes", "",
              "- **Counts are live ads, not dollars.** Nobody outside these companies",
              "  can see spend. The number of versions still running is the closest",
              "  public stand-in, because nobody builds fifty versions of a loser.",
              "- **It is a snapshot**, taken on the sweep date. Ad accounts change weekly.",
              "- **Sourced from an AdPlexity advertiser sweep.** Shared here by the",
              "  person who ran it.", "",
              "*Prizm Labs — daemn.co. Template system.*", ""]
    (kit / "README.md").write_text("\n".join(lines))

    out = Path(a.site).expanduser() / "paid-ad-dataset.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in kit.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(work))
    n = sum(1 for p in kit.rglob("*") if p.is_file())
    shutil.rmtree(work)
    print(f"{out}  ·  {out.stat().st_size/1e6:.2f} MB  ·  {n} files  ·  "
          f"{len(rows)} brands  ·  {total:,} creatives")
    record(out.parent, [{"kit": out.stem, "mb": round(out.stat().st_size / 1e6, 2),
                         "files": n, "brands": len(rows), "creatives": total}])

if __name__ == "__main__":
    main()
