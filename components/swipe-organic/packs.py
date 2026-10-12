#!/usr/bin/env python3
"""Build every download daemn.co offers, straight into the site repo.

The tools are a system and they ship in the order they are used:

  1. video-teardown-kit   the engine — any video in, your brief out
  2. brand-folder-kit     the fuel — the folder the engine reads (also
                          shipped inside the teardown kit; standalone for
                          anyone who wants only the structure)
  3. swipe-to-scene-kit   organic ammo — 34 formats already torn down
                          (built by bundle.py --public)

    python3 packs.py [--site <where to write the zips>]

Everything is plain text. No brand data, no media, no local paths — the
guard at the end refuses to write a pack that carries any.
"""
import argparse, json, os, re, shutil, subprocess, sys, zipfile
from datetime import date
from pathlib import Path


def _workspace(start=__file__):
    """The workspace root, FOUND by walking up — never counted with parents[N].

    This used to be `HERE.parents[2]`, which was the root only while this file
    sat in lab/. It moved to components/ on 2026-09-22 and every lookup
    silently pointed one level too high, at ~/Projects. A marker cannot go
    quietly wrong the next time something moves.

    The walk is run-kit's paths.repo() (SI-111 (organic one locator)); the name
    stays so feedsexport.py's packs._workspace() still resolves.
    """
    return repo(start)


HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)
REPO = None          # set in main(), after _workspace() below
CHAIN = None
# The brand template ships from THIS workspace. It used to be copied out of
# another repo, which made a shared component depend on a second repo
# on one person's Mac; the workspace's own brands/_TEMPLATE is a superset of
# what was there. Cut 2026-09-23 (the owner: "I don't want this in outlier or
# devel stuff anymore"). The guard below still checks everything that ships.
TEMPLATE = None
# Our own names, a person's disk and secrets: refused everywhere, always.
# The names themselves are private, so they come from the environment:
# PRIZM_OUR_NAMES="ourbrand|otherbrand|ourcompany|<home folder name>" (a regex alternation).
OURS = re.compile("|".join(x for x in (os.environ.get("PRIZM_OUR_NAMES", ""),
                                        r"/Users/|api[_-]?key|apify_token") if x), re.I)
# Competitors already shown by name on daemn.co (the full ad breakdowns under
# /feeds/examples/). Refused in the packs, which name nobody; allowed where the
# page itself names the competitor (My Feeds' paid tab, the examples).
# PRIZM_SHOWN_COMPETITORS="name|name" — the competitors the public page already names.
COMPETITORS = re.compile(os.environ.get("PRIZM_SHOWN_COMPETITORS", "") or r"(?!x)x", re.I)
BAD = re.compile(OURS.pattern + "|" + COMPETITORS.pattern, re.I)

def guard(root, allow_competitors=False):
    """No pack ships that names a brand, a person's disk, or a secret.
    Names count too — a post whose author is one of our own accounts puts the
    brand in the FILENAME, which no amount of content scanning would catch.
    allow_competitors=True keeps our own names refused but lets a competitor
    that is already public by name through (feedsexport.py uses it)."""
    BAD = OURS if allow_competitors else globals()["BAD"]
    hits = []
    for p in root.rglob("*"):
        if BAD.search(p.name):
            hits.append(f"{p.relative_to(root)}: brand name in the filename")
        if not p.is_file() or p.suffix.lower() not in {".md", ".json", ".txt", ".html"}:
            continue
        try:
            for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                if BAD.search(line):
                    hits.append(f"{p.relative_to(root)}:{n}: {line.strip()[:90]}")
        except Exception:
            pass
    return hits

def zip_up(stage, out):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in stage.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(stage))
    return out.stat().st_size / 1e6

def brand_kit(work):
    kit = work / "brand-folder-kit"
    shutil.copytree(TEMPLATE, kit / "your-brand")
    (kit / "READ-ME-FIRST.md").write_text("""# Your brand folder

Rename `your-brand/` to your brand, then fill it in — `your-brand/README.md`
tells you what each file is for and the order to do it in.

Every tool in the kit reads this one folder, so this is the only setup you do.
Drop it beside the teardown chain (or anywhere the tools can see it) and point
a run at it by name.
""")
    return kit

def teardown_kit(work):
    kit = work / "video-teardown-kit"
    (kit / "the-chain").mkdir(parents=True)
    shutil.copytree(TEMPLATE, kit / "your-brand-folder")
    shutil.copy(HERE / "beginner-runbook.md", kit / "HOW-TO-RUN-IT.md")
    shutil.copy(HERE / "models.md", kit / "WHICH-MODELS.md")
    if (CHAIN / "README.md").exists():
        shutil.copy(CHAIN / "README.md", kit / "reference--the-automated-version.md")
    order = []
    for d in sorted((CHAIN / "prompts").glob("stage-*")):
        picks = sorted(d.glob("*.md"))
        if not picks:
            for sub in sorted(d.iterdir()):
                if sub.is_dir():
                    picks = sorted(sub.glob("*.md"))
                    if picks:
                        break
        if not picks:
            continue
        newest = max(picks, key=lambda p: p.name)
        num = len(order) + 1
        name = f"{num:02d}--{d.name}.md"
        shutil.copy(newest, kit / "the-chain" / name)
        order.append((name, newest.name))
    (kit / "START-HERE.md").write_text("""# Video Teardown

Take any video that already worked — a competitor's ad, an organic post, a
creator video someone sent you — and get back a finished brief for **your**
brand: the scenes, what is said, what people wear, the hooks, and a prompt
for every shot you need to make.

Nothing gets installed. Nothing runs on your computer.

## What you need

1. **Claude** — the chat at claude.ai, or Claude Cowork if you have it.
2. **Higgsfield Supercomputer** — this is where the video actually gets
   watched and where your scenes get made. It has a Gemini model on it, so
   you can hand it the video directly.
3. **Google Drive** — where your brand folder and your finished briefs live.
4. **Your brand folder** — the empty template is in `your-brand-folder/`
   here. Fill it in once; open its README and it walks you through it.

## Start here

**Read `HOW-TO-RUN-IT.md`.** It is the whole process in seven numbered steps,
written for someone who has never done this before. Everything else in this
folder is the material those steps tell you to paste.

## What is in this folder

- `HOW-TO-RUN-IT.md` — the seven steps. Start here.
- `WHICH-MODELS.md` — the exact models and settings to use. Do not leave it
  on Auto; this names what actually works and what to do when a shot looks
  wrong.
- `your-brand-folder/` — the empty brand folder to copy into your Drive.
- `the-chain/` — the actual instructions you paste into Claude, one file per
  step, numbered in the order you use them. You do not need to read these
  first; the runbook tells you when each one goes in.
- `reference--the-automated-version.md` — ignore this one unless you have a
  developer. It describes a version that runs the whole thing unattended.

## The two rules

**Rebuild the structure, not the content.** The shape is what earned the
views. Your product is what changes. A scalp treatment and a countertop demo
can be the same format — that is the point.

**Nothing invented.** If your brand folder does not say what your product
looks like or what your customer sounds like, the tools will tell you they do
not know rather than make something up. That is them working correctly. Go
fill in that part.

---

*Prizm Labs — daemn.co. Template system.*
""")
    return kit

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
    global REPO, CHAIN, TEMPLATE
    REPO = _workspace()
    CHAIN = REPO / "tools/video-teardown"
    TEMPLATE = REPO / "brands" / "_TEMPLATE"
    ap = argparse.ArgumentParser()
    # Default inside the workspace, per the filing standard. Pass --site to
    # publish into the daemn.co repo when there is something to publish.
    ap.add_argument("--site", default=str(REPO / "runs" / "swipe-organic" /
                                         "_packs" / date.today().isoformat()))
    a = ap.parse_args()
    site = Path(a.site).expanduser()
    site.mkdir(parents=True, exist_ok=True)
    work = HERE / ".packs"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    built = []
    for name, fn in (("video-teardown-kit", teardown_kit), ("brand-folder-kit", brand_kit)):
        kit = fn(work)
        hits = guard(kit)
        if hits:
            print(f"REFUSED {name} — it carries what must not ship:")
            for h in hits[:8]:
                print("   ", h)
            sys.exit(1)
        mb = zip_up(kit, site / f"{name}.zip")
        n = sum(1 for p in kit.rglob("*") if p.is_file())
        built.append((name, mb, n))

    # the organic pack has its own builder
    r = subprocess.run([sys.executable, str(HERE / "bundle.py"), "--public", "--out", str(site)],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip()[-300:])
    shutil.rmtree(work)
    for name, mb, n in built:
        print(f"{name}.zip  ·  {mb:.2f} MB  ·  {n} files")
    record(site, [{"kit": name, "mb": round(mb, 2), "files": n} for name, mb, n in built])

if __name__ == "__main__":
    main()
