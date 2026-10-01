#!/usr/bin/env python3
"""Swipe in, briefs and draft pictures out. The whole of stage one, one command.

    chain.py start  --brand <brand> --product <product> --avatar <avatar> \
                    --swipe marsmen --count 3
    chain.py start  ... --dry-run               resolve everything, spend nothing
    chain.py drafts --briefs p005,p006          write the generation jobs
    chain.py ingest --results results.json      file what came back

Damon, 2026-09-13: *"have these briefs done, and the initial versions of the
images generated too, for each of these swipes. That's what we hand off to the
graphic designer, and then establish this as a chain."*

**What `start` does, in order.** Picks the N most-duplicated angles in that
swipe library — a competitor rebuilding the same ad eighty-five times is the
only free signal there is — opens a run on the most-cloned still in each, runs
all six stages for every run at once, and gives each finished brief an id out
of the register.

**Why `drafts` and `ingest` are separate.** Higgsfield's image models are
reached through its MCP, which a script cannot call, so the middle is driven
by a session: `drafts` writes exactly what to generate, the session generates
it, `ingest` files the results and rebuilds the pages. Same shape as
`image-production/tools/make_variations.py`, for the same reason.

**The gate is still a person.** This stops at briefs and draft pictures. It
never writes a batch spec and never makes a finished ad: a person reads the
brief, answers what it could not decide, and hands it on.
"""
import argparse, json, re, shutil, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))
import paths as P
import briefs as B
import brief_page as BP
import gates as G

DRAFTS = HERE / "drafts"

# Damon, 2026-09-14: *"Hey, what model are you using to generate these
# images?" … "Let's use GPT Image 2."*
#
# The id is `gpt_image_2_5`, not `gpt_image_2`, and the difference is not
# cosmetic: plain GPT Image 2 offers 1:1, 4:3, 3:4, 16:9, 21:9, 9:16, 3:2 and
# 2:3 — no 4:5, which is the ratio every draft here is cut at. 2.5 carries
# 4:5. Anyone "correcting" this back to gpt_image_2 silently changes the
# frame, so the constraint is written down beside the constant.
#
# Before this, every draft went to `nano_banana_pro` — which Higgsfield in
# fact serves as `nano_banana_2`, another reason the model belongs in code
# and not in a session's memory.
DRAFT_MODEL = "gpt_image_2_5"
DRAFT_MODEL_WHY = "GPT Image 2.5 — the only GPT Image tier that carries 4:5"


def library(swipe):
    """Where this swipe lives, and what its heat signal is.

    Two libraries, two kinds of evidence:

    **Paid** (`swipe-paid/<x>/blocks/`) ranks by duplication. A competitor
    who rebuilt one ad eighty-five times made a spend decision we can read
    for free: nobody re-executes a shape that is not working.

    **Organic** (`swipe-organic/<x>/posts/`) has no duplication at all — a
    creator posts once. Engagement is the substitute and it is weaker: a post
    can earn its numbers on subject matter with nothing to do with the
    product. The top <brand> post by engagement is a creator's dog dying.
    So the rank opens the door; the caption decides.
    """
    for root, sub, kind in ((P.SWIPE, "blocks", "paid"),
                            (P.SWIPE_ORGANIC, "posts", "organic")):
        d = root / swipe / sub
        if d.is_dir():
            return d, kind
    have = []
    for root, sub, kind in ((P.SWIPE, "blocks", "paid"),
                            (P.SWIPE_ORGANIC, "posts", "organic")):
        if root.is_dir():
            have += [f"{x.name} ({kind})" for x in root.iterdir()
                     if (x / sub).is_dir() and not x.name.startswith("_")]
    sys.exit(f"no swipe library for {swipe!r} — have: " + ", ".join(sorted(have)))


def blocks(swipe):
    """Every angle or post the library holds for this swipe, hottest first."""
    d, kind = library(swipe)
    out = []
    for f in sorted(d.glob("*.md")):
        t = f.read_text()
        g = lambda pat, c=str: (lambda m: c(m.group(1).replace(",", "")) if m else None)(
            re.search(pat, t, re.M))
        title = g(r"^#\s*\d+\s*·\s*(.+?)\.?$")
        if kind == "paid":
            clone = g(r"most-cloned single creative ran (\d+)x", int) or 0
            variants = g(r"\*\*(\d+) ad variants?\*\*", int) or 0
            images = g(r"\*\*\d+ live creatives?\*\*\s*—\s*\d+ video, (\d+) image", int) or 0
            heat, label = clone, f"rebuilt {clone}x across {variants} variants"
        else:
            eng = g(r"\*\*([\d,]+) likes", int) or 0
            com = g(r"·\s*([\d,]+) comments", int) or 0
            tot = g(r"·\s*([\d,]+) engagement", int) or 0
            clone, variants, images = 0, 0, 1
            heat, label = tot, f"{eng:,} likes and {com:,} comments"
        out.append({"file": f.name, "kind": kind, "title": title,
                    "clone": clone, "variants": variants, "images": images,
                    "heat": heat, "heat_label": label,
                    "drive": g(r"\*\*Drive:\*\*\s*`([^`]+)`")})
    return sorted(out, key=lambda b: -b["heat"])


def all_stills(block, swipe):
    """Every still the block holds, in order, off the Drive mirror — one for
    a static, several for a carousel or slideshow.

    Drive names the folder `blocks` for some paid brands and `angles` for
    others, and `posts` for organic. All three are read rather than one
    being declared correct after the fact.
    """
    stem = Path(block["file"]).stem
    for lib in ("swipe-paid", "swipe-organic"):
        for folder in ("blocks", "angles", "posts"):
            d = P.DRIVE / lib / swipe / folder / stem / "photos"
            if d.is_dir():
                stills = sorted(q for q in d.iterdir()
                                if q.suffix.lower() in (".jpg", ".jpeg", ".png"))
                if stills:
                    return stills
    return []


def pick_still(block, swipe):
    """The first creative out of the block (kept for callers)."""
    stills = all_stills(block, swipe)
    return stills[0] if stills else None


# THE ROUTE DECISION (Damon, 2026-09-15 and 2026-09-22; TEARDOWN-CHAINS.md).
# Two axes, and they are not the same question. WHO MAKES IT decides what the
# brief has to say: a creator with a phone, or the machine. WHAT IT IS decides
# how it is read: one still, or a sequence of them (a carousel, a slideshow).
# The video chain solved this once — one teardown, the last stage branches by
# who makes it. This is the same shape on the image side. `form` is read off
# the swipe (one still or several) unless named; `route` defaults to the
# machine, which is what the one brief this chain had always was.
ROUTES = ("ai", "creator")
FORMS = ("auto", "single", "sequence")

ROUTE_TEXT = {
    ("ai", "single"): """# Production route

Generated plate with the source attached as the layout reference; type set
from the layout data. One frame this run.
""",
    ("ai", "sequence"): """# Production route

A generated sequence: slide one is made with the source's first slide as the
layout reference, and every later slide is an edit off slide one — the same
person, product, palette and framing carried, only what the slide says
changing. Type set from the layout data. Several frames this run, one thread.
""",
    ("creator", "single"): """# Production route

A person shoots it on their own phone. Nothing is generated except a
reference picture for them to match. One photograph this run. The brief is
addressed to that person: what to shoot, how, and what the caption says — no
plate prompt, no type layer, no template.
""",
    ("creator", "sequence"): """# Production route

A person makes it on their own phone, slide by slide. Nobody speaks: the words
on each picture carry the whole argument. The brief is addressed to that
person, one slide at a time — what each slide shows and what it says — and the
close is built from the captions. No plate prompt, no type layer, no template.
""",
}


def read_route(run):
    """The route a run was opened on. A run from before the branch existed
    carries no file and is the AI single route — exactly what it was."""
    f = Path(run) / "vars/route.json"
    if f.is_file():
        try:
            return json.loads(f.read_text())
        except ValueError:
            pass
    return {"route": "ai", "form": "single", "slides": 1, "why": "opened before the branch existed"}


def route_for(a, stills):
    """(route, form, slides) for one pick. `--form auto` reads the swipe."""
    route = (getattr(a, "route", None) or "ai").lower()
    form = (getattr(a, "form", None) or "auto").lower()
    if route not in ROUTES:
        sys.exit(f"--route is one of {', '.join(ROUTES)}")
    if form not in FORMS:
        sys.exit(f"--form is one of {', '.join(FORMS)}")
    if form == "auto":
        form = "sequence" if len(stills) > 1 else "single"
    # CAROUSELS ARE AI ONLY (Damon, 2026-10-01): "all of these carousels are
    # going to be made with AI ... remove the content creator filming
    # himself." A sequence is always the machine's; the creator sequence brief
    # is retired and a --route creator on a carousel is overridden, loudly.
    if form == "sequence" and route != "ai":
        print("  carousels are AI only (2026-10-01) — route set to ai")
        route = "ai"
    return route, form, (len(stills) if form == "sequence" else 1)


def start(a):
    # Preflight first, always. It used to be something you could run while
    # the chain ran regardless, so a brand with no folder at all got through
    # two stages before anything noticed (2026-09-14). Stage 1 is cheap;
    # everything after it is not, and a run that cannot finish should never
    # begin.
    pre = subprocess.run([sys.executable, str(HERE / "tools/preflight.py"),
                          "--brand", a.brand, "--product", a.product,
                          "--avatar", a.avatar, "--swipe", a.swipe],
                         capture_output=True, text=True)
    if pre.returncode != 0:
        print(pre.stdout)
        sys.exit(f"preflight failed for {a.brand} — nothing generated. Fix what "
                 f"is listed above; RUN.md has 'What a new brand needs'.")
    print(f"preflight ok · {a.brand} {a.product} · {a.avatar} · {a.swipe}\n")
    if getattr(a, "dry_run", False):
        print("DRY RUN — picks are read, nothing is opened, no model is called\n")

    # One block per angle. The library holds several records under one title
    # — marsmen's top three by clone count are all "50% Off + Free Gifts" —
    # so taking the top N straight off the list returns the same argument
    # three times and calls it three shapes.
    # Named picks beat the ranking. Damon reads the feed and chooses; the
    # heat order is what he reads it in, not a substitute for reading it.
    wanted = {int(x) for x in re.findall(r"\d+", a.picks)} if getattr(a, "picks", None) else None
    if wanted:
        all_blocks = blocks(a.swipe)
        by_rank = {}
        for n, blk in enumerate(all_blocks, 1):
            by_rank[n] = blk
        missing = sorted(wanted - set(by_rank))
        if missing:
            sys.exit(f"no rank {missing} in {a.swipe} — it holds {len(all_blocks)}")
        picked = [by_rank[n] for n in sorted(wanted)]
        print(f"{len(picked)} picked by hand out of {len(all_blocks)}\n")
        return _open_and_run(a, picked)

    seen, picked = set(), []
    for blk in blocks(a.swipe):
        if not blk["images"]:
            continue
        key = (blk["title"] or "").strip().lower()
        if key in seen:
            continue
        seen.add(key); picked.append(blk)
        if len(picked) == a.count:
            break
    if not picked:
        sys.exit(f"no block in {a.swipe} carries a still")
    return _open_and_run(a, picked)


def taken_runs():
    """Every run folder a brief already points at, live or retired."""
    reg = B.load()
    out = {}
    for src in (reg.get("briefs", {}), reg.get("retired", {})):
        for bid, r in src.items():
            if r.get("run"):
                out[r["run"]] = bid
    return out


def run_py(runs, stages, a, extra=()):
    """One call to tools/run.py — the only door to the stages. `--dry-run`
    and `--gates` travel with it, so a dry `start` is dry all the way down."""
    cmd = [sys.executable, str(HERE / "tools/run.py"), ",".join(runs), stages,
           "--brand", a.brand, "--product", a.product]
    if getattr(a, "avatar", None):
        cmd += ["--avatar", a.avatar]
    if getattr(a, "dry_run", False):
        cmd += ["--dry-run"]
    if getattr(a, "gates", None):
        cmd += ["--gates", a.gates]
    sys.stdout.flush()                      # keep our lines ahead of the child's
    return subprocess.run(cmd + list(extra), check=False)


def say_held(slug):
    """A held run says why — off its own check.json. True when it is held."""
    h = G.held(P.RUNS / slug)
    for gate, problems in h.items():
        print(f"  ✗ {slug} HELD at the {gate} gate:")
        for p in problems:
            print(f"      {p}")
    return bool(h)


def named_stills(block, swipe, want):
    """The stills of this block whose filename stem is named in `want`.

    A block is not one picture. Froya's clearance block holds twenty-six
    different plates of the SAME offer, and Damon picks plates, not blocks
    (2026-09-24, off the swipe wall). `--stills` names them; without it the
    chain behaves exactly as before, one run per block off the first still.
    """
    by_stem = {q.stem: q for q in all_stills(block, swipe)}
    out, missing = [], []
    for w in want:
        (out.append(by_stem[w]) if w in by_stem else missing.append(w))
    return out, missing


def _open_and_run(a, picked):
    dry = getattr(a, "dry_run", False)
    want = [x.strip() for x in (getattr(a, "stills", None) or "").split(",") if x.strip()]
    opened, planned = [], []
    jobs = []
    for b in picked:
        stills = all_stills(b, a.swipe)
        if want:
            # one run per NAMED plate, each carrying only itself — a chosen
            # plate is a single static, never read as a slide of a sequence.
            chosen, missing = named_stills(b, a.swipe, want)
            for m in missing:
                print(f"  ! {b['file']}: no still {m!r} in this block")
            for q in chosen:
                jobs.append((b, [q], q))
        elif stills:
            jobs.append((b, stills, stills[0]))
        else:
            print(f"  ! {b['file']}: no still on Drive, skipped")
    for b, stills, still in jobs:
        route, form, n_slides = route_for(a, stills)
        # The brand leads the slug. Without it, two brands tearing down the
        # same swipe block write to the same run folder and the second
        # silently overwrites the first — proved 2026-09-14, when a test
        # brand ate a finished <brand> run.
        slug = f"{a.brand}-{a.swipe}-{Path(b['file']).stem.split('_')[0]}-" \
               + re.sub(r"[^a-z0-9]+", "-", (b["title"] or "").lower()).strip("-")[:24]
        if want:
            # five plates of one block would otherwise share a slug, and the
            # second would be refused as "already torn down" (2026-09-24).
            slug += f"-{still.stem}"
        run = P.RUNS / slug
        # A block another brief already owns is not re-openable. The slug is
        # derived from the block, so picking it again writes into that run
        # and overwrites finished stages — it took p009's teardown before
        # this guard existed (2026-09-15). The brand prefix added earlier
        # stops two BRANDS colliding; this stops one brand re-picking.
        owner = taken_runs().get(slug)
        if owner:
            print(f"  ! {b['file']}: already torn down as {owner} — skipped")
            continue
        if dry:
            opened.append(slug); planned.append((route, form, n_slides))
            print(f"  would open {slug}  ({b['heat_label']})\n"
                  f"      OK  still  {still.name}"
                  + (f"  + {n_slides - 1} more slides" if n_slides > 1 else "")
                  + f"\n      route  {route} · {form}")
            continue
        for s in ("assets", "out", "vars", "finals"):
            (run / s).mkdir(parents=True, exist_ok=True)
        shutil.copy(still, run / "assets/source.jpg")
        if form == "sequence":
            # every slide, in order, beside source.jpg (which stays slide one
            # so every stage that reads one picture still does)
            for i, q in enumerate(stills, 1):
                shutil.copy(q, run / f"assets/source-{i:02d}{q.suffix.lower()}")
        (run / "vars/brand_name.md").write_text(a.brand.upper() + "\n")
        (run / "vars/production_route.md").write_text(ROUTE_TEXT[(route, form)])
        (run / "vars/route.json").write_text(json.dumps(
            {"route": route, "form": form, "slides": n_slides,
             "why": "named with --route/--form" if getattr(a, "form", "auto") != "auto"
                    else f"read off the swipe: {n_slides} still(s)"}, indent=1))
        (run / "assets/source.json").write_text(json.dumps({
            "swipe": a.swipe, "block": b["title"], "block_file": b["file"],
            "clone": b["clone"], "variants": b["variants"], "drive": b["drive"],
            "swipe_kind": b["kind"], "heat": b["heat"], "still": still.name,
            "why": f"ranked by {'duplication' if b['kind'] == 'paid' else 'engagement'}"
                   f" — {b['heat_label']}"}, indent=1))
        opened.append(slug)
        print(f"  opened {slug}  ({b['heat_label']})  ·  {route} · {form}")

    # A pick with no still on Drive is skipped, and the skip used to scroll
    # past in the middle of six parallel runs — asked for six, got three,
    # and nothing said so at the end (2026-09-14). The count is the last
    # thing printed before the stages start, where it cannot be missed.
    missed = (len(jobs) if want else len(picked)) - len(opened)
    if missed:
        print(f"\n  {missed} of {len(picked)} picks had no still on Drive "
              f"and were skipped — listed above.")
    if not opened:
        sys.exit("nothing opened")
    if dry:
        # Everything below this line spends: six stages, then drafts. The dry
        # run stops at the stages' own report and touches none of it. The
        # route the picks WOULD open on travels with it, so the report shows
        # the branch — one route per start; mixed forms are reported per pick above.
        extra = []
        if planned:
            r, f, n = planned[-1]
            extra = ["--route", r, "--form", f, "--slides", str(n)]
        sys.exit(run_py(opened, "all", a, extra).returncode)
    print(f"\nrunning every stage on {len(opened)} runs, in parallel\n")
    run_py(opened, "all", a)

    print()
    reg = B.load()
    for slug in opened:
        # A run held at a gate gets no brief id: the id is what sends it on to
        # drafts and the designer, and held work does not travel. It says why.
        if getattr(a, "gates", "hold") == "hold" and say_held(slug):
            continue
        if (P.RUNS / slug / "out/06-brief.md").is_file():
            bid, _ = B.open_brief(slug, a.brand, B.load(), a.product, a.avatar)
            print(f"  {bid}  {slug}")
        else:
            print(f"  ! {slug} produced no brief")
    pages()

    # The chain does not end at a brief. Damon, 2026-09-14: "you have the
    # drafts and the final brief — everything needs to be ready for the
    # designer." So `start` always writes the draft prompts, and always says
    # what is still missing rather than leaving it to be noticed.
    print()
    new_ids = [b for b, r in B.load()["briefs"].items() if r.get("run") in opened]
    # WHAT FOLLOWS THE BRIEF DEPENDS ON THE ROUTE. The designer work order
    # and the draft prompts are the machine's; a creator brief is addressed to
    # a person and needs neither. A sequence has no per-slide draft yet
    # (The Build List, 4) and says so rather than drafting slide one alone.
    routes = {slug: read_route(P.RUNS / slug) for slug in opened}
    reg = B.load()["briefs"]
    def on(b, route=None, form=None):
        r = routes.get(reg[b]["run"], {})
        return (route is None or r.get("route") == route) and (form is None or r.get("form") == form)
    ai_single = [b for b in new_ids if on(b, "ai", "single")]
    ai_sequence = [b for b in new_ids if on(b, "ai", "sequence")]
    creator_single = [b for b in new_ids if on(b, "creator", "single")]
    creator_sequence = [b for b in new_ids if on(b, "creator", "sequence")]
    if creator_sequence:
        print(f"  {len(creator_sequence)} creator sequence brief(s) — a person makes these, slide by "
              f"slide; nothing is drafted: {', '.join(creator_sequence)}")
    if creator_single:
        print(f"  {len(creator_single)} creator brief(s) — the draft that follows is the "
              f"reference picture the person matches, not a work order: {', '.join(creator_single)}")
    if ai_sequence:
        print(f"  {len(ai_sequence)} AI sequence brief(s) — slide one is drafted below; slides two "
              f"onward are edits off it: the image-edit tool's sequence.py (team-only) <slide-one draft> "
              f"--brand {a.brand} --deltas <the brief>  ({', '.join(ai_sequence)})")
    if ai_single or ai_sequence:
        drafts(argparse.Namespace(brand=a.brand, briefs=",".join(sorted(ai_single + ai_sequence))))
        # The work order and its prompts, so the pack and the Drive folder are
        # complete the moment the draft lands.
        worksheet(argparse.Namespace(brand=a.brand, briefs=",".join(sorted(ai_single + ai_sequence))))
    new_ids = sorted(ai_single + ai_sequence + creator_single)
    if not new_ids:
        ready(argparse.Namespace(brand=a.brand))
        return
    # THE DRAFT STANDARD. Damon, 2026-09-17: "put this in chain." The chain
    # does not stop at a prompt for a session to run somewhere else — it
    # generates three rolls with the swipe as the reference, judges every
    # roll, ships the best passing one to Drive, the pack and the board, and
    # says which briefs got nothing and why. DRAFT-STANDARD.md is the ruling.
    print()
    draft(argparse.Namespace(brand=a.brand, briefs=",".join(sorted(new_ids)) or None,
                             no_ship=False))
    print()
    ready(argparse.Namespace(brand=a.brand))


def open_files(a):
    """Open ONE run on files handed over — the batch's door into this chain.

    `start` opens runs off a swipe library's blocks; a batch (Damon,
    2026-09-25: "literally ingest tens of videos and images at a time") hands
    over files that may sit in no library at all. Same run folder, same vars,
    same route as `start` — the slides of one post stay one sequence — and the
    slug still leads with the brand. Prints the slug; opens nothing twice."""
    files = [Path(f).expanduser() for f in a.file]
    for f in files:
        if not f.is_file():
            sys.exit(f"no file {f}")
    name = re.sub(r"[^a-z0-9]+", "-", (a.name or files[0].stem).lower()).strip("-")[:48]
    slug = f"{a.brand}-batch-{name}"
    run = P.RUNS / slug
    if (run / "assets").is_dir() and not a.again:
        print(slug); return
    route, form, n_slides = route_for(a, files)
    for s in ("assets", "out", "vars", "finals"):
        (run / s).mkdir(parents=True, exist_ok=True)
    shutil.copy(files[0], run / f"assets/source{'.png' if files[0].suffix.lower() == '.png' else '.jpg'}")
    if form == "sequence":
        for i, q in enumerate(files, 1):
            shutil.copy(q, run / f"assets/source-{i:02d}{q.suffix.lower()}")
    (run / "vars/brand_name.md").write_text(a.brand.upper() + "\n")
    (run / "vars/production_route.md").write_text(ROUTE_TEXT[(route, form)])
    (run / "vars/route.json").write_text(json.dumps(
        {"route": route, "form": form, "slides": n_slides,
         "why": f"handed over in a batch: {n_slides} still(s)"}, indent=1))
    # A file from a swipe library keeps its angle record; a loose one says it
    # has none rather than pointing stage 1 at a path that is not there.
    angle = run / "assets/angle.md"
    lib = next((q for q in files[0].parents if q.name in ("posts", "blocks")), None)
    rec = None
    if lib is not None:
        post = files[0].relative_to(lib).parts[0]
        for pool in (P.SWIPE_ORGANIC, P.SWIPE):
            q = pool / lib.parent.name / lib.name / f"{post}.md"
            if q.is_file():
                rec = q; break
    angle.write_text(rec.read_text() if rec else
                     "# No swipe-library record\n\nThis swipe was handed over as a file in a batch. "
                     "Its angle is what the picture itself says — read it off the teardown.\n")
    (run / "assets/source.json").write_text(json.dumps({
        "swipe": lib.parent.name if lib is not None else "batch",
        "block": a.name or files[0].stem, "block_file": f"{files[0].relative_to(lib).parts[0]}.md" if lib is not None else "",
        "angle_file": "assets/angle.md", "files": [str(f) for f in files],
        "swipe_kind": a.source or "unknown", "why": "handed over in a batch"}, indent=1))
    print(slug)


ROUTE = ROUTE_TEXT[("ai", "single")]      # the older re-open path keeps the AI route


def pages():
    reg = B.load()
    BP.OUT.mkdir(exist_ok=True)
    live = [(b, r) for b, r in reg["briefs"].items() if r.get("run")]
    for bid, rec in live:
        (BP.OUT / f"{bid}.html").write_text(BP.render(bid, rec, reg))
    (BP.OUT / "index.html").write_text(BP.brands(reg))
    for br in sorted({r["brand"] for r in reg["briefs"].values() if r.get("run")}):
        (BP.OUT / f"brand-{br}.html").write_text(BP.index(reg, br))
    print(f"\n{len(live)} brief pages rebuilt · http://127.0.0.1:8792")



def cast_from_roster(brand, lane, problem_hint=""):
    """Who this brand can put in an ad, chosen rather than named.

    Fewest uses first, then whoever's stated problem matches what the batch
    is about. A brand with no roster casts nobody — one of ours deliberately
    has none, and that is a legitimate answer, not a missing file.
    """
    import collections, re as _re
    f = P.brand(brand)["cast"] / "roster.json"
    if not f.is_file():
        return None
    def walk(o, out):
        if isinstance(o, dict):
            if o.get("id") and o.get("lane"):
                out.append(o)
            for v in o.values():
                walk(v, out)
        elif isinstance(o, list):
            for v in o:
                walk(v, out)
    people = []
    walk(json.loads(f.read_text()), people)
    people = [x for x in people if not lane or x.get("lane") == lane]
    if not people:
        return None
    # How often each man has already been cast, read off shipped ad names.
    used = collections.Counter()
    pat = _re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+){12}\b")
    prod = P.IMAGE_PROD
    for q in list(prod.rglob("*.png"))[:4000]:
        for n in pat.findall(q.name):
            used[n.split("-")[4]] += 1
    def score(x):
        hit = bool(problem_hint) and any(
            w in (x.get("problem") or "").lower()
            for w in problem_hint.lower().split() if len(w) > 4)
        return (0 if hit else 1, used.get(x["id"], 0))
    return sorted(people, key=score)[0]


def write_baseline(a):
    """The one cast and one product this brand's batch uses, named once.

    **A cast a person chose is never re-chosen.** The first version of this
    picked by fewest-uses on every run and promptly replaced the man Damon
    had just named, which is the churn the baseline exists to stop
    (2026-09-14). `--cast` pins him; a later run without `--cast` keeps him.
    `--recast` is the only way to let the tool choose again.
    """
    b = P.brand(a.brand)
    if not b["root"].is_dir():
        sys.exit(f"no brand folder at {b['root']} — a baseline needs a brand. "
                 f"RUN.md, 'What a new brand needs'.")
    existing = HERE / "drafts" / a.brand / "baseline.json"
    if existing.is_file() and not a.cast and not getattr(a, "recast", False):
        old = json.loads(existing.read_text())
        if old.get("cast_pinned") and old.get("cast"):
            print(f"  cast     {old['cast']['id']} — pinned, kept")
            print(f"  → {existing.relative_to(HERE)} unchanged")
            return old
    lane = a.lane or a.avatar
    man = None
    if a.cast:
        def walk(o):
            if isinstance(o, dict):
                if o.get("id") == a.cast: return o
                for v in o.values():
                    g = walk(v)
                    if g: return g
            if isinstance(o, list):
                for v in o:
                    g = walk(v)
                    if g: return g
        f = b["cast"] / "roster.json"
        man = walk(json.loads(f.read_text())) if f.is_file() else None
        if not man:
            sys.exit(f"no roster man {a.cast!r} for {a.brand}")
    else:
        man = cast_from_roster(a.brand, lane, a.problem or "")

    ids = b["cast"] / "identities.json"
    people = json.loads(ids.read_text()).get("people", {}) if ids.is_file() else {}
    el = (people.get(man["id"], {}) or {}).get("element_id") if man else None

    prod_el = None
    pf = b["cast"] / "identities.json"
    if pf.is_file():
        blob = pf.read_text()
        m = re.search(rf"{re.escape(a.product.upper())}\s+([0-9a-f-]{{36}})", blob)
        prod_el = m.group(1) if m else None

    out = {
        "_what": "The one set of people and things every draft in this batch uses. "
                 "It sits ABOVE the slot files, so the cast is named once instead "
                 "of once per ad. Change the cast here and every draft regenerates "
                 "as the same ad with a different person; nothing else moves.",
        "brand": a.brand, "product": a.product, "lane": lane,
        "core_avatar": a.avatar, "sub_avatar": (man or {}).get("sub"),
        "cast_pinned": bool(a.cast),
        "cast": ({"id": man["id"], "element": el,
                  **{k: man[k] for k in ("age", "reads", "hair", "build", "problem")
                     if k in man}} if man else None),
        "product_ref": ({"id": a.product, "element": prod_el} if prod_el else None),
        "_swap": "prompt.py render --slots <f> --cast <roster id> — his element and "
                 "his own roster lines come with him, and a cross-lane swap is refused.",
    }
    d = HERE / "drafts" / a.brand
    d.mkdir(parents=True, exist_ok=True)
    (d / "baseline.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"  cast     {(man or {}).get('id') or 'nobody — this brand has no roster'}")
    print(f"  product  {a.product}{'' if prod_el else '  (no product Element found)'}")
    print(f"  → {(d / 'baseline.json').relative_to(HERE)}")
    return out



def fill(a):
    """Run only the stages a run is missing.

    A stage can fail on its own — a guard rejects a reply, a model times out —
    and the run stops there with everything before it intact. Re-running the
    whole chain to recover one stage throws away good work and costs the
    model calls again. This finds the gaps and runs only those.
    """
    STAGE_FILE = {"1": "01-teardown.md", "2": "02-replication-spec.md",
                  "3": "03-injection.md", "4": "04-headlines.md",
                  "5": "05-image-variations.md", "6": "06-brief.md"}
    ORDER = ["1", "2", "3", "4", "5", "6"]
    # `--labels` also fills the element labels (stage 2b) on runs torn down
    # before the labelling step existed. It is asked for, never assumed: on a
    # brand with seventy finished runs it is seventy model calls.
    if getattr(a, "labels", False):
        STAGE_FILE["2b"] = "elements.json"
        ORDER = ["1", "2", "2b", "3", "4", "5", "6"]
    runs = sorted(P.RUNS.glob(f"{a.brand}-*")) if a.brand else sorted(P.RUNS.iterdir())
    todo = []
    for r in runs:
        if not r.is_dir():
            continue
        miss = [s for s, f in STAGE_FILE.items() if not (r / "out" / f).is_file()]
        if miss:
            todo.append((r, miss))
    if not todo:
        print("nothing missing"); return
    for r, miss in todo:
        print(f"  {r.name}  missing {', '.join(miss)}")
    print()
    if getattr(a, "dry_run", False):
        # One dry call per distinct gap, so a stage whose input is made by an
        # earlier missing stage reads as "made in this run", not MISSING.
        groups = {}
        for r, miss in todo:
            groups.setdefault(",".join(miss), []).append(r.name)
        rc = 0
        for miss, names in groups.items():
            rc = max(rc, run_py(names, miss, a).returncode)
        sys.exit(rc)
    # Stage by stage, all runs at once. Written serially first and it crawled:
    # nine runs x a ten-minute brief is an hour and a half in series and about
    # twelve minutes in parallel, for exactly the same work (2026-09-14).
    # Ordering only matters INSIDE a run — stage 6 reads stage 5 — so going
    # stage by stage keeps that and still parallelises across runs.
    for s in ORDER:
        group = [r.name for r, miss in todo if s in miss]
        if not group:
            continue
        print(f"\n[{s}] {len(group)} run{'s' if len(group) != 1 else ''}")
        run_py(group, s, a)

    # Issue an id to anything that now has a brief. `start` did this and
    # `fill` did not, so nine <brand> runs finished all six stages and were
    # invisible to the briefs tool — no id, no page (2026-09-14).
    reg = B.load()
    known = {r.get("run") for r in reg["briefs"].values()}
    for r, _ in todo:
        if getattr(a, "gates", "hold") == "hold" and say_held(r.name):
            continue
        if (r / "out/06-brief.md").is_file() and r.name not in known:
            bid, _rec = B.open_brief(r.name, a.brand, B.load(), a.product, a.avatar)
            print(f"  {bid}  {r.name}")
    pages()



def copy(a):
    """Every finished teardown through the copy machine, all at once.

    Damon, 2026-09-14: *"I just want simultaneous activations — a lot of the
    chains and briefs can just get pumped out now, we have pretty strong
    workflows."*

    A copy run is eleven stages and about eleven minutes. Nine of them in
    series is an hour and forty for the same work that takes eleven in
    parallel. Each run writes only to `results/<label>/` and
    `output/<label>/`, so there is nothing for them to collide over.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    COPY = P.REPO / "tools" / "copywriter"
    runs = [r for r in sorted(P.RUNS.glob(f"{a.brand}-*"))
            if (r / "out/01-teardown.md").is_file()]
    if a.runs:
        keep = {x.strip() for x in a.runs.split(",")}
        runs = [r for r in runs if any(k in r.name for k in keep)]
    if not runs:
        sys.exit(f"no finished teardowns for {a.brand}")

    def one(run):
        label = f"{a.brand}-{run.name.split('-', 2)[-1][:34]}"
        cmd = [sys.executable, str(COPY / "machine/copy.py"),
               str(run / "out/01-teardown.md"),
               "--brand", a.brand, "--product", a.product,
               "--write-as", a.write_as, "--channel", a.channel,
               "--label", label]
        r = subprocess.run(cmd, cwd=str(COPY), capture_output=True, text=True)
        return label, r.returncode, (r.stdout or r.stderr)[-300:]

    print(f"{len(runs)} copy runs · {a.write_as} · in parallel\n")
    with ThreadPoolExecutor(max_workers=len(runs)) as pool:
        jobs = {pool.submit(one, r): r for r in runs}
        for f in as_completed(jobs):
            label, rc, tail = f.result()
            print(("✓ " if rc == 0 else "✗ ") + label)
            if rc:
                print("   " + tail.replace("\n", "\n   ")[:400])


def pack_keys():
    """The style packs' own keys — the only legal values for `pack`."""
    f = P.IMAGE_PROD / "style-packs.json"
    if not f.is_file():
        f = P.REPO / "tools/image-production/style-packs.json"
    try:
        d = json.loads(f.read_text())
        return set(d.get("packs") or d)
    except (ValueError, OSError):
        return set()


PACK_KEYS = pack_keys()


def slots_from_brief(run, brand):
    """The brief's own plate prompt, as slot data the renderer can take.

    Done by hand twice and it went wrong both times — once because the
    heading differs between briefs, once because the pack laid over the
    prompt contradicted it. It is code now, and it is part of the chain
    rather than something a person remembers to do (Damon, 2026-09-14:
    "this needs to always be what is done").
    """
    t = (run / "out/06-brief.md").read_text()
    body = None
    # A real heading wins over a sentence that merely says the words. Stage 6
    # writes "## The plate prompt — control" near the end, and a hundred
    # lines earlier also writes "The plate is generated per the plate prompt
    # below" — the loose pattern matched THAT and captured the type-layer
    # JSON that followed it. p152 was one step from being generated off a
    # block of coordinates (2026-09-14).
    for pat in (r"^#{1,4}[^\S\n]*The plate prompt[^\n]*\n+(.*?)(?=\n#{1,4}[^\S\n]|\Z)",
                r"The plate prompt[^\n]*\*\*\s*\n+(.*?)(?=\n\*\*|\n```|\nCOMPOSITION)",
                r"\*\*The plate prompt\*\*(.*?)(?=\n\*\*|\n```|\nCOMPOSITION)",
                r"plate prompt[^\n]*\n+(.*?)(?=\n\*\*|\n```|\nCOMPOSITION)"):
        m = re.search(pat, t, re.S | re.I | re.M)
        if not m:
            continue
        cand = m.group(1).strip()
        # A capture that opens on a brace is a data block, not a prompt.
        if cand.lstrip("` \n").startswith("{"):
            continue
        cand = re.sub(r"```json.*?```", " ", cand, flags=re.S)
        if len(cand.strip()) > 200:
            body = re.sub(r"\s+", " ", cand).strip()
            # A brief that writes its plate prompt under "## The plate prompt"
            # opens a fenced block, and the pattern starts capturing AT the
            # fence — so "```" rode into p013's work order as the first thing
            # the image model would read. Strip a leading fence, and with it
            # any language tag. (2026-09-14)
            body = re.sub(r"^`{3,}\w*\s*", "", body).strip()
            break
    if not body:
        return None
    neg = ""
    nm = re.search(r"(?:NEGATIVE|Negatives?)\s*:?\s*(.+)$", body, re.S | re.I)
    if nm:
        neg = re.sub(r"\s+", " ", nm.group(1)).strip(); body = body[:nm.start()].strip()

    # --- the register, always. Never None. -----------------------------
    # Dropping the pack "because the brief writes its own register" removed
    # its negatives with it, and the pack's negatives are where "no phone in
    # frame" and "no better than the source" live. One decision, three
    # symptoms: a phone in a selfie, drafts far cleaner than the swipe, and
    # no negatives sent at all (Damon, 2026-09-14).
    low = body.lower()
    # THE LABEL WINS OVER THE KEYWORDS. Stage 2b already asked the element
    # library which style register this ad IS, and its answer was checked
    # against the library rather than guessed. The ladder below reads the
    # prompt's prose and gets it wrong in both directions — p186's four
    # hands on a flat neutral ground matched the black-and-white portrait
    # pack on "studio void", then the UGC pack once that was fixed, while
    # its own label said studio-object all along (2026-09-24). The ladder
    # stays as the fallback for runs labelled before 2b existed.
    labelled = None
    el = run / "out/elements.json"
    if el.is_file():
        try:
            import json as _json
            got = _json.loads(el.read_text()).get("labels", {}) or {}
            cand = ((got.get("style/image") or {}).get("id")
                    if isinstance(got.get("style/image"), dict)
                    else got.get("style/image"))
            if cand and cand != "none-fits" and cand in PACK_KEYS:
                labelled = cand
        except (ValueError, OSError):
            labelled = None
    # "studio void" alone used to land here, so every product-in-a-void ad
    # was given the black-and-white editorial portrait pack — p186's four
    # hands on a flat neutral ground came back as a mono portrait register
    # with "no product" in its negatives (2026-09-24). The pack is mono only
    # when the prompt actually says so.
    if "black and white" in low or "monochrome" in low or "greyscale" in low:
        pack = "studio-portrait-bw"
    elif "vintage" in low or "scanned" in low or "film print" in low:
        pack = "vintage-print"
    elif "mirror" in low:
        pack = "mirror-selfie"
    elif "selfie" in low or "arm's length" in low or "arm extended" in low:
        pack = "selfie"
    elif "flat vector" in low or "illustration" in low:
        pack = "flat-vector"
    elif "product" in low and "alone" in low:
        pack = "studio-object"
    else:
        pack = "candid-ugc"
    pack = labelled or pack

    # --- the source's own capture quality, off stage 1 -------------------
    td = (run / "out/01-teardown.md")
    fid = []
    if td.is_file():
        s = td.read_text()
        for key in ("Texture and stock", "Lens feel", "Grade", "Treatment"):
            m = re.search(rf"\*\*{key}[:\*]*\*?\*?\s*(.+)", s)
            if m:
                fid.append(re.sub(r"[`*]", "", m.group(1)).strip().rstrip("."))
    fidelity = ("match the source's own capture quality exactly, no better: "
                + "; ".join(x[:90] for x in fid)) if fid else None

    # --- the words that go in the frame: OURS, from the injection --------
    # This read stage 1 — the words the SOURCE carried — which is right for
    # an organic swipe whose text is incidental (p149's "2016") and
    # catastrophic for a paid one, where the source's words are a
    # competitor's ad copy. The froya batch was one step from rendering
    # "FRØYK/ORGANICS" and "Arctic Botanicals that erase wrinkles" into
    # <brand> ads — a third-party brand name in frame, which every brief
    # here calls an automatic reject.
    #
    # Stage 3 had already written ours. Its zone table's last column IS the
    # answer: "Fewer dark spots / by the holidays", "WEEK 2 / WEEK 4 /
    # WEEK 8". Organic frames still work, because injection copies an
    # unchanged zone across verbatim and marks it so.
    copy = None
    inj = run / "out/03-injection.md"
    if inj.is_file():
        # A HEADER ROW IS NOT A ZONE. Stage 3 writes more than one table, and
        # the art-direction table's header begins "| Zone | What is in frame |
        # Light | Lens and distance | …" — which matched, so "Lens and
        # distance" was handed to the image model as words to spell into the
        # frame, and it did (p186 roll 3, 2026-09-24). A real zone cell names
        # WHICH zone, so the word Zone must be followed by its identifier.
        rows = re.findall(r"^\|\s*Zone\s+[A-Za-z0-9][^|]*\|[^|]*\|[^|]*\|\s*([^|]{2,80}?)\s*\|",
                          inj.read_text(), re.M)
        SKIP = {"none", "n/a", "[none]", "-", "our copy", "source copy",
                "zone", "position", "unchanged", ""}
        words = []
        for w in rows:
            # Markdown emphasis is how the table shouts, not part of the
            # words — "**reprints**" would be spelled with asterisks.
            w = re.sub(r"\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`",
                       lambda m: m.group(1) or m.group(2) or m.group(3), w)
            w = re.sub(r"\s*[—-]+\s*unchanged\b.*$", "", w, flags=re.I).strip()
            w = re.sub(r"\s*\([^)]*\)\s*$", "", w).strip()
            # A bracketed cell describes a picture, not type.
            if not w or w.startswith("[") or w.startswith(":--"):
                continue
            if w.lower() in SKIP or w.lower().startswith(("none", "n/a")):
                continue
            # A cell naming a colour, a fill or an edge is art direction that
            # wandered into the copy column. Words that go in the frame do
            # not carry hex codes. (froya, 2026-09-14)
            if re.search(r"#[0-9A-Fa-f]{6}\b", w):
                continue
            if re.search(r"\b(?:fill|gradient|opacity|padding|margin|px)\b", w, re.I):
                continue
            # "[SLOT: first name, age 55-70]" is stage 3 saying it needed a
            # fact nobody supplied. It is a question, not copy, and it would
            # be spelled into the frame verbatim. (p162, 2026-09-15)
            if re.search(r"\[SLOT:|\bTK\b|\bTBD\b|\bXX+\b", w, re.I):
                continue
            words.append(w)
        if words:
            copy = ("the words this ad carries, in the same place and the same "
                    "weight, spelled exactly: " + "; ".join(f'"{w}"' for w in words[:6]))

    base = json.loads((HERE / "drafts" / brand / "baseline.json").read_text()) \
        if (HERE / "drafts" / brand / "baseline.json").is_file() else {}
    # --- which Elements this frame actually needs ------------------------
    # This used to attach the cast to every brief and the product to almost
    # none: cast went on unconditionally, and the product only if stage 6
    # happened to paste its uuid into the prose. The froya batch showed both
    # halves failing at once — p154 and p156 are product-only frames that
    # were about to be generated carrying a woman's face, and neither
    # carried the product Element, so the tube would have been invented.
    #
    # An invented product is the exact failure Damon ruled on 2026-09-09
    # ("go look at the device… all you need to do is swap the device"), and
    # a person in a packshot is the same mistake pointing the other way. So
    # the frame is read, and each Element goes on only when it is in shot.
    # Matched on whole words. Substring matching put a woman's face into a
    # product-only frame twice in this batch, because "warm natural stone"
    # contains "arm" — the third time this class of bug has landed here
    # after "cover" inside "recovery" and "rough" inside "through".
    PERSON = r"\b(?:wom[ae]n|m[ae]n|she|her|his|him|face|hands?|forearms?|" \
             r"chest|shoulders?|skin|hair|arms?|legs?|neck|subject|person|" \
             r"people|portrait|selfie|infant|baby|child)\b"
    PRODUCT = r"\b(?:tube|scrub|jar|bottle|packshot|sachet|product|" \
              r"squeeze|flip-top|cap|label)\b"
    # Match only what the frame CONTAINS. The brief's ban list lives in the
    # same paragraph — "No product, no tube, no scrub, no packshot" — so
    # matching the raw body reads every prohibition as a presence and
    # attaches the product Element to the frames that forbid it.
    positive = " ".join(s for s in re.split(r"(?<=[.;])\s+", body)
                        if not re.match(r"\s*(?:no|not|never|avoid)\b", s, re.I))
    # Camera vocabulary borrows the body's words and is not a body: a plate
    # of a sealed tube says "chest height", "portrait-compression" and
    # "the tube face", and all three read as a person. Dropped before the
    # match rather than removed from the word list, which would stop a real
    # chest or a real portrait from counting.
    positive = re.sub(
        r"\b(?:chest|eye|waist|lap|hip|knee|shoulder)[\s-]*(?:height|level)|"
        r"\bportrait[\s-]*(?:compression|compressed|orientation|lens|mode|crop)|"
        r"\b(?:tube|label|jar|bottle|cap|card|panel|dial|clock|box)\s+face",
        " ", positive, flags=re.I)
    has_person = bool(re.search(PERSON, positive, re.I))
    has_product = bool(re.search(PRODUCT, positive, re.I))
    refs = []
    if (base.get("cast") or {}).get("element") and has_person:
        refs.append("@cast")
    prod_el = (base.get("product_ref") or {}).get("element")
    if prod_el:
        # Strip any uuid stage 6 pasted into the prose — the Element goes in
        # as a reference, never as words inside the description.
        if prod_el in body:
            body = body.replace(f"`<<<{prod_el}>>>`", "").replace(
                f"<<<{prod_el}>>>", "")
            refs.append("@product")
        elif has_product:
            refs.append("@product")

    # --- which ratio route this frame takes ------------------------------
    # Scoped 2026-09-14 (SAFE-ZONE.md). Generating at 9:16 and asking the
    # model to keep the type inside the centre 4:5 lost the headline three
    # times out of three; generating at 4:5 and padding out is safe by
    # geometry. But a flat band across a candid photo announces it as an
    # advertisement, so the band is only acceptable where the frame already
    # looks like an ad.
    #
    # **The discriminator is words in the frame, not paid versus organic.**
    # I routed this on swipe_kind first and the froya batch disproved it the
    # same hour: froya is a paid library, and its most-cloned plate is a bare
    # UGC selfie with no text on it at all — the headline lives in the post
    # caption. A paid swipe is not necessarily a typeset frame.
    #
    # `copy` above is the words this ad carries, read off the injection's
    # own zone table. It is the measured thing, so it is what decides:
    # words in the frame can be clipped, and nothing else can.
    ratio, route = ("4:5", "pad") if copy else ("9:16", "native")
    kind = "organic"
    sj = run / "assets/source.json"
    if sj.is_file():
        kind = (json.loads(sj.read_text()).get("swipe_kind") or "organic")

    return {
        "pack": pack,
        "swipe_kind": kind,
        "ratio_route": route,
        # Either way the finished asset is 9:16 — Damon, 2026-09-14: *"the
        # full images should always be 9x16 so we can hit all placement."*
        # The only question is whether the generator is handed the tall
        # canvas or the safe one. See the route decided above.
        "ratio": ratio,
        "baseline": f"drafts/{brand}/baseline.json",
        "references": refs,
        "subject": body[:1600],
        "action": None, "wardrobe": None, "setting": None,
        "composition": None, "anchors": None,
        "fidelity": fidelity,
        "copy": copy,
        "negatives": (neg[:400] or None),
    }


def drafts(a):
    """One draft per brief: slots out of the brief, rendered, ready to run."""
    reg = B.load()
    # SAY WHO IS BEING CAST. The baseline is one file per BRAND but the thing
    # it describes is one BATCH, and a pinned cast survives into the next batch
    # in silence. On 2026-09-14 four 4bu_m <avatar> briefs were built carrying
    # the cast member pinned for an earlier batch —
    # stapled to the front of every prompt, contradicting the subject each
    # brief had just described. Nothing said so. Now it does.
    if a.brand:
        bf = HERE / "drafts" / a.brand / "baseline.json"
        if bf.is_file():
            b = json.loads(bf.read_text())
            c = b.get("cast") or {}
            if c.get("id"):
                print(f"  cast     {c['id']} ({b.get('lane') or 'no lane'})"
                      f"{' — PINNED, rides on every prompt below' if b.get('cast_pinned') else ''}")
                print("           he is wrong for any brief that describes its own "
                      "person — re-run `baseline --recast` or clear the cast first\n")
    ids = [x.strip() for x in a.briefs.split(",")] if a.briefs else \
        [b for b, r in reg["briefs"].items()
         if r.get("run") and (not a.brand or r.get("brand") == a.brand)]
    jobs = []
    for bid in sorted(ids):
        rec = reg["briefs"].get(bid)
        if not rec or not rec.get("run"):
            print(f"  ! {bid}: no run"); continue
        run = P.RUNS / rec["run"]
        if not (run / "out/06-brief.md").is_file():
            print(f"  ! {bid}: no brief yet"); continue
        s = slots_from_brief(run, rec["brand"])
        if not s:
            print(f"  ! {bid}: the brief carries no plate prompt"); continue
        # A variant carries a product the baseline does not: its Element is
        # not banked, so `@product` (the baseline's tube) must not ride on
        # the prompt. The designer attaches the product picture the pack
        # ships instead (2026-09-18).
        bl = HERE / "drafts" / rec["brand"] / "baseline.json"
        base_prod = json.loads(bl.read_text()).get("product") if bl.is_file() else None
        if rec.get("product") and base_prod and rec["product"] != base_prod:
            s["references"] = [x for x in (s.get("references") or []) if x != "@product"]
            s["subject"] = (f"The product is the {rec['product'].replace('-', ' ')} — the tube "
                            f"in the attached product picture, exact shape, colour and label. "
                            + (s.get("subject") or ""))
        sd = HERE / "drafts" / rec["brand"] / "slots"
        sd.mkdir(parents=True, exist_ok=True)
        (sd / f"{bid}.json").write_text(json.dumps(s, indent=1))
        r = subprocess.run([sys.executable,
                            str(P.IMAGE_PROD / "tools/prompt.py"),
                            "render", "--slots", str(sd / f"{bid}.json")],
                           capture_output=True, text=True, cwd=str(HERE))
        if r.returncode:
            print(f"  ! {bid}: {r.stderr.strip()[:120]}"); continue
        # Does the brief say every unit in frame is the same product? Its
        # anchors are where a brief states that, and the draft generator
        # would otherwise render the brand's whole range whenever the SOURCE
        # ad showed several products (2026-09-24).
        # Read the BRIEF, not the derived slots: slots_from_brief builds from
        # the plate prompt's prose and drops the anchors, so a decision stated
        # in the brief never reached the job.
        anch = (run / "out/06-brief.md").read_text(errors="replace")
        one_product = bool(re.search(
            r"\b(every|each|all)\b[^.;]{0,40}\b(identical|the same product|same product)\b"
            r"|\bidentical\b[^.;]{0,20}\b(tube|jar|bottle|unit|pack)s?\b",
            anch, re.I))
        jobs.append({"brief": bid, "run": rec["run"], "brand": rec["brand"],
                     "product": rec.get("product"), "one_product": one_product,
                     "ratio": s["ratio"], "model": DRAFT_MODEL,
                     "model_why": DRAFT_MODEL_WHY,
                     "quality": "high", "resolution": "2k",
                     "prompt": r.stdout.strip()})
        print(f"  {bid}  {len(r.stdout)} chars")
    d = HERE / "drafts" / (a.brand or "all"); d.mkdir(parents=True, exist_ok=True)
    f = d / "jobs.json"
    # A run for some briefs updates the brand's job list; it never replaces
    # it — a --briefs p164 run wiped the other twenty-one (2026-09-18).
    prior = json.loads(f.read_text())["jobs"] if f.is_file() else []
    by = {j["brief"]: j for j in prior}
    for j in jobs:
        by[j["brief"]] = j
    jobs_all = [by[k] for k in sorted(by)]
    f.write_text(json.dumps({"made": date.today().isoformat(), "jobs": jobs_all}, indent=2))
    print(f"\n{len(jobs)} draft prompts → {f.relative_to(HERE)}")
    print("next: the draft standard — chain.py draft --brand <brand> (DRAFT-STANDARD.md)")
    return f


def variant(a):
    """The same swipes, a different product (and its offer). Damon, 2026-09-18:
    "just use the same swipes, we're just adjusting the product and offer …
    establish that so whenever in the future we need to run a new product
    or offer with our swipes where we've already completed teardown work
    it's easy."

    Stages 1 and 2 — the teardown and the brand-free replication spec — do
    not know what product we sell, so they are copied, not re-run. Stages 3
    to 6 (injection, headlines, variations, brief) are where the product and
    the offer enter, so those run again with the new product. Each variant
    is its own run folder (`<run>--<product>`) and its own brief id, with
    `variant_of` pointing at the brief it came from; then the work orders,
    the draft standard, the pack and the board follow as for any brief."""
    reg = B.load()
    src_ids = [x.strip() for x in a.briefs.split(",")] if a.briefs else sorted(
        b for b, r in reg["briefs"].items()
        if r.get("brand") == a.brand and r.get("run") and r.get("product") != a.product
        and not r["run"].endswith(f"--{a.product}"))
    have = {r["run"] for r in reg["briefs"].values() if r.get("run")}
    opened, pairs = [], []
    for sid in src_ids:
        rec = reg["briefs"].get(sid)
        if not rec or not rec.get("run"):
            print(f"  ! {sid}: no run"); continue
        src = P.RUNS / rec["run"]
        new = P.RUNS / f"{rec['run']}--{a.product}"
        if new.name in have:
            print(f"  = {sid}: {a.product} variant already exists"); continue
        if not (src / "out/02-replication-spec.md").is_file():
            print(f"  ! {sid}: no stage-2 spec to reuse"); continue
        if getattr(a, "dry_run", False):
            print(f"  would open {new.name}  ← {sid}")
            opened.append(src.name); pairs.append((sid, new.name))
            continue
        (new / "out").mkdir(parents=True, exist_ok=True)
        (new / "vars").mkdir(exist_ok=True)
        shutil.copytree(src / "assets", new / "assets", dirs_exist_ok=True)
        for f in ("01-teardown.md", "02-replication-spec.md"):
            shutil.copy(src / "out" / f, new / "out" / f)
        # The labels describe the SWIPE, which a variant shares — reused like
        # the teardown, never asked for twice.
        for f in ("02b-elements.md", "elements.json"):
            if (src / "out" / f).is_file():
                shutil.copy(src / "out" / f, new / "out" / f)
        (new / "vars/brand_name.md").write_text(a.brand.upper() + "\n")
        (new / "vars/production_route.md").write_text(ROUTE)
        (new / "variant.json").write_text(json.dumps(
            {"variant_of": sid, "source_run": rec["run"], "product": a.product,
             "reused": ["01-teardown.md", "02-replication-spec.md"],
             "opened": date.today().isoformat()}, indent=1) + "\n")
        opened.append(new.name); pairs.append((sid, new.name))
    if not opened:
        sys.exit("nothing to run")
    avatar = a.avatar or next((reg["briefs"][s]["avatar"] for s, _ in pairs
                               if reg["briefs"][s].get("avatar")), None)
    a.avatar = avatar
    if getattr(a, "dry_run", False):
        # Dry: the source runs stand in for the variants — stages 1 and 2 are
        # copied across unchanged, so what stages 3–6 would read is the same.
        print(f"\nDRY RUN · {len(opened)} variants · {a.product} · stages 3–6\n")
        sys.exit(run_py(opened, "3,4,5,6", a).returncode)
    print(f"\n{len(opened)} variants · {a.product} · stages 3–6, in parallel\n")
    for stage in ("3", "4", "5", "6"):
        run_py(opened, stage, a)

    print()
    new_ids = []
    for sid, run_name in pairs:
        if getattr(a, "gates", "hold") == "hold" and say_held(run_name):
            continue
        if (P.RUNS / run_name / "out/06-brief.md").is_file():
            bid, r = B.open_brief(run_name, a.brand, B.load(), a.product, avatar)
            reg = B.load(); reg["briefs"][bid]["variant_of"] = sid; B.save(reg)
            new_ids.append(bid); print(f"  {bid}  ← {sid}  {run_name}")
        else:
            print(f"  ! {run_name} produced no brief")
    if not new_ids:
        sys.exit("no briefs")
    # The record goes where the workspace rules says output goes:
    # runs/<machine>/<brand>/<run-label>/ at the repo root, in git. The lane's
    # own runs/ is ignored by rule, so a run that only lives there is a run
    # that vanished in the next squash (2026-09-17, thirty-one of them).
    for _, run_name in pairs:
        record(a.brand, run_name)
    pages()
    ids = ",".join(new_ids)
    print()
    drafts(argparse.Namespace(brand=a.brand, briefs=ids))
    worksheet(argparse.Namespace(brand=a.brand, briefs=ids))
    print()
    draft(argparse.Namespace(brand=a.brand, briefs=ids, no_ship=a.no_ship, product=a.product))
    print()
    ready(argparse.Namespace(brand=a.brand))


def record(brand, run_name):
    """Copy a run's record — stage text, the labels, the swipe's index, the
    gates, the variant note — to runs/image-teardown/<brand>/<run-label>/ at
    the repo root (git). The root is FOUND by walking up (tools/paths.py), not
    counted: counting two folders up was right only until a folder moved.

    `tools/run.py` files every run as its stages finish, so this is no longer
    only the variants' door; it stays as the name `variant` has always called."""
    return G.file_record(brand, run_name)


def variations(a):
    """The variation batch, as the chain's own step: tools/variations.py.

    Damon, 2026-09-23: the stage ends at named pictures and one list — no ad
    copy, no import sheet. VARIATION-STANDARD.md is the ruling."""
    cmd = [sys.executable, str(HERE / "tools/variations.py"), "--brand", a.brand]
    for flag in ("product", "briefs", "batch", "drop"):
        if getattr(a, flag, None):
            cmd += [f"--{flag}", getattr(a, flag)]
    for flag in ("dry_run", "no_name"):
        if getattr(a, flag, False):
            cmd += ["--" + flag.replace("_", "-")]
    if getattr(a, "workers", None):
        cmd += ["--workers", str(a.workers)]
    subprocess.run(cmd, check=False)


def draft(a):
    """The draft standard, as the chain's own step: tools/draft.py."""
    cmd = [sys.executable, str(HERE / "tools/draft.py"), "--brand", a.brand]
    if getattr(a, "briefs", None):
        cmd += ["--briefs", a.briefs]
    if getattr(a, "no_ship", False):
        cmd += ["--no-ship"]
    if getattr(a, "product", None):
        cmd += ["--product", a.product]
    subprocess.run(cmd, check=False)


def worksheet(a):
    """The designer's work order for every brief: prompts, settings, rules."""
    cmd = [sys.executable, str(HERE / "tools/worksheet.py")]
    if a.brand:
        cmd += ["--brand", a.brand]
    if a.briefs:
        cmd += ["--briefs", a.briefs]
    return subprocess.run(cmd, cwd=str(HERE)).returncode


def ready(a):
    """What every brief still needs before it is the designer's.

    A brief is finished when it has all six stages, an id, a draft picture,
    a page, a folder on Drive and a work order. Anything short of that is not
    ready, and the page must not say it is.

    The work order joined the list on 2026-09-14, when Damon asked the
    question the previous definition had no answer to: *"What the hell does
    my designer do from here?"* A brief with a draft and no work order is
    finished for us and unstartable for them, which is not finished.

    **What "ready" means depends on who makes it** (2026-09-22, the first
    live creator-sequence run: the board called a correct brief "not ready"
    for missing the two things a creator brief is defined by not having). An
    AI single brief needs all six: a creator brief needs no work order, and a
    creator SEQUENCE needs no draft either — a person makes it, slide by
    slide. The row says which kind it is so nobody reads a dash as a hole.
    """
    reg = B.load()
    rows = []
    for bid, r in sorted(reg["briefs"].items()):
        if not r.get("run") or (a.brand and r.get("brand") != a.brand):
            continue
        run = P.RUNS / r["run"]
        stages = len([x for x in (run / "out").glob("0*.md")]) if (run / "out").is_dir() else 0
        d = HERE / "drafts" / r["brand"]
        draft = any((v / f"{bid}-draft.png").is_file() or (v / f"{bid}-plate.png").is_file()
                    for v in d.glob("v*") if v.is_dir())
        page = (BP.OUT / f"{bid}.html").is_file()
        drive = bool(r.get("drive"))
        order = (HERE / "worksheets" / r["brand"] / bid / "work-order.md").is_file()
        rt = read_route(run)
        rows.append((bid, r["brand"], stages, draft, page, drive, order,
                     r.get("plates") or 0, f"{rt['route']}·{rt['form']}"))
    if not rows:
        print("no briefs"); return
    bad = 0
    print(f"  {'':<6} {'brand':<9} {'route':<17} {'stages':<7} draft  page  drive  "
          f"work order")
    for bid, br, st, dr, pg, dv, wo, np, rt in rows:
        creator = rt.startswith("creator")
        wants_draft = not (creator and rt.endswith("sequence"))
        wants_order = not creator
        # six or more: the chain gained 2b (element labels) after these rows
        # were first counted, so a complete run writes seven files, and "7/6"
        # read as a fault when it was the opposite (2026-09-22).
        ok = st >= 6 and pg and dv and (dr or not wants_draft) and (wo or not wants_order)
        bad += 0 if ok else 1
        def cell(have, wanted, yes="yes", width=6):
            return (("yes" if have else "NO ") if wanted else "n/a").ljust(width)
        print(f"  {bid:<6} {br:<9} {rt:<17} {str(st) + ' files':<7} "
              f"{cell(dr, wants_draft)} {cell(pg, True, width=5)} "
              f"{cell(dv, True)} "
              f"{((str(np) + ' prompts') if wo else 'NO') if wants_order else 'n/a':<11}"
              f"{'' if ok else '<- not ready'}")
    print(f"\n{len(rows) - bad} of {len(rows)} ready — a creator brief needs no work order, "
          f"and a creator sequence needs no draft: a person makes it")


def ingest(a):
    """File what the session generated, and rebuild the pages."""
    res = json.loads(Path(a.results).read_text())
    jobs = {j["slug"]: j for j in
            json.loads((DRAFTS / "jobs.json").read_text())["jobs"]}
    n = 0
    for slug, path in res.items():
        j = jobs.get(slug)
        if not j:
            print(f"  ! {slug}: not in jobs.json"); continue
        dest = P.RUNS / j["run"] / "finals"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, dest / f"{slug}.png")
        n += 1
        print(f"  {slug} → runs/{j['run']}/finals/{slug}.png")
    print(f"{n} filed")
    pages()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--brand", required=True); s.add_argument("--product", required=True)
    s.add_argument("--avatar", required=True); s.add_argument("--swipe", required=True)
    s.add_argument("--count", type=int, default=3)
    s.add_argument("--picks", help="ranks to run, e.g. 1,2,5 — overrides --count")
    s.add_argument("--stills", help="plate stems inside the picked block(s), comma "
                   "separated — one run per plate instead of one per block")
    s.add_argument("--route", choices=list(ROUTES), default="ai",
                   help="who makes it: ai (the machine — the designer work order, default) "
                        "or creator (a person with a phone — a brief addressed to them)")
    s.add_argument("--form", choices=list(FORMS), default="auto",
                   help="what it is: single (one still) or sequence (a carousel or slideshow, "
                        "slide by slide). auto (default) reads it off the swipe")
    DRY = dict(dest="dry_run", action="store_true",
               help="resolve every stage's prompt, files and variables, say OK or "
                    "MISSING per stage — no model call, nothing opened, nothing spent")
    GATES = dict(choices=G.MODES, default="hold",
                 help="hold (default): a run that fails a gate stops and gets no "
                      "brief id. warn: the verdict is recorded and the run carries on")
    s.add_argument("--dry-run", "--dry", **DRY); s.add_argument("--gates", **GATES)
    bl = sub.add_parser("baseline")
    bl.add_argument("--brand", required=True); bl.add_argument("--product", required=True)
    bl.add_argument("--avatar", required=True); bl.add_argument("--lane")
    bl.add_argument("--cast", help="a roster id; omitted means chosen by fewest uses")
    bl.add_argument("--problem", help="what the batch is about, to bias the casting")
    bl.add_argument("--recast", action="store_true",
                    help="let the tool choose again, replacing a pinned cast")
    fl = sub.add_parser("fill")
    fl.add_argument("--brand", required=True); fl.add_argument("--product", required=True)
    fl.add_argument("--avatar", required=True)
    fl.add_argument("--labels", action="store_true",
                    help="also fill the element labels (stage 2b) on runs that lack them")
    fl.add_argument("--dry-run", "--dry", **DRY); fl.add_argument("--gates", **GATES)
    cp = sub.add_parser("copy")
    cp.add_argument("--brand", required=True); cp.add_argument("--product", required=True)
    cp.add_argument("--write-as", default="long-form")
    cp.add_argument("--channel", default="Meta (feed / Reels)")
    cp.add_argument("--runs", help="only these runs, comma separated")
    d = sub.add_parser("drafts"); d.add_argument("--briefs"); d.add_argument("--brand")
    dr = sub.add_parser("draft", help="the draft standard: generate, judge, ship")
    dr.add_argument("--brand", required=True); dr.add_argument("--briefs")
    dr.add_argument("--no-ship", action="store_true"); dr.add_argument("--product")
    vr = sub.add_parser("variations", help="the variation batch: generate, judge, name, list")
    vr.add_argument("--brand", required=True); vr.add_argument("--product")
    vr.add_argument("--briefs"); vr.add_argument("--batch"); vr.add_argument("--drop")
    vr.add_argument("--workers", type=int); vr.add_argument("--dry-run", action="store_true")
    vr.add_argument("--no-name", action="store_true")
    va = sub.add_parser("variant", help="the same swipes, a different product and offer")
    va.add_argument("--brand", required=True); va.add_argument("--product", required=True)
    va.add_argument("--avatar"); va.add_argument("--briefs", help="source brief ids; default every brief of the brand")
    va.add_argument("--no-ship", action="store_true")
    va.add_argument("--dry-run", "--dry", **DRY); va.add_argument("--gates", **GATES)
    rd = sub.add_parser("ready"); rd.add_argument("--brand")
    ws = sub.add_parser("worksheet")
    ws.add_argument("--brand"); ws.add_argument("--briefs")
    op = sub.add_parser("open", help="open one run on files handed over (the batch's door)")
    op.add_argument("--brand", required=True); op.add_argument("--file", action="append", required=True)
    op.add_argument("--name"); op.add_argument("--source")
    op.add_argument("--route", choices=list(ROUTES), default="ai"); op.add_argument("--form", default="auto")
    op.add_argument("--again", action="store_true")
    i = sub.add_parser("ingest"); i.add_argument("--results", required=True)
    sub.add_parser("pages")
    a = ap.parse_args()
    {"start": start, "baseline": write_baseline, "fill": fill, "copy": copy,
     "drafts": drafts, "ready": ready, "ingest": ingest,
     "worksheet": worksheet, "draft": draft, "variant": variant,
     "variations": variations, "open": open_files,
     "pages": lambda _: pages()}[a.cmd](a)
