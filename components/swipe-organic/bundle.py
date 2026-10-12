#!/usr/bin/env python3
"""Package the production kit as one zip the owner can send to anyone.

Everything a maker needs and nothing they don't: how the process runs,
the format library, a rebuild sheet per swiped video filed under its
format, the beat frames as pictures, and the teardown prompts themselves
for anyone running the chain. Reference videos stay out — they are
gigabytes and they live on the shared drive; the kit links to them.

    python3 bundle.py [--out ~/Desktop]

Re-run it any time; it always packages the current state.
"""
import argparse, json, os, re, shutil, sys, zipfile
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
# Our own public posts are welcome here — they are already public. What must
# never ship is a secret or somebody's disk.
LEAK = re.compile(r"/Users/|api[_-]?key|apify_token|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}", re.I)
VID = HERE / "records/swipe-videos"
SAVES = HERE / "records/damon-saves"
REPO = _workspace()
CHAIN = REPO / "tools/video-teardown"
EMPLOYEE = ("https://higgsfield.ai/supercomputer/skills"
            "?employeeId=0d38d619-0ac2-45c9-bfd5-3371837ccad3")
for _r in HERE.parents:                # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
DRIVE = " ▸ ".join(swipe_home.label("organic", "records", "swipe-videos",
                                    "<code>", "video.mp4").split("/"))

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path.home() / "Desktop"))
    ap.add_argument("--public", action="store_true",
                    help="for daemn.co: no third-party video stills, text only")
    a = ap.parse_args()
    stage = HERE / ".bundle"
    if stage.exists():
        shutil.rmtree(stage)
    kit = stage / "swipe-to-scene-kit"
    (kit / "formats").mkdir(parents=True)
    (kit / "the-teardown-process").mkdir(parents=True)

    lib = json.loads((HERE / "formats.json").read_text())["formats"]
    byid = {f["id"]: f for f in lib}
    cat = {}
    for r in json.loads((SAVES / "catalog.json").read_text())["rows"]:
        m = re.search(r"/(p|reel|reels)/([A-Za-z0-9_-]+)", r["url"])
        if m:
            cat[m.group(2)] = r

    # every classified video, filed under its format
    used, sheets = {}, 0
    for d in sorted(VID.iterdir()):
        fj, hf = d / "format.json", d / "handoff.md"
        if not (fj.is_file() and hf.is_file()):
            continue
        try:
            fid = json.loads(fj.read_text()).get("format_id", "")
        except Exception:
            continue
        f = byid.get(fid)
        # a one-off keeps its own structure name — a junk drawer helps nobody
        folder = slug(f["name"]) if f else "one-offs/" + slug(fid.replace("new:", ""))
        dest = kit / "formats" / folder
        (dest / "frames").mkdir(parents=True, exist_ok=True)
        r = cat.get(d.name, {})
        views = r.get("views") or 0
        who = r.get("author") or d.name
        name = f"{views:012d}--{who}--{d.name}"
        shutil.copy(hf, dest / f"{name}.md")
        if (d / "sheet.jpg").exists() and not a.public:
            shutil.copy(d / "sheet.jpg", dest / "frames" / f"{name}.jpg")
        used.setdefault(folder, []).append((views, r.get("author"), d.name))
        if not f:
            try:
                j = json.loads(fj.read_text())
                (dest / "00-THE-FORMAT.md").write_text("\n".join([
                    f"# {fid.replace('new:', '').replace('-', ' ').title()}", "",
                    "**A one-off** — this structure appears once in the swipes, so it has no",
                    "library card yet. The sheets here carry everything known about it.", "",
                    "## What carries the value", "", j.get("carries_the_value", "—"), "",
                    "## Produce it", "",
                    f"Prompts are inside each sheet. Run them in the Higgsfield employee: {EMPLOYEE}", ""]))
            except Exception:
                pass
        sheets += 1

    # one readable card per format, at the top of its folder
    for fid, f in byid.items():
        folder = slug(f["name"])
        dest = kit / "formats" / folder
        if not dest.exists():
            continue
        ev = (f.get("evidence") or [{}])[0]
        mine = sorted(used.get(folder, []), reverse=True)
        card = [f"# {f['name']}", "",
                f"**{ev.get('views', 0):,} views proved it** · {len(mine)} of the owner's swipes use this format", "",
                "## What it is", "", f["mechanic"], "",
                "## Why it works", "", f["why_it_works"], "",
                "## The beats, in order", ""]
        card += [f"{i+1}. {b}" for i, b in enumerate(f["beats"])]
        card += ["", "## On-screen text", "", f.get("text_behaviour", "—"),
                 "", "## Camera", "", f.get("camera", "—"),
                 "", "## Higgsfield — image prompt", "", "```", f["higgsfield"]["image"], "```",
                 "", "## Higgsfield — motion", "", "```", f["higgsfield"]["motion"], "```",
                 "", "## Produce it", "",
                 f"Paste those into the Higgsfield employee: {EMPLOYEE}", "",
                 "## The references in this folder", ""]
        card += [f"- **@{au or c}** — {v:,} views — https://www.instagram.com/p/{c}/"
                 for v, au, c in mine[:15]]
        card += ["", "Each `.md` beside this file is one reference torn down: its beats with",
                 "timestamps, what carries the value, how to shoot it, and its own prompts.",
                 "`frames/` holds the six beats of each as one picture.", ""]
        (dest / "00-THE-FORMAT.md").write_text("\n".join(card))

    # the teardown process, as-is
    if CHAIN.exists():
        shutil.copy(CHAIN / "README.md", kit / "the-teardown-process" / "how-it-works.md")
        for stage_dir in sorted((CHAIN / "prompts").glob("stage-*")):
            for p in stage_dir.glob("*.md"):
                shutil.copy(p, kit / "the-teardown-process" / f"{stage_dir.name}--{p.name}")

    # library formats lead; one-offs are listed after, never at the top
    ranked = sorted(((len(v), k) for k, v in used.items() if "/" not in k), reverse=True)
    ones = sorted(((len(v), k) for k, v in used.items() if "/" in k), reverse=True)
    start = [f"# My Feeds — organic", "",
             f"Built {date.today()} · {len(ranked)} formats · {sheets} real posts, taken apart", "",
             "Every format in here came from a post that actually worked — some past a",
             "hundred million views. Nothing is theory and nothing is invented.", "",
             "## How to use it", "",
             "1. **Pick a format** in `formats/`. Each folder is one proven structure.",
             "   Open its `00-THE-FORMAT.md` first — what it is, why it works, and the",
             "   beats in the order they happen.",
             "2. **Look at a real one.** Every other file in the folder is one real post",
             "   taken apart beat by beat, with a link to it at the bottom. `frames/`",
             "   shows the six key moments as a single picture if you would rather not",
             "   open the video.",
             "3. **Make it yours.** Copy the image prompt and the motion note into",
             f"   Higgsfield Supercomputer: {EMPLOYEE}",
             "   Fill in every blank in curly brackets — `{PRODUCT}`, `{SUBJECT}` — from",
             "   your own brand folder. Those are questions, not decoration.",
             "4. **Cut it to the beats.** The beat list in each sheet is your edit order.", "",
             "**Which models?** `WHICH-MODELS.md` in this folder names them and the",
             "settings that work. Do not leave it on Auto.", "",
             "## Two things that decide whether it works", "",
             "- **Copy the structure, not the content.** The shape is what earned the",
             "  views; your product is what changes. A scalp treatment and a countertop",
             "  demo can be the same format — that is the whole point.",
             "- **Never let it guess.** If you do not know what your product looks like",
             "  on camera or how your customer talks, go write that down first. A",
             "  generated shot that guesses is worse than no shot.", "",
             "## Want it done for you instead?", "",
             "The **Video teardown** tool does this to any video you choose, and writes",
             "the brief with your brand already in it. Both are in Prizm Labs (daemn.co).", "",
             "## The formats, by how often they show up", ""]
    (kit / "START-HERE.md").write_text("\n".join(start))
    models = HERE / "models.md"
    if models.exists():
        shutil.copy(models, kit / "WHICH-MODELS.md")

    name = "swipe-to-scene-kit" + ("" if a.public else f"-{date.today()}")
    if a.public:                       # secrets and disk paths never ship
        bad = []
        for q in kit.rglob("*"):
            if q.is_file() and q.suffix in {".md", ".json"}:
                for n, line in enumerate(q.read_text(errors="ignore").splitlines(), 1):
                    if LEAK.search(line):
                        bad.append(f"{q.relative_to(kit)}:{n}: {line.strip()[:70]}")
        if bad:
            print("REFUSED — the public pack carries a secret or a local path:")
            for b in bad[:8]:
                print("   ", b)
            raise SystemExit(1)
    out = Path(a.out).expanduser() / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in kit.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(stage))
    shutil.rmtree(stage)
    mb = out.stat().st_size / 1e6
    print(f"{out}  ·  {mb:.1f} MB  ·  {len(ranked)} formats  ·  {sheets} references")

if __name__ == "__main__":
    main()
